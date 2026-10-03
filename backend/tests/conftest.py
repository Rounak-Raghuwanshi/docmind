"""Test configuration. Runs before `app` is imported, so settings pick these values up.

External services are replaced with deterministic doubles: FakeLLM, a hashing embedder and an
overlap reranker. Tests are fast, free, offline, and don't download any models.
"""

import os
import tempfile

os.environ.setdefault("APP_ENV", "test")
os.environ["LLM_PROVIDER"] = "fake"
os.environ["EMBEDDING_PROVIDER"] = "fake"
os.environ["RERANK_PROVIDER"] = "fake"
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ["LOCAL_STORAGE_DIR"] = tempfile.mkdtemp(prefix="docmind-test-")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-test-secret-test-secret-test-secret-1234")
# Integration tests TRUNCATE every table, so they never fall back to DATABASE_URL from .env
# (your dev data). They use TEST_DATABASE_URL, defaulting to a separate local database.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://docmind:docmind@localhost:5432/docmind_test"
)
# Redis DB 15 by default, so FLUSHDB between tests can't touch the dev queue/cache (DB 0).
os.environ["REDIS_URL"] = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/15")
