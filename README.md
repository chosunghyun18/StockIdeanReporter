# 📊 StockIdea Reporter

국내/해외 주식의 산업 분석, 주가 분석, 투자 아이디어를 자동 생성하고 Slack으로 전달하는 **멀티 에이전트 투자 분석 시스템**입니다.

---

## 개요

Claude AI 기반 전문 에이전트들이 협력하여 종목 분석 → 투자 아이디어 도출 → Slack 리포트 전송까지 전 과정을 자동화합니다.

```
orchestrator (총괄)
├── industry-analyst  ─┐ 병렬 실행
├── price-analyst     ─┘
├── idea-generator      (위 2개 완료 후)
└── reporter            (idea-generator 완료 후) → Slack
```

---

## 기능

- **산업 분석**: 거시경제 환경, 섹터 트렌드, 경쟁 구도, 산업 리스크 평가
- **주가 분석**: RSI, MACD, 볼린저밴드 등 기술적 분석 + PER, ROE 등 기본적 분석
- **투자 아이디어**: 진입가/목표가/손절가, 리스크-리워드, 시나리오별 전망 도출
- **Slack 전송**: Block Kit 포맷 리포트 자동 전송 (재시도 및 Rate Limit 처리 포함)

---

## 시작하기

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
export SLACK_CHANNEL=#investment-ideas   # 선택 (기본값: #investment-ideas)
```

### 3. 실행

```bash
# 국내 주식 (KOSPI)
python main.py --ticker 005930.KS --market KR

# 국내 주식 — suffix 자동 보완
python main.py --ticker 005930 --market KR

# 해외 주식
python main.py --ticker AAPL --market US
```

---

## 프로젝트 구조

```
.
├── main.py                  # CLI 진입점
├── requirements.txt         # 의존성 목록
├── agents/                  # 에이전트 정의 (마크다운 명세)
│   ├── orchestrator.md
│   ├── industry-analyst.md
│   ├── price-analyst.md
│   ├── idea-generator.md
│   └── reporter.md
├── src/
│   ├── data/
│   │   ├── stock_data.py    # 주가 데이터 수집 (yfinance)
│   │   └── financial_data.py# 재무 데이터 수집
│   ├── analysis/
│   │   ├── technical.py     # 기술적 분석 지표
│   │   └── fundamental.py   # 기본적 분석 평가
│   ├── agents/
│   │   ├── orchestrator.py  # 파이프라인 조율 (병렬 실행)
│   │   ├── industry_analyst.py
│   │   ├── price_analyst.py
│   │   ├── idea_generator.py
│   │   └── reporter.py
│   └── slack/
│       └── client.py        # Slack Webhook 클라이언트
├── output/                  # 분석 결과 임시 저장
└── tests/                   # 단위 테스트 (56개, 커버리지 80%)
```

---

## 주요 라이브러리

| 용도 | 라이브러리 |
|------|-----------|
| 주가 데이터 | `yfinance` |
| 기술적 분석 | `ta` |
| AI 에이전트 | `anthropic` |
| Slack 전송 | `requests` |
| 데이터 처리 | `pandas`, `numpy` |

---

## 테스트

```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

---

## Slack 리포트 예시

```
📊 투자 아이디어 리포트
삼성전자 (005930.KS) | 2026-03-24 | 🟡 중기

📌 투자 테제
반도체 사이클 회복과 HBM 수요 급증으로 수혜 예상...

🎯 실행 계획
진입: 72,000~74,000원  목표1: 82,000원  목표2: 90,000원  손절: 68,000원
R/R 비율: 1:2.5

📈 시나리오별 전망
🟢 강세: HBM 수주 확대 및 실적 서프라이즈
🟡 기본: 점진적 회복세 유지
🔴 약세: 글로벌 경기 침체로 수요 위축

산업 매력도: ⭐⭐⭐⭐ | 기술적: 매수 | 밸류에이션: 저평가
```

---

## 분석 대상

- **국내 주식**: KRX (KOSPI `.KS` / KOSDAQ `.KQ`)
- **해외 주식**: NYSE / NASDAQ
