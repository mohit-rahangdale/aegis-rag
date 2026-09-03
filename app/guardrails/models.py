"""Data models for guardrails validation, injection detection, and hallucination grounding."""

from typing import List, Optional
from pydantic import BaseModel, Field


class GuardrailResult(BaseModel):
    """Result of safety, injection, or policy validation."""

    is_safe: bool = Field(..., description="Whether content passed safety checks")
    flagged_category: Optional[str] = Field(default=None, description="Category of violation if triggered")
    reason: Optional[str] = Field(default=None, description="Explanation of why check failed")
    refusal_response: Optional[str] = Field(
        default=None,
        description="Standardized safe response to return to the user if safety check fails",
    )
    fast_path_response: Optional[str] = Field(
        default=None,
        description="Predefined answer for routine conversational dialogue to save LLM tokens",
    )



class GroundingResult(BaseModel):
    """Result of hallucination grounding check between generation and source context."""

    is_grounded: bool = Field(..., description="Whether generation is supported by retrieved context")
    grounding_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score of context support")
    hallucinated_claims: List[str] = Field(default_factory=list, description="Specific unsupported phrases if any")
    reason: Optional[str] = Field(default=None, description="Explanation of grounding decision")
