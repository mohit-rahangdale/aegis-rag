"""Hybrid retrieval combining dense semantic search and sparse lexical BM25 via Reciprocal Rank Fusion (RRF)."""

from typing import Dict, List, Optional

from app.retrieval.dense import DenseRetriever
from app.retrieval.models import RetrievedChunk
from app.retrieval.sparse import SparseRetriever


class HybridRetriever:
    """Combines vector similarity and keyword search using Reciprocal Rank Fusion."""

    def __init__(
        self,
        dense_retriever: Optional[DenseRetriever] = None,
        sparse_retriever: Optional[SparseRetriever] = None,
        rrf_k: int = 60,
    ) -> None:
        self.dense = dense_retriever or DenseRetriever()
        self.sparse = sparse_retriever or SparseRetriever()
        self.rrf_k = rrf_k

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3,
        document_id: Optional[str] = None,
        candidate_pool: Optional[List[RetrievedChunk]] = None,
    ) -> List[RetrievedChunk]:
        """Execute hybrid search combining dense and sparse passes."""
        # 1. Retrieve dense candidates (fetch 2x top_k for broad candidate coverage)
        dense_results = await self.dense.retrieve(
            query=query,
            top_k=top_k * 2,
            document_id=document_id,
        )

        # 2. Determine pool for sparse search: use explicit candidate_pool if provided, or dense hits
        pool_for_sparse = candidate_pool if candidate_pool is not None else dense_results
        sparse_results = self.sparse.retrieve(
            query=query,
            top_k=top_k * 2,
            candidate_pool=pool_for_sparse,
        )

        # 3. Reciprocal Rank Fusion (RRF)
        chunk_map: Dict[str, RetrievedChunk] = {}
        rrf_scores: Dict[str, float] = {}

        # Dense rank scoring
        for rank, chunk in enumerate(dense_results, start=1):
            chunk_map[chunk.chunk_id] = chunk
            score = dense_weight / (self.rrf_k + rank)
            rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0.0) + score

        # Sparse rank scoring
        for rank, chunk in enumerate(sparse_results, start=1):
            chunk_map[chunk.chunk_id] = chunk
            score = sparse_weight / (self.rrf_k + rank)
            rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0.0) + score

        # 4. Normalize RRF scores and build unified result list
        max_rrf = max(rrf_scores.values()) if rrf_scores else 1.0
        sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

        final_chunks: List[RetrievedChunk] = []
        for cid in sorted_chunk_ids[:top_k]:
            original = chunk_map[cid]
            normalized_score = round(rrf_scores[cid] / max_rrf, 4)
            final_chunks.append(
                original.model_copy(
                    update={
                        "score": normalized_score,
                        "source": "hybrid",
                    }
                )
            )

        return final_chunks
