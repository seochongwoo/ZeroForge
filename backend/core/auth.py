import secrets

from django.conf import settings
from ninja.security import HttpBearer


class TokenAuth(HttpBearer):
    """단일 사용자 토큰. 혼자 쓰는 동안은 이걸로 충분하다 (ADR 0001)."""

    def authenticate(self, request, token):
        expected = settings.ZF_TOKEN
        # 토큰이 설정되지 않았으면 모든 요청을 거부한다
        if expected and secrets.compare_digest(token, expected):
            return token
        return None
