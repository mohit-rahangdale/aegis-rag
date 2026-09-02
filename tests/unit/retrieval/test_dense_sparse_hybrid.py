"""Unit tests for Dense, Sparse (BM25), and Hybrid (RRF) retrievers."""

import uuid
import pytest
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from app.ingestion.embeddings import EmbeddingGenerator
from app.retrieval.dense import DenseRetriever
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.models import RetrievedChunk
from app.retrieval.sparse import SparseRetriever


@pytest.fixture
async def populated_qdrant():
    """Create in-memory Qdrant instance populated with test vector points."""
    client = AsyncQdrantClient(":memory:")
    embedder = EmbeddingGenerator()
    collection_name = "test_collection"

    await client.create_collection(
        collection_name=collection_name,
        vectors_config=qmodels.VectorParams(size=768, distance=qmodels.Distance.COSINE),
    )

    documents = [
        ("doc-1", "AegisRAG features automated multi-LLM failover to Mistral."),
        ("doc-1", "Hybrid search pairs dense vector embeddings with BM25 keyword matching."),
        ("doc-2", "Redis is utilized for session caching and conversation memory buffering."),
        ("doc-2", "LangGraph state graphs orchestrate corrective RAG query flows."),
    ]

    points = []
    for idx, (doc_id, text) in enumerate(documents):
        vec = await embedder.embed_query(text)
        point_id = str(uuid.uuid4())
        points.append(
            qmodels.PointStruct(
                id=point_id,
                vector=vec,
                payload={
                    "chunk_id": f"chunk_{idx}",
                    "document_id": doc_id,
                    "text": text,
                    "filename": f"{doc_id}.txt",
                },
            )
        )

    await client.upsert(collection_name=collection_name, points=points)
    return client, collection_name, embedder


@pytest.mark.anyio
async def test_dense_retriever(populated_qdrant):
    """Verify dense retrieval returns top-k vector matches."""
    client, collection_name, embedder = populated_qdrant
    dense = DenseRetriever(client=client, embedding_generator=embedder, collection_name=collection_name)

    results = await dense.retrieve(query="LLM failover", top_k=2)
    assert len(results) > 0
    assert results[0].source == "dense"
    assert results[0].score > 0.0


@pytest.mark.anyio
async def test_dense_retriever_filter_document_id(populated_qdrant):
    """Verify document_id filter limits results to specific document."""
    client, collection_name, embedder = populated_qdrant
    dense = DenseRetriever(client=client, embedding_generator=embedder, collection_name=collection_name)

    results = await dense.retrieve(query="RAG", top_k=5, document_id="doc-2")
    assert all(r.document_id == "doc-2" for r in results)


def test_sparse_retriever():
    """Verify BM25 sparse retriever matches exact keywords."""
    chunks = [
        RetrievedChunk(chunk_id="c1", document_id="d1", text="Python asyncpg connection pool", score=1.0),
        RetrievedChunk(chunk_id="c2", document_id="d1", text="Docker container configuration for Redis", score=1.0),
        RetrievedChunk(chunk_id="c3", document_id="d2", text="Qdrant vector similarity indexing", score=1.0),
    ]

    sparse = SparseRetriever()
    results = sparse.retrieve(query="Docker Redis", top_k=2, candidate_pool=chunks)
    assert len(results) >= 1
    assert results[0].chunk_id == "c2"
    assert results[0].source == "sparse"


@pytest.mark.anyio
async def test_hybrid_retriever(populated_qdrant):
    """Verify hybrid retriever merges dense and sparse results with RRF."""
    client, collection_name, embedder = populated_qdrant
    dense = DenseRetriever(client=client, embedding_generator=embedder, collection_name=collection_name)
    sparse = SparseRetriever()
    hybrid = HybridRetriever(dense_retriever=dense, sparse_retriever=sparse)

    results = await hybrid.retrieve(query="Redis session caching", top_k=3)
    assert len(results) > 0
    assert results[0].source == "hybrid"
    assert results[0].score > 0.0
