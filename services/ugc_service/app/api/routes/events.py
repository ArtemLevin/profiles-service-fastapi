"""HTTP routes for working with user-generated content events."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from ...core.settings import Settings
from ...schemas import EventIngestResponse, EventsListResponse, UserEventCreate
from ...services.events import EventServiceProtocol
from ..dependencies import get_app_settings, get_event_service

router = APIRouter(tags=["events"])


async def _record_event(
    event: UserEventCreate, service: EventServiceProtocol
) -> EventIngestResponse:
    await service.record_event(event)
    return EventIngestResponse(ok=True)


@router.post("/events", response_model=EventIngestResponse, status_code=status.HTTP_200_OK)
async def create_event(
    event: UserEventCreate,
    service: EventServiceProtocol = Depends(get_event_service),
) -> EventIngestResponse:
    """Ingest a single event into ClickHouse."""

    return await _record_event(event=event, service=service)


@router.post(
    "/event",
    response_model=EventIngestResponse,
    include_in_schema=False,
    status_code=status.HTTP_200_OK,
)
async def create_event_legacy(
    event: UserEventCreate,
    service: EventServiceProtocol = Depends(get_event_service),
) -> EventIngestResponse:
    """Backward-compatible alias for the historical ``/event`` endpoint."""

    return await _record_event(event=event, service=service)


@router.get("/events", response_model=EventsListResponse)
async def list_events(
    limit: int | None = Query(default=None, ge=1),
    service: EventServiceProtocol = Depends(get_event_service),
    settings: Settings = Depends(get_app_settings),
) -> EventsListResponse:
    """Return the most recent events stored in ClickHouse."""

    effective_limit = limit or settings.default_list_limit
    effective_limit = min(effective_limit, settings.max_list_limit)
    items = await service.list_events(limit=effective_limit)
    return EventsListResponse(items=items, limit=effective_limit)
