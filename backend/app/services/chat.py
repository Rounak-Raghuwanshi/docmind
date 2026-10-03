"""Answering a question, streamed as Server-Sent Events.

    cache? -> rewrite follow-up -> hybrid retrieve -> rerank -> relevance gate -> LLM stream
           -> validate citations -> save message with timings -> cache

Event order: meta, token*, citations, done   (or error at any point).
If the client disconnects (Stop button) the task is cancelled: the upstream LLM stream is
closed and the partial answer is saved with status "stopped".
"""

import asyncio
import logging
import re
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import anyio
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.llm.base import LLMClient, LLMError, StreamResult
from app.logging_setup import request_id_var
from app.models import Conversation, Message, Workspace
from app.rag.citations import build_citations, strip_invalid_markers
from app.rag.prompts import NOT_FOUND_ANSWER, answer_messages, rewrite_messages
from app.rag.tokens import count_tokens
from app.redis_client import get_arq
from app.services.cache import answer_cache_key, get_cached_answer, set_cached_answer
from app.services.retrieval import RetrievalResult, Retriever
from app.services.sse import sse

log = logging.getLogger(__name__)

DEFAULT_TITLE = "New conversation"
_CACHED_TOKEN = re.compile(r"\S+\s*")


@dataclass
class _Answer:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    content: str = ""
    citations: list[dict[str, Any]] = field(default_factory=list)
    status: str = "complete"
    not_found: bool = False
    cached: bool = False
    model: str | None = None
    rewritten: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    retrieval_ms: int | None = None
    rerank_ms: int | None = None
    first_token_ms: int | None = None
    total_ms: int | None = None
    debug: list[dict[str, Any]] | None = None


def heuristic_title(question: str) -> str:
    words = question.split()
    title = " ".join(words[:8])
    return (title + "…") if len(words) > 8 else title


class ChatService:
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        redis: Redis,
        retriever: Retriever,
        llm: LLMClient,
        settings: Settings,
    ) -> None:
        self.sessionmaker = sessionmaker
        self.redis = redis
        self.retriever = retriever
        self.llm = llm
        self.settings = settings

    async def _prepare(
        self, conversation_id: uuid.UUID, question: str
    ) -> tuple[Conversation, Workspace, list[tuple[str, str]], bool]:
        async with self.sessionmaker() as session:
            conv = await session.get(Conversation, conversation_id)
            ws = await session.get(Workspace, conv.workspace_id) if conv else None
            if conv is None or ws is None:
                raise LookupError("conversation vanished")
            rows = await session.execute(
                select(Message.role, Message.content)
                .where(Message.conversation_id == conv.id, Message.status == "complete")
                .order_by(Message.created_at.desc())
                .limit(self.settings.history_messages_for_rewrite)
            )
            history = [(r, c) for r, c in reversed(rows.all())]
            is_first = not history and conv.title == DEFAULT_TITLE
            session.add(Message(conversation_id=conv.id, role="user", content=question))
            conv.updated_at = datetime.now(UTC)
            if is_first:
                conv.title = heuristic_title(question)
            await session.commit()
            return conv, ws, history, is_first

    async def _rewrite(self, history: list[tuple[str, str]], question: str) -> str:
        if not history:
            return question
        try:
            rewritten = await self.llm.complete(rewrite_messages(history, question), max_tokens=120)
        except LLMError:
            log.warning("question rewrite failed; using the original question")
            return question
        rewritten = rewritten.strip().strip('"').strip()
        # Guard against chatty models: a rewrite should be one question of similar size.
        if not rewritten or len(rewritten) > max(300, len(question) * 4) or "\n" in rewritten:
            return question
        return rewritten

    async def stream_answer(self, conversation_id: uuid.UUID, question: str) -> AsyncIterator[str]:
        started = time.perf_counter()
        ans = _Answer()
        conv: Conversation | None = None
        cache_key: str | None = None

        def elapsed() -> int:
            return int((time.perf_counter() - started) * 1000)

        try:
            conv, ws, history, is_first = await self._prepare(conversation_id, question)
            if is_first:
                await self._enqueue_title(conv.id, question)

            ans.rewritten = await self._rewrite(history, question)
            yield sse("meta", {"message_id": str(ans.id), "rewritten_question": ans.rewritten})

            cache_key = answer_cache_key(
                ws.id, ws.corpus_version, conv.document_filter, ans.rewritten
            )
            cached = await get_cached_answer(self.redis, cache_key)
            if cached is not None:
                ans.cached = True
                ans.model = cached.get("model")
                ans.not_found = bool(cached.get("not_found"))
                ans.first_token_ms = elapsed()
                for piece in _CACHED_TOKEN.findall(cached["content"]):
                    ans.content += piece
                    yield sse("token", {"text": piece})
                ans.citations = cached.get("citations", [])
            else:
                result = await self.retriever.search(
                    ws.id, ans.rewritten, document_ids=conv.document_filter
                )
                ans.retrieval_ms, ans.rerank_ms = result.retrieval_ms, result.rerank_ms
                ans.debug = [c.debug() for c in result.chunks]

                if self._below_relevance_gate(result):
                    # No LLM call: prevents hallucination and saves free-tier quota.
                    ans.not_found = True
                    ans.first_token_ms = elapsed()
                    ans.content = NOT_FOUND_ANSWER
                    yield sse("token", {"text": NOT_FOUND_ANSWER})
                else:
                    sources = [c.as_source() for c in result.chunks]
                    ans.model = self.llm.model
                    usage = StreamResult()
                    stream = self.llm.stream(
                        answer_messages(ans.rewritten, sources),
                        max_tokens=self.settings.llm_max_tokens,
                        result=usage,
                    )
                    async for delta in stream:
                        if ans.first_token_ms is None:
                            ans.first_token_ms = elapsed()
                        ans.content += delta
                        yield sse("token", {"text": delta})
                    ans.prompt_tokens = usage.usage.prompt_tokens
                    ans.completion_tokens = usage.usage.completion_tokens or count_tokens(
                        ans.content
                    )
                    ans.content = strip_invalid_markers(
                        ans.content, set(range(1, len(sources) + 1))
                    )
                    ans.citations = build_citations(ans.content, sources)

            yield sse("citations", ans.citations)
            ans.total_ms = elapsed()
            yield sse(
                "done", {"total_ms": ans.total_ms, "cached": ans.cached, "not_found": ans.not_found}
            )

        except (asyncio.CancelledError, GeneratorExit):
            ans.status = "stopped"
            raise
        except LLMError as e:
            ans.status = "error"
            yield sse("error", _error("llm_error", str(e)))
        except Exception:
            log.exception("chat stream failed", extra={"conversation_id": str(conversation_id)})
            ans.status = "error"
            yield sse("error", _error("internal_error", "Something went wrong while answering"))
        finally:
            if conv is not None:
                ans.total_ms = ans.total_ms or elapsed()
                # Shielded so the save survives the cancellation that a Stop click triggers.
                with anyio.CancelScope(shield=True):
                    await self._save(conv.id, ans, cache_key)

    def _below_relevance_gate(self, result: RetrievalResult) -> bool:
        if not result.chunks:
            return True
        top = result.top_rerank_score
        return top is not None and top < self.settings.relevance_threshold

    async def _save(self, conversation_id: uuid.UUID, ans: _Answer, cache_key: str | None) -> None:
        if ans.status != "complete" and ans.content:
            # Partial answers keep only citations whose markers made it into the text.
            ans.citations = [c for c in ans.citations if f"[{c['n']}]" in ans.content]
        try:
            async with self.sessionmaker() as session:
                session.add(
                    Message(
                        id=ans.id,
                        conversation_id=conversation_id,
                        role="assistant",
                        content=ans.content,
                        citations=ans.citations,
                        status=ans.status,
                        model=ans.model,
                        rewritten_question=ans.rewritten,
                        not_found=ans.not_found,
                        cached=ans.cached,
                        prompt_tokens=ans.prompt_tokens,
                        completion_tokens=ans.completion_tokens,
                        retrieval_ms=ans.retrieval_ms,
                        rerank_ms=ans.rerank_ms,
                        first_token_ms=ans.first_token_ms,
                        total_ms=ans.total_ms,
                        retrieval_debug=ans.debug,
                    )
                )
                conv = await session.get(Conversation, conversation_id)
                if conv is not None:
                    conv.updated_at = datetime.now(UTC)
                await session.commit()
        except Exception:
            log.exception("failed to save assistant message", extra={"message_id": str(ans.id)})
            return
        if ans.status == "complete" and not ans.cached and cache_key:
            await set_cached_answer(
                self.redis,
                cache_key,
                {
                    "content": ans.content,
                    "citations": ans.citations,
                    "not_found": ans.not_found,
                    "model": ans.model,
                },
                self.settings.answer_cache_ttl_seconds,
            )

    async def _enqueue_title(self, conversation_id: uuid.UUID, question: str) -> None:
        try:
            arq = await get_arq()
            await arq.enqueue_job("generate_title", str(conversation_id), question)
        except Exception:
            log.warning("could not enqueue title generation", exc_info=True)


def _error(code: str, message: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "request_id": request_id_var.get()}}
