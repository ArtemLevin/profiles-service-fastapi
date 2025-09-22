"""Database models for the profile service."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(Text)

    phone_e164_enc: Mapped[bytes] = mapped_column(LargeBinary)
    phone_hash: Mapped[bytes] = mapped_column(LargeBinary, unique=True, index=True)

    marketing_opt_in: Mapped[bool] = mapped_column(server_default=text("false"))
    twofa_phone_verified: Mapped[bool] = mapped_column(server_default=text("false"))


    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Rating(Base):
    __tablename__ = "ratings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("profiles.id"), index=True
    )
    film_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), index=True)


    rating: Mapped[float] = mapped_column(Float)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    profile = relationship("Profile")

    __table_args__ = (UniqueConstraint("profile_id", "film_id", name="uix_profile_film"),)


class Favorite(Base):
    __tablename__ = "favorites"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("profiles.id"), primary_key=True
    )
    film_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    __table_args__ = (UniqueConstraint("profile_id", "film_id", name="uix_favorite_profile_film"),)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("profiles.id"))
    user_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(Text)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
