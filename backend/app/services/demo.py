"""The public demo: find the demo workspace and give each guest a few showcase chats."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Conversation, Message, User, Workspace

SHOWCASE_CONVERSATIONS = 3


async def find_demo_workspace(session: AsyncSession) -> Workspace | None:
    """DEMO_WORKSPACE_ID wins if set; otherwise the workspace flagged is_demo by the seeder."""
    if ws_id := get_settings().demo_workspace_id:
        return await session.get(Workspace, uuid.UUID(ws_id))
    return (await session.execute(select(Workspace).where(Workspace.is_demo))).scalar_one_or_none()


async def copy_showcase_conversations(session: AsyncSession, demo: Workspace, guest: User) -> None:
    """Conversations are private per user, so a new guest would see an empty chat list.
    Give them copies of the demo owner's most recent conversations to explore."""
    convs = (
        (
            await session.execute(
                select(Conversation)
                .where(Conversation.workspace_id == demo.id, Conversation.user_id == demo.owner_id)
                .order_by(Conversation.updated_at.desc())
                .limit(SHOWCASE_CONVERSATIONS)
            )
        )
        .scalars()
        .all()
    )
    for conv in convs:
        copy = Conversation(
            workspace_id=demo.id,
            user_id=guest.id,
            title=conv.title,
            document_filter=conv.document_filter,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )
        session.add(copy)
        await session.flush()
        messages = (
            (
                await session.execute(
                    select(Message)
                    .where(Message.conversation_id == conv.id)
                    .order_by(Message.created_at)
                )
            )
            .scalars()
            .all()
        )
        for m in messages:
            session.add(
                Message(
                    conversation_id=copy.id,
                    role=m.role,
                    content=m.content,
                    citations=m.citations,
                    status=m.status,
                    model=m.model,
                    rewritten_question=m.rewritten_question,
                    not_found=m.not_found,
                    cached=m.cached,
                    prompt_tokens=m.prompt_tokens,
                    completion_tokens=m.completion_tokens,
                    retrieval_ms=m.retrieval_ms,
                    rerank_ms=m.rerank_ms,
                    first_token_ms=m.first_token_ms,
                    total_ms=m.total_ms,
                    retrieval_debug=m.retrieval_debug,
                    created_at=m.created_at,
                )
            )
