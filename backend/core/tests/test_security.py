import pytest


@pytest.mark.django_db
def test_http_is_redirected_to_https_when_ssl_redirect_on(client, settings):
    # 운영 설정(DEBUG=False)과 같은 상태
    settings.SECURE_SSL_REDIRECT = True
    res = client.get("/api/entries")
    assert res.status_code == 301
    assert res["Location"].startswith("https://")


@pytest.mark.django_db
def test_https_request_reaches_api_when_ssl_redirect_on(client, settings):
    settings.SECURE_SSL_REDIRECT = True
    # 토큰이 없으니 API까지 도달해 401이 나와야 한다
    assert client.get("/api/entries", secure=True).status_code == 401
