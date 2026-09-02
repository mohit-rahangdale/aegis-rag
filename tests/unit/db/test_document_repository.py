"""Unit tests for Document ORM model and DocumentRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models.document import Document
from app.db.repositories.document import DocumentRepository
from app.db.session import Base


@pytest.fixture
async def async_session():
    """Create an in-memory SQLite async session for repository tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.anyio
async def test_create_and_get_document(async_session: AsyncSession):
    """Verify creating a document record and retrieving it by ID."""
    repo = DocumentRepository(async_session)

    doc = await repo.create(
        filename="rag_paper.pdf",
        content_type="application/pdf",
        checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        storage_path="aegisrag-documents/rag_paper.pdf",
        file_size_bytes=10240,
        meta_info={"author": "Researcher", "pages": 12},
    )
    await async_session.commit()

    assert doc.id is not None
    assert doc.filename == "rag_paper.pdf"
    assert doc.status == "uploaded"

    fetched = await repo.get_by_id(doc.id)
    assert fetched is not None
    assert fetched.filename == "rag_paper.pdf"
    assert fetched.meta_info["pages"] == 12


@pytest.mark.anyio
async def test_get_document_by_checksum(async_session: AsyncSession):
    """Verify looking up document by SHA-256 checksum for deduplication."""
    repo = DocumentRepository(async_session)
    checksum = "abc123checksumvalue"

    await repo.create(
        filename="doc_one.txt",
        content_type="text/plain",
        checksum=checksum,
        storage_path="aegisrag-documents/doc_one.txt",
    )
    await async_session.commit()

    found = await repo.get_by_checksum(checksum)
    assert found is not None
    assert found.filename == "doc_one.txt"

    not_found = await repo.get_by_checksum("non_existent_checksum")
    assert not_found is None


@pytest.mark.anyio
async def test_update_document_status(async_session: AsyncSession):
    """Verify status updates and metadata enrichment."""
    repo = DocumentRepository(async_session)

    doc = await repo.create(
        filename="report.md",
        content_type="text/markdown",
        checksum="unique_checksum_report",
        storage_path="aegisrag-documents/report.md",
    )
    await async_session.commit()

    updated = await repo.update_status(
        document_id=doc.id,
        status="processed",
        meta_updates={"chunks_indexed": 42},
    )
    await async_session.commit()

    assert updated is not None
    assert updated.status == "processed"
    assert updated.meta_info.get("chunks_indexed") == 42


@pytest.mark.anyio
async def test_list_and_delete_documents(async_session: AsyncSession):
    """Verify document pagination and deletion."""
    repo = DocumentRepository(async_session)

    doc1 = await repo.create(
        filename="a.txt",
        content_type="text/plain",
        checksum="sum_a",
        storage_path="path_a",
    )
    doc2 = await repo.create(
        filename="b.txt",
        content_type="text/plain",
        checksum="sum_b",
        storage_path="path_b",
    )
    await async_session.commit()

    docs = await repo.list_documents(limit=10)
    assert len(docs) >= 2

    # Delete doc1
    deleted = await repo.delete(doc1.id)
    await async_session.commit()
    assert deleted is True

    # Ensure doc1 is gone
    check_doc1 = await repo.get_by_id(doc1.id)
    assert check_doc1 is None
