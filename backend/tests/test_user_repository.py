from app.auth.schemas import AuthenticatedUser
from app.db.client import QueryResult
from app.db.user_repository import UserRepository


class FakeDatabase:
    def __init__(self):
        self.calls = []

    def execute(self, sql, params=(), *, want_rows=True):
        self.calls.append((sql, params, want_rows))
        return QueryResult([], [], 1, None, 0, 1)


def test_user_sync_uses_firebase_uid_upsert():
    database = FakeDatabase()
    repository = UserRepository(database)
    user = AuthenticatedUser(
        uid="firebase-123",
        email="user@example.com",
        name="Lead User",
        email_verified=True,
        sign_in_provider="google.com",
    )

    repository.sync_authenticated_user(user)

    assert len(database.calls) == 1
    sql, params, want_rows = database.calls[0]
    assert "INSERT INTO users" in sql
    assert "ON CONFLICT(firebase_uid) DO UPDATE" in sql
    assert params[0] == "firebase-123"
    assert params[1] == "user@example.com"
    assert params[2] == "Lead User"
    assert params[3] is True
    assert params[4] == "google.com"
    assert want_rows is False
