# MiroFishTrader — 프로젝트 TODO

> MiroFish 군집 AI 기반 S&P500 / SPY ETF 매매 판단 시스템

## MiroFish란?

- GitHub: https://github.com/666ghj/MiroFish
- **다중 에이전트 시뮬레이션 엔진** — 수천 개 AI 에이전트가 각자 장기기억·페르소나·행동논리를 갖고 상호작용
- **GraphRAG** 기반 지식 그래프로 에이전트 관계 구성
- 뉴스/정책/금융 신호 등 **시드 정보**를 주입 → 디지털 세계 자동 구성 → 예측 보고서 생성
- CAMEL-AI의 **OASIS** 시뮬레이션 엔진 위에서 동작
- LLM: OpenAI SDK 호환 (Qwen-plus 권장, **Claude API도 호환 가능**)
- 메모리: **Zep Cloud** (에이전트 장기기억)
- 백엔드: Python 3.11~3.12 + FastAPI / 프론트엔드: Node.js 18+ + Vue
- 라이선스: **AGPL-3.0**

## 프로젝트 개요

MiroFish의 멀티 에이전트 시뮬레이션에 금융 데이터를 시드로 주입하여  
거시경제·실적·시장심리 에이전트들이 토론 → 시나리오별 확률 산출 →  
S&P500 선물 / SPY ETF 매매 판단을 자동 생성하는 시스템.

---

## 파이프라인 7단계

### ① 주가 데이터 수집
- [ ] Alpha Vantage API 연동 (일봉 OHLCV, 40년치)
- [ ] Quandl/Nasdaq Data Link 보조 데이터 연동
- [ ] S&P500 선물 + SPY ETF 기준 데이터 정의
- [ ] 원시 데이터 저장 구조 설계 (Parquet / CSV)

### ② 데이터 정리 및 가공 (Python)
- [ ] 결측값 처리 로직
- [ ] 시계열 정렬 및 리샘플링 (일봉 → 주봉/월봉)
- [ ] 정규화 / 스케일링 파이프라인
- [ ] 거래일 캘린더 처리 (NYSE 기준)

### ③ 매수/매도 시그널 추출
- [ ] RSI (14일)
- [ ] MACD (12/26/9)
- [ ] 볼린저 밴드
- [ ] 거래량 지표 (OBV, VWAP)
- [ ] 시그널 통합 피처 테이블 생성

### ④ AI 입력 형태로 변환
- [ ] 롤링 윈도우 컨텍스트 구성 (예: 252일 = 1년)
- [ ] 피처 벡터화 / 임베딩 설계
- [ ] 프롬프트 템플릿 설계 (AI가 읽을 수 있는 텍스트 형식)
- [ ] 배치 처리 최적화

### ⑤ MiroFish 멀티 에이전트 시뮬레이션 구성
- [ ] MiroFish 로컬 설치 및 구동 확인 (Docker or 소스)
- [ ] LLM 백엔드 설정: Claude API를 OpenAI 호환 엔드포인트로 연결
- [ ] Zep Cloud 메모리 설정 (에이전트 장기기억)
- [ ] **금융 시드 데이터 주입 설계** — ①~③ 결과물을 MiroFish 시드 포맷으로 변환
- [ ] 거시경제 담당 에이전트 페르소나 정의 (Fed 정책, 금리, 경기싸이클)
- [ ] 실적(어닝) 담당 에이전트 페르소나 정의 (EPS, 매출, 가이던스)
- [ ] 시장심리 담당 에이전트 페르소나 정의 (VIX, 공매도 비율, 뉴스 센티먼트)
- [ ] GraphRAG 지식 그래프 구성 (에이전트 간 관계 정의)
- [ ] 에이전트 토론 → 시뮬레이션 실행 자동화

### ⑥ 시나리오별 확률 계산
- [ ] MiroFish ReportAgent 출력 파싱 → 롱/숏/중립 확률 추출
- [ ] 3개 에이전트 결과 앙상블 (가중 투표)
- [ ] 확률 출력 포맷 정의 (롱 %, 숏 %, 중립 %)
- [ ] 신뢰도 임계값 설정 (≥75% 풀포지션 기준 연동)

### ⑦ 최종 매매 판단 출력
- [ ] 포지션 크기 결정 공식 연동 (기존 배팅 Multiplier 공식 활용)
- [ ] S&P500 선물 / SPY ETF 판단 메시지 생성
- [ ] Slack 알림 연동
- [ ] 백테스트 검증 모듈

---

## 기술 스택

| 역할 | 도구 |
|------|------|
| 데이터 수집 | Alpha Vantage, Quandl, yfinance |
| 기술적 분석 | pandas_ta, ta |
| 멀티 에이전트 시뮬레이션 | **MiroFish** (OASIS + GraphRAG) |
| 에이전트 장기기억 | **Zep Cloud** |
| LLM 백엔드 | Claude API (OpenAI 호환 프록시) |
| 지식 그래프 | GraphRAG |
| 오케스트레이션 | Python asyncio + FastAPI |
| 알림 | Slack Webhook |
| 배포 | Docker Compose |

## 주요 통합 포인트 (MiroFish ↔ 이 프로젝트)

```
① 금융 데이터 (OHLCV + 지표)
        ↓  시드 주입 (뉴스/정책/금융 신호 포맷으로 변환)
② MiroFish 시뮬레이션 엔진
   ├── 거시경제 에이전트 (장기기억: Fed 결정 히스토리)
   ├── 실적 에이전트    (장기기억: 어닝 서프라이즈 히스토리)
   └── 심리 에이전트   (장기기억: VIX / 공매도 패턴)
        ↓  GraphRAG 관계 토론
③ ReportAgent → 롱/숏/중립 확률 리포트
        ↓
④ 배팅 크기 결정 → Slack 전송
```

---

## 디렉터리 구조 (예상)

```
MiroFishTrader/
├── data/
│   ├── collector.py      # 데이터 수집
│   └── processor.py      # 정제 및 변환
├── signals/
│   └── indicators.py     # RSI, MACD 등
├── agents/
│   ├── macro_analyst.py  # 거시경제 담당
│   ├── earnings_analyst.py
│   ├── sentiment_analyst.py
│   └── orchestrator.py
├── mirofish/
│   ├── seed_builder.py   # 금융 데이터 → MiroFish 시드 포맷 변환
│   ├── agent_config.py   # 에이전트 페르소나 정의
│   └── report_parser.py  # ReportAgent 출력 → 확률 추출
├── output/
│   └── reporter.py       # Slack 전송
└── TODO.md
```
