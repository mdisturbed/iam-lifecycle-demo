import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWTError
from pydantic import BaseModel


class TokenData(BaseModel):
    username: str
    scopes: list[str] = []


# Generate a secure secret key (in production, use environment variable)
SECRET_KEY = secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Demo users (in production, use proper user store)
DEMO_USERS = {
    "admin": {
        "username": "admin",
        "hashed_password": hashlib.sha256("admin123".encode()).hexdigest(),  # demo only
        "scopes": ["admin", "read", "write"]
    },
    "readonly": {
        "username": "readonly", 
        "hashed_password": hashlib.sha256("readonly123".encode()).hexdigest(),  # demo only
        "scopes": ["read"]
    }
}

security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password (demo implementation - use bcrypt in production)"""
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticate user credentials"""
    user = DEMO_USERS.get(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> TokenData:
    """Extract and validate current user from JWT token"""
    if not credentials:
        # For demo purposes, allow some endpoints without auth
        # In production, this should raise an exception
        return TokenData(username="anonymous", scopes=["read"])
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        scopes: list = payload.get("scopes", [])
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return TokenData(username=username, scopes=scopes)
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_scopes(required_scopes: list[str]):
    """Dependency to require specific scopes"""
    def check_scopes(current_user: TokenData = Depends(get_current_user)):
        if not any(scope in current_user.scopes for scope in required_scopes):
            raise HTTPException(
                status_code=403, 
                detail=f"Insufficient permissions. Required: {required_scopes}"
            )
        return current_user
    return check_scopes


# Convenience dependencies
require_read = require_scopes(["read", "admin"])
require_write = require_scopes(["write", "admin"]) 
require_admin = require_scopes(["admin"])
