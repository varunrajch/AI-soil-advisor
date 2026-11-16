"""A small on-disk vector index (numpy) with cosine-similarity search."""
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Protocol, Sequence, Tuple

import numpy as np

from .chunking import Chunk

logger = logging.getLogger("nela.rag")


class Embedder(Protocol):
    def embed(self, texts: Sequence[str]) -> np.ndarray: ...


class FastEmbedder:
    """Local ONNX embeddings (bge-small, 384-d). No API calls, works offline after first download."""

    def __init__(self, model_name: str):
        from fastembed import TextEmbedding

        self.model = TextEmbedding(model_name)

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        return np.array(list(self.model.embed(list(texts))), dtype=np.float32)


@lru_cache(maxsize=2)
def get_embedder(model_name: str) -> FastEmbedder:
    return FastEmbedder(model_name)


def _normalise(m: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    return m / np.clip(norms, 1e-12, None)


class VectorIndex:
    def __init__(self, chunks: List[Chunk], vectors: np.ndarray):
        assert len(chunks) == len(vectors), "chunks and vectors out of sync"
        self.chunks = chunks
        self.vectors = _normalise(vectors.astype(np.float32)) if len(vectors) else vectors

    @classmethod
    def build(cls, chunks: List[Chunk], embedder: Embedder, batch: int = 64) -> "VectorIndex":
        parts = [embedder.embed([c.text for c in chunks[i:i + batch]]) for i in range(0, len(chunks), batch)]
        vectors = np.vstack(parts) if parts else np.zeros((0, 1), dtype=np.float32)
        return cls(chunks, vectors)

    def search(self, query_vec: np.ndarray, k: int = 3, min_score: float = 0.0) -> List[Tuple[Chunk, float]]:
        if not self.chunks:
            return []
        q = query_vec / max(np.linalg.norm(query_vec), 1e-12)
        scores = self.vectors @ q
        top = np.argsort(-scores)[:k]
        return [(self.chunks[i], float(scores[i])) for i in top if scores[i] >= min_score]

    def save(self, index_dir: Path) -> None:
        index_dir.mkdir(parents=True, exist_ok=True)
        np.save(index_dir / "vectors.npy", self.vectors)
        (index_dir / "chunks.json").write_text(
            json.dumps([c.to_dict() for c in self.chunks], ensure_ascii=False, indent=0))

    @classmethod
    def load(cls, index_dir: Path) -> Optional["VectorIndex"]:
        vec_path, chunk_path = index_dir / "vectors.npy", index_dir / "chunks.json"
        if not (vec_path.exists() and chunk_path.exists()):
            logger.warning("rag.index_missing", extra={"extra_fields": {"dir": str(index_dir)}})
            return None
        chunks = [Chunk(**c) for c in json.loads(chunk_path.read_text())]
        return cls(chunks, np.load(vec_path))
