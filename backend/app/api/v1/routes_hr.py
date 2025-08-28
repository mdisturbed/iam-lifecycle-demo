from fastapi import APIRouter, UploadFile, File, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.db import get_db
from app.core.security import require_write, TokenData
from app.utils.csv_loader import parse_hr_csv
from app.workers.tasks import run_sync_task
from app.services.audit import log

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

@router.post("/upload")
@limiter.limit("5/minute")  # Limit CSV uploads
async def upload_hr_csv(
    request: Request,
    csv: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_write)
):
    # File validation
    if not csv.filename or not csv.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files allowed")
    
    if csv.size and csv.size > 1024 * 1024:  # 1MB limit
        raise HTTPException(status_code=400, detail="File too large (max 1MB)")
    
    try:
        records = await csv.read()
        users = parse_hr_csv(records.decode("utf-8"))
        
        # Audit log the upload
        log(db, current_user.username, "hr_upload", "csv_file", csv.filename, 
            {"user_count": len(users), "file_size": len(records)})
        
        # For demo: save HR users into DB (upsert-like behavior)
        # In real world, you may maintain a staging table
        from app.models.user import User
        updated_count = 0
        created_count = 0
        
        for u in users:
            existing = db.query(User).filter(User.hr_user_id == u["hr_user_id"]).first()
            if existing:
                for k, v in u.items():
                    setattr(existing, k, v)
                updated_count += 1
            else:
                db.add(User(**u))
                created_count += 1
        
        db.commit()
        
        # Audit log the database changes
        log(db, current_user.username, "user_bulk_update", "user_table", "bulk",
            {"created": created_count, "updated": updated_count})

        # kick off a dry-run sync by default
        run_id = run_sync_task.delay(dry_run=True)
        
        return {
            "uploaded": len(users), 
            "created": created_count,
            "updated": updated_count,
            "run_task_id": str(run_id)
        }
        
    except Exception as e:
        # Audit log the failure
        log(db, current_user.username, "hr_upload_failed", "csv_file", csv.filename or "unknown",
            {"error": str(e)}, success=False)
        raise HTTPException(status_code=400, detail=f"CSV processing failed: {str(e)}")
