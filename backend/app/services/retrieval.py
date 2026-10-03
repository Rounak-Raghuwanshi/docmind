"""Hybrid retrieval: vector + full-text search in parallel, fused with RRF, then reranked."""

import asyncio
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.rag.embedder import Embedder
from app.rag.fusion import reciprocal_rank_fusion
from app.rag.reranker import Reranker
from app.repositories import retrieval as repo

Mode = Literal["vector", "keyword", "hybrid", "hybrid_rerank"]


@dataclass(slots=True)
class RetrievedChunk:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    page_start: int
    page_end: int
    context: str
    content: str
    vector_rank: int | None = None
    vector_score: float | None = None
    keyword_rank: int | None = None
    keyword_score: float | None = None
    rrf_score: float | None = None
    rerank_score: float | None = None

    @property
    def score(self) -> float:
        for s in (self.rerank_score, self.rrf_score, self.vector_score, self.keyword_score):
            if s is not None:
                return s
        return 0.0

    def as_source(self) -> dict[str, Any]:
        return asdict(self)

    def debug(self) -> dict[str, Any]:
        d = {k: (str(v) if isinstance(v, uuid.UUID) else v) for k, v in asdict(self).items()}
        d["content"] = self.content[:600]
        return d


@dataclass(slots=True)
class RetrievalResult:
    chunks: list[RetrievedChunk]
    retrieval_ms: int
    rerank_ms: int
    reranked: bool

    @property
    def top_rerank_score(self) -> float | None:
        return self.chunks[0].rerank_score if self.reranked and self.chunks else None


class Retriever:
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        embedder: Embedder,
        reranker: Reranker | None,
        settings: Settings,
    ) -> None:
        self.sessionmaker = sessionmaker
        self.embedder = embedder
        self.reranker = reranker
        self.settings = settings

    async def _vector(
        self, ws: uuid.UUID, query: str, doc_ids: list[uuid.UUID] | None
    ) -> list[tuple[uuid.UUID, float]]:
        embedding = await asyncio.to_thread(self.embedder.embed_query, query)
        async with self.sessionmaker() as session, session.begin():
            return await repo.vector_search(
                session,
                ws,
                embedding,
                self.settings.retrieval_candidates,
                doc_ids,
                self.settings.hnsw_ef_search,
                self.settings.hnsw_iterative_scan,
            )

    async def _keyword(
        self, ws: uuid.UUID, query: str, doc_ids: list[uuid.UUID] | None
    ) -> list[tuple[uuid.UUID, float]]:
        async with self.sessionmaker() as session:
            return await repo.keyword_search(
                session, ws, query, self.settings.retrieval_candidates, doc_ids
            )

    async def search(
        self,
        workspace_id: uuid.UUID,
        query: str,
        *,
        document_ids: list[uuid.UUID] | None = None,
        mode: Mode = "hybrid_rerank",
        top_k: int | None = None,
    ) -> RetrievalResult:
        top_k = top_k or self.settings.retrieval_top_k
        started = time.perf_counter()

        empty: list[tuple[uuid.UUID, float]] = []
        vector_hits, keyword_hits = await asyncio.gather(
            self._vector(workspace_id, query, document_ids) if mode != "keyword" else _const(empty),
            self._keyword(workspace_id, query, document_ids) if mode != "vector" else _const(empty),
        )

        vec_rank = {cid: (i, s) for i, (cid, s) in enumerate(vector_hits, start=1)}
        kw_rank = {cid: (i, s) for i, (cid, s) in enumerate(keyword_hits, start=1)}

        if mode == "vector":
            ordered: list[tuple[uuid.UUID, float | None]] = [(c, None) for c, _ in vector_hits]
        elif mode == "keyword":
            ordered = [(c, None) for c, _ in keyword_hits]
        else:
            fused = reciprocal_rank_fusion(
                [[c for c, _ in vector_hits], [c for c, _ in keyword_hits]], k=self.settings.rrf_k
            )
            ordered = [(c, s) for c, s in fused[: self.settings.retrieval_candidates]]

        async with self.sessionmaker() as session:
            rows = await repo.load_chunks(session, workspace_id, [c for c, _ in ordered])

        candidates: list[RetrievedChunk] = []
        for cid, rrf in ordered:
            row = rows.get(cid)
            if row is None:
                continue  # deleted between search and load
            vr, kr = vec_rank.get(cid), kw_rank.get(cid)
            candidates.append(
                RetrievedChunk(
                    **row,
                    vector_rank=vr[0] if vr else None,
                    vector_score=vr[1] if vr else None,
                    keyword_rank=kr[0] if kr else None,
                    keyword_score=kr[1] if kr else None,
                    rrf_score=rrf,
                )
            )
        retrieval_ms = _ms(started)

        rerank_ms = 0
        reranked = False
        if mode == "hybrid_rerank" and self.reranker is not None and candidates:
            t = time.perf_counter()
            texts = [f"{c.context}\n{c.content}" for c in candidates]
            scores = await asyncio.to_thread(self.reranker.score, query, texts)
            for c, s in zip(candidates, scores, strict=True):
                c.rerank_score = s
            candidates.sort(key=lambda c: c.rerank_score or 0.0, reverse=True)
            rerank_ms = _ms(t)
            reranked = True

        return RetrievalResult(candidates[:top_k], retrieval_ms, rerank_ms, reranked)


async def _const[T](value: T) -> T:
    return value


def _ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)
