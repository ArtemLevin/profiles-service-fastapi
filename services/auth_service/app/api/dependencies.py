from __future__ import annotations

import logging

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.user_repository import UserRepository
from ..security import PasswordHasher, TokenService
from ..services.auth import AuthService
from ..settings import get_settings
from ..db import get_session


async def get_auth_service(
    session: AsyncSession = Depends(get_session),
) -> AuthService:
    settings = get_settings()
    logger = logging.getLogger("auth_service")
    service = AuthService(
        session=session,
        user_repository=UserRepository(session),
        password_hasher=PasswordHasher(),
        token_service=TokenService(
            secret=settings.security.jwt_secret.get_secret_value(),
            algorithm=settings.security.jwt_alg,
        ),
        access_ttl_minutes=settings.tokens.access_token_expires_min,
        refresh_ttl_minutes=settings.tokens.refresh_token_expires_min,

        logger=logger,
    )
    return service
