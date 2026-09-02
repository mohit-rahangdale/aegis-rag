"""Text chunking utility preserving paragraph and sentence boundaries with overlap."""

import re
from typing import List


class TextChunker:
    """Splits raw text into overlapping windows respecting natural boundaries."""

    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 100) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks of roughly chunk_size characters with overlap."""
        cleaned = text.strip()
        if not cleaned:
            return []

        if len(cleaned) <= self.chunk_size:
            return [cleaned]

        # Natural separator hierarchy
        paragraphs = re.split(r"\n\s*\n", cleaned)
        chunks: List[str] = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If a single paragraph is too large, split by sentences or punctuation
            if len(para) > self.chunk_size:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue

                    if len(current_chunk) + len(sentence) + 1 <= self.chunk_size:
                        current_chunk = f"{current_chunk} {sentence}".strip()
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                            # Overlap from the end of current chunk
                            overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                            current_chunk = f"{current_chunk[overlap_start:]} {sentence}".strip()
                        else:
                            # Sentence itself is longer than chunk_size, split by words
                            words = sentence.split()
                            word_chunk = ""
                            for word in words:
                                if len(word_chunk) + len(word) + 1 <= self.chunk_size:
                                    word_chunk = f"{word_chunk} {word}".strip()
                                else:
                                    if word_chunk:
                                        chunks.append(word_chunk)
                                    word_chunk = word
                            if word_chunk:
                                current_chunk = word_chunk
            else:
                if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                    current_chunk = f"{current_chunk}\n\n{para}".strip() if current_chunk else para
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                        overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                        current_chunk = f"{current_chunk[overlap_start:]}\n\n{para}".strip()
                    else:
                        current_chunk = para

        if current_chunk and (not chunks or current_chunk != chunks[-1]):
            chunks.append(current_chunk)

        return chunks
