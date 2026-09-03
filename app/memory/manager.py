"""Conversation memory manager combining Redis short-term caching and PostgreSQL long-term persistence."""

from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.conversation import ConversationRepository
from app.storage.redis.service import RedisService


class ConversationMemoryManager:
    """Manages multi-tier conversation memory for fast retrieval and durable auditability."""

    def __init__(
        self,
        db_session: AsyncSession,
        redis_service: Optional[RedisService] = None,
        cache_ttl_seconds: int = 3600,
    ) -> None:
        self.repo = ConversationRepository(db_session)
        self.redis = redis_service or RedisService()
        self.cache_ttl = cache_ttl_seconds

    def _cache_key(self, conversation_id: str) -> str:
        return f"memory:conv:{conversation_id}"

    async def get_recent_history(
        self,
        conversation_id: str,
        limit: int = 10,
    ) -> List[Dict[str, str]]:
        """Retrieve recent message history formatted as role-content dicts."""
        cache_key = self._cache_key(conversation_id)

        # 1. Check Redis short-term cache
        try:
            cached = await self.redis.get_json(cache_key)
            if cached and isinstance(cached, list):
                return cached[-limit:]
        except Exception:
            pass  # Fall back to database on cache issue

        # 2. Cache miss: Fetch from PostgreSQL repository
        db_messages = await self.repo.get_messages(conversation_id, limit=limit)
        history = [{"role": msg.role, "content": msg.content} for msg in db_messages]

        # 3. Populate Redis cache
        if history:
            try:
                await self.redis.set_json(cache_key, history, ttl_seconds=self.cache_ttl)
            except Exception:
                pass

        return history

    async def record_turn(
        self,
        conversation_id: str,
        user_content: str,
        assistant_content: str,
        turn_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persist a user/assistant turn to both PostgreSQL and Redis."""
        meta = turn_metadata or {}

        # Ensure conversation exists in DB
        await self.repo.get_or_create(conversation_id=conversation_id)

        # Persist user message
        await self.repo.add_message(
            conversation_id=conversation_id,
            role="user",
            content=user_content,
        )

        # Persist assistant message
        await self.repo.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
            meta_info=meta,
        )

        # Update Redis cache
        cache_key = self._cache_key(conversation_id)
        try:
            history = await self.get_recent_history(conversation_id, limit=20)
            await self.redis.set_json(cache_key, history, ttl_seconds=self.cache_ttl)
        except Exception:
            pass

    async def clear_conversation(self, conversation_id: str) -> bool:
        """Delete conversation from both Redis and PostgreSQL."""
        cache_key = self._cache_key(conversation_id)
        try:
            await self.redis.delete(cache_key)
        except Exception:
            pass

        return await self.repo.delete_conversation(conversation_id)
