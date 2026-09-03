"""State definition for Corrective RAG (CRAG) agentic state graph."""

from typing import Any, Dict, List, Optional, TypedDict
from app.retrieval.models import RetrievedChunk


class CRAGState(TypedDict):
    """Execution state passed between nodes in the Corrective RAG state graph."""

    query: str
    rewritten_query: Optional[str]
    conversation_id: str
    history: List[Dict[str, str]]
    documents: List[RetrievedChunk]
    relevant_documents: List[RetrievedChunk]
    generation: str
    citations: List[Dict[str, Any]]
    is_grounded: bool
    safety_refusal: Optional[str]
    fast_path_response: Optional[str]
    iteration: int

    max_iterations: int
    token_usage: Dict[str, int]
    error: Optional[str]
