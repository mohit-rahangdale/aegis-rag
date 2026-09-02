"""Core LLMGateway service orchestrating provider calls, retries, and fallbacks."""

import time
from typing import Any, Dict, List, Optional

from app.config.settings import Settings, get_settings
from app.gateway.base import LLMProvider
from app.gateway.circuit_breaker import CircuitBreaker
from app.gateway.exceptions import (
    AllProvidersFailedException,
    CircuitBreakerOpenException,
    GatewayException,
)
from app.gateway.logging import (
    log_fallback_triggered,
    log_provider_attempt,
    log_provider_success,
)
from app.gateway.models import GatewayRequest, GatewayResponse
from app.gateway.providers import GeminiProvider, MistralProvider
from app.gateway.request_id import ensure_request_id
from app.gateway.retry import execute_with_retry
from app.gateway.router import ProviderRouter
from app.gateway.timeout import execute_with_timeout


class LLMGateway:
    """Production LLM Gateway.

    Provides centralized resiliency:
    - Provider abstraction and routing
    - Primary-to-fallback failover (Gemini -> Mistral)
    - Exponential backoff with jitter
    - Timeout protection
    - Per-provider circuit breaking
    - Unified usage and cost tracking
    - Correlation ID tracing and structured logging
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        router: Optional[ProviderRouter] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.router = router or ProviderRouter(
            primary_provider=self.settings.primary_llm_provider,
            fallback_provider=self.settings.fallback_llm_provider,
        )

        # Per-provider circuit breakers
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Initialize default providers if not already present
        self._initialize_default_providers()

    def _initialize_default_providers(self) -> None:
        """Instantiate default Gemini and Mistral providers with configured settings."""
        if not self.router.has_provider("gemini"):
            gemini = GeminiProvider(
                api_key=self.settings.gemini_api_key,
                default_model=self.settings.default_gemini_model,
            )
            self.register_provider(gemini)

        if not self.router.has_provider("mistral"):
            mistral = MistralProvider(
                api_key=self.settings.mistral_api_key,
                default_model=self.settings.default_mistral_model,
            )
            self.register_provider(mistral)

    def register_provider(self, provider: LLMProvider) -> None:
        """Register a provider and initialize its circuit breaker."""
        name = provider.name.lower()
        self.router.register_provider(provider)
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(
                provider=name,
                failure_threshold=self.settings.circuit_breaker_failure_threshold,
                recovery_timeout=self.settings.circuit_breaker_recovery_timeout,
            )

    def get_circuit_breaker(self, provider_name: str) -> CircuitBreaker:
        """Retrieve circuit breaker for a provider."""
        name = provider_name.lower().strip()
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(
                provider=name,
                failure_threshold=self.settings.circuit_breaker_failure_threshold,
                recovery_timeout=self.settings.circuit_breaker_recovery_timeout,
            )
        return self.circuit_breakers[name]

    async def generate(self, request: GatewayRequest) -> GatewayResponse:
        """Execute request with fallback routing, retry, timeout, and circuit breaking."""
        request_id = ensure_request_id(request.request_id)
        request.request_id = request_id

        # Determine sequence of providers to attempt
        sequence = self.router.resolve_provider_sequence(request.provider)

        attempted_providers: List[str] = []
        errors: Dict[str, str] = {}
        total_attempts = 0

        for i, provider_name in enumerate(sequence):
            attempted_providers.append(provider_name)
            provider = self.router.get_provider(provider_name)
            cb = self.get_circuit_breaker(provider_name)
            model_name = request.model or provider.default_model

            # 1. Circuit breaker gate
            try:
                cb.check_availability()
            except CircuitBreakerOpenException as exc:
                errors[provider_name] = str(exc)
                if i + 1 < len(sequence):
                    next_provider = sequence[i + 1]
                    log_fallback_triggered(
                        primary_provider=provider_name,
                        fallback_provider=next_provider,
                        reason=f"Circuit breaker is OPEN: {exc}",
                        request_id=request_id,
                    )
                continue

            # 2. Provider invocation with centralized retry and timeout
            async def _invoke_provider() -> GatewayResponse:
                return await execute_with_timeout(
                    coro=provider.generate(request),
                    timeout_seconds=self.settings.gateway_timeout_seconds,
                    provider=provider_name,
                    model=model_name,
                )

            log_provider_attempt(
                provider=provider_name,
                model=model_name,
                request_id=request_id,
                attempt=total_attempts + 1,
            )

            try:
                response = await execute_with_retry(
                    func=_invoke_provider,
                    max_retries=self.settings.gateway_max_retries,
                    initial_delay=0.1,  # swift for unit tests and responsive APIs
                    backoff_factor=self.settings.gateway_backoff_factor,
                    provider=provider_name,
                    model=model_name,
                    request_id=request_id,
                    on_failure=lambda exc, att: cb.record_failure(exc),
                )

                # Successful execution
                cb.record_success()
                total_attempts += 1

                is_fallback = (provider_name != sequence[0])
                response.attempts = total_attempts
                response.fallback_triggered = is_fallback
                response.request_id = request_id

                log_provider_success(
                    provider=provider_name,
                    model=model_name,
                    latency_ms=response.latency_ms,
                    usage=response.usage,
                    cost=response.cost,
                    request_id=request_id,
                    fallback_used=is_fallback,
                )
                return response

            except Exception as exc:
                cb.record_failure(exc)
                errors[provider_name] = str(exc)

                if i + 1 < len(sequence):
                    next_provider = sequence[i + 1]
                    log_fallback_triggered(
                        primary_provider=provider_name,
                        fallback_provider=next_provider,
                        reason=str(exc),
                        request_id=request_id,
                    )

        # If all providers exhausted
        raise AllProvidersFailedException(
            message=(
                f"All attempted providers ({', '.join(attempted_providers)}) failed to generate a response"
            ),
            attempted_providers=attempted_providers,
            errors=errors,
        )

    async def health_check(self) -> Dict[str, Any]:
        """Unified health check of all registered providers and their circuit states."""
        results: Dict[str, Any] = {}
        for name in self.router.list_providers():
            provider = self.router.get_provider(name)
            cb = self.get_circuit_breaker(name)
            healthy = await provider.is_healthy()
            results[name] = {
                "configured": healthy,
                "circuit_state": cb.state.value,
                "consecutive_failures": cb.failure_count,
            }
        return results
