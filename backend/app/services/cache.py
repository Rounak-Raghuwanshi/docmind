"""Answer cache. The key includes the workspace's corpus_version, so any document change
silently invalidates every cached answer for that workspace — no explicit purge needed."""

import hashlib
import json
import re
import uuid
from typing import Any

from redis.asyncio import Redis

_WS = re.compile(r"\s+")


def normalise_question(question: str) -> str:
    q = _WS.sub(" ", question.strip().lower())
    return q.rstrip("?!. ")


def answer_cache_key(
    workspace_id: uuid.UUID,
    corpus_version: int,
    document_filter: list[uuid.UUID] | None,
    question: str,
) -> str:
    filter_part = ",".join(sorted(str(d) for d in document_filter)) if document_filter else "*"
    raw = f"{workspace_id}|{corpus_version}|{filter_part}|{normalise_question(question)}"
    return "ans:" + hashlib.sha256(raw.encode()).hexdigest()


async def get_cached_answer(redis: Redis, key: str) -> dict[str, Any] | None:
    try:
        raw = await redis.get(key)
    except Exception:  # cache is an optimisation; never fail a request over it
        return None
    return json.loads(raw) if raw else None


async def set_cached_answer(redis: Redis, key: str, value: dict[str, Any], ttl: int) -> None:
    try:
        await redis.set(key, json.dumps(value), ex=ttl)
    except Exception:
        return
