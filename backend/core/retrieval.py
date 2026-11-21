"""검색 계층 (Step 8-2). 서기가 무엇을 참고할지 정한다.

생성보다 먼저다. 주석이 상투적이면 프롬프트보다 이 파일을 먼저 의심한다 (develop_plan Step 8-8).
여기서 나오는 점수는 기록끼리 얼마나 가까운지일 뿐, 기록이나 나에 대한 평가가 아니다 (P1).
"""

from dataclasses import dataclass

from django.db import transaction
from pgvector.django import CosineDistance

from . import embeddings
from .models import Entry, EntryEmbedding, NamingLink

# 가중치. 실험하면서 고친다. 의미가 가까운 것이 먼저이고, 나머지는 같은 값일 때의 순서를 돕는 정도다
WEIGHT_SIMILARITY = 1.0
WEIGHT_RECENCY = 0.1
WEIGHT_SHARED_NAMING = 0.1
# 이만큼 시간이 지나면 최근성 가산이 절반이 된다
RECENCY_HALF_LIFE_DAYS = 60
# 의미 유사도로 먼저 고른 뒤 다시 줄 세우는 후보 수
CANDIDATES = 50
DEFAULT_LIMIT = 5


@dataclass
class ContextItem:
    entry: Entry
    similarity: float
    recency: float
    shared_naming: bool
    score: float


def ensure_embeddings() -> int:
    """임베딩이 없거나 지금 모델과 다른 기록을 임베딩한다. 만든 개수를 돌려준다.

    쓰기 경로에는 넣지 않는다: 공급사가 멈춰도 기록 저장은 늦어지거나 실패하면 안 된다.
    """
    model = embeddings.current_model()
    missing = list(Entry.objects.exclude(embedding__model=model).order_by("written_at", "id"))
    if not missing:
        return 0
    vectors = embeddings.embed_texts([e.content for e in missing])
    with transaction.atomic():
        for entry, vector in zip(missing, vectors, strict=True):
            EntryEmbedding.objects.update_or_create(entry=entry, defaults={"model": model, "vector": vector})
    return len(missing)


def _accepted_naming_ids(entry_ids) -> dict:
    out: dict = {}
    links = NamingLink.objects.filter(entry_id__in=entry_ids, status=NamingLink.Status.ACCEPTED)
    for entry_id, naming_id in links.values_list("entry_id", "naming_id"):
        out.setdefault(entry_id, set()).add(naming_id)
    return out


def get_history_context(entry: Entry, limit: int = DEFAULT_LIMIT) -> list[ContextItem]:
    """이 기록보다 먼저 쓴 기록 중에서 서기가 참고할 것.

    의미 유사도 + 최근성 + 내가 같은 이름을 붙였는지. 과거가 없으면 빈 목록 (P3).
    고정한 기록(develop_plan에 적힌 세 번째 신호)은 고정 기능이 생기면 더한다.
    """
    if not Entry.objects.filter(written_at__lt=entry.written_at).exists():
        return []
    ensure_embeddings()
    query = EntryEmbedding.objects.get(entry=entry).vector

    candidates = list(
        EntryEmbedding.objects.filter(model=embeddings.current_model(), entry__written_at__lt=entry.written_at)
        .select_related("entry")
        .annotate(distance=CosineDistance("vector", query))
        .order_by("distance")[:CANDIDATES]
    )
    names = _accepted_naming_ids([entry.id, *(c.entry_id for c in candidates)])
    own_names = names.get(entry.id, set())

    items = []
    for c in candidates:
        similarity = 1.0 - float(c.distance)
        age_days = (entry.written_at - c.entry.written_at).total_seconds() / 86400
        recency = 0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS)
        shared = bool(own_names & names.get(c.entry_id, set()))
        score = WEIGHT_SIMILARITY * similarity + WEIGHT_RECENCY * recency + WEIGHT_SHARED_NAMING * shared
        items.append(ContextItem(c.entry, similarity, recency, shared, score))
    items.sort(key=lambda i: (-i.score, -i.entry.written_at.timestamp()))
    return items[:limit]
