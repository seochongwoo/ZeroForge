"""ZeroForge 백엔드 설정.

모든 설정값은 환경 변수에서 읽는다. 로컬에서는 저장소 루트의 .env를 읽는다.
"""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

load_dotenv(REPO_ROOT / ".env")


def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise ImproperlyConfigured(f"환경 변수 {name}가 필요합니다 (.env.example 참고)")
    return value


def env_list(name: str, default: str = "") -> list[str]:
    return [v.strip() for v in env(name, default).split(",") if v.strip()]


SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

# Railway: 공개 도메인을 RAILWAY_PUBLIC_DOMAIN으로 넣어 주고,
# 헬스체크는 healthcheck.railway.app 호스트로 들어온다 (허용하지 않으면 400 → 배포 실패)
RAILWAY_PUBLIC_DOMAIN = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
ON_RAILWAY = bool(RAILWAY_PUBLIC_DOMAIN or os.environ.get("RAILWAY_PRIVATE_DOMAIN"))
if ON_RAILWAY:
    ALLOWED_HOSTS += ["healthcheck.railway.app"]
if RAILWAY_PUBLIC_DOMAIN:
    ALLOWED_HOSTS += [RAILWAY_PUBLIC_DOMAIN]

# 단일 사용자 토큰 (core/auth.py)
ZF_TOKEN = env("ZF_TOKEN", "")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # 정적 파일 + Expo 웹 빌드를 Django가 직접 서빙한다 (ADR 0003)
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# 호스팅은 보통 DATABASE_URL 하나를 준다. 없으면 로컬용 POSTGRES_* 값을 쓴다.
if os.environ.get("DATABASE_URL"):
    DATABASES = {
        "default": dj_database_url.parse(
            os.environ["DATABASE_URL"], conn_max_age=600, conn_health_checks=True
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": env("POSTGRES_HOST", "localhost"),
            "PORT": env("POSTGRES_PORT", "5432"),
            "NAME": env("POSTGRES_DB", "zeroforge"),
            "USER": env("POSTGRES_USER", "zeroforge"),
            "PASSWORD": env("POSTGRES_PASSWORD", ""),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Expo 웹 빌드(npx expo export --platform web 결과). 있으면 같은 주소에서 서빙한다.
# 루트의 파일(/_expo/static/..., /favicon.ico)은 WhiteNoise가, 나머지 화면 경로는 core.views.web_app이 맡는다.
WEB_BUILD_DIR = Path(env("ZF_WEB_BUILD_DIR", str(BASE_DIR / "web")))
WHITENOISE_ROOT = WEB_BUILD_DIR if WEB_BUILD_DIR.is_dir() else None
# Expo는 번들 파일명에 해시를 붙이므로 오래 캐시해도 된다
WHITENOISE_IMMUTABLE_FILE_TEST = r"^.+[-.][0-9a-f]{8,}\.(js|css|map|ttf|png|jpg|svg)$"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# 웹을 따로 띄울 때(개발 중 Expo dev server)만 필요하다. 배포에서는 같은 주소라 CORS가 필요 없다.
CORS_ALLOWED_ORIGINS = env_list("DJANGO_CORS_ALLOWED_ORIGINS", "http://localhost:8081")
# 관리 화면 로그인용 (예: https://zeroforge.up.railway.app)
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "")
if RAILWAY_PUBLIC_DOMAIN:
    CSRF_TRUSTED_ORIGINS += [f"https://{RAILWAY_PUBLIC_DOMAIN}"]

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env("DJANGO_SECURE_SSL_REDIRECT", "true").lower() == "true"
    # 호스팅의 헬스체크는 보통 내부 http로 들어온다
    SECURE_REDIRECT_EXEMPT = [r"^healthz$"]
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
