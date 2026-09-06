"""
ThermalTrace backend configuration.
Loads settings from environment variables via pydantic-settings.
"""
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str
    database_url_session: str | None = None
    testing: bool = False

    @property
    def get_database_url(self) -> str:
        """
        Return the preferred database URL for application runtime.

        Uses the transaction pooler (port 6543) by default. The application handles
        PgBouncer transaction-pool mode by disabling statement caching in asyncpg.
        (The session pooler/direct connection is only needed for Alembic migrations).
        """
        return self.database_url

    # CORS
    frontend_origin: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        """
        Return list of allowed CORS origins, supporting comma-separated strings.
        In production, requires FRONTEND_ORIGIN to be set explicitly.
        """
        if not self.is_development and self.frontend_origin == "http://localhost:5173":
            import logging
            logging.getLogger("uvicorn.error").warning(
                "FRONTEND_ORIGIN is using localhost fallback in production mode. Set FRONTEND_ORIGIN in environment."
            )
        origins = [o.strip() for o in self.frontend_origin.split(",") if o.strip()]
        return origins or ["http://localhost:5173"]

    # Environment
    environment: str = "development"

    # Supabase JWT Secret
    supabase_jwt_secret: str = ""


    # NASA FIRMS API key — keep backend-only, never expose to frontend
    firms_map_key: str = ""

    # Number of past days to include in each FIRMS ingestion request.
    # NASA FIRMS Area API supports 1–10 days per request.
    # Configurable via FIRMS_INGESTION_DAYS in .env.
    firms_ingestion_days: int = 5

    # Comma-separated list of FIRMS source identifiers to ingest in multi-source mode.
    # Configurable via FIRMS_SOURCES in .env.
    # Defaults to all three operational VIIRS NRT satellites:
    #   VIIRS_SNPP_NRT   (Suomi NPP, ~375 m resolution)
    #   VIIRS_NOAA20_NRT (NOAA-20, ~375 m resolution)
    #   VIIRS_NOAA21_NRT (NOAA-21, ~375 m resolution)
    firms_sources: str = "VIIRS_SNPP_NRT,VIIRS_NOAA20_NRT,VIIRS_NOAA21_NRT"
    firms_sync_interval_hours: int = 6
    firms_stale_threshold_hours: int = 12

    # Redis Infrastructure Configuration
    redis_url: str = "redis://localhost:6379/0"
    ai_user_quota_per_hour: int = 100
    ai_guest_quota_per_hour: int = 10
    analytics_cache_ttl_seconds: int = 300
    rate_limit_general_per_minute: int = 60
    rate_limit_expensive_per_minute: int = 15

    @property
    def firms_source_list(self) -> list[str]:
        """Return the list of configured FIRMS sources (trimmed, non-empty)."""
        return [s.strip() for s in self.firms_sources.split(",") if s.strip()]

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    # LLM Settings (Backend Only)
    llm_provider: str = "openrouter"
    llm_model: str = "google/gemini-2.5-flash"
    gemini_api_key: str = ""
    openrouter_api_key: str = ""

    @model_validator(mode="after")
    def validate_production_environment(self) -> "Settings":
        """In production mode, require FRONTEND_ORIGIN and REDIS_URL from environment."""
        if not self.is_development and not self.testing:
            if self.frontend_origin == "http://localhost:5173":
                raise ValueError("FRONTEND_ORIGIN environment variable is required in production mode.")
            if self.redis_url == "redis://localhost:6379/0":
                raise ValueError("REDIS_URL environment variable is required in production mode.")
        return self



settings = Settings()  # type: ignore[call-arg]
