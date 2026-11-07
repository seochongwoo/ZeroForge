# 0003. 한 서비스로 배포 (API + 웹)

- 상태: 채택
- 날짜: 2026-11-06

## 맥락

Step 5의 목표는 "개발 서버를 끈 상태에서 휴대폰과 노트북 브라우저 양쪽으로 기록을 쓰고 서로의 기록을 본다"이다. 혼자 쓰는 도구라 관리할 것이 적을수록 좋고, 비용도 적어야 한다. 호스팅은 아직 고르지 않았다.

## 결정

- **Django가 Expo 웹 빌드까지 같은 주소에서 서빙한다.** 서비스 하나, 도메인 하나.
  - `/api/*` API, `/admin/*` 관리 화면, `/healthz` 헬스체크(인증 없음, DB 연결 확인)
  - `/_expo/static/*`, `/favicon.ico` 등 빌드 파일은 WhiteNoise가 서빙. 파일명에 해시가 붙은 번들은 1년 캐시(immutable)
  - 그 외 경로는 `index.html` (SPA). 단 확장자가 있거나 `_expo/`로 시작하는 없는 파일은 404 — JS 자리에 HTML이 가서 화면이 하얘지는 것을 막는다
  - 같은 주소라 CORS가 필요 없다. 웹 설정 화면은 서버 주소를 자동으로 채우고 토큰만 받는다
- **Dockerfile 하나**(저장소 루트)로 Railway / Render / Fly.io 어디든 올린다. node로 웹을 빌드하고, python 이미지에서 gunicorn으로 실행한다. 시작할 때 `migrate`를 적용한다.
- **DB 접속은 `DATABASE_URL`** 하나로 받는다(호스팅이 주는 형식). 없으면 로컬용 `POSTGRES_*`.
- 운영(`DEBUG=False`)에서는 HTTPS 리다이렉트를 켜되 `/healthz`는 뺀다(내부 http 헬스체크). `GET`과 `HEAD` 모두 받는다 — 웹의 NetInfo가 `HEAD /`로 연결을 확인한다.

## 검토한 대안

- 웹은 정적 호스팅(Cloudflare Pages 등), API는 따로: 서비스가 둘, 도메인이 둘, CORS 설정이 생긴다. 웹 첫 로딩은 CDN이 조금 빠르지만, 혼자 쓰는 규모에서는 관리 비용이 더 크다. 웹이 주 무대가 되면 재검토.

## 결과

- 휴대폰 브라우저에서 홈 화면에 추가하면 앱처럼 쓸 수 있다 (develop_plan 5-2).
- Android 앱(APK)은 서버 주소를 직접 넣어야 한다. iOS 앱 설치는 유료 개발자 계정이 필요해 보류.
- Dockerfile은 로컬에 Docker가 없어 CI(`.github/workflows/docker.yml`)에서 빌드·실행·스모크 테스트로 확인한다.
