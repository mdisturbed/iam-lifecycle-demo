from sqlalchemy import Column, Integer, String, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    system = Column(Enum("google", "github", name="account_system"))
    account_id = Column(String)
    status = Column(Enum("active", "disabled", "pending", name="account_status"), default="pending")

    user = relationship("User")
