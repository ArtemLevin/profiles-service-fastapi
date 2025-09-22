"""Persistence helpers for favorites."""

from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Favorite


class FavoriteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, profile_id: UUID, film_id: UUID) -> Favorite | None:
        stmt = select(Favorite).where(
            Favorite.profile_id == profile_id, Favorite.film_id == film_id
        )
        return await self._session.scalar(stmt)

    async def add(self, favorite: Favorite) -> Favorite:
        self._session.add(favorite)
        await self._session.flush()
        return favorite

    async def delete(self, favorite: Favorite) -> None:
        await self._session.delete(favorite)
        await self._session.flush()

    async def list_by_profile(
        self, profile_id: UUID, *, limit: int, offset: int
    ) -> Sequence[Favorite]:
        stmt = (
            select(Favorite)
            .where(Favorite.profile_id == profile_id)
            .order_by(desc(Favorite.created_at))
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_by_profile(self, profile_id: UUID) -> int:
        total = await self._session.scalar(
            select(func.count()).where(Favorite.profile_id == profile_id)
        )
        return int(total or 0)
