"""Unit tests for end-to-end IngestionPipeline."""

import pytest
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base
from app.ingestion.embeddings import EmbeddingGenerator
from app.ingestion.pipeline import IngestionPipeline
from app.storage.minio.service import MinioStorageService
from app.storage.qdrant.collections import QdrantCollectionManager
from tests.unit.storage.test_minio import MockMinioClient


@pytest.fixture
async def in_memory_db_session():
    """Create async in-memory SQLite session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def test_pipeline(in_memory_db_session: AsyncSession):
    """Build an isolated IngestionPipeline for tests."""
    mock_minio = MinioStorageService(client=MockMinioClient(), default_bucket="test-bucket")
    in_memory_qdrant = AsyncQdrantClient(":memory:")
    qdrant_mgr = QdrantCollectionManager(
        client=in_memory_qdrant,
        default_collection="test_docs",
        default_vector_size=768,
    )
    embedder = EmbeddingGenerator()

    return IngestionPipeline(
        db_session=in_memory_db_session,
        storage_service=mock_minio,
        qdrant_manager=qdrant_mgr,
        embedding_generator=embedder,
        chunk_size=100,
        chunk_overlap=20,
    )


@pytest.mark.anyio
async def test_ingest_document_success_and_deduplication(
    test_pipeline: IngestionPipeline,
    in_memory_db_session: AsyncSession,
):
    """Verify document processing, vector indexing, and subsequent deduplication."""
    content = (
        b"AegisRAG is designed with high reliability in mind.\n\n"
        b"It supports multi-LLM failover, hybrid dense and sparse retrieval,\n\n"
        b"and automated self-correction via LangGraph state machine."
    )

    # 1. First Ingestion
    result1 = await test_pipeline.ingest_document(
        filename="overview.txt",
        content=content,
        content_type="text/plain",
    )
    await in_memory_db_session.commit()

    assert result1.status == "processed"
    assert result1.chunk_count >= 1
    assert result1.is_duplicate is False
    assert result1.document_id is not None

    # Verify Qdrant collection exists and has points
    qdrant_client = test_pipeline.qdrant.client
    collection_name = test_pipeline.settings.qdrant_collection
    count_res = await qdrant_client.count(collection_name=collection_name)
    assert count_res.count == result1.chunk_count

    # 2. Duplicate Ingestion (exact same bytes)
    result2 = await test_pipeline.ingest_document(
        filename="overview_copy.txt",
        content=content,
        content_type="text/plain",
    )
    assert result2.status == "processed"
    assert result2.is_duplicate is True
    assert result2.document_id == result1.document_id
    assert result2.chunk_count == result1.chunk_count
