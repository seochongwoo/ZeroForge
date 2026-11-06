# ZeroForge

언제든 접속해, 아주 짧게라도 자기 언어로 사유하고 스스로 이름 붙이는 공간.

AI는 판정자가 아니라 서기(scribe)다.

사업이 아니라 지금의 나에게 도움이 되는 개인 도구로 만든다. 기능은 설계가 아니라 실제 사용에서 나온다.

- [PLAN.md](PLAN.md) — 재시작 플랜
- [PRINCIPLES.md](PRINCIPLES.md) — 모든 PR이 확인하는 원칙
- [docs/decisions/](docs/decisions/) — 결정 기록(ADR)
- [docs/friction.md](docs/friction.md) — 쓰면서 느낀 마찰 = 백로그

## 개발 환경

```bash
cp .env.example .env
pip install pre-commit && pre-commit install   # gitleaks로 비밀값 커밋 방지
```

실제 기록, DB 덤프, 실제 내용이 담긴 fixture는 커밋하지 않는다 (P8).

## 라이선스

[MIT](LICENSE)
