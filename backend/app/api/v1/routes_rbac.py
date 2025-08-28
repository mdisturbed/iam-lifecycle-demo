from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.core.db import get_db
from app.core.security import require_read, require_write, TokenData
from app.models.user import User
from app.models.entitlement import Entitlement
from app.models.account import Account
from app.services.identity_engine import IdentityEngine
from app.services.diff import plan_changes
from app.services.provisioner.google_ws_mock import GoogleWSMock
from app.services.provisioner.github_mock import GitHubMock

router = APIRouter()

# Request/Response models for policy management
class SystemEntitlements(BaseModel):
    groups: Optional[List[str]] = []
    teams: Optional[List[str]] = []

class RoleMapping(BaseModel):
    google: Optional[SystemEntitlements] = None
    github: Optional[SystemEntitlements] = None

class ConditionalRule(BaseModel):
    when: str
    grant: Dict[str, SystemEntitlements]

class PolicyUpdate(BaseModel):
    roles: Optional[Dict[str, RoleMapping]] = None
    rules: Optional[List[ConditionalRule]] = None

@router.get("/users/{user_id}/entitlements")
async def get_user_entitlements(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_read)
):
    """Get entitlements for a specific user"""
    user = db.query(User).filter(User.hr_user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    entitlements = db.query(Entitlement).filter(Entitlement.user_id == user.id).all()
    
    return {
        "user": {
            "id": user.id,
            "hr_user_id": user.hr_user_id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "department": user.department,
            "title": user.title,
            "location": user.location,
            "employment_type": user.employment_type,
            "status": user.status
        },
        "entitlements": [
            {
                "id": e.id,
                "entitlement_key": e.entitlement_key,
                "source": e.source
            }
            for e in entitlements
        ]
    }

@router.get("/users/{user_id}/accounts")
async def get_user_accounts(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_read)
):
    """Get SaaS accounts for a specific user"""
    user = db.query(User).filter(User.hr_user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    
    return {
        "user": {
            "id": user.id,
            "hr_user_id": user.hr_user_id,
            "email": user.email,
            "department": user.department,
            "status": user.status
        },
        "accounts": [
            {
                "id": a.id,
                "system": a.system,
                "account_id": a.account_id,
                "status": a.status
            }
            for a in accounts
        ]
    }

@router.get("/users/{user_id}/desired-entitlements")
async def get_user_desired_entitlements(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_read)
):
    """Get desired entitlements for a user based on RBAC rules"""
    user = db.query(User).filter(User.hr_user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    engine = IdentityEngine()
    user_dict = {
        "department": user.department,
        "location": user.location,
        "employment_type": user.employment_type,
        "title": user.title,
        "status": user.status
    }
    
    desired = engine.desired_for_user(user_dict)
    
    return {
        "user": {
            "id": user.id,
            "hr_user_id": user.hr_user_id,
            "email": user.email,
            "department": user.department,
            "status": user.status
        },
        "desired_entitlements": desired
    }

@router.get("/entitlements/summary")
async def get_entitlements_summary(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_read)
):
    """Get summary of all entitlements across users"""
    users = db.query(User).all()
    entitlements = db.query(Entitlement).all()
    accounts = db.query(Account).all()
    
    # Group entitlements by key
    entitlement_counts = {}
    for e in entitlements:
        key = e.entitlement_key
        entitlement_counts[key] = entitlement_counts.get(key, 0) + 1
    
    # Group accounts by system
    account_counts = {}
    for a in accounts:
        system = a.system
        status = a.status
        key = f"{system}_{status}"
        account_counts[key] = account_counts.get(key, 0) + 1
    
    return {
        "total_users": len(users),
        "total_entitlements": len(entitlements),
        "total_accounts": len(accounts),
        "entitlement_breakdown": entitlement_counts,
        "account_breakdown": account_counts,
        "systems": ["google", "github"]
    }

@router.get("/policies")
async def get_rbac_policies(
    current_user: TokenData = Depends(require_read)
):
    """Get current RBAC policies and rules"""
    engine = IdentityEngine()
    
    return {
        "roles": engine.cfg.get("roles", {}),
        "rules": engine.cfg.get("rules", [])
    }

@router.get("/users/{user_id}/access-review")
async def get_user_access_review(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_read)
):
    """Get complete access review for a user including current vs desired"""
    user = db.query(User).filter(User.hr_user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get desired entitlements from identity engine
    engine = IdentityEngine()
    user_dict = {
        "department": user.department,
        "location": user.location,
        "employment_type": user.employment_type,
        "title": user.title,
        "status": user.status
    }
    desired = engine.desired_for_user(user_dict)
    
    # Get current state from provisioners
    google_provisioner = GoogleWSMock()
    github_provisioner = GitHubMock()
    
    current_google = google_provisioner.fetch_current(user.email)
    current_github = github_provisioner.fetch_current(user.email)
    
    current = {
        "google": current_google.get("google", {"groups": []}),
        "github": current_github.get("github", {"teams": []})
    }
    
    # Calculate differences
    changes = plan_changes(desired, current)
    
    return {
        "user": {
            "id": user.id,
            "hr_user_id": user.hr_user_id,
            "email": user.email,
            "department": user.department,
            "status": user.status
        },
        "desired": desired,
        "current": current,
        "changes_needed": changes,
        "compliance_status": "compliant" if not changes else "needs_changes"
    }

# Policy Management Endpoints

@router.post("/policies")
async def update_rbac_policies(
    policy_update: PolicyUpdate,
    current_user: TokenData = Depends(require_write)
):
    """Update RBAC policies and rules"""
    try:
        engine = IdentityEngine()
        
        # Update roles if provided
        if policy_update.roles is not None:
            for dept, role_config in policy_update.roles.items():
                if dept not in engine.cfg.setdefault("roles", {}):
                    engine.cfg["roles"][dept] = {}
                
                if role_config.google:
                    engine.cfg["roles"][dept]["google"] = {
                        "groups": role_config.google.groups or []
                    }
                
                if role_config.github:
                    engine.cfg["roles"][dept]["github"] = {
                        "teams": role_config.github.teams or []
                    }
        
        # Update rules if provided
        if policy_update.rules is not None:
            engine.cfg["rules"] = []
            for rule in policy_update.rules:
                rule_dict = {
                    "when": rule.when,
                    "grant": {}
                }
                
                for system, entitlements in rule.grant.items():
                    rule_dict["grant"][system] = {}
                    if entitlements.groups:
                        rule_dict["grant"][system]["groups"] = entitlements.groups
                    if entitlements.teams:
                        rule_dict["grant"][system]["teams"] = entitlements.teams
                
                engine.cfg["rules"].append(rule_dict)
        
        # Save configuration
        engine.save_config()
        
        return {
            "message": "Policies updated successfully",
            "updated_roles": list(policy_update.roles.keys()) if policy_update.roles else [],
            "updated_rules_count": len(policy_update.rules) if policy_update.rules else 0
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update policies: {str(e)}")

@router.post("/policies/roles/{department}")
async def create_or_update_role(
    department: str,
    role_config: RoleMapping,
    current_user: TokenData = Depends(require_write)
):
    """Create or update a specific department role mapping"""
    try:
        engine = IdentityEngine()
        
        if "roles" not in engine.cfg:
            engine.cfg["roles"] = {}
        
        engine.cfg["roles"][department] = {}
        
        if role_config.google:
            engine.cfg["roles"][department]["google"] = {
                "groups": role_config.google.groups or []
            }
        
        if role_config.github:
            engine.cfg["roles"][department]["github"] = {
                "teams": role_config.github.teams or []
            }
        
        engine.save_config()
        
        return {
            "message": f"Role mapping for {department} updated successfully",
            "department": department,
            "google_groups": role_config.google.groups if role_config.google else [],
            "github_teams": role_config.github.teams if role_config.github else []
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update role: {str(e)}")

@router.delete("/policies/roles/{department}")
async def delete_role(
    department: str,
    current_user: TokenData = Depends(require_write)
):
    """Delete a department role mapping"""
    try:
        engine = IdentityEngine()
        
        if "roles" not in engine.cfg or department not in engine.cfg["roles"]:
            raise HTTPException(status_code=404, detail=f"Role mapping for {department} not found")
        
        del engine.cfg["roles"][department]
        engine.save_config()
        
        return {
            "message": f"Role mapping for {department} deleted successfully",
            "department": department
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete role: {str(e)}")

@router.post("/policies/rules")
async def add_conditional_rule(
    rule: ConditionalRule,
    current_user: TokenData = Depends(require_write)
):
    """Add a new conditional access rule"""
    try:
        engine = IdentityEngine()
        
        if "rules" not in engine.cfg:
            engine.cfg["rules"] = []
        
        rule_dict = {
            "when": rule.when,
            "grant": {}
        }
        
        for system, entitlements in rule.grant.items():
            rule_dict["grant"][system] = {}
            if entitlements.groups:
                rule_dict["grant"][system]["groups"] = entitlements.groups
            if entitlements.teams:
                rule_dict["grant"][system]["teams"] = entitlements.teams
        
        engine.cfg["rules"].append(rule_dict)
        engine.save_config()
        
        return {
            "message": "Conditional rule added successfully",
            "rule": rule_dict,
            "total_rules": len(engine.cfg["rules"])
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add rule: {str(e)}")

@router.delete("/policies/rules/{rule_index}")
async def delete_conditional_rule(
    rule_index: int,
    current_user: TokenData = Depends(require_write)
):
    """Delete a conditional access rule by index"""
    try:
        engine = IdentityEngine()
        
        if "rules" not in engine.cfg or rule_index < 0 or rule_index >= len(engine.cfg["rules"]):
            raise HTTPException(status_code=404, detail=f"Rule at index {rule_index} not found")
        
        deleted_rule = engine.cfg["rules"].pop(rule_index)
        engine.save_config()
        
        return {
            "message": f"Conditional rule at index {rule_index} deleted successfully",
            "deleted_rule": deleted_rule,
            "remaining_rules": len(engine.cfg["rules"])
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete rule: {str(e)}")

@router.post("/policies/preview")
async def preview_policy_impact(
    policy_update: PolicyUpdate,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_read)
):
    """Preview the impact of policy changes on users without applying them"""
    try:
        # Create temporary engine with new policies for testing
        temp_engine = IdentityEngine()
        
        # Apply temporary changes
        if policy_update.roles:
            for dept, role_config in policy_update.roles.items():
                if dept not in temp_engine.cfg.setdefault("roles", {}):
                    temp_engine.cfg["roles"][dept] = {}
                
                if role_config.google:
                    temp_engine.cfg["roles"][dept]["google"] = {
                        "groups": role_config.google.groups or []
                    }
                
                if role_config.github:
                    temp_engine.cfg["roles"][dept]["github"] = {
                        "teams": role_config.github.teams or []
                    }
        
        if policy_update.rules:
            temp_engine.cfg["rules"] = []
            for rule in policy_update.rules:
                rule_dict = {
                    "when": rule.when,
                    "grant": {}
                }
                
                for system, entitlements in rule.grant.items():
                    rule_dict["grant"][system] = {}
                    if entitlements.groups:
                        rule_dict["grant"][system]["groups"] = entitlements.groups
                    if entitlements.teams:
                        rule_dict["grant"][system]["teams"] = entitlements.teams
                
                temp_engine.cfg["rules"].append(rule_dict)
        
        # Test against current users
        users = db.query(User).filter(User.status == "Active").limit(10).all()
        impact_summary = {
            "total_users_tested": len(users),
            "users_affected": 0,
            "changes_by_user": [],
            "entitlement_changes": {"added": 0, "removed": 0}
        }
        
        original_engine = IdentityEngine()  # Original policies
        
        for user in users:
            user_dict = {
                "department": user.department,
                "location": user.location,
                "employment_type": user.employment_type,
                "title": user.title,
                "status": user.status
            }
            
            original_entitlements = original_engine.desired_for_user(user_dict)
            new_entitlements = temp_engine.desired_for_user(user_dict)
            
            if original_entitlements != new_entitlements:
                impact_summary["users_affected"] += 1
                changes = plan_changes(new_entitlements, original_entitlements)
                
                impact_summary["changes_by_user"].append({
                    "user_id": user.hr_user_id,
                    "email": user.email,
                    "department": user.department,
                    "original": original_entitlements,
                    "new": new_entitlements,
                    "changes": changes
                })
        
        return {
            "message": "Policy impact preview completed",
            "impact": impact_summary
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to preview policy impact: {str(e)}")
