"""Audit log persistence helpers."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AuditLog


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log(
        self,
        *,
        profile_id: Any,
        user_id: int,
        action: str,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        payload = json.dumps(details, ensure_ascii=False) if details else None
        entry = AuditLog(
            profile_id=profile_id,
            user_id=user_id,
            action=action,
            details=payload,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry
