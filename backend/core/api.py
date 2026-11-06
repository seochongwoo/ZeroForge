import base64
import json
from datetime import datetime
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Q
from ninja import NinjaAPI, Query, Status
from ninja.errors import HttpError

from .auth import TokenAuth
from .models import Entry
from .schemas import EntryIn, EntryOut, EntryPage

api = NinjaAPI(title="ZeroForge", version="0.1", auth=TokenAuth(), urls_namespace="api")

MAX_LIMIT = 200


def encode_cursor(entry: Entry) -> str:
    raw = json.dumps([entry.written_at.isoformat(), str(entry.id)])
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        written_at, entry_id = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return datetime.fromisoformat(written_at), UUID(entry_id)
    except (ValueError, TypeError) as exc:
        raise HttpError(400, "잘못된 cursor입니다") from exc


@api.post("/entries", response={200: EntryOut, 201: EntryOut})
def create_entry(request, payload: EntryIn):
    """기록 저장. 같은 id가 이미 있으면 기존 기록을 그대로 돌려준다 (멱등).

    Entry는 불변이므로, 같은 id로 다른 내용을 보내도 덮어쓰지 않는다.
    """
    existing = Entry.objects.filter(id=payload.id).first()
    if existing:
        return Status(200, existing)
    try:
        with transaction.atomic():
            entry = Entry.objects.create(**payload.dict())
    except IntegrityError:
        # 동시에 같은 id가 들어온 경우
        return Status(200, Entry.objects.get(id=payload.id))
    return Status(201, entry)


@api.get("/entries", response=EntryPage)
def list_entries(request, cursor: str | None = None, limit: int = Query(50, ge=1, le=MAX_LIMIT)):
    """기록 목록. 쓴 시각 기준 최신순, 커서 기반 페이지네이션."""
    qs = Entry.objects.order_by("-written_at", "-id")
    if cursor:
        written_at, entry_id = decode_cursor(cursor)
        qs = qs.filter(Q(written_at__lt=written_at) | Q(written_at=written_at, id__lt=entry_id))
    items = list(qs[: limit + 1])
    next_cursor = encode_cursor(items[limit - 1]) if len(items) > limit else None
    return {"items": items[:limit], "next_cursor": next_cursor}
