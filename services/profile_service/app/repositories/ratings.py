"""Persistence helpers for ``Rating`` objects."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Rating


class RatingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, profile_id: UUID, film_id: UUID) -> Rating | None:
        stmt = select(Rating).where(Rating.profile_id == profile_id, Rating.film_id == film_id)
        return await self._session.scalar(stmt)

    async def add(self, rating: Rating) -> Rating:
        self._session.add(rating)
        await self._session.flush()
        return rating

    async def aggregate_for_film(self, film_id: UUID) -> tuple[float | None, int | None]:
        result = await self._session.execute(
            select(func.avg(Rating.rating), func.count()).where(Rating.film_id == film_id)
        )
        avg_value, count_value = result.one()
        return avg_value, count_value
