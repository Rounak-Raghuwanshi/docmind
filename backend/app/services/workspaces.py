import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.errors import AppError, Conflict, NotFound
from app.models import Document, Role, User, Workspace, WorkspaceInvite, WorkspaceMember
from app.repositories import workspaces as repo
from app.security import hash_token, new_opaque_token


async def create_workspace(session: AsyncSession, user: User, name: str) -> Workspace:
    ws = Workspace(name=name, owner_id=user.id)
    session.add(ws)
    await session.flush()
    session.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=Role.owner))
    await session.commit()
    return ws


async def storage_keys(session: AsyncSession, workspace_id: uuid.UUID) -> list[str]:
    rows = await session.execute(
        select(Document.storage_key).where(Document.workspace_id == workspace_id)
    )
    return list(rows.scalars())


async def change_role(
    session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID, role: Role
) -> WorkspaceMember:
    member = await repo.get_member(session, workspace_id, user_id)
    if member is None:
        raise NotFound("Member not found")
    if (
        member.role == Role.owner
        and role != Role.owner
        and await repo.count_owners(session, workspace_id) <= 1
    ):
        raise Conflict("A workspace needs at least one owner", code="last_owner")
    member.role = role
    await session.commit()
    return member


async def remove_member(session: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
    member = await repo.get_member(session, workspace_id, user_id)
    if member is None:
        raise NotFound("Member not found")
    if member.role == Role.owner and await repo.count_owners(session, workspace_id) <= 1:
        raise Conflict("A workspace needs at least one owner", code="last_owner")
    await session.delete(member)
    await session.commit()


async def create_invite(
    session: AsyncSession, workspace_id: uuid.UUID, created_by: User, role: Role
) -> tuple[WorkspaceInvite, str]:
    raw = new_opaque_token()
    invite = WorkspaceInvite(
        workspace_id=workspace_id,
        token_hash=hash_token(raw),
        role=role,
        expires_at=datetime.now(UTC) + timedelta(days=get_settings().invite_days),
        created_by=created_by.id,
    )
    session.add(invite)
    await session.commit()
    return invite, raw


async def _valid_invite(session: AsyncSession, raw: str, lock: bool = False) -> WorkspaceInvite:
    stmt = select(WorkspaceInvite).where(WorkspaceInvite.token_hash == hash_token(raw))
    if lock:
        stmt = stmt.with_for_update()
    invite = (await session.execute(stmt)).scalar_one_or_none()
    if invite is None:
        raise NotFound("Invite not found", code="invite_invalid")
    if invite.used_at is not None:
        raise AppError(
            "This invite link has already been used", code="invite_used", status_code=410
        )
    if invite.expires_at <= datetime.now(UTC):
        raise AppError("This invite link has expired", code="invite_expired", status_code=410)
    return invite


async def preview_invite(
    session: AsyncSession, raw: str
) -> tuple[WorkspaceInvite, Workspace, User]:
    invite = await _valid_invite(session, raw)
    ws = await session.get(Workspace, invite.workspace_id)
    inviter = await session.get(User, invite.created_by)
    if ws is None or inviter is None:
        raise NotFound("Invite not found", code="invite_invalid")
    return invite, ws, inviter


async def accept_invite(session: AsyncSession, raw: str, user: User) -> Workspace:
    invite = await _valid_invite(session, raw, lock=True)
    ws = await session.get(Workspace, invite.workspace_id)
    if ws is None:
        raise NotFound("Invite not found", code="invite_invalid")
    existing = await repo.get_member(session, ws.id, user.id)
    if existing is None:
        session.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=invite.role))
    elif not Role(existing.role).at_least(Role(invite.role)):
        existing.role = invite.role  # an invite can upgrade, never downgrade
    invite.used_at = datetime.now(UTC)
    invite.used_by = user.id
    await session.commit()
    return ws
