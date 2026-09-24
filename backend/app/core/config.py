from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Lead Gen API"
    app_version: str = "1.0.0"
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
    admin_emails: str = ""
    background_jobs_mode: str = "inline"
    worker_poll_seconds: float = 3.0
    worker_lease_seconds: int = 300
    user_access_cache_seconds: int = 60
    embedded_workers: bool = False
    quick_send_per_minute: int = 6

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def admin_email_list(self) -> set[str]:
        return {email.strip().lower() for email in self.admin_emails.split(",") if email.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
