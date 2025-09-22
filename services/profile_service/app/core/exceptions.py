"""Domain-level exceptions and HTTP translation utilities."""

from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from typing import Any


@dataclass(slots=True)
class DomainError(Exception):
    """Base class for domain errors that can be mapped to HTTP responses."""

    message: str
    status_code: int = HTTPStatus.BAD_REQUEST
    payload: dict[str, Any] | None = None


class ProfileNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__("Profile not found", HTTPStatus.NOT_FOUND)


class ProfileAlreadyExistsError(DomainError):
    def __init__(self) -> None:
        super().__init__("Profile already exists", HTTPStatus.CONFLICT)


class PhoneAlreadyInUseError(DomainError):
    def __init__(self) -> None:
        super().__init__("Phone already in use", HTTPStatus.CONFLICT)


class InvalidPhoneError(DomainError):
    def __init__(self) -> None:
        super().__init__("Phone is invalid", HTTPStatus.UNPROCESSABLE_ENTITY)


class RatingNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__("Rating not found", HTTPStatus.NOT_FOUND)
