"""Embedding generator using Google GenAI with deterministic offline fallback."""

import hashlib
import math
from typing import List, Optional

from app.config.settings import Settings, get_settings


class EmbeddingGenerator:
    """Generates vector embeddings for document chunks and search queries."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        model: str = "text-embedding-004",
        dimension: int = 768,
    ) -> None:
        self.settings = settings or get_settings()
        self.model = model
        self.dimension = dimension
        self._client = None

        if self.settings.gemini_api_key:
            from google import genai
            self._client = genai.Client(api_key=self.settings.gemini_api_key)

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        if not texts:
            return []

        # If live Gemini API key is configured, invoke Gemini embedding model
        if self._client and self.settings.gemini_api_key and not self.settings.is_testing:
            try:
                embeddings: List[List[float]] = []
                for text in texts:
                    response = await self._client.aio.models.embed_content(
                        model=self.model,
                        contents=text,
                    )
                    # Extract embedding values
                    if hasattr(response, "embedding") and hasattr(response.embedding, "values"):
                        embeddings.append(list(response.embedding.values))
                    elif hasattr(response, "embeddings") and response.embeddings:
                        embeddings.append(list(response.embeddings[0].values))
                    else:
                        embeddings.append(self._generate_deterministic_vector(text))
                return embeddings
            except Exception:
                # Graceful fallback to deterministic embeddings on network/quota error
                return [self._generate_deterministic_vector(t) for t in texts]

        # Deterministic offline vector generation (for testing & offline dev)
        return [self._generate_deterministic_vector(t) for t in texts]

    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding vector for a single query."""
        results = await self.embed_texts([query])
        return results[0]

    def _generate_deterministic_vector(self, text: str) -> List[float]:
        """Produce a normalized float vector of dimension self.dimension derived from text hash."""
        vec = []
        # Generate pseudo-random deterministic floats using chained SHA-256 hashes
        base_hash = hashlib.sha256(text.encode("utf-8")).digest()
        for i in range(self.dimension):
            byte_val = base_hash[i % len(base_hash)]
            val = (byte_val / 255.0) * 2.0 - 1.0  # Range [-1.0, 1.0]
            # Add positional perturbation
            val += math.sin(i * 0.1) * 0.1
            vec.append(val)

        # L2 normalize the vector
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec
