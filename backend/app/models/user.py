from sqlalchemy import Column, Integer, String, Enum
from app.models.base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    hr_user_id = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, index=True)
    department = Column(String)
    department_code = Column(String(4))  # 4-digit department code
    title = Column(String)
    job_code = Column(String(5))  # 5-digit job code
    location = Column(String)
    employment_type = Column(String)
    status = Column(Enum("Active", "Terminated", name="user_status"), default="Active")
