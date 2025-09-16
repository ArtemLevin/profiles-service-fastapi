from redis.asyncio import Redis
from fastapi import Depends
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from .models import Rating
from .schemas import RatingAggregate
from .db import get_session
from .settings import settings

REDIS_URL = f"redis://{settings.redis_host}:{settings.redis_port}/0"
REDIS_TTL = 300

async def get_redis():
    redis = Redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    try:
        yield redis
    finally:
        await redis.close()

async def get_rating_aggregate(
    film_id: UUID,
    session: AsyncSession = Depends(get_session),
    redis = Depends(get_redis)
):
    key = f"rating_agg:{film_id}"
    cached = await redis.get(key)
    if cached:
        avg_rating, ratings_count = map(float, cached.split(":"))
        return RatingAggregate(avg_rating=avg_rating, ratings_count=int(ratings_count))
    res = await session.execute(
        select(func.avg(Rating.rating), func.count()).where(Rating.film_id == film_id)
    )
    avg_rating, ratings_count = res.first()
    await redis.set(key, f"{avg_rating or 0}:{ratings_count}", ex=REDIS_TTL)
    return RatingAggregate(avg_rating=avg_rating or 0, ratings_count=ratings_count or 0)

async def invalidate_rating_aggregate_cache(film_id: UUID, redis):
    key = f"rating_agg:{film_id}"
    await redis.delete(key)
