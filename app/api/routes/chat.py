"""Chat endpoint executing Corrective RAG agent with memory and safety guardrails."""

import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import run_crag_pipeline
from app.db.session import get_db

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    """User prompt and session parameters for chat interaction."""

    message: str = Field(..., min_length=1, description="User question or query")
    conversation_id: Optional[str] = Field(default=None, description="Existing conversation UUID")


class ChatResponse(BaseModel):
    """Grounded assistant response with citations and execution telemetry."""

    conversation_id: str
    response: str
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    is_grounded: bool = True
    is_safe: bool = True
    iterations: int = 0
    token_usage: Dict[str, int] = Field(default_factory=dict)
    latency_ms: float = 0.0


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Agentic Chat Interaction",
    description=(
        "Interact with AegisRAG agent. Executes prompt injection screening, hybrid retrieval, "
        "relevance grading, query reformulation if needed, grounded generation, and memory persistence."
    ),
)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Execute Corrective RAG interaction turn."""
    start_time = time.perf_counter()

    state = await run_crag_pipeline(
        query=request.message,
        conversation_id=request.conversation_id,
        db_session=db,
    )

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    is_safe = state.get("safety_refusal") is None

    return ChatResponse(
        conversation_id=state["conversation_id"],
        response=state.get("generation", ""),
        citations=state.get("citations", []),
        is_grounded=state.get("is_grounded", False),
        is_safe=is_safe,
        iterations=state.get("iteration", 0),
        token_usage=state.get("token_usage", {}),
        latency_ms=elapsed_ms,
    )
