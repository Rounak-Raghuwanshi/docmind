"""Initial schema: users, workspaces, documents, chunks (pgvector + full-text), chat.

Revision ID: 0001
Revises:
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql as pg

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = pg.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)


def _id() -> sa.Column:
    return sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()"))


def _created() -> sa.Column:
    return sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        _id(),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("hashed_password", sa.String(100), nullable=False),
        sa.Column("is_guest", sa.Boolean, server_default=sa.false(), nullable=False),
        _created(),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )

    op.create_table(
        "refresh_tokens",
        _id(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_refresh_tokens_user_id_users"), nullable=False),
        sa.Column("family_id", UUID, nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", TS, nullable=False),
        sa.Column("revoked_at", TS),
        sa.Column("replaced_by", UUID),
        _created(),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_tokens"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])

    op.create_table(
        "workspaces",
        _id(),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("owner_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_workspaces_owner_id_users"), nullable=False),
        sa.Column("is_personal", sa.Boolean, server_default=sa.false(), nullable=False),
        sa.Column("corpus_version", sa.Integer, server_default="0", nullable=False),
        _created(),
        sa.PrimaryKeyConstraint("id", name="pk_workspaces"),
    )

    op.create_table(
        "workspace_members",
        sa.Column("workspace_id", UUID, sa.ForeignKey("workspaces.id", ondelete="CASCADE", name="fk_workspace_members_workspace_id_workspaces"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_workspace_members_user_id_users"), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("joined_at", TS, server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("workspace_id", "user_id", name="pk_workspace_members"),
        sa.CheckConstraint("role IN ('owner', 'editor', 'viewer')", name="ck_workspace_members_role"),
    )
    op.create_index("ix_workspace_members_user_id", "workspace_members", ["user_id"])

    op.create_table(
        "workspace_invites",
        _id(),
        sa.Column("workspace_id", UUID, sa.ForeignKey("workspaces.id", ondelete="CASCADE", name="fk_workspace_invites_workspace_id_workspaces"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("expires_at", TS, nullable=False),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_workspace_invites_created_by_users"), nullable=False),
        sa.Column("used_at", TS),
        sa.Column("used_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_workspace_invites_used_by_users")),
        _created(),
        sa.UniqueConstraint("token_hash", name="uq_workspace_invites_token_hash"),
        sa.PrimaryKeyConstraint("id", name="pk_workspace_invites"),
        sa.CheckConstraint("role IN ('owner', 'editor', 'viewer')", name="ck_workspace_invites_role"),
    )
    op.create_index("ix_workspace_invites_workspace_id", "workspace_invites", ["workspace_id"])

    op.create_table(
        "documents",
        _id(),
        sa.Column("workspace_id", UUID, sa.ForeignKey("workspaces.id", ondelete="CASCADE", name="fk_documents_workspace_id_workspaces"), nullable=False),
        sa.Column("uploaded_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_documents_uploaded_by_users")),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="queued"),
        sa.Column("pages_total", sa.Integer),
        sa.Column("pages_done", sa.Integer, server_default="0", nullable=False),
        sa.Column("error_message", sa.Text),
        sa.Column("summary", sa.Text),
        sa.Column("suggested_questions", pg.JSONB),
        sa.Column("embedding_model", sa.String(100)),
        sa.Column("chunk_count", sa.Integer, server_default="0", nullable=False),
        _created(),
        sa.Column("processed_at", TS),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
        sa.UniqueConstraint("workspace_id", "sha256", name="uq_documents_workspace_sha256"),
        sa.CheckConstraint("status IN ('queued', 'processing', 'ready', 'failed')", name="ck_documents_status"),
    )
    op.create_index("ix_documents_workspace_created", "documents", ["workspace_id", sa.text("created_at DESC")])

    op.create_table(
        "chunks",
        _id(),
        sa.Column("document_id", UUID, sa.ForeignKey("documents.id", ondelete="CASCADE", name="fk_chunks_document_id_documents"), nullable=False),
        sa.Column("workspace_id", UUID, sa.ForeignKey("workspaces.id", ondelete="CASCADE", name="fk_chunks_workspace_id_workspaces"), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("page_start", sa.Integer, nullable=False),
        sa.Column("page_end", sa.Integer, nullable=False),
        sa.Column("context", sa.Text, nullable=False, server_default=""),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column(
            "search_vector",
            pg.TSVECTOR,
            sa.Computed("to_tsvector('english', context || ' ' || content)", persisted=True),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_chunks"),
    )
    op.create_index("ix_chunks_workspace_document", "chunks", ["workspace_id", "document_id"])
    op.create_index("ix_chunks_search_vector", "chunks", ["search_vector"], postgresql_using="gin")
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw ON chunks "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )

    op.create_table(
        "conversations",
        _id(),
        sa.Column("workspace_id", UUID, sa.ForeignKey("workspaces.id", ondelete="CASCADE", name="fk_conversations_workspace_id_workspaces"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_conversations_user_id_users"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False, server_default="New conversation"),
        sa.Column("document_filter", pg.ARRAY(UUID)),
        _created(),
        sa.Column("updated_at", TS, server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_conversations"),
    )
    op.create_index("ix_conversations_ws_user_updated", "conversations", ["workspace_id", "user_id", "updated_at"])

    op.create_table(
        "messages",
        _id(),
        sa.Column("conversation_id", UUID, sa.ForeignKey("conversations.id", ondelete="CASCADE", name="fk_messages_conversation_id_conversations"), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("citations", pg.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("status", sa.String(10), nullable=False, server_default="complete"),
        sa.Column("model", sa.String(100)),
        sa.Column("rewritten_question", sa.Text),
        sa.Column("not_found", sa.Boolean, server_default=sa.false(), nullable=False),
        sa.Column("cached", sa.Boolean, server_default=sa.false(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer),
        sa.Column("completion_tokens", sa.Integer),
        sa.Column("retrieval_ms", sa.Integer),
        sa.Column("rerank_ms", sa.Integer),
        sa.Column("first_token_ms", sa.Integer),
        sa.Column("total_ms", sa.Integer),
        sa.Column("retrieval_debug", pg.JSONB),
        _created(),
        sa.PrimaryKeyConstraint("id", name="pk_messages"),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_messages_role"),
        sa.CheckConstraint("status IN ('complete', 'stopped', 'error')", name="ck_messages_status"),
    )
    op.create_index("ix_messages_conversation_created", "messages", ["conversation_id", "created_at"])

    op.create_table(
        "message_feedback",
        sa.Column("message_id", UUID, sa.ForeignKey("messages.id", ondelete="CASCADE", name="fk_message_feedback_message_id_messages"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_message_feedback_user_id_users"), nullable=False),
        sa.Column("rating", sa.SmallInteger, nullable=False),
        sa.Column("comment", sa.Text),
        _created(),
        sa.PrimaryKeyConstraint("message_id", "user_id", name="pk_message_feedback"),
        sa.CheckConstraint("rating IN (-1, 1)", name="ck_message_feedback_rating"),
    )


def downgrade() -> None:
    for table in (
        "message_feedback",
        "messages",
        "conversations",
        "chunks",
        "documents",
        "workspace_invites",
        "workspace_members",
        "workspaces",
        "refresh_tokens",
        "users",
    ):
        op.drop_table(table)
