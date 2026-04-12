"""Tests for mirofish/seed_builder.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mirofish.seed_builder import (
    MarketSnapshot,
    build_macro_seed,
    build_sentiment_seed,
    build_earnings_seed,
    build_all_seeds,
    snapshot_from_features,
    _rsi_label,
    _vix_label,
    _bb_label,
)


def _make_snapshot(**kwargs) -> MarketSnapshot:
    defaults = dict(
        date="2024-03-15",
        spy_close=512.3,
        spy_change_pct=1.2,
        rsi=68.4,
        macd=2.1,
        macd_signal=1.8,
        bb_pct=0.75,
        sma_50=500.0,
        sma_200=480.0,
        price_vs_sma200_pct=6.7,
        vix=14.2,
        tnx=4.35,
        obv_change_pct=2.5,
        atr=5.8,
    )
    defaults.update(kwargs)
    return MarketSnapshot(**defaults)


# ── Label helpers ─────────────────────────────────────────────────────────────

class TestRsiLabel:
    def test_extreme_overbought(self):
        assert "극단" in _rsi_label(76)

    def test_overbought_near(self):
        assert "과매수 근접" in _rsi_label(67)

    def test_neutral(self):
        assert "중립" in _rsi_label(50)

    def test_oversold_near(self):
        assert "과매도" in _rsi_label(33)

    def test_extreme_oversold(self):
        assert "극단" in _rsi_label(20)


class TestVixLabel:
    def test_none_returns_no_data_string(self):
        assert "없음" in _vix_label(None)

    def test_crisis_level(self):
        assert "위기" in _vix_label(45)

    def test_low_volatility(self):
        assert "저변동성" in _vix_label(13)

    def test_normal(self):
        result = _vix_label(20)
        assert "20.0" in result


class TestBbLabel:
    def test_upper_breakout(self):
        assert "상단 돌파" in _bb_label(0.95)

    def test_lower_breakout(self):
        assert "하단 이탈" in _bb_label(0.05)

    def test_middle(self):
        assert "중단" in _bb_label(0.5)


# ── Seed text builders ────────────────────────────────────────────────────────

class TestBuildMacroSeed:
    def test_contains_date(self):
        snap = _make_snapshot()
        text = build_macro_seed(snap)
        assert "2024-03-15" in text

    def test_contains_spy_price(self):
        snap = _make_snapshot(spy_close=512.3)
        text = build_macro_seed(snap)
        assert "512.3" in text

    def test_contains_tnx(self):
        snap = _make_snapshot(tnx=4.35)
        text = build_macro_seed(snap)
        assert "4.35" in text

    def test_none_tnx_handled(self):
        snap = _make_snapshot(tnx=None)
        text = build_macro_seed(snap)
        assert "없음" in text

    def test_none_vix_handled(self):
        snap = _make_snapshot(vix=None)
        text = build_macro_seed(snap)
        assert "없음" in text


class TestBuildSentimentSeed:
    def test_contains_rsi(self):
        snap = _make_snapshot(rsi=68.4)
        text = build_sentiment_seed(snap)
        assert "68.4" in text

    def test_contains_vix(self):
        snap = _make_snapshot(vix=14.2)
        text = build_sentiment_seed(snap)
        assert "14.2" in text

    def test_contains_obv_change(self):
        snap = _make_snapshot(obv_change_pct=5.5)
        text = build_sentiment_seed(snap)
        assert "5.5" in text


class TestBuildEarningsSeed:
    def test_contains_trend_label(self):
        snap = _make_snapshot(price_vs_sma200_pct=8.0)
        text = build_earnings_seed(snap)
        assert "상승 추세" in text

    def test_negative_trend(self):
        snap = _make_snapshot(price_vs_sma200_pct=-12.0)
        text = build_earnings_seed(snap)
        assert "하락 추세" in text


class TestBuildAllSeeds:
    def test_returns_three_keys(self):
        seeds = build_all_seeds(_make_snapshot())
        assert set(seeds.keys()) == {"macro", "sentiment", "earnings"}

    def test_all_seeds_are_non_empty_strings(self):
        seeds = build_all_seeds(_make_snapshot())
        for key, text in seeds.items():
            assert isinstance(text, str) and len(text) > 10, f"{key} seed is empty"

    def test_seeds_have_different_content(self):
        seeds = build_all_seeds(_make_snapshot())
        assert seeds["macro"] != seeds["sentiment"]
        assert seeds["sentiment"] != seeds["earnings"]


# ── snapshot_from_features ────────────────────────────────────────────────────

def _make_features_df(n: int = 250) -> pd.DataFrame:
    """Minimal feature DataFrame mimicking indicators.build_features() output."""
    rng = np.random.default_rng(0)
    idx = pd.date_range("2023-01-01", periods=n, freq="B")
    prices = 400 + np.cumsum(rng.normal(0, 1, n))
    return pd.DataFrame(
        {
            "Open": prices * 0.999,
            "High": prices * 1.005,
            "Low":  prices * 0.995,
            "Close": prices,
            "Volume": rng.integers(1_000_000, 5_000_000, n).astype(float),
            "rsi": rng.uniform(30, 70, n),
            "macd": rng.uniform(-2, 2, n),
            "macd_signal": rng.uniform(-2, 2, n),
            "macd_hist": rng.uniform(-1, 1, n),
            "bb_upper": prices * 1.02,
            "bb_mid":   prices,
            "bb_lower": prices * 0.98,
            "bb_pct":   rng.uniform(0, 1, n),
            "obv":      np.cumsum(rng.normal(0, 1_000_000, n)),
            "atr":      rng.uniform(3, 8, n),
            "sma_50":   prices * 0.99,
            "sma_200":  prices * 0.95,
            "price_vs_sma200_pct": rng.uniform(-5, 10, n),
        },
        index=idx,
    )


class TestSnapshotFromFeatures:
    def test_defaults_to_last_row(self):
        df = _make_features_df()
        snap = snapshot_from_features(df)
        assert snap.date == df.index[-1].strftime("%Y-%m-%d")

    def test_specific_date(self):
        df = _make_features_df()
        target = df.index[100].strftime("%Y-%m-%d")
        snap = snapshot_from_features(df, date=target)
        assert snap.date == target

    def test_vix_injected(self):
        df = _make_features_df()
        vix = pd.Series(20.0, index=df.index)
        snap = snapshot_from_features(df, vix_series=vix)
        assert snap.vix == pytest.approx(20.0)

    def test_tnx_injected(self):
        df = _make_features_df()
        tnx = pd.Series(4.5, index=df.index)
        snap = snapshot_from_features(df, tnx_series=tnx)
        assert snap.tnx == pytest.approx(4.5)

    def test_vix_none_when_not_provided(self):
        df = _make_features_df()
        snap = snapshot_from_features(df)
        assert snap.vix is None

    def test_change_pct_calculated(self):
        df = _make_features_df()
        snap = snapshot_from_features(df, date=df.index[10].strftime("%Y-%m-%d"))
        expected = (df["Close"].iloc[10] - df["Close"].iloc[9]) / df["Close"].iloc[9] * 100
        assert snap.spy_change_pct == pytest.approx(expected, rel=1e-4)
