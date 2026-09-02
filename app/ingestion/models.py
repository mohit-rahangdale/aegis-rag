"""Data models for document ingestion, chunking, and indexing."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    """Represents an individual text chunk extracted from a document."""

    chunk_id: str = Field(..., description="Unique chunk identifier")
    document_id: str = Field(..., description="Parent document identifier")
    chunk_index: int = Field(..., ge=0, description="Sequential index of the chunk")
    text: str = Field(..., min_length=1, description="Textual content of the chunk")
    page_number: Optional[int] = Field(default=None, ge=1, description="Page number if applicable")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk-level metadata")
    embedding: Optional[List[float]] = Field(default=None, description="Vector embedding values")


class IngestionResult(BaseModel):
    """Result summary of a completed or skipped ingestion task."""

    document_id: str
    filename: str
    status: str
    checksum: str
    chunk_count: int
    file_size_bytes: int
    is_duplicate: bool = False
    error: Optional[str] = None
