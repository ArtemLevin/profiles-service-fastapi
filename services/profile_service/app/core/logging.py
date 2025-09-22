"""Compatibility shim exposing shared logging configuration."""

from __future__ import annotations

import logging

from services.common.observability.logging import configure_logging as _configure_logging


def configure_logging(level: str) -> logging.Logger:
    """Initialise structured logging for the profile service."""

    return _configure_logging("profile_service", level)


__all__ = ["configure_logging"]
