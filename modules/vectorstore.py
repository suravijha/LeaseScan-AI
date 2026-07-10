"""
Embeddings + FAISS vector store.

This is the retrieval half of the RAG pipeline: chunks are embedded
locally with sentence-transformers (no extra API cost/latency per
chunk) and indexed in FAISS for fast nearest-neighbor lookup. Agents
and the chat feature both query this index instead of re-sending the
entire lease to Gemini on every call.
"""

from dataclasses import dataclass

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from modules.chunking import Chunk

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float  # lower = more similar (L2 distance)


class LeaseVectorStore:
    """Wraps a FAISS flat-L2 index over embedded lease chunks."""

    def __init__(self, model: SentenceTransformer):
        self._model = model
        self._index: faiss.IndexFlatL2 | None = None
        self._chunks: list[Chunk] = []

    @classmethod
    def build(cls, chunks: list[Chunk], model: SentenceTransformer) -> "LeaseVectorStore":
        store = cls(model)
        store._chunks = chunks

        if not chunks:
            return store

        texts = [c.text for c in chunks]
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        embeddings = np.asarray(embeddings, dtype="float32")

        index = faiss.IndexFlatL2(embeddings.shape[1])
        index.add(embeddings)
        store._index = index
        return store

    def search(self, query: str, k: int = 4) -> list[RetrievedChunk]:
        if self._index is None or not self._chunks:
            return []

        query_vec = self._model.encode([query], normalize_embeddings=True, show_progress_bar=False)
        query_vec = np.asarray(query_vec, dtype="float32")

        k = min(k, len(self._chunks))
        distances, indices = self._index.search(query_vec, k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            results.append(RetrievedChunk(chunk=self._chunks[idx], score=float(dist)))
        return results

    def __len__(self) -> int:
        return len(self._chunks)


def load_embedding_model() -> SentenceTransformer:
    """Load the sentence-transformers model.

    Callers should wrap this with st.cache_resource so the model is
    only downloaded/loaded once per app process, not once per rerun.
    """
    return SentenceTransformer(EMBEDDING_MODEL_NAME)
