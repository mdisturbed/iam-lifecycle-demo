from ._base import ProvisionerBase

# In-memory state for demo
_STATE: dict[str, dict] = {}

class GoogleWSMock(ProvisionerBase):
    def fetch_current(self, user_email: str) -> dict:
        user = _STATE.get(user_email, {"groups": []})
        return {"google": {"groups": user.get("groups", [])}}

    def apply(self, user_email: str, plan: list[dict]) -> list[dict]:
        user = _STATE.setdefault(user_email, {"groups": []})
        for p in plan:
            if p.get("target") != "google":
                continue
            if p["action"] == "add_group":
                if p["group"] not in user["groups"]:
                    user["groups"].append(p["group"])
            if p["action"] == "remove_group":
                if p["group"] in user["groups"]:
                    user["groups"].remove(p["group"])
        user["groups"].sort()
        return plan
