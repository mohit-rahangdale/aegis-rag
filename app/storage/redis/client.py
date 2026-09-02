"""Redis connection management and client initialization."""

from typing import Optional

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.config.settings import Settings, get_settings

_redis_client: Optional[Redis] = None


def get_redis_client(settings: Optional[Settings] = None) -> Redis:
    """Return a singleton async Redis client."""
    global _redis_client
    if _redis_client is None:
        if settings is None:
            settings = get_settings()

        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=0.2,
            socket_connect_timeout=0.2,
        )
    return _redis_client




async def check_redis_health(client: Optional[Redis] = None) -> bool:
    """Check if Redis responds to PING."""
    try:
        if client is None:
            client = get_redis_client()
        return await client.ping() is True
    except Exception:
        return False


async def close_redis() -> None:
    """Close the active Redis connection."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
