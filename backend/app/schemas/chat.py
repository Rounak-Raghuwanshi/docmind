import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel


class ConversationIn(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    document_ids: list[uuid.UUID] | None = Field(default=None, max_length=50)


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    # Explicit null clears the filter (= all documents); omitting the field leaves it alone.
    document_ids: list[uuid.UUID] | None = Field(default=None, max_length=50)


class ConversationOut(ORMModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    document_filter: list[uuid.UUID] | None
    created_at: datetime
    updated_at: datetime


class Citation(BaseModel):
    n: int
    chunk_id: str
    document_id: str
    filename: str
    page: int
    page_end: int | None = None
    snippet: str


class MessageOut(ORMModel):
    id: uuid.UUID
    role: Literal["user", "assistant"]
    content: str
    citations: list[Citation]
    status: str
    not_found: bool
    cached: bool
    model: str | None
    first_token_ms: int | None
    total_ms: int | None
    feedback: int | None = None
    created_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("question is required")
        return v


class FeedbackIn(BaseModel):
    rating: Literal[1, -1]
    comment: str | None = Field(default=None, max_length=1000)


class RetrievalDebugOut(BaseModel):
    message_id: uuid.UUID
    rewritten_question: str | None
    retrieval_ms: int | None
    rerank_ms: int | None
    chunks: list[dict[str, Any]]


SearchMode = Literal["vector", "keyword", "hybrid", "hybrid_rerank"]


class SearchIn(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    mode: SearchMode = "hybrid_rerank"
    top_k: int = Field(default=6, ge=1, le=50)
    document_ids: list[uuid.UUID] | None = None


class SearchHit(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    page_start: int
    page_end: int
    content: str
    vector_rank: int | None
    keyword_rank: int | None
    rrf_score: float | None
    rerank_score: float | None
    score: float


class SearchOut(BaseModel):
    mode: SearchMode
    retrieval_ms: int
    rerank_ms: int
    hits: list[SearchHit]
