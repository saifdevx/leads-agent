from fastapi import HTTPException

from app.admin.dependencies import require_admin
from app.auth.schemas import AuthenticatedUser


class FakeRepository:
    def __init__(self, role="user", status="active"):
        self.role = role
        self.status = status

    def get_by_firebase_uid(self, uid):
        return {"firebase_uid": uid, "role": self.role, "status": self.status}


def user(email="user@example.com", role="user"):
    return AuthenticatedUser(uid="uid-1", email=email, name="User", email_verified=True, sign_in_provider="password", role=role, status="active")


def test_require_admin_accepts_database_admin(monkeypatch):
    class Settings:
        admin_email_list = set()
    monkeypatch.setattr("app.admin.dependencies.get_settings", lambda: Settings())

    result = require_admin(current_user=user(), repository=FakeRepository(role="admin"))

    assert result.role == "admin"


def test_require_admin_rejects_regular_user(monkeypatch):
    class Settings:
        admin_email_list = set()
    monkeypatch.setattr("app.admin.dependencies.get_settings", lambda: Settings())

    try:
        require_admin(current_user=user(), repository=FakeRepository())
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("Expected 403")
