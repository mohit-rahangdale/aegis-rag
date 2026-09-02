"""Structured telemetry and logging helpers for LLM Gateway events."""

import logging
from typing import Any, Dict, Optional

from app.gateway.models import CostEstimate, TokenUsage

logger = logging.getLogger("aegisrag.gateway")


def log_provider_attempt(
    provider: str,
    model: str,
    request_id: str,
    attempt: int,
) -> None:
    """Log the dispatch of a request to a specific LLM provider."""
    logger.info(
        f"Dispatching LLM call to provider={provider} model={model} (attempt={attempt})",
        extra={
            "provider": provider,
            "model": model,
            "request_id": request_id,
            "attempt": attempt,
            "event": "llm_call_started",
        },
    )


def log_provider_success(
    provider: str,
    model: str,
    latency_ms: float,
    usage: TokenUsage,
    cost: CostEstimate,
    request_id: str,
    fallback_used: bool,
) -> None:
    """Log successful completion of an LLM generation."""
    logger.info(
        f"LLM call succeeded: provider={provider} model={model} "
        f"latency={latency_ms:.1f}ms total_tokens={usage.total_tokens} cost=${cost.total_cost_usd:.6f}",
        extra={
            "provider": provider,
            "model": model,
            "latency_ms": latency_ms,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "total_cost_usd": cost.total_cost_usd,
            "request_id": request_id,
            "fallback_used": fallback_used,
            "event": "llm_call_succeeded",
        },
    )


def log_provider_failure(
    provider: str,
    model: str,
    error: Exception,
    request_id: str,
    attempt: int,
    will_retry: bool,
) -> None:
    """Log an LLM provider call failure."""
    level = logging.WARNING if will_retry else logging.ERROR
    logger.log(
        level,
        f"LLM call failed: provider={provider} model={model} (attempt={attempt}, will_retry={will_retry}) - {error}",
        extra={
            "provider": provider,
            "model": model,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "request_id": request_id,
            "attempt": attempt,
            "will_retry": will_retry,
            "event": "llm_call_failed",
        },
    )


def log_fallback_triggered(
    primary_provider: str,
    fallback_provider: str,
    reason: str,
    request_id: str,
) -> None:
    """Log failover event from primary to fallback provider."""
    logger.warning(
        f"Failover triggered: Primary={primary_provider} failed ({reason}) -> Switching to Fallback={fallback_provider}",
        extra={
            "primary_provider": primary_provider,
            "fallback_provider": fallback_provider,
            "reason": reason,
            "request_id": request_id,
            "event": "llm_fallback_triggered",
        },
    )


def log_circuit_state_change(
    provider: str,
    old_state: str,
    new_state: str,
    reason: Optional[str] = None,
) -> None:
    """Log circuit breaker state transition."""
    logger.warning(
        f"Circuit breaker state change for provider={provider}: {old_state} -> {new_state} (reason: {reason})",
        extra={
            "provider": provider,
            "old_state": old_state,
            "new_state": new_state,
            "reason": reason,
            "event": "circuit_breaker_state_change",
        },
    )
