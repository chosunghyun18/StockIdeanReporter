"""Tests for data/collector.py."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from data.collector import fetch_ticker, load_or_fetch, collect_all, _raw_path


def _make_df(start: str = "2024-01-02", periods: int = 5) -> pd.DataFrame:
    idx = pd.date_range(start, periods=periods, freq="B")
    return pd.DataFrame(
        {
            "Open":   [100.0] * periods,
            "High":   [105.0] * periods,
            "Low":    [95.0]  * periods,
            "Close":  [102.0] * periods,
            "Volume": [1_000_000] * periods,
        },
        index=idx,
    )


# ── fetch_ticker ──────────────────────────────────────────────────────────────

class TestFetchTicker:
    def test_returns_dataframe_with_correct_columns(self):
        mock_df = _make_df()
        with patch("data.collector.yf.download", return_value=mock_df):
            result = fetch_ticker("SPY", start="2024-01-01", end="2024-01-10")
        assert list(result.columns) == ["Open", "High", "Low", "Close", "Volume"]

    def test_raises_on_empty_data(self):
        with patch("data.collector.yf.download", return_value=pd.DataFrame()):
            with pytest.raises(ValueError, match="No data returned"):
                fetch_ticker("FAKE", start="2024-01-01")

    def test_flattens_multiindex_columns(self):
        mock_df = _make_df()
        # Simulate MultiIndex columns that yfinance sometimes returns
        mock_df.columns = pd.MultiIndex.from_tuples(
            [(c, "SPY") for c in mock_df.columns]
        )
        with patch("data.collector.yf.download", return_value=mock_df):
            result = fetch_ticker("SPY", start="2024-01-01")
        assert isinstance(result.columns, pd.Index)
        assert "Close" in result.columns

    def test_index_is_datetimeindex(self):
        with patch("data.collector.yf.download", return_value=_make_df()):
            result = fetch_ticker("SPY", start="2024-01-01")
        assert isinstance(result.index, pd.DatetimeIndex)


# ── load_or_fetch ─────────────────────────────────────────────────────────────

class TestLoadOrFetch:
    def test_fetches_and_saves_when_no_cache(self, tmp_path, monkeypatch):
        monkeypatch.setattr("data.collector.DATA_DIR", tmp_path)
        mock_df = _make_df()
        with patch("data.collector.fetch_ticker", return_value=mock_df) as mock_fetch:
            result = load_or_fetch("SPY")
        mock_fetch.assert_called_once()
        assert (tmp_path / "SPY.parquet").exists()
        assert len(result) == len(mock_df)

    def test_incremental_update_appends_new_rows(self, tmp_path, monkeypatch):
        monkeypatch.setattr("data.collector.DATA_DIR", tmp_path)
        old_df = _make_df(start="2024-01-02", periods=5)
        old_df.to_parquet(tmp_path / "SPY.parquet")

        new_df = _make_df(start="2024-01-09", periods=3)
        with patch("data.collector.fetch_ticker", return_value=new_df):
            result = load_or_fetch("SPY")
        assert len(result) == len(old_df) + len(new_df)

    def test_returns_cache_when_up_to_date(self, tmp_path, monkeypatch):
        monkeypatch.setattr("data.collector.DATA_DIR", tmp_path)
        today = date.today().isoformat()
        df = _make_df(start=today, periods=1)
        df.to_parquet(tmp_path / "SPY.parquet")

        with patch("data.collector.fetch_ticker") as mock_fetch:
            load_or_fetch("SPY")
        mock_fetch.assert_not_called()

    def test_no_duplicate_rows_after_update(self, tmp_path, monkeypatch):
        monkeypatch.setattr("data.collector.DATA_DIR", tmp_path)
        df = _make_df(start="2024-01-02", periods=5)
        df.to_parquet(tmp_path / "SPY.parquet")

        overlap_df = _make_df(start="2024-01-05", periods=5)  # 2 overlap days
        with patch("data.collector.fetch_ticker", return_value=overlap_df):
            result = load_or_fetch("SPY")
        assert result.index.is_unique


# ── collect_all ───────────────────────────────────────────────────────────────

class TestCollectAll:
    def test_returns_dict_for_all_tickers(self, tmp_path, monkeypatch):
        monkeypatch.setattr("data.collector.DATA_DIR", tmp_path)
        mock_df = _make_df()
        with patch("data.collector.load_or_fetch", return_value=mock_df):
            result = collect_all()
        from data.collector import TICKERS
        assert set(result.keys()) == set(TICKERS.keys())
