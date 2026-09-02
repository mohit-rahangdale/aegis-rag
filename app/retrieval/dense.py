"""Dense vector retrieval using Qdrant similarity search."""

from typing import List, Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from app.config.settings import get_settings
from app.ingestion.embeddings import EmbeddingGenerator
from app.retrieval.models import RetrievedChunk
from app.storage.qdrant.client import get_qdrant_client


class DenseRetriever:
    """Executes vector similarity search against Qdrant collection."""

    def __init__(
        self,
        client: Optional[AsyncQdrantClient] = None,
        embedding_generator: Optional[EmbeddingGenerator] = None,
        collection_name: Optional[str] = None,
    ) -> None:
        self.settings = get_settings()
        self.client = client or get_qdrant_client()
        self.embedder = embedding_generator or EmbeddingGenerator()
        self.collection_name = collection_name or self.settings.qdrant_collection

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        document_id: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        """Search top-k most similar chunks for a given natural language query."""
        # 1. Compute query vector
        query_vector = await self.embedder.embed_query(query)

        # 2. Build filter condition if document_id specified
        query_filter = None
        if document_id:
            query_filter = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchValue(value=document_id),
                    )
                ]
            )

        # 3. Query Qdrant vector index
        try:
            response = await self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=top_k,
                query_filter=query_filter,
            )
        except Exception:
            return []

        # 4. Map hits to RetrievedChunk models
        results: List[RetrievedChunk] = []
        for point in response.points:
            payload = point.payload or {}
            results.append(
                RetrievedChunk(
                    chunk_id=payload.get("chunk_id", str(point.id)),
                    document_id=payload.get("document_id", ""),
                    text=payload.get("text", ""),
                    score=float(point.score),
                    page_number=payload.get("page_number"),
                    filename=payload.get("filename"),
                    metadata=payload.get("metadata", {}),
                    source="dense",
                )
            )

        return results
