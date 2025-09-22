from __future__ import annotations

from dataclasses import dataclass

from elasticsearch import AsyncElasticsearch

from ..core.settings import Settings
from ..models.models import Film, Genre, Person
from .cache import RedisJSONCache
from .content_service import ContentService
from .repository import ElasticContentRepository


@dataclass(frozen=True)
class ServiceContainer:
    film: ContentService[Film]
    genre: ContentService[Genre]
    person: ContentService[Person]


def build_service_container(
    *,
    elastic: AsyncElasticsearch,
    cache: RedisJSONCache,
    settings: Settings,
) -> ServiceContainer:
    film_repository = ElasticContentRepository(elastic, index=settings.film_index)
    genre_repository = ElasticContentRepository(elastic, index=settings.genre_index)
    person_repository = ElasticContentRepository(elastic, index=settings.person_index)

    film_service: ContentService[Film] = ContentService(
        repository=film_repository,
        cache=cache,
        model_type=Film,
        cache_ttl_seconds=settings.redis_cache_ttl_seconds,
        default_page_size=settings.default_page_size,
    )
    genre_service: ContentService[Genre] = ContentService(
        repository=genre_repository,
        cache=cache,
        model_type=Genre,
        cache_ttl_seconds=settings.redis_cache_ttl_seconds,
        default_page_size=settings.default_page_size,
    )
    person_service: ContentService[Person] = ContentService(
        repository=person_repository,
        cache=cache,
        model_type=Person,
        cache_ttl_seconds=settings.redis_cache_ttl_seconds,
        default_page_size=settings.default_page_size,
    )

    return ServiceContainer(
        film=film_service,
        genre=genre_service,
        person=person_service,
    )
