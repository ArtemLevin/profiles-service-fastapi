"""Pydantic schemas used by the UGC service."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UserEventCreate(BaseModel):
    user_id: str
    movie_id: str
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: dict[str, Any] | None = None


class UserEventRead(BaseModel):
    user_id: str
    movie_id: str
    event_type: str
    timestamp: datetime
    payload: dict[str, Any] | None = None


class EventIngestResponse(BaseModel):
    ok: bool


class EventsListResponse(BaseModel):
    items: list[UserEventRead]
    limit: int
