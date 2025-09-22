from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from ..dependencies import get_film_service
from ...models.models import Film
from ...services.content_service import ContentService

router = APIRouter()


@router.get("/{film_uuid}", response_model=Film)
async def get_film(
    film_uuid: UUID,
    service: ContentService[Film] = Depends(get_film_service),
) -> Film:
    return await service.get(film_uuid)


@router.get("/", response_model=list[Film])
async def list_films(
    size: int | None = Query(default=None, ge=1, le=500),
    service: ContentService[Film] = Depends(get_film_service),
) -> list[Film]:
    return await service.list(size=size)
