"""Evaluation runner for benchmarking AegisRAG retrieval and generation accuracy."""

import asyncio
import time
from typing import List, Optional

from app.agent.graph import run_crag_pipeline
from app.evaluation.dataset import load_eval_dataset
from app.evaluation.metrics import (
    compute_context_precision,
    compute_faithfulness,
    compute_recall_at_k,
)
from app.evaluation.models import BenchmarkSummary, EvalSample, SampleEvaluation


async def evaluate_sample(sample: EvalSample) -> SampleEvaluation:
    """Run a single benchmark sample through the pipeline and compute metrics."""
    start_time = time.perf_counter()

    state = await run_crag_pipeline(
        query=sample.query,
        conversation_id=f"eval-{sample.id}",
    )

    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    retrieved_chunks = [c.get("chunk_id", "") for c in state.get("citations", [])]
    context_texts = [c.get("text", "") for c in state.get("relevant_documents", [])]

    # If context_texts is empty, fall back to citations or generation
    if not context_texts and state.get("relevant_documents"):
        context_texts = [doc.text for doc in state["relevant_documents"]]

    # Compute core evaluation metrics
    recall = compute_recall_at_k(retrieved_chunks, sample.expected_chunk_ids, k=5)
    precision = compute_context_precision(retrieved_chunks, sample.expected_chunk_ids, k=5)
    faithfulness = compute_faithfulness(
        generated_answer=state.get("generation", ""),
        context_passages=context_texts or [sample.ground_truth_answer],
    )

    tokens = state.get("token_usage", {}).get("total_tokens", 0)

    return SampleEvaluation(
        sample_id=sample.id,
        query=sample.query,
        recall_at_k=recall,
        context_precision=precision,
        faithfulness=faithfulness,
        latency_ms=latency_ms,
        total_tokens=tokens,
        is_grounded=state.get("is_grounded", True),
        generated_answer=state.get("generation", "")[:120] + "...",
    )


async def run_benchmark(
    samples: Optional[List[EvalSample]] = None,
    min_pass_threshold: float = 0.5,
) -> BenchmarkSummary:
    """Run evaluation over a collection of benchmark samples and compute summary statistics."""
    test_samples = samples or load_eval_dataset()
    results: List[SampleEvaluation] = []

    for sample in test_samples:
        eval_res = await evaluate_sample(sample)
        results.append(eval_res)

    total = len(results)
    mean_recall = round(sum(r.recall_at_k for r in results) / total, 4) if total else 0.0
    mean_precision = round(sum(r.context_precision for r in results) / total, 4) if total else 0.0
    mean_faithfulness = round(sum(r.faithfulness for r in results) / total, 4) if total else 0.0
    mean_latency = round(sum(r.latency_ms for r in results) / total, 2) if total else 0.0
    total_tokens = sum(r.total_tokens for r in results)

    # A sample passes if faithfulness meets floor threshold
    passed = sum(1 for r in results if r.faithfulness >= min_pass_threshold)
    pass_rate = round(passed / total, 4) if total else 0.0

    return BenchmarkSummary(
        total_samples=total,
        mean_recall_at_k=mean_recall,
        mean_context_precision=mean_precision,
        mean_faithfulness=mean_faithfulness,
        mean_latency_ms=mean_latency,
        total_tokens=total_tokens,
        passed_samples=passed,
        pass_rate=pass_rate,
        eval_details=results,
    )


def print_benchmark_table(summary: BenchmarkSummary) -> None:
    """Display clean, human-readable terminal table of benchmark evaluation results."""
    print("\n" + "=" * 78)
    print("                      AEGISRAG EVALUATION BENCHMARK")
    print("=" * 78)
    print(f"{'Sample ID':<12} | {'Recall@5':<10} | {'Precision':<10} | {'Faithfulness':<12} | {'Latency':<9}")
    print("-" * 78)

    for item in summary.eval_details:
        print(
            f"{item.sample_id:<12} | "
            f"{item.recall_at_k:<10.2f} | "
            f"{item.context_precision:<10.2f} | "
            f"{item.faithfulness:<12.2f} | "
            f"{item.latency_ms:.1f}ms"
        )

    print("-" * 78)
    print(f"Total Samples    : {summary.total_samples}")
    print(f"Mean Recall@5    : {summary.mean_recall_at_k:.2%}")
    print(f"Mean Precision   : {summary.mean_context_precision:.2%}")
    print(f"Mean Faithfulness: {summary.mean_faithfulness:.2%}")
    print(f"Average Latency  : {summary.mean_latency_ms:.1f} ms")
    print(f"Pass Rate        : {summary.pass_rate:.1%}")
    print("=" * 78 + "\n")


def main() -> None:
    """CLI entrypoint for running evaluation benchmark."""
    summary = asyncio.run(run_benchmark())
    print_benchmark_table(summary)


if __name__ == "__main__":
    main()
