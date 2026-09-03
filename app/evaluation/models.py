"""Data models for RAG evaluation benchmarks and metrics."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvalSample(BaseModel):
    """A benchmark query with expected ground-truth chunks and target answer."""

    id: str
    query: str
    ground_truth_answer: str
    expected_chunk_ids: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class SampleEvaluation(BaseModel):
    """Evaluation result for a single sample."""

    sample_id: str
    query: str
    recall_at_k: float = Field(ge=0.0, le=1.0)
    context_precision: float = Field(ge=0.0, le=1.0)
    faithfulness: float = Field(ge=0.0, le=1.0)
    latency_ms: float
    total_tokens: int
    is_grounded: bool
    generated_answer: str


class BenchmarkSummary(BaseModel):
    """Aggregated benchmark statistics across all evaluated samples."""

    total_samples: int
    mean_recall_at_k: float
    mean_context_precision: float
    mean_faithfulness: float
    mean_latency_ms: float
    total_tokens: int
    passed_samples: int
    pass_rate: float
    eval_details: List[SampleEvaluation] = Field(default_factory=list)
