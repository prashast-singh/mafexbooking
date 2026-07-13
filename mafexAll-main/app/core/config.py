from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "no-reply@example.com"
    SMTP_USE_TLS: bool = True

    # Optional bootstrap admin (created/promoted at API startup).
    BOOTSTRAP_ADMIN_EMAIL: str | None = None
    BOOTSTRAP_ADMIN_NAME: str = "System Admin"

    OTP_EXPIRE_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 5

    API_V1_PREFIX: str = "/api/v1"

    # Comma-separated browser origins for CORS (dev + production frontend URL).
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Local filesystem storage root (contains room_images/, etc.)
    STORAGE_ROOT: Path = Field(default=Path("storage"))

    @property
    def cors_allow_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def room_images_dir(self) -> Path:
        return self.STORAGE_ROOT / "room_images"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
