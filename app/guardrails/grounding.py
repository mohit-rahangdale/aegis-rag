"""Hallucination and factual grounding verification against retrieved context."""

import re
from typing import List, Set

from app.guardrails.models import GroundingResult

COMMON_STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "if", "then", "of", "to", "in",
    "on", "at", "by", "for", "with", "about", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did", "this",
    "that", "these", "those", "it", "its", "as", "from", "into", "through",
}


def extract_keywords(text: str) -> Set[str]:
    """Extract lowercase non-stopword alphanumeric words."""
    words = re.findall(r"\b[a-zA-Z0-9_\-]{3,}\b", text.lower())
    return {w for w in words if w not in COMMON_STOPWORDS}


def verify_grounding(
    generation: str,
    contexts: List[str],
    min_overlap_threshold: float = 0.35,
) -> GroundingResult:
    """Verify whether generated response is grounded in provided source contexts."""
    if not contexts:
        # If no context was provided and model says it doesn't know, it is grounded
        text_lower = generation.lower()
        if "cannot find" in text_lower or "no information" in text_lower or "not mentioned" in text_lower:
            return GroundingResult(
                is_grounded=True,
                grounding_score=1.0,
                reason="Model appropriately stated absence of relevant context.",
            )
        return GroundingResult(
            is_grounded=False,
            grounding_score=0.0,
            reason="Generation provided without supporting context passages.",
        )

    # Combine all contexts
    all_context_text = " ".join(contexts)
    context_keywords = extract_keywords(all_context_text)
    gen_keywords = extract_keywords(generation)

    if not gen_keywords:
        return GroundingResult(is_grounded=True, grounding_score=1.0)

    # Calculate token overlap
    supported_keywords = gen_keywords.intersection(context_keywords)
    overlap_ratio = len(supported_keywords) / len(gen_keywords)

    is_grounded = overlap_ratio >= min_overlap_threshold
    unsupported = list(gen_keywords - context_keywords)[:5]

    return GroundingResult(
        is_grounded=is_grounded,
        grounding_score=round(overlap_ratio, 4),
        hallucinated_claims=unsupported if not is_grounded else [],
        reason="Grounded in retrieved context." if is_grounded else "Low lexical support in retrieved context.",
    )
