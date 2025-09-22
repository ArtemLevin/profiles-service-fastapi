from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exceptions import (
    AuthServiceError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from ..models import User
from ..repositories.user_repository import UserRepository
from ..schemas import TokenPair
from ..security import PasswordHasher, TokenService


class AuthService:
    """Business logic for authentication and user management."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
        access_ttl_minutes: int,
        refresh_ttl_minutes: int,
        logger: logging.Logger | None = None,
    ) -> None:
        self._session = session
        self._users = user_repository
        self._passwords = password_hasher
        self._tokens = token_service
        self._access_ttl = access_ttl_minutes
        self._refresh_ttl = refresh_ttl_minutes
        self._logger = logger or logging.getLogger("auth_service.auth")

    async def register_user(self, *, email: str, password: str) -> User:
        existing = await self._users.find_by_email(email)
        if existing is not None:
            raise UserAlreadyExistsError()

        user = User(
            email=email,
            password_hash=self._passwords.hash(password),
            is_active=True,
        )
        await self._users.add(user)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise UserAlreadyExistsError() from exc
        await self._session.refresh(user)
        self._logger.info("Registered new user", extra={"user_id": user.id, "email": email})
        return user

    async def login(self, *, email: str, password: str) -> TokenPair:
        user = await self._users.find_by_email(email)
        if user is None or not user.is_active:
            raise InvalidCredentialsError()
        if not self._passwords.verify(password, user.password_hash):
            raise InvalidCredentialsError()

        tokens = TokenPair(
            access=self._tokens.create(str(user.id), expires_in_minutes=self._access_ttl),
            refresh=self._tokens.create(str(user.id), expires_in_minutes=self._refresh_ttl),
        )
        self._logger.info("User authenticated", extra={"user_id": user.id})
        return tokens

    async def get_user_from_token(self, token: str) -> User:
        payload = self._tokens.decode(token)
        try:
            user_id = int(payload.sub)
        except ValueError as exc:
            raise InvalidTokenError() from exc

        user = await self._users.find_by_id(user_id)
        if user is None:
            raise UserNotFoundError()
        if not user.is_active:
            raise InvalidTokenError("User is inactive")
        return user

    async def ensure_user_active(self, user: User) -> None:
        if not user.is_active:
            raise InvalidCredentialsError("User is inactive")

    def log_exception(self, exc: AuthServiceError, *, extra: dict[str, Any] | None = None) -> None:
        context = {"detail": exc.detail, **(extra or {})}
        self._logger.warning("Auth service error", extra=context)
