"""Backward-compatible configuration accessors."""

from __future__ import annotations

from .settings import Settings, get_settings

__all__ = [
    "Settings",
    "get_settings",
    "PROJECT_NAME",
    "REDIS_HOST",
    "REDIS_PORT",
    "ELASTIC_HOST",
    "ELASTIC_PORT",
]

_settings = get_settings()

PROJECT_NAME = _settings.project_name
REDIS_HOST = _settings.redis_host
REDIS_PORT = _settings.redis_port
ELASTIC_HOST = _settings.elastic_host
ELASTIC_PORT = _settings.elastic_port
