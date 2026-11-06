import pytest


@pytest.fixture(autouse=True)
def _http_test_client(settings):
    """테스트 결과가 DJANGO_DEBUG 값(.env 유무)에 따라 달라지지 않게 한다.

    운영 설정(DEBUG=False)에서는 SECURE_SSL_REDIRECT가 켜져 테스트 클라이언트의
    http:// 요청이 전부 301이 된다. API 동작 테스트에서는 이를 끄고,
    리다이렉트 자체는 core/tests/test_security.py에서 따로 확인한다.
    """
    settings.SECURE_SSL_REDIRECT = False
