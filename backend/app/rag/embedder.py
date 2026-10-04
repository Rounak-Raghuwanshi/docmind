"""Embedding models are loaded once per process and called from a worker thread."""

import hashlib
import logging
import math
import re
from functools import lru_cache
from typing import Protocol

import numpy as np

from app.config import get_settings

log = logging.getLogger(__name__)

# bge v1.5 models are trained with this instruction on the *query* side only.
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
BATCH_SIZE = 32


class Embedder(Protocol):
    name: str
    dim: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


def _normalise(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


class FastEmbedEmbedder:
    def __init__(self, model_name: str, cache_dir: str | None = None) -> None:
        from fastembed import TextEmbedding

        log.info("loading embedding model", extra={"model": model_name})
        self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)
        self.name = model_name
        self.dim = len(next(iter(self._model.embed(["warmup"]))))
        self._query_prefix = BGE_QUERY_PREFIX if "bge" in model_name.lower() else ""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = np.array(list(self._model.embed(texts, batch_size=BATCH_SIZE)))
        return _normalise(vectors).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([self._query_prefix + text])[0]


class HashingEmbedder:
    """Deterministic bag-of-words embedder for tests: no model download, still meaningful."""

    _TOKEN = re.compile(r"[a-z0-9]+")

    def __init__(self, dim: int = 384, name: str = "fake-hashing") -> None:
        self.name = name
        self.dim = dim

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in self._TOKEN.findall(text.lower()):
            h = int(hashlib.md5(tok.encode(), usedforsecurity=False).hexdigest(), 16)
            vec[h % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


@lru_cache
def get_embedder() -> Embedder:
    s = get_settings()
    if s.embedding_provider == "fake":
        return HashingEmbedder(s.embedding_dim)
    if s.embedding_provider == "hashing":
        # Lite mode: no model in memory. Similarity = shared words, so keyword search and the
        # LLM carry answer quality.
        return HashingEmbedder(s.embedding_dim, name="hashing-bow-384")
    embedder = FastEmbedEmbedder(s.embedding_model, s.models_cache_dir)
    if embedder.dim != s.embedding_dim:
        raise RuntimeError(
            f"{s.embedding_model} produces {embedder.dim}-d vectors but the schema is "
            f"{s.embedding_dim}-d; add a migration before switching models"
        )
    return embedder
