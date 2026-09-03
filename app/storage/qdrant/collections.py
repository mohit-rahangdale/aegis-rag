"""Qdrant collection management and schema configuration."""

from typing import Any, Dict, Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from app.config.settings import get_settings
from app.storage.qdrant.client import check_qdrant_health, get_qdrant_client


class QdrantCollectionManager:
    """Manages vector collections, distance metrics, and vector configurations in Qdrant."""

    def __init__(
        self,
        client: Optional[AsyncQdrantClient] = None,
        default_collection: Optional[str] = None,
        default_vector_size: Optional[int] = None,
    ) -> None:
        self._client = client
        settings = get_settings()
        self.default_collection = default_collection or settings.qdrant_collection
        self.default_vector_size = default_vector_size or settings.qdrant_vector_size

    @property
    def client(self) -> AsyncQdrantClient:
        if self._client is None:
            self._client = get_qdrant_client()
        return self._client

    async def collection_exists(self, collection_name: Optional[str] = None) -> bool:
        """Check if a vector collection exists."""
        target = collection_name or self.default_collection
        try:
            return await self.client.collection_exists(collection_name=target)
        except Exception:
            return False

    async def ensure_collection(
        self,
        collection_name: Optional[str] = None,
        vector_size: Optional[int] = None,
        distance: str = "Cosine",
    ) -> bool:
        """Ensure vector collection exists, creating it if absent."""
        target_name = collection_name or self.default_collection
        target_size = vector_size or self.default_vector_size

        if await self.collection_exists(target_name):
            return True

        # Map distance metric
        distance_map = {
            "cosine": qmodels.Distance.COSINE,
            "euclid": qmodels.Distance.EUCLID,
            "dot": qmodels.Distance.DOT,
        }
        metric = distance_map.get(distance.lower(), qmodels.Distance.COSINE)

        await self.client.create_collection(
            collection_name=target_name,
            vectors_config=qmodels.VectorParams(
                size=target_size,
                distance=metric,
            ),
        )
        return True

    async def get_collection_info(self, collection_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve collection metadata and stats."""
        target = collection_name or self.default_collection
        try:
            info = await self.client.get_collection(collection_name=target)
            return {
                "name": target,
                "status": str(info.status),
                "vectors_count": getattr(info, "indexed_vectors_count", getattr(info, "points_count", 0)),
                "points_count": getattr(info, "points_count", 0),
            }
        except Exception:
            return None

    async def delete_collection(self, collection_name: str) -> bool:
        """Delete an existing collection."""
        try:
            return await self.client.delete_collection(collection_name=collection_name)
        except Exception:
            return False

    async def is_healthy(self) -> bool:
        """Check Qdrant health."""
        return await check_qdrant_health(self.client)
