import asyncio
import uuid

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.llm.fake import FakeLLM
from app.models import Message
from app.rag.prompts import NOT_FOUND_ANSWER
from app.redis_client import get_redis
from app.services.chat import ChatService
from app.services.ingestion import Ingestor
from tests.factories import make_pdf

from .conftest import Api, ingest


async def _ready_workspace(api: Api, ingestor: Ingestor) -> tuple[dict, str, str]:
    user = await api.signup()
    ws = await api.personal_workspace(user)
    doc_id = (await api.upload(user, ws, "tax-guide.pdf", make_pdf())).json()["id"]
    await ingest(ingestor, doc_id)
    return user, ws, doc_id


async def _conversation(api: Api, user: dict, ws: str, **body: object) -> str:
    r = await api.client.post(
        f"/api/workspaces/{ws}/conversations", headers=user["headers"], json=body
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_search_ranks_the_right_page_first(api: Api, ingestor: Ingestor) -> None:
    user, ws, _ = await _ready_workspace(api, ingestor)
    for mode in ("vector", "keyword", "hybrid", "hybrid_rerank"):
        r = await api.client.post(
            f"/api/workspaces/{ws}/search",
            headers=user["headers"],
            json={"query": "health insurance premium deduction 80D", "mode": mode, "top_k": 3},
        )
        assert r.status_code == 200, r.text
        hits = r.json()["hits"]
        assert hits, mode
        assert hits[0]["page_start"] <= 2 <= hits[0]["page_end"], (mode, hits[0])


async def test_search_never_crosses_workspaces(api: Api, ingestor: Ingestor) -> None:
    _, _, _ = await _ready_workspace(api, ingestor)
    other = await api.signup()
    other_ws = await api.personal_workspace(other)
    r = await api.client.post(
        f"/api/workspaces/{other_ws}/search",
        headers=other["headers"],
        json={"query": "Section 80D health insurance"},
    )
    assert r.json()["hits"] == []


async def test_answer_streams_with_valid_citations(api: Api, ingestor: Ingestor) -> None:
    user, ws, doc_id = await _ready_workspace(api, ingestor)
    conv = await _conversation(api, user, ws)
    events = await api.ask(
        user, conv, "What deduction does section 80D allow for health insurance?"
    )
    names = [e for e, _ in events]
    assert names[0] == "meta" and names[-2:] == ["citations", "done"]
    assert "token" in names
    answer = "".join(d["text"] for e, d in events if e == "token")
    assert "[1]" in answer
    citations = dict(events)["citations"]
    assert [c["n"] for c in citations] == [1, 2]
    assert all(c["document_id"] == doc_id for c in citations)
    done = dict(events)["done"]
    assert done["cached"] is False and done["total_ms"] >= 0

    detail = (await api.client.get(f"/api/conversations/{conv}", headers=user["headers"])).json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assistant = detail["messages"][1]
    assert assistant["status"] == "complete" and assistant["citations"] == citations
    assert detail["title"] != "New conversation"  # auto-titled from the first question

    debug = (
        await api.client.get(f"/api/messages/{assistant['id']}/retrieval", headers=user["headers"])
    ).json()
    assert debug["chunks"] and "rerank_score" in debug["chunks"][0]


async def test_out_of_scope_question_is_not_found_without_llm(api: Api, ingestor: Ingestor) -> None:
    user, ws, _ = await _ready_workspace(api, ingestor)
    conv = await _conversation(api, user, ws)
    events = await api.ask(user, conv, "Who won the football world cup in 1998?")
    answer = "".join(d["text"] for e, d in events if e == "token")
    assert answer == NOT_FOUND_ANSWER
    assert dict(events)["citations"] == []
    assert dict(events)["done"]["not_found"] is True


async def test_repeat_question_is_served_from_cache_until_corpus_changes(
    api: Api, ingestor: Ingestor
) -> None:
    user, ws, _ = await _ready_workspace(api, ingestor)
    q = "What deduction does section 80D allow for health insurance?"
    first = await api.ask(user, await _conversation(api, user, ws), q)
    second = await api.ask(user, await _conversation(api, user, ws), q.upper())
    assert dict(first)["done"]["cached"] is False
    assert dict(second)["done"]["cached"] is True
    assert dict(second)["citations"] == dict(first)["citations"]

    # A new upload bumps corpus_version, so the cached answer is no longer used.
    doc2 = (
        await api.upload(
            user, ws, "more.txt", b"Section 80D also covers preventive health checkups."
        )
    ).json()["id"]
    await ingest(ingestor, doc2)
    third = await api.ask(user, await _conversation(api, user, ws), q)
    assert dict(third)["done"]["cached"] is False


async def test_document_filter_limits_retrieval(api: Api, ingestor: Ingestor) -> None:
    user, ws, _tax_doc = await _ready_workspace(api, ingestor)
    other = (
        await api.upload(user, ws, "hr.txt", b"Employees receive 24 days of paid leave per year.")
    ).json()["id"]
    await ingest(ingestor, other)
    conv = await _conversation(api, user, ws, document_ids=[other])
    events = await api.ask(
        user, conv, "What deduction does section 80D allow for health insurance?"
    )
    assert all(c["document_id"] == other for c in dict(events)["citations"])
    # filters must reference documents in the same workspace
    r = await api.client.post(
        f"/api/workspaces/{ws}/conversations",
        headers=user["headers"],
        json={"document_ids": [str(uuid.uuid4())]},
    )
    assert r.status_code == 400


async def test_follow_up_is_rewritten_with_history(api: Api, ingestor: Ingestor) -> None:
    user, ws, _ = await _ready_workspace(api, ingestor)
    conv = await _conversation(api, user, ws)
    await api.ask(user, conv, "What does section 80C allow?")
    events = await api.ask(user, conv, "What about 80D health insurance?")
    meta = dict(events)["meta"]
    assert meta["rewritten_question"]  # FakeLLM echoes the latest question


async def test_stop_saves_partial_answer(api: Api, ingestor: Ingestor) -> None:
    user, ws, _ = await _ready_workspace(api, ingestor)
    conv = await _conversation(api, user, ws)
    slow = FakeLLM(answer="Section 80D allows a deduction [1]. " * 30, delay=0.01)
    app_chat = api.client._transport.app.state.chat  # type: ignore[attr-defined]
    chat = ChatService(SessionLocal, get_redis(), app_chat.retriever, slow, get_settings())

    stream = chat.stream_answer(uuid.UUID(conv), "What does section 80D allow?")
    seen = []
    async for frame in stream:
        seen.append(frame)
        if sum(f.startswith("event: token") for f in seen) >= 5:
            break
    await stream.aclose()  # what Starlette does when the browser aborts the fetch
    await asyncio.sleep(0.05)

    async with SessionLocal() as s:
        msg = (
            await s.execute(
                select(Message).where(
                    Message.conversation_id == uuid.UUID(conv), Message.role == "assistant"
                )
            )
        ).scalar_one()
    assert msg.status == "stopped"
    assert 0 < len(msg.content) < len(slow.answer)


async def test_feedback_and_analytics(api: Api, ingestor: Ingestor) -> None:
    user, ws, _ = await _ready_workspace(api, ingestor)
    conv = await _conversation(api, user, ws)
    await api.ask(user, conv, "What deduction does section 80D allow for health insurance?")
    await api.ask(user, conv, "Who won the football world cup in 1998?")
    detail = (await api.client.get(f"/api/conversations/{conv}", headers=user["headers"])).json()
    answer_id = detail["messages"][1]["id"]
    question_id = detail["messages"][0]["id"]

    r = await api.client.post(
        f"/api/messages/{answer_id}/feedback", headers=user["headers"], json={"rating": 1}
    )
    assert r.status_code == 204
    r = await api.client.post(
        f"/api/messages/{answer_id}/feedback",
        headers=user["headers"],
        json={"rating": -1, "comment": "changed my mind"},
    )
    assert r.status_code == 204  # upsert: one rating per user per message
    r = await api.client.post(
        f"/api/messages/{question_id}/feedback", headers=user["headers"], json={"rating": 1}
    )
    assert r.status_code == 400

    stats = (
        await api.client.get(f"/api/workspaces/{ws}/analytics", headers=user["headers"])
    ).json()
    assert stats["total_questions"] == 2
    assert stats["not_found_rate"] == 0.5
    assert (stats["feedback_up"], stats["feedback_down"]) == (0, 1)
    assert stats["top_documents"][0]["filename"] == "tax-guide.pdf"
    assert stats["daily"][0]["questions"] == 2


async def test_conversations_are_private_to_their_creator(api: Api, ingestor: Ingestor) -> None:
    owner, ws, _ = await _ready_workspace(api, ingestor)
    conv = await _conversation(api, owner, ws)
    teammate = await api.signup()
    token = (
        await api.client.post(
            f"/api/workspaces/{ws}/invites", headers=owner["headers"], json={"role": "editor"}
        )
    ).json()["token"]
    await api.client.post(f"/api/invites/{token}/accept", headers=teammate["headers"])
    assert (
        await api.client.get(f"/api/conversations/{conv}", headers=teammate["headers"])
    ).status_code == 404
    r = await api.client.post(
        f"/api/conversations/{conv}/messages", headers=teammate["headers"], json={"question": "hi"}
    )
    assert r.status_code == 404


async def test_rename_and_delete_conversation(api: Api, ingestor: Ingestor) -> None:
    user, ws, _ = await _ready_workspace(api, ingestor)
    conv = await _conversation(api, user, ws)
    r = await api.client.patch(
        f"/api/conversations/{conv}", headers=user["headers"], json={"title": "Renamed"}
    )
    assert r.json()["title"] == "Renamed"
    assert (
        await api.client.delete(f"/api/conversations/{conv}", headers=user["headers"])
    ).status_code == 204
    assert (
        await api.client.get(f"/api/conversations/{conv}", headers=user["headers"])
    ).status_code == 404


async def test_rate_limit_returns_429_with_retry_after(
    api: Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "rate_limit_enabled", True)
    statuses = []
    for _ in range(get_settings().login_per_minute + 1):
        r = await api.client.post(
            "/api/auth/login", json={"email": "x@example.com", "password": "whatever1"}
        )
        statuses.append(r.status_code)
    assert statuses[-1] == 429
    assert set(statuses[:-1]) == {401}
    assert int(r.headers["Retry-After"]) >= 1
    assert r.json()["error"]["code"] == "rate_limited"


async def test_health_and_ready(api: Api) -> None:
    assert (await api.client.get("/api/health")).json() == {"status": "ok"}
    r = await api.client.get("/api/ready")
    assert r.status_code == 200 and r.json()["checks"] == {"database": "ok", "redis": "ok"}
    assert r.headers["X-Request-ID"]
    assert r.headers["X-Content-Type-Options"] == "nosniff"
