"""Market data collector using yfinance.

Collects OHLCV data for SPY, VIX, TNX, DXY.
Supports incremental updates (only fetches data after last saved date).
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf


# Tickers to collect
TICKERS: dict[str, str] = {
    "SPY": "SPY ETF",
    "^GSPC": "S&P 500 Index",
    "^VIX": "VIX Volatility",
    "^TNX": "10Y Treasury Yield",
    "DX-Y.NYB": "US Dollar Index",
}

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"


def _raw_path(ticker: str) -> Path:
    safe = ticker.replace("^", "").replace("-", "_").replace(".", "_")
    return DATA_DIR / f"{safe}.parquet"


def fetch_ticker(
    ticker: str,
    start: str = "1993-01-01",
    end: Optional[str] = None,
) -> pd.DataFrame:
    """Download OHLCV data for a single ticker.

    Args:
        ticker: Yahoo Finance ticker symbol.
        start: Start date (YYYY-MM-DD).
        end: End date (YYYY-MM-DD). Defaults to today.

    Returns:
        DataFrame with DatetimeIndex and columns [Open, High, Low, Close, Volume].

    Raises:
        ValueError: If downloaded data is empty.
    """
    end = end or date.today().isoformat()
    df: pd.DataFrame = yf.download(
        ticker,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
    )
    if df.empty:
        raise ValueError(f"No data returned for {ticker} ({start} ~ {end})")

    # Flatten MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.index = pd.to_datetime(df.index)
    df.index.name = "Date"
    return df[["Open", "High", "Low", "Close", "Volume"]].copy()


def load_or_fetch(ticker: str, start: str = "1993-01-01") -> pd.DataFrame:
    """Load from parquet cache or fetch from yfinance with incremental update.

    Args:
        ticker: Yahoo Finance ticker symbol.
        start: Initial start date when no cache exists.

    Returns:
        Full historical DataFrame.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = _raw_path(ticker)

    if path.exists():
        cached = pd.read_parquet(path)
        last_date = cached.index.max()
        # Fetch only missing days
        next_start = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
        today = date.today().isoformat()
        if next_start >= today:
            return cached
        new_data = fetch_ticker(ticker, start=next_start)
        combined = pd.concat([cached, new_data])
        combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    else:
        combined = fetch_ticker(ticker, start=start)

    combined.to_parquet(path)
    return combined


def collect_all(start: str = "1993-01-01") -> dict[str, pd.DataFrame]:
    """Collect all configured tickers.

    Args:
        start: Initial start date.

    Returns:
        Dict mapping ticker → DataFrame.
    """
    results: dict[str, pd.DataFrame] = {}
    for ticker in TICKERS:
        results[ticker] = load_or_fetch(ticker, start=start)
    return results
