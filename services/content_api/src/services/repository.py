from __future__ import annotations

import logging
from typing import Any

from elasticsearch import AsyncElasticsearch, NotFoundError
from elastic_transport import ApiError, TransportError

from ..core.exceptions import ContentNotFoundError, ExternalServiceError


class ElasticContentRepository:
    """Repository facade encapsulating Elasticsearch operations."""

    def __init__(self, client: AsyncElasticsearch, *, index: str) -> None:
        self._client = client
        self._index = index
        self._logger = logging.getLogger(f"content_api.repository.{index}")

    @property
    def index_name(self) -> str:
        return self._index

    async def get(self, entity_id: str) -> dict[str, Any]:
        try:
            response = await self._client.get(index=self._index, id=entity_id)
        except NotFoundError as exc:
            raise ContentNotFoundError(entity=self._index, entity_id=entity_id) from exc
        except (ApiError, TransportError) as exc:
            self._logger.error(
                "Elasticsearch transport error", extra={"id": entity_id}, exc_info=exc
            )
            raise ExternalServiceError(
                message="Elasticsearch request failed", details={"index": self._index}
            ) from exc
        except Exception as exc:  # pragma: no cover - defensive logging
            self._logger.exception("Unexpected error fetching document", extra={"id": entity_id})
            raise ExternalServiceError(
                message="Unexpected Elasticsearch error", details={"index": self._index}
            ) from exc

        source = response.get("_source")
        if not isinstance(source, dict):
            self._logger.error("Document missing _source", extra={"id": entity_id})
            raise ExternalServiceError(
                message="Invalid Elasticsearch document", details={"index": self._index}
            )
        return source

    async def search_all(self, size: int) -> list[dict[str, Any]]:
        try:
            response = await self._client.search(
                index=self._index, query={"match_all": {}}, size=size
            )
        except (ApiError, TransportError) as exc:
            self._logger.error("Elasticsearch search error", extra={"size": size}, exc_info=exc)
            raise ExternalServiceError(
                message="Elasticsearch search failed", details={"index": self._index}
            ) from exc
        except Exception as exc:  # pragma: no cover - defensive logging
            self._logger.exception("Unexpected error searching documents", extra={"size": size})
            raise ExternalServiceError(
                message="Unexpected Elasticsearch error", details={"index": self._index}
            ) from exc

        hits = response.get("hits", {}).get("hits", [])
        results: list[dict[str, Any]] = []
        for hit in hits:
            source = hit.get("_source") if isinstance(hit, dict) else None
            if isinstance(source, dict):
                results.append(source)
            else:  # pragma: no cover - defensive branch
                self._logger.debug("Skipping hit without source", extra={"hit": hit})
        return results
