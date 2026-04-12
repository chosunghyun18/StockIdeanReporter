# MiroFishTrader — 구현 플랜

## 전체 흐름 요약

```
Phase 0 → 환경 세팅 & MiroFish 소스 분석
Phase 1 → 데이터 파이프라인 (수집 → 정제 → 지표 + Reddit 수집)
Phase 2 → 시드 변환 (금융 데이터 + Reddit 센티먼트 → MiroFish 입력 포맷)
Phase 3 → MiroFish 에이전트 구성 (페르소나 + GraphRAG + LLM 연결)
Phase 4 → 시뮬레이션 실행 & 확률 추출
Phase 5 → 매매 판단 출력 + Slack
Phase 6 → 백테스트 & 검증
```

---

## Phase 0 — 환경 세팅 & MiroFish 소스 분석

**목표:** 착수 전 외부 의존성과 MiroFish 내부 구조를 완전히 파악한다.

### 0-1. MiroFish 소스 코드 분석
- `git clone https://github.com/666ghj/MiroFish` 후 코드 전체 리딩
- 확인 항목:
  - 시드 데이터 입력 포맷 (JSON 스키마, 필드명)
  - `ReportAgent` 출력 구조 (어떤 필드로 결과를 반환하는지)
  - 에이전트 페르소나 설정 방식 (config 파일 or API)
  - GraphRAG 지식 그래프 구성 방식
  - 외부에서 시뮬레이션을 트리거하는 API 엔드포인트

### 0-2. 외부 서비스 계정 확보
- [ ] **Alpha Vantage** 무료/유료 API 키 발급 (40년치 일봉 필요 → 유료 플랜 검토)
- [ ] **Zep Cloud** 계정 + API 키 (MiroFish 에이전트 장기기억)
- [ ] **Claude API** 키 (이미 보유)
- [ ] **Slack Webhook URL** (기존 프로젝트 것 재사용 가능)

### 0-3. 로컬 개발 환경
```bash
# Python 3.11 가상환경
python3.11 -m venv .venv && source .venv/bin/activate

# MiroFish Docker 실행 확인
cd MiroFish && docker compose up -d

# 필수 패키지
pip install yfinance pandas_ta anthropic zep-python requests fastapi
```

### 0-4. .env 파일 정의
```
ALPHA_VANTAGE_API_KEY=
ZEP_API_KEY=
ANTHROPIC_API_KEY=
SLACK_WEBHOOK_URL=
```

**완료 기준:** MiroFish가 Docker로 정상 기동되고, ReportAgent 출력 포맷 문서화 완료

---

## Phase 1 — 데이터 파이프라인

**목표:** SPY 40년치 일봉 OHLCV + 기술적 지표를 Parquet으로 저장한다.

### 1-1. 데이터 수집 (`data/collector.py`)
```
수집 대상:
  - SPY ETF 일봉 (1993~현재, 약 30년 = yfinance로 충분)
  - S&P500 지수 (^GSPC, 1980~현재)
  - VIX 지수 (^VIX)
  - 미국 10년물 국채금리 (^TNX)
  - DXY 달러인덱스 (DX-Y.NYB)

저장 형식: data/raw/{ticker}_{YYYYMMDD}.parquet
```

- [ ] `yfinance.download()` 래퍼 함수 작성
- [ ] 증분 업데이트 로직 (마지막 저장일 이후만 재수집)
- [ ] 수집 실패 시 재시도 (최대 3회)

### 1-2. 데이터 정제 (`data/processor.py`)
- [ ] 결측값 처리 (거래일 기준 forward fill)
- [ ] NYSE 거래일 캘린더 적용 (`pandas_market_calendars`)
- [ ] 일봉 → 주봉 리샘플링 (OHLCV 규칙: O=첫날, H=최고, L=최저, C=마지막, V=합계)
- [ ] 저장: `data/processed/{ticker}_daily.parquet`, `data/processed/{ticker}_weekly.parquet`

### 1-3. 기술적 지표 계산 (`signals/indicators.py`)
```python
계산 지표:
  - RSI(14)
  - MACD(12, 26, 9)  →  MACD선, 시그널선, 히스토그램
  - 볼린저밴드(20, 2)  →  upper, mid, lower, %B
  - OBV (On-Balance Volume)
  - ATR(14)  →  변동성 측정
  - 200일 / 50일 이동평균 (추세 방향)
```

- [ ] 각 지표 함수 단위 테스트 작성
- [ ] 지표 통합 피처 테이블 생성 → `data/features/spy_features.parquet`

**완료 기준:** `spy_features.parquet` 로컬 생성, 결측값 0개 확인

---

## Phase 1-B — Reddit 센티먼트 파이프라인

**목표:** 주요 금융 서브레딧의 실시간 + 과거 데이터를 수집해 시장심리 에이전트의 시드로 활용한다.

### 왜 Reddit인가?

```
Reddit 데이터의 투자 신호 가치:

  r/wallstreetbets  → 극단적 소매 FOMO/공포 = 역추세 신호 (극단 낙관 = 천장 경고)
  r/investing       → 메인스트림 정서 흐름
  r/stocks          → 개별 종목 내러티브 변화 감지
  r/Economics       → 거시경제 해석 군중 반응
  r/options         → 풋/콜 포지션 심리 (기관과 개인 괴리)
  r/SecurityAnalysis → 고품질 펀더멘털 분석 (스마트머니 관점)
```

### 수집 도구 선택

| 도구 | 용도 | 한계 |
|------|------|------|
| `asyncpraw` | 실시간 스트리밍 + 최근 1000개 포스트 | 오래된 과거 데이터 불가 |
| Reddit JSON API | 인증 없이 `.json` 접근 (임시용) | rate limit 빡빡함 |
| Hugging Face 데이터셋 | WSB 과거 데이터 (2012~2021 공개) | 업데이트 안됨 |
| Kaggle Reddit 데이터셋 | 백테스트용 과거 아카이브 | 수동 다운로드 |

**전략: 과거(백테스트)는 HuggingFace 데이터셋, 실시간은 asyncpraw**

### 1-B-1. asyncpraw 수집기 (`data/reddit_collector.py`)

```python
# 수집 대상 서브레딧 + 항목
SUBREDDITS = {
    "wallstreetbets": {"weight": 0.35, "role": "contrarian"},
    "investing":      {"weight": 0.25, "role": "consensus"},
    "stocks":         {"weight": 0.20, "role": "narrative"},
    "Economics":      {"weight": 0.10, "role": "macro"},
    "options":        {"weight": 0.10, "role": "positioning"},
}

# 수집 필드
fields = [
    "title", "selftext", "score", "upvote_ratio",
    "num_comments", "created_utc", "flair"
]
```

- [ ] asyncpraw OAuth2 앱 등록 및 `.env` 키 설정
  - Reddit → Preferences → Apps → "script" 타입 앱 생성
  - 필요 키: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`
- [ ] 서브레딧별 `hot` + `new` 포스트 수집 (각 100개/회)
- [ ] 실시간 스트림: `subreddit.stream.submissions()` 비동기 처리
- [ ] 저장: `data/raw/reddit/{date}/{subreddit}.jsonl`

### 1-B-2. Reddit 센티먼트 분석 (`data/reddit_processor.py`)

```
분석 레이어 1 — 키워드 기반 (빠름, 비용 없음)
  - "buy / bull / moon / YOLO / all in" → 강세 점수 +1
  - "sell / bear / crash / puts / short" → 약세 점수 -1
  - SPY/S&P/market 언급 빈도 카운트

분석 레이어 2 — Claude API 배치 분석 (정확함)
  - 상위 20개 포스트 제목+본문 배치 전송
  - 출력: {bullish_pct, bearish_pct, neutral_pct, dominant_narrative}

분석 레이어 3 — 이상 감지
  - 포스트 수 / 업보트 수 Z-score → 비정상 급등 감지 (이벤트 트리거)
```

- [ ] 레이어 1 키워드 룰셋 정의 (`signals/sentiment_keywords.py`)
- [ ] 레이어 2 Claude API 배치 분석 함수 (일 1회, 장 마감 후)
- [ ] 레이어 3 이상 감지 알림 (VIX 급등과 교차 검증)
- [ ] 일별 Reddit 센티먼트 지수 생성 → `data/features/reddit_sentiment.parquet`

### 1-B-3. WSB 역추세 지표 (핵심 알파)

```
WSB 극단 지수 (Contrarian Score):
  - 최근 7일 bullish 포스트 비율 상위 10% 진입 → 단기 천장 경고
  - 최근 7일 bearish 포스트 비율 상위 10% 진입 → 단기 바닥 기회
  - 월별 FOMO 점수 vs SPY 수익률 백테스트로 신호 강도 검증
```

- [ ] WSB 극단 지수 계산 함수
- [ ] SPY 수익률과 상관관계 분석 (백테스트 Phase 6에서 검증)

### 1-B-4. 과거 데이터 (백테스트용)

```
무료 데이터셋:
  - HuggingFace: "mjw/stockmarket_reddit_posts" (WSB 2012~)
  - Kaggle: "Reddit WallStreetBets Posts" (여러 버전 존재)
  - 직접 아카이브: pushshift.io 대안으로 arctic.dmi.dk 검토
```
- [ ] HuggingFace datasets 라이브러리로 다운로드
- [ ] 날짜 인덱스 정렬 후 `data/raw/reddit_historical.parquet` 저장

### Reddit 데이터의 MiroFish 활용 방식

```
Reddit 센티먼트
       ↓
시장심리 담당 에이전트에 시드로 주입

에이전트 입력 텍스트 예시:
"2024-03-15 Reddit 시장 심리:
 - r/wallstreetbets: 강세 72% / 약세 18% (극단 낙관 주의)
 - WSB 극단 지수: 8.3/10 → 과거 유사 수준에서 5회 중 4회 단기 조정
 - 지배적 내러티브: 'AI 랠리 지속', 'Fed 피벗 임박'
 - 이상 감지: r/investing 포스트 수 3일 연속 +2σ 급등"
```

**완료 기준:** 날짜 입력 → Reddit 센티먼트 요약 텍스트 자동 생성

---

## Phase 2 — 시드 데이터 변환

**목표:** Phase 1 결과물을 MiroFish가 읽을 수 있는 시드 포맷으로 변환한다.

> MiroFish는 "뉴스/정책/금융 신호 텍스트"를 시드로 받는다.
> 숫자 데이터를 자연어 요약 텍스트로 변환하는 것이 핵심.

### 2-1. 롤링 컨텍스트 윈도우 구성 (`mirofish/seed_builder.py`)
```
윈도우 크기: 최근 252 거래일 (= 1년)
출력: 각 날짜 기준 "시장 상황 요약 텍스트"

예시 출력 (기술적 지표 + Reddit 통합):
"2024-03-15 기준 시장 데이터:
 - SPY 종가: $512.3 (전일 대비 +1.2%)
 - RSI(14): 68.4 → 과매수 근접
 - MACD: 양전환 3일째
 - 200일 이평 대비: +8.3% (상단 유지)
 - VIX: 14.2 (저변동성 구간)
 - 10년물 금리: 4.35%
 - Reddit 심리: WSB 강세 72% / 극단지수 8.3 (역추세 경고)
 - 지배 내러티브: 'AI 랠리 지속', 'Fed 피벗 임박'"
```

- [ ] 숫자 → 자연어 변환 함수 (각 지표별 해석 룰 정의)
- [ ] 날짜 범위별 시드 텍스트 배치 생성
- [ ] MiroFish 시드 JSON 스키마로 직렬화

### 2-2. 에이전트별 프롬프트 템플릿 설계
```
거시경제 에이전트 → 금리, DXY, 경기지표 중심 요약
실적 에이전트    → 어닝시즌 일정, EPS 서프라이즈 히스토리
심리 에이전트    → VIX + RSI + 볼린저밴드 %B + Reddit 극단지수 + 내러티브
                   ↑ Reddit 데이터가 가장 직접적으로 투입되는 지점
```

**완료 기준:** 임의 날짜에 대해 3개 에이전트용 시드 텍스트 정상 생성 확인

---

## Phase 3 — MiroFish 에이전트 구성

**목표:** 3개 전문 에이전트를 MiroFish 위에 올리고 Claude API와 연결한다.

### 3-1. LLM 백엔드 연결 (`mirofish/agent_config.py`)
```
MiroFish는 OpenAI SDK 호환 엔드포인트를 사용.
Claude API는 직접 호환되지 않으므로 프록시 레이어 필요.

방법 A: litellm 프록시 서버로 Claude → OpenAI 포맷 변환
  pip install litellm
  litellm --model anthropic/claude-sonnet-4-6 --port 8001

방법 B: MiroFish LLM 설정을 Claude SDK로 직접 패치 (소스 수정)
```
- [ ] litellm 프록시 방식으로 우선 시도
- [ ] MiroFish config에서 `base_url=http://localhost:8001` 설정

### 3-2. Zep Cloud 메모리 설정
```
에이전트별 메모리 세션:
  - macro_agent_memory   → Fed 결정, 금리 변동 히스토리
  - earnings_agent_memory → 어닝 서프라이즈 패턴
  - sentiment_agent_memory → VIX 스파이크, 공포/탐욕 히스토리
```
- [ ] Zep Python SDK로 세션 초기화 코드 작성
- [ ] 과거 데이터 기반 초기 메모리 주입 (cold start 방지)

### 3-3. 에이전트 페르소나 정의
```yaml
# macro_analyst 페르소나 예시
name: "MacroAnalyst"
role: "연준 정책 및 거시경제 전문가"
background: |
  20년 경력의 채권/매크로 트레이더.
  금리 사이클, 달러 강세/약세, 경기 확장/수축 구간을 분석하여
  S&P500의 방향성에 미치는 영향을 판단한다.
decision_style: "데이터 기반, 보수적, 리스크 우선"
```
- [ ] `macro_analyst` 페르소나 작성
- [ ] `earnings_analyst` 페르소나 작성
- [ ] `sentiment_analyst` 페르소나 작성

### 3-4. GraphRAG 지식 그래프 구성
```
노드: 거시경제 ↔ 실적 ↔ 시장심리
엣지:
  - 금리 상승 → 실적 멀티플 하락 (거시→실적)
  - 실적 어닝 미스 → VIX 상승 (실적→심리)
  - 공포 지수 극단 → 반등 가능성 (심리→거시)
```
- [ ] 관계 엣지 정의 파일 작성
- [ ] MiroFish GraphRAG에 로드

**완료 기준:** 3개 에이전트가 동일 시드 텍스트로 독립적인 분석 텍스트를 반환

---

## Phase 4 — 시뮬레이션 실행 & 확률 추출

**목표:** 시뮬레이션을 자동화하고 롱/숏/중립 확률을 숫자로 추출한다.

### 4-1. 시뮬레이션 오케스트레이터 (`agents/orchestrator.py`)
```python
async def run_simulation(date: str) -> dict:
    seed = seed_builder.build(date)          # Phase 2
    await mirofish.inject_seed(seed)         # MiroFish 시드 주입
    await mirofish.run_simulation(rounds=5)  # 에이전트 토론 5라운드
    report = await mirofish.get_report()     # ReportAgent 결과 수집
    return report_parser.parse(report)       # 확률 추출
```

### 4-2. ReportAgent 출력 파싱 (`mirofish/report_parser.py`)
```
파싱 목표:
  - 각 에이전트의 결론 (강세 / 약세 / 중립)
  - 신뢰도 (에이전트가 언급한 근거 수 / 반대 의견 강도)
  - 핵심 근거 텍스트 (Slack 메시지용)

출력 포맷:
  {
    "long_prob": 0.72,
    "short_prob": 0.18,
    "neutral_prob": 0.10,
    "confidence": 0.72,
    "rationale": "..."
  }
```

### 4-3. 앙상블 가중치 설정
```
초기 가중치 (추후 백테스트로 최적화):
  거시경제 에이전트: 40%
  실적 에이전트:    35%
  심리 에이전트:    25%
```

**완료 기준:** 단일 날짜 입력 → 확률 딕셔너리 정상 반환

---

## Phase 5 — 매매 판단 출력 + Slack

**목표:** 확률을 배팅 크기로 변환하고 Slack으로 전송한다.

### 5-1. 배팅 크기 결정 (`agents/idea_generator.py`)
```python
# 기존 투자 에이전트 시스템의 공식 그대로 적용
BASE_BET = 0.10  # 10%

def calc_position(long_prob, regime_multiplier):
    confidence = long_prob  # 또는 short_prob
    if confidence >= 0.75:
        size = BASE_BET * regime_multiplier * 1.0   # 풀 포지션
    elif confidence >= 0.65:
        size = BASE_BET * regime_multiplier * 0.6
    elif confidence >= 0.55:
        size = BASE_BET * regime_multiplier * 0.3
    else:
        size = 0  # 관망
    return size
```

### 5-2. Slack 메시지 포맷
```
📊 MiroFish 매매 판단 — SPY ETF

방향: 🟢 LONG  |  신뢰도: 72%
포지션 크기: 7.2% (기본 10% × 0.72)

[거시경제] 연준 피벗 기대 + 달러 약세 전환 확인
[실적]     S&P500 어닝 컨센서스 상향 중
[심리]     VIX 14대 안정, RSI 68 과매수 근접 주의

롱 72% / 숏 18% / 중립 10%
```

- [ ] Slack Webhook 전송 함수 (기존 `src/slack/` 재사용)
- [ ] 메시지 포맷터 작성

### 5-3. 스케줄러
- [ ] 매일 장 마감 후 자동 실행 (한국시간 06:00 = NYSE 마감)
- [ ] cron or Python APScheduler

**완료 기준:** 실제 Slack 채널에 메시지 수신 확인

---

## Phase 6 — 백테스트 & 검증

**목표:** 과거 데이터로 시스템 성능을 검증한다.

### 6-1. 백테스트 엔진 (`tests/backtest.py`)
```
기간: 2020~2024 (코로나 크래시, 불장, 금리 인상 사이클 포함)
기준: 매주 월요일 시뮬레이션 실행 → 금요일 청산
지표: 누적 수익률, 샤프 비율, 최대 낙폭(MDD), 승률
```

### 6-2. 벤치마크 비교
```
비교 대상:
  - Buy & Hold SPY
  - RSI 단순 룰 (RSI<30 매수, >70 매도)
  - 본 시스템 (MiroFish 기반)
```

### 6-3. 파라미터 최적화
- [ ] 앙상블 가중치 최적화 (grid search)
- [ ] 신뢰도 임계값 최적화
- [ ] 결과를 `output/backtest_results.md`에 저장

**완료 기준:** 샤프 비율 > 1.0, MDD < 20% (목표치)

---

## 단계별 의존성 & 순서

```
Phase 0  ──────────────────────────────────── 선행 필수
    │
    ▼
Phase 1  (데이터 파이프라인)
    │
    ▼
Phase 2  (시드 변환)  ←────────────── Phase 0의 MiroFish 포맷 분석 결과 필요
    │
    ▼
Phase 3  (에이전트 구성) ←──────────── Phase 0의 구동 확인 필요
    │
    ▼
Phase 4  (시뮬레이션) ←───── Phase 2 + Phase 3 모두 완료 후
    │
    ▼
Phase 5  (출력)
    │
    ▼
Phase 6  (백테스트) ←──────── Phase 1~5 전체 완료 후
```

## 예상 리스크 & 대응

| 리스크 | 대응 |
|--------|------|
| MiroFish 시드 포맷이 문서화 안 돼있을 수 있음 | Phase 0에서 소스 직접 분석, 필요시 저자 Issue 문의 |
| Claude ↔ OpenAI 호환 불일치 | litellm 프록시 우선, 안되면 MiroFish LLM 레이어 직접 패치 |
| Zep Cloud 유료 | 초기엔 in-memory 대체 후 나중에 교체 |
| 40년치 데이터 Alpha Vantage 비용 | yfinance로 SPY 1993~ 무료 수집 가능, Alpha Vantage는 보조 |
| AGPL-3.0 라이선스 | 내부 사용만이면 문제없음, 외부 배포 시 오픈소스 공개 의무 |
| Reddit API 2023 변경 (유료화) | 개인 script 앱은 무료 100 req/min 유지 — 일 1회 배치면 충분 |
| Reddit 과거 데이터 (Pushshift 제한) | HuggingFace/Kaggle 공개 데이터셋으로 백테스트 커버 |
| Reddit 노이즈 비율 높음 | 레이어 1(키워드) + 레이어 2(Claude 배치) 이중 필터로 신호 추출 |
