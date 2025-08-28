from fastapi import APIRouter, Query
from app.workers.tasks import run_sync_task

router = APIRouter()

@router.post("/sync")
async def sync(dry_run: bool = Query(True)):
    task = run_sync_task.delay(dry_run=dry_run)
    return {"queued": True, "task_id": str(task)}
