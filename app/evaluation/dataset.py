"""Curated golden evaluation dataset for benchmarking AegisRAG retrieval and generation."""

from typing import List
from app.evaluation.models import EvalSample

GOLDEN_EVAL_DATASET: List[EvalSample] = [
    EvalSample(
        id="sample_01",
        query="How does hybrid retrieval combine dense and sparse search in AegisRAG?",
        ground_truth_answer="AegisRAG uses Reciprocal Rank Fusion (RRF) to combine Qdrant dense vector scores with BM25 sparse keyword scores, scoring documents as sum(weight / (60 + rank)).",
        expected_chunk_ids=["chunk_hybrid_01", "chunk_hybrid_02"],
        tags=["retrieval", "hybrid", "architecture"],
    ),
    EvalSample(
        id="sample_02",
        query="What multi-LLM failover strategy does the gateway implement?",
        ground_truth_answer="The gateway uses Google Gemini as the primary provider with automatic failover to Mistral AI via exponential backoff retries and a three-state circuit breaker.",
        expected_chunk_ids=["chunk_gateway_01"],
        tags=["gateway", "resilience"],
    ),
    EvalSample(
        id="sample_03",
        query="What guardrails are implemented to save tokens on routine dialogues?",
        ground_truth_answer="A fast-path dialogue layer matches greetings, thanks, farewells, and help questions directly, returning instant responses with zero token usage.",
        expected_chunk_ids=["chunk_guardrails_01"],
        tags=["guardrails", "token_saving"],
    ),
    EvalSample(
        id="sample_04",
        query="How is conversation memory partitioned between short-term and long-term storage?",
        ground_truth_answer="Short-term recent turns are cached in Redis with sliding TTL for low-latency prompt augmentation, while all messages are durably stored in PostgreSQL.",
        expected_chunk_ids=["chunk_memory_01"],
        tags=["memory", "storage"],
    ),
    EvalSample(
        id="sample_05",
        query="What action does the Corrective RAG (CRAG) state machine take when retrieved documents have low relevance?",
        ground_truth_answer="When retrieved passages fall below the relevance threshold, the state machine invokes query rewriting to reformulate the query and re-retrieves context up to 2 iterations.",
        expected_chunk_ids=["chunk_crag_01"],
        tags=["crag", "agent"],
    ),
]


def load_eval_dataset() -> List[EvalSample]:
    """Load default golden evaluation benchmark dataset."""
    return GOLDEN_EVAL_DATASET
