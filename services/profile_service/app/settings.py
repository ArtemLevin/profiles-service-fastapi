"""Application configuration for the profile service."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings loaded from environment variables or a .env file."""

    database_url: str = "sqlite+aiosqlite:///./dev.db"
    jwt_secret: str = "supersecretjwt"
    jwt_alg: str = "HS256"
    profiles_crypto_key_base64: str = "npKbpZeqEz7YCeTmRnh+W/tVCAq9lavsjDsuT9yyz2o="  # 32 bytes
    phone_hash_pepper: str = "pepper"
    redis_host: str = "redis"
    redis_port: int = 6379
    rate_limit_storage_uri: str | None = None
    rating_cache_ttl_seconds: int = 300
    log_level: str = "INFO"
    metrics_enabled: bool = Field(default=True)
    metrics_endpoint: str = Field(default="/metrics")
    tracing_enabled: bool = Field(default=False)
    otlp_endpoint: str | None = Field(default=None)
    otlp_insecure: bool = Field(default=False)
    traces_sample_ratio: float = Field(default=1.0, ge=0.0, le=1.0)
    sentry_dsn: str | None = Field(default=None)
    sentry_environment: str | None = Field(default=None)
    sentry_traces_sample_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    cors_allow_origins: str = Field(default="*")
    cors_allow_methods: str = Field(default="*")
    cors_allow_headers: str = Field(default="*")
    cors_allow_credentials: bool = Field(default=True)
    allowed_hosts: str = Field(default="*")
    request_id_header: str = Field(default="X-Request-ID")
    trust_request_id_header: bool = Field(default=True)
    request_log_headers: str = Field(default="x-forwarded-for")
    rate_limit_enabled: bool = Field(default=False)
    rate_limit_requests: int = Field(default=120, ge=1)
    rate_limit_window_seconds: float = Field(default=60.0, gt=0.0)
    rate_limit_exempt_paths: str = Field(default="/health,/metrics")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def redis_url(self) -> str:
        """Build a Redis connection string compatible with redis-py."""

        return f"redis://{self.redis_host}:{self.redis_port}/0"

    @property
    def limiter_storage_uri(self) -> str:
        """Storage backend URI used by SlowAPI for rate limiting."""

        return self.rate_limit_storage_uri or self.redis_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached ``Settings`` instance."""

    return Settings()


def reload_settings() -> Settings:
    """Clear the settings cache and return a freshly loaded instance."""

    get_settings.cache_clear()
    settings_obj = get_settings()
    global settings
    settings = settings_obj
    return settings_obj


settings = get_settings()
