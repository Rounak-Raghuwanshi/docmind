import logging
import re
from functools import lru_cache
from typing import Protocol

from app.config import get_settings

log = logging.getLogger(__name__)


class Reranker(Protocol):
    def score(self, query: str, documents: list[str]) -> list[float]: ...


class FastEmbedReranker:
    """Cross-encoder: reads query and passage together, far more precise than bi-encoders."""

    def __init__(self, model_name: str, cache_dir: str | None = None) -> None:
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        log.info("loading reranker model", extra={"model": model_name})
        self._model = TextCrossEncoder(model_name=model_name, cache_dir=cache_dir)

    def score(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        return [float(s) for s in self._model.rerank(query, documents, batch_size=32)]


class OverlapReranker:
    """Test double: scores by query-term overlap on a logit-like scale."""

    _TOKEN = re.compile(r"[a-z0-9]+")

    def score(self, query: str, documents: list[str]) -> list[float]:
        q = set(self._TOKEN.findall(query.lower()))
        out = []
        for doc in documents:
            d = set(self._TOKEN.findall(doc.lower()))
            overlap = len(q & d) / (len(q) or 1)
            out.append(overlap * 10 - 5)  # 0 overlap -> -5, full overlap -> +5
        return out


@lru_cache
def get_reranker() -> Reranker | None:
    s = get_settings()
    if s.rerank_provider == "none":
        return None
    if s.rerank_provider == "fake":
        return OverlapReranker()
    return FastEmbedReranker(s.rerank_model, s.models_cache_dir)
