import pytest
from redis.asyncio import Redis

@pytest.fixture(scope="session")
async def redis():
    redis = Redis.from_url("redis://localhost:6379/0", encoding="utf-8", decode_responses=True)
    await redis.flushdb()  # Очищаем БД перед тестами
    yield redis
    await redis.close()
