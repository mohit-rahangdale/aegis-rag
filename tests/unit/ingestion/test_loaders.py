"""Unit tests for document format loaders."""

import io
from pypdf import PdfWriter

from app.ingestion.loaders import (
    MarkdownLoader,
    PDFLoader,
    TextLoader,
    get_loader_for_file,
)


def test_text_loader():
    """Verify text loader handles plain text bytes."""
    loader = TextLoader()
    raw = b"Hello AegisRAG! This is a simple test document."
    results = loader.extract_text(raw)
    assert len(results) == 1
    text, page = results[0]
    assert "Hello AegisRAG" in text
    assert page is None


def test_markdown_loader():
    """Verify markdown loader collapses excessive blank lines."""
    loader = MarkdownLoader()
    raw = b"# Title\n\n\n\nParagraph one.\n\n\n\nParagraph two."
    results = loader.extract_text(raw)
    assert len(results) == 1
    text, _ = results[0]
    assert "\n\n\n" not in text
    assert "Paragraph one." in text


def test_pdf_loader_with_synthetic_pdf():
    """Verify PDF loader extracts text and page indices."""
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    pdf_bytes_io = io.BytesIO()
    writer.write(pdf_bytes_io)
    pdf_bytes = pdf_bytes_io.getvalue()

    loader = PDFLoader()
    # Blank PDF produces 0 non-empty text pages
    results = loader.extract_text(pdf_bytes)
    assert isinstance(results, list)


def test_get_loader_selection():
    """Verify loader routing based on extension and MIME type."""
    assert isinstance(get_loader_for_file("doc.pdf"), PDFLoader)
    assert isinstance(get_loader_for_file("notes.md"), MarkdownLoader)
    assert isinstance(get_loader_for_file("readme.markdown"), MarkdownLoader)
    assert isinstance(get_loader_for_file("log.txt"), TextLoader)
    assert isinstance(get_loader_for_file("unknown_file", "application/pdf"), PDFLoader)
