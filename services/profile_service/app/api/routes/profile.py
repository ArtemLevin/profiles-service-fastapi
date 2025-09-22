"""HTTP routes for the profile service."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request, Response, status

from ...schemas import (
    FavoriteIn,
    FavoriteOut,
    FavoritesListOut,
    ProfileCreate,
    ProfileOut,
    ProfileUpdate,
    RatingAggregate,
    RatingOut,
    RatingPut,
)
from ..dependencies import AdminDep, CurrentUserDep, ServiceDep, limiter

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/me", response_model=ProfileOut)
@limiter.limit("10/minute")
async def get_me(
    request: Request,
    service: ServiceDep,
    user_id: CurrentUserDep,
    admin: AdminDep,
) -> ProfileOut:
    return await service.get_profile(user_id, actor_is_admin=admin)


@router.post("", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_profile(
    request: Request,
    service: ServiceDep,
    user_id: CurrentUserDep,
    payload: ProfileCreate,
) -> ProfileOut:
    return await service.create_profile(user_id, payload.model_dump())


@router.put("", response_model=ProfileOut)
@limiter.limit("10/minute")
async def update_profile(
    request: Request,
    service: ServiceDep,
    user_id: CurrentUserDep,
    payload: ProfileUpdate,
) -> ProfileOut:
    return await service.update_profile(user_id, payload.model_dump(exclude_none=True))


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_profile(
    request: Request,
    service: ServiceDep,
    user_id: CurrentUserDep,
) -> Response:
    await service.delete_profile(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me/ratings", response_model=RatingOut)
@limiter.limit("10/minute")
async def get_rating(
    request: Request,
    service: ServiceDep,
    user_id: CurrentUserDep,
    film_id: UUID,
) -> RatingOut:
    return await service.get_rating(user_id, film_id)


@router.put("/me/ratings", response_model=RatingOut)
@limiter.limit("10/minute")
async def put_rating(
    request: Request,
    service: ServiceDep,
    user_id: CurrentUserDep,
    payload: RatingPut,
) -> RatingOut:
    return await service.put_rating(user_id, payload.model_dump())


@router.get("/public/films/{film_id}/rating-agg", response_model=RatingAggregate)
@limiter.limit("10/minute")
async def get_rating_aggregate(
    request: Request,
    service: ServiceDep,
    film_id: UUID,
) -> RatingAggregate:
    return await service.get_rating_aggregate(film_id)


@router.post("/me/favorites", response_model=FavoriteOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def add_favorite(
    request: Request,
    service: ServiceDep,
    user_id: CurrentUserDep,
    payload: FavoriteIn,
) -> FavoriteOut:
    return await service.add_favorite(user_id, payload.film_id)


@router.delete("/me/favorites", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_favorite(
    request: Request,
    service: ServiceDep,
    user_id: CurrentUserDep,
    payload: FavoriteIn,
) -> Response:
    await service.delete_favorite(user_id, payload.film_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me/favorites", response_model=FavoritesListOut)
@limiter.limit("10/minute")
async def list_favorites(
    request: Request,
    service: ServiceDep,
    user_id: CurrentUserDep,
    limit: int = 20,
    offset: int = 0,
) -> FavoritesListOut:
    return await service.list_favorites(user_id, limit=limit, offset=offset)
