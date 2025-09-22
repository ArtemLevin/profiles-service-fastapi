"""Pydantic schemas for the profile service API."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ProfileCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    phone: str
    marketing_opt_in: bool = False


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    phone: Optional[str] = None
    marketing_opt_in: Optional[bool] = None


class ProfileOut(BaseModel):
    id: str
    user_id: int
    full_name: str
    phone: str
    marketing_opt_in: bool
    twofa_phone_verified: bool


class RatingPut(BaseModel):
    film_id: UUID
    rating: float

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, value: float) -> float:
        if not (0 <= value <= 10):
            raise ValueError("Rating must be between 0 and 10")
        if (value * 2) % 1 != 0:
            raise ValueError("Rating must be in steps of 0.5")
        return float(value)


class RatingOut(BaseModel):
    rating: float

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, value: float) -> float:
        if not (0 <= value <= 10):
            raise ValueError("Rating must be between 0 and 10")
        if (value * 2) % 1 != 0:
            raise ValueError("Rating must be in steps of 0.5")
        return float(value)


class RatingAggregate(BaseModel):
    avg_rating: float
    ratings_count: int

    def model_post_init(self, __context: object) -> None:  # noqa: D401 (pydantic hook)
        self.avg_rating = round(self.avg_rating, 1)


class FavoriteIn(BaseModel):
    film_id: UUID


class FavoriteOut(BaseModel):
    film_id: UUID
    created_at: str


class FavoritesListOut(BaseModel):
    items: list[FavoriteOut]
    total: int
