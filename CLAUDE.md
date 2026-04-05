# CLAUDE.md — 투자 분석 에이전트 시스템

Claude Code가 이 저장소에서 작업할 때 따르는 지침입니다.

## 프로젝트 개요

**목적:** 국내/해외 주식의 산업 분석, 주가 분석, 투자 아이디어를 자동 생성하고 Slack으로 전달하는 멀티 에이전트 시스템

**기술 스택:** Python
**분석 대상:** 국내주식 (KRX), 해외주식 (NYSE/NASDAQ)
**결과물:** Slack 메시지

## 에이전트 아키텍처

### 개별 종목 파이프라인
```
orchestrator (총괄)
├── market-bias-analyst  (항상 첫 번째 — 레짐 + 배팅 Multiplier)
│     ↓ SIDEWAYS? → 현금 보유 알림 후 종료
├── industry-analyst  ─┐ 병렬 실행
├── price-analyst     ─┘ (롱/숏 확률 % 산출)
├── idea-generator       (위 3개 완료 후 — 최종 배팅 크기 결정)
└── reporter             (idea-generator 완료 후) → Slack
```

### ETF 파이프라인
```
orchestrator
├── market-bias-analyst  (레짐 확인)
├── etf-manager          (ETF 서브-오케스트레이터)
│     ├── leveraged-etf-analyst  ─┐ 병렬 실행
│     └── thematic-etf-analyst   ─┘
│     └── etf-launch-monitor       (주간 모드 시)
└── reporter → Slack
```

### 롱/숏 배팅 크기 결정 공식
```
최종 포지션 = 기본 배팅(10%) × 레짐 Multiplier × 신뢰도(%)

레짐 Multiplier:
  BULL      → 1.0x
  BEAR      → 1.0x (숏 방향)
  VOLATILE  → 1.3x (방향 있을 때)
  SIDEWAYS  → 0x  (신규 진입 금지)

신뢰도 구간:
  ≥75% → 풀 포지션  ≥65% → 중간  ≥55% → 소규모  <55% → 관망
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

## 작업 기억 시스템 (Task Memory System)

큰 작업을 시작할 때마다 반드시 세 가지 문서를 먼저 생성하고 작업 내내 업데이트한다.

| 문서 | 파일 위치 | 역할 |
|------|-----------|------|
| 계획서 | `output/plan-<기능명>.md` | 무엇을 어떻게 만들지 설계도 |
| 맥락노트 | `output/context-<기능명>.md` | 왜 이렇게 결정했는지, 관련 파일 위치 |
| 체크리스트 | `output/checklist-<기능명>.md` | 완료 항목 / 남은 항목 추적 |

### 작업 흐름

1. **계획 수립** → planner 에이전트 호출: `이번 작업 계획 세워줘`
2. **계획 검토** → 핵심 의도가 맞는지 직접 확인 (AI 해석 오류 방지)
3. **문서 저장** → 계획 승인 즉시 세 문서 파일 생성
4. **새 대화에서 재개** → 저장된 문서 읽고 이어서 작업
5. **중간중간 업데이트** → `체크리스트 업데이트하고 다음 작업 정리해`

> 대화가 길어지거나 새 세션을 시작해도 이 세 문서가 있으면 컨텍스트를 즉시 복원할 수 있다.

## 자동 훅 시스템 (Auto Hook System)

`hooks/scripts/` 의 두 훅이 자동으로 동작한다.

| 훅 | 시점 | 동작 |
|----|------|------|
| `investment-skill-router.js` | 프롬프트 제출 직후 | 키워드 분석 → 관련 스킬/에이전트 매뉴얼 안내 |
| `investment-quality-check.js` | 응답 완료 후 | 보안·에러처리·타입힌트·테스트 자체 점검 리마인더 |

**스킬 라우팅 키워드 예시**

| 키워드 | 연결 매뉴얼 |
|--------|------------|
| test, pytest, 테스트 | `skills/python-testing/SKILL.md` |
| market, 주가, 종목, 산업 | `skills/market-research/SKILL.md` |
| security, 보안, token | `skills/security-scan/SKILL.md` |
| api, yfinance, pykrx, slack | `skills/backend-patterns/SKILL.md` |
| agent, orchestrat, 파이프라인 | `agents/orchestrator.md` |

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
| 시장 방향/레짐 확인 | market-bias-analyst |
| 산업/섹터 분석 | industry-analyst |
| 주가 분석 + 롱숏 확률 | price-analyst |
| 투자 아이디어 + 배팅 크기 | idea-generator |
| ETF 전반 분석 | etf-manager |
| 레버리지/인버스 ETF | leveraged-etf-analyst |
| 테마 ETF | thematic-etf-analyst |
| 신규 ETF 출시 모니터링 | etf-launch-monitor |
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
