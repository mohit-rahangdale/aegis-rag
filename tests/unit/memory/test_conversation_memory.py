"""Unit tests for ConversationRepository and ConversationMemoryManager."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.repositories.conversation import ConversationRepository
from app.db.session import Base
from app.memory.manager import ConversationMemoryManager
from app.storage.redis.service import RedisService
from tests.unit.storage.test_redis import MockAsyncRedis


@pytest.fixture
async def async_session():
    """Provide isolated in-memory SQLite session with all tables."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.anyio
async def test_conversation_repository_crud(async_session: AsyncSession):
    """Verify creating conversations, adding messages, and querying history."""
    repo = ConversationRepository(async_session)

    # Create conversation
    conv = await repo.create_conversation(title="Test Chat")
    await async_session.commit()
    assert conv.id is not None
    assert conv.title == "Test Chat"

    # Add message
    msg = await repo.add_message(
        conversation_id=conv.id,
        role="user",
        content="Hello AegisRAG!",
    )
    await async_session.commit()
    assert msg.id is not None
    assert msg.role == "user"

    # Get conversation with messages
    fetched = await repo.get_conversation(conv.id)
    assert fetched is not None
    assert len(fetched.messages) == 1
    assert fetched.messages[0].content == "Hello AegisRAG!"

    # Delete conversation
    deleted = await repo.delete_conversation(conv.id)
    await async_session.commit()
    assert deleted is True

    # Verify deleted
    after_del = await repo.get_conversation(conv.id)
    assert after_del is None


@pytest.mark.anyio
async def test_memory_manager_redis_caching_and_persistence(async_session: AsyncSession):
    """Verify ConversationMemoryManager caches to Redis and writes to PostgreSQL."""
    fake_redis = MockAsyncRedis()
    redis_service = RedisService(client=fake_redis)
    memory = ConversationMemoryManager(
        db_session=async_session,
        redis_service=redis_service,
    )

    conv_id = "test-conv-123"

    # Record first turn
    await memory.record_turn(
        conversation_id=conv_id,
        user_content="What is RAG?",
        assistant_content="Retrieval-Augmented Generation.",
    )
    await async_session.commit()

    # Verify Redis cache has the turn
    history = await memory.get_recent_history(conv_id)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "What is RAG?"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Retrieval-Augmented Generation."

    # Clear conversation
    cleared = await memory.clear_conversation(conv_id)
    await async_session.commit()
    assert cleared is True

    # History after clear should be empty
    history_after = await memory.get_recent_history(conv_id)
    assert len(history_after) == 0
