"""Seed text builder for MiroFish simulation.

Converts numeric financial features into natural-language seed text
that MiroFish agents can read and reason about.
Each agent type (macro / earnings / sentiment) gets a tailored view.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class MarketSnapshot:
    """Structured market data for a single date."""

    date: str
    spy_close: float
    spy_change_pct: float
    rsi: float
    macd: float
    macd_signal: float
    bb_pct: float          # Bollinger %B  (0=lower band, 1=upper band)
    sma_50: float
    sma_200: float
    price_vs_sma200_pct: float
    vix: Optional[float]
    tnx: Optional[float]   # 10Y Treasury yield
    obv_change_pct: float  # OBV % change over 5 days (volume momentum)
    atr: float


def _rsi_label(rsi: float) -> str:
    if rsi >= 75:
        return "극단 과매수 (75+)"
    if rsi >= 65:
        return "과매수 근접"
    if rsi <= 25:
        return "극단 과매도 (25-)"
    if rsi <= 35:
        return "과매도 근접"
    return "중립"


def _trend_label(pct: float) -> str:
    if pct >= 10:
        return f"200일 이평 대비 +{pct:.1f}% (강한 상승 추세)"
    if pct >= 3:
        return f"200일 이평 대비 +{pct:.1f}% (상승 추세)"
    if pct <= -10:
        return f"200일 이평 대비 {pct:.1f}% (강한 하락 추세)"
    if pct <= -3:
        return f"200일 이평 대비 {pct:.1f}% (하락 추세)"
    return f"200일 이평 대비 {pct:+.1f}% (횡보 구간)"


def _macd_label(macd: float, signal: float) -> str:
    hist = macd - signal
    if hist > 0 and macd > 0:
        return "MACD 강세 (양전환, 제로선 위)"
    if hist > 0:
        return "MACD 골든크로스 (상향 전환)"
    if hist < 0 and macd < 0:
        return "MACD 약세 (음전환, 제로선 아래)"
    return "MACD 데드크로스 (하향 전환)"


def _bb_label(bb_pct: float) -> str:
    if bb_pct >= 0.9:
        return f"볼린저밴드 %B={bb_pct:.2f} — 상단 돌파 (과열)"
    if bb_pct >= 0.7:
        return f"볼린저밴드 %B={bb_pct:.2f} — 상단 근접"
    if bb_pct <= 0.1:
        return f"볼린저밴드 %B={bb_pct:.2f} — 하단 이탈 (공포)"
    if bb_pct <= 0.3:
        return f"볼린저밴드 %B={bb_pct:.2f} — 하단 근접"
    return f"볼린저밴드 %B={bb_pct:.2f} — 밴드 중단"


def _vix_label(vix: Optional[float]) -> str:
    if vix is None:
        return "VIX 데이터 없음"
    if vix >= 40:
        return f"VIX {vix:.1f} — 극단 공포 (시장 위기)"
    if vix >= 25:
        return f"VIX {vix:.1f} — 고변동성 (불안)"
    if vix <= 12:
        return f"VIX {vix:.1f} — 극단 안도 (과신 주의)"
    if vix <= 17:
        return f"VIX {vix:.1f} — 저변동성 (안정)"
    return f"VIX {vix:.1f} — 보통"


def build_macro_seed(snap: MarketSnapshot) -> str:
    """Seed text for the macro-economic analyst agent.

    Focuses on rate environment and trend structure.
    """
    tnx_line = (
        f"- 미국 10년물 국채금리: {snap.tnx:.2f}%\n"
        if snap.tnx is not None
        else "- 미국 10년물 국채금리: 데이터 없음\n"
    )
    return (
        f"[거시경제 데이터] {snap.date}\n"
        f"- SPY 종가: ${snap.spy_close:.2f} (전일 대비 {snap.spy_change_pct:+.2f}%)\n"
        f"- {_trend_label(snap.price_vs_sma200_pct)}\n"
        f"- SMA50: ${snap.sma_50:.2f} / SMA200: ${snap.sma_200:.2f}\n"
        f"{tnx_line}"
        f"- {_vix_label(snap.vix)}\n"
        f"- ATR(14): ${snap.atr:.2f} (일간 평균변동폭)\n"
    )


def build_sentiment_seed(snap: MarketSnapshot) -> str:
    """Seed text for the market sentiment analyst agent.

    Focuses on momentum, volatility, and crowd psychology signals.
    """
    return (
        f"[시장심리 데이터] {snap.date}\n"
        f"- SPY 종가: ${snap.spy_close:.2f} (전일 대비 {snap.spy_change_pct:+.2f}%)\n"
        f"- RSI(14): {snap.rsi:.1f} — {_rsi_label(snap.rsi)}\n"
        f"- {_macd_label(snap.macd, snap.macd_signal)}\n"
        f"- {_bb_label(snap.bb_pct)}\n"
        f"- {_vix_label(snap.vix)}\n"
        f"- OBV 5일 변화: {snap.obv_change_pct:+.1f}% (거래량 추세)\n"
    )


def build_earnings_seed(snap: MarketSnapshot) -> str:
    """Seed text for the earnings analyst agent.

    Focuses on price action relative to fair value proxies.
    """
    return (
        f"[실적/밸류에이션 데이터] {snap.date}\n"
        f"- SPY 종가: ${snap.spy_close:.2f} (전일 대비 {snap.spy_change_pct:+.2f}%)\n"
        f"- {_trend_label(snap.price_vs_sma200_pct)}\n"
        f"- {_macd_label(snap.macd, snap.macd_signal)}\n"
        f"- {_vix_label(snap.vix)}\n"
        f"- 최근 변동성(ATR): ${snap.atr:.2f}\n"
    )


def snapshot_from_features(
    features: pd.DataFrame,
    vix_series: Optional[pd.Series] = None,
    tnx_series: Optional[pd.Series] = None,
    date: Optional[str] = None,
) -> MarketSnapshot:
    """Build a MarketSnapshot from the feature DataFrame.

    Args:
        features: Output of signals.indicators.build_features().
        vix_series: Optional VIX close series aligned to same index.
        tnx_series: Optional TNX close series aligned to same index.
        date: Target date (YYYY-MM-DD). Defaults to last available row.

    Returns:
        MarketSnapshot for the specified date.

    Raises:
        KeyError: If date not found in features index.
    """
    if date is None:
        row = features.iloc[-1]
        date = features.index[-1].strftime("%Y-%m-%d")
    else:
        row = features.loc[pd.Timestamp(date)]

    prev_idx = features.index.get_loc(pd.Timestamp(date))
    if prev_idx > 0:
        prev_close = features.iloc[prev_idx - 1]["Close"]
        change_pct = (row["Close"] - prev_close) / prev_close * 100
    else:
        change_pct = 0.0

    # OBV 5-day momentum
    obv_now   = row["obv"]
    obv_5d_ago = features["obv"].iloc[max(0, prev_idx - 5)]
    obv_change = (obv_now - obv_5d_ago) / abs(obv_5d_ago) * 100 if obv_5d_ago != 0 else 0.0

    ts = pd.Timestamp(date)
    vix_val = float(vix_series.loc[ts]) if (vix_series is not None and ts in vix_series.index) else None
    tnx_val = float(tnx_series.loc[ts]) if (tnx_series is not None and ts in tnx_series.index) else None

    return MarketSnapshot(
        date=date,
        spy_close=float(row["Close"]),
        spy_change_pct=float(change_pct),
        rsi=float(row["rsi"]),
        macd=float(row["macd"]),
        macd_signal=float(row["macd_signal"]),
        bb_pct=float(row["bb_pct"]),
        sma_50=float(row["sma_50"]),
        sma_200=float(row["sma_200"]),
        price_vs_sma200_pct=float(row["price_vs_sma200_pct"]),
        vix=vix_val,
        tnx=tnx_val,
        obv_change_pct=float(obv_change),
        atr=float(row["atr"]),
    )


def build_all_seeds(snap: MarketSnapshot) -> dict[str, str]:
    """Build seed texts for all three agents.

    Args:
        snap: MarketSnapshot for the target date.

    Returns:
        Dict with keys 'macro', 'sentiment', 'earnings'.
    """
    return {
        "macro":     build_macro_seed(snap),
        "sentiment": build_sentiment_seed(snap),
        "earnings":  build_earnings_seed(snap),
    }
