"""동종업계 경쟁사 밸류에이션 비교 모듈.

PER/PBR/ROE를 동종업계 중앙값과 비교하여 상대적 저평가 여부를 평가한다.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from statistics import median
from typing import Optional

import pandas as pd
import yfinance as yf

from src.data.financial_data import FinancialDataFetcher

logger = logging.getLogger(__name__)

_MAX_PEERS = 6


@dataclass(frozen=True)
class PeerComparisonResult:
    """경쟁사 비교 결과."""

    ticker: str
    sector: str
    industry: str
    peers: list[str]
    peer_names: list[str]
    peer_avg_per: Optional[float]
    peer_avg_pbr: Optional[float]
    peer_avg_roe: Optional[float]
    target_per: Optional[float]
    target_pbr: Optional[float]
    target_roe: Optional[float]
    per_discount: Optional[float]    # 음수 = 저평가
    pbr_discount: Optional[float]
    relative_strength_1m: float      # 동종업계 대비 1개월 상대 강도
    relative_valuation: str          # "저평가" / "적정" / "고평가" / "데이터 부족"


class PeerComparator:
    """동종업계 밸류에이션 비교 분석."""

    def __init__(self) -> None:
        self._fetcher = FinancialDataFetcher()

    def compare(self, ticker: str, market: str) -> PeerComparisonResult:
        """동종업계 비교 분석 실행.

        Args:
            ticker: 종목 코드
            market: "KR" / "US"

        Returns:
            PeerComparisonResult
        """
        try:
            info = yf.Ticker(ticker).info
        except Exception:
            info = {}

        sector = info.get("sector", "Unknown")
        industry = info.get("industry", "Unknown")

        peers = self._find_peers(ticker, sector, market)
        target = self._fetcher.get_fundamentals(ticker)
        peer_data = [self._fetcher.get_fundamentals(p) for p in peers]
        peer_data = [d for d in peer_data if d is not None]

        peer_avg_per = _safe_median([d.trailing_pe for d in peer_data if d.trailing_pe])
        peer_avg_pbr = _safe_median([d.price_to_book for d in peer_data if d.price_to_book])
        peer_avg_roe = _safe_median([d.return_on_equity for d in peer_data if d.return_on_equity])

        per_disc = _discount(target.trailing_pe, peer_avg_per)
        pbr_disc = _discount(target.price_to_book, peer_avg_pbr)
        rel_val = _assess_valuation(per_disc, pbr_disc)
        rs_1m = _calc_relative_strength(ticker, peers)
        peer_names = _fetch_names(peers[:4])

        return PeerComparisonResult(
            ticker=ticker,
            sector=sector,
            industry=industry,
            peers=peers,
            peer_names=peer_names,
            peer_avg_per=peer_avg_per,
            peer_avg_pbr=peer_avg_pbr,
            peer_avg_roe=peer_avg_roe,
            target_per=target.trailing_pe,
            target_pbr=target.price_to_book,
            target_roe=target.return_on_equity,
            per_discount=per_disc,
            pbr_discount=pbr_disc,
            relative_strength_1m=rs_1m,
            relative_valuation=rel_val,
        )

    def _find_peers(self, ticker: str, sector: str, market: str) -> list[str]:
        if market == "KR":
            return _find_kr_peers(ticker)
        return _find_us_peers(ticker, sector)


# ── 피어 탐색 ────────────────────────────────────────────────────

def _find_us_peers(ticker: str, sector: str) -> list[str]:
    """US 시장: S&P500 내 같은 섹터 종목."""
    try:
        table = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            attrs={"id": "constituents"},
        )[0]
        peers = [
            str(row["Symbol"]).replace(".", "-")
            for _, row in table.iterrows()
            if row.get("GICS Sector") == sector
            and str(row["Symbol"]).replace(".", "-") != ticker
        ]
        return peers[:_MAX_PEERS]
    except Exception:
        return []


def _find_kr_peers(ticker: str) -> list[str]:
    """KR 시장: KOSPI 시총 상위 종목 (업종 분리 불가 시 대형주 폴백)."""
    try:
        from pykrx import stock as krx
        today = pd.Timestamp.today().strftime("%Y%m%d")
        df = krx.get_market_cap(today, market="KOSPI")
        if df.empty:
            return []
        base = ticker.replace(".KS", "").replace(".KQ", "")
        codes = [
            f"{code}.KS"
            for code in df.sort_values("시가총액", ascending=False).index
            if str(code) != base
        ]
        return codes[:_MAX_PEERS]
    except Exception:
        return []


# ── 계산 헬퍼 ────────────────────────────────────────────────────

def _safe_median(values: list[Optional[float]]) -> Optional[float]:
    clean = [v for v in values if v and 0 < v < 1000]
    if not clean:
        return None
    return round(median(clean), 2)


def _discount(target: Optional[float], peer_avg: Optional[float]) -> Optional[float]:
    if target is None or peer_avg is None or peer_avg == 0:
        return None
    return round((target - peer_avg) / peer_avg * 100, 1)


def _assess_valuation(
    per_disc: Optional[float], pbr_disc: Optional[float]
) -> str:
    discounts = [d for d in [per_disc, pbr_disc] if d is not None]
    if not discounts:
        return "데이터 부족"
    avg = sum(discounts) / len(discounts)
    if avg < -20:
        return "저평가"
    if avg > 20:
        return "고평가"
    return "적정"


def _calc_relative_strength(ticker: str, peers: list[str]) -> float:
    """1개월 상대 강도 = 대상 수익률 - 동종업계 평균 수익률."""
    all_tickers = [ticker] + peers[:4]
    try:
        raw = yf.download(all_tickers, period="1mo", auto_adjust=True, progress=False)
        close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
        if close.empty:
            return 0.0
        returns = (close.iloc[-1] - close.iloc[0]) / close.iloc[0] * 100
        target_ret = float(returns[ticker]) if ticker in returns else 0.0
        peer_rets = [float(returns[p]) for p in peers[:4] if p in returns]
        peer_avg = sum(peer_rets) / len(peer_rets) if peer_rets else 0.0
        return round(target_ret - peer_avg, 2)
    except Exception:
        return 0.0


def _fetch_names(tickers: list[str]) -> list[str]:
    names: list[str] = []
    for t in tickers:
        try:
            name = yf.Ticker(t).info.get("shortName", t)
            names.append(str(name))
        except Exception:
            names.append(t)
    return names
