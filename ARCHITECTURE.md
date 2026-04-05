# Architecture

## 레포 구조 (멀티 프로젝트)

```
josh/
├── StockIdeaReporter/      — 주식 분석 + Slack 리포팅 (Python)
│   ├── src/
│   │   ├── agents/         — 에이전트 Python 구현체
│   │   ├── analysis/       — 분석 로직 (순수 함수)
│   │   ├── data/           — 외부 데이터 수집
│   │   └── slack/          — Slack 연동
│   ├── tests/
│   ├── output/             — 분석 결과 임시 저장
│   ├── main.py
│   └── requirements.txt
│
├── AgentDashBoard/         — 에이전트 모니터링 UI (Next.js)
│   ├── app/
│   │   └── api/            — REST API Routes
│   └── components/
│
├── agents/                 — Claude 에이전트 프롬프트 (공유, .md)
│   ├── orchestrator.md
│   ├── market-bias-analyst.md
│   ├── industry-analyst.md
│   ├── price-analyst.md
│   ├── idea-generator.md
│   ├── reporter.md
│   └── ... (ECC 범용 에이전트 포함)
│
├── docs/                   — 프로젝트 문서
│   ├── design-docs/        — 설계 결정 문서
│   ├── exec-plans/         — 실행 계획 (active / completed)
│   ├── generated/          — 자동 생성 문서
│   ├── product-specs/      — 제품 기능 명세
│   ├── references/         — 참고 자료 (스크린샷 등)
│   ├── DESIGN.md
│   ├── FRONTEND.md
│   ├── PLANS.md
│   ├── PRODUCT_SENSE.md
│   ├── QUALITY_SCORE.md
│   ├── RELIABILITY.md
│   └── SECURITY.md
│
├── .claude/                — Claude Code 설정
├── commands/               — 슬래시 커맨드
├── skills/                 — ECC 스킬
├── rules/                  — 코딩 규칙
├── hooks/                  — 자동화 훅
├── config/                 — 파이프라인 설정
│
├── AGENTS.md               — 에이전트 사용 지침
├── ARCHITECTURE.md         — 이 파일
├── CLAUDE.md               — Claude Code 지침
└── README.md               — 프로젝트 소개
```

## 에이전트 파이프라인 (StockIdeaReporter)

```
orchestrator (총괄)
├── market-bias-analyst  ← 항상 첫 번째 (레짐 판단)
│     ↓ SIDEWAYS → 현금 보유 알림 후 종료
├── industry-analyst  ─┐ 병렬
├── price-analyst     ─┘
├── idea-generator       ← 위 3개 완료 후
└── reporter             ← idea-generator 완료 후 → Slack
```

## 레이어 책임

| 레이어 | 위치 | 책임 | Side-effect |
|--------|------|------|-------------|
| Data | `src/data/` | 외부 API 호출 | 허용 |
| Analysis | `src/analysis/` | 지표 계산 | 없음 (순수 함수) |
| Agents | `src/agents/` | Claude API + 판단 | 허용 |
| Slack | `src/slack/` | 메시지 전송 | 허용 |

## 에이전트 프롬프트 vs 구현체

| 구분 | 위치 | 역할 |
|------|------|------|
| 프롬프트 정의 | `agents/*.md` | Claude Code가 읽는 역할 명세 |
| Python 구현 | `src/agents/*.py` | 실제 Claude API 호출 코드 |

## 기술 스택

| 영역 | 기술 |
|------|------|
| 분석 엔진 | Python, yfinance, pykrx, ta |
| AI | Anthropic Claude API |
| 알림 | Slack Webhook |
| 대시보드 | Next.js, TypeScript |
| 테스트 | pytest |
| CI | GitHub Actions |
