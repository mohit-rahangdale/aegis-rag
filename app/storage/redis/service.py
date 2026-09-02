"""Key-value and JSON caching service using Redis."""

import json
from typing import Any, Optional

from redis.asyncio import Redis

from app.storage.redis.client import check_redis_health, get_redis_client


class RedisService:
    """Convenient async wrapper around Redis for caching and temporary state."""

    def __init__(self, client: Optional[Redis] = None) -> None:
        self._client = client

    @property
    def client(self) -> Redis:
        """Return the Redis client instance."""
        if self._client is None:
            self._client = get_redis_client()
        return self._client

    async def get(self, key: str) -> Optional[str]:
        """Fetch a string value by key."""
        return await self.client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """Store a string value with optional expiration in seconds."""
        if ttl_seconds:
            return bool(await self.client.setex(key, ttl_seconds, value))
        return bool(await self.client.set(key, value))

    async def get_json(self, key: str) -> Optional[Any]:
        """Fetch and deserialize a JSON object by key."""
        raw = await self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def set_json(
        self,
        key: str,
        data: Any,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """Serialize and store an object as JSON."""
        payload = json.dumps(data)
        return await self.set(key, payload, ttl_seconds=ttl_seconds)

    async def delete(self, key: str) -> bool:
        """Delete a key."""
        return bool(await self.client.delete(key))

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        return bool(await self.client.exists(key))

    async def is_healthy(self) -> bool:
        """Check connection health."""
        return await check_redis_health(self.client)
