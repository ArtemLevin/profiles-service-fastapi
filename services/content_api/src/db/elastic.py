from __future__ import annotations

import logging
from typing import Any

from elasticsearch import AsyncElasticsearch
from elastic_transport import ApiError, TransportError

from ..core.settings import Settings

LOGGER = logging.getLogger("content_api.elastic")


def create_elastic_client(settings: Settings) -> AsyncElasticsearch:
    """Instantiate a configured AsyncElasticsearch client."""

    scheme = "https" if settings.elastic_use_ssl else "http"
    hosts = [{"host": settings.elastic_host, "port": settings.elastic_port, "scheme": scheme}]
    kwargs: dict[str, Any] = {
        "hosts": hosts,
        "verify_certs": settings.elastic_verify_certs,
        "request_timeout": settings.elastic_request_timeout,
        "max_retries": settings.elastic_max_retries,
        "retry_on_timeout": True,
    }
    if settings.elastic_username and settings.elastic_password:
        kwargs["basic_auth"] = (settings.elastic_username, settings.elastic_password)
    return AsyncElasticsearch(**kwargs)


async def ping_elastic(client: AsyncElasticsearch) -> bool:
    """Ping elastic and log connectivity failures."""

    try:
        return await client.ping()
    except (ApiError, TransportError) as exc:  # pragma: no cover - network failure path
        LOGGER.warning("Elasticsearch ping failed", exc_info=exc)
        return False


async def close_elastic(client: AsyncElasticsearch) -> None:
    """Close the elastic client."""

    try:
        await client.close()
    except Exception:  # pragma: no cover - best effort
        LOGGER.exception("Failed to close elastic client")
