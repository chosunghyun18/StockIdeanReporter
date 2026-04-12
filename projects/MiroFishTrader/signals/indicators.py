"""Technical indicators for market analysis.

Calculates RSI, MACD, Bollinger Bands, OBV, ATR, and moving averages
using the `ta` library. Returns a unified feature DataFrame.
"""

from __future__ import annotations

import pandas as pd
import ta.momentum
import ta.trend
import ta.volatility
import ta.volume


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index.

    Args:
        close: Close price series.
        period: RSI lookback period.

    Returns:
        RSI series (0–100).
    """
    return ta.momentum.RSIIndicator(close=close, window=period).rsi()


def calculate_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """MACD indicator.

    Args:
        close: Close price series.
        fast: Fast EMA period.
        slow: Slow EMA period.
        signal: Signal line period.

    Returns:
        DataFrame with columns [macd, macd_signal, macd_hist].
    """
    ind = ta.trend.MACD(close=close, window_fast=fast, window_slow=slow, window_sign=signal)
    return pd.DataFrame(
        {
            "macd":        ind.macd(),
            "macd_signal": ind.macd_signal(),
            "macd_hist":   ind.macd_diff(),
        },
        index=close.index,
    )


def calculate_bollinger(
    close: pd.Series,
    period: int = 20,
    std: float = 2.0,
) -> pd.DataFrame:
    """Bollinger Bands.

    Args:
        close: Close price series.
        period: Rolling window.
        std: Standard deviation multiplier.

    Returns:
        DataFrame with columns [bb_upper, bb_mid, bb_lower, bb_pct].
    """
    ind = ta.volatility.BollingerBands(close=close, window=period, window_dev=std)
    return pd.DataFrame(
        {
            "bb_upper": ind.bollinger_hband(),
            "bb_mid":   ind.bollinger_mavg(),
            "bb_lower": ind.bollinger_lband(),
            "bb_pct":   ind.bollinger_pband(),
        },
        index=close.index,
    )


def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume.

    Args:
        close: Close price series.
        volume: Volume series.

    Returns:
        OBV series.
    """
    return ta.volume.OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """Average True Range (volatility measure).

    Args:
        high: High price series.
        low: Low price series.
        close: Close price series.
        period: ATR lookback period.

    Returns:
        ATR series.
    """
    return ta.volatility.AverageTrueRange(
        high=high, low=low, close=close, window=period
    ).average_true_range()


def calculate_moving_averages(close: pd.Series) -> pd.DataFrame:
    """50-day and 200-day simple moving averages.

    Args:
        close: Close price series.

    Returns:
        DataFrame with columns [sma_50, sma_200, price_vs_sma200_pct].
    """
    sma50  = ta.trend.SMAIndicator(close=close, window=50).sma_indicator()
    sma200 = ta.trend.SMAIndicator(close=close, window=200).sma_indicator()
    pct_vs_200 = ((close - sma200) / sma200 * 100).rename("price_vs_sma200_pct")
    return pd.DataFrame(
        {
            "sma_50":              sma50,
            "sma_200":             sma200,
            "price_vs_sma200_pct": pct_vs_200,
        },
        index=close.index,
    )


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build full feature table from OHLCV DataFrame.

    Args:
        df: DataFrame with columns [Open, High, Low, Close, Volume]
            and DatetimeIndex.

    Returns:
        DataFrame with all technical indicators appended.
        Rows with insufficient history (NaN) are dropped.
    """
    close  = df["Close"]
    high   = df["High"]
    low    = df["Low"]
    volume = df["Volume"]

    features = pd.concat(
        [
            df[["Open", "High", "Low", "Close", "Volume"]],
            calculate_rsi(close).rename("rsi"),
            calculate_macd(close),
            calculate_bollinger(close),
            calculate_obv(close, volume).rename("obv"),
            calculate_atr(high, low, close).rename("atr"),
            calculate_moving_averages(close),
        ],
        axis=1,
    )
    # Drop rows where core indicators are NaN (warm-up period)
    features = features.dropna(subset=["rsi", "macd", "sma_200"])
    return features
