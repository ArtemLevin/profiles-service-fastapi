"""Repository for persisting and querying user events in ClickHouse."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import httpx

from ..core.exceptions import RepositoryError
from ..schemas import UserEventCreate, UserEventRead

LOGGER = logging.getLogger(__name__)


class EventRepository:
    """Persistence layer for ClickHouse-backed user events."""

    def __init__(self, client: httpx.AsyncClient, database: str) -> None:
        self._client = client
        self._database = database

    async def ensure_schema(self) -> None:
        """Create the ``user_events`` table if it does not already exist."""

        query = f"""
        CREATE TABLE IF NOT EXISTS {self._database}.user_events
        (
            user_id String,
            movie_id String,
            event_type String,
            timestamp DateTime,
            payload String
        )
        ENGINE = MergeTree
        ORDER BY (timestamp, user_id)
        """
        await self._execute(query=query)

    async def insert_event(self, event: UserEventCreate) -> None:
        """Persist a new event into ClickHouse using ``JSONEachRow`` format."""

        row = {
            "user_id": event.user_id,
            "movie_id": event.movie_id,
            "event_type": event.event_type,
            "timestamp": event.timestamp.replace(microsecond=0).isoformat(sep=" "),
            "payload": self._encode_payload(event.payload),
        }
        payload = (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
        query = f"INSERT INTO {self._database}.user_events FORMAT JSONEachRow"
        await self._execute(query=query, data=payload)

    async def fetch_recent(self, limit: int) -> list[UserEventRead]:
        """Return the most recent events in reverse-chronological order."""

        query = (
            "SELECT user_id, movie_id, event_type, toString(timestamp) AS timestamp, payload "
            f"FROM {self._database}.user_events ORDER BY timestamp DESC LIMIT {limit}"
        )
        response = await self._execute(query=query, params={"default_format": "JSON"})
        try:
            payload = response.json()
        except ValueError as exc:  # pragma: no cover - defensive guard
            raise RepositoryError("Received invalid JSON from ClickHouse") from exc

        records = payload.get("data", []) if isinstance(payload, dict) else []
        events: list[UserEventRead] = []
        for record in records:
            try:
                timestamp_raw = record["timestamp"]
                event = UserEventRead(
                    user_id=record["user_id"],
                    movie_id=record["movie_id"],
                    event_type=record["event_type"],
                    timestamp=self._parse_timestamp(timestamp_raw),
                    payload=self._decode_payload(record.get("payload")),
                )
            except (KeyError, TypeError, ValueError) as exc:
                LOGGER.exception("Failed to parse ClickHouse row", extra={"row": record})
                raise RepositoryError("Malformed ClickHouse row encountered") from exc
            events.append(event)
        return events

    async def _execute(
        self,
        query: str,
        *,
        params: dict[str, Any] | None = None,
        data: bytes | None = None,
    ) -> httpx.Response:
        request_params: dict[str, Any] = {"database": self._database, "query": query}
        if params:
            request_params.update(params)
        try:
            response = await self._client.post("/", params=request_params, content=data)
            response.raise_for_status()
            return response
        except httpx.HTTPError as exc:
            LOGGER.exception("ClickHouse query failed", extra={"query": query})
            raise RepositoryError("ClickHouse request failed") from exc

    @staticmethod
    def _encode_payload(payload: dict[str, Any] | None) -> str:
        if payload is None:
            return ""
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _decode_payload(payload: str | None) -> dict[str, Any] | None:
        if not payload:
            return None
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            LOGGER.warning("Invalid JSON payload stored in ClickHouse", extra={"payload": payload})
            return None

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        try:
            return datetime.fromisoformat(value.replace(" ", "T"))
        except ValueError as exc:
            raise ValueError(f"Invalid timestamp received from ClickHouse: {value}") from exc
