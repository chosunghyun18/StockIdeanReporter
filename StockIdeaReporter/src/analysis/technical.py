"""기술적 분석 모듈.

이동평균, 모멘텀, 변동성, 거래량, 지지/저항 지표 계산.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd
import ta


@dataclass(frozen=True)
class TechnicalSignals:
    """기술적 분석 주요 신호 데이터."""

    # 추세
    ma20: Optional[float]
    ma60: Optional[float]
    ma120: Optional[float]
    ma240: Optional[float]
    golden_cross: bool  # ma20 > ma60
    above_ma60: bool

    # 모멘텀
    rsi_14: Optional[float]
    macd: Optional[float]
    macd_signal: Optional[float]
    macd_histogram: Optional[float]
    stoch_k: Optional[float]
    stoch_d: Optional[float]

    # 변동성
    bb_upper: Optional[float]
    bb_middle: Optional[float]
    bb_lower: Optional[float]
    bb_percent: Optional[float]  # (price - lower) / (upper - lower)
    atr_14: Optional[float]

    # 거래량
    obv: Optional[float]
    volume_ma20: Optional[float]
    volume_ratio: Optional[float]  # 최근 거래량 / MA20

    # 지지/저항
    support: Optional[float]   # 52주 저점 기반
    resistance: Optional[float]  # 52주 고점 기반
    fib_382: Optional[float]
    fib_618: Optional[float]

    # 종합 신호
    signal: str  # "매수" / "중립" / "매도"
    signal_strength: int  # 1-5


class TechnicalAnalyzer:
    """기술적 분석기."""

    def analyze(self, df: pd.DataFrame) -> TechnicalSignals:
        """주가 데이터프레임으로 기술적 지표를 계산한다.

        Args:
            df: OHLCV 데이터프레임 (Open, High, Low, Close, Volume 컬럼)

        Returns:
            TechnicalSignals 객체

        Raises:
            ValueError: 데이터가 부족한 경우
        """
        if len(df) < 30:
            raise ValueError(f"데이터가 부족합니다. 최소 30일 필요, 현재 {len(df)}일")

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        # 이동평균
        ma20 = _last(close.rolling(20).mean())
        ma60 = _last(close.rolling(60).mean()) if len(df) >= 60 else None
        ma120 = _last(close.rolling(120).mean()) if len(df) >= 120 else None
        ma240 = _last(close.rolling(240).mean()) if len(df) >= 240 else None

        current_price = float(close.iloc[-1])
        golden_cross = (ma20 is not None and ma60 is not None and ma20 > ma60)
        above_ma60 = (ma60 is not None and current_price > ma60)

        # RSI
        rsi = ta.momentum.RSIIndicator(close=close, window=14)
        rsi_14 = _last(rsi.rsi())

        # MACD
        macd_ind = ta.trend.MACD(close=close)
        macd_val = _last(macd_ind.macd())
        macd_sig = _last(macd_ind.macd_signal())
        macd_hist = _last(macd_ind.macd_diff())

        # Stochastic
        stoch = ta.momentum.StochasticOscillator(high=high, low=low, close=close)
        stoch_k = _last(stoch.stoch())
        stoch_d = _last(stoch.stoch_signal())

        # 볼린저밴드
        bb = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
        bb_upper = _last(bb.bollinger_hband())
        bb_middle = _last(bb.bollinger_mavg())
        bb_lower = _last(bb.bollinger_lband())
        bb_percent = _last(bb.bollinger_pband())

        # ATR
        atr_ind = ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=14)
        atr_14 = _last(atr_ind.average_true_range())

        # OBV
        obv_ind = ta.volume.OnBalanceVolumeIndicator(close=close, volume=volume)
        obv = _last(obv_ind.on_balance_volume())

        # 거래량 MA
        vol_ma20 = _last(volume.rolling(20).mean())
        vol_ratio = None
        if vol_ma20 and vol_ma20 > 0:
            vol_ratio = float(volume.iloc[-1]) / vol_ma20

        # 지지/저항 (52주 범위)
        recent = df.tail(252)
        support = float(recent["Low"].min())
        resistance = float(recent["High"].max())

        price_range = resistance - support
        fib_382 = support + price_range * 0.382
        fib_618 = support + price_range * 0.618

        # 종합 신호 계산
        signal, strength = _calc_signal(
            rsi_14=rsi_14,
            macd_hist=macd_hist,
            golden_cross=golden_cross,
            above_ma60=above_ma60,
            bb_percent=bb_percent,
            stoch_k=stoch_k,
        )

        return TechnicalSignals(
            ma20=ma20, ma60=ma60, ma120=ma120, ma240=ma240,
            golden_cross=golden_cross, above_ma60=above_ma60,
            rsi_14=rsi_14,
            macd=macd_val, macd_signal=macd_sig, macd_histogram=macd_hist,
            stoch_k=stoch_k, stoch_d=stoch_d,
            bb_upper=bb_upper, bb_middle=bb_middle, bb_lower=bb_lower,
            bb_percent=bb_percent, atr_14=atr_14,
            obv=obv, volume_ma20=vol_ma20, volume_ratio=vol_ratio,
            support=support, resistance=resistance,
            fib_382=fib_382, fib_618=fib_618,
            signal=signal, signal_strength=strength,
        )

    def calc_mdd(self, df: pd.DataFrame) -> float:
        """최대 낙폭(MDD) 계산.

        Args:
            df: OHLCV 데이터프레임

        Returns:
            MDD 비율 (음수, 예: -0.35 = -35%)
        """
        close = df["Close"]
        roll_max = close.cummax()
        drawdown = (close - roll_max) / roll_max
        return float(drawdown.min())


def _last(series: pd.Series) -> Optional[float]:
    """시리즈의 마지막 유효 값 반환."""
    if series is None or series.empty:
        return None
    val = series.iloc[-1]
    if pd.isna(val):
        return None
    return float(val)


def _calc_signal(
    rsi_14: Optional[float],
    macd_hist: Optional[float],
    golden_cross: bool,
    above_ma60: bool,
    bb_percent: Optional[float],
    stoch_k: Optional[float],
) -> tuple[str, int]:
    """다중 지표 기반 종합 신호 계산.

    Returns:
        (signal, strength) 튜플
    """
    score = 0  # -5 ~ +5

    if rsi_14 is not None:
        if rsi_14 < 30:
            score += 2  # 과매도
        elif rsi_14 < 50:
            score += 1
        elif rsi_14 > 70:
            score -= 2  # 과매수
        elif rsi_14 > 60:
            score -= 1

    if macd_hist is not None:
        score += 1 if macd_hist > 0 else -1

    if golden_cross:
        score += 1
    if above_ma60:
        score += 1

    if bb_percent is not None:
        if bb_percent < 0.2:
            score += 1  # 하단 밴드 근처
        elif bb_percent > 0.8:
            score -= 1  # 상단 밴드 근처

    if stoch_k is not None:
        if stoch_k < 20:
            score += 1
        elif stoch_k > 80:
            score -= 1

    if score >= 3:
        return "매수", min(5, score)
    elif score <= -3:
        return "매도", min(5, abs(score))
    else:
        return "중립", max(1, abs(score))
