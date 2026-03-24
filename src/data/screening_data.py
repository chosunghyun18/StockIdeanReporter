"""스크리닝용 배치 가격 데이터 수집 모듈.

다수 종목의 OHLCV 데이터를 청크 단위로 효율적으로 수집한다.
"""
from __future__ import annotations

import logging

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 50   # yfinance API rate limit 방어


class ScreeningDataFetcher:
    """다수 종목의 OHLCV 배치 수집."""

    def fetch_batch(
        self,
        tickers: list[str],
        period_days: int = 60,
    ) -> dict[str, pd.DataFrame]:
        """종목 리스트의 OHLCV 일괄 수집.

        Args:
            tickers: 종목 코드 리스트
            period_days: 수집 기간 (일)

        Returns:
            ticker → OHLCV DataFrame (최소 20행 미만 종목은 제외)
        """
        result: dict[str, pd.DataFrame] = {}
        chunks = [
            tickers[i:i + _CHUNK_SIZE]
            for i in range(0, len(tickers), _CHUNK_SIZE)
        ]

        for chunk in chunks:
            chunk_data = self._fetch_chunk(chunk, period_days)
            result.update(chunk_data)

        logger.info("배치 수집 완료: %d / %d 종목", len(result), len(tickers))
        return result

    def _fetch_chunk(
        self, tickers: list[str], period_days: int
    ) -> dict[str, pd.DataFrame]:
        """단일 청크 다운로드."""
        try:
            raw = yf.download(
                tickers=tickers,
                period=f"{period_days}d",
                auto_adjust=True,
                progress=False,
                threads=True,
            )
        except Exception as e:
            logger.warning("청크 다운로드 실패: %s", e)
            return {}

        if raw.empty:
            return {}

        # 단일 종목이면 MultiIndex 없음
        if len(tickers) == 1:
            df = raw.dropna(how="all")
            return {tickers[0]: df} if len(df) >= 20 else {}

        return self._split_multiindex(raw, tickers)

    @staticmethod
    def _split_multiindex(
        raw: pd.DataFrame, tickers: list[str]
    ) -> dict[str, pd.DataFrame]:
        """MultiIndex DataFrame을 종목별로 분리."""
        result: dict[str, pd.DataFrame] = {}

        if not isinstance(raw.columns, pd.MultiIndex):
            return result

        for ticker in tickers:
            try:
                df = raw.xs(ticker, axis=1, level=1).dropna(how="all")
                if len(df) >= 20:
                    result[ticker] = df
            except (KeyError, Exception):
                pass

        return result
