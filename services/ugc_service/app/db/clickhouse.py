"""Helpers for managing ClickHouse HTTP connections."""

from __future__ import annotations

import httpx

from ..core.settings import ClickHouseSettings


def create_clickhouse_client(settings: ClickHouseSettings) -> httpx.AsyncClient:
    """Return an :class:`httpx.AsyncClient` configured for ClickHouse."""

    scheme = "https" if settings.secure else "http"
    base_url = f"{scheme}://{settings.host}:{settings.port}"
    timeout = httpx.Timeout(
        connect=settings.connect_timeout,
        read=settings.read_timeout,
        write=settings.write_timeout,
        pool=settings.pool_timeout,
    )
    limits = httpx.Limits(
        max_connections=settings.max_connections,
        max_keepalive_connections=settings.max_keepalive_connections,
    )
    auth = (settings.user, settings.password) if settings.user or settings.password else None
    return httpx.AsyncClient(base_url=base_url, timeout=timeout, limits=limits, auth=auth)


async def close_clickhouse_client(client: httpx.AsyncClient) -> None:
    """Close the underlying HTTP connection pool."""

    await client.aclose()


async def ping_clickhouse(client: httpx.AsyncClient, database: str) -> None:
    """Perform a lightweight ``SELECT 1`` query to verify connectivity."""

    response = await client.post("/", params={"database": database, "query": "SELECT 1"})
    response.raise_for_status()
