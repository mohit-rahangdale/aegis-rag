"""Output guardrails protecting against system prompt leakage and sensitive data exposure."""

import re
from typing import Tuple

from app.guardrails.models import GuardrailResult

# Patterns for credentials and sensitive data
_SECRET_PATTERNS = [
    (re.compile(r"(AIza[0-9A-Za-z-_]{35})"), "[REDACTED_API_KEY]"),
    (re.compile(r"(sk-[a-zA-Z0-9]{32,})"), "[REDACTED_API_KEY]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
    (re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "[REDACTED_CARD]"),
]

# Phrases that indicate raw system instructions leaked into output
_LEAK_PHRASES = [
    "you are aegisrag, an accurate, truthful ai assistant",
    "answer the user's question using only the provided context blocks",
]


def sanitize_output(text: str) -> Tuple[str, GuardrailResult]:
    """Inspect and sanitize generated text before returning to client.

    Redacts exposed credentials/PII and prevents internal prompt leakage.
    """
    cleaned = text.strip()
    if not cleaned:
        return "", GuardrailResult(
            is_safe=False,
            flagged_category="empty_response",
            reason="Model generated empty response.",
        )

    # Check for system prompt leakage
    lower = cleaned.lower()
    for phrase in _LEAK_PHRASES:
        if phrase in lower:
            return (
                "I cannot output internal system directives.",
                GuardrailResult(
                    is_safe=False,
                    flagged_category="prompt_leak",
                    reason="Model output contained system prompt directives.",
                ),
            )

    # Redact credentials and PII
    sanitized = cleaned
    for pattern, replacement in _SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    return sanitized, GuardrailResult(is_safe=True)
