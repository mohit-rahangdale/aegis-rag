"""Unit tests for Redis storage client and RedisService."""

import json
import pytest

from app.storage.redis.service import RedisService


class MockAsyncRedis:
    """Lightweight in-memory fake Redis for unit testing."""

    def __init__(self) -> None:
        self._store = {}

    async def get(self, key: str):
        return self._store.get(key)

    async def set(self, key: str, value: str):
        self._store[key] = str(value)
        return True

    async def setex(self, key: str, time: int, value: str):
        self._store[key] = str(value)
        return True

    async def delete(self, *keys: str):
        count = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                count += 1
        return count

    async def exists(self, *keys: str):
        return sum(1 for k in keys if k in self._store)

    async def ping(self):
        return True


@pytest.mark.anyio
async def test_redis_service_key_value():
    """Verify basic set, get, and exists operations."""
    fake_redis = MockAsyncRedis()
    service = RedisService(client=fake_redis)

    await service.set("test_key", "hello_aegis")
    val = await service.get("test_key")
    assert val == "hello_aegis"

    exists = await service.exists("test_key")
    assert exists is True

    deleted = await service.delete("test_key")
    assert deleted is True

    missing = await service.get("test_key")
    assert missing is None


@pytest.mark.anyio
async def test_redis_service_json_serialization():
    """Verify JSON serialization and deserialization."""
    fake_redis = MockAsyncRedis()
    service = RedisService(client=fake_redis)

    payload = {"conversation_id": "conv-1", "messages": ["hi", "hello"]}
    await service.set_json("conv:conv-1", payload)

    retrieved = await service.get_json("conv:conv-1")
    assert retrieved == payload
    assert retrieved["conversation_id"] == "conv-1"


@pytest.mark.anyio
async def test_redis_service_health():
    """Verify health check returns True when ping succeeds."""
    fake_redis = MockAsyncRedis()
    service = RedisService(client=fake_redis)
    assert await service.is_healthy() is True
