"""Retrieval search endpoint executing hybrid retrieval and reranking."""

from fastapi import APIRouter, status

from app.retrieval.hybrid import HybridRetriever
from app.retrieval.models import RetrievalRequest, RetrievalResponse
from app.retrieval.reranker import Reranker

router = APIRouter(prefix="/retrieval", tags=["Retrieval"])


@router.post(
    "/search",
    response_model=RetrievalResponse,
    status_code=status.HTTP_200_OK,
    summary="Hybrid Retrieval Search",
    description="Execute combined dense vector similarity and sparse BM25 retrieval with optional neural reranking.",
)
async def search(request: RetrievalRequest) -> RetrievalResponse:
    """Execute hybrid search pipeline across indexed documents."""
    hybrid = HybridRetriever()
    reranker = Reranker()

    # 1. Hybrid retrieval (Dense + Sparse with RRF)
    chunks = await hybrid.retrieve(
        query=request.query,
        top_k=request.top_k,
        dense_weight=request.dense_weight,
        sparse_weight=request.sparse_weight,
        document_id=request.document_id,
    )

    # 2. Contextual reranking if enabled
    reranked = False
    if request.enable_reranking and chunks:
        chunks = reranker.rerank(
            query=request.query,
            candidates=chunks,
            top_k=request.top_k,
        )
        reranked = True

    return RetrievalResponse(
        query=request.query,
        results=chunks,
        total_found=len(chunks),
        reranked=reranked,
    )
