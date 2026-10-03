"""Request dependencies: the current user, workspace role checks and rate limits.

Tenant isolation rule: a resource the caller can't access is reported as 404, never 403,
so IDs from other workspaces can't even be confirmed to exist. 403 is only returned when
the caller is a member but their role is too low.
"""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, Request
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_session
from app.errors import Forbidden, NotFound, Unauthorized
from app.models import Conversation, Document, Role, User, Workspace, WorkspaceMember
from app.redis_client import get_redis
from app.security import decode_access_token
from app.services.rate_limit import check_rate_limit

DB = Annotated[AsyncSession, Depends(get_session)]
RedisDep = Annotated[Redis, Depends(get_redis)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_current_user(
    session: DB, authorization: Annotated[str | None, Header()] = None
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise Unauthorized("Not authenticated")
    user_id = decode_access_token(authorization[7:].strip())
    if user_id is None:
        raise Unauthorized("Invalid or expired token", code="token_expired")
    user = await session.get(User, user_id)
    if user is None:
        raise Unauthorized("Invalid or expired token", code="token_expired")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


@dataclass(slots=True)
class WorkspaceAccess:
    workspace: Workspace
    role: Role
    user: User


async def load_access(
    session: AsyncSession, user: User, workspace_id: uuid.UUID, minimum: Role
) -> WorkspaceAccess:
    row = (
        await session.execute(
            select(Workspace, WorkspaceMember.role)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(Workspace.id == workspace_id, WorkspaceMember.user_id == user.id)
        )
    ).first()
    if row is None:
        raise NotFound("Workspace not found")
    role = Role(row[1])
    if not role.at_least(minimum):
        raise Forbidden(f"This action needs the {minimum.value} role in this workspace")
    return WorkspaceAccess(workspace=row[0], role=role, user=user)


def require_role(minimum: Role) -> Callable[..., Awaitable[WorkspaceAccess]]:
    """Dependency for routes with a {ws} path parameter."""

    async def dep(ws: uuid.UUID, user: CurrentUser, session: DB) -> WorkspaceAccess:
        return await load_access(session, user, ws, minimum)

    return dep


@dataclass(slots=True)
class DocumentAccess:
    document: Document
    access: WorkspaceAccess


def require_document_role(minimum: Role) -> Callable[..., Awaitable[DocumentAccess]]:
    """For /documents/{doc} routes: resolve the document's workspace, then check the role."""

    async def dep(doc: uuid.UUID, user: CurrentUser, session: DB) -> DocumentAccess:
        document = await session.get(Document, doc)
        if document is None:
            raise NotFound("Document not found")
        try:
            access = await load_access(session, user, document.workspace_id, minimum)
        except NotFound as e:
            raise NotFound("Document not found") from e
        return DocumentAccess(document=document, access=access)

    return dep


async def get_own_conversation(conv: uuid.UUID, user: CurrentUser, session: DB) -> Conversation:
    """Conversations are private to their creator, who must still be a workspace member."""
    row = (
        await session.execute(
            select(Conversation)
            .join(
                WorkspaceMember,
                (WorkspaceMember.workspace_id == Conversation.workspace_id)
                & (WorkspaceMember.user_id == user.id),
            )
            .where(Conversation.id == conv, Conversation.user_id == user.id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFound("Conversation not found")
    return row


OwnConversation = Annotated[Conversation, Depends(get_own_conversation)]


def client_ip(request: Request) -> str:
    # Uvicorn runs with --proxy-headers, so request.client is the real client behind a proxy.
    return request.client.host if request.client else "unknown"


def rate_limit(name: str, per_user: bool = True) -> Callable[..., Awaitable[None]]:
    windows = {
        "login": (lambda s: s.login_per_minute, 60),
        "chat": (lambda s: s.chat_per_minute, 60),
        "upload": (lambda s: s.uploads_per_hour, 3600),
        "demo": (lambda s: s.demo_logins_per_hour, 3600),
    }
    limit_of, window = windows[name]

    if per_user:

        async def user_dep(user: CurrentUser, redis: RedisDep, settings: SettingsDep) -> None:
            if settings.rate_limit_enabled:
                await check_rate_limit(redis, f"{name}:u:{user.id}", limit_of(settings), window)

        return user_dep

    async def ip_dep(request: Request, redis: RedisDep, settings: SettingsDep) -> None:
        if settings.rate_limit_enabled:
            await check_rate_limit(
                redis, f"{name}:ip:{client_ip(request)}", limit_of(settings), window
            )

    return ip_dep
