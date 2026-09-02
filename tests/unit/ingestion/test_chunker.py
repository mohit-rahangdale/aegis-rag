"""Unit tests for text chunker."""

from app.ingestion.chunking.text_chunker import TextChunker


def test_chunker_short_text():
    """Short text smaller than chunk_size should return a single chunk."""
    chunker = TextChunker(chunk_size=500, chunk_overlap=50)
    text = "AegisRAG is a production-grade RAG system."
    chunks = chunker.chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunker_empty_text():
    """Empty or whitespace text returns empty list."""
    chunker = TextChunker(chunk_size=500, chunk_overlap=50)
    assert chunker.chunk_text("") == []
    assert chunker.chunk_text("   \n\t  ") == []


def test_chunker_paragraph_splitting():
    """Paragraphs are preserved and grouped up to chunk_size."""
    chunker = TextChunker(chunk_size=50, chunk_overlap=15)
    text = "First paragraph content here.\n\nSecond paragraph content with more words.\n\nThird paragraph."
    chunks = chunker.chunk_text(text)

    assert len(chunks) >= 2
    assert all(len(c) <= 150 for c in chunks)


def test_chunker_overlap():
    """Adjacent chunks should share overlap content."""
    chunker = TextChunker(chunk_size=60, chunk_overlap=25)
    text = "Alpha Beta Gamma Delta. Epsilon Zeta Eta Theta. Iota Kappa Lambda Mu."
    chunks = chunker.chunk_text(text)
    assert len(chunks) >= 2
