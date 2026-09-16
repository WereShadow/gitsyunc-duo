from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "GitSync Duo"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./gitsync.db"

    # Security
    SECRET_KEY: str = "gitsync-super-secret-jwt-key-for-development-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # Fernet key for encrypting GitHub tokens
    FERNET_KEY: str = "k1acIVME5nBrPTNFC3xTOX0qnlq4B0Muv4jQFLlfFis="

    # GitHub OAuth & Webhooks
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_WEBHOOK_SECRET: str = "gitsync_webhook_secret_dev_2026"

    # Duo Defaults
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"
    DEFAULT_DEADLINE: str = "23:59"
    DEFAULT_GRACE_PERIOD_MINUTES: int = 30

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        return []

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
