"""
Application settings loaded from environment variables via pydantic-settings.

All secrets and connection parameters are centralised here. The `.env` file is
loaded automatically when present. Every downstream module imports the singleton
`settings` object exported from this module.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, List, Tuple, Type

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource


class Settings(BaseSettings):
    """Immutable application-wide configuration."""

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_parse_none_str="null,none,None",
    )

    # ── Application ──────────────────────────────────────────
    APP_NAME: str = "SMART AI IoT Backend"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production"
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: Any = ["http://localhost:3000", "http://localhost:8000"]

    # ── Server ───────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1

    # Database (MySQL XAMPP)
    DATABASE_URL: str = "mysql+aiomysql://root:@localhost:3306/smart_aiot"

    # MQTT / HiveMQ Cloud
    MQTT_BROKER: str = ""
    MQTT_PORT: int = 8883
    MQTT_USERNAME: str = ""
    MQTT_PASSWORD: str = ""
    MQTT_CLIENT_ID: str = "smart-aiot-backend"
    MQTT_KEEPALIVE: int = 60
    MQTT_TLS_ENABLED: bool = True

    # ── Google Gemini AI ─────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-flash-latest"
    GEMINI_MAX_TOKENS: int = 2048
    GEMINI_TEMPERATURE: float = 0.3

    # ── JWT Authentication ───────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Rate Limiting ────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── Logging ──────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # ── Validators ───────────────────────────────────────────
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            if not v or v.strip() == "":
                return []
            v_str = v.strip()
            if v_str.startswith("["):
                import json
                try:
                    res = json.loads(v_str)
                    if isinstance(res, list):
                        return [str(item).strip() for item in res if str(item).strip()]
                except Exception:
                    pass
            return [origin.strip() for origin in v_str.split(",") if origin.strip()]
        elif isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        return []

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        # Skip JSON parsing for List fields in dotenv/env - let validator handle it
        return (init_settings, env_settings, dotenv_settings, file_secret_settings)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()


settings = get_settings()
