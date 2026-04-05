"""레버리지/인버스 ETF 분석 에이전트.

시장 바이어스 결과를 읽어 기초지수 기술적 분석 후 레버리지 ETF 포지션 추천.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

import anthropic
import pandas as pd
import yfinance as yf

try:
    import ta
    _TA_AVAILABLE = True
except ImportError:
    _TA_AVAILABLE = False

logger = logging.getLogger(__name__)
OUTPUT_DIR = Path("output")
_MODEL = "claude-haiku-4-5-20251001"

# 기초지수 → 레버리지 ETF 매핑
BASE_INDEX_MAP = {
    "QQQ":  {"3x_long": "TQQQ", "3x_short": "SQQQ", "2x_long": "QLD",  "2x_short": "QID"},
    "SPY":  {"3x_long": "UPRO", "3x_short": "SPXS", "2x_long": "SSO",  "2x_short": "SDS"},
    "SOXX": {"3x_long": "SOXL", "3x_short": "SOXS", "2x_long": "USD",  "2x_short": "SMN"},
    "XLF":  {"3x_long": "FAS",  "3x_short": "FAZ",  "2x_long": "UYG",  "2x_short": "SKF"},
    "IWM":  {"3x_long": "TNA",  "3x_short": "TZA",  "2x_long": "UWM",  "2x_short": "TWM"},
}


def _safe_float(val) -> float:
    try:
        return round(float(val), 4)
    except Exception:
        return 0.0


@dataclass
class BaseIndexSignal:
    ticker: str
    price: float
    rsi: float
    macd_diff: float
    adx: float
    bb_pct: float        # 0=하단, 1=상단
    confidence_long: int  # 0-100
    confidence_short: int


def analyze_base_index(ticker: str) -> BaseIndexSignal:
    """기초지수 3개월 데이터로 롱/숏 신뢰도 산출."""
    data = yf.download(ticker, period="3mo", progress=False, auto_adjust=True)
    close = data["Close"].squeeze()
    high  = data["High"].squeeze()
    low   = data["Low"].squeeze()

    price = _safe_float(close.iloc[-1])

    if _TA_AVAILABLE:
        rsi      = _safe_float(ta.momentum.RSIIndicator(close).rsi().iloc[-1])
        macd_obj = ta.trend.MACD(close)
        macd_diff = _safe_float(macd_obj.macd_diff().iloc[-1])
        adx      = _safe_float(ta.trend.ADXIndicator(high, low, close).adx().iloc[-1])
        bb_obj   = ta.volatility.BollingerBands(close)
        bb_pct   = _safe_float(bb_obj.bollinger_pband().iloc[-1])
    else:
        rsi, macd_diff, adx, bb_pct = 50.0, 0.0, 20.0, 0.5

    # 롱 신뢰도
    long_score = 0
    if rsi > 50:       long_score += 20
    if macd_diff > 0:  long_score += 25
    if bb_pct > 0.5:   long_score += 20
    if adx > 25:       long_score += 35

    # 숏 신뢰도
    short_score = 0
    if rsi < 50:       short_score += 20
    if macd_diff < 0:  short_score += 25
    if bb_pct < 0.5:   short_score += 20
    if adx > 25:       short_score += 35

    return BaseIndexSignal(
        ticker=ticker, price=price, rsi=rsi, macd_diff=macd_diff,
        adx=adx, bb_pct=bb_pct,
        confidence_long=long_score, confidence_short=short_score,
    )


def _calc_decay_risk(vix: float, leverage: int = 3, holding_days: int = 5) -> str:
    daily_vol = vix / (252 ** 0.5) / 100
    n = float(leverage)
    decay_pct = (daily_vol ** 2) * (n * n - n) / 2 * holding_days * 100
    if decay_pct > 3:
        return f"HIGH ({decay_pct:.1f}%)"
    elif decay_pct > 1:
        return f"MEDIUM ({decay_pct:.1f}%)"
    return f"LOW ({decay_pct:.1f}%)"


def _betting_size(confidence: int) -> str:
    # 레버리지 ETF는 일반 대비 50% 제한
    if confidence >= 80:
        return "4-5% (최대)"
    elif confidence >= 70:
        return "2-3% (중간)"
    elif confidence >= 60:
        return "1-2% (소규모)"
    return "진입 금지"


class LeveragedEtfAnalyst:
    """레버리지 ETF 분석 에이전트."""

    def __init__(self, client: Optional[anthropic.Anthropic] = None) -> None:
        self.client = client or anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    def _read_market_bias(self) -> tuple[str, float, str]:
        """가장 최근 market_bias 파일에서 레짐/VIX/신뢰도 읽기."""
        files = sorted(OUTPUT_DIR.glob("market_bias_*.md"), reverse=True)
        if not files:
            return "BULL", 18.0, "60"
        content = files[0].read_text(encoding="utf-8")
        import re
        regime_m = re.search(r"현재 레짐:\s*(\w+)", content)
        vix_m    = re.search(r"VIX\s*\|\s*([\d.]+)", content)
        conf_m   = re.search(r"레짐 신뢰도:\s*(\d+)%", content)
        regime  = regime_m.group(1) if regime_m else "BULL"
        vix     = float(vix_m.group(1)) if vix_m else 18.0
        conf    = conf_m.group(1) if conf_m else "60"
        return regime, vix, conf

    def analyze(self) -> tuple[str, list[BaseIndexSignal]]:
        today   = date.today().strftime("%Y-%m-%d")
        regime, vix, bias_conf = self._read_market_bias()

        signals: list[BaseIndexSignal] = []
        for ticker in BASE_INDEX_MAP:
            try:
                sig = analyze_base_index(ticker)
                signals.append(sig)
            except Exception as e:
                logger.warning("기초지수 분석 실패 %s: %s", ticker, e)

        # SIDEWAYS면 진입 금지
        trading_allowed = regime != "SIDEWAYS" and vix < 35

        # 테이블 행 생성
        table_rows = ""
        avoidance = ""
        for sig in signals:
            etf_map = BASE_INDEX_MAP.get(sig.ticker, {})
            if trading_allowed and sig.confidence_long >= 60 and sig.confidence_long > sig.confidence_short:
                direction = "LONG"
                conf = sig.confidence_long
                etf  = etf_map.get("3x_long", "N/A")
            elif trading_allowed and sig.confidence_short >= 60 and sig.confidence_short > sig.confidence_long:
                direction = "SHORT"
                conf = sig.confidence_short
                etf  = etf_map.get("3x_short", "N/A")
            else:
                avoidance += f"- {sig.ticker} 관련: 신뢰도 부족 (롱 {sig.confidence_long}% / 숏 {sig.confidence_short}%)\n"
                continue

            size  = _betting_size(conf)
            decay = _calc_decay_risk(vix)
            table_rows += (
                f"| {etf} | {direction} | {conf}% | {size} | "
                f"RSI {sig.rsi:.1f} / ADX {sig.adx:.1f} | {decay} | 3-5일 |\n"
            )

        if not table_rows:
            table_rows = "| — | — | — | — | — | — | — |\n"
        if not avoidance:
            avoidance = "없음"
        if not trading_allowed:
            avoidance = f"시장 레짐 {regime} 또는 VIX {vix:.1f} — 모든 레버리지 ETF 진입 금지"

        # 기초지수 신호 요약
        index_summary = "\n".join(
            f"- {s.ticker}: RSI {s.rsi:.1f} | MACD {s.macd_diff:+.4f} | ADX {s.adx:.1f}"
            for s in signals
        )

        prompt = f"""아래 데이터로 레버리지 ETF 분석 리포트를 **정확히 아래 포맷**으로 작성하세요.
설명 없이 마크다운 본문만 출력하세요.

=== 입력 데이터 ===
분석 기준일: {today}
시장 레짐: {regime} (신뢰도 {bias_conf}%)
VIX: {vix:.2f}
거래 허용: {"YES" if trading_allowed else "NO"}

기초지수 신호:
{index_summary}

=== 출력 포맷 ===
## 레버리지 ETF 분석 결과

### 분석 기준일: {today}
### 시장 레짐: {regime}

#### 추천 포지션

| ETF | 방향 | 신뢰도 | 배팅 크기 | 기술 신호 | Decay 리스크 | 보유기간 |
|-----|------|--------|----------|----------|-------------|---------|
{table_rows}
#### 근거
[각 추천 ETF의 핵심 근거 2-3줄]

#### 회피 리스트 (현재 진입 금지)
{avoidance}

#### 모니터링 기준
- 손절 트리거: [조건]
- 청산 트리거: [조건]
"""
        msg = self.client.messages.create(
            model=_MODEL, max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        content = msg.content[0].text.strip()

        OUTPUT_DIR.mkdir(exist_ok=True)
        out = OUTPUT_DIR / f"leveraged_etf_{today}.md"
        out.write_text(content, encoding="utf-8")
        logger.info("레버리지 ETF 분석 저장: %s", out)
        return content, signals
