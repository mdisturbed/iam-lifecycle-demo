from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from datetime import datetime
from app.models.base import Base

class Run(Base):
    __tablename__ = "runs"
    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    actor = Column(String, default="system")
    dry_run = Column(Boolean, default=True)
    summary = Column(JSON, nullable=True)
