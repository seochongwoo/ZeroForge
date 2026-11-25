import base64
import json
from datetime import datetime
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Max, Prefetch, Q
from django.db.models.functions import Greatest
from django.shortcuts import get_object_or_404
from ninja import NinjaAPI, Query, Status
from ninja.errors import HttpError

from .auth import TokenAuth
from .embeddings import EmbeddingUnavailable
from .models import Entry, EntryLink, Naming, NamingLink, NamingVersion
from .retrieval import MIN_SIMILARITY, get_history_context
from .schemas import ContextItemOut, EntryIn, EntryOut, EntryPage, NameIn, NamingDetail, NamingOut

api = NinjaAPI(title="ZeroForge", version="0.1", auth=TokenAuth(), urls_namespace="api")

MAX_LIMIT = 200


def entries_with_namings():
    """EntryOut의 이름·이어진 기록을 한 번에 불러온다. 거절·제안 상태는 보여주지 않는다."""
    accepted = NamingLink.Status.ACCEPTED
    links = NamingLink.objects.filter(status=accepted).select_related("naming")
    entry_links = EntryLink.objects.filter(status=accepted)
    return Entry.objects.prefetch_related(
        Prefetch("naming_links", queryset=links),
        Prefetch("links_out", queryset=entry_links.select_related("to_entry").order_by("to_entry__written_at")),
        Prefetch("links_in", queryset=entry_links.select_related("from_entry").order_by("from_entry__written_at")),
    )


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
    existing = entries_with_namings().filter(id=payload.id).first()
    if existing:
        return Status(200, existing)
    data = payload.dict()
    continues = set(data.pop("continues")) - {payload.id}
    try:
        with transaction.atomic():
            entry = Entry.objects.create(**data)
            # 이어 쓰기. 기록과 연결을 함께 만들어서, 재전송해도 연결이 따로 생기거나 빠지지 않는다.
            # outbox는 쓴 순서대로 올라가므로 이을 기록은 보통 이미 있다. 없으면 건너뛴다 (막지 않는다)
            targets = Entry.objects.filter(id__in=continues)
            EntryLink.objects.bulk_create([EntryLink(from_entry=entry, to_entry=t) for t in targets])
    except IntegrityError:
        # 동시에 같은 id가 들어온 경우
        return Status(200, entries_with_namings().get(id=payload.id))
    return Status(201, entries_with_namings().get(id=payload.id))


@api.get("/entries", response=EntryPage)
def list_entries(request, cursor: str | None = None, limit: int = Query(50, ge=1, le=MAX_LIMIT)):
    """기록 목록. 쓴 시각 기준 최신순, 커서 기반 페이지네이션."""
    qs = entries_with_namings().order_by("-written_at", "-id")
    if cursor:
        written_at, entry_id = decode_cursor(cursor)
        qs = qs.filter(Q(written_at__lt=written_at) | Q(written_at=written_at, id__lt=entry_id))
    items = list(qs[: limit + 1])
    next_cursor = encode_cursor(items[limit - 1]) if len(items) > limit else None
    return {"items": items[:limit], "next_cursor": next_cursor}



@api.get("/entries/{entry_id}/context", response={200: list[ContextItemOut], 503: dict})
def history_context(
    request,
    entry_id: UUID,
    limit: int = Query(5, ge=1, le=20),
    min_similarity: float = Query(MIN_SIMILARITY, ge=0, le=1),
):
    """이 기록과 이어지는 과거 기록. 기록을 펼쳤을 때 보여주고, 서기가 참고할 후보이기도 하다.

    먼저 쓴 기록 중 의미가 충분히 가까운 것이 없으면 빈 목록 (P3). 실험할 때는 min_similarity=0으로 전부 본다.
    """
    entry = get_object_or_404(Entry, id=entry_id)
    try:
        return Status(200, get_history_context(entry, limit=limit, min_similarity=min_similarity))
    except EmbeddingUnavailable as exc:
        return Status(503, {"detail": str(exc)})

# ---- 이름 (Step 7). 이름은 전부 내가 붙인다 (P2) ----


def namings_with_versions():
    return Naming.objects.prefetch_related("versions")


def find_or_create_naming(label: str) -> Naming:
    """지금 이름이 같은 것이 있으면 그것을, 없으면 새로 만든다."""
    naming = Naming.objects.filter(label__iexact=label).first()
    if naming:
        return naming
    try:
        with transaction.atomic():
            naming = Naming.objects.create(label=label)
            NamingVersion.objects.create(naming=naming, label=label)
    except IntegrityError:
        # 동시에 같은 이름이 만들어진 경우
        return Naming.objects.get(label__iexact=label)
    return naming


@api.get("/namings", response=list[NamingOut])
def list_namings(request):
    """기록이 하나라도 붙어 있는 이름 (이름 목록·자동완성용). 최근에 쓴 이름이 먼저.

    "쓴" = 기록에 붙였거나 이름을 바꾼 때. 개수는 돌려주지 않는다 (P4).
    모든 기록에서 떼어진 이름은 목록에서 빠지지만, 같은 이름을 다시 붙이면 그 이름(과 변천)으로 돌아온다.
    """
    accepted = NamingLink.Status.ACCEPTED
    return (
        namings_with_versions()
        .filter(links__status=accepted)
        .annotate(last_used=Greatest(Max("links__created_at"), Max("versions__created_at")))
        .order_by("-last_used", "label")
    )


@api.get("/namings/{naming_id}", response=NamingDetail)
def get_naming(request, naming_id: UUID):
    """이름 하나: 변천과 이 이름이 붙은 기록."""
    naming = get_object_or_404(namings_with_versions(), id=naming_id)
    naming.entries = list(
        entries_with_namings()
        .filter(naming_links__naming=naming, naming_links__status=NamingLink.Status.ACCEPTED)
        .order_by("-written_at", "-id")
    )
    return naming


@api.post("/namings/{naming_id}/versions", response={200: NamingOut, 409: dict})
def rename_naming(request, naming_id: UUID, payload: NameIn):
    """이름 바꾸기. 덮어쓰지 않고 새 버전을 쌓는다."""
    with transaction.atomic():
        naming = get_object_or_404(Naming.objects.select_for_update(), id=naming_id)
        if naming.label != payload.label:
            if Naming.objects.filter(label__iexact=payload.label).exclude(id=naming.id).exists():
                return Status(409, {"detail": "이미 있는 이름입니다"})
            # 대소문자만 바꾸는 것도 변천으로 남긴다
            NamingVersion.objects.create(naming=naming, label=payload.label)
            naming.label = payload.label
            naming.save(update_fields=["label"])
    return Status(200, namings_with_versions().get(id=naming_id))


@api.post("/entries/{entry_id}/namings", response=EntryOut)
def attach_naming(request, entry_id: UUID, payload: NameIn):
    """기록에 이름 붙이기. 같은 이름이 있으면 그것을 쓰고, 없으면 새로 만든다. 여러 번 보내도 한 번만 붙는다."""
    entry = get_object_or_404(Entry, id=entry_id)
    with transaction.atomic():
        naming = find_or_create_naming(payload.label)
        link, created = NamingLink.objects.get_or_create(entry=entry, naming=naming)
        if not created and link.status != NamingLink.Status.ACCEPTED:
            # 거절했거나 제안 상태였던 것을 내가 직접 붙이면 내 연결이 된다
            link.author, link.status = NamingLink.Author.USER, NamingLink.Status.ACCEPTED
            link.save(update_fields=["author", "status"])
    return entries_with_namings().get(id=entry_id)


@api.delete("/entries/{entry_id}/namings/{naming_id}", response=EntryOut)
def detach_naming(request, entry_id: UUID, naming_id: UUID):
    """내가 붙인 이름 떼기. 이름 자체와 그 변천은 남는다."""
    get_object_or_404(Entry, id=entry_id)
    NamingLink.objects.filter(entry_id=entry_id, naming_id=naming_id, author=NamingLink.Author.USER).delete()
    return entries_with_namings().get(id=entry_id)
