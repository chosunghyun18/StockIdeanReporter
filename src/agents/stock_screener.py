"""종목 자동 발굴 에이전트.

스윙 매매 관점에서 급락 종목을 자동으로 발굴하고
센티멘트·섹터·경쟁사 분석을 종합해 최종 후보를 순위화한다.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from src.data.universe import UniverseBuilder, UniverseTicker
from src.data.screening_data import ScreeningDataFetcher
from src.analysis.drop_screener import DropScreener, DropCandidate
from src.analysis.sentiment import SentimentAnalyzer, SentimentSignals
from src.analysis.sector_momentum import SectorMomentumAnalyzer, SectorMomentum
from src.analysis.peer_comparator import PeerComparator, PeerComparisonResult

logger = logging.getLogger(__name__)
_OUTPUT_DIR = Path("output")

_WEIGHTS = {"drop": 0.35, "sentiment": 0.25, "sector": 0.20, "peer": 0.20}
_ENRICH_WORKERS = 4
_PRE_FILTER_MULT = 3   # top_n * 배수만큼 심층 분석


@dataclass
class ScreeningCandidate:
    """스크리닝 최종 후보."""

    drop: DropCandidate
    sentiment: Optional[SentimentSignals]
    sector_momentum: Optional[SectorMomentum]
    peer_comparison: Optional[PeerComparisonResult]
    final_score: float
    rank: int = 0
    recommendation: str = ""


@dataclass
class ScreeningResult:
    """스크리닝 전체 결과."""

    screened_at: str
    markets: list[str]
    total_universe: int
    total_candidates: int
    top_candidates: list[ScreeningCandidate]

    def swing_context(self, candidate: ScreeningCandidate) -> str:
        """오케스트레이터에 전달할 스윙 매매 맥락 문자열 생성."""
        d = candidate.drop
        lines = [
            f"[스크리닝 선정 근거] {d.name} ({d.ticker})",
            f"낙폭: 3일 {d.drop_3d}% / 10일 {d.drop_10d}% / 52주고점대비 {d.from_52w_high}%",
            f"신호: {', '.join(d.signals)}",
        ]
        if candidate.sentiment:
            lines.append(f"심리: {candidate.sentiment.summary}")
        if candidate.sector_momentum:
            sm = candidate.sector_momentum
            lines.append(f"섹터({sm.sector}): {sm.trend} (1M {sm.momentum_1m:+.1f}%)")
        if candidate.peer_comparison:
            pc = candidate.peer_comparison
            lines.append(f"밸류에이션: {pc.relative_valuation} (PER할인 {pc.per_discount}%)")
        lines.append(f"스윙 매매 기준: 3~20일 보유, 반등 목표")
        return "\n".join(lines)


class StockScreener:
    """종목 자동 발굴 에이전트."""

    def __init__(self) -> None:
        self._universe = UniverseBuilder()
        self._data = ScreeningDataFetcher()
        self._drop = DropScreener()
        self._sentiment = SentimentAnalyzer()
        self._sector = SectorMomentumAnalyzer()
        self._peer = PeerComparator()

    def screen(
        self, markets: list[str] | None = None, top_n: int = 5
    ) -> ScreeningResult:
        """종목 자동 발굴 실행.

        Args:
            markets: ["KR"], ["US"], ["KR", "US"] (None이면 ["KR", "US"])
            top_n: 최종 선정 종목 수

        Returns:
            ScreeningResult
        """
        markets = markets or ["KR", "US"]
        logger.info("스크리닝 시작: %s (top %d)", markets, top_n)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        universe = self._universe.build(markets)
        tickers = [u.ticker for u in universe]
        market_map = {u.ticker: u.market for u in universe}
        name_map = {u.ticker: u.name for u in universe}

        price_data = self._data.fetch_batch(tickers, period_days=60)
        drop_candidates = self._drop.screen(price_data, market_map, name_map)
        logger.info("급락 후보: %d 종목", len(drop_candidates))

        if not drop_candidates:
            return ScreeningResult(
                screened_at=now, markets=markets,
                total_universe=len(universe), total_candidates=0, top_candidates=[],
            )

        pre = drop_candidates[:min(top_n * _PRE_FILTER_MULT, 20)]
        enriched = self._enrich_parallel(pre, price_data)
        ranked = self._rank(enriched, top_n)
        self._save(ranked, now)

        return ScreeningResult(
            screened_at=now,
            markets=markets,
            total_universe=len(universe),
            total_candidates=len(drop_candidates),
            top_candidates=ranked,
        )

    # ── 심층 분석 (병렬) ─────────────────────────────────────────

    def _enrich_parallel(
        self,
        candidates: list[DropCandidate],
        price_data: dict[str, pd.DataFrame],
    ) -> list[ScreeningCandidate]:
        results: list[ScreeningCandidate] = []
        with ThreadPoolExecutor(max_workers=_ENRICH_WORKERS) as executor:
            futures = {
                executor.submit(self._enrich_one, c, price_data): c
                for c in candidates
            }
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    logger.debug("심층 분석 실패: %s", e)
        return results

    def _enrich_one(
        self, drop: DropCandidate, price_data: dict[str, pd.DataFrame]
    ) -> ScreeningCandidate:
        df = price_data.get(drop.ticker)
        sentiment = self._sentiment.analyze(drop.ticker, df) if df is not None else None

        sector_info: Optional[SectorMomentum] = None
        peer_info: Optional[PeerComparisonResult] = None

        try:
            import yfinance as yf
            sector = yf.Ticker(drop.ticker).info.get("sector", "")
            if sector:
                sector_info = self._sector.analyze(sector, drop.market)
        except Exception:
            pass

        try:
            peer_info = self._peer.compare(drop.ticker, drop.market)
        except Exception:
            pass

        score = _calc_final_score(drop, sentiment, sector_info, peer_info)
        rec = _recommend(score)

        return ScreeningCandidate(
            drop=drop,
            sentiment=sentiment,
            sector_momentum=sector_info,
            peer_comparison=peer_info,
            final_score=round(score, 3),
            recommendation=rec,
        )

    def _rank(
        self, candidates: list[ScreeningCandidate], top_n: int
    ) -> list[ScreeningCandidate]:
        ranked = sorted(candidates, key=lambda c: c.final_score, reverse=True)[:top_n]
        for i, c in enumerate(ranked):
            c.rank = i + 1
        return ranked

    def _save(self, candidates: list[ScreeningCandidate], timestamp: str) -> None:
        _OUTPUT_DIR.mkdir(exist_ok=True)
        date_str = timestamp[:10]
        path = _OUTPUT_DIR / f"screening_{date_str}.md"
        lines = [f"# 스크리닝 결과 ({timestamp})\n\n"]
        for c in candidates:
            d = c.drop
            lines.append(
                f"## {c.rank}. {d.name} ({d.ticker})\n"
                f"- **{c.recommendation}** (점수: {c.final_score:.3f})\n"
                f"- 낙폭: 3일 {d.drop_3d}% / 10일 {d.drop_10d}% / 52주고점 {d.from_52w_high}%\n"
                f"- RSI: {d.rsi} | BB: {d.bb_pct} | 거래량: {d.volume_ratio}x\n"
                f"- 신호: {', '.join(d.signals)}\n"
            )
            if c.sentiment:
                lines.append(f"- 심리: {c.sentiment.summary}\n")
            lines.append("\n")
        path.write_text("".join(lines), encoding="utf-8")
        logger.info("스크리닝 결과 저장: %s", path)


# ── 점수 계산 (모듈 레벨) ────────────────────────────────────────

def _calc_final_score(
    drop: DropCandidate,
    sentiment: Optional[SentimentSignals],
    sector: Optional[SectorMomentum],
    peer: Optional[PeerComparisonResult],
) -> float:
    drop_score = min(drop.drop_score / 10.0, 1.0)
    sent_score = (sentiment.sentiment_score + 5) / 10.0 if sentiment else 0.5
    sec_score = max(0.0, (5.0 - sector.momentum_1m) / 10.0) if sector else 0.5
    if peer and peer.per_discount is not None:
        peer_score = max(0.0, min(1.0, (-peer.per_discount + 30) / 60.0))
    else:
        peer_score = 0.5

    return (
        drop_score * _WEIGHTS["drop"]
        + sent_score * _WEIGHTS["sentiment"]
        + sec_score * _WEIGHTS["sector"]
        + peer_score * _WEIGHTS["peer"]
    )


def _recommend(score: float) -> str:
    if score >= 0.65:
        return "강력 매수 후보"
    if score >= 0.50:
        return "매수 후보"
    return "관망"
