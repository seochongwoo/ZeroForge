# ZeroForge: Django API + Expo 웹 빌드를 한 서비스로 (ADR 0003)
# Railway / Render / Fly.io 모두 이 Dockerfile 하나로 배포한다.

# 1) Expo 웹 정적 빌드
FROM node:24-slim AS web
WORKDIR /app
COPY app/package.json app/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY app/ ./
RUN npx expo export --platform web --output-dir /web

# 2) Django
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ZF_WEB_BUILD_DIR=/srv/web
WORKDIR /srv/backend

COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/ ./
COPY --from=web /web /srv/web

# collectstatic은 비밀값 없이도 돌아가야 한다 (빌드 시점용 더미 값)
RUN DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput

RUN useradd --create-home zeroforge
USER zeroforge

ENV PORT=8000
EXPOSE 8000
# 시작할 때 마이그레이션을 적용하고 gunicorn을 띄운다
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi --bind 0.0.0.0:${PORT} --workers 2 --access-logfile -"]
