from __future__ import annotations

from fastapi import APIRouter

from .routes.auth import router as auth_router

api_router = APIRouter()
api_router.include_router(auth_router)

__all__ = ["api_router"]
