from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ...schemas import LoginRequest, Me, RegisterRequest, TokenPair
from ...services.auth import AuthService
from ..dependencies import get_auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


@router.post("/register", response_model=Me, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> Me:
    user = await service.register_user(email=payload.email, password=payload.password)
    return Me.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenPair:
    return await service.login(email=payload.email, password=payload.password)


@router.get("/me", response_model=Me)
async def read_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    service: AuthService = Depends(get_auth_service),
) -> Me:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user = await service.get_user_from_token(credentials.credentials)
    return Me.model_validate(user)
