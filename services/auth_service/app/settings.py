from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    database_url: str = Field(
        default="sqlite+aiosqlite:///./auth.db",

        description="SQLAlchemy-compatible database URL",
    )
    jwt_secret: SecretStr = Field(
        default=SecretStr("supersecretjwt"),
        description="Secret value used to sign JWT tokens.",
    )
    jwt_alg: str = Field(
        default="HS256",
        description="Algorithm used to sign JWT tokens.",
    )
    access_token_expires_min: int = Field(
        default=30,
        ge=1,
        description="Access token lifetime in minutes.",
    )
    refresh_token_expires_min: int = Field(
        default=43200,
        ge=1,
        description="Refresh token lifetime in minutes.",
    )
    log_level: str = Field(default="INFO", description="Log level for the application logger.")
    metrics_enabled: bool = Field(
        default=True,
        description="Expose Prometheus metrics endpoint when enabled.",
    )
    metrics_endpoint: str = Field(
        default="/metrics",
        description="Path where Prometheus metrics are exposed.",
    )
    tracing_enabled: bool = Field(
        default=False,
        description="Enable OpenTelemetry tracing when true.",
    )
    otlp_endpoint: str | None = Field(
        default=None,
        description="OTLP gRPC collector endpoint.",
    )
    otlp_insecure: bool = Field(
        default=False,
        description="Disable TLS certificate verification for OTLP exporter.",
    )
    traces_sample_ratio: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Sampling ratio for tracing (0.0-1.0).",
    )
    sentry_dsn: str | None = Field(
        default=None,
        description="Sentry DSN used for error reporting.",
    )
    sentry_environment: str | None = Field(
        default=None,
        description="Sentry environment tag (e.g. production).",
    )
    sentry_traces_sample_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Sampling ratio for Sentry performance tracing.",
    )
    cors_allow_origins: str = Field(
        default="*",
        description="Comma separated list of allowed CORS origins.",
    )
    cors_allow_methods: str = Field(
        default="*",
        description="Comma separated list of allowed CORS methods.",
    )
    cors_allow_headers: str = Field(
        default="*",
        description="Comma separated list of allowed CORS headers.",
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="Allow credentialed CORS requests.",
    )
    allowed_hosts: str = Field(
        default="*",
        description="Comma separated list of trusted hosts for Starlette's middleware.",
    )
    request_id_header: str = Field(
        default="X-Request-ID",
        description="HTTP header used for propagating request identifiers.",
    )
    trust_request_id_header: bool = Field(
        default=True,
        description="Trust incoming request id header from clients.",
    )
    request_log_headers: str = Field(
        default="x-forwarded-for",
        description="Comma separated list of headers to include in request logs.",
    )
    rate_limit_enabled: bool = Field(
        default=False,
        description="Enable in-memory rate limiting middleware.",
    )
    rate_limit_requests: int = Field(
        default=120,
        ge=1,
        description="Maximum requests per window before throttling.",
    )
    rate_limit_window_seconds: float = Field(
        default=60.0,
        gt=0.0,
        description="Size of the sliding window in seconds.",
    )
    rate_limit_exempt_paths: str = Field(
        default="/health,/metrics",
        description="Comma separated list of paths exempt from rate limiting.",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""

    return Settings()
