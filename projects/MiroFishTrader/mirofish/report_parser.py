"""MiroFish report parser.

Extracts long/short/neutral probabilities and a rationale summary
from free-form ReportAgent text output using keyword heuristics
and optional Claude API refinement.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


# Betting size table (mirrors CLAUDE.md formula)
_CONFIDENCE_TIERS = [
    (0.75, 1.0),   # ≥75% → full position
    (0.65, 0.6),   # ≥65% → medium
    (0.55, 0.3),   # ≥55% → small
    (0.00, 0.0),   # <55% → stay out
]
BASE_BET = 0.10  # 10%


@dataclass
class ParsedSignal:
    """Trading signal extracted from the MiroFish report."""

    long_prob: float
    short_prob: float
    neutral_prob: float
    direction: str          # "LONG" | "SHORT" | "NEUTRAL"
    confidence: float       # dominant probability
    position_size: float    # 0.0 – 0.10 (fraction of portfolio)
    rationale: str          # 1–3 sentence summary


def _extract_percentage(text: str, keyword: str) -> Optional[float]:
    """Find the first percentage number after a keyword.

    Searches for patterns like '롱 72%', 'long: 72%', 'LONG 0.72'.
    """
    pattern = rf"{keyword}[\s:：\-]*(\d+(?:\.\d+)?)\s*%"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return float(match.group(1)) / 100.0

    # Also try decimal form: 'long 0.72'
    pattern_dec = rf"{keyword}[\s:：\-]*(0\.\d+)"
    match = re.search(pattern_dec, text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def _extract_probabilities(text: str) -> tuple[float, float, float]:
    """Extract (long, short, neutral) probabilities from report text.

    Strategy:
      1. Look for explicit percentage labels (롱/long, 숏/short, 중립/neutral).
      2. If not found, count directional keywords and normalize.
    """
    long_kws    = ["롱", "long", "매수", "bullish", "상승", "bull"]
    short_kws   = ["숏", "short", "매도", "bearish", "하락", "bear"]
    neutral_kws = ["중립", "neutral", "횡보", "관망", "sideways"]

    # Try explicit extraction for each direction
    for kw in long_kws:
        val = _extract_percentage(text, kw)
        if val is not None:
            long_p = val
            break
    else:
        long_p = None

    for kw in short_kws:
        val = _extract_percentage(text, kw)
        if val is not None:
            short_p = val
            break
    else:
        short_p = None

    for kw in neutral_kws:
        val = _extract_percentage(text, kw)
        if val is not None:
            neutral_p = val
            break
    else:
        neutral_p = None

    # If all three found and they're reasonable, use them
    if long_p is not None and short_p is not None and neutral_p is not None:
        total = long_p + short_p + neutral_p
        if 0.9 <= total <= 1.1:
            # Normalize to sum to 1.0
            return long_p / total, short_p / total, neutral_p / total

    # If only two found, infer the third
    if long_p is not None and short_p is not None:
        neutral_p = max(0.0, 1.0 - long_p - short_p)
        return long_p, short_p, neutral_p

    # Fallback: keyword frequency analysis
    text_lower = text.lower()
    long_count    = sum(text_lower.count(k) for k in long_kws)
    short_count   = sum(text_lower.count(k) for k in short_kws)
    neutral_count = sum(text_lower.count(k) for k in neutral_kws)
    total = long_count + short_count + neutral_count

    if total == 0:
        return 0.33, 0.33, 0.34

    return (
        long_count    / total,
        short_count   / total,
        neutral_count / total,
    )


def _extract_rationale(text: str, max_sentences: int = 3) -> str:
    """Extract key rationale sentences from the report.

    Picks sentences containing directional keywords or probability numbers.
    """
    sentences = re.split(r"[.。\n]", text)
    scored: list[tuple[int, str]] = []
    signal_words = [
        "롱", "숏", "중립", "long", "short", "neutral",
        "%", "확률", "추세", "RSI", "MACD", "VIX", "금리",
    ]
    for sent in sentences:
        sent = sent.strip()
        if len(sent) < 10:
            continue
        score = sum(1 for w in signal_words if w.lower() in sent.lower())
        if score > 0:
            scored.append((score, sent))

    scored.sort(key=lambda x: -x[0])
    top = [s for _, s in scored[:max_sentences]]
    return " ".join(top) if top else text[:200].strip()


def _calc_position_size(confidence: float) -> float:
    """Calculate position size from confidence level."""
    for threshold, multiplier in _CONFIDENCE_TIERS:
        if confidence >= threshold:
            return round(BASE_BET * multiplier, 4)
    return 0.0


def parse_report(report_text: str) -> ParsedSignal:
    """Parse a MiroFish ReportAgent output into a structured trading signal.

    Args:
        report_text: Raw text from MiroFish ReportAgent.

    Returns:
        ParsedSignal with probabilities, direction, and position size.
    """
    long_p, short_p, neutral_p = _extract_probabilities(report_text)

    # Determine direction
    max_p = max(long_p, short_p, neutral_p)
    if max_p == long_p:
        direction = "LONG"
        confidence = long_p
    elif max_p == short_p:
        direction = "SHORT"
        confidence = short_p
    else:
        direction = "NEUTRAL"
        confidence = neutral_p

    position_size = _calc_position_size(confidence) if direction != "NEUTRAL" else 0.0
    rationale = _extract_rationale(report_text)

    return ParsedSignal(
        long_prob=round(long_p, 4),
        short_prob=round(short_p, 4),
        neutral_prob=round(neutral_p, 4),
        direction=direction,
        confidence=round(confidence, 4),
        position_size=position_size,
        rationale=rationale,
    )
