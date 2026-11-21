"""검색 계층 테스트 (Step 8-2).

임베딩 공급사는 부르지 않는다. 문장 끝의 '#ab' 같은 표시로 축을 정하는 가짜 임베딩을 쓴다.
테스트 데이터는 지어낸 문장만 쓴다 (P8).
"""

import io
import json
import math
import urllib.error
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from django.core.management import call_command

from core import embeddings
from core.models import EMBEDDING_DIMENSIONS, Entry, EntryEmbedding, Naming, NamingLink
from core.retrieval import get_history_context

TOKEN = "test-token"
KST = timezone(timedelta(hours=9))
DAY0 = datetime(2026, 11, 1, 12, 0, tzinfo=KST)

pytestmark = pytest.mark.django_db


def fake_vector(text: str) -> list[float]:
    """'#ab' → a축과 b축을 반씩. 표시가 없으면 마지막 축."""
    tags = text.rsplit("#", 1)[1] if "#" in text else ""
    v = [0.0] * EMBEDDING_DIMENSIONS
    for ch in tags or "~":
        v[(ord(ch) - ord("a")) % EMBEDDING_DIMENSIONS] += 1.0
    norm = math.sqrt(sum(x * x for x in v))
    return [x / norm for x in v]


@pytest.fixture(autouse=True)
def setup(settings, monkeypatch):
    settings.ZF_TOKEN = TOKEN
    settings.EMBEDDING_MODEL = "fake-1"
    calls = []

    def fake_embed(texts):
        calls.append(list(texts))
        return [fake_vector(t) for t in texts]

    monkeypatch.setattr(embeddings, "embed_texts", fake_embed)
    return calls


@pytest.fixture
def calls(setup):
    return setup


def entry(text, days=0, hours=0):
    return Entry.objects.create(
        id=uuid.uuid4(), content=f"지어낸 문장 {text}", source="web", written_at=DAY0 + timedelta(days=days, hours=hours)
    )


def name(e, label):
    naming, _ = Naming.objects.get_or_create(label=label)
    NamingLink.objects.create(entry=e, naming=naming)


def ids(items):
    return [i.entry.id for i in items]


def test_no_past_means_no_context_and_no_embedding_call(calls):
    first = entry("#a")
    entry("#a", days=1)  # 나중에 쓴 기록은 과거가 아니다
    assert get_history_context(first) == []
    assert calls == []


def test_only_earlier_entries_most_similar_first():
    far = entry("#c", days=0)
    near = entry("#a", days=1)
    half = entry("#ab", days=2)
    query = entry("#a", days=3)
    later = entry("#a", days=4)

    items = get_history_context(query, min_similarity=0)
    assert ids(items) == [near.id, half.id, far.id]
    assert query.id not in ids(items) and later.id not in ids(items)
    assert items[0].similarity == pytest.approx(1.0)
    assert items[1].similarity == pytest.approx(1 / math.sqrt(2))


def test_limit():
    for d in range(4):
        entry("#a", days=d)
    query = entry("#a", days=10)
    assert len(get_history_context(query, limit=2)) == 2


def test_far_meaning_is_not_context():
    entry("#ab", days=0)  # 유사도 0.71
    entry("#abc", days=1)  # 0.58: 기준선 아래
    entry("#z", days=2)  # 0
    query = entry("#a", days=3)
    items = get_history_context(query)
    assert [round(i.similarity, 2) for i in items] == [0.71]


def test_nothing_close_means_no_context():
    entry("#z", days=0)
    query = entry("#a", days=1)
    assert get_history_context(query) == []


def test_shared_name_only_settles_near_ties():
    query = entry("#aab", days=1)
    # 0.949 대 0.913: 0.03보다 크게 차이 나면 같은 이름이어도 더 가까운 쪽이 먼저
    closer = entry("#ab", days=0)
    named_far = entry("#aabc", days=0)
    # 1.0 대 0.99: 거의 같으면 같은 이름이 먼저
    near = entry("#aab", days=0)
    named_near = entry("#aaab", days=0)
    for e in (named_far, named_near, query):
        name(e, "지어낸 이름")
    order = ids(get_history_context(query, min_similarity=0))
    assert order.index(closer.id) < order.index(named_far.id)
    assert order.index(named_near.id) < order.index(near.id)


def test_embeds_missing_once_and_again_when_model_changes(settings, calls):
    entry("#a")
    query = entry("#a", days=1)
    get_history_context(query)
    get_history_context(query)
    assert len(calls) == 1 and len(calls[0]) == 2

    settings.EMBEDDING_MODEL = "fake-2"
    get_history_context(query)
    assert len(calls) == 2 and len(calls[1]) == 2
    assert set(EntryEmbedding.objects.values_list("model", flat=True)) == {"fake-2"}


def test_recency_breaks_ties():
    old = entry("#a", days=0)
    recent = entry("#a", days=50)
    query = entry("#a", days=60)
    assert ids(get_history_context(query)) == [recent.id, old.id]


def test_my_shared_name_breaks_ties():
    named = entry("#a", days=0)
    other = entry("#a", days=0, hours=1)
    query = entry("#a", days=1)
    name(named, "지어낸 이름")
    name(query, "지어낸 이름")
    items = get_history_context(query)
    assert ids(items) == [named.id, other.id]
    assert items[0].shared_naming and not items[1].shared_naming


def test_rejected_ai_name_is_not_shared():
    a = entry("#a", days=0)
    query = entry("#a", days=1)
    naming = Naming.objects.create(label="지어낸 이름")
    NamingLink.objects.create(entry=a, naming=naming, author="ai", status="rejected")
    NamingLink.objects.create(entry=query, naming=naming)
    assert get_history_context(query)[0].shared_naming is False


def test_meaning_outweighs_recency():
    close_but_old = entry("#a", days=0)
    recent_unrelated = entry("#z", days=119)
    query = entry("#a", days=120)
    items = get_history_context(query, min_similarity=0)
    assert ids(items)[0] == close_but_old.id
    assert recent_unrelated.id in ids(items)


# ---- API ----


def get(client, path):
    return client.get(f"/api{path}", HTTP_AUTHORIZATION=f"Bearer {TOKEN}")


def test_context_api_fields(client):
    past = entry("#a")
    query = entry("#a", days=1)
    res = get(client, f"/entries/{query.id}/context")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    # 점수는 기록끼리의 거리일 뿐. 평가성 필드가 끼어들면 실패한다 (P1)
    assert set(body[0]) == {"entry", "similarity", "recency", "shared_naming", "score"}
    assert body[0]["entry"]["id"] == str(past.id)


def test_context_api_503_without_key(client, settings, monkeypatch):
    monkeypatch.setattr(embeddings, "embed_texts", embeddings.__dict__["_voyage"])
    settings.VOYAGE_API_KEY = ""
    entry("#a")
    query = entry("#a", days=1)
    res = get(client, f"/entries/{query.id}/context")
    assert res.status_code == 503
    assert "VOYAGE_API_KEY" in res.json()["detail"]


def test_context_api_404_and_auth(client):
    assert get(client, f"/entries/{uuid.uuid4()}/context").status_code == 404
    assert client.get(f"/api/entries/{uuid.uuid4()}/context").status_code == 401


def test_writing_never_waits_for_embeddings(client, monkeypatch):
    def broken(texts):
        raise embeddings.EmbeddingUnavailable("down")

    monkeypatch.setattr(embeddings, "embed_texts", broken)
    payload = {"id": str(uuid.uuid4()), "content": "지어낸 문장", "source": "web", "written_at": DAY0.isoformat()}
    res = client.post("/api/entries", payload, content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {TOKEN}")
    assert res.status_code == 201
    assert not EntryEmbedding.objects.exists()


def test_embed_command_prints_count_not_content():
    entry("#a")
    out = io.StringIO()
    call_command("embed_entries", stdout=out)
    assert "1개" in out.getvalue()
    assert "지어낸" not in out.getvalue()


# ---- Voyage 호출 (네트워크 없이) ----


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_voyage_request_and_order(settings, monkeypatch):
    settings.VOYAGE_API_KEY = "test-key"
    seen = {}

    def fake_urlopen(request, timeout):
        seen["body"] = json.loads(request.data)
        seen["auth"] = request.get_header("Authorization")
        data = [{"index": 1, "embedding": [0.0] * EMBEDDING_DIMENSIONS}, {"index": 0, "embedding": [1.0] * EMBEDDING_DIMENSIONS}]
        return FakeResponse(json.dumps({"data": data}).encode())

    monkeypatch.setattr(embeddings.urllib.request, "urlopen", fake_urlopen)
    vectors = embeddings._voyage(["가", "나"])
    assert vectors[0][0] == 1.0 and vectors[1][0] == 0.0
    assert seen["body"] == {
        "input": ["가", "나"],
        "model": "fake-1",
        "input_type": "document",
        "output_dimension": EMBEDDING_DIMENSIONS,
    }
    assert seen["auth"] == "Bearer test-key"


def test_voyage_wrong_dimensions(settings, monkeypatch):
    settings.VOYAGE_API_KEY = "test-key"
    monkeypatch.setattr(
        embeddings.urllib.request,
        "urlopen",
        lambda r, timeout: FakeResponse(json.dumps({"data": [{"index": 0, "embedding": [1.0]}]}).encode()),
    )
    with pytest.raises(embeddings.EmbeddingUnavailable):
        embeddings._voyage(["가"])


def test_voyage_http_error_hides_body(settings, monkeypatch):
    settings.VOYAGE_API_KEY = "test-key"

    def boom(request, timeout):
        raise urllib.error.HTTPError(embeddings.VOYAGE_URL, 400, "bad", {}, io.BytesIO(b"echo: secret thought"))

    monkeypatch.setattr(embeddings.urllib.request, "urlopen", boom)
    with pytest.raises(embeddings.EmbeddingUnavailable) as info:
        embeddings._voyage(["가"])
    assert "400" in str(info.value) and "secret" not in str(info.value)
