"""주가 분석 에이전트.

기술적/기본적 분석 모듈을 활용하여 Claude API로 종합 보고서 생성.
"""
from __future__ import annotations

import concurrent.futures
import logging
import os
from datetime import date
from pathlib import Path
from typing import Optional

import anthropic

from src.analysis.fundamental import FundamentalAnalyzer
from src.analysis.technical import TechnicalAnalyzer
from src.data.financial_data import FinancialDataFetcher
from src.data.stock_data import StockDataFetcher

logger = logging.getLogger(__name__)

_OUTPUT_DIR = Path("output")
_MODEL = "claude-sonnet-4-6"


class PriceAnalyst:
    """주가 기술적/기본적 분석 에이전트."""

    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        """초기화.

        Args:
            client: Anthropic 클라이언트 (None이면 환경변수 ANTHROPIC_API_KEY 사용)
        """
        self.client = client or anthropic.Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"]
        )
        self.stock_fetcher = StockDataFetcher()
        self.financial_fetcher = FinancialDataFetcher()
        self.tech_analyzer = TechnicalAnalyzer()
        self.fund_analyzer = FundamentalAnalyzer()

    def analyze(self, ticker: str, market: str = "KR") -> str:
        """주가 분석 수행.

        Args:
            ticker: 종목 코드
            market: 시장 구분 (KR/US)

        Returns:
            분석 결과 마크다운 문자열

        Raises:
            ValueError: 데이터를 가져올 수 없는 경우
        """
        today = date.today().strftime("%Y-%m-%d")

        # 데이터 수집 (병렬)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            f_info = executor.submit(self.stock_fetcher.get_stock_info, ticker)
            f_history = executor.submit(self.stock_fetcher.get_price_history, ticker, 365)
            f_fund = executor.submit(self.financial_fetcher.get_fundamentals, ticker)
            f_sector = executor.submit(self.stock_fetcher.get_sector, ticker)
            stock_info = f_info.result()
            price_history = f_history.result()
            fundamental_data = f_fund.result()
            sector = f_sector.result()

        # 분석 수행
        tech_signals = self.tech_analyzer.analyze(price_history.df)
        mdd = self.tech_analyzer.calc_mdd(price_history.df)
        fund_summary = self.fund_analyzer.analyze(
            fundamental_data,
            current_price=stock_info.current_price,
            sector=sector,
        )

        prompt = _build_price_prompt(
            stock_info=stock_info,
            tech_signals=tech_signals,
            fund_summary=fund_summary,
            mdd=mdd,
            market=market,
            date=today,
        )

        logger.info("주가 분석 시작: %s", ticker)

        message = self.client.messages.create(
            model=_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        result = message.content[0].text

        # 결과 저장
        _OUTPUT_DIR.mkdir(exist_ok=True)
        output_path = _OUTPUT_DIR / f"price_analysis_{ticker}_{today}.md"
        output_path.write_text(result, encoding="utf-8")
        logger.info("주가 분석 저장: %s", output_path)

        return result


def _build_price_prompt(
    stock_info: object,
    tech_signals: object,
    fund_summary: object,
    mdd: float,
    market: str,
    date: str,
) -> str:
    """주가 분석 프롬프트 생성."""
    from src.data.stock_data import StockInfo
    from src.analysis.technical import TechnicalSignals
    from src.analysis.fundamental import FundamentalSummary

    info: StockInfo = stock_info  # type: ignore[assignment]
    tech: TechnicalSignals = tech_signals  # type: ignore[assignment]
    fund: FundamentalSummary = fund_summary  # type: ignore[assignment]

    currency = "원" if market == "KR" else "USD"
    market_label = "국내 주식 (KRX)" if market == "KR" else "해외 주식 (NYSE/NASDAQ)"

    tech_data = f"""
기술적 지표:
- 이동평균: MA20={_fmt(tech.ma20, currency)}, MA60={_fmt(tech.ma60, currency)}, MA120={_fmt(tech.ma120, currency)}
- 골든크로스: {"예" if tech.golden_cross else "아니오"}
- RSI(14): {_fmt_num(tech.rsi_14)}
- MACD: {_fmt_num(tech.macd)}, Signal: {_fmt_num(tech.macd_signal)}, Histogram: {_fmt_num(tech.macd_histogram)}
- 볼린저밴드: 상단={_fmt(tech.bb_upper, currency)}, 중간={_fmt(tech.bb_middle, currency)}, 하단={_fmt(tech.bb_lower, currency)}
- BB%: {_fmt_pct(tech.bb_percent)}
- Stochastic: K={_fmt_num(tech.stoch_k)}, D={_fmt_num(tech.stoch_d)}
- ATR(14): {_fmt(tech.atr_14, currency)}
- 거래량 비율(vs MA20): {_fmt_num(tech.volume_ratio)}
- 지지: {_fmt(tech.support, currency)}, 저항: {_fmt(tech.resistance, currency)}
- 피보나치 38.2%: {_fmt(tech.fib_382, currency)}, 61.8%: {_fmt(tech.fib_618, currency)}
- MDD(최대낙폭): {mdd:.1%}
"""

    fund_data = f"""
기본적 분석:
{chr(10).join(f'- {k}: {v}' for k, v in fund.key_metrics.items())}
- 밸류에이션 평가: {fund.valuation}
- 수익성: {fund.profitability}
- 성장성: {fund.growth}
- 재무 건전성: {fund.financial_health}
- 목표가 범위: {_fmt(fund.target_price_low, currency)} ~ {_fmt(fund.target_price_high, currency)}
"""

    return f"""당신은 전문 주가 분석가입니다. 다음 데이터를 바탕으로 종합 주가 분석 보고서를 작성해 주세요.

종목 정보:
- 기업명: {info.name}
- 종목코드: {info.ticker}
- 시장: {market_label}
- 현재가: {info.current_price:,.0f}{currency}
- 52주 최고/최저: {info.week_52_high:,.0f} / {info.week_52_low:,.0f}{currency}
- 시가총액: {_fmt_market_cap(info.market_cap, currency)}
- 분석 기준일: {date}

{tech_data}
{fund_data}

다음 형식으로 보고서를 작성해 주세요:

## 주가 분석 결과

### 종목: {info.name} ({info.ticker})
### 시장: {"KR" if market == "KR" else "US"}
### 분석 기준일: {date}

#### 현재가 정보
[현재가, 52주 최고/최저, 시가총액 등 정리]

#### 기술적 분석
[주요 지표 해석 및 트레이딩 시그널]

#### 기본적 분석
[밸류에이션 및 재무 지표 해석]

#### 리스크 평가
[베타, MDD, 단기/중기/장기 리스크 요인]

#### 종합 판단
- 기술적 신호: 매수/중립/매도
- 밸류에이션: 저평가/적정/고평가
- 목표가 범위: [하단] ~ [상단]{currency}
"""


def _fmt(val: Optional[float], unit: str = "") -> str:
    if val is None:
        return "N/A"
    return f"{val:,.0f}{unit}"


def _fmt_num(val: Optional[float]) -> str:
    if val is None:
        return "N/A"
    return f"{val:.2f}"


def _fmt_pct(val: Optional[float]) -> str:
    if val is None:
        return "N/A"
    return f"{val:.1%}"


def _fmt_market_cap(val: Optional[float], unit: str) -> str:
    if val is None:
        return "N/A"
    if val >= 1_000_000_000_000:
        return f"{val / 1_000_000_000_000:.1f}조{unit}"
    if val >= 100_000_000:
        return f"{val / 100_000_000:.0f}억{unit}"
    if val >= 1_000_000_000:
        return f"{val / 1_000_000_000:.1f}B {unit}"
    return f"{val / 1_000_000:.1f}M {unit}"
