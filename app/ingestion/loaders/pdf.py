"""PDF document loader extracting page-aware text."""

import io
from typing import List, Optional, Tuple

from pypdf import PdfReader

from app.ingestion.loaders.base import BaseLoader


class PDFLoader(BaseLoader):
    """Extracts text page by page from PDF files using pypdf."""

    def extract_text(self, content: bytes) -> List[Tuple[str, Optional[int]]]:
        reader = PdfReader(io.BytesIO(content))
        pages_text: List[Tuple[str, Optional[int]]] = []

        for page_idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            cleaned = text.strip()
            if cleaned:
                pages_text.append((cleaned, page_idx))

        return pages_text
