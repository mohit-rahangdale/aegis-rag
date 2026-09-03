"""Unit tests for evaluation harness runner."""

from unittest.mock import AsyncMock, patch
import pytest

from app.evaluation.dataset import EvalSample
from app.evaluation.runner import evaluate_sample, run_benchmark


@pytest.mark.anyio
async def test_evaluate_sample():
    """Verify evaluating an individual sample computes all metrics."""
    mock_state = {
        "conversation_id": "eval-s1",
        "generation": "AegisRAG uses Reciprocal Rank Fusion for hybrid retrieval.",
        "citations": [{"chunk_id": "c1"}, {"chunk_id": "c2"}],
        "relevant_documents": [],
        "is_grounded": True,
        "token_usage": {"total_tokens": 42},
    }

    sample = EvalSample(
        id="s1",
        query="What does AegisRAG use?",
        ground_truth_answer="AegisRAG uses Reciprocal Rank Fusion for hybrid retrieval.",
        expected_chunk_ids=["c1", "c2"],
    )

    with patch("app.evaluation.runner.run_crag_pipeline", new_callable=AsyncMock, return_value=mock_state):
        eval_result = await evaluate_sample(sample)

        assert eval_result.sample_id == "s1"
        assert eval_result.recall_at_k == 1.0
        assert eval_result.context_precision == 1.0
        assert eval_result.faithfulness > 0.5
        assert eval_result.total_tokens == 42
        assert eval_result.latency_ms >= 0.0


@pytest.mark.anyio
async def test_run_benchmark_summary():
    """Verify aggregated benchmark computes means and pass rate across samples."""
    mock_state = {
        "conversation_id": "eval-s1",
        "generation": "AegisRAG uses Reciprocal Rank Fusion for hybrid retrieval.",
        "citations": [{"chunk_id": "c1"}],
        "relevant_documents": [],
        "is_grounded": True,
        "token_usage": {"total_tokens": 30},
    }

    samples = [
        EvalSample(
            id="s1",
            query="Query 1",
            ground_truth_answer="AegisRAG uses Reciprocal Rank Fusion for hybrid retrieval.",
            expected_chunk_ids=["c1"],
        ),
        EvalSample(
            id="s2",
            query="Query 2",
            ground_truth_answer="AegisRAG uses Reciprocal Rank Fusion for hybrid retrieval.",
            expected_chunk_ids=["c1"],
        ),
    ]


    with patch("app.evaluation.runner.run_crag_pipeline", new_callable=AsyncMock, return_value=mock_state):
        summary = await run_benchmark(samples=samples)

        assert summary.total_samples == 2
        assert summary.mean_recall_at_k == 1.0
        assert summary.pass_rate == 1.0
        assert summary.total_tokens == 60
        assert len(summary.eval_details) == 2
