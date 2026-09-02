"""Loaders package for various document formats."""

from app.ingestion.loaders.base import BaseLoader
from app.ingestion.loaders.markdown import MarkdownLoader
from app.ingestion.loaders.pdf import PDFLoader
from app.ingestion.loaders.text import TextLoader


def get_loader_for_file(filename: str, content_type: str = "") -> BaseLoader:
    """Return appropriate loader based on filename extension or MIME content type."""
    lower_name = filename.lower()
    lower_type = content_type.lower()

    if lower_name.endswith(".pdf") or "pdf" in lower_type:
        return PDFLoader()
    if lower_name.endswith((".md", ".markdown")) or "markdown" in lower_type:
        return MarkdownLoader()
    return TextLoader()


__all__ = [
    "BaseLoader",
    "PDFLoader",
    "MarkdownLoader",
    "TextLoader",
    "get_loader_for_file",
]
