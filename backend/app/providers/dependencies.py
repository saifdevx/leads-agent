from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.db.dependencies import get_database_client
from app.providers.repository import ProviderRepository
from app.providers.security import CredentialCipher


@lru_cache
def get_credential_cipher() -> CredentialCipher:
    return CredentialCipher(get_settings().credential_encryption_key)


def get_provider_repository() -> ProviderRepository:
    return ProviderRepository(get_database_client(), get_credential_cipher())
