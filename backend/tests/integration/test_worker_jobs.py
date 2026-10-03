"""The ARQ job functions, called directly with a fake worker context."""

import uuid
from typing import Any

import pytest
from arq import Retry
from sqlalchemy import select

from app.db import SessionLocal
from app.llm.fake import FakeLLM
from app.models import Conversation, Document
from app.redis_client import get_redis
from app.services.ingestion import Ingestor
from app.services.storage import get_storage
from app.workers import jobs
from tests.factories import make_pdf

from .conftest import Api


class FakeArq:
    def __init__(self) -> None:
        self.enqueued: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    async def enqueue_job(self, name: str, *args: Any, **kwargs: Any) -> object:
        self.enqueued.append((name, args, kwargs))
        return object()


def _ctx(ingestor: Ingestor, job_try: int = 1) -> dict[str, Any]:
    return {
        "ingestor": ingestor,
        "sessionmaker": SessionLocal,
        "pubsub_redis": get_redis(),
        "redis": FakeArq(),
        "llm": FakeLLM(),
        "storage": get_storage(),
        "job_try": job_try,
    }


async def _status(doc_id: str) -> Document:
    async with SessionLocal() as s:
        doc = await s.get(Document, uuid.UUID(doc_id))
    assert doc is not None
    return doc


async def test_ingest_job_then_enrich(api: Api, ingestor: Ingestor) -> None:
    user = await api.signup()
    ws = await api.personal_workspace(user)
    doc_id = (await api.upload(user, ws, "a.pdf", make_pdf())).json()["id"]
    ctx = _ctx(ingestor)
    await jobs.ingest_document(ctx, doc_id)
    assert (await _status(doc_id)).status == "ready"
    assert ctx["redis"].enqueued == [("enrich_document", (doc_id,), {})]

    await jobs.enrich(ctx, doc_id)
    doc = await _status(doc_id)
    assert doc.summary and doc.suggested_questions and len(doc.suggested_questions) == 3


async def test_permanent_failure_is_not_retried(api: Api, ingestor: Ingestor) -> None:
    user = await api.signup()
    ws = await api.personal_workspace(user)
    doc_id = (await api.upload(user, ws, "blank.pdf", make_pdf(["", ""]))).json()["id"]
    await jobs.ingest_document(_ctx(ingestor), doc_id)
    doc = await _status(doc_id)
    assert doc.status == "failed"
    assert "No readable text" in (doc.error_message or "")


async def test_transient_failure_retries_then_fails(
    api: Api, ingestor: Ingestor, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = await api.signup()
    ws = await api.personal_workspace(user)
    doc_id = (await api.upload(user, ws, "a.pdf", make_pdf())).json()["id"]

    async def broken_get(key: str) -> bytes:
        raise ConnectionError("storage down")

    monkeypatch.setattr(ingestor.storage, "get", broken_get)
    with pytest.raises(Retry):
        await jobs.ingest_document(_ctx(ingestor, job_try=1), doc_id)
    assert (await _status(doc_id)).status == "queued"

    await jobs.ingest_document(_ctx(ingestor, job_try=jobs.MAX_TRIES), doc_id)
    doc = await _status(doc_id)
    assert doc.status == "failed"
    assert "several attempts" in (doc.error_message or "")


async def test_deleted_document_job_is_a_noop(ingestor: Ingestor) -> None:
    ctx = _ctx(ingestor)
    await jobs.ingest_document(ctx, str(uuid.uuid4()))
    assert ctx["redis"].enqueued == []


async def test_requeue_interrupted_documents(api: Api, ingestor: Ingestor) -> None:
    user = await api.signup()
    ws = await api.personal_workspace(user)
    queued = (await api.upload(user, ws, "a.pdf", make_pdf())).json()["id"]
    ctx = _ctx(ingestor)
    assert await jobs.requeue_interrupted(ctx) == 1
    name, args, kwargs = ctx["redis"].enqueued[0]
    assert (name, args, kwargs["_job_id"]) == ("ingest_document", (queued,), f"ingest:{queued}")


async def test_generate_title_only_replaces_placeholder(api: Api, ingestor: Ingestor) -> None:
    user = await api.signup()
    ws = await api.personal_workspace(user)
    question = "What does section 80D allow for parents?"
    conv_id = (
        await api.client.post(
            f"/api/workspaces/{ws}/conversations",
            headers=user["headers"],
            json={"title": "What does section 80D allow for parents?"},
        )
    ).json()["id"]
    await jobs.generate_title(_ctx(ingestor), conv_id, question)
    async with SessionLocal() as s:
        conv = (
            await s.execute(select(Conversation).where(Conversation.id == uuid.UUID(conv_id)))
        ).scalar_one()
    assert conv.title == "Fake conversation title"

    await api.client.patch(
        f"/api/conversations/{conv_id}", headers=user["headers"], json={"title": "Mine"}
    )
    await jobs.generate_title(_ctx(ingestor), conv_id, question)
    async with SessionLocal() as s:
        conv = (
            await s.execute(select(Conversation).where(Conversation.id == uuid.UUID(conv_id)))
        ).scalar_one()
    assert conv.title == "Mine"


async def test_delete_storage_objects(ingestor: Ingestor) -> None:
    storage = get_storage()
    await storage.put("tmp/x", b"data", "text/plain")
    await jobs.delete_storage_objects(_ctx(ingestor), ["tmp/x", "tmp/missing"])
    with pytest.raises(FileNotFoundError):
        await storage.get("tmp/x")
