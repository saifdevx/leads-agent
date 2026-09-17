from __future__ import annotations

from datetime import datetime, timezone

from app.auth.schemas import AuthenticatedUser
from app.db.client import TursoHttpClient


class UserRepository:
    def __init__(self, database: TursoHttpClient) -> None:
        self.database = database

    def sync_authenticated_user(self, user: AuthenticatedUser) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.database.execute(
            """
            INSERT INTO users (
                firebase_uid,
                email,
                display_name,
                email_verified,
                sign_in_provider,
                status,
                created_at,
                updated_at,
                last_login_at
            ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?)
            ON CONFLICT(firebase_uid) DO UPDATE SET
                email = excluded.email,
                display_name = excluded.display_name,
                email_verified = excluded.email_verified,
                sign_in_provider = excluded.sign_in_provider,
                updated_at = excluded.updated_at,
                last_login_at = excluded.last_login_at
            """,
            (
                user.uid,
                user.email,
                user.name,
                user.email_verified,
                user.sign_in_provider,
                now,
                now,
                now,
            ),
            want_rows=False,
        )

    def get_by_firebase_uid(self, firebase_uid: str) -> dict | None:
        result = self.database.execute(
            """
            SELECT
                firebase_uid,
                email,
                display_name,
                email_verified,
                sign_in_provider,
                status,
                created_at,
                updated_at,
                last_login_at
            FROM users
            WHERE firebase_uid = ?
            LIMIT 1
            """,
            (firebase_uid,),
        )
        return result.rows[0] if result.rows else None
