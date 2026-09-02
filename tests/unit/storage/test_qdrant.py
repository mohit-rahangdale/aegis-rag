"""Unit tests for Qdrant client and collection management using in-memory engine."""

import pytest
from qdrant_client import AsyncQdrantClient

from app.storage.qdrant.collections import QdrantCollectionManager


@pytest.fixture
def in_memory_qdrant():
    """Create an in-memory AsyncQdrantClient for hermetic testing."""
    return AsyncQdrantClient(":memory:")


@pytest.mark.anyio
async def test_qdrant_collection_lifecycle(in_memory_qdrant: AsyncQdrantClient):
    """Verify creating, querying, and deleting collections in Qdrant."""
    manager = QdrantCollectionManager(
        client=in_memory_qdrant,
        default_collection="test_vectors",
        default_vector_size=384,
    )

    # Initially collection should not exist
    exists = await manager.collection_exists("test_vectors")
    assert exists is False

    # Ensure/create collection
    created = await manager.ensure_collection("test_vectors", vector_size=384, distance="cosine")
    assert created is True

    # Now it exists
    exists_now = await manager.collection_exists("test_vectors")
    assert exists_now is True

    # Check collection info
    info = await manager.get_collection_info("test_vectors")
    assert info is not None
    assert info["name"] == "test_vectors"

    # Delete collection
    deleted = await manager.delete_collection("test_vectors")
    assert deleted is True

    # Ensure gone
    assert await manager.collection_exists("test_vectors") is False


@pytest.mark.anyio
async def test_qdrant_health_check(in_memory_qdrant: AsyncQdrantClient):
    """Verify Qdrant health check returns True."""
    manager = QdrantCollectionManager(client=in_memory_qdrant)
    assert await manager.is_healthy() is True
