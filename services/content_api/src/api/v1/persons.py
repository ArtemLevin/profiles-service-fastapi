from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from ..dependencies import get_person_service
from ...models.models import Person
from ...services.content_service import ContentService

router = APIRouter()


@router.get("/{person_uuid}", response_model=Person)
async def get_person(
    person_uuid: UUID,
    service: ContentService[Person] = Depends(get_person_service),
) -> Person:
    return await service.get(person_uuid)


@router.get("/", response_model=list[Person])
async def list_persons(
    size: int | None = Query(default=None, ge=1, le=500),
    service: ContentService[Person] = Depends(get_person_service),
) -> list[Person]:
    return await service.list(size=size)
