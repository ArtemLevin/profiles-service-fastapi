from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class Film(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    rating: Optional[float] = None


class Genre(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None


class Person(BaseModel):
    id: UUID
    full_name: str
