import base64
import json
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.errors import AppError


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    items: list[T]
    next_cursor: str | None = None


def encode_cursor(ts: datetime, id_: uuid.UUID) -> str:
    raw = json.dumps([ts.isoformat(), str(id_)]).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> tuple[datetime, uuid.UUID] | None:
    if not cursor:
        return None
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        ts, id_ = json.loads(raw)
        return datetime.fromisoformat(ts), uuid.UUID(id_)
    except (ValueError, TypeError) as e:
        raise AppError("Invalid cursor", code="invalid_cursor") from e
