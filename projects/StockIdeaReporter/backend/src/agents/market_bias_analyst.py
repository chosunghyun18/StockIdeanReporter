"""시장 바이어스 분석 에이전트.

VIX, SPY MA, 섹터 브레드스로 레짐(BULL/BEAR/SIDEWAYS/VOLATILE) 판단.
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

SECTOR_ETFS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLC", "XLY", "XLP", "XLU", "XLRE", "XLB"]


@dataclass
class MarketIndicators:
    vix: float
    spy_price: float
    spy_ma50: float
    spy_ma200: float
    mom_20d: float
    rsi_14: float
    macd_hist: float
    breadth_pct: float
    regime: str          # BULL / BEAR / SIDEWAYS / VOLATILE
    multiplier: float    # 0 / 1.0 / 1.3
    confidence: int      # 0-100


def _safe_float(val) -> float:
    try:
        v = float(val)
        return round(v, 4)
    except Exception:
        return 0.0


def collect_indicators() -> MarketIndicators:
    """VIX + SPY + 섹터 브레드스 수집."""
    vix_data = yf.download("^VIX", period="5d", progress=False, auto_adjust=True)
    vix = _safe_float(vix_data["Close"].iloc[-1])

    spy_data = yf.download("SPY", period="1y", progress=False, auto_adjust=True)
    close = spy_data["Close"].squeeze()
    spy_price = _safe_float(close.iloc[-1])
    spy_ma50  = _safe_float(close.rolling(50).mean().iloc[-1])
    spy_ma200 = _safe_float(close.rolling(200).mean().iloc[-1])
    mom_20d   = _safe_float((close.iloc[-1] / close.iloc[-22] - 1) * 100)

    if _TA_AVAILABLE:
        rsi_14   = _safe_float(ta.momentum.RSIIndicator(close).rsi().iloc[-1])
        macd_obj = ta.trend.MACD(close)
        macd_hist = _safe_float(macd_obj.macd_diff().iloc[-1])
    else:
        rsi_14    = 50.0
        macd_hist = 0.0

    # 섹터 브레드스: 1개월 수익률 양수 섹터 비율
    try:
        sec = yf.download(SECTOR_ETFS, period="1mo", progress=False, auto_adjust=True)["Close"]
        ret = sec.iloc[-1] / sec.iloc[0] - 1
        breadth_pct = _safe_float((ret > 0).mean() * 100)
    except Exception:
        breadth_pct = 50.0

    # 레짐 결정
    above_ma50  = spy_price > spy_ma50
    above_ma200 = spy_price > spy_ma200

    if vix > 35:
        regime, multiplier = "VOLATILE", 1.3
    elif not above_ma200 and mom_20d < -3:
        regime, multiplier = "BEAR", 1.0
    elif above_ma200 and above_ma50 and abs(mom_20d) < 1.5 and vix < 18:
        regime, multiplier = "SIDEWAYS", 0.0
    elif above_ma200:
        regime, multiplier = "BULL", 1.0
    else:
        regime, multiplier = "BEAR", 1.0

    # 신뢰도: 방향과 일치하는 신호 수
    checks = {
        "BULL":     [above_ma200, above_ma50, mom_20d > 0, rsi_14 > 50, macd_hist > 0],
        "BEAR":     [not above_ma200, not above_ma50, mom_20d < 0, rsi_14 < 50, macd_hist < 0],
        "SIDEWAYS": [vix < 18, abs(mom_20d) < 2, 40 < rsi_14 < 60, abs(macd_hist) < 0.5, True],
        "VOLATILE": [vix > 30, abs(mom_20d) > 3, True, True, True],
    }
    hits = sum(1 for c in checks.get(regime, []) if c)
    confidence = int(hits / 5 * 100)

    return MarketIndicators(
        vix=vix, spy_price=spy_price, spy_ma50=spy_ma50, spy_ma200=spy_ma200,
        mom_20d=mom_20d, rsi_14=rsi_14, macd_hist=macd_hist,
        breadth_pct=breadth_pct, regime=regime, multiplier=multiplier,
        confidence=confidence,
    )


class MarketBiasAnalyst:
    """시장 바이어스 분석 에이전트."""

    def __init__(self, client: Optional[anthropic.Anthropic] = None) -> None:
        self.client = client or anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    def analyze(self) -> tuple[str, MarketIndicators]:
        """레짐 분석 수행. (보고서 마크다운, 지표) 반환."""
        today = date.today().strftime("%Y-%m-%d")
        ind = collect_indicators()

        above_ma50_str  = "상회" if ind.spy_price > ind.spy_ma50  else "하회"
        above_ma200_str = "상회" if ind.spy_price > ind.spy_ma200 else "하회"

        regime_guide = {
            "BULL":      ("YES", f"{ind.multiplier}x", "0~20%",  "롱 포지션 위주"),
            "BEAR":      ("YES", f"{ind.multiplier}x", "20~40%", "숏 / 인버스 ETF"),
            "SIDEWAYS":  ("NO",  "0x",                  "100%",   "현금 보유"),
            "VOLATILE":  ("YES", f"{ind.multiplier}x", "20%",    "레버리지 ETF (방향 확실 시)"),
        }
        allow, mult, cash, strategy = regime_guide.get(ind.regime, ("NO", "0x", "100%", "현금"))

        prompt = f"""아래 시장 데이터를 바탕으로 시장 바이어스 분석 리포트를 **정확히 아래 포맷**으로 작성하세요.
설명 없이 마크다운 본문만 출력하세요.

=== 입력 데이터 ===
VIX: {ind.vix:.2f}
SPY: ${ind.spy_price:.2f} | MA50 ${ind.spy_ma50:.2f}({above_ma50_str}) | MA200 ${ind.spy_ma200:.2f}({above_ma200_str})
20일 모멘텀: {ind.mom_20d:+.2f}%
RSI(14): {ind.rsi_14:.1f}
MACD Histogram: {ind.macd_hist:+.4f}
섹터 브레드스: {ind.breadth_pct:.0f}% 상승
판단 레짐: {ind.regime} (신뢰도 {ind.confidence}%)

=== 출력 포맷 ===
## 시장 바이어스 분석 결과

### 분석 기준일: {today}

#### 현재 레짐: {ind.regime}

#### 주요 지표 현황
| 지표 | 값 | 해석 |
|------|----|------|
| VIX | {ind.vix:.2f} | [한 줄 해석] |
| SPY vs MA50/MA200 | {above_ma50_str}/{above_ma200_str} | [한 줄 해석] |
| 브레드스 | {ind.breadth_pct:.0f}% | [한 줄 해석] |
| 20일 모멘텀 | {ind.mom_20d:+.2f}% | [한 줄 해석] |
| RSI(14) | {ind.rsi_14:.1f} | [한 줄 해석] |

#### 레짐 신뢰도: {ind.confidence}%

#### 운용 지침
- 신규 포지션 허용: {allow}
- 배팅 Multiplier: {mult}
- 권장 현금 비중: {cash}
- 우선 전략: {strategy}

#### 핵심 리스크
[향후 1-2주 레짐 전환 이벤트 2-3가지, 각 한 줄]
"""
        msg = self.client.messages.create(
            model=_MODEL, max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        content = msg.content[0].text.strip()

        OUTPUT_DIR.mkdir(exist_ok=True)
        out = OUTPUT_DIR / f"market_bias_{today}.md"
        out.write_text(content, encoding="utf-8")
        logger.info("시장 바이어스 저장: %s", out)
        return content, ind
