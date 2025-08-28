from ._base import ProvisionerBase

# In-memory state for demo
_STATE: dict[str, dict] = {}

class GitHubMock(ProvisionerBase):
    def fetch_current(self, user_email: str) -> dict:
        user = _STATE.get(user_email, {"teams": []})
        return {"github": {"teams": user.get("teams", [])}}

    def apply(self, user_email: str, plan: list[dict]) -> list[dict]:
        user = _STATE.setdefault(user_email, {"teams": []})
        for p in plan:
            if p.get("target") != "github":
                continue
            if p["action"] == "add_team":
                if p["team"] not in user["teams"]:
                    user["teams"].append(p["team"])
            if p["action"] == "remove_team":
                if p["team"] in user["teams"]:
                    user["teams"].remove(p["team"])
        user["teams"].sort()
        return plan
