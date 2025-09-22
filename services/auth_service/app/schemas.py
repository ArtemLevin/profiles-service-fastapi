from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenPair(BaseModel):
    access: str
    refresh: str


class TokenPayload(BaseModel):
    sub: str
    iat: datetime
    exp: datetime


class Me(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr


__all__ = ("RegisterRequest", "LoginRequest", "TokenPair", "TokenPayload", "Me")
