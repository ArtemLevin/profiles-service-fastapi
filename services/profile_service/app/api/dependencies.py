"""Common FastAPI dependencies used by the profile API."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import DomainError
from ..crypto import CryptoBox
from ..db import get_session
from ..security import decode_jwt
from ..services import ProfileService
from ..settings import settings

try:  # pragma: no cover - optional dependency for docs/tests
    from slowapi import Limiter
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.util import get_remote_address
except ModuleNotFoundError:  # pragma: no cover - fallback for tests
    from ..utils.slowapi_stub import (
        Limiter,
        RateLimitExceeded,
        SlowAPIMiddleware,
        get_remote_address,
    )


security = HTTPBearer()
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.limiter_storage_uri)


@lru_cache(maxsize=1)
def get_crypto_box() -> CryptoBox:
    return CryptoBox(settings.profiles_crypto_key_base64)


async def get_redis(request: Request) -> Redis:
    redis = getattr(request.app.state, "redis", None)
    if redis is None:  # pragma: no cover - defensive
        raise RuntimeError("Redis client is not initialised")
    return redis


async def get_profile_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> ProfileService:
    return ProfileService(
        session=session,
        redis=redis,
        crypto_box=get_crypto_box(),
        phone_pepper=settings.phone_hash_pepper,
        rating_cache_ttl=settings.rating_cache_ttl_seconds,
    )


def _decode_credentials(token: HTTPAuthorizationCredentials) -> dict[str, Any]:
    try:
        return decode_jwt(token.credentials, secret=settings.jwt_secret, alg=settings.jwt_alg)
    except JWTError as exc:  # pragma: no cover - JWT library failure
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc


async def get_current_user_id(
    token: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> int:
    payload = _decode_credentials(token)
    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        ) from exc


async def get_is_admin(token: Annotated[HTTPAuthorizationCredentials, Depends(security)]) -> bool:
    try:
        payload = _decode_credentials(token)
    except HTTPException:
        return False
    return payload.get("role") == "admin"


SessionDep = Annotated[AsyncSession, Depends(get_session)]
RedisDep = Annotated[Redis, Depends(get_redis)]
CurrentUserDep = Annotated[int, Depends(get_current_user_id)]
AdminDep = Annotated[bool, Depends(get_is_admin)]
ServiceDep = Annotated[ProfileService, Depends(get_profile_service)]

__all__ = [
    "AdminDep",
    "CurrentUserDep",
    "DomainError",
    "Limiter",
    "RateLimitExceeded",
    "RedisDep",
    "ServiceDep",
    "SessionDep",
    "SlowAPIMiddleware",
    "get_current_user_id",
    "get_is_admin",
    "get_profile_service",
    "get_redis",
    "limiter",
    "security",
]
