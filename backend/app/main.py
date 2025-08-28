from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.v1.routes_health import router as health_router
from app.api.v1.routes_hr import router as hr_router
from app.api.v1.routes_sync import router as sync_router
from app.api.v1.routes_users import router as users_router
from app.api.v1.routes_runs import router as runs_router
from app.api.v1.routes_audit import router as audit_router
from app.api.v1.routes_dashboard import router as dashboard_router
from app.api.v1.routes_auth import router as auth_router
from app.api.v1.routes_rbac import router as rbac_router
from app.api.v1.routes_saas import router as saas_router
from app.core.db import engine
from app.models.base import Base
# Import all models to register them with Base.metadata
from app.models import user, account, entitlement, run, audit_log

# Create tables on startup
Base.metadata.create_all(bind=engine)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="IAM Lifecycle Demo", 
    version="0.1.0",
    description="Secure IAM lifecycle automation system"
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.localhost"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Add your frontend origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security headers
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; font-src 'self' https://cdnjs.cloudflare.com; script-src 'self' 'unsafe-inline'"
    return response

app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(hr_router, prefix="/api/v1/hr", tags=["hr"])
app.include_router(sync_router, prefix="/api/v1", tags=["sync"])
app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
app.include_router(runs_router, prefix="/api/v1/runs", tags=["runs"])
app.include_router(audit_router, prefix="/api/v1/audit", tags=["audit"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(rbac_router, prefix="/api/v1/rbac", tags=["rbac"])
app.include_router(saas_router, prefix="/api/v1/saas", tags=["saas"])
