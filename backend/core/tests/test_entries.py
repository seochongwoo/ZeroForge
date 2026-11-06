"""Entry API 테스트.

테스트 데이터는 지어낸 문장만 쓴다 (P8).
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from core.models import Entry

TOKEN = "test-token"
KST = timezone(timedelta(hours=9))


@pytest.fixture(autouse=True)
def zf_token(settings):
    settings.ZF_TOKEN = TOKEN


@pytest.fixture
def auth():
    return {"HTTP_AUTHORIZATION": f"Bearer {TOKEN}"}


def make_payload(content="지어낸 문장: 오늘은 창밖의 비를 오래 봤다", **overrides):
    payload = {
        "id": str(uuid.uuid4()),
        "content": content,
        "source": "web",
        "written_at": datetime(2026, 11, 6, 14, 0, tzinfo=KST).isoformat(),
    }
    payload.update(overrides)
    return payload


def post(client, payload, headers):
    return client.post("/api/entries", payload, content_type="application/json", **headers)


@pytest.mark.django_db
def test_save_then_list(client, auth):
    payload = make_payload()
    res = post(client, payload, auth)
    assert res.status_code == 201
    assert res.json()["id"] == payload["id"]

    res = client.get("/api/entries", **auth)
    assert res.status_code == 200
    body = res.json()
    assert [e["id"] for e in body["items"]] == [payload["id"]]
    assert body["items"][0]["content"] == payload["content"]
    assert body["next_cursor"] is None


@pytest.mark.django_db
def test_same_id_twice_is_stored_once(client, auth):
    payload = make_payload()
    assert post(client, payload, auth).status_code == 201

    # 오프라인 재시도: 같은 id로 다시 보내도 하나만 저장되고, 기존 기록이 돌아온다
    retry = dict(payload, content="지어낸 문장: 다른 내용으로 덮어쓰려는 시도")
    res = post(client, retry, auth)
    assert res.status_code == 200
    assert res.json()["content"] == payload["content"]
    assert Entry.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "headers",
    [{}, {"HTTP_AUTHORIZATION": "Bearer wrong-token"}, {"HTTP_AUTHORIZATION": TOKEN}],
    ids=["no-token", "wrong-token", "no-bearer-prefix"],
)
def test_rejects_without_valid_token(client, headers):
    assert post(client, make_payload(), headers).status_code == 401
    assert client.get("/api/entries", **headers).status_code == 401
    assert Entry.objects.count() == 0


@pytest.mark.django_db
def test_rejects_everything_when_token_not_configured(client, settings):
    settings.ZF_TOKEN = ""
    assert client.get("/api/entries", HTTP_AUTHORIZATION="Bearer ").status_code == 401
    assert client.get("/api/entries", HTTP_AUTHORIZATION="Bearer anything").status_code == 401


@pytest.mark.django_db
def test_list_is_newest_first_by_written_at_with_cursor(client, auth):
    base = datetime(2026, 11, 1, 9, 0, tzinfo=KST)
    # 일부러 쓴 순서와 다르게 도착시킨다 (늦게 동기화된 기록)
    ids_by_age = []
    for i in [2, 0, 4, 1, 3]:
        payload = make_payload(
            content=f"지어낸 문장 {i}", written_at=(base + timedelta(hours=i)).isoformat()
        )
        post(client, payload, auth)
        ids_by_age.append((i, payload["id"]))
    expected = [pid for _, pid in sorted(ids_by_age, reverse=True)]

    seen, cursor = [], None
    while True:
        url = "/api/entries?limit=2" + (f"&cursor={cursor}" if cursor else "")
        body = client.get(url, **auth).json()
        seen += [e["id"] for e in body["items"]]
        cursor = body["next_cursor"]
        if not cursor:
            break
    assert seen == expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "overrides",
    [
        {"content": "   "},
        {"source": "desktop"},
        {"written_at": "2026-11-06T14:00:00"},  # 시간대 없음
        {"id": "not-a-uuid"},
    ],
    ids=["blank", "bad-source", "naive-time", "bad-id"],
)
def test_rejects_invalid_payload(client, auth, overrides):
    res = post(client, make_payload(**overrides), auth)
    assert res.status_code == 422
    assert Entry.objects.count() == 0


@pytest.mark.django_db
def test_entry_is_immutable_no_update_or_delete_api(client, auth):
    payload = make_payload()
    post(client, payload, auth)
    for method in ("put", "patch", "delete"):
        res = getattr(client, method)(f"/api/entries/{payload['id']}", **auth)
        assert res.status_code in (404, 405)
    assert Entry.objects.count() == 1


def test_entry_has_no_score_or_status_fields():
    # P1, P4: 점수·상태 필드가 생기면 실패한다
    fields = {f.name for f in Entry._meta.get_fields()}
    assert fields == {"id", "content", "source", "written_at", "created_at"}
