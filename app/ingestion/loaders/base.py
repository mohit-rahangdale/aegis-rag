"""Base loader abstraction for document content extraction."""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple


class BaseLoader(ABC):
    """Abstract interface for extracting text content from file bytes."""

    @abstractmethod
    def extract_text(self, content: bytes) -> List[Tuple[str, Optional[int]]]:
        """Extract text chunks with optional page numbers.

        Returns:
            List of (text_content, page_number) tuples.
        """
        pass
