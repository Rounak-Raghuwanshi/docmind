import uuid
from datetime import datetime

from app.schemas.common import ORMModel


class DocumentOut(ORMModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    status: str
    pages_total: int | None
    pages_done: int
    chunk_count: int
    error_message: str | None
    summary: str | None
    suggested_questions: list[str] | None
    embedding_model: str | None
    created_at: datetime
    processed_at: datetime | None


class PageTextOut(ORMModel):
    document_id: uuid.UUID
    page: int
    chunks: list[str]
