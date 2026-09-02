"""Token usage tracking and cost calculation for LLM providers."""

from typing import Dict, Tuple

from app.gateway.models import CostEstimate

# Pricing dictionary: (input_cost_per_million, output_cost_per_million)
MODEL_PRICING_PER_MILLION: Dict[str, Tuple[float, float]] = {
    # Gemini models
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-1.5-pro": (3.50, 10.50),
    # Mistral models
    "mistral-small-latest": (0.20, 0.60),
    "mistral-small": (0.20, 0.60),
    "mistral-medium": (2.70, 8.10),
    "mistral-large-latest": (2.00, 6.00),
    "mistral-large": (2.00, 6.00),
    "open-mistral-7b": (0.25, 0.25),
    # Default fallback rate
    "default": (0.20, 0.60),
}


def get_pricing_rate(model: str) -> Tuple[float, float]:
    """Retrieve input and output cost per million tokens for a model."""
    normalized_model = model.lower().strip()
    for pattern, rate in MODEL_PRICING_PER_MILLION.items():
        if pattern != "default" and pattern in normalized_model:
            return rate
    return MODEL_PRICING_PER_MILLION["default"]


def calculate_cost(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> CostEstimate:
    """Calculate estimated financial cost for tokens consumed in a generation."""
    input_rate, output_rate = get_pricing_rate(model)

    input_cost = (prompt_tokens / 1_000_000.0) * input_rate
    output_cost = (completion_tokens / 1_000_000.0) * output_rate
    total_cost = input_cost + output_cost

    return CostEstimate(
        input_cost_usd=round(input_cost, 6),
        output_cost_usd=round(output_cost, 6),
        total_cost_usd=round(total_cost, 6),
    )
