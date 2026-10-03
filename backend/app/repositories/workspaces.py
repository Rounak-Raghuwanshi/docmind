import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, User, Workspace, WorkspaceMember


async def list_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    limit: int,
    after: tuple[datetime, uuid.UUID] | None,
    workspace_id: uuid.UUID | None = None,
) -> list[dict[str, Any]]:
    doc_count = (
        select(func.count())
        .where(Document.workspace_id == Workspace.id)
        .correlate(Workspace)
        .scalar_subquery()
    )
    member_count = (
        select(func.count())
        .where(WorkspaceMember.workspace_id == Workspace.id)
        .correlate(Workspace)
        .scalar_subquery()
    )
    me = WorkspaceMember.__table__.alias("me")
    stmt = (
        select(Workspace, me.c.role, doc_count.label("docs"), member_count.label("members"))
        .join(me, (me.c.workspace_id == Workspace.id) & (me.c.user_id == user_id))
        .order_by(Workspace.created_at.desc(), Workspace.id.desc())
        .limit(limit)
    )
    if workspace_id is not None:
        stmt = stmt.where(Workspace.id == workspace_id)
    if after:
        ts, id_ = after
        stmt = stmt.where(tuple_(Workspace.created_at, Workspace.id) < tuple_(ts, id_))
    rows = (await session.execute(stmt)).all()
    return [
        {
            "id": ws.id,
            "name": ws.name,
            "role": role,
            "is_personal": ws.is_personal,
            "is_demo": ws.is_demo,
            "document_count": docs,
            "member_count": members,
            "created_at": ws.created_at,
        }
        for ws, role, docs, members in rows
    ]


async def list_members(session: AsyncSession, workspace_id: uuid.UUID) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            select(WorkspaceMember, User)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.joined_at)
        )
    ).all()
    return [
        {
            "user_id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": m.role,
            "joined_at": m.joined_at,
        }
        for m, u in rows
    ]


async def get_member(
    session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> WorkspaceMember | None:
    return await session.get(WorkspaceMember, (workspace_id, user_id))


async def count_owners(session: AsyncSession, workspace_id: uuid.UUID) -> int:
    return int(
        await session.scalar(
            select(func.count()).where(
                WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.role == "owner"
            )
        )
        or 0
    )


async def bump_corpus_version(session: AsyncSession, workspace_id: uuid.UUID) -> None:
    await session.execute(
        update(Workspace)
        .where(Workspace.id == workspace_id)
        .values(corpus_version=Workspace.corpus_version + 1)
    )


async def get_for_user(
    session: AsyncSession, user_id: uuid.UUID, workspace_id: uuid.UUID
) -> dict[str, Any] | None:
    rows = await list_for_user(session, user_id, 1, None, workspace_id)
    return rows[0] if rows else None
