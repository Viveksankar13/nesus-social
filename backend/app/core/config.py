"""
Application Configuration
==========================
All settings are loaded from environment variables.
The app fails fast with a clear message if required vars are missing.
Uses pydantic-settings for type-safe, validated configuration.
"""

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, EmailStr, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings — all values come from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────
    ENVIRONMENT: Literal["development", "test", "production"] = "development"

    # ── Database ─────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        ...,
        description="PostgreSQL connection URL (postgresql+asyncpg://...)",
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_database_url(cls, v: str) -> str:
        """
        Render provides postgres:// URLs; SQLAlchemy 2 requires postgresql+asyncpg://.
        This validator silently converts the scheme so deployment just works.
        """
        if v.startswith("postgres://"):
            v = "postgresql+asyncpg://" + v[len("postgres://"):]
        if v.startswith("postgresql://") and "+asyncpg" not in v:
            v = "postgresql+asyncpg://" + v[len("postgresql://"):]
        return v

    # ── JWT ──────────────────────────────────────────────────────────
    JWT_SECRET: str = Field(..., min_length=32, description="Secret for signing JWTs (min 32 chars)")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 15
    REFRESH_TOKEN_DAYS: int = 7

    # ── CORS / Frontend ──────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse comma-separated ALLOWED_ORIGINS into a list."""
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    # ── SMTP ─────────────────────────────────────────────────────────
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: EmailStr = "noreply@nexussocial.dev"  # type: ignore[assignment]
    SMTP_FROM_NAME: str = "Nexus Social"
    SMTP_USE_TLS: bool = False

    # ── Gemini AI ────────────────────────────────────────────────────
    GEMINI_API_KEY: str = Field(..., description="Google Gemini API key")
    GEMINI_MODEL: str = "gemini-2.5-flash"
    AI_DAILY_QUOTA: int = 100
    MODERATION_FAIL_MODE: Literal["open", "closed"] = "open"

    # ── Admin Seed ───────────────────────────────────────────────────
    ADMIN_EMAIL: EmailStr = Field(..., description="Seed admin email")  # type: ignore[assignment]
    ADMIN_USERNAME: str = Field(..., min_length=3, description="Seed admin username")
    ADMIN_PASSWORD: str = Field(..., min_length=8, description="Seed admin password")

    # ── Rate Limits ──────────────────────────────────────────────────
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_REGISTER: str = "3/minute"
    RATE_LIMIT_FORGOT_PASSWORD: str = "3/minute"
    RATE_LIMIT_RESEND_VERIFICATION: str = "3/minute"
    RATE_LIMIT_AI: str = "20/minute"

    # ── Optional Observability ───────────────────────────────────────
    SENTRY_DSN: str = ""

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Extra validation for production environment."""
        if self.ENVIRONMENT == "production":
            if self.JWT_SECRET == "CHANGE_ME_USE_OPENSSL_RAND_HEX_32":
                raise ValueError("JWT_SECRET must be changed from the default in production")
            if self.ADMIN_PASSWORD in ("CHANGE_ME_STRONG_PASSWORD", "password", "admin"):
                raise ValueError("ADMIN_PASSWORD must be a strong password in production")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance. Call this everywhere."""
    return Settings()  # type: ignore[call-arg]


# Module-level singleton for convenience
settings: Settings = get_settings()
