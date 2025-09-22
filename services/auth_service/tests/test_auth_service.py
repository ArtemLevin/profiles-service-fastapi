from __future__ import annotations

from pathlib import Path
import sys
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.auth_service.app.core.exceptions import (  # noqa: E402
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
)
from services.auth_service.app.models import User  # noqa: E402
from services.auth_service.app.repositories.user_repository import UserRepository  # noqa: E402
from services.auth_service.app.security import PasswordHasher, TokenService  # noqa: E402
from services.auth_service.app.services.auth import AuthService  # noqa: E402

pytestmark = pytest.mark.anyio("asyncio")


@pytest.fixture
def anyio_backend() -> str:
    """Restrict anyio to the asyncio backend for local testing."""

    return "asyncio"


class InMemorySession:
    async def commit(self) -> None:  # pragma: no cover - simple stub
        return None

    async def rollback(self) -> None:  # pragma: no cover - simple stub
        return None

    async def refresh(self, _: User) -> None:  # pragma: no cover - simple stub
        return None


class InMemoryUserRepository:
    def __init__(self) -> None:
        self._users: dict[int, User] = {}
        self._email_index: dict[str, int] = {}
        self._next_id = 1

    async def find_by_email(self, email: str) -> User | None:
        user_id = self._email_index.get(email)
        if user_id is None:
            return None
        return self._users.get(user_id)

    async def find_by_id(self, user_id: int) -> User | None:
        return self._users.get(user_id)

    async def add(self, user: User) -> User:
        user.id = self._next_id
        self._next_id += 1
        self._users[user.id] = user
        self._email_index[user.email] = user.id
        return user


@pytest.fixture
def auth_service() -> AuthService:
    session = cast(AsyncSession, InMemorySession())
    repository = cast(UserRepository, InMemoryUserRepository())
    return AuthService(
        session=session,
        user_repository=repository,
        password_hasher=PasswordHasher(),
        token_service=TokenService(secret="testsecret", algorithm="HS256"),
        access_ttl_minutes=30,
        refresh_ttl_minutes=60,
    )


async def test_registers_user(auth_service: AuthService) -> None:
    user = await auth_service.register_user(email="user@example.com", password="strongpassword")
    assert user.id == 1
    assert user.email == "user@example.com"


async def test_register_duplicate_email(auth_service: AuthService) -> None:
    await auth_service.register_user(email="user@example.com", password="strongpassword")
    with pytest.raises(UserAlreadyExistsError):
        await auth_service.register_user(email="user@example.com", password="otherpass")


async def test_login_success(auth_service: AuthService) -> None:
    await auth_service.register_user(email="user@example.com", password="strongpassword")
    tokens = await auth_service.login(email="user@example.com", password="strongpassword")
    assert tokens.access
    assert tokens.refresh


async def test_login_invalid_password(auth_service: AuthService) -> None:
    await auth_service.register_user(email="user@example.com", password="strongpassword")
    with pytest.raises(InvalidCredentialsError):
        await auth_service.login(email="user@example.com", password="wrongpassword")


async def test_get_user_from_token(auth_service: AuthService) -> None:
    user = await auth_service.register_user(email="user@example.com", password="strongpassword")
    tokens = await auth_service.login(email="user@example.com", password="strongpassword")
    fetched = await auth_service.get_user_from_token(tokens.access)
    assert fetched.id == user.id
    assert fetched.email == user.email

    with pytest.raises(InvalidTokenError):
        await auth_service.get_user_from_token("invalid")
