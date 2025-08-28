from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from datetime import datetime
from app.models.base import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    ts = Column(DateTime, default=datetime.utcnow)
    actor = Column(String, default="system")
    action = Column(String)
    entity_type = Column(String)
    entity_id = Column(String)
    details = Column(JSON)
    success = Column(Boolean, default=True)
