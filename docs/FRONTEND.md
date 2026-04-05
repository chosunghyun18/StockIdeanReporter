# Frontend Guide

## AgentDashBoard (Next.js)

위치: `AgentDashBoard/`

### 기술 스택

- Framework: Next.js (App Router)
- Language: TypeScript
- Style: CSS Modules

### 실행

```bash
cd AgentDashBoard
npm install
npm run dev
```

### 주요 페이지

| 경로 | 설명 |
|------|------|
| `/` | 에이전트 목록 |
| `/graph` | 파이프라인 그래프 시각화 |
| `/sessions` | 실행 세션 이력 |

### API Routes

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /api/agents` | 에이전트 목록 |
| `GET /api/agents/[slug]` | 에이전트 상세 |
| `GET /api/graph` | 파이프라인 그래프 데이터 |
| `GET /api/pipelines` | 파이프라인 목록 |
| `GET /api/sessions` | 세션 이력 |
