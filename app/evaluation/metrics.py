"""RAG evaluation metrics: Recall@K, Context Precision, and Faithfulness."""

from typing import List
from app.guardrails.grounding import verify_grounding


def compute_recall_at_k(
    retrieved_chunk_ids: List[str],
    expected_chunk_ids: List[str],
    k: int = 5,
) -> float:
    """Proportion of relevant chunks successfully retrieved in the top K."""
    if not expected_chunk_ids:
        return 1.0

    top_k = retrieved_chunk_ids[:k]
    hits = len(set(top_k).intersection(set(expected_chunk_ids)))
    return round(hits / len(expected_chunk_ids), 4)


def compute_context_precision(
    retrieved_chunk_ids: List[str],
    expected_chunk_ids: List[str],
    k: int = 5,
) -> float:
    """Mean Average Precision (MAP) rewarding relevant chunks ranked near the top."""
    if not expected_chunk_ids:
        return 1.0

    top_k = retrieved_chunk_ids[:k]
    if not top_k:
        return 0.0

    hits = 0
    score_sum = 0.0

    for rank, chunk_id in enumerate(top_k, start=1):
        if chunk_id in expected_chunk_ids:
            hits += 1
            precision_at_rank = hits / rank
            score_sum += precision_at_rank

    if hits == 0:
        return 0.0

    return round(score_sum / hits, 4)


def compute_faithfulness(
    generated_answer: str,
    context_passages: List[str],
) -> float:
    """Grounding ratio assessing whether claims in generation are supported by retrieved context."""
    if not generated_answer.strip():
        return 0.0

    result = verify_grounding(generation=generated_answer, contexts=context_passages)
    return round(result.grounding_score, 4)
