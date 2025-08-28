from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.run import Run
from datetime import datetime

router = APIRouter()

@router.get("")
async def list_runs(limit: int = Query(20, le=100), db: Session = Depends(get_db)):
    runs = db.query(Run).order_by(Run.started_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "actor": r.actor,
            "dry_run": r.dry_run,
            "summary": r.summary,
        }
        for r in runs
    ]

@router.get("/{run_id}")
async def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        return {"error": "Run not found"}
    
    return {
        "id": run.id,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "actor": run.actor,
        "dry_run": run.dry_run,
        "summary": run.summary,
    }
