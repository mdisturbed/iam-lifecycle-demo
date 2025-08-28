from typing import Dict, List

Change = Dict[str, str]

def plan_changes(desired: dict, current: dict) -> List[Change]:
    """Compare desired vs current membership to produce add/remove actions."""
    actions: List[Change] = []

    # Google groups
    d_groups = set(desired.get("google", {}).get("groups", []))
    c_groups = set(current.get("google", {}).get("groups", []))
    for g in sorted(d_groups - c_groups):
        actions.append({"target": "google", "action": "add_group", "group": g})
    for g in sorted(c_groups - d_groups):
        actions.append({"target": "google", "action": "remove_group", "group": g})

    # GitHub teams
    d_teams = set(desired.get("github", {}).get("teams", []))
    c_teams = set(current.get("github", {}).get("teams", []))
    for t in sorted(d_teams - c_teams):
        actions.append({"target": "github", "action": "add_team", "team": t})
    for t in sorted(c_teams - d_teams):
        actions.append({"target": "github", "action": "remove_team", "team": t})

    return actions
