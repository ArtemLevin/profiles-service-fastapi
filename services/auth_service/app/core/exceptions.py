from __future__ import annotations

from http import HTTPStatus


class AuthServiceError(Exception):
    """Base exception for domain errors in the auth service."""

    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or HTTPStatus(self.status_code).phrase
        super().__init__(self.detail)


class UserAlreadyExistsError(AuthServiceError):
    status_code = HTTPStatus.CONFLICT

    def __init__(self, detail: str = "Email already registered") -> None:
        super().__init__(detail)


class InvalidCredentialsError(AuthServiceError):
    status_code = HTTPStatus.UNAUTHORIZED

    def __init__(self, detail: str = "Invalid credentials") -> None:
        super().__init__(detail)


class InvalidTokenError(AuthServiceError):
    status_code = HTTPStatus.UNAUTHORIZED

    def __init__(self, detail: str = "Invalid token") -> None:
        super().__init__(detail)


class UserNotFoundError(AuthServiceError):
    status_code = HTTPStatus.NOT_FOUND

    def __init__(self, detail: str = "User not found") -> None:
        super().__init__(detail)
