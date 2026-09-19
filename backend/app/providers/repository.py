from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.db.client import TursoHttpClient
from app.providers.catalog import PROVIDERS, provider_meta
from app.providers.security import CredentialCipher


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProviderRepository:
    def __init__(self, database: TursoHttpClient, cipher: CredentialCipher):
        self.database = database
        self.cipher = cipher

    def _row(self, user_id: str, provider: str) -> dict | None:
        result = self.database.execute(
            """
            SELECT provider, credentials_ciphertext, status, last_validated_at, last_error
            FROM provider_connections
            WHERE user_id = ? AND provider = ?
            """,
            (user_id, provider),
        )
        return result.rows[0] if result.rows else None

    def _rows_by_provider(self, user_id: str) -> dict[str, dict]:
        """Load all provider connection rows with one remote database request."""
        result = self.database.execute(
            """
            SELECT provider, credentials_ciphertext, status, last_validated_at, last_error
            FROM provider_connections
            WHERE user_id = ?
            """,
            (user_id,),
        )
        return {str(row["provider"]): row for row in result.rows}

    def get_credentials(self, user_id: str, provider: str) -> dict | None:
        row = self._row(user_id, provider)
        if not row or row.get("status") != "connected" or not row.get("credentials_ciphertext"):
            return None
        return self.cipher.decrypt(row["credentials_ciphertext"])

    def connected_providers(self, user_id: str) -> set[str]:
        """Return connected provider names using a single Turso query."""
        rows = self._rows_by_provider(user_id)
        return {
            provider
            for provider, row in rows.items()
            if row.get("status") == "connected" and row.get("credentials_ciphertext")
        }

    def connected_credentials(self, user_id: str) -> dict[str, dict]:
        """Decrypt all connected provider credentials after one Turso read.

        Discovery jobs use a stable credential snapshot for the duration of a run. This
        avoids a remote database lookup for every search query/page.
        """
        rows = self._rows_by_provider(user_id)
        credentials: dict[str, dict] = {}
        for provider, row in rows.items():
            if row.get("status") != "connected" or not row.get("credentials_ciphertext"):
                continue
            try:
                credentials[provider] = self.cipher.decrypt(row["credentials_ciphertext"])
            except Exception:
                continue
        return credentials

    def is_connected(self, user_id: str, provider: str) -> bool:
        row = self._row(user_id, provider)
        return bool(row and row.get("status") == "connected" and row.get("credentials_ciphertext"))

    def save(self, user_id: str, provider: str, *, api_key: str, model: str | None = None) -> dict:
        meta = provider_meta(provider)
        now = _now()
        payload = {
            "api_key": api_key.strip(),
            "model": (model or meta.get("default_model") or "").strip() or None,
        }
        ciphertext = self.cipher.encrypt(payload)
        existing = self._row(user_id, provider)
        if existing:
            self.database.execute(
                """
                UPDATE provider_connections
                SET credentials_ciphertext = ?, status = 'connected', last_validated_at = ?,
                    last_error = NULL, updated_at = ?
                WHERE user_id = ? AND provider = ?
                """,
                (ciphertext, now, now, user_id, provider),
                want_rows=False,
            )
        else:
            self.database.execute(
                """
                INSERT INTO provider_connections (
                    id, user_id, provider, credentials_ciphertext, status,
                    last_validated_at, last_error, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'connected', ?, NULL, ?, ?)
                """,
                (str(uuid4()), user_id, provider, ciphertext, now, now, now),
                want_rows=False,
            )
        return self.describe(user_id, provider)

    def mark_error(self, user_id: str, provider: str, message: str) -> None:
        self.database.execute(
            """
            UPDATE provider_connections
            SET status = 'error', last_error = ?, updated_at = ?
            WHERE user_id = ? AND provider = ?
            """,
            (message[:500], _now(), user_id, provider),
            want_rows=False,
        )

    def delete(self, user_id: str, provider: str) -> None:
        self.database.execute(
            "DELETE FROM provider_connections WHERE user_id = ? AND provider = ?",
            (user_id, provider),
            want_rows=False,
        )

    def _describe_row(self, provider: str, row: dict | None) -> dict:
        meta = provider_meta(provider)
        credentials = None
        if row and row.get("credentials_ciphertext"):
            try:
                credentials = self.cipher.decrypt(row["credentials_ciphertext"])
            except Exception:
                credentials = None
        api_key = (credentials or {}).get("api_key") or ""
        model = (credentials or {}).get("model") or meta.get("default_model")
        connected = bool(row and row.get("status") == "connected" and api_key)
        return {
            "provider": provider,
            "category": meta["category"],
            "label": meta["label"],
            "description": meta["description"],
            "status": row.get("status") if row else "disconnected",
            "connected": connected,
            "model": model,
            "key_hint": f"••••{api_key[-4:]}" if api_key else None,
            "last_validated_at": row.get("last_validated_at") if row else None,
            "last_error": row.get("last_error") if row else None,
        }

    def describe(self, user_id: str, provider: str) -> dict:
        return self._describe_row(provider, self._row(user_id, provider))

    def list_connections(self, user_id: str) -> list[dict]:
        rows = self._rows_by_provider(user_id)
        return [self._describe_row(provider, rows.get(provider)) for provider in PROVIDERS]
