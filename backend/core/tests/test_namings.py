"""이름 붙이기 API 테스트 (Step 7).

테스트 데이터는 지어낸 문장과 지어낸 이름만 쓴다 (P8).
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from core.models import Naming, NamingLink, NamingVersion

TOKEN = "test-token"
KST = timezone(timedelta(hours=9))

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def zf_token(settings):
    settings.ZF_TOKEN = TOKEN


@pytest.fixture
def api(client):
    headers = {"HTTP_AUTHORIZATION": f"Bearer {TOKEN}"}

    class Api:
        def get(self, path):
            return client.get(f"/api{path}", **headers)

        def post(self, path, body):
            return client.post(f"/api{path}", body, content_type="application/json", **headers)

        def delete(self, path):
            return client.delete(f"/api{path}", **headers)

    return Api()


def new_entry(api, content="지어낸 문장: 버스 창에 김이 서렸다", hour=14):
    payload = {
        "id": str(uuid.uuid4()),
        "content": content,
        "source": "web",
        "written_at": datetime(2026, 11, 6, hour, 0, tzinfo=KST).isoformat(),
    }
    assert api.post("/entries", payload).status_code == 201
    return payload["id"]


def labels(entry_json):
    return [n["label"] for n in entry_json["namings"]]


def test_new_entry_has_no_names(api):
    entry_id = new_entry(api)
    item = api.get("/entries").json()["items"][0]
    assert item["id"] == entry_id
    assert item["namings"] == []


def test_attach_creates_name_with_first_version(api):
    entry_id = new_entry(api)
    res = api.post(f"/entries/{entry_id}/namings", {"label": "  안개  낀  아침 "})
    assert res.status_code == 200
    assert labels(res.json()) == ["안개 낀 아침"]  # 앞뒤·중복 공백 정리

    naming = Naming.objects.get()
    assert [v.label for v in naming.versions.all()] == ["안개 낀 아침"]
    link = NamingLink.objects.get()
    assert (link.author, link.status) == ("user", "accepted")
    # 목록에도 보인다
    assert labels(api.get("/entries").json()["items"][0]) == ["안개 낀 아침"]


def test_attach_is_idempotent_and_reuses_existing_name(api):
    a, b = new_entry(api), new_entry(api, "지어낸 문장: 우산을 두고 왔다")
    api.post(f"/entries/{a}/namings", {"label": "기다림"})
    api.post(f"/entries/{a}/namings", {"label": "기다림"})
    api.post(f"/entries/{b}/namings", {"label": "기다림"})  # 이미 있는 이름에 붙는다
    assert Naming.objects.count() == 1
    assert NamingLink.objects.count() == 2


def test_name_match_ignores_case(api):
    a, b = new_entry(api), new_entry(api)
    api.post(f"/entries/{a}/namings", {"label": "Drift"})
    api.post(f"/entries/{b}/namings", {"label": "drift"})
    assert Naming.objects.count() == 1


@pytest.mark.parametrize("label", ["", "   ", "가" * 81])
def test_blank_or_too_long_name_is_rejected(api, label):
    entry_id = new_entry(api)
    assert api.post(f"/entries/{entry_id}/namings", {"label": label}).status_code == 422
    assert Naming.objects.count() == 0


def test_attach_to_missing_entry_is_404(api):
    assert api.post(f"/entries/{uuid.uuid4()}/namings", {"label": "기다림"}).status_code == 404
    assert Naming.objects.count() == 0


def test_rename_keeps_history(api):
    entry_id = new_entry(api)
    naming_id = api.post(f"/entries/{entry_id}/namings", {"label": "방황"}).json()["namings"][0]["id"]

    res = api.post(f"/namings/{naming_id}/versions", {"label": "유예"})
    assert res.status_code == 200
    res = api.post(f"/namings/{naming_id}/versions", {"label": "기다림"})
    body = res.json()
    assert body["label"] == "기다림"
    assert [v["label"] for v in body["versions"]] == ["방황", "유예", "기다림"]
    # 기록에는 지금 이름이 보인다
    assert labels(api.get("/entries").json()["items"][0]) == ["기다림"]


def test_rename_to_same_label_adds_nothing(api):
    entry_id = new_entry(api)
    naming_id = api.post(f"/entries/{entry_id}/namings", {"label": "기다림"}).json()["namings"][0]["id"]
    api.post(f"/namings/{naming_id}/versions", {"label": " 기다림 "})
    assert NamingVersion.objects.count() == 1


def test_rename_to_existing_other_name_conflicts(api):
    a, b = new_entry(api), new_entry(api)
    api.post(f"/entries/{a}/namings", {"label": "멈춤"})
    other = api.post(f"/entries/{b}/namings", {"label": "기다림"}).json()["namings"][0]["id"]
    res = api.post(f"/namings/{other}/versions", {"label": "멈춤"})
    assert res.status_code == 409
    assert Naming.objects.get(id=other).label == "기다림"


def test_naming_detail_lists_its_entries_newest_first(api):
    older = new_entry(api, "지어낸 문장: 아침", hour=8)
    newer = new_entry(api, "지어낸 문장: 저녁", hour=20)
    other = new_entry(api, "지어낸 문장: 상관없는 기록")
    naming_id = api.post(f"/entries/{older}/namings", {"label": "기다림"}).json()["namings"][0]["id"]
    api.post(f"/entries/{newer}/namings", {"label": "기다림"})
    api.post(f"/entries/{other}/namings", {"label": "다른 이름"})

    body = api.get(f"/namings/{naming_id}").json()
    assert body["label"] == "기다림"
    assert [e["id"] for e in body["entries"]] == [newer, older]
    assert [v["label"] for v in body["versions"]] == ["기다림"]


def test_list_namings_has_no_counts(api):
    entry_id = new_entry(api)
    api.post(f"/entries/{entry_id}/namings", {"label": "기다림"})
    body = api.get("/namings").json()
    assert [n["label"] for n in body] == ["기다림"]
    # P4: 이름마다 몇 개인지 같은 숫자는 내려보내지 않는다
    assert set(body[0]) == {"id", "label", "created_at", "versions"}


def test_detach_keeps_name_and_history(api):
    entry_id = new_entry(api)
    naming_id = api.post(f"/entries/{entry_id}/namings", {"label": "방황"}).json()["namings"][0]["id"]
    api.post(f"/namings/{naming_id}/versions", {"label": "기다림"})

    res = api.delete(f"/entries/{entry_id}/namings/{naming_id}")
    assert res.status_code == 200
    assert res.json()["namings"] == []
    assert Naming.objects.filter(id=naming_id).exists()
    assert NamingVersion.objects.filter(naming_id=naming_id).count() == 2


def test_rejected_ai_suggestion_is_hidden_but_kept(api):
    # Step 8 대비: AI 제안을 거절한 연결은 화면에는 안 보이지만 데이터로 남는다
    entry_id = new_entry(api)
    naming = Naming.objects.create(label="제안된 이름")
    NamingLink.objects.create(entry_id=entry_id, naming=naming, author="ai", status="rejected")
    assert api.get("/entries").json()["items"][0]["namings"] == []
    # AI 연결은 "떼기"로 지워지지 않는다
    api.delete(f"/entries/{entry_id}/namings/{naming.id}")
    assert NamingLink.objects.filter(entry_id=entry_id, status="rejected").exists()
    # 내가 직접 붙이면 내 연결이 된다
    res = api.post(f"/entries/{entry_id}/namings", {"label": "제안된 이름"})
    assert labels(res.json()) == ["제안된 이름"]
    link = NamingLink.objects.get(entry_id=entry_id)
    assert (link.author, link.status) == ("user", "accepted")


def test_naming_endpoints_need_token(client):
    assert client.get("/api/namings").status_code == 401
    assert client.post(f"/api/entries/{uuid.uuid4()}/namings", {"label": "x"}, content_type="application/json").status_code == 401


def test_naming_models_have_no_score_fields():
    # P1, P4: 이름에도 점수·완료 같은 칸이 생기면 실패한다
    def own(model):
        return {f.name for f in model._meta.get_fields() if not f.auto_created}

    assert own(Naming) == {"id", "label", "created_at"}
    assert own(NamingVersion) == {"id", "naming", "label", "created_at"}
    # status는 연결의 출처 상태(제안/수락/거절)일 뿐 평가가 아니다 (PLAN.md §5 Link)
    assert own(NamingLink) == {"entry", "naming", "author", "status", "created_at"}
