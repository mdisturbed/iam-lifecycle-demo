from datetime import timedelta
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.core.security import (
    authenticate_user, 
    create_access_token, 
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user,
    TokenData
)

router = APIRouter()


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest):
    """Authenticate user and return JWT token"""
    user = authenticate_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"], "scopes": user["scopes"]},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 compatible token endpoint"""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"], "scopes": user["scopes"]},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer", 
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.get("/me")
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """Get current user information"""
    return {
        "username": current_user.username,
        "scopes": current_user.scopes
    }


@router.get("/demo-users")
async def get_demo_users():
    """Get available demo user accounts for testing"""
    return {
        "users": [
            {"username": "admin", "password": "admin123", "scopes": ["admin", "read", "write"]},
            {"username": "readonly", "password": "readonly123", "scopes": ["read"]}
        ],
        "note": "These are demo credentials. In production, use proper user management."
    }
