import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_col, uuid_pk


class Role(StrEnum):
    viewer = "viewer"
    editor = "editor"
    owner = "owner"

    @property
    def rank(self) -> int:
        return {"viewer": 1, "editor": 2, "owner": 3}[self.value]

    def at_least(self, other: "Role") -> bool:
        return self.rank >= other.rank


ROLE_CHECK = "role IN ('owner', 'editor', 'viewer')"


class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        Index(
            "uq_workspaces_single_demo", "is_demo", unique=True, postgresql_where=text("is_demo")
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    is_personal: Mapped[bool] = mapped_column(default=False, nullable=False)
    # The public demo workspace: guests join it as viewers via "Try the demo".
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    # Bumped on every document change; part of the answer-cache key so stale answers can't leak.
    corpus_version: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = created_at_col()


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (CheckConstraint(ROLE_CHECK, name="role"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    joined_at: Mapped[datetime] = created_at_col()


class WorkspaceInvite(Base):
    __tablename__ = "workspace_invites"
    __table_args__ = (CheckConstraint(ROLE_CHECK, name="role"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    used_at: Mapped[datetime | None]
    used_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = created_at_col()
