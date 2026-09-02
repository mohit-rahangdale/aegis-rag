"""Comprehensive integration tests for LLMGateway."""

import pytest

from app.config.settings import Settings
from app.gateway.base import LLMProvider
from app.gateway.exceptions import (
    AllProvidersFailedException,
    ProviderUnavailableException,
    UnsupportedProviderException,
)
from app.gateway.models import (
    CostEstimate,
    GatewayRequest,
    GatewayResponse,
    TokenUsage,
)
from app.gateway.service import LLMGateway


class MockProvider(LLMProvider):
    """Configurable mock provider for deterministic gateway testing."""

    def __init__(
        self,
        name: str,
        default_model: str,
        should_fail: bool = False,
        failure_exc: Exception | None = None,
        content: str = "Mock generation response",
        prompt_tokens: int = 100,
        completion_tokens: int = 40,
    ) -> None:
        super().__init__(name=name, default_model=default_model, api_key="mock-key")
        self.should_fail = should_fail
        self.failure_exc = failure_exc or ProviderUnavailableException(
            f"Provider {name} unavailable", provider=name
        )
        self.content = content
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.call_count = 0

    async def is_healthy(self) -> bool:
        return not self.should_fail

    async def generate(self, request: GatewayRequest) -> GatewayResponse:
        self.call_count += 1
        if self.should_fail:
            raise self.failure_exc

        usage = TokenUsage(
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
        )
        cost = CostEstimate(input_cost_usd=0.0001, output_cost_usd=0.0002)

        return GatewayResponse(
            content=self.content,
            provider=self.name,
            model=request.model or self.default_model,
            usage=usage,
            cost=cost,
            latency_ms=12.5,
            request_id=request.request_id,
        )


@pytest.fixture
def gateway() -> LLMGateway:
    """Create test gateway with mock primary (gemini) and mock fallback (mistral)."""
    settings = Settings(
        app_env="testing",
        gateway_max_retries=2,
        circuit_breaker_failure_threshold=2,
    )
    gw = LLMGateway(settings=settings)

    # Register mocks for testing
    mock_gemini = MockProvider(name="gemini", default_model="gemini-2.5-flash", content="Answer from Gemini")
    mock_mistral = MockProvider(name="mistral", default_model="mistral-small-latest", content="Answer from Mistral")

    gw.register_provider(mock_gemini)
    gw.register_provider(mock_mistral)
    return gw


@pytest.mark.anyio
async def test_gateway_successful_primary(gateway: LLMGateway):
    """Verify standard execution where primary provider succeeds."""
    request = GatewayRequest(prompt="Hello AegisRAG")
    response = await gateway.generate(request)

    assert response.provider == "gemini"
    assert response.content == "Answer from Gemini"
    assert response.fallback_triggered is False
    assert response.attempts == 1
    assert response.usage.total_tokens == 140
    assert response.cost.total_cost_usd > 0
    assert response.request_id is not None


@pytest.mark.anyio
async def test_gateway_primary_failure_triggers_fallback(gateway: LLMGateway):
    """Verify that when primary fails, gateway automatically falls back to secondary."""
    # Configure Gemini to fail
    failing_gemini = MockProvider(
        name="gemini",
        default_model="gemini-2.5-flash",
        should_fail=True,
    )
    gateway.register_provider(failing_gemini)

    request = GatewayRequest(prompt="Hello AegisRAG")
    response = await gateway.generate(request)

    assert response.provider == "mistral"
    assert response.content == "Answer from Mistral"
    assert response.fallback_triggered is True
    assert failing_gemini.call_count == gateway.settings.gateway_max_retries


@pytest.mark.anyio
async def test_gateway_all_providers_failed(gateway: LLMGateway):
    """Verify AllProvidersFailedException when both primary and fallback fail."""
    failing_gemini = MockProvider(name="gemini", default_model="gemini-2.5-flash", should_fail=True)
    failing_mistral = MockProvider(name="mistral", default_model="mistral-small-latest", should_fail=True)

    gateway.register_provider(failing_gemini)
    gateway.register_provider(failing_mistral)

    request = GatewayRequest(prompt="Hello AegisRAG")
    with pytest.raises(AllProvidersFailedException) as exc_info:
        await gateway.generate(request)

    err = exc_info.value
    assert "gemini" in err.attempted_providers
    assert "mistral" in err.attempted_providers
    assert "gemini" in err.errors
    assert "mistral" in err.errors


@pytest.mark.anyio
async def test_gateway_unsupported_provider(gateway: LLMGateway):
    """Verify UnsupportedProviderException when invalid provider is requested."""
    request = GatewayRequest(prompt="Hello", provider="non-existent-llm")
    with pytest.raises(UnsupportedProviderException):
        await gateway.generate(request)


@pytest.mark.anyio
async def test_gateway_custom_request_id_preserved(gateway: LLMGateway):
    """Verify caller-provided request_id is preserved across pipeline."""
    custom_id = "req-12345-abcde"
    request = GatewayRequest(prompt="Hello", request_id=custom_id)
    response = await gateway.generate(request)

    assert response.request_id == custom_id


@pytest.mark.anyio
async def test_gateway_circuit_breaker_fast_failover(gateway: LLMGateway):
    """Verify that an OPEN circuit breaker bypasses the primary provider without retry delay."""
    # Trip Gemini's circuit breaker to OPEN
    cb = gateway.get_circuit_breaker("gemini")
    cb.record_failure(Exception("failure 1"))
    cb.record_failure(Exception("failure 2"))
    assert cb.is_open is True

    # Primary mock should NOT receive any calls because circuit is open
    mock_gemini = gateway.router.get_provider("gemini")
    initial_gemini_calls = getattr(mock_gemini, "call_count", 0)

    request = GatewayRequest(prompt="Fast failover test")
    response = await gateway.generate(request)

    # Immediately answered by Mistral
    assert response.provider == "mistral"
    assert response.fallback_triggered is True
    # Gemini was skipped entirely due to open circuit
    assert getattr(mock_gemini, "call_count", 0) == initial_gemini_calls


@pytest.mark.anyio
async def test_gateway_health_check(gateway: LLMGateway):
    """Verify gateway health_check method returns health and circuit states."""
    health = await gateway.health_check()
    assert "gemini" in health
    assert "mistral" in health
    assert health["gemini"]["circuit_state"] == "CLOSED"
    assert health["mistral"]["circuit_state"] == "CLOSED"
