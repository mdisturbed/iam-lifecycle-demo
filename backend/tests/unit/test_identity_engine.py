from app.services.identity_engine import IdentityEngine

def test_desired_for_user_roles():
    ie = IdentityEngine()
    user = {"department": "Engineering", "location": "US", "employment_type": "FullTime", "title": "SE", "status": "Active"}
    d = ie.desired_for_user(user)
    assert "engineering@example.com" in d["google"]["groups"]
