from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from passlib.hash import bcrypt
from pydantic import ValidationError

from .core.exceptions import InvalidTokenError
from .schemas import TokenPayload


class PasswordHasher:
    """Password hashing and verification helper."""

    def hash(self, password: str) -> str:
        return bcrypt.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        return bcrypt.verify(password, password_hash)


class TokenService:
    """Utility class for creating and validating JWT tokens."""

    def __init__(self, *, secret: str, algorithm: str) -> None:
        self._secret = secret
        self._algorithm = algorithm

    def create(self, subject: str, *, expires_in_minutes: int) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": subject,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=expires_in_minutes)).timestamp()),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode(self, token: str) -> TokenPayload:
        try:
            data = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except JWTError as exc:  # pragma: no cover - passthrough for actual runtime failures
            raise InvalidTokenError() from exc
        try:
            return TokenPayload.model_validate(data)
        except ValidationError as exc:
            raise InvalidTokenError() from exc
