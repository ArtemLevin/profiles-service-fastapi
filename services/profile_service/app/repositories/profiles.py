"""Persistence helpers for ``Profile`` objects."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Profile


class ProfileRepository:
    """High-level data access helpers for profiles."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, user_id: int) -> Profile | None:
        return await self._session.scalar(select(Profile).where(Profile.user_id == user_id))

    async def phone_in_use(
        self, phone_digest: bytes, *, exclude_profile_id: UUID | None = None
    ) -> bool:
        stmt = select(Profile.id).where(Profile.phone_hash == phone_digest)
        if exclude_profile_id is not None:
            stmt = stmt.where(Profile.id != exclude_profile_id)
        return await self._session.scalar(stmt) is not None

    async def add(self, profile: Profile) -> Profile:
        self._session.add(profile)
        await self._session.flush()
        return profile

    async def update(self, profile: Profile, updates: dict[str, Any]) -> Profile:
        for field, value in updates.items():
            setattr(profile, field, value)
        await self._session.flush()
        return profile

    async def delete(self, profile: Profile) -> None:
        await self._session.delete(profile)
        await self._session.flush()
