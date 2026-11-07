"""Railway 환경 변수에 맞춰 허용 호스트가 자동으로 잡히는지 (docs/deploy.md).

설정은 import 시점에 정해지므로 새 프로세스에서 확인한다.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]

PROBE = (
    "import json, django; django.setup(); from django.conf import settings as s; "
    "print(json.dumps({'hosts': s.ALLOWED_HOSTS, 'csrf': s.CSRF_TRUSTED_ORIGINS}))"
)


def load_settings(**extra_env):
    env = {k: v for k, v in os.environ.items() if not k.startswith("RAILWAY_")}
    env.update(
        DJANGO_SETTINGS_MODULE="config.settings",
        DJANGO_SECRET_KEY="test-only",
        DJANGO_ALLOWED_HOSTS="localhost",
        DJANGO_CSRF_TRUSTED_ORIGINS="",
        **extra_env,
    )
    out = subprocess.run(
        [sys.executable, "-c", PROBE], cwd=BACKEND, env=env, capture_output=True, text=True, check=True
    )
    return json.loads(out.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("var", ["RAILWAY_PUBLIC_DOMAIN", "RAILWAY_PRIVATE_DOMAIN"])
def test_railway_allows_healthcheck_host(var):
    s = load_settings(**{var: "zeroforge-production.up.railway.app"})
    assert "healthcheck.railway.app" in s["hosts"]


def test_railway_public_domain_is_allowed_and_csrf_trusted():
    s = load_settings(RAILWAY_PUBLIC_DOMAIN="zeroforge-production.up.railway.app")
    assert "zeroforge-production.up.railway.app" in s["hosts"]
    assert "https://zeroforge-production.up.railway.app" in s["csrf"]


def test_outside_railway_nothing_is_added():
    s = load_settings()
    assert s["hosts"] == ["localhost"]
    assert s["csrf"] == []
