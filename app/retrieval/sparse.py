"""Sparse / lexical retrieval using BM25 for keyword and acronym precision."""

import re
from typing import List, Optional

from rank_bm25 import BM25Okapi

from app.retrieval.models import RetrievedChunk


def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase alphanumeric words."""
    return re.findall(r"\w+", text.lower())


class SparseRetriever:
    """Performs exact lexical and keyword search across chunks using BM25."""

    def __init__(self) -> None:
        self.chunks: List[RetrievedChunk] = []
        self.bm25: Optional[BM25Okapi] = None

    def index_chunks(self, chunks: List[RetrievedChunk]) -> None:
        """Build in-memory BM25 index over provided chunk candidate pool."""
        self.chunks = list(chunks)
        if not self.chunks:
            self.bm25 = None
            return

        corpus = [tokenize(c.text) for c in self.chunks]
        self.bm25 = BM25Okapi(corpus)

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        candidate_pool: Optional[List[RetrievedChunk]] = None,
    ) -> List[RetrievedChunk]:
        """Search top-k chunks with highest BM25 lexical match to query."""
        if candidate_pool is not None:
            self.index_chunks(candidate_pool)

        if not self.chunks or self.bm25 is None:
            return []

        tokens = tokenize(query)
        if not tokens:
            return []

        raw_scores = self.bm25.get_scores(tokens)
        max_score = max(raw_scores) if len(raw_scores) > 0 and max(raw_scores) > 0 else 1.0

        # Pair chunks with normalized scores
        scored_pairs = []
        for chunk, raw_score in zip(self.chunks, raw_scores):
            if raw_score > 0:
                normalized = float(raw_score / max_score)
                # Clone chunk with sparse scoring
                chunk_copy = chunk.model_copy(
                    update={
                        "score": round(normalized, 4),
                        "source": "sparse",
                    }
                )
                scored_pairs.append((chunk_copy, raw_score))

        # Sort descending by score
        scored_pairs.sort(key=lambda x: x[1], reverse=True)
        return [pair[0] for pair in scored_pairs[:top_k]]
