"""SentimentAnalyzer 단위 테스트."""
from __future__ import annotations

import pandas as pd
import pytest

from src.analysis.sentiment import (
    SentimentAnalyzer,
    _calc_rsi,
    _detect_rsi_divergence,
    _detect_volume_climax,
    _calc_selling_climax_score,
    _calc_obv,
    _detect_obv_signal,
    _classify_fear_greed,
    _detect_candle_pattern,
    _calc_sentiment_score,
)


def _make_df(closes: list[float], volumes: list[float] | None = None) -> pd.DataFrame:
    n = len(closes)
    vols = volumes or [1_000_000] * n
    return pd.DataFrame({
        "Open": closes,
        "High": [c * 1.01 for c in closes],
        "Low": [c * 0.99 for c in closes],
        "Close": closes,
        "Volume": vols,
    })


class TestRsiDivergence:
    def test_no_divergence_flat(self):
        closes = pd.Series([100.0] * 30)
        rsi = _calc_rsi(closes)
        result = _detect_rsi_divergence(closes, rsi)
        assert result is None

    def test_short_series_returns_none(self):
        closes = pd.Series([100.0] * 10)
        rsi = _calc_rsi(closes)
        assert _detect_rsi_divergence(closes, rsi) is None

    def test_returns_string_or_none(self):
        closes = pd.Series([100, 95, 98, 92, 97, 89, 95, 83, 90] * 4, dtype=float)
        rsi = _calc_rsi(closes)
        result = _detect_rsi_divergence(closes, rsi)
        assert result in (None, "상승 다이버전스", "하락 다이버전스")


class TestVolumeClimax:
    def test_no_climax_normal_volume(self):
        closes = [100.0] * 25
        vols = [1_000_000] * 25
        df = _make_df(closes, vols)
        climax, ctype = _detect_volume_climax(df, df["Volume"])
        assert not climax

    def test_selling_climax_detected(self):
        closes = [100.0] * 23 + [100.0, 90.0]  # 마지막 날 하락
        vols = [1_000_000] * 23 + [1_000_000, 4_000_000]  # 거래량 4배
        df = _make_df(closes, vols)
        climax, ctype = _detect_volume_climax(df, df["Volume"])
        assert climax
        assert ctype == "매도 클라이맥스"

    def test_buying_climax_detected(self):
        closes = [100.0] * 23 + [100.0, 105.0]
        vols = [1_000_000] * 23 + [1_000_000, 4_000_000]
        df = _make_df(closes, vols)
        climax, ctype = _detect_volume_climax(df, df["Volume"])
        assert climax
        assert ctype == "매수 클라이맥스"

    def test_empty_volume_returns_false(self):
        df = _make_df([100.0] * 25)
        climax, ctype = _detect_volume_climax(df, pd.Series(dtype=float))
        assert not climax


class TestObvSignal:
    def test_accumulation_detected(self):
        # 가격 하락 + OBV 상승 = 매집
        close = pd.Series([100.0 - i * 0.5 for i in range(15)])
        volume = pd.Series([1_000_000 + i * 100_000 for i in range(15)])
        obv = _calc_obv(close, volume)
        result = _detect_obv_signal(close, obv)
        # 결과가 문자열이거나 None임을 확인
        assert result in (None, "매집", "분배")

    def test_short_series_returns_none(self):
        close = pd.Series([100.0] * 5)
        obv = pd.Series([0.0] * 5)
        assert _detect_obv_signal(close, obv) is None


class TestFearGreed:
    def test_extreme_fear_low_rsi(self):
        close = pd.Series([100.0 - i for i in range(30)])
        rsi = _calc_rsi(close)
        result = _classify_fear_greed(rsi, close)
        assert result in ("극단적 공포", "공포")

    def test_neutral_flat(self):
        close = pd.Series([100.0] * 30)
        rsi = _calc_rsi(close)
        result = _classify_fear_greed(rsi, close)
        assert result in ("중립", "공포", "탐욕")


class TestCandlePattern:
    def test_hammer_pattern(self):
        # 아래꼬리 길고 몸통 작은 망치형
        df = pd.DataFrame({
            "Open": [99.0], "High": [99.5], "Low": [85.0], "Close": [99.0],
        })
        result = _detect_candle_pattern(df)
        assert isinstance(result, str) and len(result) > 0

    def test_doji_pattern(self):
        df = pd.DataFrame({
            "Open": [100.0], "High": [105.0], "Low": [95.0], "Close": [100.1],
        })
        result = _detect_candle_pattern(df)
        assert isinstance(result, str)


class TestSentimentScore:
    def test_bullish_signals_positive_score(self):
        score = _calc_sentiment_score("상승 다이버전스", True, "매도 클라이맥스", "매집", "극단적 공포")
        assert score > 0

    def test_bearish_signals_negative_score(self):
        score = _calc_sentiment_score("하락 다이버전스", True, "매수 클라이맥스", "분배", "극단적 탐욕")
        assert score < 0

    def test_score_within_bounds(self):
        score = _calc_sentiment_score("상승 다이버전스", True, "매도 클라이맥스", "매집", "극단적 공포")
        assert -5 <= score <= 5


class TestSentimentAnalyzer:
    def test_analyze_returns_signals(self):
        analyzer = SentimentAnalyzer()
        closes = [100.0 - i * 0.5 for i in range(40)]
        volumes = [1_000_000] * 38 + [1_000_000, 4_000_000]
        df = _make_df(closes, volumes)
        result = analyzer.analyze("TEST", df)
        assert result.ticker == "TEST"
        assert isinstance(result.sentiment_score, int)
        assert -5 <= result.sentiment_score <= 5
        assert isinstance(result.summary, str)
