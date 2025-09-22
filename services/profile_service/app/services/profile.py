"""Business logic for working with profiles and related entities."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Sequence
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import (
    InvalidPhoneError,
    PhoneAlreadyInUseError,
    ProfileAlreadyExistsError,
    ProfileNotFoundError,
    RatingNotFoundError,
)
from ..crypto import CryptoBox, normalize_e164, phone_hash
from ..models import Favorite, Profile, Rating
from ..repositories.audit import AuditLogRepository
from ..repositories.favorites import FavoriteRepository
from ..repositories.profiles import ProfileRepository
from ..repositories.ratings import RatingRepository
from ..schemas import FavoriteOut, FavoritesListOut, ProfileOut, RatingAggregate, RatingOut


@dataclass(slots=True)
class ProfileService:
    """Encapsulates business operations for profile management."""

    session: AsyncSession
    redis: Redis
    crypto_box: CryptoBox
    phone_pepper: str
    rating_cache_ttl: int
    _profiles: ProfileRepository = field(init=False)
    _ratings: RatingRepository = field(init=False)
    _favorites: FavoriteRepository = field(init=False)
    _audit: AuditLogRepository = field(init=False)

    def __post_init__(self) -> None:
        self._profiles = ProfileRepository(self.session)
        self._ratings = RatingRepository(self.session)
        self._favorites = FavoriteRepository(self.session)
        self._audit = AuditLogRepository(self.session)

    async def get_profile(self, user_id: int, *, actor_is_admin: bool) -> ProfileOut:
        profile = await self._get_profile_or_raise(user_id)
        await self._audit.log(
            profile_id=profile.id,
            user_id=user_id,
            action="profile_view",
            details={"by": "admin" if actor_is_admin else "owner"},
        )
        await self.session.commit()
        return self._to_profile_out(profile)

    async def create_profile(self, user_id: int, payload: dict[str, Any]) -> ProfileOut:
        if await self._profiles.get_by_user_id(user_id):
            raise ProfileAlreadyExistsError()

        phone_e164, encrypted, phone_digest = await self._prepare_phone(payload["phone"])
        profile = Profile(
            user_id=user_id,
            full_name=payload["full_name"],
            phone_e164_enc=encrypted,
            phone_hash=phone_digest,
            marketing_opt_in=payload.get("marketing_opt_in", False),
        )
        await self._profiles.add(profile)
        await self._audit.log(
            profile_id=profile.id,
            user_id=user_id,
            action="profile_create",
            details={"payload": payload},
        )
        await self.session.commit()
        await self.session.refresh(profile)
        return self._to_profile_out(profile)

    async def update_profile(self, user_id: int, payload: dict[str, Any]) -> ProfileOut:
        profile = await self._get_profile_or_raise(user_id)

        updates: dict[str, Any] = {}
        if payload.get("full_name") is not None:
            updates["full_name"] = payload["full_name"]
        if payload.get("marketing_opt_in") is not None:
            updates["marketing_opt_in"] = payload["marketing_opt_in"]
        if payload.get("phone") is not None:
            _, encrypted, phone_digest = await self._prepare_phone(
                payload["phone"], exclude_profile_id=profile.id
            )
            updates["phone_e164_enc"] = encrypted
            updates["phone_hash"] = phone_digest

        if updates:
            await self._profiles.update(profile, updates)
            await self._audit.log(
                profile_id=profile.id,
                user_id=user_id,
                action="profile_update",
                details={"payload": payload},
            )
            await self.session.commit()
            await self.session.refresh(profile)
        return self._to_profile_out(profile)

    async def delete_profile(self, user_id: int) -> None:
        profile = await self._get_profile_or_raise(user_id)
        await self._profiles.delete(profile)
        await self._audit.log(profile_id=profile.id, user_id=user_id, action="profile_delete")
        await self.session.commit()

    async def get_rating(self, user_id: int, film_id: UUID) -> RatingOut:
        profile = await self._get_profile_or_raise(user_id)
        rating = await self._ratings.get(profile.id, film_id)
        if not rating:
            raise RatingNotFoundError()

        await self._audit.log(
            profile_id=profile.id,
            user_id=user_id,
            action="rating_get",
            details={"film_id": str(film_id)},
        )
        await self.session.commit()
        return RatingOut(rating=rating.rating)

    async def put_rating(self, user_id: int, payload: dict[str, Any]) -> RatingOut:
        profile = await self._get_profile_or_raise(user_id)
        rating = await self._ratings.get(profile.id, payload["film_id"])
        if rating:
            rating.rating = payload["rating"]
            await self.session.flush()
        else:
            rating = Rating(
                profile_id=profile.id,
                film_id=payload["film_id"],
                rating=payload["rating"],
            )
            await self._ratings.add(rating)

        await self._audit.log(
            profile_id=profile.id,
            user_id=user_id,
            action="rating_put",
            details={"film_id": str(payload["film_id"]), "rating": payload["rating"]},
        )
        await self.session.commit()
        await self.session.refresh(rating)
        await self._invalidate_rating_cache(payload["film_id"])
        return RatingOut(rating=rating.rating)

    async def get_rating_aggregate(self, film_id: UUID) -> RatingAggregate:
        cached = await self.redis.get(self._rating_cache_key(film_id))
        if cached:
            try:
                return RatingAggregate.model_validate(json.loads(cached))
            except (TypeError, ValueError):
                pass

        avg_rating, ratings_count = await self._ratings.aggregate_for_film(film_id)
        aggregate = RatingAggregate(
            avg_rating=float(avg_rating or 0),
            ratings_count=int(ratings_count or 0),
        )
        await self.redis.set(
            self._rating_cache_key(film_id),
            aggregate.model_dump_json(),
            ex=self.rating_cache_ttl,
        )
        return aggregate

    async def add_favorite(self, user_id: int, film_id: UUID) -> FavoriteOut:
        profile = await self._get_profile_or_raise(user_id)
        favorite = await self._favorites.get(profile.id, film_id)
        if not favorite:
            favorite = Favorite(profile_id=profile.id, film_id=film_id)
            await self._favorites.add(favorite)
            action = "favorite_add"
        else:
            action = "favorite_add_idempotent"

        await self._audit.log(
            profile_id=profile.id,
            user_id=user_id,
            action=action,
            details={"film_id": str(film_id)},
        )
        await self.session.commit()
        await self.session.refresh(favorite)
        return FavoriteOut(film_id=favorite.film_id, created_at=str(favorite.created_at))

    async def delete_favorite(self, user_id: int, film_id: UUID) -> None:
        profile = await self._get_profile_or_raise(user_id)
        favorite = await self._favorites.get(profile.id, film_id)
        action = "favorite_delete"
        if favorite:
            await self._favorites.delete(favorite)
        else:
            action = "favorite_delete_idempotent"

        await self._audit.log(
            profile_id=profile.id,
            user_id=user_id,
            action=action,
            details={"film_id": str(film_id)},
        )
        await self.session.commit()

    async def list_favorites(self, user_id: int, *, limit: int, offset: int) -> FavoritesListOut:
        profile = await self._get_profile_or_raise(user_id)
        items: Sequence[Favorite] = await self._favorites.list_by_profile(
            profile.id, limit=limit, offset=offset
        )
        total = await self._favorites.count_by_profile(profile.id)
        await self._audit.log(
            profile_id=profile.id,
            user_id=user_id,
            action="favorite_list",
            details={"limit": limit, "offset": offset},
        )
        await self.session.commit()
        payload = [
            FavoriteOut(film_id=item.film_id, created_at=str(item.created_at)) for item in items
        ]
        return FavoritesListOut(items=payload, total=total)

    async def _get_profile_or_raise(self, user_id: int) -> Profile:
        profile = await self._profiles.get_by_user_id(user_id)
        if not profile:
            raise ProfileNotFoundError()
        return profile

    async def _prepare_phone(
        self, phone_raw: str, *, exclude_profile_id: Any | None = None
    ) -> tuple[str, bytes, bytes]:
        try:
            e164 = normalize_e164(phone_raw)
        except Exception as exc:  # pragma: no cover - defensive conversions
            raise InvalidPhoneError() from exc

        phone_digest = phone_hash(e164, self.phone_pepper)
        if await self._profiles.phone_in_use(phone_digest, exclude_profile_id=exclude_profile_id):
            raise PhoneAlreadyInUseError()
        encrypted = self.crypto_box.encrypt(e164.encode("utf-8"))
        return e164, encrypted, phone_digest

    async def _invalidate_rating_cache(self, film_id: UUID) -> None:
        await self.redis.delete(self._rating_cache_key(film_id))

    @staticmethod
    def _rating_cache_key(film_id: UUID) -> str:
        return f"rating_agg:{film_id}"

    def _to_profile_out(self, profile: Profile) -> ProfileOut:
        phone_plain = self.crypto_box.decrypt(profile.phone_e164_enc).decode("utf-8")
        return ProfileOut(
            id=str(profile.id),
            user_id=profile.user_id,
            full_name=profile.full_name,
            phone=phone_plain,
            marketing_opt_in=profile.marketing_opt_in,
            twofa_phone_verified=profile.twofa_phone_verified,
        )
