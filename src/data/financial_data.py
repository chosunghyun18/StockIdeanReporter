"""재무 데이터 수집 모듈.

국내: pykrx + yfinance
해외: yfinance
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import yfinance as yf


@dataclass(frozen=True)
class FundamentalData:
    """기본적 분석 재무 데이터."""

    ticker: str
    # 밸류에이션
    per: Optional[float]
    pbr: Optional[float]
    ev_ebitda: Optional[float]
    psr: Optional[float]
    # 수익성
    roe: Optional[float]
    roa: Optional[float]
    operating_margin: Optional[float]
    net_margin: Optional[float]
    # 성장성
    revenue_growth: Optional[float]
    earnings_growth: Optional[float]
    # 재무 건전성
    debt_to_equity: Optional[float]
    current_ratio: Optional[float]
    interest_coverage: Optional[float]
    # 배당
    dividend_yield: Optional[float]
    payout_ratio: Optional[float]
    # EPS
    eps: Optional[float]
    forward_eps: Optional[float]


class FinancialDataFetcher:
    """재무 데이터 수집기."""

    def get_fundamentals(self, ticker: str) -> FundamentalData:
        """종목 기본적 분석 데이터 조회.

        Args:
            ticker: 종목 코드 (예: 005930.KS, AAPL)

        Returns:
            FundamentalData 객체

        Raises:
            ValueError: 데이터를 가져올 수 없는 경우
        """
        try:
            info = yf.Ticker(ticker).info
        except Exception as e:
            raise ValueError(f"재무 데이터 조회 실패: {ticker}, {e}") from e

        def safe_float(key: str) -> Optional[float]:
            val = info.get(key)
            if val is None or val == "Infinity" or val != val:  # NaN check
                return None
            try:
                return float(val)
            except (TypeError, ValueError):
                return None

        return FundamentalData(
            ticker=ticker,
            per=safe_float("trailingPE"),
            pbr=safe_float("priceToBook"),
            ev_ebitda=safe_float("enterpriseToEbitda"),
            psr=safe_float("priceToSalesTrailing12Months"),
            roe=safe_float("returnOnEquity"),
            roa=safe_float("returnOnAssets"),
            operating_margin=safe_float("operatingMargins"),
            net_margin=safe_float("profitMargins"),
            revenue_growth=safe_float("revenueGrowth"),
            earnings_growth=safe_float("earningsGrowth"),
            debt_to_equity=safe_float("debtToEquity"),
            current_ratio=safe_float("currentRatio"),
            interest_coverage=safe_float("interestCoverage") if "interestCoverage" in info else None,
            dividend_yield=safe_float("dividendYield"),
            payout_ratio=safe_float("payoutRatio"),
            eps=safe_float("trailingEps"),
            forward_eps=safe_float("forwardEps"),
        )

    def get_income_statement_summary(self, ticker: str) -> dict:
        """최근 손익계산서 요약.

        Args:
            ticker: 종목 코드

        Returns:
            손익계산서 주요 항목 딕셔너리
        """
        try:
            stock = yf.Ticker(ticker)
            income = stock.income_stmt
            if income is None or income.empty:
                return {}

            latest = income.iloc[:, 0]
            return {
                "total_revenue": _safe_val(latest, "Total Revenue"),
                "gross_profit": _safe_val(latest, "Gross Profit"),
                "operating_income": _safe_val(latest, "Operating Income"),
                "net_income": _safe_val(latest, "Net Income"),
            }
        except Exception:
            return {}

    def get_balance_sheet_summary(self, ticker: str) -> dict:
        """최근 대차대조표 요약.

        Args:
            ticker: 종목 코드

        Returns:
            대차대조표 주요 항목 딕셔너리
        """
        try:
            stock = yf.Ticker(ticker)
            balance = stock.balance_sheet
            if balance is None or balance.empty:
                return {}

            latest = balance.iloc[:, 0]
            return {
                "total_assets": _safe_val(latest, "Total Assets"),
                "total_liabilities": _safe_val(latest, "Total Liabilities Net Minority Interest"),
                "stockholders_equity": _safe_val(latest, "Stockholders Equity"),
                "cash": _safe_val(latest, "Cash And Cash Equivalents"),
                "total_debt": _safe_val(latest, "Total Debt"),
            }
        except Exception:
            return {}


def _safe_val(series: object, key: str) -> Optional[float]:
    """시리즈에서 안전하게 값 추출."""
    try:
        val = series[key]  # type: ignore[index]
        if val is None or val != val:
            return None
        return float(val)
    except (KeyError, TypeError, ValueError):
        return None
