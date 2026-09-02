"""Data models for retrieval, scoring, and hybrid search responses."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    """An individual retrieved chunk with relevance scoring and origin metadata."""

    chunk_id: str
    document_id: str
    text: str
    score: float = Field(..., description="Relevance score (higher is more relevant)")
    page_number: Optional[int] = None
    filename: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: str = Field(default="dense", description="Search mechanism: dense, sparse, hybrid, or reranked")


class RetrievalRequest(BaseModel):
    """Query and parameters for hybrid retrieval."""

    query: str = Field(..., min_length=1, description="Natural language search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to return")
    dense_weight: float = Field(default=0.7, ge=0.0, le=1.0, description="Weight given to dense retrieval")
    sparse_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="Weight given to lexical retrieval")
    document_id: Optional[str] = Field(default=None, description="Optional document ID filter")
    enable_reranking: bool = Field(default=True, description="Whether to apply neural reranking to candidates")


class RetrievalResponse(BaseModel):
    """Standard response containing ranked chunks and retrieval telemetry."""

    query: str
    results: List[RetrievedChunk]
    total_found: int
    dense_candidates_count: int = 0
    sparse_candidates_count: int = 0
    reranked: bool = False
