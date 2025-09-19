import os
import base64
import asyncio
import pytest
from httpx import AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import Base, get_session

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
def test_env():
    key = b"0"*32
    os.environ["PROFILES_CRYPTO_KEY_BASE64"] = base64.b64encode(key).decode()
    os.environ["PHONE_HASH_PEPPER"] = "pepper_test"
    os.environ["JWT_SECRET"] = "jwt_test"
    os.environ["JWT_ALG"] = "HS256"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"

@pytest.fixture(scope="session")
async def db_engine():
    from app.settings import settings
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def session_override(db_engine):
    SessionLocal = async_sessionmaker(db_engine, expire_on_commit=False)
    async def _get_session():
        async with SessionLocal() as s:
            yield s
    app.dependency_overrides[get_session] = _get_session
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def bearer_token():
    secret = os.environ["JWT_SECRET"]
    alg = os.environ["JWT_ALG"]
    token = jwt.encode({"sub": "123"}, secret, algorithm=alg)
    return f"Bearer {token}"

@pytest.fixture
async def client(session_override):
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac

@pytest.fixture
async def async_client(session_override):
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac
