"""ARQ worker entrypoint:  arq app.workers.settings.WorkerSettings"""

import logging
from typing import Any, ClassVar

from arq import func

from app.config import get_settings
from app.db import SessionLocal, engine
from app.llm.client import get_llm
from app.logging_setup import configure_logging
from app.rag.embedder import get_embedder
from app.redis_client import arq_redis_settings, get_redis
from app.services.ingestion import Ingestor
from app.services.storage import get_storage
from app.workers import jobs

log = logging.getLogger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    embedder = get_embedder()  # load the model once, before the first job
    ctx["sessionmaker"] = SessionLocal
    ctx["pubsub_redis"] = get_redis()
    ctx["storage"] = get_storage()
    ctx["llm"] = get_llm()
    ctx["ingestor"] = Ingestor(SessionLocal, ctx["pubsub_redis"], ctx["storage"], embedder)
    await jobs.requeue_interrupted(ctx)
    log.info("worker ready", extra={"embedding_model": embedder.name})


async def shutdown(ctx: dict[str, Any]) -> None:
    # Startup may have failed part-way (e.g. Redis unreachable); clean up what exists.
    if (redis := ctx.get("pubsub_redis")) is not None:
        await redis.aclose()
    await engine.dispose()


_settings = get_settings()


class WorkerSettings:
    functions: ClassVar = [
        # keep_result=0 frees the fixed job id as soon as a run finishes, so reprocess works.
        func(jobs.ingest_document, keep_result=0, max_tries=jobs.MAX_TRIES, timeout=900),
        func(jobs.enrich, name="enrich_document", keep_result=0, max_tries=1, timeout=120),
        func(jobs.generate_title, keep_result=0, max_tries=1, timeout=60),
        func(jobs.delete_storage_objects, keep_result=0, max_tries=3),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = arq_redis_settings()
    max_jobs = _settings.worker_max_jobs  # ingestion is CPU-bound; don't oversubscribe
    poll_delay = _settings.worker_poll_delay_seconds
    health_check_interval = 60
