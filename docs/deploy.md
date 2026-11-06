# 배포

구조는 [ADR 0003](decisions/0003-single-service-deploy.md): 저장소 루트의 `Dockerfile` 하나로 API와 웹을 함께 올린다.

## 1. 공통으로 필요한 것

**PostgreSQL** (pgvector 확장을 쓸 수 있어야 한다 — Step 8에서 필요)

**환경 변수**

| 이름 | 값 |
|------|----|
| `DATABASE_URL` | 호스팅이 주는 Postgres 접속 주소 |
| `DJANGO_SECRET_KEY` | 새로 만든 긴 무작위 문자열 (로컬 `.env`와 다른 값) |
| `ZF_TOKEN` | 새로 만든 토큰 (로컬과 다른 값). 앱 설정 화면에 넣는다 |
| `DJANGO_ALLOWED_HOSTS` | 배포 도메인 (예: `zeroforge.up.railway.app`) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://` + 배포 도메인 (관리 화면 로그인용) |

무작위 값 만들기:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

`PORT`는 호스팅이 넣어 준다. 헬스체크 경로는 `/healthz`.

## 2. 처음 한 번

배포가 뜬 뒤 DB에 pgvector를 켜 둔다 (Step 8 대비, 지금은 없어도 동작한다):

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

관리 화면 계정 (호스팅의 셸/콘솔에서):

```bash
python manage.py createsuperuser
```

## 3. 호스팅별 메모

### Railway

1. GitHub 저장소로 새 프로젝트 → 루트의 `Dockerfile`을 자동으로 쓴다
2. 같은 프로젝트에 PostgreSQL 추가. pgvector가 필요하면 pgvector 템플릿(이미지 `pgvector/pgvector:pg16`)으로 만든다
3. 앱 서비스 변수에 `DATABASE_URL`을 Postgres 서비스의 값으로 연결하고, 위 표의 나머지 값을 넣는다
4. Settings → Networking에서 도메인 생성, Healthcheck Path `/healthz`

### Render + Neon

1. Neon에서 DB 생성 → 접속 주소를 `DATABASE_URL`로
2. Render에서 Web Service → Docker, 저장소 연결, Health Check Path `/healthz`
3. 무료 플랜은 한동안 쓰지 않으면 잠들어 첫 접속이 느리다. 쓰기는 outbox 덕분에 막히지 않는다

### Fly.io

1. `fly launch` (Dockerfile 감지, 리전 `nrt` 또는 가까운 곳)
2. Postgres는 Fly Postgres 또는 외부(Neon 등) → `fly secrets set DATABASE_URL=...` 및 나머지 값
3. `fly.toml`의 헬스체크 경로 `/healthz`

## 4. 확인 (develop_plan Step 5 완료 기준)

- [ ] `https://<도메인>/healthz` → `{"ok": true}`
- [ ] 노트북 브라우저에서 열기 → 설정에 서버 주소가 자동으로 채워짐 → 토큰만 넣기
- [ ] 휴대폰 브라우저에서 열기 → 홈 화면에 추가
- [ ] 개발 서버를 끈 상태에서, 한쪽에서 쓴 기록이 다른 쪽 목록에 보임
- [ ] 비행기 모드로 쓰고 → 연결 후 한 번만 올라감
