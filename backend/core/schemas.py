from datetime import datetime
from typing import Literal
from uuid import UUID

from ninja import Schema
from pydantic import field_validator


class EntryIn(Schema):
    id: UUID
    content: str
    source: Literal["web", "ios", "android"]
    written_at: datetime

    @field_validator("content")
    @classmethod
    def not_blank(cls, v: str) -> str:
        # 아무리 짧아도 되지만, 비어 있으면 기록이 아니다
        if not v.strip():
            raise ValueError("content가 비어 있습니다")
        return v

    @field_validator("written_at")
    @classmethod
    def must_be_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("written_at에는 시간대가 있어야 합니다 (예: 2026-11-06T14:00:00+09:00)")
        return v


class EntryOut(Schema):
    id: UUID
    content: str
    source: str
    written_at: datetime
    created_at: datetime


class EntryPage(Schema):
    items: list[EntryOut]
    next_cursor: str | None
