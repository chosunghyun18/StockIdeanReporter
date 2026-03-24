# CLAUDE.md — 투자 분석 에이전트 시스템

Claude Code가 이 저장소에서 작업할 때 따르는 지침입니다.

## 프로젝트 개요

**목적:** 국내/해외 주식의 산업 분석, 주가 분석, 투자 아이디어를 자동 생성하고 Slack으로 전달하는 멀티 에이전트 시스템

**기술 스택:** Python
**분석 대상:** 국내주식 (KRX), 해외주식 (NYSE/NASDAQ)
**결과물:** Slack 메시지

## 에이전트 아키텍처

```
orchestrator (총괄)
├── industry-analyst   ─┐ 병렬 실행
├── price-analyst      ─┘
├── idea-generator       (위 2개 완료 후)
└── reporter             (idea-generator 완료 후) → Slack
```

## 디렉터리 구조

```
agents/
├── orchestrator.md      — 전체 파이프라인 조율
├── industry-analyst.md  — 산업/섹터 분석
├── price-analyst.md     — 주가 기술적/기본적 분석
├── idea-generator.md    — 투자 아이디어 도출
├── reporter.md          — Slack 전송
├── planner.md           — 구현 계획 (ECC 기본 제공)
├── code-reviewer.md     — 코드 리뷰 (ECC 기본 제공)
└── security-reviewer.md — 보안 검토 (ECC 기본 제공)
src/
├── data/               — 데이터 수집 모듈
├── analysis/           — 분석 로직
├── agents/             — 에이전트 구현체
└── slack/              — Slack 연동
output/                 — 분석 결과 임시 저장
tests/                  — 테스트
skills/                 — ECC 스킬 (python-patterns, market-research 등)
rules/                  — ECC 코딩 규칙
commands/               — ECC 슬래시 커맨드
hooks/                  — ECC 자동화 훅
```

## 환경변수 (필수)

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SLACK_CHANNEL=#investment-ideas
```

## 주요 Python 라이브러리

```python
yfinance          # 주가 데이터 (국내 .KS/.KQ + 해외)
FinanceDataReader # 국내 주가 보조
pykrx             # KRX 재무데이터
ta / pandas_ta    # 기술적 분석 지표
anthropic         # Claude API
requests          # Slack Webhook
```

## 개발 원칙 (ECC 기반)

- **에이전트 우선**: 복잡한 작업은 전문 에이전트에 위임
- **테스트 우선**: 80% 이상 커버리지 (pytest)
- **보안**: API 키/토큰 절대 하드코딩 금지, 환경변수 사용
- **불변성**: 데이터 객체 직접 수정 금지, 새 객체 반환
- **계획 후 실행**: 복잡한 구현 전 planner 에이전트 사용

## 에이전트 오케스트레이션

| 상황 | 호출 에이전트 |
|------|-------------|
| 종목 분석 요청 | orchestrator |
| 산업/섹터 분석 | industry-analyst |
| 주가 분석 | price-analyst |
| 투자 아이디어 도출 | idea-generator |
| Slack 전송 | reporter |
| 구현 계획 필요 | planner |
| 코드 작성/수정 후 | code-reviewer |
| 보안 민감 코드 | security-reviewer |
| Python 리뷰 | python-reviewer |

## 코딩 컨벤션

- 파일당 최대 400줄
- 함수당 최대 50줄
- 타입 힌트 필수
- docstring: Google 스타일
- 파일명: lowercase with hyphens

## 테스트 실행

```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

## 슬래시 커맨드 (ECC 제공)

- `/plan` — 구현 계획 수립
- `/tdd` — 테스트 주도 개발
- `/code-review` — 코드 품질 검토
- `/security-scan` — 보안 취약점 스캔

## 커밋 규칙

`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:` 접두사 사용

## 보안 체크리스트 (커밋 전)

- [ ] 환경변수로 모든 민감 정보 관리
- [ ] 외부 입력 검증
- [ ] SQL 인젝션 방지 (파라미터화 쿼리)
- [ ] 에러 메시지에 민감 정보 미포함
