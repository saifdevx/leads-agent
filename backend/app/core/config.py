from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Lead Platform API"
    app_version: str = "0.2.0"
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173"
    log_level: str = "INFO"
    firebase_project_id: str = ""
    firebase_credentials_path: str = ""
    firebase_service_account_json: str = ""

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
