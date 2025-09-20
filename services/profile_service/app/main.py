from uuid import UUID

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, desc, func
import json
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from redis.asyncio import Redis

from .db import Base, engine, get_session
from .models import Profile, Rating, Favorite, AuditLog
from .schemas import ProfileCreate, ProfileUpdate, ProfileOut, RatingPut, RatingOut, \
    RatingAggregate, FavoriteIn, FavoriteOut, FavoritesListOut
from .settings import settings
from .security import decode_jwt
from .crypto import CryptoBox, normalize_e164, phone_hash
from .rating_cache import get_rating_aggregate as cached_rating_aggregate, invalidate_rating_aggregate_cache, get_redis

app = FastAPI(title="Profile Service", docs_url="/api/profile/openapi", openapi_url="/api/profile/openapi.json")

security = HTTPBearer()
box = CryptoBox(settings.profiles_crypto_key_base64)

limiter = Limiter(key_func=get_remote_address, storage_uri=f"redis://{settings.redis_host}:{settings.redis_port}/0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda request, exc: JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"}))

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/health")
@limiter.limit("10/minute")
async def health(request: Request):
    # Аудит не требуется для health
    return {"status": "OK"}

def current_user_id(token: HTTPAuthorizationCredentials = Depends(security)) -> int:
    try:
        payload = decode_jwt(token.credentials, secret=settings.jwt_secret, alg=settings.jwt_alg)
        sub = payload.get("sub")
        return int(sub)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def is_admin(token: HTTPAuthorizationCredentials = Depends(security)) -> bool:
    try:
        payload = decode_jwt(token.credentials, secret=settings.jwt_secret, alg=settings.jwt_alg)
        return payload.get("role") == "admin"
    except Exception:
        return False

async def log_audit(session: AsyncSession, profile_id, user_id, action, details=None):
    log = AuditLog(profile_id=profile_id, user_id=user_id, action=action, details=json.dumps(details) if details else None)
    session.add(log)
    await session.commit()

def _profile_to_out(p: Profile) -> ProfileOut:
    phone_plain = box.decrypt(p.phone_e164_enc).decode("utf-8")
    return ProfileOut(
        id=str(p.id),
        user_id=p.user_id,
        full_name=p.full_name,
        phone=phone_plain,
        marketing_opt_in=p.marketing_opt_in,
        twofa_phone_verified=p.twofa_phone_verified,
    )

@app.get("/api/profile/me", response_model=ProfileOut)
@limiter.limit("10/minute")
async def get_me(request: Request, user_id: int = Depends(current_user_id), session: AsyncSession = Depends(get_session), admin: bool = Depends(is_admin)):
    res = await session.execute(select(Profile).where(Profile.user_id == user_id))
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    await log_audit(session, profile.id, user_id, "profile_view", {"by": "admin" if admin else "owner"})
    return _profile_to_out(profile)

@app.post("/api/profile", response_model=ProfileOut, status_code=201)
@limiter.limit("10/minute")
async def create_profile(request: Request, payload: ProfileCreate, user_id: int = Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Profile).where(Profile.user_id == user_id))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Profile already exists")

    try:
        e164 = normalize_e164(payload.phone)
    except Exception:
        raise HTTPException(status_code=422, detail="Phone is invalid")
    h = phone_hash(e164, settings.phone_hash_pepper)

    res = await session.execute(select(Profile).where(Profile.phone_hash == h))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Phone already in use")

    enc = box.encrypt(e164.encode("utf-8"))

    p = Profile(
        user_id=user_id,
        full_name=payload.full_name,
        phone_e164_enc=enc,
        phone_hash=h,
        marketing_opt_in=payload.marketing_opt_in,
    )
    session.add(p)
    await session.commit()
    await session.refresh(p)
    await log_audit(session, p.id, user_id, "profile_create", {"payload": payload.model_dump()})
    return _profile_to_out(p)

@app.put("/api/profile", response_model=ProfileOut)
@limiter.limit("10/minute")
async def update_profile(request: Request, payload: ProfileUpdate, user_id: int = Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Profile).where(Profile.user_id == user_id))
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")

    updates = {}
    if payload.full_name is not None:
        updates["full_name"] = payload.full_name
    if payload.marketing_opt_in is not None:
        updates["marketing_opt_in"] = payload.marketing_opt_in
    if payload.phone is not None:
        try:
            e164 = normalize_e164(payload.phone)
        except Exception:
            raise HTTPException(status_code=422, detail="Phone is invalid")
        h = phone_hash(e164, settings.phone_hash_pepper)
        res = await session.execute(select(Profile).where(Profile.phone_hash == h, Profile.user_id != user_id))
        if res.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Phone already in use")
        updates["phone_e164_enc"] = box.encrypt(e164.encode("utf-8"))
        updates["phone_hash"] = h

    if not updates:
        return _profile_to_out(p)

    await session.execute(
        update(Profile).where(Profile.user_id == user_id).values(**updates)
    )
    await session.commit()
    await session.refresh(p)
    await log_audit(session, p.id, user_id, "profile_update", {"payload": payload.model_dump()})
    return _profile_to_out(p)

@app.delete("/api/profile", status_code=204)
@limiter.limit("10/minute")
async def delete_profile(request: Request, user_id: int = Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Profile).where(Profile.user_id == user_id))
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    await session.execute(delete(Profile).where(Profile.user_id == user_id))
    await session.commit()
    await log_audit(session, p.id, user_id, "profile_delete", None)
    return

@app.get("/api/profile/me/ratings", response_model=RatingOut, status_code=200)
@limiter.limit("10/minute")
async def get_rating(request: Request, film_id: UUID, user_id: int = Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Profile).where(Profile.user_id == user_id))
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    res = await session.execute(
        select(Rating).where(
            Rating.profile_id == profile.id,
            Rating.film_id == film_id
        )
    )

    rating = res.scalar_one_or_none()

    await log_audit(session, profile.id, user_id, "rating_get", {"film_id": str(film_id)})
    if rating:
        return RatingOut(rating=rating.rating)
    else:
        raise HTTPException(status_code=404, detail="Rating not found")

@app.put("/api/profile/me/ratings", response_model=RatingOut, status_code=200)
@limiter.limit("10/minute")
async def put_rating(request: Request, payload: RatingPut, user_id: int = Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Profile).where(Profile.user_id == user_id))
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    res = await session.execute(
        select(Rating).where(
            Rating.profile_id == profile.id,
            Rating.film_id == payload.film_id
        )
    )
    rating = res.scalar_one_or_none()

    redis = await Redis.from_url("redis://localhost:6379/0", encoding="utf-8", decode_responses=True)
    try:
        if rating:
            rating.rating = payload.rating
            await session.commit()
            await session.refresh(rating)
            r = rating
        else:
            r = Rating(
                profile_id=profile.id,
                film_id=payload.film_id,
                rating=payload.rating
            )
            session.add(r)
            await session.commit()
            await session.refresh(r)
        await invalidate_rating_aggregate_cache(payload.film_id, redis)
    finally:
        await redis.close()
    await log_audit(session, profile.id, user_id, "rating_put", {"film_id": str(payload.film_id), "rating": payload.rating})
    return RatingOut(rating=r.rating)

@app.get("/api/profile/public/films/{film_id}/rating-agg", response_model=RatingAggregate, status_code=200)
@limiter.limit("10/minute")
async def get_rating_aggregate(request: Request, film_id: UUID, session: AsyncSession = Depends(get_session)):
    # Аудит не требуется для публичной агрегации
    redis = await Redis.from_url("redis://localhost:6379/0", encoding="utf-8", decode_responses=True)
    try:
        return await cached_rating_aggregate(film_id, session, redis)
    finally:
        await redis.close()

@app.post("/api/profile/me/favorites", response_model=FavoriteOut, status_code=201)
@limiter.limit("10/minute")
async def add_favorite(request: Request, payload: FavoriteIn, user_id: int = Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Profile).where(Profile.user_id == user_id))
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    fav = await session.get(Favorite, {"profile_id": profile.id, "film_id": payload.film_id})
    if fav:
        await log_audit(session, profile.id, user_id, "favorite_add_idempotent", {"film_id": str(payload.film_id)})
        return FavoriteOut(film_id=fav.film_id, created_at=str(fav.created_at))
    fav = Favorite(profile_id=profile.id, film_id=payload.film_id)
    session.add(fav)
    await session.commit()
    await session.refresh(fav)
    await log_audit(session, profile.id, user_id, "favorite_add", {"film_id": str(payload.film_id)})
    return FavoriteOut(film_id=fav.film_id, created_at=str(fav.created_at))

@app.delete("/api/profile/me/favorites", status_code=204)
@limiter.limit("10/minute")
async def delete_favorite(request: Request, payload: FavoriteIn, user_id: int = Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Profile).where(Profile.user_id == user_id))
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    fav = await session.get(Favorite, {"profile_id": profile.id, "film_id": payload.film_id})
    if fav:
        await session.delete(fav)
        await session.commit()
        await log_audit(session, profile.id, user_id, "favorite_delete", {"film_id": str(payload.film_id)})
    else:
        await log_audit(session, profile.id, user_id, "favorite_delete_idempotent", {"film_id": str(payload.film_id)})
    return

@app.get("/api/profile/me/favorites", response_model=FavoritesListOut)
@limiter.limit("10/minute")
async def list_favorites(request: Request, limit: int = 20, offset: int = 0, user_id: int = Depends(current_user_id), session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Profile).where(Profile.user_id == user_id))
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    total = await session.scalar(select(func.count()).where(Favorite.profile_id == profile.id))
    res = await session.execute(
        select(Favorite)
        .where(Favorite.profile_id == profile.id)
        .order_by(desc(Favorite.created_at))
        .offset(offset)
        .limit(limit)
    )
    items = [FavoriteOut(film_id=f.film_id, created_at=str(f.created_at)) for f in res.scalars().all()]
    await log_audit(session, profile.id, user_id, "favorite_list", {"limit": limit, "offset": offset})
    return FavoritesListOut(items=items, total=total)


