from fastapi import APIRouter
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter()

@router.get("/")
async def dashboard():
    """Serve the IAM dashboard HTML interface"""
    dashboard_path = Path(__file__).parent.parent.parent / "static" / "dashboard.html"
    return FileResponse(dashboard_path, media_type="text/html")
