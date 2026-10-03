from datetime import date

from pydantic import BaseModel


class DailyPoint(BaseModel):
    day: date
    questions: int
    avg_total_ms: float | None
    avg_first_token_ms: float | None
    not_found: int


class TopDocument(BaseModel):
    document_id: str
    filename: str
    citations: int


class AnalyticsOut(BaseModel):
    days: int
    total_questions: int
    avg_total_ms: float | None
    avg_first_token_ms: float | None
    not_found_rate: float | None
    cache_hit_rate: float | None
    feedback_up: int
    feedback_down: int
    feedback_score: float | None
    daily: list[DailyPoint]
    top_documents: list[TopDocument]


class EmbeddingPoint(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page: int
    preview: str
    x: float
    y: float
    z: float


class HistogramBin(BaseModel):
    start: float
    end: float
    answered: int
    not_found: int


class KnowledgeGap(BaseModel):
    question: str
    count: int


class DocumentCoverage(BaseModel):
    document_id: str
    filename: str
    chunks: int
    pages: int | None
    answers: int


class InsightsOut(BaseModel):
    days: int
    points: list[EmbeddingPoint]
    explained_variance: list[float]
    retrieval_sources: dict[str, int]
    confidence: list[HistogramBin]
    relevance_threshold: float
    knowledge_gaps: list[KnowledgeGap]
    coverage: list[DocumentCoverage]
    highlights: list[str]
