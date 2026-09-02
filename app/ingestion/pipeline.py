"""Ingestion pipeline orchestrating storage, chunking, embedding, and vector indexing."""

import hashlib
import uuid
from typing import Any, Dict, List, Optional

from qdrant_client.http import models as qmodels
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.db.repositories.document import DocumentRepository
from app.ingestion.chunking.text_chunker import TextChunker
from app.ingestion.embeddings import EmbeddingGenerator
from app.ingestion.loaders import get_loader_for_file
from app.ingestion.models import DocumentChunk, IngestionResult
from app.storage.minio.service import MinioStorageService
from app.storage.qdrant.collections import QdrantCollectionManager


class IngestionPipeline:
    """End-to-end document processing, embedding, and vector indexing pipeline."""

    def __init__(
        self,
        db_session: AsyncSession,
        storage_service: Optional[MinioStorageService] = None,
        qdrant_manager: Optional[QdrantCollectionManager] = None,
        embedding_generator: Optional[EmbeddingGenerator] = None,
        chunk_size: int = 600,
        chunk_overlap: int = 100,
    ) -> None:
        self.repo = DocumentRepository(db_session)
        self.storage = storage_service or MinioStorageService()
        self.qdrant = qdrant_manager or QdrantCollectionManager()
        self.embedder = embedding_generator or EmbeddingGenerator()
        self.chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.settings = get_settings()

    async def ingest_document(
        self,
        filename: str,
        content: bytes,
        content_type: str = "",
        meta_info: Optional[Dict[str, Any]] = None,
    ) -> IngestionResult:
        """Process and index a document through the entire RAG ingestion pipeline."""
        file_size = len(content)
        checksum = hashlib.sha256(content).hexdigest()
        meta_info = meta_info or {}

        # 1. Deduplication check via SHA-256
        existing_doc = await self.repo.get_by_checksum(checksum)
        if existing_doc and existing_doc.status == "processed":
            chunk_count = existing_doc.meta_info.get("chunk_count", 0) if existing_doc.meta_info else 0
            return IngestionResult(
                document_id=str(existing_doc.id),
                filename=existing_doc.filename,
                status="processed",
                checksum=checksum,
                chunk_count=chunk_count,
                file_size_bytes=file_size,
                is_duplicate=True,
            )

        # 2. Upload raw bytes to MinIO object storage
        storage_key = f"documents/{uuid.uuid4()}_{filename}"
        storage_path = await self.storage.upload_bytes(
            object_name=storage_key,
            data=content,
            content_type=content_type or "application/octet-stream",
        )

        # 3. Create document record in database
        doc_record = await self.repo.create(
            filename=filename,
            content_type=content_type or "application/octet-stream",
            checksum=checksum,
            storage_path=storage_path,
            file_size_bytes=file_size,
            meta_info=meta_info,
        )
        doc_id_str = str(doc_record.id)

        try:
            # 4. Extract text pages / sections
            loader = get_loader_for_file(filename=filename, content_type=content_type)
            extracted_sections = loader.extract_text(content)

            # 5. Split sections into overlapping chunks
            chunks: List[DocumentChunk] = []
            chunk_idx = 0
            for section_text, page_num in extracted_sections:
                raw_chunks = self.chunker.chunk_text(section_text)
                for c_text in raw_chunks:
                    chunk_id = f"{doc_id_str}#c{chunk_idx}"
                    chunk_obj = DocumentChunk(
                        chunk_id=chunk_id,
                        document_id=doc_id_str,
                        chunk_index=chunk_idx,
                        text=c_text,
                        page_number=page_num,
                        metadata={
                            **meta_info,
                            "filename": filename,
                            "page": page_num,
                        },
                    )
                    chunks.append(chunk_obj)
                    chunk_idx += 1

            if not chunks:
                # Document was empty
                await self.repo.update_status(
                    document_id=doc_record.id,
                    status="failed",
                    meta_updates={"error": "Document contains no extractable text"},
                )
                return IngestionResult(
                    document_id=doc_id_str,
                    filename=filename,
                    status="failed",
                    checksum=checksum,
                    chunk_count=0,
                    file_size_bytes=file_size,
                    error="No text extractable from document",
                )

            # 6. Ensure target Qdrant collection exists
            await self.qdrant.ensure_collection(
                collection_name=self.settings.qdrant_collection,
                vector_size=self.settings.qdrant_vector_size,
            )

            # 7. Generate vector embeddings for chunks
            chunk_texts = [c.text for c in chunks]
            embeddings = await self.embedder.embed_texts(chunk_texts)

            # 8. Upsert points into Qdrant
            points = []
            for chunk, emb in zip(chunks, embeddings):
                chunk.embedding = emb
                # Deterministic UUID for Qdrant point from chunk_id
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk.chunk_id))
                payload = {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "page_number": chunk.page_number,
                    "filename": filename,
                    "metadata": chunk.metadata,
                }
                points.append(
                    qmodels.PointStruct(
                        id=point_id,
                        vector=emb,
                        payload=payload,
                    )
                )

            await self.qdrant.client.upsert(
                collection_name=self.settings.qdrant_collection,
                points=points,
            )

            # 9. Mark document processed in database
            await self.repo.update_status(
                document_id=doc_record.id,
                status="processed",
                meta_updates={
                    "chunk_count": len(chunks),
                    "storage_path": storage_path,
                },
            )

            return IngestionResult(
                document_id=doc_id_str,
                filename=filename,
                status="processed",
                checksum=checksum,
                chunk_count=len(chunks),
                file_size_bytes=file_size,
            )

        except Exception as e:
            await self.repo.update_status(
                document_id=doc_record.id,
                status="failed",
                meta_updates={"error": str(e)},
            )
            return IngestionResult(
                document_id=doc_id_str,
                filename=filename,
                status="failed",
                checksum=checksum,
                chunk_count=0,
                file_size_bytes=file_size,
                error=str(e),
            )
