"""이어 쓰기 테스트. 새 기록이 옛 기록에 이어진다 (EntryLink).

테스트 데이터는 지어낸 문장만 쓴다 (P8).
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from core.models import Entry, EntryLink

TOKEN = "test-token"
KST = timezone(timedelta(hours=9))

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def zf_token(settings):
    settings.ZF_TOKEN = TOKEN


def post(client, body):
    return client.post("/api/entries", body, content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {TOKEN}")


def get(client, path):
    return client.get(f"/api{path}", HTTP_AUTHORIZATION=f"Bearer {TOKEN}")


def payload(content, day=1, continues=None):
    body = {
        "id": str(uuid.uuid4()),
        "content": content,
        "source": "web",
        "written_at": datetime(2026, 11, day, 12, 0, tzinfo=KST).isoformat(),
    }
    if continues is not None:
        body["continues"] = continues
    return body


def test_continue_links_new_entry_to_old(client):
    old = post(client, payload("지어낸 문장: 비 오는 날 우산을 두고 나왔다", day=1)).json()
    res = post(client, payload("지어낸 문장: 그날 젖은 게 싫지만은 않았다", day=5, continues=[old["id"]]))
    assert res.status_code == 201
    new = res.json()
    assert [r["id"] for r in new["continues"]] == [old["id"]]
    assert new["continues"][0]["content"].startswith("지어낸 문장: 비 오는")
    assert new["continued_by"] == []

    listed = {e["id"]: e for e in get(client, "/entries").json()["items"]}
    assert [r["id"] for r in listed[old["id"]]["continued_by"]] == [new["id"]]
    assert listed[old["id"]]["continues"] == []


def test_without_continues_is_unchanged(client):
    res = post(client, payload("지어낸 문장: 혼자 걷는 저녁"))
    assert res.status_code == 201
    assert res.json()["continues"] == [] and res.json()["continued_by"] == []
    assert not EntryLink.objects.exists()


def test_resend_does_not_duplicate_links(client):
    old = post(client, payload("지어낸 문장: 첫 생각", day=1)).json()
    body = payload("지어낸 문장: 이어진 생각", day=2, continues=[old["id"]])
    assert post(client, body).status_code == 201
    assert post(client, body).status_code == 200  # outbox 재전송
    assert EntryLink.objects.count() == 1


def test_unknown_and_self_ids_are_skipped_not_rejected(client):
    body = payload("지어낸 문장: 아직 서버에 없는 기록에 이어서", continues=[str(uuid.uuid4())])
    body["continues"].append(body["id"])
    res = post(client, body)
    assert res.status_code == 201
    assert res.json()["continues"] == []
    assert not EntryLink.objects.exists()


def test_continue_from_several(client):
    a = post(client, payload("지어낸 문장: 하나", day=1)).json()
    b = post(client, payload("지어낸 문장: 둘", day=2)).json()
    res = post(client, payload("지어낸 문장: 둘 다 생각났다", day=3, continues=[b["id"], a["id"]]))
    # 옛 기록은 쓴 순서대로
    assert [r["id"] for r in res.json()["continues"]] == [a["id"], b["id"]]


def test_too_many_continues_is_rejected(client):
    ids = [post(client, payload(f"지어낸 문장: {i}", day=1)).json()["id"] for i in range(6)]
    assert post(client, payload("지어낸 문장: 너무 많이", day=2, continues=ids)).status_code == 422


def test_only_accepted_links_are_shown(client):
    a = Entry.objects.create(id=uuid.uuid4(), content="지어낸 문장: 옛", source="web", written_at=datetime(2026, 11, 1, tzinfo=KST))
    b = Entry.objects.create(id=uuid.uuid4(), content="지어낸 문장: 새", source="web", written_at=datetime(2026, 11, 2, tzinfo=KST))
    EntryLink.objects.create(from_entry=b, to_entry=a, author="ai", status="proposed")
    listed = {e["id"]: e for e in get(client, "/entries").json()["items"]}
    assert listed[str(b.id)]["continues"] == [] and listed[str(a.id)]["continued_by"] == []


def test_entry_link_has_no_score_fields():
    names = {f.name for f in EntryLink._meta.get_fields()}
    assert names == {"id", "from_entry", "to_entry", "author", "status", "created_at"}
