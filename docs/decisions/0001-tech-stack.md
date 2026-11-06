# 0001. 기술 스택

- 상태: 채택
- 날짜: 2026-11-06

## 맥락

핵심 경험은 "언제든 접속해 아주 짧게라도 사유하는 것"이다. 웹과 앱을 모두 지원해야 하고, 웹 첫 로딩이 빨라야 하며, 한글 입력이 완벽해야 한다. 또한 P1(AI는 판정하지 않는다)을 구조적으로 강제할 수 있어야 한다.

## 결정

| 영역 | 선택 |
|------|------|
| 클라이언트 | Expo (React Native) + TypeScript |
| 백엔드 | Django + Django Ninja |
| DB | PostgreSQL + pgvector |
| LLM | 공급사 SDK 직접 사용, 프롬프트는 파일로 버전 관리 |
| 캐시 | Redis 보류 |

## 근거

- Expo는 iOS/Android/웹을 한 코드베이스로 다루고, 웹에서 실제 HTML 입력창이 렌더링되어 한글 조합을 브라우저가 처리한다.
- Django Ninja의 Pydantic 스키마 하나로 LLM structured output, 서버 검증, API 응답 타입을 통일해 P1을 구조로 강제한다.
- pgvector로 구조화된 기록과 `history_context` 의미 검색을 한 DB에서 처리한다.

## 검토한 대안

- Flutter: 웹 초기 로딩 용량과 한글 IME 이슈가 핵심 경험과 충돌
- Next.js + Capacitor: 앱이 웹뷰 기반, 앱스토어 심사 리스크. 웹이 주 무대가 되면 재검토
- 풀 TypeScript 백엔드: Python 데이터 분석·ML 역량과 단절
