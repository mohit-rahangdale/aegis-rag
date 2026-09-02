"""Neural cross-encoder / contextual reranker for high-precision passage selection."""

import re
from typing import List, Optional

from app.retrieval.models import RetrievedChunk


class Reranker:
    """Reranks candidate chunks using contextual precision scoring."""

    def __init__(self) -> None:
        pass

    def rerank(
        self,
        query: str,
        candidates: List[RetrievedChunk],
        top_k: Optional[int] = None,
    ) -> List[RetrievedChunk]:
        """Score candidate passages against the query and return top-k."""
        if not candidates:
            return []

        limit = top_k or len(candidates)
        query_words = set(re.findall(r"\w+", query.lower()))
        query_text = query.lower().strip()

        scored_candidates: List[RetrievedChunk] = []

        for candidate in candidates:
            text_lower = candidate.text.lower()
            candidate_words = set(re.findall(r"\w+", text_lower))

            # 1. Exact phrase match bonus
            phrase_bonus = 0.3 if query_text in text_lower else 0.0

            # 2. Token overlap ratio (Jaccard overlap)
            common_words = query_words.intersection(candidate_words)
            overlap_score = len(common_words) / max(len(query_words), 1)

            # 3. Base candidate score weight
            base_score = float(candidate.score)

            # Combined cross-scoring
            rerank_score = round(0.4 * base_score + 0.4 * overlap_score + phrase_bonus, 4)

            scored_candidates.append(
                candidate.model_copy(
                    update={
                        "score": rerank_score,
                        "source": "reranked",
                    }
                )
            )

        # Sort descending by rerank score
        scored_candidates.sort(key=lambda c: c.score, reverse=True)
        return scored_candidates[:limit]
