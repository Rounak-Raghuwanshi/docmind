import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import DB, CurrentUser, OwnConversation, WorkspaceAccess, rate_limit, require_role
from app.errors import AppError, NotFound
from app.models import Conversation, Document, Message, MessageFeedback, Role, User, WorkspaceMember
from app.schemas.chat import (
    AskIn,
    ConversationDetail,
    ConversationIn,
    ConversationOut,
    ConversationUpdate,
    FeedbackIn,
    MessageOut,
    RetrievalDebugOut,
)
from app.schemas.common import Page, decode_cursor, encode_cursor
from app.services.chat import DEFAULT_TITLE, ChatService
from app.services.sse import SSE_HEADERS

router = APIRouter(tags=["chat"])

Viewer = Annotated[WorkspaceAccess, Depends(require_role(Role.viewer))]
MAX_MESSAGES = 500


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat


async def _validate_filter(
    session: AsyncSession, workspace_id: uuid.UUID, ids: list[uuid.UUID] | None
) -> list[uuid.UUID] | None:
    if not ids:
        return None
    unique = list(dict.fromkeys(ids))
    found = await session.scalar(
        select(func.count()).where(Document.workspace_id == workspace_id, Document.id.in_(unique))
    )
    if found != len(unique):
        raise AppError(
            "Some selected documents are not in this workspace", code="invalid_document_filter"
        )
    return unique


@router.get("/workspaces/{ws}/conversations", response_model=Page[ConversationOut])
async def list_conversations(
    access: Viewer,
    session: DB,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    cursor: str | None = None,
) -> Page[ConversationOut]:
    stmt = (
        select(Conversation)
        .where(
            Conversation.workspace_id == access.workspace.id, Conversation.user_id == access.user.id
        )
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        .limit(limit + 1)
    )
    if after := decode_cursor(cursor):
        stmt = stmt.where(tuple_(Conversation.updated_at, Conversation.id) < tuple_(*after))
    rows = list((await session.execute(stmt)).scalars())
    page, more = rows[:limit], len(rows) > limit
    nxt = encode_cursor(page[-1].updated_at, page[-1].id) if more else None
    return Page(items=[ConversationOut.model_validate(c) for c in page], next_cursor=nxt)


@router.post(
    "/workspaces/{ws}/conversations",
    response_model=ConversationOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(body: ConversationIn, access: Viewer, session: DB) -> ConversationOut:
    conv = Conversation(
        workspace_id=access.workspace.id,
        user_id=access.user.id,
        title=(body.title or "").strip() or DEFAULT_TITLE,
        document_filter=await _validate_filter(session, access.workspace.id, body.document_ids),
    )
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return ConversationOut.model_validate(conv)


@router.get("/conversations/{conv}", response_model=ConversationDetail)
async def get_conversation(
    conv: OwnConversation, user: CurrentUser, session: DB
) -> ConversationDetail:
    rows = (
        await session.execute(
            select(Message, MessageFeedback.rating)
            .outerjoin(
                MessageFeedback,
                (MessageFeedback.message_id == Message.id) & (MessageFeedback.user_id == user.id),
            )
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .limit(MAX_MESSAGES)
        )
    ).all()
    messages = []
    for msg, rating in reversed(rows):
        out = MessageOut.model_validate(msg)
        out.feedback = rating
        messages.append(out)
    return ConversationDetail(
        **ConversationOut.model_validate(conv).model_dump(), messages=messages
    )


@router.patch("/conversations/{conv}", response_model=ConversationOut)
async def update_conversation(
    body: ConversationUpdate, conv: OwnConversation, session: DB
) -> ConversationOut:
    if body.title is not None:
        conv.title = body.title.strip() or conv.title
    if "document_ids" in body.model_fields_set:
        conv.document_filter = await _validate_filter(session, conv.workspace_id, body.document_ids)
    await session.commit()
    await session.refresh(conv)
    return ConversationOut.model_validate(conv)


@router.delete("/conversations/{conv}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conv: OwnConversation, session: DB) -> Response:
    await session.delete(conv)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/conversations/{conv}/messages",
    dependencies=[Depends(rate_limit("chat"))],
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def ask(
    body: AskIn,
    conv: OwnConversation,
    session: DB,
    chat: Annotated[ChatService, Depends(get_chat_service)],
) -> StreamingResponse:
    """Ask a question. The answer streams back as SSE: meta, token*, citations, done."""
    conversation_id = conv.id
    await session.close()  # the stream opens its own short-lived sessions
    return StreamingResponse(
        chat.stream_answer(conversation_id, body.question),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


async def _own_message(session: AsyncSession, user: User, message_id: uuid.UUID) -> Message:
    msg = (
        await session.execute(
            select(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .join(
                WorkspaceMember,
                (WorkspaceMember.workspace_id == Conversation.workspace_id)
                & (WorkspaceMember.user_id == user.id),
            )
            .where(Message.id == message_id, Conversation.user_id == user.id)
        )
    ).scalar_one_or_none()
    if msg is None:
        raise NotFound("Message not found")
    return msg


@router.post("/messages/{msg}/feedback", status_code=status.HTTP_204_NO_CONTENT)
async def give_feedback(
    msg: uuid.UUID, body: FeedbackIn, user: CurrentUser, session: DB
) -> Response:
    message = await _own_message(session, user, msg)
    if message.role != "assistant":
        raise AppError("Feedback can only be given on answers", code="invalid_target")
    stmt = pg_insert(MessageFeedback).values(
        message_id=message.id, user_id=user.id, rating=body.rating, comment=body.comment
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[MessageFeedback.message_id, MessageFeedback.user_id],
        set_={"rating": body.rating, "comment": body.comment, "created_at": func.now()},
    )
    await session.execute(stmt)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/messages/{msg}/retrieval", response_model=RetrievalDebugOut)
async def retrieval_debug(msg: uuid.UUID, user: CurrentUser, session: DB) -> RetrievalDebugOut:
    message = await _own_message(session, user, msg)
    return RetrievalDebugOut(
        message_id=message.id,
        rewritten_question=message.rewritten_question,
        retrieval_ms=message.retrieval_ms,
        rerank_ms=message.rerank_ms,
        chunks=message.retrieval_debug or [],
    )
