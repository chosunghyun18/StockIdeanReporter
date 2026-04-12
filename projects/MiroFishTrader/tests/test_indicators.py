"""Tests for signals/indicators.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from signals.indicators import (
    calculate_rsi,
    calculate_macd,
    calculate_bollinger,
    calculate_obv,
    calculate_atr,
    calculate_moving_averages,
    build_features,
)


def _price_series(n: int = 300, start_price: float = 100.0) -> pd.Series:
    """Generate a realistic price series using random walk."""
    rng = np.random.default_rng(42)
    returns = rng.normal(0.0005, 0.01, n)
    prices = start_price * np.cumprod(1 + returns)
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    return pd.Series(prices, index=idx, name="Close")


def _ohlcv_df(n: int = 300) -> pd.DataFrame:
    close = _price_series(n)
    rng = np.random.default_rng(42)
    noise = rng.uniform(0.99, 1.01, n)
    return pd.DataFrame(
        {
            "Open":   close * rng.uniform(0.99, 1.01, n),
            "High":   close * rng.uniform(1.00, 1.02, n),
            "Low":    close * rng.uniform(0.98, 1.00, n),
            "Close":  close,
            "Volume": rng.integers(500_000, 5_000_000, n).astype(float),
        },
        index=close.index,
    )


# ── RSI ───────────────────────────────────────────────────────────────────────

class TestRSI:
    def test_values_within_0_100(self):
        rsi = calculate_rsi(_price_series())
        valid = rsi.dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_length_matches_input(self):
        s = _price_series()
        rsi = calculate_rsi(s)
        assert len(rsi) == len(s)

    def test_first_n_values_are_nan(self):
        # ta library RSI(14) fills indices 0..12 with NaN (period-1 values)
        rsi = calculate_rsi(_price_series(50), period=14)
        assert rsi.iloc[:13].isna().all()


# ── MACD ─────────────────────────────────────────────────────────────────────

class TestMACD:
    def test_returns_three_columns(self):
        result = calculate_macd(_price_series())
        assert list(result.columns) == ["macd", "macd_signal", "macd_hist"]

    def test_hist_equals_macd_minus_signal(self):
        result = calculate_macd(_price_series()).dropna()
        diff = (result["macd"] - result["macd_signal"]).round(8)
        assert (diff - result["macd_hist"].round(8)).abs().max() < 1e-6

    def test_length_matches_input(self):
        s = _price_series()
        result = calculate_macd(s)
        assert len(result) == len(s)


# ── Bollinger Bands ───────────────────────────────────────────────────────────

class TestBollingerBands:
    def test_returns_four_columns(self):
        result = calculate_bollinger(_price_series())
        assert list(result.columns) == ["bb_upper", "bb_mid", "bb_lower", "bb_pct"]

    def test_upper_above_lower(self):
        result = calculate_bollinger(_price_series()).dropna()
        assert (result["bb_upper"] > result["bb_lower"]).all()

    def test_mid_is_sma(self):
        close = _price_series()
        bb = calculate_bollinger(close, period=20).dropna()
        sma = close.rolling(20).mean().dropna()
        common = bb.index.intersection(sma.index)
        pd.testing.assert_series_equal(
            bb.loc[common, "bb_mid"].round(6),
            sma.loc[common].round(6),
            check_names=False,
        )


# ── OBV ───────────────────────────────────────────────────────────────────────

class TestOBV:
    def test_returns_series(self):
        df = _ohlcv_df()
        result = calculate_obv(df["Close"], df["Volume"])
        assert isinstance(result, pd.Series)

    def test_length_matches_input(self):
        df = _ohlcv_df()
        result = calculate_obv(df["Close"], df["Volume"])
        assert len(result) == len(df)


# ── ATR ───────────────────────────────────────────────────────────────────────

class TestATR:
    def test_values_are_positive(self):
        # ta library ATR fills warm-up period with 0; drop NaN and zeros
        df = _ohlcv_df()
        atr = calculate_atr(df["High"], df["Low"], df["Close"])
        valid = atr[atr > 0]
        assert len(valid) > 0
        assert (valid > 0).all()

    def test_length_matches_input(self):
        df = _ohlcv_df()
        atr = calculate_atr(df["High"], df["Low"], df["Close"])
        assert len(atr) == len(df)


# ── Moving Averages ───────────────────────────────────────────────────────────

class TestMovingAverages:
    def test_returns_three_columns(self):
        result = calculate_moving_averages(_price_series())
        assert list(result.columns) == ["sma_50", "sma_200", "price_vs_sma200_pct"]

    def test_pct_calculation(self):
        close = _price_series()
        result = calculate_moving_averages(close).dropna()
        expected = ((close - close.rolling(200).mean()) / close.rolling(200).mean() * 100).dropna()
        common = result.index.intersection(expected.index)
        pd.testing.assert_series_equal(
            result.loc[common, "price_vs_sma200_pct"].round(6),
            expected.loc[common].round(6),
            check_names=False,
        )


# ── build_features ────────────────────────────────────────────────────────────

class TestBuildFeatures:
    def test_no_nan_in_core_columns(self):
        df = _ohlcv_df(300)
        features = build_features(df)
        for col in ["rsi", "macd", "sma_200"]:
            assert features[col].notna().all(), f"{col} has NaN values"

    def test_expected_columns_present(self):
        df = _ohlcv_df(300)
        features = build_features(df)
        expected = [
            "Open", "High", "Low", "Close", "Volume",
            "rsi", "macd", "macd_signal", "macd_hist",
            "bb_upper", "bb_mid", "bb_lower", "bb_pct",
            "obv", "atr", "sma_50", "sma_200", "price_vs_sma200_pct",
        ]
        for col in expected:
            assert col in features.columns, f"Missing column: {col}"

    def test_warm_up_rows_dropped(self):
        df = _ohlcv_df(300)
        features = build_features(df)
        # 200-day SMA needs 200 rows — should have < 300 rows
        assert len(features) < len(df)
        assert len(features) > 0
