"""Prompt injection and jailbreak defense heuristics."""

import re
from typing import List, Tuple

from app.guardrails.models import GuardrailResult

INJECTION_PATTERNS: List[Tuple[str, re.Pattern]] = [
    (
        "instruction_override",
        re.compile(
            r"(ignore|disregard|forget|bypass|override)\s+(all\s+)?(previous|prior|above)\s+(instructions|directives|prompts|rules|commands)",
            re.IGNORECASE,
        ),
    ),
    (
        "system_prompt_leak",
        re.compile(
            r"(reveal|print|show|output|repeat|display)\s+(the\s+)?(system\s+prompt|initial\s+prompt|hidden\s+instructions|system\s+instructions)",
            re.IGNORECASE,
        ),
    ),
    (
        "jailbreak_persona",
        re.compile(
            r"(dan\s+mode|jailbreak|unrestricted\s+ai|do\s+anything\s+now|act\s+as\s+an\s+unfiltered)",
            re.IGNORECASE,
        ),
    ),
    (
        "script_injection",
        re.compile(
            r"(<script\b|javascript:|onerror\s*=|onload\s*=)",
            re.IGNORECASE,
        ),
    ),
]


def detect_prompt_injection(text: str) -> GuardrailResult:
    """Scan query for malicious adversarial prompt injections or jailbreak patterns."""
    cleaned = text.strip()
    if not cleaned:
        return GuardrailResult(is_safe=True)

    for category, pattern in INJECTION_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            return GuardrailResult(
                is_safe=False,
                flagged_category="prompt_injection",
                reason=f"Query matched suspicious adversarial injection pattern ({category}).",
                refusal_response=(
                    "I cannot fulfill this request. AegisRAG safety policies prohibit prompt "
                    "injections or instructions that override system directives."
                ),
            )

    return GuardrailResult(is_safe=True)
