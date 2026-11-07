"""배포 형태 테스트: 헬스체크, 같은 주소에서 웹 앱 서빙 (ADR 0003)."""

import pytest


@pytest.mark.django_db
def test_healthz_ok_without_token(client):
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"ok": True}


@pytest.mark.django_db
def test_healthz_not_redirected_even_when_ssl_redirect_on(client, settings):
    # 호스팅 헬스체크는 내부 http로 들어오므로 https 리다이렉트에서 빠져야 한다
    settings.SECURE_SSL_REDIRECT = True
    settings.SECURE_REDIRECT_EXEMPT = [r"^healthz$"]
    assert client.get("/healthz").status_code == 200


@pytest.fixture
def web_build(tmp_path, settings):
    (tmp_path / "index.html").write_text("<!doctype html><title>ZeroForge</title>", encoding="utf-8")
    settings.WEB_BUILD_DIR = tmp_path
    return tmp_path


@pytest.mark.parametrize("path", ["/", "/settings", "/some/deep/route"])
def test_screen_paths_serve_index_html(client, web_build, path):
    res = client.get(path)
    assert res.status_code == 200
    assert res["Content-Type"].startswith("text/html")
    assert b"ZeroForge" in b"".join(res.streaming_content)


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/api/entries", "/api", "/api/unknown"])
def test_api_paths_are_not_swallowed_by_web_app(client, web_build, path):
    res = client.get(path)
    assert res.status_code in (301, 401, 404)  # /api → /api/ 슬래시 리다이렉트 포함
    # 웹 앱(index.html)이 아니라 API/Django가 응답해야 한다
    assert b"<title>ZeroForge</title>" not in res.content


def test_admin_is_not_swallowed_by_web_app(client, web_build):
    res = client.get("/admin/")
    assert res.status_code == 302  # 로그인 화면으로
    assert "/admin/login/" in res["Location"]


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/", "/settings", "/healthz"])
def test_head_is_allowed(client, web_build, path):
    # 웹의 NetInfo는 HEAD /로 연결을 확인한다. 405면 계속 오프라인으로 판단한다.
    assert client.head(path).status_code == 200


@pytest.mark.parametrize(
    "path", ["/_expo/static/js/web/entry-deadbeefdeadbeef.js", "/missing.png", "/a/b/old.js"]
)
def test_missing_asset_is_404_not_index_html(client, web_build, path):
    # 없는 파일에 index.html을 주면 JS 자리에 HTML이 와서 화면이 하얘진다
    res = client.get(path)
    assert res.status_code == 404
    assert b"<title>ZeroForge</title>" not in res.content


def test_missing_web_build_gives_clear_404(client, tmp_path, settings):
    settings.WEB_BUILD_DIR = tmp_path / "nope"
    res = client.get("/")
    assert res.status_code == 404
    assert "expo export" in res.content.decode()
