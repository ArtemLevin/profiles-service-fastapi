from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseModel):
    """General application behaviour and observability settings."""

    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("APP__LOG_LEVEL", "LOG_LEVEL"),
    )
    metrics_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("APP__METRICS_ENABLED", "METRICS_ENABLED"),
    )
    metrics_endpoint: str = Field(
        default="/metrics",
        validation_alias=AliasChoices("APP__METRICS_ENDPOINT", "METRICS_ENDPOINT"),
    )
    tracing_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("APP__TRACING_ENABLED", "TRACING_ENABLED"),
    )
    otlp_endpoint: str | None = Field(
        default=None,
        validation_alias=AliasChoices("APP__OTLP_ENDPOINT", "OTLP_ENDPOINT"),
    )
    otlp_insecure: bool = Field(
        default=False,
        validation_alias=AliasChoices("APP__OTLP_INSECURE", "OTLP_INSECURE"),
    )
    traces_sample_ratio: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices("APP__TRACES_SAMPLE_RATIO", "TRACES_SAMPLE_RATIO"),
    )
    sentry_dsn: str | None = Field(
        default=None,
        validation_alias=AliasChoices("APP__SENTRY_DSN", "SENTRY_DSN"),
    )
    sentry_environment: str | None = Field(
        default=None,
        validation_alias=AliasChoices("APP__SENTRY_ENVIRONMENT", "SENTRY_ENVIRONMENT"),
    )
    sentry_traces_sample_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "APP__SENTRY_TRACES_SAMPLE_RATE",
            "SENTRY_TRACES_SAMPLE_RATE",
        ),
    )
    cors_allow_origins: str = Field(
        default="*",
        validation_alias=AliasChoices("APP__CORS_ALLOW_ORIGINS", "CORS_ALLOW_ORIGINS"),
    )
    cors_allow_methods: str = Field(
        default="*",
        validation_alias=AliasChoices("APP__CORS_ALLOW_METHODS", "CORS_ALLOW_METHODS"),
    )
    cors_allow_headers: str = Field(
        default="*",
        validation_alias=AliasChoices("APP__CORS_ALLOW_HEADERS", "CORS_ALLOW_HEADERS"),
    )
    cors_allow_credentials: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "APP__CORS_ALLOW_CREDENTIALS",
            "CORS_ALLOW_CREDENTIALS",
        ),
    )
    allowed_hosts: str = Field(
        default="*",
        validation_alias=AliasChoices("APP__ALLOWED_HOSTS", "ALLOWED_HOSTS"),
    )
    request_id_header: str = Field(
        default="X-Request-ID",
        validation_alias=AliasChoices("APP__REQUEST_ID_HEADER", "REQUEST_ID_HEADER"),
    )
    trust_request_id_header: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "APP__TRUST_REQUEST_ID_HEADER",
            "TRUST_REQUEST_ID_HEADER",
        ),
    )
    request_log_headers: str = Field(
        default="x-forwarded-for",
        validation_alias=AliasChoices(
            "APP__REQUEST_LOG_HEADERS",
            "REQUEST_LOG_HEADERS",
        ),
    )


class DatabaseSettings(BaseModel):
    """Database connection parameters."""

    url: str = Field(
        default="sqlite+aiosqlite:///./auth.db",
        validation_alias=AliasChoices("DATABASE__URL", "DATABASE_URL"),
    )
    echo: bool = Field(
        default=False,
        validation_alias=AliasChoices("DATABASE__ECHO", "DATABASE_ECHO"),
    )


class SecuritySettings(BaseModel):
    """JWT signing configuration."""

    jwt_secret: SecretStr = Field(
        default=SecretStr("supersecretjwt"),
        validation_alias=AliasChoices("SECURITY__JWT_SECRET", "JWT_SECRET"),
    )
    jwt_alg: str = Field(
        default="HS256",
        validation_alias=AliasChoices("SECURITY__JWT_ALG", "JWT_ALG"),
    )


class TokenSettings(BaseModel):
    """Access and refresh token lifetimes."""

    access_token_expires_min: int = Field(
        default=30,
        ge=1,
        validation_alias=AliasChoices(
            "TOKENS__ACCESS_TOKEN_EXPIRES_MIN",
            "ACCESS_TOKEN_EXPIRES_MIN",
        ),
    )
    refresh_token_expires_min: int = Field(
        default=43200,
        ge=1,
        validation_alias=AliasChoices(
            "TOKENS__REFRESH_TOKEN_EXPIRES_MIN",
            "REFRESH_TOKEN_EXPIRES_MIN",
        ),
    )


class RateLimitSettings(BaseModel):
    """Sliding window rate limiter configuration."""

    enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("RATE_LIMIT__ENABLED", "RATE_LIMIT_ENABLED"),
    )
    requests: int = Field(
        default=120,
        ge=1,
        validation_alias=AliasChoices("RATE_LIMIT__REQUESTS", "RATE_LIMIT_REQUESTS"),
    )
    window_seconds: float = Field(
        default=60.0,
        gt=0.0,
        validation_alias=AliasChoices(
            "RATE_LIMIT__WINDOW_SECONDS",
            "RATE_LIMIT_WINDOW_SECONDS",
        ),
    )
    exempt_paths: str = Field(
        default="/health,/metrics",
        validation_alias=AliasChoices(
            "RATE_LIMIT__EXEMPT_PATHS",
            "RATE_LIMIT_EXEMPT_PATHS",
        ),
    )




class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    tokens: TokenSettings = Field(default_factory=TokenSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",

        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""

    return Settings()
