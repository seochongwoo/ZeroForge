# ZeroForge

언제든 접속해, 아주 짧게라도 자기 언어로 사유하고 스스로 이름 붙이는 공간.

AI는 판정자가 아니라 서기(scribe)다.

사업이 아니라 지금의 나에게 도움이 되는 개인 도구로 만든다. 기능은 설계가 아니라 실제 사용에서 나온다.

- [PLAN.md](PLAN.md) — 재시작 플랜
- [PRINCIPLES.md](PRINCIPLES.md) — 모든 PR이 확인하는 원칙
- [docs/decisions/](docs/decisions/) — 결정 기록(ADR)
- [docs/friction.md](docs/friction.md) — 쓰면서 느낀 마찰 = 백로그

## 개발 환경

필요한 것: Node.js LTS, Python 3.12+, [uv](https://docs.astral.sh/uv/), PostgreSQL + pgvector (또는 Docker), 휴대폰의 Expo Go.

```bash
cp .env.example .env          # 값 채우기 (ZF_TOKEN, POSTGRES_PASSWORD 등)
pip install pre-commit && pre-commit install   # gitleaks로 비밀값 커밋 방지
```

### DB

- Docker: `docker compose up -d`
- Windows에 설치된 PostgreSQL: `powershell -ExecutionPolicy Bypass -File backend\scripts\setup_local_db.ps1` (postgres 비밀번호를 물어본다)

### 백엔드

```bash
cd backend
uv venv && uv pip install -r requirements.txt
.venv/Scripts/python manage.py migrate      # macOS/Linux: .venv/bin/python
.venv/Scripts/python manage.py runserver 0.0.0.0:8000
.venv/Scripts/pytest
```

### 앱

```bash
cd app
npm install
npx expo start          # w: 웹, 휴대폰은 Expo Go로 QR 스캔
```

처음 열면 설정 화면에서 서버 주소와 `ZF_TOKEN`을 한 번 입력한다.
휴대폰에서는 `localhost` 대신 노트북의 LAN 주소(예: `http://192.168.0.10:8000`)를 쓰고, 그 주소를 `.env`의 `DJANGO_ALLOWED_HOSTS`에 추가한다.

실제 기록, DB 덤프, 실제 내용이 담긴 fixture는 커밋하지 않는다 (P8).

## 라이선스

[MIT](LICENSE)
