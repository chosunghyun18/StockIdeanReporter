"""주가 데이터 수집 모듈.

yfinance (국내/해외), FinanceDataReader (국내 보조) 활용.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf


@dataclass(frozen=True)
class StockInfo:
    """종목 기본 정보."""

    ticker: str
    name: str
    market: str  # KR or US
    currency: str
    current_price: float
    prev_close: float
    week_52_high: float
    week_52_low: float
    market_cap: Optional[float]
    volume: Optional[int]


@dataclass(frozen=True)
class PriceHistory:
    """주가 이력 데이터."""

    ticker: str
    df: pd.DataFrame  # columns: Open, High, Low, Close, Volume


class StockDataFetcher:
    """주가 데이터 수집기.

    국내 종목은 ticker에 .KS (KOSPI) 또는 .KQ (KOSDAQ) suffix 사용.
    해외 종목은 티커 그대로 사용 (e.g. AAPL).
    """

    def get_stock_info(self, ticker: str) -> StockInfo:
        """종목 기본 정보 조회.

        Args:
            ticker: 종목 코드 (예: 005930.KS, AAPL)

        Returns:
            StockInfo 객체

        Raises:
            ValueError: 종목 정보를 가져올 수 없는 경우
        """
        stock = yf.Ticker(ticker)
        info = stock.info

        if not info or "regularMarketPrice" not in info and "currentPrice" not in info:
            raise ValueError(f"종목 정보를 가져올 수 없습니다: {ticker}")

        market = "KR" if ticker.endswith((".KS", ".KQ")) else "US"
        current_price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose", 0)

        return StockInfo(
            ticker=ticker,
            name=info.get("longName") or info.get("shortName") or ticker,
            market=market,
            currency=info.get("currency", "KRW" if market == "KR" else "USD"),
            current_price=current_price,
            prev_close=prev_close,
            week_52_high=info.get("fiftyTwoWeekHigh", 0),
            week_52_low=info.get("fiftyTwoWeekLow", 0),
            market_cap=info.get("marketCap"),
            volume=info.get("regularMarketVolume"),
        )

    def get_price_history(
        self,
        ticker: str,
        period_days: int = 365,
    ) -> PriceHistory:
        """주가 이력 데이터 조회.

        Args:
            ticker: 종목 코드
            period_days: 조회 기간 (일)

        Returns:
            PriceHistory 객체

        Raises:
            ValueError: 데이터를 가져올 수 없는 경우
        """
        end = datetime.today()
        start = end - timedelta(days=period_days)

        df = yf.download(
            ticker,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            progress=False,
            auto_adjust=True,
        )

        if df.empty:
            raise ValueError(f"주가 이력을 가져올 수 없습니다: {ticker}")

        # MultiIndex 컬럼 평탄화
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()

        return PriceHistory(ticker=ticker, df=df)

    def get_sector(self, ticker: str) -> str:
        """종목의 섹터 정보 조회.

        Args:
            ticker: 종목 코드

        Returns:
            섹터 문자열 (정보 없으면 'Unknown')
        """
        try:
            info = yf.Ticker(ticker).info
            return info.get("sector") or info.get("sectorDisp") or "Unknown"
        except Exception:
            return "Unknown"

    def get_industry(self, ticker: str) -> str:
        """종목의 산업 정보 조회.

        Args:
            ticker: 종목 코드

        Returns:
            산업 문자열 (정보 없으면 'Unknown')
        """
        try:
            info = yf.Ticker(ticker).info
            return info.get("industry") or info.get("industryDisp") or "Unknown"
        except Exception:
            return "Unknown"
