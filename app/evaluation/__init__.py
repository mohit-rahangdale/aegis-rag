"""RAG evaluation and benchmarking package."""

from app.evaluation.dataset import load_eval_dataset
from app.evaluation.metrics import (
    compute_context_precision,
    compute_faithfulness,
    compute_recall_at_k,
)
from app.evaluation.models import BenchmarkSummary, EvalSample, SampleEvaluation

__all__ = [
    "EvalSample",
    "SampleEvaluation",
    "BenchmarkSummary",
    "load_eval_dataset",
    "compute_recall_at_k",
    "compute_context_precision",
    "compute_faithfulness",
]
