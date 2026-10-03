import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import SessionLocal, engine
from app.errors import install_error_handlers
from app.llm.client import get_llm
from app.logging_setup import configure_logging
from app.middleware import (
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
    SelectiveGZipMiddleware,
)
from app.rag.embedder import get_embedder
from app.rag.reranker import get_reranker
from app.redis_client import close_redis, get_redis
from app.routers import auth, chat, documents, health, search, workspaces
from app.services.chat import ChatService
from app.services.retrieval import Retriever

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    # Load models once per process at startup, never per request.
    embedder = get_embedder()
    reranker = get_reranker()
    retriever = Retriever(SessionLocal, embedder, reranker, settings)
    app.state.retriever = retriever
    app.state.chat = ChatService(SessionLocal, get_redis(), retriever, get_llm(), settings)
    log.info(
        "api ready",
        extra={
            "env": settings.app_env,
            "llm": settings.llm_model,
            "embedding_model": embedder.name,
        },
    )
    yield
    await close_redis()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    settings.check_production_safety()
    configure_logging(settings.log_level)

    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            traces_sample_rate=0.1,
            send_default_pii=False,  # never ship document text or tokens off-box
        )

    app = FastAPI(
        title="DocMind API",
        version="1.0.0",
        description="Ask questions across your documents; every answer cites its sources.",
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    install_error_handlers(app)

    api = APIRouter(prefix="/api")
    for r in (
        health.router,
        auth.router,
        workspaces.router,
        documents.router,
        chat.router,
        search.router,
    ):
        api.include_router(r)
    app.include_router(api)

    # Order matters: the last added runs first (outermost).
    app.add_middleware(SelectiveGZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Retry-After"],
        max_age=600,
    )
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.is_prod)
    app.add_middleware(RequestContextMiddleware)
    return app


app = create_app()
