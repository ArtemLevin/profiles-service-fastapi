from uuid import UUID

from pydantic import BaseModel, Field, field_validator, ValidationError
from typing import Optional

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
    def validate_rating(cls, v):
        if not (0 <= v <= 10):
            raise ValueError("Rating must be between 0 and 10")
        if (v * 2) % 1 != 0:
            raise ValueError("Rating must be in steps of 0.5")
        return float(v)

class RatingOut(BaseModel):
    rating: float

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v):
        if not (0 <= v <= 10):
            raise ValueError("Rating must be between 0 and 10")
        if (v * 2) % 1 != 0:
            raise ValueError("Rating must be in steps of 0.5")
        return float(v)
