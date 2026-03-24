"""종목 유니버스 구성 모듈.

KOSPI/KOSDAQ/S&P500/NASDAQ100 시총 상위 종목 리스트를 제공한다.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

logger = logging.getLogger(__name__)

_KR_UNIVERSE_SIZE = 300   # 시총 상위 N개 (API 부하 방어)
_US_UNIVERSE_SIZE = 200


@dataclass(frozen=True)
class UniverseTicker:
    """유니버스 종목 정보."""

    ticker: str     # 005930.KS, AAPL
    market: str     # KR, US
    exchange: str   # KOSPI, KOSDAQ, NYSE/NASDAQ
    name: str


class UniverseBuilder:
    """시장별 종목 유니버스 구성."""

    def build(self, markets: list[str]) -> list[UniverseTicker]:
        """지정 시장의 유니버스 종목 리스트 반환.

        Args:
            markets: ["KR"], ["US"], 또는 ["KR", "US"]

        Returns:
            UniverseTicker 리스트
        """
        result: list[UniverseTicker] = []
        for market in markets:
            if market == "KR":
                result.extend(self._get_kr_universe())
            elif market == "US":
                result.extend(self._get_us_universe())
        logger.info("유니버스 구성 완료: %d 종목", len(result))
        return result

    def _get_kr_universe(self) -> list[UniverseTicker]:
        """KOSPI/KOSDAQ 시총 상위 종목."""
        try:
            from pykrx import stock as krx
        except ImportError:
            logger.warning("pykrx 미설치 — KR 유니버스 스킵")
            return self._get_kr_fallback()

        tickers: list[UniverseTicker] = []
        today = pd.Timestamp.today().strftime("%Y%m%d")

        for exchange in ["KOSPI", "KOSDAQ"]:
            try:
                df = krx.get_market_cap(today, market=exchange)
                if df.empty:
                    continue
                df = df.sort_values("시가총액", ascending=False).head(_KR_UNIVERSE_SIZE // 2)
                suffix = ".KS" if exchange == "KOSPI" else ".KQ"
                for code, row in df.iterrows():
                    tickers.append(UniverseTicker(
                        ticker=f"{code}{suffix}",
                        market="KR",
                        exchange=exchange,
                        name=str(row.get("종목명", code)),
                    ))
            except Exception as e:
                logger.error("KR 유니버스 수집 실패 (%s): %s", exchange, e)

        return tickers or self._get_kr_fallback()

    @staticmethod
    def _get_kr_fallback() -> list[UniverseTicker]:
        """pykrx 불가 시 대표 종목 하드코딩 폴백."""
        stocks = [
            ("005930.KS", "KOSPI", "삼성전자"),
            ("000660.KS", "KOSPI", "SK하이닉스"),
            ("035420.KS", "KOSPI", "NAVER"),
            ("005380.KS", "KOSPI", "현대차"),
            ("051910.KS", "KOSPI", "LG화학"),
            ("006400.KS", "KOSPI", "삼성SDI"),
            ("035720.KS", "KOSPI", "카카오"),
            ("068270.KS", "KOSPI", "셀트리온"),
            ("028260.KS", "KOSPI", "삼성물산"),
            ("207940.KS", "KOSPI", "삼성바이오로직스"),
        ]
        return [
            UniverseTicker(ticker=t, market="KR", exchange=ex, name=n)
            for t, ex, n in stocks
        ]

    def _get_us_universe(self) -> list[UniverseTicker]:
        """S&P500 + NASDAQ100 종목 (중복 제거)."""
        tickers: list[UniverseTicker] = []
        tickers.extend(self._get_sp500())
        tickers.extend(self._get_nasdaq100())

        seen: set[str] = set()
        unique: list[UniverseTicker] = []
        for t in tickers:
            if t.ticker not in seen:
                seen.add(t.ticker)
                unique.append(t)
        return unique[:_US_UNIVERSE_SIZE]

    def _get_sp500(self) -> list[UniverseTicker]:
        try:
            table = pd.read_html(
                "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
                attrs={"id": "constituents"},
            )[0]
            return [
                UniverseTicker(
                    ticker=str(row["Symbol"]).replace(".", "-"),
                    market="US",
                    exchange="NYSE/NASDAQ",
                    name=str(row["Security"]),
                )
                for _, row in table.iterrows()
            ]
        except Exception as e:
            logger.error("S&P500 유니버스 수집 실패: %s", e)
            return self._get_us_fallback()

    def _get_nasdaq100(self) -> list[UniverseTicker]:
        try:
            tables = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")
            for table in tables:
                if "Ticker" in table.columns and "Company" in table.columns:
                    return [
                        UniverseTicker(
                            ticker=str(row["Ticker"]),
                            market="US",
                            exchange="NASDAQ",
                            name=str(row["Company"]),
                        )
                        for _, row in table.iterrows()
                    ]
        except Exception as e:
            logger.error("NASDAQ100 유니버스 수집 실패: %s", e)
        return []

    @staticmethod
    def _get_us_fallback() -> list[UniverseTicker]:
        """Wikipedia 접근 불가 시 대표 종목 폴백."""
        stocks = [
            ("AAPL", "Apple Inc."), ("MSFT", "Microsoft"), ("NVDA", "NVIDIA"),
            ("GOOGL", "Alphabet"), ("AMZN", "Amazon"), ("META", "Meta"),
            ("TSLA", "Tesla"), ("AVGO", "Broadcom"), ("JPM", "JPMorgan"),
            ("LLY", "Eli Lilly"), ("V", "Visa"), ("UNH", "UnitedHealth"),
        ]
        return [
            UniverseTicker(ticker=t, market="US", exchange="NYSE/NASDAQ", name=n)
            for t, n in stocks
        ]
