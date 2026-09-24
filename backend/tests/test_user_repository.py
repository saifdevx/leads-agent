from app.auth.schemas import AuthenticatedUser
from app.db.client import QueryResult
from app.db.user_repository import UserRepository


class FakeDatabase:
    def __init__(self):
        self.calls = []

    def execute(self, sql, params=(), *, want_rows=True):
        self.calls.append((sql, params, want_rows))
        if "RETURNING firebase_uid" in sql:
            return QueryResult(
                [],
                [{
                    "firebase_uid": params[0],
                    "email": params[1],
                    "display_name": params[2],
                    "status": "active",
                    "role": "user",
                }],
                1,
                None,
                1,
                1,
            )
        if "FROM users" in sql and "WHERE firebase_uid" in sql:
            return QueryResult([], [{"firebase_uid": params[0], "status": "active", "role": "user"}], 0, None, 1, 0)
        return QueryResult([], [], 1, None, 0, 1)


def test_user_sync_uses_one_round_trip_upsert_with_returning():
    database = FakeDatabase()
    repository = UserRepository(database)
    user = AuthenticatedUser(
        uid="firebase-123",
        email="user@example.com",
        name="Lead User",
        email_verified=True,
        sign_in_provider="google.com",
    )

    row = repository.sync_authenticated_user(user)

    assert len(database.calls) == 1
    sql, params, want_rows = database.calls[0]
    assert "INSERT INTO users" in sql
    assert "ON CONFLICT(firebase_uid) DO UPDATE" in sql
    assert "RETURNING firebase_uid" in sql
    assert params[0] == "firebase-123"
    assert params[1] == "user@example.com"
    assert params[2] == "Lead User"
    assert params[3] is True
    assert params[4] == "google.com"
    assert want_rows is True
    assert row["firebase_uid"] == "firebase-123"
