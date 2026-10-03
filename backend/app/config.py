from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables (or backend/.env in development)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["dev", "test", "prod"] = "dev"
    log_level: str = "INFO"
    public_app_url: str = "http://localhost:5173"

    # Database / Redis
    database_url: str = "postgresql+asyncpg://docmind:docmind@localhost:5432/docmind"
    db_pool_size: int = 5
    db_max_overflow: int = 5
    # Set true behind PgBouncer/Supavisor *transaction* mode, which can't hold prepared statements.
    db_disable_prepared_statements: bool = False
    redis_url: str = "redis://localhost:6379"

    # Auth
    jwt_secret_key: SecretStr = SecretStr("dev-only-secret-change-me-dev-only-secret-change-me")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    refresh_cookie_name: str = "docmind_refresh"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    invite_days: int = 7

    # HTTP
    cors_origins: list[str] = ["http://localhost:5173"]

    # Storage
    storage_backend: Literal["local", "s3"] = "local"
    local_storage_dir: Path = Path("./storage")
    s3_endpoint: str | None = None
    s3_region: str = "us-east-1"
    s3_bucket: str | None = None
    s3_access_key: SecretStr | None = None
    s3_secret_key: SecretStr | None = None

    # LLM (any OpenAI-compatible endpoint: Ollama, Groq, Gemini, ...)
    # openai = any OpenAI-compatible API; none = no LLM (answers quote the best sentences);
    # fake = canned test answers.
    llm_provider: Literal["openai", "none", "fake"] = "openai"
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: SecretStr = SecretStr("ollama")
    llm_model: str = "llama3.2:3b"
    llm_max_tokens: int = 800
    llm_temperature: float = 0.1
    llm_timeout_seconds: float = 60.0
    llm_stream_usage: bool = True

    # Retrieval models
    embedding_provider: Literal["fastembed", "fake"] = "fastembed"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    rerank_provider: Literal["fastembed", "fake", "none"] = "fastembed"
    rerank_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    models_cache_dir: str | None = None

    # RAG tuning (starting values; the eval harness decides the final ones)
    chunk_tokens: int = 400
    chunk_overlap_tokens: int = 60
    retrieval_candidates: int = 20
    retrieval_top_k: int = 6
    rrf_k: int = 60
    relevance_threshold: float = -2.0
    hnsw_ef_search: int = 100
    hnsw_iterative_scan: bool = True
    history_messages_for_rewrite: int = 4

    # Uploads / ingestion
    max_upload_mb: int = 20
    ocr_enabled: bool = True
    ocr_min_chars: int = 20
    ocr_dpi: int = 200
    worker_max_jobs: int = 2
    worker_poll_delay_seconds: float = 0.5

    # Rate limits
    rate_limit_enabled: bool = True
    login_per_minute: int = 5
    chat_per_minute: int = 20
    uploads_per_hour: int = 20
    demo_logins_per_hour: int = 10

    # Answer cache
    answer_cache_ttl_seconds: int = 60 * 60 * 24

    # Public demo ("Try the demo" button)
    demo_workspace_id: str | None = None

    # Observability
    sentry_dsn: str | None = None

    @field_validator("database_url")
    @classmethod
    def _force_asyncpg(cls, v: str) -> str:
        # Hosting dashboards hand out postgres:// URLs; normalise so copy-paste just works.
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+asyncpg://" + v[len(prefix) :]
        return v

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def is_prod(self) -> bool:
        return self.app_env == "prod"

    def check_production_safety(self) -> None:
        if not self.is_prod:
            return
        secret = self.jwt_secret_key.get_secret_value()
        if len(secret) < 48 or "change-me" in secret:
            raise RuntimeError("JWT_SECRET_KEY must be a random value of 48+ characters in prod")
        if not self.cookie_secure:
            raise RuntimeError("COOKIE_SECURE must be true in prod")


@lru_cache
def get_settings() -> Settings:
    return Settings()
