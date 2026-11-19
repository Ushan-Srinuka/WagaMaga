"""Typed, provider-independent configuration shared by the API and worker."""

from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from email_validator import EmailNotValidError, validate_email
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: Literal["development", "test", "production"] = "development"
    database_url: SecretStr | None = None
    migration_database_url: SecretStr | None = None
    test_database_url: SecretStr | None = None
    test_migration_database_url: SecretStr | None = None
    app_db_user: str = Field(default="wagamaga_app", pattern=r"^[a-z_][a-z0-9_]{0,62}$")
    cors_allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    document_storage_path: Path = PROJECT_ROOT / ".data" / "documents"
    auth_signing_key: SecretStr | None = None
    auth_issuer: str = "wagamaga-api"
    auth_audience: str = "wagamaga-web"
    auth_access_minutes: int = Field(default=15, ge=1, le=60)
    auth_session_days: int = Field(default=7, ge=1, le=30)
    auth_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        ]
    )
    auth_login_failures: int = Field(default=5, ge=1, le=100)
    auth_login_ip_attempts: int = Field(default=50, ge=1, le=1000)
    auth_registration_attempts: int = Field(default=5, ge=1, le=100)
    auth_refresh_attempts: int = Field(default=30, ge=1, le=1000)
    support_contact_email: str | None = None

    @field_validator("support_contact_email", mode="before")
    @classmethod
    def public_support_email(cls, value):
        if value is None or isinstance(value, str) and not value.strip():
            return None
        if not isinstance(value, str):
            raise ValueError("SUPPORT_CONTACT_EMAIL must be a valid public support email")
        try:
            return validate_email(value.strip(), check_deliverability=False).normalized
        except EmailNotValidError, TypeError:
            raise ValueError("SUPPORT_CONTACT_EMAIL must be a valid public support email") from None

    @field_validator("auth_signing_key")
    @classmethod
    def long_signing_key(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and len(value.get_secret_value().encode()) < 32:
            raise ValueError("AUTH_SIGNING_KEY must contain at least 32 bytes")
        return value

    @field_validator("document_storage_path")
    @classmethod
    def root_relative_storage(cls, value: Path) -> Path:
        return value if value.is_absolute() else (PROJECT_ROOT / value).resolve()

    @field_validator(
        "database_url", "migration_database_url", "test_database_url", "test_migration_database_url"
    )
    @classmethod
    def postgres_only(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None:
            try:
                driver = make_url(value.get_secret_value()).drivername
            except Exception:
                raise ValueError("A PostgreSQL Psycopg connection URL is required") from None
            if driver != "postgresql+psycopg":
                raise ValueError("Use postgresql+psycopg; other database engines are not supported")
        return value

    @field_validator("cors_allowed_origins", "auth_allowed_origins")
    @classmethod
    def explicit_origins(cls, origins: list[str]) -> list[str]:
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or "*" in origin
                or parsed.username
                or parsed.password
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(
                    "CORS origins must be explicit HTTP(S) origins without credentials"
                )
        return [origin.rstrip("/") for origin in origins]
