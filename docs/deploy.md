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
| `DJANGO_ALLOWED_HOSTS` | 배포 도메인 (예: `zeroforge.up.railway.app`). **Railway는 자동이라 필요 없음** |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://` + 배포 도메인 (관리 화면 로그인용). **Railway는 자동이라 필요 없음** |

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

Railway 문서 기준(2026-11 확인). 메뉴 이름은 바뀔 수 있다.

1. **DB 먼저**: 새 프로젝트에 **pgvector 템플릿**으로 Postgres를 만든다 (기본 Postgres 템플릿은 확장을 추가하지 않는다고 문서에 적혀 있다). 템플릿: https://railway.com/deploy/3jJFCA
2. **앱**: 같은 프로젝트에서 GitHub 저장소 `ZeroForge` 연결, 브랜치 `main`. 루트에 `Dockerfile`이 있으면 Railway가 그걸로 빌드한다
3. **변수** (앱 서비스 → Variables)
   - `DATABASE_URL` = `${{<Postgres 서비스 이름>.DATABASE_URL}}` (참조 변수. 직접 복사하지 말고 참조로 연결)
   - `DJANGO_SECRET_KEY`, `ZF_TOKEN` = 새로 만든 무작위 값
   - `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`는 넣지 않아도 된다. Railway가 주는 `RAILWAY_PUBLIC_DOMAIN`과 헬스체크 호스트(`healthcheck.railway.app`)를 설정이 자동으로 허용한다
4. **도메인**: 앱 서비스 → Settings → Networking → Public Networking → **Generate Domain**
5. **헬스체크**: 앱 서비스 Settings에서 Healthcheck Path를 `/healthz`로. 배포 시작 때 한 번 확인하고, 2xx가 오면 새 버전으로 전환된다
6. `railway.toml`(Config as Code)은 쓰지 않는다. Railway 문서상 2026-12-01 이후 지원이 끝나는 방식이라 대시보드에서 설정한다
7. 처음 한 번: Postgres 서비스의 Data/Query 화면에서 `CREATE EXTENSION IF NOT EXISTS vector;`, 앱 서비스 셸에서 `python manage.py createsuperuser` (관리 화면이 필요할 때만)

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
