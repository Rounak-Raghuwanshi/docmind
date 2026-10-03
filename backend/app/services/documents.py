"""Upload validation and document lifecycle. Parsing and embedding never happen here —
they run in the ARQ worker so a 200-page upload can't slow anyone's chat down."""

import hashlib
import logging
import uuid
from pathlib import PurePath

from fastapi import UploadFile
from redis.asyncio import Redis
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.errors import AppError, Conflict, PayloadTooLarge, UnsupportedMediaType
from app.models import Chunk, DocStatus, Document, User
from app.rag.parser import IngestionError, detect_content_type
from app.redis_client import get_arq
from app.repositories import documents as repo
from app.repositories.workspaces import bump_corpus_version
from app.services.events import publish_document_event
from app.services.storage import get_storage

log = logging.getLogger(__name__)

READ_CHUNK = 1024 * 1024


def safe_filename(name: str | None) -> str:
    base = PurePath((name or "document").replace("\\", "/")).name.strip() or "document"
    return "".join(ch for ch in base if ch.isprintable())[:255]


async def read_limited(upload: UploadFile, limit: int) -> bytes:
    """Stream the upload into memory, aborting as soon as it exceeds the limit."""
    buf = bytearray()
    while chunk := await upload.read(READ_CHUNK):
        buf.extend(chunk)
        if len(buf) > limit:
            raise PayloadTooLarge(f"File exceeds the {limit // (1024 * 1024)} MB limit")
    return bytes(buf)


def document_event(doc: Document, stage: str | None = None) -> dict[str, object]:
    return {
        "type": "document",
        "document_id": str(doc.id),
        "status": doc.status,
        "pages_done": doc.pages_done,
        "pages_total": doc.pages_total,
        "error_message": doc.error_message,
        "stage": stage,
    }


async def enqueue_ingestion(document_id: uuid.UUID) -> bool:
    arq = await get_arq()
    # Fixed job id: enqueueing a document that is already queued/running is a no-op.
    job = await arq.enqueue_job(
        "ingest_document", str(document_id), _job_id=f"ingest:{document_id}"
    )
    return job is not None


async def upload(
    session: AsyncSession, redis: Redis, workspace_id: uuid.UUID, user: User, file: UploadFile
) -> Document:
    data = await read_limited(file, get_settings().max_upload_bytes)
    return await add_document(
        session, redis, workspace_id, user, safe_filename(file.filename), data
    )


async def add_document(
    session: AsyncSession,
    redis: Redis,
    workspace_id: uuid.UUID,
    user: User,
    filename: str,
    data: bytes,
) -> Document:
    if not data:
        raise AppError("The file is empty", code="empty_file")
    try:
        content_type = detect_content_type(filename, data[:16], data)
    except IngestionError as e:
        raise UnsupportedMediaType(str(e)) from e

    sha256 = hashlib.sha256(data).hexdigest()
    if (dup := await repo.find_duplicate(session, workspace_id, sha256)) is not None:
        raise Conflict(
            f"This file is already in the workspace as “{dup.filename}”",
            code="duplicate_document",
            details={"document_id": str(dup.id)},
        )

    # Random key: never trust (or reveal) the user's filename in storage paths.
    doc_id = uuid.uuid4()
    storage_key = f"{workspace_id}/{doc_id.hex}"
    await get_storage().put(storage_key, data, content_type)

    doc = Document(
        id=doc_id,
        workspace_id=workspace_id,
        uploaded_by=user.id,
        filename=filename,
        content_type=content_type,
        size_bytes=len(data),
        sha256=sha256,
        storage_key=storage_key,
        status=DocStatus.queued,
    )
    session.add(doc)
    try:
        await session.commit()
    except IntegrityError as e:  # concurrent upload of the same file
        await session.rollback()
        await get_storage().delete(storage_key)
        raise Conflict("This file is already in the workspace", code="duplicate_document") from e

    await enqueue_ingestion(doc.id)
    await publish_document_event(redis, workspace_id, document_event(doc))
    log.info("document queued", extra={"document_id": str(doc.id), "size": len(data)})
    return doc


async def reprocess(session: AsyncSession, redis: Redis, doc: Document) -> Document:
    # Status alone can't be trusted after a worker crash, so the job queue decides.
    if not await enqueue_ingestion(doc.id):
        raise Conflict("Document is already being processed", code="already_processing")
    doc.status = DocStatus.queued
    doc.pages_done = 0
    doc.error_message = None
    await session.commit()
    await publish_document_event(redis, doc.workspace_id, document_event(doc))
    return doc


async def delete_document(session: AsyncSession, redis: Redis, doc: Document) -> None:
    workspace_id, storage_key, doc_id = doc.workspace_id, doc.storage_key, doc.id
    await session.execute(delete(Chunk).where(Chunk.document_id == doc_id))
    await session.delete(doc)
    await bump_corpus_version(session, workspace_id)  # invalidates cached answers
    await session.commit()
    try:
        await get_storage().delete(storage_key)
    except Exception:
        log.warning(
            "failed to delete stored file", extra={"storage_key": storage_key}, exc_info=True
        )
    await publish_document_event(
        redis, workspace_id, {"type": "document_deleted", "document_id": str(doc_id)}
    )
