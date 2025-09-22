import asyncio
import base64
import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient
from jose import jwt
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Ensure the project root is importable when running tests from the service directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.dependencies import get_current_user_id, get_is_admin, get_redis
from app.settings import reload_settings, settings
from app.db import Base, get_session
from app.models import AuditLog, Favorite, Profile, Rating
from app.main import app

os.environ.setdefault("PROFILES_CRYPTO_KEY_BASE64", base64.b64encode(b"0" * 32).decode())
os.environ.setdefault("PHONE_HASH_PEPPER", "pepper_test")
os.environ.setdefault("JWT_SECRET", "jwt_test")
os.environ.setdefault("JWT_ALG", "HS256")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("RATE_LIMIT_STORAGE_URI", "memory://")

reload_settings()


class InMemoryRedis:
    """Minimal async Redis replacement for tests."""

    def __init__(self) -> None:
        self._storage: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> str | None:
        async with self._lock:
            return self._storage.get(key)

    async def set(
        self, key: str, value: str, ex: int | None = None
    ) -> None:  # noqa: ARG002 - TTL not used in tests
        async with self._lock:
            self._storage[key] = value

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._storage.pop(key, None)

    async def flushdb(self) -> None:
        async with self._lock:
            self._storage.clear()

    async def close(self) -> None:
        await self.flushdb()

    async def aclose(self) -> None:
        await self.close()


@pytest_asyncio.fixture(scope="session")
async def redis() -> AsyncIterator[InMemoryRedis]:
    redis_instance = InMemoryRedis()
    await redis_instance.flushdb()
    yield redis_instance
    await redis_instance.aclose()


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_override(db_engine, redis):
    SessionLocal = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _get_session():
        async with SessionLocal() as session:
            yield session

    async def _get_redis():
        return redis

    async def _get_user_id():
        return 123

    async def _get_is_admin():
        return False

    async with SessionLocal() as cleanup:
        await cleanup.execute(delete(AuditLog))
        await cleanup.execute(delete(Favorite))
        await cleanup.execute(delete(Rating))
        await cleanup.execute(delete(Profile))
        await cleanup.commit()

    app.dependency_overrides[get_session] = _get_session
    app.dependency_overrides[get_redis] = _get_redis
    app.dependency_overrides[get_current_user_id] = _get_user_id
    app.dependency_overrides[get_is_admin] = _get_is_admin

    yield

    app.dependency_overrides.clear()


@pytest.fixture
def bearer_token():
    secret = os.environ["JWT_SECRET"]
    alg = os.environ["JWT_ALG"]
    token = jwt.encode({"sub": "123"}, secret, algorithm=alg)
    return f"Bearer {token}"


@pytest_asyncio.fixture
async def client(session_override):
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac


@pytest_asyncio.fixture
async def async_client(session_override):
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac
