"""ARQ jobs. Each job gets shared resources (DB sessionmaker, Redis, models) from ctx."""

import logging
import uuid
from typing import Any

from arq import Retry
from sqlalchemy import select

from app.models import Conversation, DocStatus, Document
from app.rag.parser import IngestionError
from app.services.chat import heuristic_title
from app.services.ingestion import Ingestor, enrich_document

log = logging.getLogger(__name__)

MAX_TRIES = 3


async def ingest_document(ctx: dict[str, Any], document_id: str) -> None:
    doc_id = uuid.UUID(document_id)
    ingestor: Ingestor = ctx["ingestor"]
    attempt = ctx.get("job_try", 1)
    try:
        if not await ingestor.run(doc_id):
            return
    except IngestionError as e:
        # Permanent problem with the file itself (encrypted, corrupt, no text): don't retry.
        await ingestor.mark_failed(doc_id, str(e))
        return
    except Exception as e:
        if attempt < MAX_TRIES:
            log.warning(
                "ingestion failed; retrying",
                extra={"document_id": document_id, "attempt": attempt},
                exc_info=True,
            )
            await ingestor._update(doc_id, status=DocStatus.queued, stage="retrying")
            raise Retry(defer=5 * attempt**2) from e
        log.exception("ingestion failed permanently", extra={"document_id": document_id})
        await ingestor.mark_failed(
            doc_id, "Processing failed after several attempts. Try reprocessing."
        )
        return
    await ctx["redis"].enqueue_job("enrich_document", document_id)


async def enrich(ctx: dict[str, Any], document_id: str) -> None:
    await enrich_document(
        ctx["sessionmaker"], ctx["pubsub_redis"], ctx["llm"], uuid.UUID(document_id)
    )


async def generate_title(ctx: dict[str, Any], conversation_id: str, question: str) -> None:
    from app.rag.prompts import title_messages

    try:
        title = await ctx["llm"].complete(title_messages(question), max_tokens=24)
    except Exception:
        log.warning("title generation failed", exc_info=True)
        return
    title = title.strip().strip("\"'").strip().rstrip(".")[:120]
    if not title or "\n" in title:
        return
    async with ctx["sessionmaker"]() as session:
        conv = await session.get(Conversation, uuid.UUID(conversation_id))
        # Only replace our own placeholder, never a title the user has set.
        if conv is not None and conv.title == heuristic_title(question):
            conv.title = title
            await session.commit()


async def delete_storage_objects(ctx: dict[str, Any], keys: list[str]) -> None:
    for key in keys:
        try:
            await ctx["storage"].delete(key)
        except Exception:
            log.warning("failed to delete object", extra={"storage_key": key}, exc_info=True)


async def requeue_interrupted(ctx: dict[str, Any]) -> int:
    """On worker start, re-enqueue documents left queued/processing by a crash or redeploy.

    Fixed job ids make this safe: anything still genuinely queued is not duplicated.
    """
    async with ctx["sessionmaker"]() as session:
        rows = await session.execute(
            select(Document.id).where(Document.status.in_([DocStatus.queued, DocStatus.processing]))
        )
        ids = list(rows.scalars())
    for doc_id in ids:
        await ctx["redis"].enqueue_job("ingest_document", str(doc_id), _job_id=f"ingest:{doc_id}")
    if ids:
        log.info("re-enqueued interrupted documents", extra={"count": len(ids)})
    return len(ids)
