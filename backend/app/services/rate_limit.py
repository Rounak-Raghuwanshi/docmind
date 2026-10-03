"""Sliding-window rate limiter: one Redis sorted set per key, updated atomically in Lua."""

import time
import uuid

from redis.asyncio import Redis

from app.errors import RateLimited

_SLIDING_WINDOW = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)
if count < limit then
  redis.call('ZADD', key, now, ARGV[4])
  redis.call('PEXPIRE', key, math.ceil(window * 1000))
  return {1, '0'}
end
local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
return {0, tostring(tonumber(oldest[2]) + window - now)}
"""


async def check_rate_limit(redis: Redis, key: str, limit: int, window_seconds: int) -> None:
    allowed, retry_after = await redis.eval(  # type: ignore[misc]
        _SLIDING_WINDOW,
        1,
        f"rl:{key}",
        str(time.time()),
        str(window_seconds),
        str(limit),
        uuid.uuid4().hex,
    )
    if not int(allowed):
        seconds = max(1, int(float(retry_after) + 0.999))
        raise RateLimited(
            f"Too many requests. Try again in {seconds} seconds.",
            headers={"Retry-After": str(seconds)},
        )
