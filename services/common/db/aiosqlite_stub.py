"""Fallback implementation for :mod:`aiosqlite` used in tests."""

from __future__ import annotations

import asyncio
import sqlite3
import sys
from types import ModuleType
from typing import Any, Awaitable, Callable, Iterable, Mapping, Sequence, cast

SQLRow = Sequence[Any] | Mapping[str, Any]
RowFactory = Callable[[sqlite3.Row], Any] | None


class _Cursor:
    def __init__(self, cursor: sqlite3.Cursor) -> None:
        self._cursor = cursor

    @property
    def description(self) -> Any:
        return self._cursor.description

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    @property
    def lastrowid(self) -> int | None:
        return self._cursor.lastrowid

    async def fetchone(self) -> Any:
        return await asyncio.to_thread(self._cursor.fetchone)

    async def fetchmany(self, size: int | None = None) -> list[Any]:
        if size is None:
            return await asyncio.to_thread(self._cursor.fetchmany)
        return await asyncio.to_thread(self._cursor.fetchmany, size)

    async def fetchall(self) -> list[Any]:
        return await asyncio.to_thread(self._cursor.fetchall)

    async def execute(self, sql: str, parameters: Iterable[Any] | None = None) -> "_Cursor":
        params = tuple(parameters or ())
        await asyncio.to_thread(self._cursor.execute, sql, params)
        return self

    async def executemany(self, sql: str, seq_of_parameters: Iterable[SQLRow]) -> "_Cursor":
        await asyncio.to_thread(self._cursor.executemany, sql, seq_of_parameters)
        return self

    async def executescript(self, script: str) -> "_Cursor":
        await asyncio.to_thread(self._cursor.executescript, script)
        return self

    async def close(self) -> None:
        await asyncio.to_thread(self._cursor.close)

    async def __aenter__(self) -> "_Cursor":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: D401
        await self.close()


class _Connection:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._lock = asyncio.Lock()

    async def _run(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        async with self._lock:
            return await asyncio.to_thread(fn, *args, **kwargs)

    async def cursor(self) -> _Cursor:
        cursor = await self._run(self._connection.cursor)
        return _Cursor(cast(sqlite3.Cursor, cursor))

    async def execute(self, sql: str, parameters: Iterable[Any] | None = None) -> _Cursor:
        params = tuple(parameters or ())
        cursor = await self._run(self._connection.execute, sql, params)
        return _Cursor(cast(sqlite3.Cursor, cursor))

    async def executemany(self, sql: str, seq_of_parameters: Iterable[SQLRow]) -> _Cursor:
        cursor = await self._run(self._connection.executemany, sql, seq_of_parameters)
        return _Cursor(cast(sqlite3.Cursor, cursor))

    async def executescript(self, script: str) -> _Cursor:
        cursor = await self._run(self._connection.executescript, script)
        return _Cursor(cast(sqlite3.Cursor, cursor))

    async def commit(self) -> None:
        await self._run(self._connection.commit)

    async def rollback(self) -> None:
        await self._run(self._connection.rollback)

    async def close(self) -> None:
        await self._run(self._connection.close)

    async def create_function(self, *args: Any, **kwargs: Any) -> None:
        await self._run(self._connection.create_function, *args, **kwargs)

    async def create_aggregate(self, *args: Any, **kwargs: Any) -> None:
        await self._run(self._connection.create_aggregate, *args, **kwargs)

    async def create_collation(self, *args: Any, **kwargs: Any) -> None:
        await self._run(self._connection.create_collation, *args, **kwargs)

    async def __aenter__(self) -> "_Connection":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: D401
        await self.close()

    @property
    def row_factory(self) -> RowFactory:
        return self._connection.row_factory

    @row_factory.setter
    def row_factory(self, factory: RowFactory) -> None:
        self._connection.row_factory = factory

    @property
    def total_changes(self) -> int:
        return self._connection.total_changes


async def _connect(database: str, **kwargs: Any) -> _Connection:
    kwargs.setdefault("check_same_thread", False)
    connect_fn = cast(Callable[..., sqlite3.Connection], sqlite3.connect)
    connection = await asyncio.to_thread(connect_fn, database, **kwargs)
    return _Connection(connection)


class _ConnectionHandle:
    def __init__(self, coro: Awaitable[_Connection]) -> None:
        self._coro = coro
        self.daemon = False

    def __await__(self):
        return self._coro.__await__()


def ensure_aiosqlite() -> None:
    """Install a lightweight :mod:`aiosqlite` stub if the real package is absent."""

    if "aiosqlite" in sys.modules:
        return

    module = ModuleType("aiosqlite")

    def _connect_handle(*args: Any, **kwargs: Any) -> _ConnectionHandle:
        return _ConnectionHandle(_connect(*args, **kwargs))

    setattr(module, "connect", _connect_handle)
    setattr(module, "Connection", _Connection)
    setattr(module, "Cursor", _Cursor)

    for attr_name in [
        "Row",
        "PARSE_DECLTYPES",
        "PARSE_COLNAMES",
        "sqlite_version",
        "sqlite_version_info",
        "version",
        "version_info",
        "Warning",
        "Error",
        "OperationalError",
        "DatabaseError",
        "IntegrityError",
        "InterfaceError",
        "InternalError",
        "NotSupportedError",
        "DataError",
        "ProgrammingError",
    ]:
        setattr(module, attr_name, getattr(sqlite3, attr_name))

    setattr(module, "__all__", ["connect", "Connection", "Cursor", "Row"])

    sys.modules["aiosqlite"] = module
