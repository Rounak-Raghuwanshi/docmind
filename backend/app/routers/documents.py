import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from fastapi.responses import Response, StreamingResponse

from app.deps import (
    DB,
    DocumentAccess,
    RedisDep,
    WorkspaceAccess,
    rate_limit,
    require_document_role,
    require_role,
)
from app.models import Role
from app.repositories import documents as repo
from app.schemas.common import Page, decode_cursor, encode_cursor
from app.schemas.document import DocumentOut, PageTextOut
from app.services import documents as service
from app.services.events import documents_channel
from app.services.sse import SSE_HEADERS, sse, sse_comment
from app.services.storage import get_storage

router = APIRouter(tags=["documents"])

Viewer = Annotated[WorkspaceAccess, Depends(require_role(Role.viewer))]
Editor = Annotated[WorkspaceAccess, Depends(require_role(Role.editor))]
DocViewer = Annotated[DocumentAccess, Depends(require_document_role(Role.viewer))]
DocEditor = Annotated[DocumentAccess, Depends(require_document_role(Role.editor))]

HEARTBEAT_SECONDS = 15


@router.post(
    "/workspaces/{ws}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit("upload"))],
)
async def upload_document(
    access: Editor, session: DB, redis: RedisDep, file: Annotated[UploadFile, File()]
) -> DocumentOut:
    """Validates and stores the file, then queues ingestion. Returns immediately (202)."""
    doc = await service.upload(session, redis, access.workspace.id, access.user, file)
    return DocumentOut.model_validate(doc)


@router.get("/workspaces/{ws}/documents", response_model=Page[DocumentOut])
async def list_documents(
    access: Viewer,
    session: DB,
    status_filter: Annotated[
        Literal["queued", "processing", "ready", "failed"] | None, Query(alias="status")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
) -> Page[DocumentOut]:
    docs = await repo.list_documents(
        session, access.workspace.id, status_filter, limit + 1, decode_cursor(cursor)
    )
    page, more = docs[:limit], len(docs) > limit
    nxt = encode_cursor(page[-1].created_at, page[-1].id) if more else None
    return Page(items=[DocumentOut.model_validate(d) for d in page], next_cursor=nxt)


@router.get("/workspaces/{ws}/documents/events")
async def document_events(
    access: Viewer, session: DB, request: Request, redis: RedisDep
) -> StreamingResponse:
    """SSE stream of status/progress changes for every document in the workspace."""
    channel = documents_channel(access.workspace.id)
    # Give the pooled DB connection back now; the stream may stay open for hours.
    await session.close()

    async def stream() -> AsyncIterator[str]:
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            yield sse_comment("connected")
            while not await request.is_disconnected():
                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=HEARTBEAT_SECONDS
                )
                if msg is None:
                    yield sse_comment()  # keeps proxies from closing an idle connection
                    continue
                payload = json.loads(msg["data"])
                yield sse(payload.pop("type", "document"), payload)
        finally:
            await asyncio.shield(pubsub.aclose())

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.get("/documents/{doc}", response_model=DocumentOut)
async def get_document(access: DocViewer) -> DocumentOut:
    return DocumentOut.model_validate(access.document)


@router.get("/documents/{doc}/file")
async def download_file(access: DocViewer) -> Response:
    """Originals are only reachable through this authorised endpoint, never a public URL."""
    doc = access.document
    data = await get_storage().get(doc.storage_key)
    return Response(
        data,
        media_type=doc.content_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(doc.filename)}",
            "Cache-Control": "private, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/documents/{doc}/pages/{page}", response_model=PageTextOut)
async def page_text(page: int, access: DocViewer, session: DB) -> PageTextOut:
    """Indexed text for one page/section; used by the viewer for non-PDF documents."""
    chunks = await repo.page_chunks(session, access.document.id, page)
    return PageTextOut(document_id=access.document.id, page=page, chunks=chunks)


@router.post(
    "/documents/{doc}/reprocess", response_model=DocumentOut, status_code=status.HTTP_202_ACCEPTED
)
async def reprocess(access: DocEditor, session: DB, redis: RedisDep) -> DocumentOut:
    doc = await service.reprocess(session, redis, access.document)
    return DocumentOut.model_validate(doc)


@router.delete("/documents/{doc}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(access: DocEditor, session: DB, redis: RedisDep) -> Response:
    await service.delete_document(session, redis, access.document)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
