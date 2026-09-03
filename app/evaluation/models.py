"""Data models for evaluation benchmarks and telemetry metrics."""

from typing import Any, List, Optional
from pydantic import BaseModel, Field, model_validator


class EvalSample(BaseModel):
    """A benchmark sample with query, expected answer, and metadata."""

    id: str
    query: str
    ground_truth_answer: str
    expected_chunk_ids: List[str] = Field(default_factory=list)
    sample_type: str = "document_rag"
    tags: List[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def infer_sample_type(cls, data: Any) -> Any:
        if isinstance(data, dict) and "sample_type" not in data:
            tags = data.get("tags", [])
            if any(t in tags for t in ("fast_path", "dialogue", "token_saving")):
                data["sample_type"] = "fast_path"
            elif any(t in tags for t in ("injection", "adversarial", "system_override")):
                data["sample_type"] = "adversarial"
            else:
                data["sample_type"] = "document_rag"
        return data


class SampleEvaluation(BaseModel):
    """Evaluation result for an individual sample query."""

    sample_id: str
    query: str
    sample_type: str = "document_rag"
    recall_at_k: float = Field(ge=0.0, le=1.0)
    context_precision: float = Field(ge=0.0, le=1.0)
    faithfulness: float = Field(ge=0.0, le=1.0)
    latency_ms: float
    total_tokens: int
    tokens_saved: int = 0
    is_fast_path: bool = False
    is_grounded: bool = True
    status: str = "PASSED"
    generated_answer: str = ""
    retrieved_context_snippet: Optional[str] = None


class BenchmarkSummary(BaseModel):
    """Aggregated evaluation metrics across all benchmark test cases."""

    total_samples: int
    document_samples_count: int = 0
    fast_path_samples_count: int = 0
    adversarial_samples_count: int = 0
    mean_recall_at_k: float
    mean_context_precision: float
    mean_faithfulness: float
    mean_latency_ms: float
    total_tokens: int = 0
    total_tokens_used: int = 0
    total_tokens_saved: int = 0
    passed_samples: int
    pass_rate: float
    knowledge_connected_rate: float = 1.0
    eval_details: List[SampleEvaluation] = Field(default_factory=list)
