from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.models.base import Base

class Entitlement(Base):
    __tablename__ = "entitlements"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    entitlement_key = Column(String, index=True)
    source = Column(Enum("role", "rule", "manual", name="entitlement_source"), default="role")

    user = relationship("User")
