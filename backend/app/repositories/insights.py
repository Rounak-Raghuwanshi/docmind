"""AI analysis over a workspace: the shape of its embedding space and how retrieval behaves."""

import math
import re
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Document

MAX_POINTS = 1500
BIN_WIDTH = 2.0
BIN_MIN, BIN_MAX = -12.0, 10.0


async def embedding_points(session: AsyncSession, workspace_id: uuid.UUID) -> list[dict[str, Any]]:
    total = await session.scalar(select(func.count()).where(Chunk.workspace_id == workspace_id))
    stmt = (
        select(
            Chunk.id,
            Chunk.document_id,
            Chunk.page_start,
            Chunk.content,
            Chunk.embedding,
            Document.filename,
        )
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.workspace_id == workspace_id)
    )
    # Large corpora: a random sample keeps the map fast and still shows the structure.
    stmt = stmt.order_by(func.random()).limit(MAX_POINTS) if (total or 0) > MAX_POINTS else stmt
    rows = (await session.execute(stmt)).all()
    return [
        {
            "chunk_id": str(r.id),
            "document_id": str(r.document_id),
            "filename": r.filename,
            "page": r.page_start,
            "preview": r.content[:160],
            "embedding": np.asarray(r.embedding, dtype=np.float32),
        }
        for r in rows
    ]


def project_3d(points: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[float]]:
    """PCA: the three directions along which the chunk embeddings vary the most.

    Chunks about similar topics sit close together in the 384-d space, and PCA keeps as much
    of that structure as three axes can. Coordinates are scaled to [-1, 1].
    """
    if not points:
        return [], [0.0, 0.0, 0.0]
    x = np.stack([p.pop("embedding") for p in points])
    x = x - x.mean(axis=0)
    if len(points) < 2:
        coords = np.zeros((len(points), 3))
        ratio = [0.0, 0.0, 0.0]
    else:
        _, s, vt = np.linalg.svd(x, full_matrices=False)
        k = min(3, vt.shape[0])
        coords = x @ vt[:k].T
        if k < 3:
            coords = np.hstack([coords, np.zeros((len(points), 3 - k))])
        var = s**2
        ratio = [float(v) for v in (var[:3] / var.sum() if var.sum() else var[:3])]
        ratio += [0.0] * (3 - len(ratio))
        scale = float(np.abs(coords).max()) or 1.0
        coords = coords / scale
    for p, (cx, cy, cz) in zip(points, coords, strict=True):
        p.update(x=round(float(cx), 4), y=round(float(cy), 4), z=round(float(cz), 4))
    return points, [round(r, 4) for r in ratio]


async def answer_rows(
    session: AsyncSession, workspace_id: uuid.UUID, days: int
) -> list[dict[str, Any]]:
    since = datetime.now(UTC) - timedelta(days=days)
    rows = await session.execute(
        text(
            """
            SELECT m.citations, m.retrieval_debug, m.not_found, m.cached,
                   coalesce(m.rewritten_question, '') AS question
            FROM messages m JOIN conversations c ON c.id = m.conversation_id
            WHERE c.workspace_id = :ws AND m.role = 'assistant' AND m.created_at >= :since
            """
        ),
        {"ws": workspace_id, "since": since},
    )
    return [dict(r) for r in rows.mappings()]


def retrieval_sources(rows: list[dict[str, Any]]) -> dict[str, int]:
    """For each cited chunk: was it found by vector search, keyword search, or both?"""
    counts = {"both": 0, "vector_only": 0, "keyword_only": 0}
    for r in rows:
        debug = {d["chunk_id"]: d for d in (r["retrieval_debug"] or [])}
        for c in r["citations"] or []:
            d = debug.get(c["chunk_id"])
            if not d:
                continue
            v, k = d.get("vector_rank") is not None, d.get("keyword_rank") is not None
            if v and k:
                counts["both"] += 1
            elif v:
                counts["vector_only"] += 1
            elif k:
                counts["keyword_only"] += 1
    return counts


def confidence_histogram(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Distribution of the best rerank score per question, split by answered vs not found."""
    edges = np.arange(BIN_MIN, BIN_MAX + BIN_WIDTH, BIN_WIDTH)
    bins = [
        {"start": float(lo), "end": float(lo + BIN_WIDTH), "answered": 0, "not_found": 0}
        for lo in edges[:-1]
    ]
    for r in rows:
        debug = r["retrieval_debug"] or []
        if r["cached"] or not debug or debug[0].get("rerank_score") is None:
            continue
        score = min(max(float(debug[0]["rerank_score"]), BIN_MIN), BIN_MAX - 1e-6)
        idx = math.floor((score - BIN_MIN) / BIN_WIDTH)
        bins[idx]["not_found" if r["not_found"] else "answered"] += 1
    return bins


_NORM = re.compile(r"[^a-z0-9 ]+")


def knowledge_gaps(rows: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    """Questions people asked that the documents couldn't answer: what to upload next."""
    counter: Counter[str] = Counter()
    original: dict[str, str] = {}
    for r in rows:
        if not r["not_found"] or not r["question"]:
            continue
        key = _NORM.sub("", r["question"].lower()).strip()
        counter[key] += 1
        original.setdefault(key, r["question"])
    return [{"question": original[k], "count": n} for k, n in counter.most_common(limit)]


async def document_coverage(
    session: AsyncSession, workspace_id: uuid.UUID, rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    cited: Counter[str] = Counter()
    for r in rows:
        for doc_id in {c["document_id"] for c in r["citations"] or []}:
            cited[doc_id] += 1
    docs = (
        await session.execute(
            select(Document.id, Document.filename, Document.chunk_count, Document.pages_total)
            .where(Document.workspace_id == workspace_id, Document.status == "ready")
            .order_by(Document.created_at)
        )
    ).all()
    return [
        {
            "document_id": str(d.id),
            "filename": d.filename,
            "chunks": d.chunk_count,
            "pages": d.pages_total,
            "answers": cited.get(str(d.id), 0),
        }
        for d in docs
    ]


def highlights(
    sources: dict[str, int],
    hist: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    threshold: float,
) -> list[str]:
    """Plain-language findings derived from the numbers above."""
    out: list[str] = []
    total = sum(sources.values())
    if total:
        rescued_kw = sources["keyword_only"] / total
        rescued_vec = sources["vector_only"] / total
        if rescued_kw or rescued_vec:
            out.append(
                f"Hybrid search paid off: {rescued_kw:.0%} of cited passages were found only by "
                f"keyword search and {rescued_vec:.0%} only by vector search. Either method alone "
                f"would have missed them."
            )
        else:
            out.append(
                "Every cited passage was found by both vector and keyword search. When the two "
                "methods agree, that's a strong sign the passage really is relevant."
            )
    answered = [b for b in hist if b["answered"]]
    refused = sum(b["not_found"] for b in hist)
    if answered:
        low = sum(b["answered"] for b in hist if b["end"] <= threshold + BIN_WIDTH)
        all_answered = sum(b["answered"] for b in hist)
        out.append(
            f"{all_answered} answers passed the relevance gate (threshold {threshold:g}); "
            f"{low} of them were close to it. Review those for weak sources."
        )
    if refused:
        out.append(
            f"The gate refused {refused} question(s) without calling the LLM, which prevented "
            f"made-up answers and saved quota."
        )
    if gaps:
        out.append(
            f"Most-asked unanswered topic: “{gaps[0]['question']}”. "
            "Consider uploading a document that covers it."
        )
    unused = [c["filename"] for c in coverage if c["answers"] == 0]
    if unused and len(unused) < len(coverage):
        out.append(f"Never cited yet: {', '.join(unused[:3])}{'…' if len(unused) > 3 else ''}.")
    return out
