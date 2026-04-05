# DB Schema (Generated)

> 이 파일은 자동 생성됩니다. 직접 수정하지 마세요.

현재 이 프로젝트는 파일 기반 저장(`output/*.md`, `output/*.log`)을 사용하며 DB가 없습니다.
DB 도입 시 스키마 정의가 여기에 자동 생성됩니다.

## 데이터 흐름 (현재)

```
yfinance / pykrx → src/data/ → src/analysis/ → src/agents/ → output/ → Slack
```

## 향후 DB 도입 시 후보 테이블

- `analysis_runs` — 분석 실행 이력
- `investment_ideas` — 생성된 투자 아이디어
- `slack_logs` — Slack 전송 이력
