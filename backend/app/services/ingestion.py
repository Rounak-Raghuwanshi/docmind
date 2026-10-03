"""The ingestion pipeline, run by the ARQ worker:

    load file -> parse pages (OCR fallback) -> clean -> chunk -> embed -> store -> ready
                                                                         \\-> enrich (separate job)

Jobs are idempotent: chunks are replaced wholesale in one transaction, so a retry or a
reprocess can never leave half-indexed documents behind.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.llm.base import LLMClient
from app.models import DocStatus, Document
from app.rag.chunker import chunk_pages
from app.rag.cleaner import clean_pages
from app.rag.embedder import Embedder
from app.rag.parser import IngestionError, count_pages, iter_pages
from app.rag.prompts import enrich_messages
from app.rag.types import Page
from app.repositories import documents as repo
from app.repositories.workspaces import bump_corpus_version
from app.services.documents import document_event
from app.services.events import publish_document_event
from app.services.storage import Storage

log = logging.getLogger(__name__)

PROGRESS_INTERVAL_S = 0.75


class Ingestor:
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        redis: Redis,
        storage: Storage,
        embedder: Embedder,
    ) -> None:
        self.sessionmaker = sessionmaker
        self.redis = redis
        self.storage = storage
        self.embedder = embedder
        self.settings = get_settings()

    async def _update(
        self, document_id: uuid.UUID, stage: str | None = None, **values: Any
    ) -> Document | None:
        async with self.sessionmaker() as session:
            doc = await session.get(Document, document_id)
            if doc is None:
                return None
            for k, v in values.items():
                setattr(doc, k, v)
            await session.commit()
            await publish_document_event(self.redis, doc.workspace_id, document_event(doc, stage))
            return doc

    async def run(self, document_id: uuid.UUID) -> bool:
        """Returns False if the document no longer exists (deleted while queued)."""
        started = time.perf_counter()
        doc = await self._update(
            document_id,
            stage="parsing",
            status=DocStatus.processing,
            pages_done=0,
            error_message=None,
        )
        if doc is None:
            return False

        data = await self.storage.get(doc.storage_key)
        total = await asyncio.to_thread(count_pages, doc.content_type, data)
        if total == 0:
            raise IngestionError("The document has no pages")
        await self._update(document_id, stage="parsing", pages_total=total)

        pages = await self._parse_with_progress(document_id, doc.content_type, data, total)
        cleaned = clean_pages(pages)
        if sum(len(p.text) for p in cleaned) < 20:
            hint = "" if self.settings.ocr_enabled else " (OCR is disabled)"
            raise IngestionError(f"No readable text found in this document{hint}")

        title = doc.filename.rsplit(".", 1)[0]
        drafts = chunk_pages(
            cleaned,
            title=title,
            target_tokens=self.settings.chunk_tokens,
            overlap_tokens=self.settings.chunk_overlap_tokens,
        )
        await self._update(document_id, stage="embedding")
        vectors = await asyncio.to_thread(
            self.embedder.embed_documents, [d.embedding_text for d in drafts]
        )
        for draft, vec in zip(drafts, vectors, strict=True):
            draft.embedding = vec

        async with self.sessionmaker() as session:
            fresh = await session.get(Document, document_id, with_for_update=True)
            if fresh is None:  # deleted mid-flight
                return False
            await repo.replace_chunks(session, fresh, drafts)
            fresh.status = DocStatus.ready
            fresh.pages_done = total
            fresh.chunk_count = len(drafts)
            fresh.embedding_model = self.embedder.name
            fresh.processed_at = datetime.now(UTC)
            await bump_corpus_version(session, fresh.workspace_id)
            await session.commit()
            await publish_document_event(self.redis, fresh.workspace_id, document_event(fresh))

        log.info(
            "document ready",
            extra={
                "document_id": str(document_id),
                "pages": total,
                "chunks": len(drafts),
                "ocr_pages": sum(p.ocr for p in pages),
                "seconds": round(time.perf_counter() - started, 2),
            },
        )
        return True

    async def _parse_with_progress(
        self, document_id: uuid.UUID, content_type: str, data: bytes, total: int
    ) -> list[Page]:
        """Parse in a thread, publishing page progress (OCR pages can take seconds each)."""
        loop = asyncio.get_running_loop()
        progress: asyncio.Queue[int] = asyncio.Queue()
        s = self.settings

        def work() -> list[Page]:
            out = []
            for page in iter_pages(
                content_type,
                data,
                ocr_enabled=s.ocr_enabled,
                ocr_min_chars=s.ocr_min_chars,
                ocr_dpi=s.ocr_dpi,
            ):
                out.append(page)
                loop.call_soon_threadsafe(progress.put_nowait, len(out))
            return out

        task = asyncio.ensure_future(asyncio.to_thread(work))
        last_sent = 0.0
        done = 0
        while not task.done():
            try:
                done = await asyncio.wait_for(progress.get(), timeout=0.25)
            except TimeoutError:
                continue
            now = time.monotonic()
            if now - last_sent >= PROGRESS_INTERVAL_S and done < total:
                last_sent = now
                await self._update(document_id, stage="parsing", pages_done=done)
        return await task

    async def mark_failed(self, document_id: uuid.UUID, message: str) -> None:
        await self._update(document_id, status=DocStatus.failed, error_message=message[:500])


async def enrich_document(
    sessionmaker: async_sessionmaker[AsyncSession],
    redis: Redis,
    llm: LLMClient,
    document_id: uuid.UUID,
) -> None:
    """Summary + suggested questions. Best effort: failure never fails the document."""
    async with sessionmaker() as session:
        doc = await session.get(Document, document_id)
        if doc is None or doc.status != DocStatus.ready:
            return
        text = await repo.first_chunks_text(session, document_id, max_chars=6000)
        filename = doc.filename
    if not text:
        return
    try:
        raw = await llm.complete(enrich_messages(filename, text), max_tokens=400)
        parsed = _parse_json_object(raw)
        summary = str(parsed.get("summary", "")).strip()[:1500] or None
        questions = [str(q).strip()[:300] for q in parsed.get("questions", []) if str(q).strip()][
            :3
        ]
    except Exception:
        log.warning("enrichment failed", extra={"document_id": str(document_id)}, exc_info=True)
        return
    async with sessionmaker() as session:
        doc = await session.get(Document, document_id)
        if doc is None:
            return
        doc.summary = summary
        doc.suggested_questions = questions or None
        await session.commit()
        await publish_document_event(redis, doc.workspace_id, document_event(doc))


def _parse_json_object(raw: str) -> dict[str, Any]:
    """Small models wrap JSON in prose or code fences; take the outermost object."""
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in LLM output")
    value = json.loads(raw[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value
