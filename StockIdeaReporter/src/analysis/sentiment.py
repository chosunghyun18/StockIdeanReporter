"""가격/거래량 기반 시장 심리 분석 모듈.

RSI 다이버전스, 거래량 클라이맥스, OBV 매집/분배 신호 등을 통해
주가 심리를 정량화한다.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SentimentSignals:
    """종목 심리 분석 결과."""

    ticker: str
    rsi_divergence: Optional[str]    # "상승 다이버전스" / "하락 다이버전스" / None
    volume_climax: bool
    climax_type: Optional[str]       # "매도 클라이맥스" / "매수 클라이맥스"
    selling_climax_score: float      # 0~1 (1=강한 매도 클라이맥스)
    obv_signal: Optional[str]        # "매집" / "분배" / None
    fear_greed: str                  # "극단적 공포" / "공포" / "중립" / "탐욕"
    candle_pattern: str
    sentiment_score: int             # -5 ~ +5 (양수=낙관=반등 기대)
    summary: str


class SentimentAnalyzer:
    """가격·거래량 기반 심리 지표 종합 분석."""

    def analyze(self, ticker: str, df: pd.DataFrame) -> SentimentSignals:
        """심리 지표 종합 분석.

        Args:
            ticker: 종목 코드
            df: OHLCV DataFrame (최소 30행)

        Returns:
            SentimentSignals
        """
        close = df["Close"]
        volume = df["Volume"] if "Volume" in df.columns else pd.Series(dtype=float)

        rsi_series = _calc_rsi(close)
        obv = _calc_obv(close, volume) if not volume.empty else pd.Series(dtype=float)

        rsi_div = _detect_rsi_divergence(close, rsi_series)
        vol_climax, climax_type = _detect_volume_climax(df, volume)
        selling_score = _calc_selling_climax_score(df, volume)
        obv_signal = _detect_obv_signal(close, obv) if not obv.empty else None
        fear_greed = _classify_fear_greed(rsi_series, close)
        candle = _detect_candle_pattern(df)
        score = _calc_sentiment_score(rsi_div, vol_climax, climax_type, obv_signal, fear_greed)
        summary = _build_summary(rsi_div, vol_climax, climax_type, obv_signal, fear_greed, candle)

        return SentimentSignals(
            ticker=ticker,
            rsi_divergence=rsi_div,
            volume_climax=vol_climax,
            climax_type=climax_type,
            selling_climax_score=round(selling_score, 3),
            obv_signal=obv_signal,
            fear_greed=fear_greed,
            candle_pattern=candle,
            sentiment_score=score,
            summary=summary,
        )


# ── RSI ────────────────────────────────────────────────────────────

def _calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def _detect_rsi_divergence(close: pd.Series, rsi: pd.Series) -> Optional[str]:
    """가격 저점과 RSI 저점 비교로 다이버전스 감지 (최근 20일)."""
    window = 20
    if len(close) < window:
        return None

    c = close.tail(window).values
    r = rsi.tail(window).values

    lows = [i for i in range(1, len(c) - 1) if c[i] < c[i - 1] and c[i] < c[i + 1]]
    if len(lows) < 2:
        return None

    p1, p2 = lows[-2], lows[-1]
    price_lower = c[p2] < c[p1]
    rsi_lower = r[p2] < r[p1]

    if price_lower and not rsi_lower:
        return "상승 다이버전스"
    if not price_lower and rsi_lower:
        return "하락 다이버전스"
    return None


# ── 거래량 클라이맥스 ───────────────────────────────────────────────

def _detect_volume_climax(
    df: pd.DataFrame, volume: pd.Series
) -> tuple[bool, Optional[str]]:
    """거래량이 20일 평균의 2.5배 초과 시 클라이맥스로 판정."""
    if volume.empty or len(volume) < 20:
        return False, None

    avg_vol = volume.tail(20).mean()
    if avg_vol == 0 or volume.iloc[-1] < avg_vol * 2.5:
        return False, None

    last_close = df["Close"].iloc[-1]
    prev_close = df["Close"].iloc[-2] if len(df) >= 2 else last_close

    if last_close < prev_close:
        return True, "매도 클라이맥스"
    return True, "매수 클라이맥스"


def _calc_selling_climax_score(df: pd.DataFrame, volume: pd.Series) -> float:
    """매도 클라이맥스 강도 (0~1)."""
    if volume.empty or len(volume) < 20:
        return 0.0
    avg_vol = volume.tail(20).mean()
    if avg_vol == 0:
        return 0.0

    vol_ratio = float(volume.iloc[-1] / avg_vol)
    if len(df) < 2:
        return 0.0
    change = float((df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2])
    if change >= 0:
        return 0.0
    return min(vol_ratio / 5.0, 1.0) * min(abs(change) * 20, 1.0)


# ── OBV ────────────────────────────────────────────────────────────

def _calc_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    return (direction * volume).cumsum()


def _detect_obv_signal(close: pd.Series, obv: pd.Series) -> Optional[str]:
    """OBV 추세 vs 가격 추세 비교."""
    if len(close) < 10:
        return None
    price_up = close.iloc[-1] > close.iloc[-10]
    obv_up = obv.iloc[-1] > obv.iloc[-10]
    if not price_up and obv_up:
        return "매집"
    if price_up and not obv_up:
        return "분배"
    return None


# ── 공포/탐욕 ──────────────────────────────────────────────────────

def _classify_fear_greed(rsi: pd.Series, close: pd.Series) -> str:
    last_rsi = float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else 50.0
    ma20 = close.tail(20).mean()
    price_vs_ma = float(close.iloc[-1] / ma20 - 1) if ma20 else 0.0

    score = 0
    if last_rsi < 25:
        score -= 2
    elif last_rsi < 35:
        score -= 1
    elif last_rsi > 75:
        score += 2
    elif last_rsi > 65:
        score += 1

    if price_vs_ma < -0.10:
        score -= 1
    elif price_vs_ma > 0.10:
        score += 1

    mapping = {-3: "극단적 공포", -2: "극단적 공포", -1: "공포", 0: "중립", 1: "탐욕"}
    return mapping.get(score, "극단적 탐욕" if score >= 2 else "극단적 공포")


# ── 캔들 패턴 ──────────────────────────────────────────────────────

def _detect_candle_pattern(df: pd.DataFrame) -> str:
    if len(df) < 1:
        return "패턴 없음"
    o = float(df["Open"].iloc[-1])
    h = float(df["High"].iloc[-1])
    l = float(df["Low"].iloc[-1])
    c = float(df["Close"].iloc[-1])

    total = h - l
    if total == 0:
        return "도지"
    body = abs(c - o)
    lower_tail = min(o, c) - l
    upper_tail = h - max(o, c)

    if body / total < 0.1:
        return "도지 (방향 전환 가능)"
    if lower_tail > body * 2 and upper_tail < body * 0.5:
        return "망치형 (반등 신호)"
    if upper_tail > body * 2 and lower_tail < body * 0.5:
        return "역망치형 (상승 전환 가능)"
    if c > o and body / total > 0.6:
        return "강한 양봉"
    if c < o and body / total > 0.6:
        return "강한 음봉"
    return "중립 캔들"


# ── 종합 점수 ──────────────────────────────────────────────────────

def _calc_sentiment_score(
    rsi_div: Optional[str],
    vol_climax: bool,
    climax_type: Optional[str],
    obv_signal: Optional[str],
    fear_greed: str,
) -> int:
    score = 0
    if rsi_div == "상승 다이버전스":
        score += 2
    elif rsi_div == "하락 다이버전스":
        score -= 2
    if vol_climax and climax_type == "매도 클라이맥스":
        score += 2
    elif vol_climax and climax_type == "매수 클라이맥스":
        score -= 1
    if obv_signal == "매집":
        score += 1
    elif obv_signal == "분배":
        score -= 1
    fg_map = {"극단적 공포": 2, "공포": 1, "중립": 0, "탐욕": -1, "극단적 탐욕": -2}
    score += fg_map.get(fear_greed, 0)
    return max(-5, min(5, score))


def _build_summary(
    rsi_div: Optional[str],
    vol_climax: bool,
    climax_type: Optional[str],
    obv_signal: Optional[str],
    fear_greed: str,
    candle: str,
) -> str:
    parts = [f"심리: {fear_greed}", f"캔들: {candle}"]
    if rsi_div:
        parts.append(f"RSI {rsi_div}")
    if vol_climax and climax_type:
        parts.append(climax_type)
    if obv_signal:
        parts.append(f"OBV {obv_signal}")
    return " | ".join(parts)
