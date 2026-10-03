"""Integration fixtures: a real Postgres (pgvector) and Redis, migrated with Alembic.

Point TEST_DATABASE_URL / TEST_REDIS_URL at disposable instances; every test truncates them.
"""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from sqlalchemy import text

from app.db import SessionLocal, engine
from app.main import app
from app.rag.embedder import get_embedder
from app.redis_client import get_redis
from app.services.ingestion import Ingestor
from app.services.storage import get_storage

pytestmark = pytest.mark.integration

TABLES = [
    "message_feedback",
    "messages",
    "conversations",
    "chunks",
    "documents",
    "workspace_invites",
    "workspace_members",
    "workspaces",
    "refresh_tokens",
    "users",
]


def _migrate() -> None:
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(scope="session", autouse=True)
async def database() -> AsyncIterator[None]:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await get_redis().ping()
    except Exception as e:  # pragma: no cover - environment guard
        pytest.skip(f"integration services unavailable: {e}", allow_module_level=True)
    await asyncio.to_thread(_migrate)  # alembic's env.py runs its own event loop
    yield
    await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_state(database: None) -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {', '.join(TABLES)} CASCADE"))
    await get_redis().flushdb()
    yield


@pytest.fixture(scope="session")
async def client(database: None) -> AsyncIterator[httpx.AsyncClient]:
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


class Api:
    """Small helper so tests read like user journeys."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def signup(
        self, email: str | None = None, password: str = "password123"
    ) -> dict[str, Any]:
        email = email or f"user-{uuid.uuid4().hex[:8]}@example.com"
        r = await self.client.post(
            "/api/auth/register",
            json={"email": email, "full_name": "Test User", "password": password},
        )
        assert r.status_code == 201, r.text
        r = await self.client.post("/api/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        body = r.json()
        self.client.cookies.clear()  # each user is explicit; don't leak cookies between them
        return {
            "email": email,
            "user": body["user"],
            "headers": {"Authorization": f"Bearer {body['access_token']}"},
            "refresh_cookie": r.cookies.get("docmind_refresh"),
        }

    async def refresh(self, token: str) -> httpx.Response:
        self.client.cookies.clear()
        self.client.cookies.set("docmind_refresh", token, path="/api/auth")
        r = await self.client.post("/api/auth/refresh")
        self.client.cookies.clear()
        return r

    async def personal_workspace(self, user: dict[str, Any]) -> str:
        r = await self.client.get("/api/workspaces", headers=user["headers"])
        return next(w["id"] for w in r.json()["items"] if w["is_personal"])

    async def upload(self, user: dict[str, Any], ws: str, name: str, data: bytes) -> httpx.Response:
        return await self.client.post(
            f"/api/workspaces/{ws}/documents",
            headers=user["headers"],
            files={"file": (name, data, "application/octet-stream")},
        )

    async def ask(self, user: dict[str, Any], conv: str, question: str) -> list[tuple[str, Any]]:
        r = await self.client.post(
            f"/api/conversations/{conv}/messages",
            headers=user["headers"],
            json={"question": question},
        )
        assert r.status_code == 200, r.text
        return parse_sse(r.text)


def parse_sse(raw: str) -> list[tuple[str, Any]]:
    events = []
    for frame in raw.split("\n\n"):
        name, data = None, None
        for line in frame.split("\n"):
            if line.startswith("event: "):
                name = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
        if name:
            events.append((name, data))
    return events


@pytest.fixture
def api(client: httpx.AsyncClient) -> Api:
    return Api(client)


@pytest.fixture
def ingestor() -> Ingestor:
    return Ingestor(SessionLocal, get_redis(), get_storage(), get_embedder())


async def ingest(ingestor: Ingestor, document_id: str) -> None:
    """Run the worker job inline (tests don't need a running ARQ worker)."""
    assert await ingestor.run(uuid.UUID(document_id))
