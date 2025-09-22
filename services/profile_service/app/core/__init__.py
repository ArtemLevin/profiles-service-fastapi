"""Core utilities for the profile service."""

from .exceptions import (
    DomainError,
    InvalidPhoneError,
    PhoneAlreadyInUseError,
    ProfileAlreadyExistsError,
    ProfileNotFoundError,
    RatingNotFoundError,
)
from .logging import configure_logging

__all__ = [
    "DomainError",
    "InvalidPhoneError",
    "PhoneAlreadyInUseError",
    "ProfileAlreadyExistsError",
    "ProfileNotFoundError",
    "RatingNotFoundError",
    "configure_logging",
]
