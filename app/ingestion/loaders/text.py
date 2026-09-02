"""Plain text file loader."""

from typing import List, Optional, Tuple

from app.ingestion.loaders.base import BaseLoader


class TextLoader(BaseLoader):
    """Extracts text from raw UTF-8 / ASCII encoded files."""

    def extract_text(self, content: bytes) -> List[Tuple[str, Optional[int]]]:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1", errors="replace")

        cleaned = text.strip()
        if not cleaned:
            return []
        return [(cleaned, None)]
