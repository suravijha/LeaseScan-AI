"""
Document chunking.

Splits lease text into overlapping, page-aware chunks so retrieval
can point back to a specific page (needed for evidence citations
and clause highlighting in the UI).
"""

from dataclasses import dataclass

from modules.pdf_processor import PageText


@dataclass
class Chunk:
    chunk_id: int
    text: str
    page_number: int


def chunk_pages(
    pages: list[PageText],
    chunk_size: int = 900,
    overlap: int = 150,
) -> list[Chunk]:
    """Split each page's text into overlapping character chunks.

    Chunking per-page (rather than across the whole document) keeps
    the page attribution exact, at the small cost of occasionally
    splitting a clause across a page boundary - an acceptable
    trade-off for evidence citations.
    """
    chunks: list[Chunk] = []
    chunk_id = 0

    for page in pages:
        text = page.text.strip()
        if not text:
            continue

        if len(text) <= chunk_size:
            chunks.append(Chunk(chunk_id=chunk_id, text=text, page_number=page.page_number))
            chunk_id += 1
            continue

        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            piece = text[start:end].strip()
            if piece:
                chunks.append(Chunk(chunk_id=chunk_id, text=piece, page_number=page.page_number))
                chunk_id += 1
            if end == len(text):
                break
            start = end - overlap

    return chunks
