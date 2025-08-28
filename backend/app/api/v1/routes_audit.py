from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.audit_log import AuditLog

router = APIRouter()

@router.get("")
async def list_audit_logs(
    limit: int = Query(50, le=200), 
    entity_type: str | None = Query(None),
    action: str | None = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog)
    
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if action:
        query = query.filter(AuditLog.action == action)
    
    logs = query.order_by(AuditLog.ts.desc()).limit(limit).all()
    
    return [
        {
            "id": log.id,
            "timestamp": log.ts.isoformat() if log.ts else None,
            "actor": log.actor,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "success": log.success,
            "details": log.details,
        }
        for log in logs
    ]
