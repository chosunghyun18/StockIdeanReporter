# StockIdeaReporter

AI 기반 주식 투자 아이디어 분석 시스템

## 구조

```
StockIdeaReporter/
├── backend/          Python FastAPI 서버 + 에이전트 코어
│   ├── api.py        FastAPI 엔드포인트
│   ├── main.py       CLI 진입점
│   ├── src/          에이전트, 분석, 데이터, Slack 모듈
│   ├── tests/
│   └── output/       분석 결과 마크다운 저장
└── frontend/         Vue.js UI
    ├── src/
    │   ├── App.vue
    │   ├── api/      axios 클라이언트
    │   └── components/
    │       ├── StockAnalyzer.vue    — 종목 입력 + 분석 실행
    │       ├── AnalysisResult.vue  — 결과 표시 + Slack 버튼
    │       ├── SlackSendButton.vue — Slack 전송 버튼
    │       └── ResultHistory.vue  — 과거 분석 결과 목록
    └── vite.config.js
```

## 실행

### 백엔드

```bash
cd backend
pip install -r requirements.txt

# 환경변수 설정
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
export ANTHROPIC_API_KEY=sk-ant-...

uvicorn api:app --reload --port 8000
```

### 프론트엔드

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| GET | /api/results | 분석 결과 목록 |
| GET | /api/results/{ticker} | 특정 종목 결과 |
| POST | /api/analyze | 종목 분석 실행 |
| POST | /api/slack/send | Slack 전송 |
| GET | /api/health | 헬스체크 |

## CLI 사용 (기존 방식)

```bash
cd backend
python main.py --ticker AAPL --market US
python main.py --ticker 005930 --market KR
python main.py --discover --market KR US --top-n 5
```
