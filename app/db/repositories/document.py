"""Repository for Document entity persistence and queries."""

from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document, utc_now


class DocumentRepository:
    """Async repository providing CRUD access for Document records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        filename: str,
        content_type: str,
        checksum: str,
        storage_path: str,
        file_size_bytes: int = 0,
        status: str = "uploaded",
        meta_info: Optional[Dict[str, Any]] = None,
        document_id: Optional[str] = None,
    ) -> Document:
        """Create and persist a new Document record."""
        doc = Document(
            filename=filename,
            content_type=content_type,
            checksum=checksum,
            storage_path=storage_path,
            file_size_bytes=file_size_bytes,
            status=status,
            meta_info=meta_info or {},
        )
        if document_id:
            doc.id = document_id

        self.session.add(doc)
        await self.session.flush()
        await self.session.refresh(doc)
        return doc

    async def get_by_id(self, document_id: str) -> Optional[Document]:
        """Retrieve a document by its primary UUID."""
        stmt = select(Document).where(Document.id == document_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_checksum(self, checksum: str) -> Optional[Document]:
        """Look up an existing document by content checksum (for deduplication)."""
        stmt = select(Document).where(Document.checksum == checksum)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        document_id: str,
        status: str,
        meta_updates: Optional[Dict[str, Any]] = None,
    ) -> Optional[Document]:
        """Update processing status and optional metadata for a document."""
        doc = await self.get_by_id(document_id)
        if not doc:
            return None

        doc.status = status
        doc.updated_at = utc_now()
        if meta_updates:
            current_meta = dict(doc.meta_info)
            current_meta.update(meta_updates)
            doc.meta_info = current_meta

        await self.session.flush()
        await self.session.refresh(doc)
        return doc

    async def list_documents(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> List[Document]:
        """List documents with pagination and optional status filter."""
        stmt = select(Document).order_by(Document.created_at.desc()).limit(limit).offset(offset)
        if status:
            stmt = stmt.where(Document.status == status)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, document_id: str) -> bool:
        """Delete a document record by ID."""
        doc = await self.get_by_id(document_id)
        if not doc:
            return False

        await self.session.delete(doc)
        await self.session.flush()
        return True
