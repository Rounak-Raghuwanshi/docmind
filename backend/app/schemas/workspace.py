import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel

RoleLiteral = Literal["owner", "editor", "viewer"]


class WorkspaceIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name is required")
        return v


class WorkspaceOut(BaseModel):
    id: uuid.UUID
    name: str
    role: RoleLiteral
    is_personal: bool
    is_demo: bool = False
    document_count: int = 0
    member_count: int = 1
    created_at: datetime


class MemberOut(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    role: RoleLiteral
    joined_at: datetime


class MemberUpdate(BaseModel):
    role: RoleLiteral


class InviteIn(BaseModel):
    role: Literal["editor", "viewer"] = "viewer"


class InviteOut(BaseModel):
    token: str
    url: str
    role: RoleLiteral
    expires_at: datetime


class InvitePreview(BaseModel):
    workspace_id: uuid.UUID
    workspace_name: str
    role: RoleLiteral
    invited_by: str
    expires_at: datetime


class InviteListItem(ORMModel):
    id: uuid.UUID
    role: RoleLiteral
    expires_at: datetime
    used_at: datetime | None
    created_at: datetime
