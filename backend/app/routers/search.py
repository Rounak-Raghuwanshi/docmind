import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.deps import DB, WorkspaceAccess, rate_limit, require_role
from app.errors import Forbidden
from app.models import Role
from app.repositories import insights as ins
from app.repositories.analytics import workspace_analytics
from app.schemas.analytics import AnalyticsOut, InsightsOut
from app.schemas.chat import SearchHit, SearchIn, SearchOut
from app.services.retrieval import Retriever

router = APIRouter(tags=["search & analytics"])

Viewer = Annotated[WorkspaceAccess, Depends(require_role(Role.viewer))]


async def _stats_access(access: Viewer) -> WorkspaceAccess:
    """Owners see their workspace's stats; in the public demo everyone may look."""
    if access.role != Role.owner and not access.workspace.is_demo:
        raise Forbidden("This action needs the owner role in this workspace")
    return access


StatsReader = Annotated[WorkspaceAccess, Depends(_stats_access)]


@router.post(
    "/workspaces/{ws}/search", response_model=SearchOut, dependencies=[Depends(rate_limit("chat"))]
)
async def search(body: SearchIn, access: Viewer, session: DB, request: Request) -> SearchOut:
    """Retrieval only, no LLM. Powers the eval harness and makes retrieval debuggable."""
    await session.close()
    retriever: Retriever = request.app.state.retriever
    result = await retriever.search(
        access.workspace.id,
        body.query,
        document_ids=body.document_ids,
        mode=body.mode,
        top_k=body.top_k,
    )
    hits = [
        SearchHit(
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            filename=c.filename,
            page_start=c.page_start,
            page_end=c.page_end,
            content=c.content,
            vector_rank=c.vector_rank,
            keyword_rank=c.keyword_rank,
            rrf_score=c.rrf_score,
            rerank_score=c.rerank_score,
            score=c.score,
        )
        for c in result.chunks
    ]
    return SearchOut(
        mode=body.mode, retrieval_ms=result.retrieval_ms, rerank_ms=result.rerank_ms, hits=hits
    )


@router.get("/workspaces/{ws}/analytics", response_model=AnalyticsOut)
async def analytics(
    access: StatsReader, session: DB, days: Annotated[int, Query(ge=1, le=365)] = 30
) -> AnalyticsOut:
    return AnalyticsOut(**await workspace_analytics(session, access.workspace.id, days))


@router.get("/workspaces/{ws}/insights", response_model=InsightsOut)
async def insights(
    access: StatsReader,
    session: DB,
    request: Request,
    days: Annotated[int, Query(ge=1, le=365)] = 90,
) -> InsightsOut:
    """AI analysis: a 3D map of the embedding space plus how retrieval behaved on real questions."""
    ws_id = access.workspace.id
    points = await ins.embedding_points(session, ws_id)
    rows = await ins.answer_rows(session, ws_id, days)
    coverage = await ins.document_coverage(session, ws_id, rows)
    projected, variance = await asyncio.to_thread(ins.project_3d, points)
    sources = ins.retrieval_sources(rows)
    hist = ins.confidence_histogram(rows)
    gaps = ins.knowledge_gaps(rows)
    threshold = request.app.state.retriever.settings.relevance_threshold
    return InsightsOut(
        days=days,
        points=projected,
        explained_variance=variance,
        retrieval_sources=sources,
        confidence=hist,
        relevance_threshold=threshold,
        knowledge_gaps=gaps,
        coverage=coverage,
        highlights=ins.highlights(sources, hist, gaps, coverage, threshold),
    )
