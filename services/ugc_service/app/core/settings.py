"""Pydantic settings for the UGC service."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ClickHouseSettings(BaseModel):
    host: str = "clickhouse"
    port: int = 8123
    user: str = "default"
    password: str = ""
    database: str = "default"
    secure: bool = False
    connect_timeout: float = 2.0
    read_timeout: float = 5.0
    write_timeout: float = 5.0
    pool_timeout: float = 5.0
    max_connections: int = 50
    max_keepalive_connections: int = 20


class Settings(BaseSettings):
    """Application configuration loaded from the environment or ``.env``."""

    service_name: str = "UGC Service"
    docs_url: str = "/api/ugc/openapi"
    openapi_url: str = "/api/ugc/openapi.json"
    api_prefix: str = "/api/ugc"
    health_path: str = "/health"
    log_level: str = "INFO"
    ensure_schema: bool = True
    default_list_limit: int = 50
    max_list_limit: int = 500
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
    rate_limit_requests: int = Field(default=200, ge=1)
    rate_limit_window_seconds: float = Field(default=60.0, gt=0.0)
    rate_limit_exempt_paths: str = Field(default="/health,/metrics")
    clickhouse: ClickHouseSettings = Field(default_factory=ClickHouseSettings)

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        env_prefix="UGC_",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached :class:`Settings` instance."""

    return Settings()


def reload_settings() -> Settings:
    """Clear the cache and reload configuration (useful for tests)."""

    get_settings.cache_clear()
    settings_obj = get_settings()
    global settings
    settings = settings_obj
    return settings_obj


settings = get_settings()
