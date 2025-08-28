from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime

from app.core.db import get_db
from app.core.security import require_read, require_write, TokenData

router = APIRouter()

# Pydantic models for SaaS management
class SaasAppConfig(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern="^(google|github|slack|okta|custom)$")
    description: Optional[str] = Field(None, max_length=500)
    base_url: Optional[HttpUrl] = None
    api_endpoint: Optional[HttpUrl] = None
    icon: Optional[str] = None
    enabled: bool = True

class SaasAppUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    base_url: Optional[HttpUrl] = None
    api_endpoint: Optional[HttpUrl] = None
    icon: Optional[str] = None
    enabled: Optional[bool] = None

class SaasConnectionConfig(BaseModel):
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    api_key: Optional[str] = None
    webhook_url: Optional[HttpUrl] = None
    scopes: Optional[List[str]] = []
    additional_config: Optional[Dict[str, Any]] = {}

class SaasAppResponse(BaseModel):
    id: str
    name: str
    type: str
    description: Optional[str]
    base_url: Optional[str]
    api_endpoint: Optional[str]
    icon: Optional[str]
    enabled: bool
    created_at: datetime
    last_sync: Optional[datetime]
    status: str  # connected, disconnected, error
    user_count: int
    group_count: int

# In-memory store for SaaS apps (in production, this would be a database)
saas_apps_store = {
    "google-workspace": {
        "id": "google-workspace",
        "name": "Google Workspace",
        "type": "google",
        "description": "Google Workspace (formerly G Suite) integration for email, groups, and drive access",
        "base_url": "https://workspace.google.com",
        "api_endpoint": "https://www.googleapis.com/admin/directory/v1",
        "icon": "fab fa-google",
        "enabled": True,
        "created_at": datetime.now(),
        "last_sync": datetime.now(),
        "status": "connected",
        "user_count": 15,
        "group_count": 8
    },
    "github": {
        "id": "github",
        "name": "GitHub",
        "type": "github",
        "description": "GitHub organization and team management",
        "base_url": "https://github.com",
        "api_endpoint": "https://api.github.com",
        "icon": "fab fa-github",
        "enabled": True,
        "created_at": datetime.now(),
        "last_sync": datetime.now(),
        "status": "connected",
        "user_count": 8,
        "group_count": 12
    }
}

@router.get("/apps")
async def list_saas_apps(
    current_user: TokenData = Depends(require_read)
):
    """List all configured SaaS applications"""
    return [
        SaasAppResponse(**app_data) for app_data in saas_apps_store.values()
    ]

@router.get("/apps/{app_id}")
async def get_saas_app(
    app_id: str,
    current_user: TokenData = Depends(require_read)
):
    """Get details of a specific SaaS application"""
    if app_id not in saas_apps_store:
        raise HTTPException(status_code=404, detail="SaaS app not found")
    
    return SaasAppResponse(**saas_apps_store[app_id])

@router.post("/apps", response_model=SaasAppResponse)
async def create_saas_app(
    app_config: SaasAppConfig,
    current_user: TokenData = Depends(require_write)
):
    """Add a new SaaS application"""
    app_id = f"{app_config.type}-{app_config.name.lower().replace(' ', '-')}"
    
    if app_id in saas_apps_store:
        raise HTTPException(status_code=400, detail="SaaS app with this name already exists")
    
    new_app = {
        "id": app_id,
        "name": app_config.name,
        "type": app_config.type,
        "description": app_config.description,
        "base_url": str(app_config.base_url) if app_config.base_url else None,
        "api_endpoint": str(app_config.api_endpoint) if app_config.api_endpoint else None,
        "icon": app_config.icon or f"fab fa-{app_config.type}" if app_config.type != "custom" else "fas fa-cube",
        "enabled": app_config.enabled,
        "created_at": datetime.now(),
        "last_sync": None,
        "status": "disconnected",
        "user_count": 0,
        "group_count": 0
    }
    
    saas_apps_store[app_id] = new_app
    
    return SaasAppResponse(**new_app)

@router.put("/apps/{app_id}", response_model=SaasAppResponse)
async def update_saas_app(
    app_id: str,
    app_update: SaasAppUpdate,
    current_user: TokenData = Depends(require_write)
):
    """Update a SaaS application configuration"""
    if app_id not in saas_apps_store:
        raise HTTPException(status_code=404, detail="SaaS app not found")
    
    app = saas_apps_store[app_id]
    update_data = app_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        if field in ["base_url", "api_endpoint"] and value:
            app[field] = str(value)
        else:
            app[field] = value
    
    return SaasAppResponse(**app)

@router.delete("/apps/{app_id}")
async def delete_saas_app(
    app_id: str,
    current_user: TokenData = Depends(require_write)
):
    """Remove a SaaS application"""
    if app_id not in saas_apps_store:
        raise HTTPException(status_code=404, detail="SaaS app not found")
    
    # Don't allow deleting built-in apps
    if app_id in ["google-workspace", "github"]:
        raise HTTPException(status_code=400, detail="Cannot delete built-in SaaS applications")
    
    app = saas_apps_store.pop(app_id)
    
    return {
        "message": f"SaaS app '{app['name']}' removed successfully",
        "app_id": app_id
    }

@router.post("/apps/{app_id}/connection")
async def configure_saas_connection(
    app_id: str,
    connection_config: SaasConnectionConfig,
    current_user: TokenData = Depends(require_write)
):
    """Configure connection settings for a SaaS application"""
    if app_id not in saas_apps_store:
        raise HTTPException(status_code=404, detail="SaaS app not found")
    
    app = saas_apps_store[app_id]
    
    # Simulate connection test
    if connection_config.client_id or connection_config.api_key:
        app["status"] = "connected"
        app["last_sync"] = datetime.now()
    else:
        app["status"] = "disconnected"
    
    return {
        "message": f"Connection configured for {app['name']}",
        "app_id": app_id,
        "status": app["status"]
    }

@router.post("/apps/{app_id}/test-connection")
async def test_saas_connection(
    app_id: str,
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(require_write)
):
    """Test connection to a SaaS application"""
    if app_id not in saas_apps_store:
        raise HTTPException(status_code=404, detail="SaaS app not found")
    
    app = saas_apps_store[app_id]
    
    # Simulate connection test
    import asyncio
    await asyncio.sleep(0.5)  # Simulate API call
    
    # Update connection status
    app["status"] = "connected"
    app["last_sync"] = datetime.now()
    
    return {
        "message": f"Connection test successful for {app['name']}",
        "app_id": app_id,
        "status": "connected",
        "response_time_ms": 245
    }

@router.post("/apps/{app_id}/sync")
async def sync_saas_app(
    app_id: str,
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(require_write)
):
    """Trigger a sync for a SaaS application"""
    if app_id not in saas_apps_store:
        raise HTTPException(status_code=404, detail="SaaS app not found")
    
    app = saas_apps_store[app_id]
    
    if app["status"] != "connected":
        raise HTTPException(status_code=400, detail="Cannot sync disconnected SaaS app")
    
    # Simulate sync process
    app["last_sync"] = datetime.now()
    
    # Simulate updated counts
    if app_id == "google-workspace":
        app["user_count"] = 18
        app["group_count"] = 9
    elif app_id == "github":
        app["user_count"] = 12
        app["group_count"] = 15
    
    return {
        "message": f"Sync initiated for {app['name']}",
        "app_id": app_id,
        "sync_started_at": app["last_sync"],
        "users_synced": app["user_count"],
        "groups_synced": app["group_count"]
    }

@router.get("/apps/{app_id}/users")
async def list_saas_app_users(
    app_id: str,
    current_user: TokenData = Depends(require_read)
):
    """List users in a SaaS application"""
    if app_id not in saas_apps_store:
        raise HTTPException(status_code=404, detail="SaaS app not found")
    
    app = saas_apps_store[app_id]
    
    # Mock user data for the SaaS app
    mock_users = []
    if app_id == "google-workspace":
        mock_users = [
            {"id": "user1", "email": "john.doe@example.com", "name": "John Doe", "status": "active"},
            {"id": "user2", "email": "jane.smith@example.com", "name": "Jane Smith", "status": "active"},
            {"id": "user3", "email": "bob.johnson@example.com", "name": "Bob Johnson", "status": "suspended"}
        ]
    elif app_id == "github":
        mock_users = [
            {"id": "dev1", "username": "johndoe", "name": "John Doe", "role": "member"},
            {"id": "dev2", "username": "janesmith", "name": "Jane Smith", "role": "admin"},
        ]
    
    return {
        "app_id": app_id,
        "app_name": app["name"],
        "total_users": len(mock_users),
        "users": mock_users
    }

@router.get("/summary")
async def get_saas_summary(
    current_user: TokenData = Depends(require_read)
):
    """Get summary statistics for all SaaS applications"""
    total_apps = len(saas_apps_store)
    connected_apps = sum(1 for app in saas_apps_store.values() if app["status"] == "connected")
    total_users = sum(app["user_count"] for app in saas_apps_store.values())
    total_groups = sum(app["group_count"] for app in saas_apps_store.values())
    
    return {
        "total_apps": total_apps,
        "connected_apps": connected_apps,
        "disconnected_apps": total_apps - connected_apps,
        "total_managed_users": total_users,
        "total_groups": total_groups,
        "apps": [
            {
                "id": app["id"],
                "name": app["name"],
                "type": app["type"],
                "status": app["status"],
                "users": app["user_count"],
                "groups": app["group_count"],
                "last_sync": app["last_sync"]
            }
            for app in saas_apps_store.values()
        ]
    }
