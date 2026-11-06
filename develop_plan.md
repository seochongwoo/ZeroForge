# ZeroForge 개발 순서

> PLAN.md가 "무엇을, 왜"라면 이 문서는 "어떤 순서로, 어떻게"다.
> 원칙: **얇게, 끝까지, 먼저.** 기능을 하나씩 완성하는 게 아니라, 가장 얇은 기능을 클라이언트–서버–DB–배포까지 한 번 관통시킨 뒤 두껍게 만든다.

---

## 전체 순서 한눈에 보기

```
Step 0  개발 환경 준비
Step 1  저장소 뼈대 + 안전장치         ← 코드보다 먼저 (public 저장소이므로)
Step 2  백엔드: Entry 저장/조회 API
Step 3  앱: 입력창 하나 + 기록 목록
Step 4  로컬 우선 저장 (outbox)
Step 5  배포                           ← 여기까지가 PLAN.md의 Phase 1
Step 6  직접 사용 + friction.md        ← Phase 2 (1~2주)
Step 7  이름 붙이기                    ← Phase 3
Step 8  AI 되돌려 받기                 ← Phase 4 (기록이 쌓인 뒤)
```

각 Step에는 **완료 기준**이 있다. 완료 기준을 넘기 전에는 다음 Step으로 가지 않는다.

---

## Step 0 — 개발 환경 준비

- Node.js LTS, Python 3.12 이상, Git, Docker
- Python 가상환경 도구 (venv 또는 uv)
- 휴대폰에 Expo Go 설치 (개발 중 확인용)

**완료 기준:** `node -v`, `python --version`, `docker run hello-world`가 모두 동작한다.

---

## Step 1 — 저장소 뼈대 + 안전장치

public 저장소이고 그 안에서 다룰 것이 내 사유이므로, 코드 한 줄 전에 안전장치부터 둔다.

### 1-1. 디렉터리 구조

```
zeroforge/
├── PLAN.md
├── develop_plan.md
├── PRINCIPLES.md
├── LICENSE                 # MIT
├── README.md
├── .gitignore
├── .env.example
├── docker-compose.yml
├── docs/
│   ├── decisions/
│   └── friction.md
├── backend/
└── app/
```

### 1-2. `.gitignore`에 반드시 포함

```
# 비밀값
.env
.env.*
!.env.example

# 실제 데이터 (P8)
*.sql
*.dump
backend/**/fixtures/real_*
data/

# Python
__pycache__/
.venv/

# Node / Expo
node_modules/
.expo/
dist/
```

### 1-3. 비밀값 유출 방지

- GitHub 저장소 설정에서 secret scanning / push protection이 켜져 있는지 확인
- 로컬에 pre-commit + gitleaks 설치해서 커밋 전에 검사

### 1-4. 첫 ADR

- `docs/decisions/0001-tech-stack.md` — Expo + Django Ninja + PostgreSQL(pgvector)를 고른 이유와 버린 대안 (PLAN.md §4 요약)

**완료 기준:** 첫 커밋이 문서와 설정 파일만으로 push되어 있고, `.env`를 일부러 커밋하려 하면 막힌다.

---

## Step 2 — 백엔드: Entry 저장/조회 API

### 2-1. 로컬 DB는 처음부터 pgvector 이미지로

나중에 AI 단계에서 DB를 바꾸지 않도록, 지금부터 pgvector가 포함된 PostgreSQL을 쓴다.

```yaml
# docker-compose.yml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: zeroforge
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: zeroforge
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

### 2-2. Django 프로젝트

- `backend/`에 Django 프로젝트(`config`)와 앱(`core`) 생성
- 패키지: `django`, `django-ninja`, `psycopg`, `django-cors-headers`, `pytest-django`
- 설정값(DB 접속 정보, 토큰)은 전부 환경 변수에서 읽는다

### 2-3. Entry 모델

```python
class Entry(models.Model):
    id = models.UUIDField(primary_key=True)        # 클라이언트가 생성 (Step 4의 중복 방지용)
    content = models.TextField()
    source = models.CharField(max_length=16)       # web | ios | android
    written_at = models.DateTimeField()            # 기기에서 실제로 쓴 시각
    created_at = models.DateTimeField(auto_now_add=True)  # 서버에 도착한 시각
```

- **id를 클라이언트가 만드는 이유:** 오프라인에서 쓴 기록을 나중에 다시 보낼 때, 같은 기록이 두 번 저장되지 않게 하기 위해서
- **written_at과 created_at을 나누는 이유:** 지하철에서 쓰고 한 시간 뒤에 동기화돼도, 기록의 시간은 쓴 순간이어야 한다
- 점수·상태 필드는 없다 (P1, P4)
- **Entry는 불변이다.** 수정 API를 만들지 않는다

### 2-4. API 두 개

```
POST /api/entries     기록 저장. 같은 id가 이미 있으면 기존 것을 그대로 돌려준다 (멱등)
GET  /api/entries     기록 목록. 최신순, 커서 기반 페이지네이션
```

인증은 단일 사용자 토큰:

```python
import secrets
from django.conf import settings
from ninja.security import HttpBearer

class TokenAuth(HttpBearer):
    def authenticate(self, request, token):
        if secrets.compare_digest(token, settings.ZF_TOKEN):
            return token
```

### 2-5. 테스트

- 저장 → 조회가 되는지
- 같은 id로 두 번 POST해도 하나만 저장되는지
- 토큰 없이 요청하면 거부되는지
- 테스트 데이터는 지어낸 문장만 사용 (P8)

**완료 기준:** 로컬에서 curl로 기록을 저장하고 조회할 수 있고, 테스트가 통과한다.

---

## Step 3 — 앱: 입력창 하나 + 기록 목록

### 3-1. Expo 프로젝트

- `app/`에 Expo 프로젝트 생성 (TypeScript, Expo Router)
- 화면은 두 개뿐
  - **메인:** 열면 바로 커서가 들어가 있는 입력창 + 저장 버튼, 아래에 지난 기록 목록
  - **설정 (한 번만):** 서버 주소와 토큰 입력

### 3-2. 토큰 저장

- 앱(iOS/Android): `expo-secure-store`
- 웹: secure-store를 쓸 수 없으므로 브라우저 저장소 사용. 혼자 쓰는 도구라 일단 이걸로 충분하고, 나중에 다른 사람에게 열 때 인증 방식을 다시 정한다

### 3-3. 이 단계에서 반드시 확인할 것

- **웹 브라우저(데스크톱·모바일)와 휴대폰에서 한글 입력이 끊기지 않는가**
- 앱을 열고 첫 글자를 칠 때까지 몇 번의 터치가 필요한가 (목표: 0번)
- 백엔드에 `django-cors-headers`로 웹 클라이언트 주소 허용

**완료 기준:** 로컬 서버에 붙여서 웹과 휴대폰(Expo Go) 양쪽에서 기록을 쓰고 목록에서 볼 수 있다.

---

## Step 4 — 로컬 우선 저장 (outbox)

"짧은 사유"에서 한 문장이 날아가는 경험은 치명적이다. 배포 전에 넣는다.

```
1. 입력 중인 내용은 타이핑할 때마다 기기에 임시 저장 (draft)
2. 저장 버튼 → 클라이언트가 UUID 생성 → outbox(기기 저장소)에 넣기 → 입력창 비우기
3. outbox에 있는 기록을 서버로 전송 시도
4. 성공하면 outbox에서 제거, 실패하면 남겨두고 나중에 재시도
5. 목록 화면은 서버 기록 + 아직 outbox에 있는 기록을 함께 보여준다
```

- 기기 저장소는 `@react-native-async-storage/async-storage` (웹에서도 동작)
- 서버 POST가 멱등이므로(Step 2-4) 재시도해도 중복이 생기지 않는다
- 재시도 시점: 앱이 다시 열릴 때, 네트워크가 돌아왔을 때, 다음 저장 때

**완료 기준:** 비행기 모드에서 기록을 쓰고 앱을 껐다 켠 뒤 네트워크를 연결하면, 기록이 한 번만 서버에 올라간다.

---

## Step 5 — 배포

"언제든 접속"은 배포해야만 확인할 수 있다. 여기까지가 첫 마일스톤이다.

### 5-1. 백엔드 + DB

- 비용이 적고 관리가 단순한 호스팅을 고른다
- **DB 호스팅이 pgvector 확장을 지원하는지 반드시 확인** (Step 8에서 필요)
- 운영 환경 설정: `DEBUG=False`, `ALLOWED_HOSTS`, HTTPS, 토큰은 호스팅의 환경 변수로

### 5-2. 웹

- Expo의 웹 정적 빌드를 정적 호스팅에 배포
- 휴대폰 브라우저에서 홈 화면에 추가해 두면 앱처럼 바로 열 수 있다

### 5-3. 앱

- **Android:** EAS Build로 APK를 만들어 직접 설치할 수 있다
- **iOS:** 스토어 밖 설치(TestFlight 등)는 유료 Apple 개발자 계정이 필요하다. 계정이 없다면 처음에는 웹을 홈 화면에 추가해서 쓰고, 앱 설치는 나중에 결정해도 된다

**완료 기준:** 개발 서버를 끈 상태에서, 휴대폰과 노트북 브라우저 양쪽으로 기록을 쓰고 서로의 기록을 볼 수 있다.

---

## Step 6 — 직접 사용 (1~2주)

새 기능을 만들지 않는다. 쓴다.

- 하루에 한 번 이상 열어 본다. 한 문장이어도 된다
- 불편한 순간을 바로 `docs/friction.md`에 적는다 (날짜 + 한 줄)
- 고치는 건 **마찰을 막는 것만.** 새 기능 아이디어는 friction.md 아래쪽 "아이디어" 칸에 적어 두고 만들지 않는다
- 기간이 끝나면 PLAN.md §9-1을 판단한다: 메모장보다 손이 먼저 가는가?

**완료 기준:** friction.md에 실제 사용에서 나온 기록이 쌓여 있고, 그중 가장 큰 것들이 고쳐져 있다.

---

## Step 7 — 이름 붙이기

friction.md가 다른 우선순위를 가리키면 그쪽을 먼저 한다.

- `Naming` (이름 자체) + `NamingVersion` (이름의 변천)
- 기록 하나 또는 여러 개에 이름을 붙일 수 있게
- 이름을 바꾸면 덮어쓰지 않고 새 버전을 추가
- 화면: 기록에서 이름 붙이기, 이름별로 기록 모아 보기, 이름이 어떻게 바뀌어 왔는지 보기
- AI는 아직 없다. 이름은 전부 내가 붙인다 (P2)

**완료 기준:** 이름을 붙이고, 바꾸고, 바뀐 과정을 다시 볼 수 있다.

---

## Step 8 — AI 되돌려 받기

기록이 충분히 쌓였을 때 시작한다. 참조할 과거가 없으면 AI는 응답하지 않는다 (P3). 안쪽 순서도 중요하다. **검색이 먼저, 생성은 나중이다.**

1. **pgvector 활성화 + 임베딩.** Entry에 embedding 필드 추가, 기존 기록 전부 임베딩
2. **검색 계층 하나.** `get_history_context(entry) -> list[Entry]` (의미 유사도 + 최근성 + 고정한 기록). 이 함수만으로 먼저 실험해 본다. 내 기록 몇 개를 넣었을 때 가져오는 과거 기록이 정말 관련 있어 보이는가?
3. **출력 스키마.** Pydantic 모델: 인용 / 연결 제안 / 질문 / 균열 지점. 그 외 필드가 생기면 실패하는 테스트를 같이 작성
4. **프롬프트 v1.** `backend/prompts/`에 파일로. 예시에 실제 기록을 넣지 않는다 (P8)
5. **API.** 기록 하나에 대해 Reflection 생성. `referenced_entry_ids`, `prompt_version`, `model` 저장
6. **화면.** 되돌려 받은 내용 + "참고한 기록" 표시 + 연결 제안 수락/거절 (`Link`)
7. **평가성 표현 필터.** 응답 후 이중 장치
8. **판단.** PLAN.md §9-2: 연결이 의미 있는가, 상투어인가. 상투어라면 프롬프트보다 2번 검색 계층을 먼저 의심한다

**완료 기준:** 내 기록에 대해 AI가 과거 기록을 근거로 인용·연결·질문을 돌려주고, 평가하는 필드는 구조적으로 존재하지 않는다.

---

## 계속 지킬 작업 습관

- **작은 커밋.** 혼자라도 기능 단위로 짧은 브랜치 → main
- **결정은 ADR로.** 바꾸기 어려운 결정을 할 때마다 `docs/decisions/`에 짧게 (예: 0002 로컬 우선 동기화 방식)
- **CI는 Step 2부터 조금씩.** 처음엔 백엔드 테스트만, Step 3부터 타입 검사, Step 8부터 스키마 필드 고정 테스트와 금지 어휘 검사
- **PR 템플릿의 P1–P8 체크리스트**는 혼자 머지할 때도 훑어본다
- **friction.md는 Step 6 이후에도 계속.** 이 도구의 방향은 내 사용에서 나온다
