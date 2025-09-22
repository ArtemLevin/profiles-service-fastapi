"""Compatibility shim re-exporting the shared logging configuration."""

from __future__ import annotations

import logging

from services.common.observability.logging import configure_logging as _configure_logging


def configure_logging(level: str) -> logging.Logger:
    """Initialise structured logging for the content API."""

    return _configure_logging("content_api", level)


__all__ = ["configure_logging"]
