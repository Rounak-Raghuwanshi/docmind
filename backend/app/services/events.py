"""Document status events: the worker publishes, the API relays them to browsers over SSE."""

import json
import logging
import uuid
from typing import Any

from redis.asyncio import Redis

log = logging.getLogger(__name__)


def documents_channel(workspace_id: uuid.UUID | str) -> str:
    return f"ws:{workspace_id}:documents"


async def publish_document_event(
    redis: Redis, workspace_id: uuid.UUID | str, payload: dict[str, Any]
) -> None:
    try:
        await redis.publish(documents_channel(workspace_id), json.dumps(payload, default=str))
    except Exception:
        log.warning("failed to publish document event", exc_info=True)
