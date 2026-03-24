"""섹터 모멘텀 분석 모듈.

섹터 대표 ETF의 수익률로 업황 방향을 평가한다.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

_US_SECTOR_ETFS: dict[str, str] = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financial Services": "XLF",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Industrials": "XLI",
    "Energy": "XLE",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Basic Materials": "XLB",
    "Communication Services": "XLC",
}

_KR_SECTOR_ETFS: dict[str, str] = {
    "반도체": "091160.KS",
    "2차전지": "305720.KS",
    "바이오": "244580.KS",
    "자동차": "091180.KS",
    "금융": "139270.KS",
    "에너지화학": "117460.KS",
    "철강소재": "117480.KS",
    "건설": "117490.KS",
}

_INDEX_ETF = {"US": "SPY", "KR": "069500.KS"}


@dataclass(frozen=True)
class SectorMomentum:
    """섹터 모멘텀 분석 결과."""

    sector: str
    market: str
    etf_ticker: str
    momentum_1m: float      # 1개월 수익률 (%)
    momentum_3m: float      # 3개월 수익률 (%)
    relative_to_index: float  # 지수 대비 초과 수익률 (%)
    trend: str              # "강세" / "중립" / "약세"


class SectorMomentumAnalyzer:
    """섹터 ETF 기반 모멘텀 분석."""

    def analyze(self, sector: str, market: str) -> Optional[SectorMomentum]:
        """단일 섹터 모멘텀 분석.

        Args:
            sector: 섹터명 (yfinance info['sector'] 기준)
            market: "KR" / "US"

        Returns:
            SectorMomentum 또는 None (ETF 없거나 데이터 부족)
        """
        etf = self._get_etf(sector, market)
        if not etf:
            return None
        index_etf = _INDEX_ETF.get(market, "SPY")
        return self._calc_momentum(sector, market, etf, index_etf)

    def _calc_momentum(
        self, sector: str, market: str, etf: str, index_etf: str
    ) -> Optional[SectorMomentum]:
        try:
            raw = yf.download(
                [etf, index_etf],
                period="3mo",
                auto_adjust=True,
                progress=False,
            )
        except Exception as e:
            logger.debug("섹터 ETF 수집 실패 (%s): %s", etf, e)
            return None

        try:
            close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
            etf_close = close[etf].dropna() if etf in close.columns else None
            idx_close = close[index_etf].dropna() if index_etf in close.columns else None

            if etf_close is None or len(etf_close) < 20:
                return None

            m1 = _pct_change(etf_close, 21)
            m3 = _pct_change(etf_close, len(etf_close))
            idx_m1 = _pct_change(idx_close, 21) if idx_close is not None else 0.0
            relative = m1 - idx_m1
            trend = "강세" if m1 > 2.0 else ("약세" if m1 < -2.0 else "중립")

            return SectorMomentum(
                sector=sector,
                market=market,
                etf_ticker=etf,
                momentum_1m=round(m1, 2),
                momentum_3m=round(m3, 2),
                relative_to_index=round(relative, 2),
                trend=trend,
            )
        except Exception as e:
            logger.debug("모멘텀 계산 실패 (%s): %s", etf, e)
            return None

    @staticmethod
    def _get_etf(sector: str, market: str) -> Optional[str]:
        if market == "US":
            return _US_SECTOR_ETFS.get(sector)
        return _KR_SECTOR_ETFS.get(sector)


def _pct_change(series: pd.Series, lookback: int) -> float:
    if len(series) < 2:
        return 0.0
    idx = min(lookback, len(series) - 1)
    base = float(series.iloc[-idx - 1])
    if base == 0:
        return 0.0
    return float((series.iloc[-1] - base) / base * 100)
