"""Unit tests for RAG evaluation metric computations."""

from app.evaluation.metrics import (
    compute_context_precision,
    compute_faithfulness,
    compute_recall_at_k,
)


def test_compute_recall_at_k():
    """Verify Recall@K accurately computes intersection ratios."""
    expected = ["chunk_1", "chunk_2"]

    # All hits
    assert compute_recall_at_k(["chunk_1", "chunk_2", "chunk_3"], expected, k=3) == 1.0

    # Partial hit
    assert compute_recall_at_k(["chunk_1", "chunk_x", "chunk_y"], expected, k=3) == 0.5

    # Zero hit
    assert compute_recall_at_k(["chunk_x", "chunk_y"], expected, k=2) == 0.0

    # Expected list empty
    assert compute_recall_at_k(["chunk_1"], [], k=5) == 1.0


def test_compute_context_precision():
    """Verify Context Precision rewards relevant chunks ranked earlier in candidate list."""
    expected = ["chunk_1"]

    # Rank 1 hit: precision at rank 1 = 1/1 = 1.0
    prec_top = compute_context_precision(["chunk_1", "chunk_x", "chunk_y"], expected, k=3)
    assert prec_top == 1.0

    # Rank 3 hit: precision at rank 3 = 1/3 ≈ 0.3333
    prec_bottom = compute_context_precision(["chunk_x", "chunk_y", "chunk_1"], expected, k=3)
    assert prec_bottom < prec_top

    # Zero hits
    assert compute_context_precision(["chunk_x", "chunk_y"], expected, k=2) == 0.0


def test_compute_faithfulness():
    """Verify Faithfulness measures grounding support between generation and context."""
    contexts = [
        "AegisRAG utilizes hybrid dense and sparse search fused with Reciprocal Rank Fusion.",
    ]

    # Grounded answer
    grounded_ans = "AegisRAG uses hybrid dense and sparse search with Reciprocal Rank Fusion."
    score_high = compute_faithfulness(grounded_ans, contexts)
    assert score_high > 0.5

    # Ungrounded answer
    hallucinated_ans = "Quantum computing algorithms achieved nuclear propulsion in Kyoto."
    score_low = compute_faithfulness(hallucinated_ans, contexts)
    assert score_low < 0.35

    # Empty answer
    assert compute_faithfulness("", contexts) == 0.0
