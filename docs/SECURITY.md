# Security

## 원칙

모든 민감 정보는 환경변수로 관리한다. 코드에 직접 입력 금지.

## 민감 정보 목록

| 항목 | 환경변수명 | 저장 위치 |
|------|-----------|-----------|
| Anthropic API 키 | `ANTHROPIC_API_KEY` | `.env` (gitignore) |
| Slack Webhook URL | `SLACK_WEBHOOK_URL` | `.env` (gitignore) |

## 보안 체크리스트 (커밋 전)

- [ ] `.env` 파일이 `.gitignore`에 포함됨
- [ ] API 키/토큰이 코드에 하드코딩되지 않음
- [ ] 외부 입력(종목코드 등) 검증 처리됨
- [ ] 에러 메시지에 민감 정보 미포함

## 취약점 대응 이력

| 날짜 | 내용 | 조치 |
|------|------|------|
| - | - | - |

## 참고

- OWASP Top 10 준수
- `agents/security-reviewer.md` — 보안 리뷰 에이전트
- `skills/security-scan/SKILL.md` — 보안 스캔 스킬
