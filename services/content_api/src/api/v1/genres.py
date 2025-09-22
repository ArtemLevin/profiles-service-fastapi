from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from ..dependencies import get_genre_service
from ...models.models import Genre
from ...services.content_service import ContentService

router = APIRouter()


@router.get("/{genre_uuid}", response_model=Genre)
async def get_genre(
    genre_uuid: UUID,
    service: ContentService[Genre] = Depends(get_genre_service),
) -> Genre:
    return await service.get(genre_uuid)


@router.get("/", response_model=list[Genre])
async def list_genres(
    size: int | None = Query(default=None, ge=1, le=500),
    service: ContentService[Genre] = Depends(get_genre_service),
) -> list[Genre]:
    return await service.list(size=size)
