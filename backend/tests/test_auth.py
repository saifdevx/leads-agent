from fastapi.testclient import TestClient

from app.auth.dependencies import (
    get_current_application_user,
    get_current_user,
)
from app.auth.firebase import FirebaseTokenError
from app.auth.schemas import AuthenticatedUser
from app.main import app

client = TestClient(app)


def test_me_requires_bearer_token():
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Authentication required."


def test_me_returns_verified_identity_with_dependency_override():
    app.dependency_overrides[get_current_application_user] = lambda: AuthenticatedUser(
        uid="firebase-user-123",
        email="user@example.com",
        name="Test User",
        email_verified=True,
        sign_in_provider="password",
    )

    try:
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer test"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "uid": "firebase-user-123",
        "email": "user@example.com",
        "name": "Test User",
        "email_verified": True,
        "sign_in_provider": "password",
    }


def test_me_rejects_invalid_firebase_token(monkeypatch):
    def fail_verification(_: str):
        raise FirebaseTokenError("bad token")

    monkeypatch.setattr(
        "app.auth.dependencies.verify_firebase_token", fail_verification
    )

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer invalid-token"}
    )

    assert response.status_code == 401
    assert "invalid or expired" in response.json()["error"]["message"]


def test_application_user_syncs_to_repository():
    class FakeRepository:
        def __init__(self):
            self.synced = None

        def sync_authenticated_user(self, user):
            self.synced = user

    user = AuthenticatedUser(
        uid="firebase-user-456",
        email="sync@example.com",
        name="Synced User",
        email_verified=True,
        sign_in_provider="google.com",
    )
    repository = FakeRepository()

    result = get_current_application_user(
        current_user=user,
        repository=repository,
    )

    assert result is user
    assert repository.synced is user
