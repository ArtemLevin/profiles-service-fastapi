from __future__ import annotations

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Content API service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
    )

    project_name: str = Field(default="Content API", alias="PROJECT_NAME")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")
    metrics_endpoint: str = Field(default="/metrics", alias="METRICS_ENDPOINT")
    tracing_enabled: bool = Field(default=False, alias="TRACING_ENABLED")
    otlp_endpoint: str | None = Field(default=None, alias="OTLP_ENDPOINT")
    otlp_insecure: bool = Field(default=False, alias="OTLP_INSECURE")
    traces_sample_ratio: float = Field(default=1.0, ge=0.0, le=1.0, alias="TRACES_SAMPLE_RATIO")
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")
    sentry_environment: str | None = Field(default=None, alias="SENTRY_ENVIRONMENT")
    sentry_traces_sample_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, alias="SENTRY_TRACES_SAMPLE_RATE"
    )
    cors_allow_origins: str = Field(default="*", alias="CORS_ALLOW_ORIGINS")
    cors_allow_methods: str = Field(default="*", alias="CORS_ALLOW_METHODS")
    cors_allow_headers: str = Field(default="*", alias="CORS_ALLOW_HEADERS")
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")
    allowed_hosts: str = Field(default="*", alias="ALLOWED_HOSTS")
    request_id_header: str = Field(default="X-Request-ID", alias="REQUEST_ID_HEADER")
    trust_request_id_header: bool = Field(default=True, alias="TRUST_REQUEST_ID_HEADER")
    request_log_headers: str = Field(default="x-forwarded-for", alias="REQUEST_LOG_HEADERS")
    rate_limit_enabled: bool = Field(default=False, alias="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=200, ge=1, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: float = Field(
        default=60.0, gt=0.0, alias="RATE_LIMIT_WINDOW_SECONDS"
    )
    rate_limit_exempt_paths: str = Field(
        default="/health,/metrics", alias="RATE_LIMIT_EXEMPT_PATHS"
    )

    redis_host: str = Field(default="redis", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_password: str | None = Field(default=None, alias="REDIS_PASSWORD")
    redis_cache_ttl_seconds: int = Field(default=60, alias="REDIS_CACHE_TTL_SECONDS")
    redis_socket_timeout: float = Field(default=2.0, alias="REDIS_SOCKET_TIMEOUT")
    redis_socket_connect_timeout: float = Field(default=2.0, alias="REDIS_SOCKET_CONNECT_TIMEOUT")
    redis_retry_attempts: int = Field(default=3, alias="REDIS_RETRY_ATTEMPTS")
    redis_retry_backoff_seconds: float = Field(default=0.2, alias="REDIS_RETRY_BACKOFF_SECONDS")

    elastic_host: str = Field(default="elasticsearch", alias="ELASTIC_HOST")
    elastic_port: int = Field(default=9200, alias="ELASTIC_PORT")
    elastic_use_ssl: bool = Field(default=False, alias="ELASTIC_USE_SSL")
    elastic_verify_certs: bool = Field(default=False, alias="ELASTIC_VERIFY_CERTS")
    elastic_username: str | None = Field(default=None, alias="ELASTIC_USERNAME")
    elastic_password: str | None = Field(default=None, alias="ELASTIC_PASSWORD")
    elastic_request_timeout: float = Field(default=5.0, alias="ELASTIC_REQUEST_TIMEOUT")
    elastic_max_retries: int = Field(default=2, alias="ELASTIC_MAX_RETRIES")

    default_page_size: int = Field(default=50, alias="DEFAULT_PAGE_SIZE")
    cache_namespace: str = Field(default="content", alias="CACHE_NAMESPACE")

    film_index: str = Field(default="films", alias="FILM_INDEX")
    genre_index: str = Field(default="genres", alias="GENRE_INDEX")
    person_index: str = Field(default="persons", alias="PERSON_INDEX")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings instance."""

    return Settings()
