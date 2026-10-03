"""The two retrieval queries. Both are scoped by workspace_id in SQL — the tenant boundary is
enforced by the database query itself, never by filtering results in Python afterwards."""

import re
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_WORD = re.compile(r"[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*")


def keyword_query(question: str) -> str:
    """OR the question's terms for websearch_to_tsquery.

    Plain websearch_to_tsquery ANDs every word, so a natural-language question rarely matches
    anything. ORing terms and ranking with ts_rank_cd rewards chunks that contain more of them
    (and exact tokens like "80D" or "GSTR-3B" that embeddings tend to blur).
    """
    terms = [t for t in _WORD.findall(question) if t.lower() not in {"or", "and", "not"}]
    return " or ".join(terms[:32])


def _doc_filter_sql(document_ids: list[uuid.UUID] | None) -> str:
    return " AND c.document_id = ANY(:doc_ids)" if document_ids else ""


async def vector_search(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    query_embedding: list[float],
    limit: int,
    document_ids: list[uuid.UUID] | None,
    ef_search: int,
    iterative_scan: bool,
) -> list[tuple[uuid.UUID, float]]:
    # SET LOCAL lasts for this transaction only. iterative_scan (pgvector >= 0.8) keeps
    # scanning the HNSW graph when the workspace filter removes most nearest neighbours.
    await session.execute(text(f"SET LOCAL hnsw.ef_search = {int(ef_search)}"))
    if iterative_scan:
        await session.execute(text("SET LOCAL hnsw.iterative_scan = relaxed_order"))
    sql = text(
        f"""
        SELECT c.id, 1 - (c.embedding <=> CAST(:qv AS vector)) AS score
        FROM chunks c
        WHERE c.workspace_id = :ws{_doc_filter_sql(document_ids)}
        ORDER BY c.embedding <=> CAST(:qv AS vector)
        LIMIT :limit
        """  # noqa: S608 - only a fixed fragment is interpolated
    )
    params: dict[str, Any] = {"qv": _vec(query_embedding), "ws": workspace_id, "limit": limit}
    if document_ids:
        params["doc_ids"] = document_ids
    rows = (await session.execute(sql, params)).all()
    # relaxed_order may return slightly out-of-order rows; re-sort by exact score.
    return sorted(((r[0], float(r[1])) for r in rows), key=lambda r: r[1], reverse=True)


async def keyword_search(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    question: str,
    limit: int,
    document_ids: list[uuid.UUID] | None,
) -> list[tuple[uuid.UUID, float]]:
    q = keyword_query(question)
    if not q:
        return []
    sql = text(
        f"""
        SELECT c.id, ts_rank_cd(c.search_vector, query) AS score
        FROM chunks c, websearch_to_tsquery('english', :q) AS query
        WHERE c.workspace_id = :ws AND c.search_vector @@ query{_doc_filter_sql(document_ids)}
        ORDER BY score DESC
        LIMIT :limit
        """  # noqa: S608
    )
    params: dict[str, Any] = {"q": q, "ws": workspace_id, "limit": limit}
    if document_ids:
        params["doc_ids"] = document_ids
    return [(r[0], float(r[1])) for r in (await session.execute(sql, params)).all()]


async def load_chunks(
    session: AsyncSession, workspace_id: uuid.UUID, chunk_ids: list[uuid.UUID]
) -> dict[uuid.UUID, dict[str, Any]]:
    if not chunk_ids:
        return {}
    sql = text(
        """
        SELECT c.id, c.document_id, d.filename, c.page_start, c.page_end, c.context, c.content
        FROM chunks c JOIN documents d ON d.id = c.document_id
        WHERE c.workspace_id = :ws AND c.id = ANY(:ids)
        """
    )
    rows = (await session.execute(sql, {"ws": workspace_id, "ids": chunk_ids})).mappings().all()
    return {
        r["id"]: {
            "chunk_id": r["id"],
            "document_id": r["document_id"],
            "filename": r["filename"],
            "page_start": r["page_start"],
            "page_end": r["page_end"],
            "context": r["context"],
            "content": r["content"],
        }
        for r in rows
    }


def _vec(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.7g}" for v in values) + "]"
