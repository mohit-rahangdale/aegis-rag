"""Tests for Gateway models, token usage, and cost calculation."""

import pytest
from pydantic import ValidationError

from app.gateway.models import (
    ChatMessage,
    CostEstimate,
    GatewayRequest,
    GatewayResponse,
    Role,
    TokenUsage,
)
from app.gateway.usage import calculate_cost, get_pricing_rate


def test_gateway_request_prompt_conversion():
    """Verify single prompt is automatically converted to user ChatMessage."""
    req = GatewayRequest(prompt="What is AegisRAG?")
    assert len(req.messages) == 1
    assert req.messages[0].role == Role.USER
    assert req.messages[0].content == "What is AegisRAG?"


def test_gateway_request_explicit_messages():
    """Verify explicit messages list is preserved."""
    req = GatewayRequest(
        messages=[
            ChatMessage(role=Role.SYSTEM, content="You are a helpful assistant."),
            ChatMessage(role=Role.USER, content="Hello!"),
        ]
    )
    assert len(req.messages) == 2
    assert req.messages[0].role == Role.SYSTEM
    assert req.messages[1].role == Role.USER


def test_gateway_request_empty_validation():
    """Verify error when neither prompt nor messages is provided."""
    with pytest.raises(ValidationError):
        GatewayRequest()


def test_token_usage_auto_sum():
    """Verify total tokens is computed if omitted."""
    usage = TokenUsage(prompt_tokens=150, completion_tokens=50)
    assert usage.total_tokens == 200


def test_cost_estimate_auto_sum():
    """Verify total cost is computed if omitted."""
    cost = CostEstimate(input_cost_usd=0.00015, output_cost_usd=0.00060)
    assert cost.total_cost_usd == 0.00075


def test_calculate_cost_gemini():
    """Verify cost calculation for Gemini model."""
    # gemini-2.5-flash: $0.15/1M input, $0.60/1M output
    cost = calculate_cost(
        provider="gemini",
        model="gemini-2.5-flash",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
    )
    assert cost.input_cost_usd == 0.15
    assert cost.output_cost_usd == 0.60
    assert cost.total_cost_usd == 0.75


def test_calculate_cost_mistral():
    """Verify cost calculation for Mistral model."""
    # mistral-small-latest: $0.20/1M input, $0.60/1M output
    cost = calculate_cost(
        provider="mistral",
        model="mistral-small-latest",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
    )
    assert cost.input_cost_usd == 0.20
    assert cost.output_cost_usd == 0.60
    assert cost.total_cost_usd == 0.80


def test_calculate_cost_fallback_rate():
    """Verify default rate is applied for unrecognized models."""
    rate = get_pricing_rate("unknown-experimental-model")
    assert rate == (0.20, 0.60)
