from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Lead Platform API"
    app_version: str = "0.10.0"
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173"
    log_level: str = "INFO"
    firebase_project_id: str = ""
    firebase_credentials_path: str = ""
    firebase_service_account_json: str = ""
    turso_database_url: str = ""
    turso_auth_token: str = ""
    turso_timeout_seconds: float = 15.0
    credential_encryption_key: str = ""
    frontend_app_url: str = "http://localhost:5173"
    public_api_url: str = ""
    gmail_oauth_client_id: str = ""
    gmail_oauth_client_secret: str = ""
    gmail_oauth_redirect_uri: str = "http://localhost:8000/api/v1/outreach/gmail/callback"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
