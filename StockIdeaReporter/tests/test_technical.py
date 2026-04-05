"""기술적 분석 모듈 테스트."""
import numpy as np
import pandas as pd
import pytest

from src.analysis.technical import TechnicalAnalyzer, _calc_signal, _last


def _make_df(n: int = 100, trend: str = "up") -> pd.DataFrame:
    """테스트용 OHLCV 데이터프레임 생성."""
    np.random.seed(42)
    base = 50000

    if trend == "up":
        closes = base + np.cumsum(np.random.randn(n) * 500 + 100)
    elif trend == "down":
        closes = base + np.cumsum(np.random.randn(n) * 500 - 100)
    else:
        closes = base + np.random.randn(n) * 500

    closes = np.maximum(closes, 1000)
    dates = pd.date_range("2024-01-01", periods=n, freq="B")

    return pd.DataFrame(
        {
            "Open": closes * 0.99,
            "High": closes * 1.02,
            "Low": closes * 0.98,
            "Close": closes,
            "Volume": np.random.randint(1_000_000, 10_000_000, size=n),
        },
        index=dates,
    )


class TestTechnicalAnalyzer:
    """TechnicalAnalyzer 테스트."""

    def test_analyze_returns_signals(self):
        """분석 결과 반환 확인."""
        analyzer = TechnicalAnalyzer()
        df = _make_df(100)
        signals = analyzer.analyze(df)

        assert signals is not None
        assert signals.rsi_14 is not None
        assert signals.ma20 is not None
        assert signals.signal in ("매수", "중립", "매도")
        assert 1 <= signals.signal_strength <= 5

    def test_analyze_insufficient_data_raises(self):
        """데이터 부족 시 ValueError 발생."""
        analyzer = TechnicalAnalyzer()
        df = _make_df(10)
        with pytest.raises(ValueError, match="데이터가 부족"):
            analyzer.analyze(df)

    def test_rsi_range(self):
        """RSI는 0-100 범위여야 한다."""
        analyzer = TechnicalAnalyzer()
        df = _make_df(100)
        signals = analyzer.analyze(df)
        assert 0 <= signals.rsi_14 <= 100

    def test_bollinger_band_order(self):
        """볼린저밴드: 하단 < 중간 < 상단."""
        analyzer = TechnicalAnalyzer()
        df = _make_df(100)
        signals = analyzer.analyze(df)
        assert signals.bb_lower < signals.bb_middle < signals.bb_upper

    def test_support_below_resistance(self):
        """지지가 저항보다 낮아야 한다."""
        analyzer = TechnicalAnalyzer()
        df = _make_df(100)
        signals = analyzer.analyze(df)
        assert signals.support <= signals.resistance

    def test_mdd_is_negative(self):
        """MDD는 0 이하여야 한다."""
        analyzer = TechnicalAnalyzer()
        df = _make_df(100)
        mdd = analyzer.calc_mdd(df)
        assert mdd <= 0

    def test_ma60_requires_60_days(self):
        """60일 미만 데이터에서 MA60은 None."""
        analyzer = TechnicalAnalyzer()
        df = _make_df(50)
        signals = analyzer.analyze(df)
        assert signals.ma60 is None

    def test_ma60_present_with_sufficient_data(self):
        """60일 이상 데이터에서 MA60은 값이 있어야 한다."""
        analyzer = TechnicalAnalyzer()
        df = _make_df(100)
        signals = analyzer.analyze(df)
        assert signals.ma60 is not None


class TestHelpers:
    """헬퍼 함수 테스트."""

    def test_last_returns_last_valid(self):
        s = pd.Series([1.0, 2.0, 3.0])
        assert _last(s) == 3.0

    def test_last_skips_nan(self):
        s = pd.Series([1.0, float("nan")])
        assert _last(s) is None

    def test_last_empty_series(self):
        assert _last(pd.Series([], dtype=float)) is None

    def test_calc_signal_buy(self):
        signal, strength = _calc_signal(
            rsi_14=25,
            macd_hist=0.5,
            golden_cross=True,
            above_ma60=True,
            bb_percent=0.1,
            stoch_k=15,
        )
        assert signal == "매수"
        assert strength >= 3

    def test_calc_signal_sell(self):
        signal, strength = _calc_signal(
            rsi_14=75,
            macd_hist=-0.5,
            golden_cross=False,
            above_ma60=False,
            bb_percent=0.9,
            stoch_k=85,
        )
        assert signal == "매도"

    def test_calc_signal_neutral(self):
        signal, _ = _calc_signal(
            rsi_14=50,
            macd_hist=0.0,
            golden_cross=False,
            above_ma60=True,
            bb_percent=0.5,
            stoch_k=50,
        )
        assert signal == "중립"
