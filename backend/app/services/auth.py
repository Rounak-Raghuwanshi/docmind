"""Accounts and sessions.

Access token: short-lived JWT, kept in memory by the SPA, sent as a Bearer header.
Refresh token: opaque 256-bit value in an httpOnly cookie, stored as SHA-256, rotated on every
use. Presenting an already-rotated token means it was stolen (or replayed), so the whole token
family is revoked and every session descended from that login must sign in again.
"""

import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.errors import Conflict, NotFound, Unauthorized
from app.models import RefreshToken, Role, User, Workspace, WorkspaceMember
from app.repositories import users as users_repo
from app.security import (
    burn_password_check,
    create_access_token,
    hash_password,
    hash_token,
    new_opaque_token,
    verify_password,
)
from app.services.demo import copy_showcase_conversations, find_demo_workspace

log = logging.getLogger(__name__)

# Two tabs refreshing at the same moment both present the same token. Within this window a
# just-rotated token gets a sibling token instead of being treated as stolen.
REUSE_GRACE_SECONDS = 10


@dataclass(slots=True)
class Session:
    user: User
    access_token: str
    expires_in: int
    refresh_token: str


async def create_personal_workspace(session: AsyncSession, user: User) -> Workspace:
    ws = Workspace(name="Personal", owner_id=user.id, is_personal=True)
    session.add(ws)
    await session.flush()
    session.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=Role.owner))
    return ws


async def register(session: AsyncSession, email: str, full_name: str, password: str) -> User:
    user = User(email=email, full_name=full_name, hashed_password=hash_password(password))
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as e:
        await session.rollback()
        raise Conflict("An account with this email already exists", code="email_taken") from e
    await create_personal_workspace(session, user)
    await session.commit()
    log.info("user registered", extra={"user_id": str(user.id)})
    return user


async def _issue(
    session: AsyncSession, user: User, family_id: uuid.UUID
) -> tuple[RefreshToken, str]:
    raw = new_opaque_token()
    token = RefreshToken(
        user_id=user.id,
        family_id=family_id,
        token_hash=hash_token(raw),
        expires_at=datetime.now(UTC) + timedelta(days=get_settings().refresh_token_days),
    )
    session.add(token)
    await session.flush()
    return token, raw


async def login(session: AsyncSession, email: str, password: str) -> Session:
    user = await users_repo.get_by_email(session, email)
    if user is None:
        burn_password_check(password)  # same latency whether or not the email exists
        raise Unauthorized("Incorrect email or password", code="invalid_credentials")
    if not verify_password(password, user.hashed_password):
        raise Unauthorized("Incorrect email or password", code="invalid_credentials")
    return await start_session(session, user)


async def start_session(session: AsyncSession, user: User) -> Session:
    _, raw = await _issue(session, user, family_id=uuid.uuid4())
    await session.commit()
    access, expires_in = create_access_token(user.id)
    return Session(user=user, access_token=access, expires_in=expires_in, refresh_token=raw)


async def refresh(session: AsyncSession, raw_token: str | None) -> Session:
    if not raw_token:
        raise Unauthorized("No session", code="no_session")
    token = await users_repo.get_refresh_token(session, hash_token(raw_token))
    if token is None:
        raise Unauthorized("Session expired", code="session_expired")
    now = datetime.now(UTC)
    in_grace = False
    if (
        token.revoked_at is not None
        and token.replaced_by is not None
        and now - token.revoked_at < timedelta(seconds=REUSE_GRACE_SECONDS)
    ):
        # Only a benign race if the family is still alive (its successor not revoked).
        successor = await session.get(RefreshToken, token.replaced_by)
        in_grace = successor is not None and successor.revoked_at is None
    if token.revoked_at is not None and not in_grace:
        # Reuse of a rotated token: assume theft and kill the whole family.
        await users_repo.revoke_family(session, token.family_id)
        await session.commit()
        log.warning("refresh token reuse detected", extra={"user_id": str(token.user_id)})
        raise Unauthorized("Session expired", code="session_reused")
    if token.expires_at <= now:
        raise Unauthorized("Session expired", code="session_expired")

    user = await session.get(User, token.user_id)
    if user is None:
        raise Unauthorized("Session expired", code="session_expired")
    new_token, raw = await _issue(session, user, token.family_id)
    if not in_grace:
        token.revoked_at = now
        token.replaced_by = new_token.id
    await session.commit()
    access, expires_in = create_access_token(user.id)
    return Session(user=user, access_token=access, expires_in=expires_in, refresh_token=raw)


async def logout(session: AsyncSession, raw_token: str | None) -> None:
    if not raw_token:
        return
    token = await users_repo.get_refresh_token(session, hash_token(raw_token))
    if token is not None:
        await users_repo.revoke_family(session, token.family_id)
        await session.commit()


async def create_demo_guest(session: AsyncSession) -> Session:
    """A throwaway account with viewer access to the public demo workspace."""
    demo_ws = await find_demo_workspace(session)
    if demo_ws is None:
        raise NotFound(
            "The demo isn't set up on this server yet. Run `make seed` to create it.",
            code="demo_disabled",
        )
    suffix = secrets.token_hex(4)
    user = User(
        email=f"guest-{suffix}@demo.docmind.local",
        full_name=f"Guest {suffix[:4].upper()}",
        hashed_password=hash_password(secrets.token_urlsafe(24)),
        is_guest=True,
    )
    session.add(user)
    await session.flush()
    await create_personal_workspace(session, user)
    session.add(WorkspaceMember(workspace_id=demo_ws.id, user_id=user.id, role=Role.viewer))
    await copy_showcase_conversations(session, demo_ws, user)
    return await start_session(session, user)
