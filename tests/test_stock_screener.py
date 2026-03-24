"""StockScreener 단위 테스트."""
from __future__ import annotations

import pytest

from src.agents.stock_screener import (
    ScreeningCandidate,
    ScreeningResult,
    _calc_final_score,
    _recommend,
)
from src.analysis.drop_screener import DropCandidate
from src.analysis.sentiment import SentimentSignals
from src.analysis.sector_momentum import SectorMomentum


def _make_drop(ticker: str = "TEST", drop_score: float = 5.0) -> DropCandidate:
    return DropCandidate(
        ticker=ticker, market="KR", name="테스트",
        drop_3d=-6.0, drop_10d=-12.0, drop_20d=-10.0,
        from_52w_high=-25.0, rsi=30.0, bb_pct=0.1,
        stoch_k=20.0, volume_ratio=3.0,
        drop_score=drop_score,
        signals=["RSI 과매도(30.0)", "거래량급증(3.0x)"],
    )


def _make_sentiment(score: int = 3) -> SentimentSignals:
    return SentimentSignals(
        ticker="TEST",
        rsi_divergence="상승 다이버전스",
        volume_climax=True,
        climax_type="매도 클라이맥스",
        selling_climax_score=0.8,
        obv_signal="매집",
        fear_greed="극단적 공포",
        candle_pattern="망치형 (반등 신호)",
        sentiment_score=score,
        summary="심리: 극단적 공포 | RSI 상승 다이버전스",
    )


def _make_sector(momentum_1m: float = -5.0) -> SectorMomentum:
    return SectorMomentum(
        sector="Technology", market="KR", etf_ticker="XLK",
        momentum_1m=momentum_1m, momentum_3m=-10.0,
        relative_to_index=-3.0, trend="약세",
    )


class TestCalcFinalScore:
    def test_returns_float_in_range(self):
        drop = _make_drop(drop_score=5.0)
        score = _calc_final_score(drop, None, None, None)
        assert 0.0 <= score <= 1.0

    def test_positive_sentiment_increases_score(self):
        drop = _make_drop()
        score_no_sent = _calc_final_score(drop, None, None, None)
        score_with_sent = _calc_final_score(drop, _make_sentiment(5), None, None)
        assert score_with_sent > score_no_sent

    def test_weak_sector_increases_score(self):
        drop = _make_drop()
        score_strong = _calc_final_score(drop, None, _make_sector(momentum_1m=10.0), None)
        score_weak = _calc_final_score(drop, None, _make_sector(momentum_1m=-8.0), None)
        assert score_weak > score_strong

    def test_all_bullish_signals_high_score(self):
        drop = _make_drop(drop_score=8.0)
        sent = _make_sentiment(5)
        sect = _make_sector(-8.0)
        score = _calc_final_score(drop, sent, sect, None)
        assert score > 0.6


class TestRecommend:
    def test_strong_buy(self):
        assert _recommend(0.70) == "강력 매수 후보"

    def test_buy(self):
        assert _recommend(0.55) == "매수 후보"

    def test_watch(self):
        assert _recommend(0.40) == "관망"

    def test_boundary_065(self):
        assert _recommend(0.65) == "강력 매수 후보"

    def test_boundary_050(self):
        assert _recommend(0.50) == "매수 후보"


class TestScreeningResult:
    def _make_candidate(self) -> ScreeningCandidate:
        return ScreeningCandidate(
            drop=_make_drop(),
            sentiment=_make_sentiment(),
            sector_momentum=_make_sector(),
            peer_comparison=None,
            final_score=0.65,
            rank=1,
            recommendation="강력 매수 후보",
        )

    def test_swing_context_contains_ticker(self):
        result = ScreeningResult(
            screened_at="2026-03-24 12:00",
            markets=["KR"],
            total_universe=100,
            total_candidates=3,
            top_candidates=[],
        )
        candidate = self._make_candidate()
        context = result.swing_context(candidate)
        assert "TEST" in context
        assert "스윙 매매" in context

    def test_swing_context_contains_sentiment(self):
        result = ScreeningResult(
            screened_at="2026-03-24 12:00",
            markets=["KR"],
            total_universe=100,
            total_candidates=3,
            top_candidates=[],
        )
        candidate = self._make_candidate()
        context = result.swing_context(candidate)
        assert "심리" in context
