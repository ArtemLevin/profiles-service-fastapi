from __future__ import annotations

from fastapi import Depends, Request

from ..services.container import ServiceContainer
from ..services.content_service import ContentService
from ..models.models import Film, Genre, Person


def get_service_container(request: Request) -> ServiceContainer:
    container = getattr(request.app.state, "services", None)
    if container is None:
        raise RuntimeError("Service container has not been initialised")
    if not isinstance(container, ServiceContainer):  # pragma: no cover - defensive
        raise RuntimeError("Invalid service container attached to application state")
    return container


def get_film_service(
    container: ServiceContainer = Depends(get_service_container),
) -> ContentService[Film]:
    return container.film


def get_genre_service(
    container: ServiceContainer = Depends(get_service_container),
) -> ContentService[Genre]:
    return container.genre


def get_person_service(
    container: ServiceContainer = Depends(get_service_container),
) -> ContentService[Person]:
    return container.person
