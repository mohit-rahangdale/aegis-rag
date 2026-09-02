"""Unit tests for passage reranker."""

from app.retrieval.models import RetrievedChunk
from app.retrieval.reranker import Reranker


def test_reranker_promotes_relevant_passage():
    """Verify reranker elevates passage with exact query match to top rank."""
    candidates = [
        RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            text="Unrelated text about weather in Seattle.",
            score=0.9,
            source="dense",
        ),
        RetrievedChunk(
            chunk_id="c2",
            document_id="d1",
            text="AegisRAG features multi-LLM failover to Mistral when Gemini fails.",
            score=0.4,
            source="dense",
        ),
    ]

    reranker = Reranker()
    reranked = reranker.rerank(
        query="multi-LLM failover to Mistral",
        candidates=candidates,
        top_k=2,
    )

    assert len(reranked) == 2
    # c2 should be promoted to #1 because of exact phrase match
    assert reranked[0].chunk_id == "c2"
    assert reranked[0].source == "reranked"
    assert reranked[0].score > reranked[1].score


def test_reranker_empty():
    """Verify reranker gracefully handles empty candidate list."""
    reranker = Reranker()
    assert reranker.rerank(query="anything", candidates=[]) == []
