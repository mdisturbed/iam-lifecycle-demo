from celery import Celery
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.db import SessionLocal
from app.models.user import User
from app.models.run import Run
from app.services.identity_engine import IdentityEngine
from app.services.diff import plan_changes
from app.services.provisioner.google_ws_mock import GoogleWSMock
from app.services.provisioner.github_mock import GitHubMock

celery_app = Celery("iam-demo", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

@celery_app.task
def run_sync_task(dry_run: bool = True) -> dict:
    db: Session = SessionLocal()
    run = Run(dry_run=dry_run)
    db.add(run)
    db.commit()
    db.refresh(run)

    engine = IdentityEngine()
    google = GoogleWSMock()
    github = GitHubMock()

    created = updated = disabled = access_cleared = 0
    results: list[dict] = []

    for u in db.query(User).all():
        user_dict = {
            "email": u.email,
            "department": u.department,
            "title": u.title,
            "location": u.location,
            "employment_type": u.employment_type,
            "status": u.status,
        }
        desired = engine.desired_for_user(user_dict)
        current = {}
        current.update(google.fetch_current(u.email))
        current.update(github.fetch_current(u.email))
        plan = plan_changes(desired, current)
        
        # Track if this is a terminated user having access cleared
        is_terminated = u.status.lower() == "terminated"
        has_current_access = (
            current.get("google", {}).get("groups", []) or 
            current.get("github", {}).get("teams", [])
        )
        
        if is_terminated and has_current_access:
            access_cleared += 1
            if not dry_run:
                print(f"Clearing all access for terminated user: {u.email}")
            else:
                print(f"Would clear all access for terminated user: {u.email}")
        
        if not dry_run:
            google.apply(u.email, plan)
            github.apply(u.email, plan)
            
        results.append({
            "user": u.email, 
            "user_status": u.status,
            "desired": desired, 
            "current": current, 
            "plan": plan,
            "access_cleared": is_terminated and has_current_access
        })

    from datetime import datetime
    run.completed_at = datetime.utcnow()
    run.summary = {
        "count": len(results), 
        "processed": len(results),
        "access_cleared": access_cleared,
        "terminated_users_processed": sum(1 for r in results if r.get("user_status", "").lower() == "terminated")
    }
    db.add(run)
    db.commit()
    
    return {
        "run_id": run.id, 
        "results": results,
        "summary": run.summary
    }
