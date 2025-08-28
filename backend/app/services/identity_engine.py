import yaml
from pathlib import Path
import os
from datetime import datetime

ENTL_PATH = Path(__file__).resolve().parents[1] / "config" / "entitlements.yaml"

class IdentityEngine:
    def __init__(self):
        self.cfg = yaml.safe_load(ENTL_PATH.read_text())

    def desired_for_user(self, user: dict) -> dict:
        """Return desired entitlements structure per user.
        Example shape:
        {"google": {"groups": ["eng@example.com"]}, "github": {"teams": ["backend"]}}
        """
        desired = {"google": {"groups": []}, "github": {"teams": []}}
        
        # CRITICAL: Terminated users should have NO access
        user_status = (user.get("status") or "").strip()
        if user_status.lower() == "terminated":
            # Return empty entitlements for terminated users
            return desired

        dept = (user.get("department") or "").strip()
        roles = self.cfg.get("roles", {})
        if dept in roles:
            role = roles[dept]
            desired["google"]["groups"] += role.get("google", {}).get("groups", [])
            desired["github"]["teams"] += role.get("github", {}).get("teams", [])

        # simple rule evaluation via eval-safe mapping
        for rule in self.cfg.get("rules", []):
            when = rule.get("when", "")
            ctx = {
                "location": user.get("location"),
                "employment_type": user.get("employment_type"),
                "department": user.get("department"),
                "title": user.get("title"),
                "status": user.get("status"),
            }
            try:
                # Safe rule evaluation - only allow simple comparisons
                if self._safe_eval_rule(when, ctx):
                    grant = rule.get("grant", {})
                    for sys, parts in grant.items():
                        for k, v in parts.items():
                            desired.setdefault(sys, {}).setdefault(k, [])
                            desired[sys][k] += v
            except Exception:
                continue
        # normalize uniques
        for sys in desired:
            for k in desired[sys]:
                desired[sys][k] = sorted(set(desired[sys][k]))
        return desired

    def _safe_eval_rule(self, rule_expr: str, context: dict) -> bool:
        """Safely evaluate rule expressions without using eval().
        Only supports simple equality comparisons for security.
        """
        # Remove whitespace
        rule_expr = rule_expr.strip()
        
        # Support format: field == "value"
        if " == " in rule_expr:
            field, value = rule_expr.split(" == ", 1)
            field = field.strip()
            value = value.strip().strip('"\'')
            return context.get(field) == value
        
        # Support format: field != "value"
        elif " != " in rule_expr:
            field, value = rule_expr.split(" != ", 1)
            field = field.strip()
            value = value.strip().strip('"\'')
            return context.get(field) != value
            
        # Unsupported rule format
        return False
    
    def save_config(self):
        """Save the current configuration back to the YAML file."""
        try:
            # Create backup before saving
            backup_path = ENTL_PATH.with_suffix(f".yaml.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            if ENTL_PATH.exists():
                backup_path.write_text(ENTL_PATH.read_text())
            
            # Write updated configuration
            with open(ENTL_PATH, 'w') as f:
                yaml.safe_dump(self.cfg, f, default_flow_style=False, indent=2)
            
            return True
        except Exception as e:
            raise Exception(f"Failed to save configuration: {str(e)}")
    
    def reload_config(self):
        """Reload configuration from YAML file."""
        try:
            self.cfg = yaml.safe_load(ENTL_PATH.read_text())
            return True
        except Exception as e:
            raise Exception(f"Failed to reload configuration: {str(e)}")
