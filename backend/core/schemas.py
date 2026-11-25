from datetime import datetime
from typing import Literal
from uuid import UUID

from ninja import Schema
from pydantic import Field, field_validator


class EntryIn(Schema):
    id: UUID
    content: str
    source: Literal["web", "ios", "android"]
    written_at: datetime
    # 이어 쓰기: 이 기록이 이어지는 옛 기록들. 서버에 아직 없는 id는 건너뛴다
    continues: list[UUID] = Field(default_factory=list, max_length=5)

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


class NamingRef(Schema):
    id: UUID
    label: str


class EntryRef(Schema):
    """이어진 기록을 그 자리에서 보여주기 위한 최소한"""

    id: UUID
    content: str
    written_at: datetime


class EntryOut(Schema):
    id: UUID
    content: str
    source: str
    written_at: datetime
    created_at: datetime
    # 이 기록에 붙은 이름 (내가 붙였거나 수락한 것만)
    namings: list[NamingRef]

    @staticmethod
    def resolve_namings(obj) -> list[dict]:
        # api.entries_with_namings()로 미리 불러온 연결을 쓴다
        return [{"id": link.naming.id, "label": link.naming.label} for link in obj.naming_links.all()]

    # 이 기록이 이어 쓴 옛 기록 / 이 기록에 이어 쓴 새 기록 (내가 이었거나 수락한 것만)
    continues: list[EntryRef]
    continued_by: list[EntryRef]

    # 미리 불러오지 않은 기록(검색 계층 결과 등)에서도 수락된 것만 나가도록 여기서 한 번 더 거른다
    @staticmethod
    def resolve_continues(obj) -> list:
        return [link.to_entry for link in obj.links_out.all() if link.status == "accepted"]

    @staticmethod
    def resolve_continued_by(obj) -> list:
        return [link.from_entry for link in obj.links_in.all() if link.status == "accepted"]


class EntryPage(Schema):
    items: list[EntryOut]
    next_cursor: str | None


class NameIn(Schema):
    label: str

    @field_validator("label")
    @classmethod
    def clean_label(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("이름이 비어 있습니다")
        if len(v) > 80:
            raise ValueError("이름은 80자까지입니다")
        return v


class NamingVersionOut(Schema):
    label: str
    created_at: datetime


class NamingOut(Schema):
    id: UUID
    label: str
    created_at: datetime
    # 오래된 것부터. 마지막이 지금 이름이다
    versions: list[NamingVersionOut]


class NamingDetail(NamingOut):
    # 이 이름이 붙은 기록, 쓴 시각 최신순
    entries: list[EntryOut]


class ContextItemOut(Schema):
    """검색 계층 실험용 (Step 8-2). 점수는 기록끼리의 거리일 뿐, 평가가 아니다 (P1)."""

    entry: EntryOut
    similarity: float
    recency: float
    shared_naming: bool
    score: float
