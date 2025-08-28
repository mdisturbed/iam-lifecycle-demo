from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog

MASK = "***"

def mask_email(s: str | None) -> str:
    if not s:
        return ""
    name, _, domain = s.partition("@")
    return (name[:2] + "***@" + domain) if domain else MASK

def log(db: Session, actor: str, action: str, entity_type: str, entity_id: str, details: dict, success: bool=True):
    db.add(AuditLog(actor=actor, action=action, entity_type=entity_type, entity_id=entity_id, details=details, success=success))
    db.commit()
