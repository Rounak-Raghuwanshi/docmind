import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import delete, insert, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Document
from app.rag.types import ChunkDraft


async def list_documents(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    status: str | None,
    limit: int,
    after: tuple[datetime, uuid.UUID] | None,
) -> list[Document]:
    stmt = (
        select(Document)
        .where(Document.workspace_id == workspace_id)
        .order_by(Document.created_at.desc(), Document.id.desc())
        .limit(limit)
    )
    if status:
        stmt = stmt.where(Document.status == status)
    if after:
        stmt = stmt.where(tuple_(Document.created_at, Document.id) < tuple_(*after))
    return list((await session.execute(stmt)).scalars())


async def find_duplicate(
    session: AsyncSession, workspace_id: uuid.UUID, sha256: str
) -> Document | None:
    return (
        await session.execute(
            select(Document).where(Document.workspace_id == workspace_id, Document.sha256 == sha256)
        )
    ).scalar_one_or_none()


async def replace_chunks(
    session: AsyncSession, document: Document, drafts: list[ChunkDraft]
) -> None:
    """Idempotent: re-running ingestion replaces the document's chunks wholesale."""
    await session.execute(delete(Chunk).where(Chunk.document_id == document.id))
    rows: list[dict[str, Any]] = [
        {
            "id": uuid.uuid4(),
            "document_id": document.id,
            "workspace_id": document.workspace_id,
            "chunk_index": d.index,
            "page_start": d.page_start,
            "page_end": d.page_end,
            "context": d.context,
            "content": d.content,
            "token_count": d.token_count,
            "embedding": d.embedding,
        }
        for d in drafts
    ]
    for i in range(0, len(rows), 500):
        await session.execute(insert(Chunk), rows[i : i + 500])


async def page_chunks(session: AsyncSession, document_id: uuid.UUID, page: int) -> list[str]:
    rows = await session.execute(
        select(Chunk.content)
        .where(Chunk.document_id == document_id, Chunk.page_start <= page, Chunk.page_end >= page)
        .order_by(Chunk.chunk_index)
    )
    return list(rows.scalars())


async def first_chunks_text(session: AsyncSession, document_id: uuid.UUID, max_chars: int) -> str:
    rows = await session.execute(
        select(Chunk.content)
        .where(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index)
        .limit(12)
    )
    text = ""
    for content in rows.scalars():
        if len(text) + len(content) > max_chars:
            break
        text += content + "\n\n"
    return text.strip()
