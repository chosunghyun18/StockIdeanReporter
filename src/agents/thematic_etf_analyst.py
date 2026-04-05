"""테마 ETF 분석 에이전트.

AI/반도체/클린에너지/사이버보안 등 주요 테마 ETF의 모멘텀 스코어 분석 후 롱/숏 추천.
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

logger = logging.getLogger(__name__)
OUTPUT_DIR = Path("output")
_MODEL = "claude-haiku-4-5-20251001"

# 분석 대상 테마 ETF
THEMATIC_UNIVERSE: dict[str, list[str]] = {
    "AI/기술":     ["QQQ", "ARKK", "BOTZ", "CHAT"],
    "반도체":      ["SOXX", "SMH"],
    "클린에너지":  ["ICLN", "LIT", "DRIV"],
    "사이버보안":  ["CIBR", "HACK"],
    "바이오/헬스": ["ARKG", "XBI"],
}

# 분석할 티커 목록 (중복 제거)
ALL_TICKERS = list({t for tickers in THEMATIC_UNIVERSE.values() for t in tickers})


def _safe_float(val) -> float:
    try:
        return round(float(val), 4)
    except Exception:
        return 0.0


@dataclass
class ThematicScore:
    ticker: str
    theme: str
    price: float
    mom_1m: float
    mom_3m: float
    flow_ratio: float   # 20일 평균 거래량 / 60일 평균
    pos_52w_pct: float  # 현재가 / 52주 고점 %
    score: int          # 0-100
    direction: str      # LONG / SHORT / WATCH


def calc_momentum_score(ticker: str, theme: str) -> ThematicScore | None:
    """테마 ETF 모멘텀 종합 점수 (0-100) 산출."""
    try:
        data = yf.download(ticker, period="6mo", progress=False, auto_adjust=True)
        if data.empty or len(data) < 63:
            return None
        close  = data["Close"].squeeze()
        volume = data["Volume"].squeeze()
    except Exception as e:
        logger.warning("다운로드 실패 %s: %s", ticker, e)
        return None

    price   = _safe_float(close.iloc[-1])
    mom_1m  = _safe_float((close.iloc[-1] / close.iloc[-21] - 1) * 100)
    mom_3m  = _safe_float((close.iloc[-1] / close.iloc[-63] - 1) * 100)

    vol_20  = float(volume.iloc[-20:].mean())
    vol_60  = float(volume.iloc[-60:].mean())
    flow_ratio = _safe_float(vol_20 / vol_60 if vol_60 > 0 else 1.0)

    high_52w   = float(close.rolling(252, min_periods=len(close)).max().iloc[-1])
    pos_52w    = _safe_float(close.iloc[-1] / high_52w * 100 if high_52w > 0 else 100)

    score = 0
    if mom_1m > 0:         score += 15
    if mom_3m > 0:         score += 20
    if mom_3m > 5:         score += 10
    if flow_ratio > 1.2:   score += 25
    if pos_52w > 90:       score += 30

    if score >= 65:
        direction = "LONG"
    elif score < 35:
        direction = "SHORT"
    else:
        direction = "WATCH"

    return ThematicScore(
        ticker=ticker, theme=theme, price=price,
        mom_1m=mom_1m, mom_3m=mom_3m, flow_ratio=flow_ratio,
        pos_52w_pct=pos_52w, score=score, direction=direction,
    )


def _betting_size_thematic(score: int) -> str:
    if score >= 80:
        return "8-12%"
    elif score >= 65:
        return "4-7%"
    elif score >= 55:
        return "2-3%"
    return "관망"


class ThematicEtfAnalyst:
    """테마 ETF 분석 에이전트."""

    def __init__(self, client: Optional[anthropic.Anthropic] = None) -> None:
        self.client = client or anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    def _read_market_regime(self) -> str:
        files = sorted(OUTPUT_DIR.glob("market_bias_*.md"), reverse=True)
        if not files:
            return "BULL"
        content = files[0].read_text(encoding="utf-8")
        import re
        m = re.search(r"현재 레짐:\s*(\w+)", content)
        return m.group(1) if m else "BULL"

    def analyze(self) -> tuple[str, list[ThematicScore]]:
        today  = date.today().strftime("%Y-%m-%d")
        regime = self._read_market_regime()

        # 티커별 테마 역방향 매핑
        ticker_theme: dict[str, str] = {}
        for theme, tickers in THEMATIC_UNIVERSE.items():
            for t in tickers:
                ticker_theme[t] = theme

        scores: list[ThematicScore] = []
        for ticker in ALL_TICKERS:
            theme = ticker_theme.get(ticker, "기타")
            s = calc_momentum_score(ticker, theme)
            if s:
                scores.append(s)

        scores.sort(key=lambda x: x.score, reverse=True)

        # 핫 테마 — 테마별 평균 스코어
        theme_scores: dict[str, list[int]] = {}
        for s in scores:
            theme_scores.setdefault(s.theme, []).append(s.score)
        hot_themes = sorted(
            theme_scores.items(),
            key=lambda kv: sum(kv[1]) / len(kv[1]),
            reverse=True,
        )[:3]

        hot_lines = "\n".join(
            f"{i+1}. {theme}: 평균 스코어 {sum(v)/len(v):.0f}점"
            for i, (theme, v) in enumerate(hot_themes)
        )

        # 추천 포지션 테이블
        table_rows = ""
        for s in scores:
            if regime == "SIDEWAYS" and s.direction == "LONG":
                continue
            if s.direction == "WATCH":
                continue
            size = _betting_size_thematic(s.score)
            table_rows += (
                f"| {s.ticker} | {s.theme} | {s.direction} | {s.score}% | {size} | "
                f"1M {s.mom_1m:+.1f}% / 3M {s.mom_3m:+.1f}% | "
                f"흐름 {s.flow_ratio:.2f}x |\n"
            )
        if not table_rows:
            table_rows = "| — | — | — | — | — | — | — |\n"

        # 리밸런싱 경고
        rebalance = "\n".join(
            f"- {s.ticker}: 모멘텀 약화 (스코어 {s.score}점), 비중 축소 고려"
            for s in scores if s.score < 40
        ) or "없음"

        # 상대 강도
        rs_top = ", ".join(s.ticker for s in scores[:3])
        rs_bot = ", ".join(s.ticker for s in reversed(scores[-3:]))

        prompt = f"""아래 데이터로 테마 ETF 분석 리포트를 **정확히 아래 포맷**으로 작성하세요.
설명 없이 마크다운 본문만 출력하세요.

=== 입력 데이터 ===
분석 기준일: {today}
시장 레짐: {regime}

핫 테마:
{hot_lines}

주요 ETF 모멘텀:
{chr(10).join(f"  {s.ticker}({s.theme}): 1M {s.mom_1m:+.1f}% / 3M {s.mom_3m:+.1f}% / 스코어 {s.score}" for s in scores)}

=== 출력 포맷 ===
## 테마 ETF 분석 결과

### 분석 기준일: {today}

#### 핫 테마 (자금 유입 상위)
{hot_lines}

#### 추천 포지션

| ETF | 테마 | 롱/숏 | 신뢰도 | 배팅 크기 | 모멘텀 | 자금흐름 |
|-----|------|-------|--------|----------|--------|---------|
{table_rows}
#### 촉매 이벤트 캘린더
[향후 1-2주 주요 이벤트 2-3가지]

#### 리밸런싱 알림
{rebalance}

#### 시장 대비 상대 강도 (RS)
- 상위 테마: {rs_top}
- 하위 테마: {rs_bot}
"""
        msg = self.client.messages.create(
            model=_MODEL, max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        content = msg.content[0].text.strip()

        OUTPUT_DIR.mkdir(exist_ok=True)
        out = OUTPUT_DIR / f"thematic_etf_{today}.md"
        out.write_text(content, encoding="utf-8")
        logger.info("테마 ETF 분석 저장: %s", out)
        return content, scores
