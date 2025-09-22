"""Application configuration for the profile service."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

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
    """Database connection tuning."""

    url: str = Field(
        default="sqlite+aiosqlite:///./dev.db",
        validation_alias=AliasChoices(
            "DATABASE__URL",
            "DATABASE_URL",
            "DATABASE_URL_PROFILES",
        ),
    )
    echo: bool = Field(
        default=False,
        validation_alias=AliasChoices("DATABASE__ECHO", "DATABASE_ECHO"),
    )


class RedisSettings(BaseModel):
    """Redis cache configuration."""

    host: str = Field(
        default="redis",
        validation_alias=AliasChoices("REDIS__HOST", "REDIS_HOST"),
    )
    port: int = Field(
        default=6379,
        validation_alias=AliasChoices("REDIS__PORT", "REDIS_PORT"),
    )
    db: int = Field(
        default=0,
        validation_alias=AliasChoices("REDIS__DB", "REDIS_DB"),
    )
    password: str | None = Field(
        default=None,
        validation_alias=AliasChoices("REDIS__PASSWORD", "REDIS_PASSWORD"),
    )

    @property
    def dsn(self) -> str:
        """Return a redis-py compatible DSN."""

        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class SecuritySettings(BaseModel):
    """Secrets and crypto configuration."""

    jwt_secret: SecretStr = Field(
        default=SecretStr("supersecretjwt"),
        validation_alias=AliasChoices("SECURITY__JWT_SECRET", "JWT_SECRET"),
    )
    jwt_alg: str = Field(
        default="HS256",
        validation_alias=AliasChoices("SECURITY__JWT_ALG", "JWT_ALG"),
    )
    profiles_crypto_key_base64: str = Field(
        default="npKbpZeqEz7YCeTmRnh+W/tVCAq9lavsjDsuT9yyz2o=",
        validation_alias=AliasChoices(
            "SECURITY__PROFILES_CRYPTO_KEY_BASE64",
            "PROFILES_CRYPTO_KEY_BASE64",
        ),
    )
    phone_hash_pepper: str = Field(
        default="pepper",
        validation_alias=AliasChoices(
            "SECURITY__PHONE_HASH_PEPPER",
            "PHONE_HASH_PEPPER",
        ),
    )


class RateLimitSettings(BaseModel):
    """Rate limiting knobs for the API."""

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
    storage_uri: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "RATE_LIMIT__STORAGE_URI",
            "RATE_LIMIT_STORAGE_URI",
        ),
    )


class CacheSettings(BaseModel):
    """Caching controls for derived aggregates."""

    rating_ttl_seconds: int = Field(
        default=300,
        validation_alias=AliasChoices(
            "CACHE__RATING_TTL_SECONDS",
            "RATING_CACHE_TTL_SECONDS",
        ),
    )


class Settings(BaseSettings):
    """Typed settings loaded from environment variables or a .env file."""

    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)


    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def redis_url(self) -> str:
        """Backward compatible access to the Redis DSN."""

        return self.redis.dsn

    @property
    def limiter_storage_uri(self) -> str:
        """Return the rate limiter backend URI with Redis as fallback."""

        return self.rate_limit.storage_uri or self.redis.dsn


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
