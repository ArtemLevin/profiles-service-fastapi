from __future__ import annotations

import logging
from typing import Generic, Protocol, TypeVar
from uuid import UUID

from pydantic import BaseModel, ValidationError

from ..core.exceptions import ContentServiceError, ExternalServiceError

ModelT = TypeVar("ModelT", bound=BaseModel)


class ContentCacheProtocol(Protocol, Generic[ModelT]):
    async def fetch_model(self, key: str, model_type: type[ModelT]) -> ModelT | None: ...

    async def store_model(self, key: str, model: ModelT, *, ttl: int | None = None) -> None: ...


class ContentRepositoryProtocol(Protocol):
    @property
    def index_name(self) -> str: ...

    async def get(self, entity_id: str) -> dict[str, object]: ...

    async def search_all(self, size: int) -> list[dict[str, object]]: ...


class ContentService(Generic[ModelT]):
    """High-level service orchestrating cache and repository access."""

    def __init__(
        self,
        *,
        repository: ContentRepositoryProtocol,
        cache: ContentCacheProtocol[ModelT],
        model_type: type[ModelT],
        cache_ttl_seconds: int,
        default_page_size: int,
    ) -> None:
        self._repository: ContentRepositoryProtocol = repository
        self._cache: ContentCacheProtocol[ModelT] = cache
        self._model_type = model_type
        self._cache_ttl_seconds = cache_ttl_seconds
        self._default_page_size = default_page_size
        self._logger = logging.getLogger(f"content_api.service.{repository.index_name}")

    async def get(self, entity_id: UUID) -> ModelT:
        key = self._cache_key(entity_id)
        cached = await self._cache.fetch_model(key, self._model_type)
        if cached is not None:
            self._logger.debug("Cache hit", extra={"id": str(entity_id)})
            return cached

        document = await self._repository.get(str(entity_id))
        model = self._to_model(document, entity_id)
        await self._cache.store_model(key, model, ttl=self._cache_ttl_seconds)
        self._logger.debug("Cache populated", extra={"id": str(entity_id)})
        return model

    async def list(self, *, size: int | None = None) -> list[ModelT]:
        limit = size or self._default_page_size
        documents = await self._repository.search_all(limit)
        models: list[ModelT] = []
        for document in documents:
            try:
                models.append(self._model_type.model_validate(document))
            except ValidationError as exc:
                self._logger.error(
                    "Invalid document payload", extra={"document": document}, exc_info=exc
                )
                raise ExternalServiceError(
                    message="Invalid document payload",
                    details={"index": self._repository.index_name},
                ) from exc
        return models

    def _cache_key(self, entity_id: UUID) -> str:
        return f"{self._repository.index_name}:{entity_id}"  # Namespacing keeps cache keys unique per index

    def _to_model(self, document: dict[str, object], entity_id: UUID) -> ModelT:
        try:
            return self._model_type.model_validate(document)
        except ValidationError as exc:
            self._logger.error(
                "Invalid document payload",
                extra={"id": str(entity_id), "document": document},
                exc_info=exc,
            )
            raise ExternalServiceError(
                message="Invalid document payload", details={"index": self._repository.index_name}
            ) from exc
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.exception(
                "Unexpected error converting document", extra={"id": str(entity_id)}
            )
            raise ContentServiceError(message="Unexpected error processing document") from exc
