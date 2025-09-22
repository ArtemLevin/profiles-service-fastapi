from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from services.common.db import ensure_aiosqlite

from .settings import get_settings

settings = get_settings()

ensure_aiosqlite()

engine = create_async_engine(
    settings.database_url,
    future=True,
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""



async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a scoped SQLAlchemy asynchronous session."""

    async with SessionLocal() as session:
        yield session


async def init_models() -> None:
    """Ensure database schema is available."""

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
