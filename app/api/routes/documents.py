"""Document upload and status inspection endpoints."""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.document import DocumentRepository
from app.db.session import get_db
from app.ingestion.models import IngestionResult
from app.ingestion.pipeline import IngestionPipeline

router = APIRouter(prefix="/documents", tags=["Documents"])

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown"}


class DocumentSummary(BaseModel):
    """Document record overview."""

    id: str
    filename: str
    content_type: str
    file_size_bytes: int
    status: str
    storage_path: Optional[str] = None
    checksum: str
    meta_info: dict = Field(default_factory=dict)
    created_at: str


@router.post(
    "/upload",
    response_model=IngestionResult,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Document",
    description="Upload a PDF, Markdown, or text file for automatic parsing, chunking, and vector indexing.",
)
async def upload_document(
    file: UploadFile = File(..., description="Document file (.pdf, .md, .txt)"),
    db: AsyncSession = Depends(get_db),
) -> IngestionResult:
    """Handle document upload and invoke ingestion pipeline."""
    filename = file.filename or "unnamed_document.txt"
    lower_name = filename.lower()

    # Validate allowed extensions
    if not any(lower_name.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    pipeline = IngestionPipeline(db_session=db)
    result = await pipeline.ingest_document(
        filename=filename,
        content=content,
        content_type=file.content_type or "",
    )

    if result.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.error or "Failed to parse and index document.",
        )

    return result


@router.get(
    "/{document_id}",
    response_model=DocumentSummary,
    summary="Get Document Details",
    description="Fetch processing status, chunk count, and metadata for a specific document ID.",
)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentSummary:
    """Retrieve document status by ID."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UUID format.",
        )

    repo = DocumentRepository(db)
    doc = await repo.get_by_id(doc_uuid)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )

    return DocumentSummary(
        id=str(doc.id),
        filename=doc.filename,
        content_type=doc.content_type,
        file_size_bytes=doc.file_size_bytes,
        status=doc.status,
        storage_path=doc.storage_path,
        checksum=doc.checksum,
        meta_info=doc.meta_info or {},
        created_at=doc.created_at.isoformat(),
    )


@router.get(
    "",
    response_model=List[DocumentSummary],
    summary="List Documents",
    description="List uploaded documents with pagination.",
)
async def list_documents(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[DocumentSummary]:
    """List documents with pagination."""
    repo = DocumentRepository(db)
    docs = await repo.list_documents(limit=limit, offset=offset)
    return [
        DocumentSummary(
            id=str(d.id),
            filename=d.filename,
            content_type=d.content_type,
            file_size_bytes=d.file_size_bytes,
            status=d.status,
            storage_path=d.storage_path,
            checksum=d.checksum,
            meta_info=d.meta_info or {},
            created_at=d.created_at.isoformat(),
        )
        for d in docs
    ]
