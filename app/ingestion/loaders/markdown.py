"""Markdown file loader and normalizer."""

import re
from typing import List, Optional, Tuple

from app.ingestion.loaders.base import BaseLoader


class MarkdownLoader(BaseLoader):
    """Extracts and normalizes Markdown documentation files."""

    def extract_text(self, content: bytes) -> List[Tuple[str, Optional[int]]]:
        try:
            raw_text = content.decode("utf-8")
        except UnicodeDecodeError:
            raw_text = content.decode("latin-1", errors="replace")

        # Normalize excessive blank lines while preserving paragraph boundaries
        cleaned = re.sub(r"\n{3,}", "\n\n", raw_text).strip()
        if not cleaned:
            return []
        return [(cleaned, None)]
