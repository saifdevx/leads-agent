from __future__ import annotations

import json

from cryptography.fernet import Fernet, InvalidToken


class CredentialEncryptionError(RuntimeError):
    pass


class CredentialCipher:
    def __init__(self, key: str):
        clean = key.strip()
        if not clean:
            raise CredentialEncryptionError("CREDENTIAL_ENCRYPTION_KEY is not configured.")
        try:
            self._fernet = Fernet(clean.encode("utf-8"))
        except (ValueError, TypeError) as exc:
            raise CredentialEncryptionError(
                "CREDENTIAL_ENCRYPTION_KEY must be a valid Fernet key."
            ) from exc

    def encrypt(self, payload: dict) -> str:
        data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return self._fernet.encrypt(data).decode("utf-8")

    def decrypt(self, ciphertext: str) -> dict:
        try:
            raw = self._fernet.decrypt(ciphertext.encode("utf-8"))
            data = json.loads(raw.decode("utf-8"))
        except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
            raise CredentialEncryptionError("Stored provider credentials could not be decrypted.") from exc
        if not isinstance(data, dict):
            raise CredentialEncryptionError("Stored provider credentials are invalid.")
        return data
