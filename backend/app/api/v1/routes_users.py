from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.core.db import get_db
from app.core.security import require_read, require_write, TokenData
from app.models.user import User

router = APIRouter()

# Pydantic models for user management
class UserCreate(BaseModel):
    hr_user_id: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    department: str = Field(..., min_length=1, max_length=100)
    department_code: str = Field(..., pattern="^[0-9]{4}$", description="4-digit department code")
    title: str = Field(..., min_length=1, max_length=100)
    job_code: str = Field(..., pattern="^[0-9]{5}$", description="5-digit job code")
    location: str = Field(..., min_length=1, max_length=100)
    employment_type: str = Field(..., min_length=1, max_length=50)
    status: str = Field(..., pattern="^(Active|Terminated|Inactive)$")

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    department: Optional[str] = Field(None, min_length=1, max_length=100)
    department_code: Optional[str] = Field(None, pattern="^[0-9]{4}$", description="4-digit department code")
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    job_code: Optional[str] = Field(None, pattern="^[0-9]{5}$", description="5-digit job code")
    location: Optional[str] = Field(None, min_length=1, max_length=100)
    employment_type: Optional[str] = Field(None, min_length=1, max_length=50)
    status: Optional[str] = Field(None, pattern="^(Active|Terminated|Inactive)$")

class UserResponse(BaseModel):
    id: int
    hr_user_id: str
    email: str
    first_name: str
    last_name: str
    department: str
    department_code: str
    title: str
    job_code: str
    location: str
    employment_type: str
    status: str
    
    class Config:
        from_attributes = True

@router.get("")
async def list_users(
    q: str | None = Query(None), 
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_read)
):
    """List all users with optional search"""
    qset = db.query(User)
    if q:
        like = f"%{q}%"
        qset = qset.filter((User.email.ilike(like)) | (User.first_name.ilike(like)) | (User.last_name.ilike(like)))
    return [
        {
            "id": u.id,
            "hr_user_id": u.hr_user_id,
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "department": u.department,
            "department_code": u.department_code,
            "title": u.title,
            "job_code": u.job_code,
            "location": u.location,
            "employment_type": u.employment_type,
            "status": u.status,
        }
        for u in qset.limit(100).all()
    ]

@router.get("/{user_id}")
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_read)
):
    """Get a specific user by HR user ID"""
    user = db.query(User).filter(User.hr_user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse.from_orm(user)

@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_write)
):
    """Create a new user"""
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.hr_user_id == user_data.hr_user_id) | 
        (User.email == user_data.email)
    ).first()
    
    if existing_user:
        if existing_user.hr_user_id == user_data.hr_user_id:
            raise HTTPException(status_code=400, detail="User with this HR ID already exists")
        else:
            raise HTTPException(status_code=400, detail="User with this email already exists")
    
    try:
        # Create new user
        new_user = User(
            hr_user_id=user_data.hr_user_id,
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            department=user_data.department,
            department_code=user_data.department_code,
            title=user_data.title,
            job_code=user_data.job_code,
            location=user_data.location,
            employment_type=user_data.employment_type,
            status=user_data.status
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return UserResponse.from_orm(new_user)
        
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to create user due to database constraint")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_write)
):
    """Update an existing user"""
    user = db.query(User).filter(User.hr_user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        # Store original status to detect termination
        original_status = user.status
        
        # Update only provided fields
        update_data = user_data.dict(exclude_unset=True)
        
        # Check for email uniqueness if email is being updated
        if "email" in update_data and update_data["email"] != user.email:
            existing_email = db.query(User).filter(
                User.email == update_data["email"],
                User.id != user.id
            ).first()
            if existing_email:
                raise HTTPException(status_code=400, detail="Email already exists for another user")
        
        for field, value in update_data.items():
            setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        
        # If user status was changed to Terminated, trigger access clearing
        if ("status" in update_data and 
            update_data["status"].lower() == "terminated" and 
            original_status.lower() != "terminated"):
            try:
                from app.workers.tasks import run_sync_task
                # Queue a live sync to immediately clear the terminated user's access
                task = run_sync_task.delay(dry_run=False)
                print(f"Queued access clearing sync (task_id: {task.id}) for newly terminated user {user_id}")
            except Exception as sync_error:
                # Log the error but don't fail the update
                print(f"Warning: Failed to queue access clearing sync for terminated user {user_id}: {sync_error}")
        
        return UserResponse.from_orm(user)
        
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to update user due to database constraint")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_write)
):
    """Delete a user (sets status to Terminated instead of hard delete)"""
    user = db.query(User).filter(User.hr_user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        # Store original status to check if this is a new termination
        original_status = user.status
        
        # Soft delete - set status to Terminated
        user.status = "Terminated"
        db.commit()
        
        # If user was just terminated (not already terminated), trigger immediate access clearing
        task_id = None
        if original_status.lower() != "terminated":
            try:
                from app.workers.tasks import run_sync_task
                # Queue a live sync to immediately clear the terminated user's access
                task = run_sync_task.delay(dry_run=False)
                task_id = task.id
            except Exception as sync_error:
                # Log the error but don't fail the termination
                print(f"Warning: Failed to queue access clearing sync for terminated user {user_id}: {sync_error}")
        
        response = {
            "message": f"User {user_id} has been terminated",
            "user_id": user_id,
            "email": user.email,
            "access_cleared": original_status.lower() != "terminated"
        }
        
        if task_id:
            response["sync_task_id"] = task_id
            response["message"] += ". Access clearing sync has been queued."
        
        return response
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")


@router.post("/{user_id}/reactivate")
async def reactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_write)
):
    """Reactivate a terminated user"""
    user = db.query(User).filter(User.hr_user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.status != "Terminated":
        raise HTTPException(status_code=400, detail="User is not terminated")
    
    try:
        user.status = "Active"
        db.commit()
        
        # Queue a sync to restore appropriate access
        task_id = None
        try:
            from app.workers.tasks import run_sync_task
            task = run_sync_task.delay(dry_run=False)
            task_id = task.id
            print(f"Queued access restoration sync (task_id: {task.id}) for reactivated user {user_id}")
        except Exception as sync_error:
            print(f"Warning: Failed to queue access restoration sync for reactivated user {user_id}: {sync_error}")
        
        response = {
            "message": f"User {user_id} has been reactivated",
            "user_id": user_id,
            "email": user.email,
            "status": "Active"
        }
        
        if task_id:
            response["sync_task_id"] = task_id
            response["message"] += " and access restoration has been queued"
        
        return response
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reactivate user: {str(e)}")
