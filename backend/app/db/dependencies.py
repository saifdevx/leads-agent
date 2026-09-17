from functools import lru_cache

from app.core.config import get_settings
from app.db.client import DatabaseConfigurationError, TursoHttpClient
from app.db.user_repository import UserRepository


@lru_cache
def get_database_client() -> TursoHttpClient:
    settings = get_settings()
    if not settings.turso_database_url.strip() or not settings.turso_auth_token.strip():
        raise DatabaseConfigurationError("Turso database credentials are not configured.")

    return TursoHttpClient(
        settings.turso_database_url,
        settings.turso_auth_token,
        timeout_seconds=settings.turso_timeout_seconds,
    )


def get_user_repository() -> UserRepository:
    return UserRepository(get_database_client())
