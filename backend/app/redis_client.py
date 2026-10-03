from functools import lru_cache

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings
from redis.asyncio import Redis

from app.config import get_settings


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=True, health_check_interval=30)


def arq_redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


class _ArqPool:
    pool: ArqRedis | None = None


async def get_arq() -> ArqRedis:
    if _ArqPool.pool is None:
        _ArqPool.pool = await create_pool(arq_redis_settings())
    return _ArqPool.pool


async def close_redis() -> None:
    await get_redis().aclose()
    if _ArqPool.pool is not None:
        await _ArqPool.pool.aclose()
        _ArqPool.pool = None
