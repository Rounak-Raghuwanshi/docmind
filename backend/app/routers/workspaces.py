import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy import select

from app.config import get_settings
from app.deps import DB, CurrentUser, WorkspaceAccess, require_role
from app.errors import AppError, Forbidden, NotFound
from app.models import Role, WorkspaceInvite
from app.redis_client import get_arq
from app.repositories import workspaces as repo
from app.schemas.common import Page, decode_cursor, encode_cursor
from app.schemas.workspace import (
    InviteIn,
    InviteListItem,
    InviteOut,
    InvitePreview,
    MemberOut,
    MemberUpdate,
    WorkspaceIn,
    WorkspaceOut,
)
from app.services import workspaces as service

router = APIRouter(tags=["workspaces"])

Viewer = Annotated[WorkspaceAccess, Depends(require_role(Role.viewer))]
Owner = Annotated[WorkspaceAccess, Depends(require_role(Role.owner))]


@router.get("/workspaces", response_model=Page[WorkspaceOut])
async def list_workspaces(
    user: CurrentUser,
    session: DB,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
) -> Page[WorkspaceOut]:
    rows = await repo.list_for_user(session, user.id, limit + 1, decode_cursor(cursor))
    page, more = rows[:limit], len(rows) > limit
    nxt = encode_cursor(page[-1]["created_at"], page[-1]["id"]) if more else None
    return Page(items=[WorkspaceOut(**r) for r in page], next_cursor=nxt)


@router.post("/workspaces", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_workspace(body: WorkspaceIn, user: CurrentUser, session: DB) -> WorkspaceOut:
    if user.is_guest:
        raise Forbidden("Guest accounts can't create workspaces. Sign up to create your own.")
    ws = await service.create_workspace(session, user, body.name)
    return WorkspaceOut(
        id=ws.id, name=ws.name, role="owner", is_personal=False, created_at=ws.created_at
    )


async def _workspace_out(session: DB, user_id: uuid.UUID, workspace_id: uuid.UUID) -> WorkspaceOut:
    row = await repo.get_for_user(session, user_id, workspace_id)
    if row is None:
        raise NotFound("Workspace not found")
    return WorkspaceOut(**row)


@router.get("/workspaces/{ws}", response_model=WorkspaceOut)
async def get_workspace(access: Viewer, session: DB) -> WorkspaceOut:
    return await _workspace_out(session, access.user.id, access.workspace.id)


@router.patch("/workspaces/{ws}", response_model=WorkspaceOut)
async def rename_workspace(body: WorkspaceIn, access: Owner, session: DB) -> WorkspaceOut:
    access.workspace.name = body.name
    await session.commit()
    return await _workspace_out(session, access.user.id, access.workspace.id)


@router.delete("/workspaces/{ws}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(access: Owner, session: DB) -> Response:
    if access.workspace.is_personal:
        raise AppError("Your personal workspace can't be deleted", code="personal_workspace")
    keys = await service.storage_keys(session, access.workspace.id)
    await session.delete(access.workspace)  # cascades to members, documents, chunks, chats
    await session.commit()
    if keys:
        await (await get_arq()).enqueue_job("delete_storage_objects", keys)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/workspaces/{ws}/members", response_model=list[MemberOut])
async def list_members(access: Viewer, session: DB) -> list[MemberOut]:
    return [MemberOut(**m) for m in await repo.list_members(session, access.workspace.id)]


@router.patch("/workspaces/{ws}/members/{user_id}", response_model=MemberOut)
async def change_member_role(
    user_id: uuid.UUID, body: MemberUpdate, access: Owner, session: DB
) -> MemberOut:
    await service.change_role(session, access.workspace.id, user_id, Role(body.role))
    members = await repo.list_members(session, access.workspace.id)
    return MemberOut(**next(m for m in members if m["user_id"] == user_id))


@router.delete("/workspaces/{ws}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(user_id: uuid.UUID, access: Viewer, session: DB) -> Response:
    # Owners can remove anyone; everyone else can only remove themselves (leave).
    if user_id != access.user.id and access.role != Role.owner:
        raise Forbidden("Only owners can remove other members")
    if access.workspace.is_personal and user_id == access.workspace.owner_id:
        raise AppError("You can't leave your personal workspace", code="personal_workspace")
    await service.remove_member(session, access.workspace.id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/workspaces/{ws}/invites", response_model=InviteOut, status_code=status.HTTP_201_CREATED
)
async def create_invite(body: InviteIn, access: Owner, session: DB) -> InviteOut:
    invite, raw = await service.create_invite(
        session, access.workspace.id, access.user, Role(body.role)
    )
    url = f"{get_settings().public_app_url.rstrip('/')}/invite/{raw}"
    return InviteOut(token=raw, url=url, role=body.role, expires_at=invite.expires_at)


@router.get("/workspaces/{ws}/invites", response_model=list[InviteListItem])
async def list_invites(access: Owner, session: DB) -> list[InviteListItem]:
    rows = await session.execute(
        select(WorkspaceInvite)
        .where(WorkspaceInvite.workspace_id == access.workspace.id)
        .order_by(WorkspaceInvite.created_at.desc())
        .limit(50)
    )
    return [InviteListItem.model_validate(i) for i in rows.scalars()]


@router.get("/invites/{token}", response_model=InvitePreview)
async def preview_invite(token: str, _: CurrentUser, session: DB) -> InvitePreview:
    invite, ws, inviter = await service.preview_invite(session, token)
    return InvitePreview(
        workspace_id=ws.id,
        workspace_name=ws.name,
        role=invite.role,
        invited_by=inviter.full_name,
        expires_at=invite.expires_at,
    )


@router.post("/invites/{token}/accept", response_model=WorkspaceOut)
async def accept_invite(token: str, user: CurrentUser, session: DB) -> WorkspaceOut:
    if user.is_guest:
        raise Forbidden("Guest accounts can't join workspaces. Sign up first.")
    ws = await service.accept_invite(session, token, user)
    return await _workspace_out(session, user.id, ws.id)
