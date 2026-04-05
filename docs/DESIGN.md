# Design Overview

멀티 프로젝트 레포 설계 개요입니다. 상세 내용은 `design-docs/` 참조.

## 프로젝트 구조

```
josh/
├── StockIdeaReporter/   — 주식 분석 + Slack 리포팅 (Python)
├── AgentDashBoard/      — 에이전트 모니터링 UI (Next.js)
├── agents/              — Claude 에이전트 프롬프트 (공유)
├── docs/                — 이 문서 루트
└── .claude/             — Claude Code 설정
```

## 에이전트 레이어

에이전트 프롬프트(`.md`)와 Python 구현체(`.py`)는 분리 관리:

- `agents/*.md` — Claude 프롬프트 정의 (Claude Code가 읽음)
- `StockIdeaReporter/src/agents/*.py` — 실제 API 호출 구현

자세한 내용: [core-beliefs.md](design-docs/core-beliefs.md)
