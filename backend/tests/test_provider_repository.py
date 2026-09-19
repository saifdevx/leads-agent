from cryptography.fernet import Fernet

from app.db.client import QueryResult
from app.providers.repository import ProviderRepository
from app.providers.security import CredentialCipher


class FakeDatabase:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, sql, params=(), *, want_rows=True):
        self.calls.append((sql, params, want_rows))
        return QueryResult([], self.rows, 0, None, len(self.rows), 0)


def test_list_connections_reads_provider_rows_once():
    cipher = CredentialCipher(Fernet.generate_key().decode())
    encrypted = cipher.encrypt({"api_key": "serper-secret", "model": None})
    database = FakeDatabase([
        {
            "provider": "serper",
            "credentials_ciphertext": encrypted,
            "status": "connected",
            "last_validated_at": "2026-09-18T00:00:00+00:00",
            "last_error": None,
        }
    ])
    repository = ProviderRepository(database, cipher)

    rows = repository.list_connections("user-1")

    assert len(database.calls) == 1
    serper = next(row for row in rows if row["provider"] == "serper")
    assert serper["connected"] is True
    assert serper["key_hint"].endswith("cret")


def test_connected_credentials_decrypts_snapshot_after_one_read():
    cipher = CredentialCipher(Fernet.generate_key().decode())
    database = FakeDatabase([
        {
            "provider": "brave",
            "credentials_ciphertext": cipher.encrypt({"api_key": "brave-key", "model": None}),
            "status": "connected",
            "last_validated_at": None,
            "last_error": None,
        },
        {
            "provider": "gemini",
            "credentials_ciphertext": cipher.encrypt({"api_key": "gemini-key", "model": "gemini-3.1-flash-lite"}),
            "status": "connected",
            "last_validated_at": None,
            "last_error": None,
        },
    ])
    repository = ProviderRepository(database, cipher)

    snapshot = repository.connected_credentials("user-1")

    assert len(database.calls) == 1
    assert snapshot["brave"]["api_key"] == "brave-key"
    assert snapshot["gemini"]["model"] == "gemini-3.1-flash-lite"
