"""Slack 메시지에서 명령어를 파싱하는 모듈."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SlackCommand:
    """파싱된 슬랙 명령어."""

    type: str           # "analyze" | "discover" | "help" | "unknown"
    ticker: Optional[str] = None
    market: Optional[str] = None
    markets: Optional[list[str]] = None
    top_n: int = 5
    raw: str = ""


_KR_TICKERS = re.compile(r"\b(\d{6})(\.KS|\.KQ)?\b")
_US_TICKERS = re.compile(r"\b([A-Z]{1,5})\b")
_TOP_N = re.compile(r"(\d+)개|top[- ]?(\d+)", re.IGNORECASE)

_ANALYZE_KEYWORDS = ["분석", "analyze", "analysis", "봐줘", "알려줘"]
_DISCOVER_KEYWORDS = ["발굴", "찾아", "스크리닝", "screening", "discover", "급락"]
_HELP_KEYWORDS = ["도움말", "help", "사용법", "명령어"]

_MARKET_KW = {
    "KR": ["kr", "한국", "코스피", "kospi", "kosdaq", "코스닥", "국내"],
    "US": ["us", "미국", "nasdaq", "nyse", "나스닥", "해외"],
}


def parse(text: str) -> SlackCommand:
    """슬랙 메시지 텍스트에서 명령어 파싱.

    지원 형식:
        분석 005930 KR
        분석 AAPL US
        발굴 KR US top 3
        도움말

    Args:
        text: 슬랙 메시지 본문 (멘션 제거 후)

    Returns:
        SlackCommand
    """
    clean = _remove_mention(text).strip()
    lower = clean.lower()

    if any(kw in lower for kw in _HELP_KEYWORDS):
        return SlackCommand(type="help", raw=clean)

    if any(kw in lower for kw in _DISCOVER_KEYWORDS):
        return _parse_discover(clean, lower)

    if any(kw in lower for kw in _ANALYZE_KEYWORDS):
        return _parse_analyze(clean, lower)

    # 키워드 없어도 종목코드 있으면 분석으로 처리
    ticker, market = _extract_ticker(clean, lower)
    if ticker:
        return SlackCommand(type="analyze", ticker=ticker, market=market, raw=clean)

    return SlackCommand(type="unknown", raw=clean)


def _parse_analyze(clean: str, lower: str) -> SlackCommand:
    ticker, market = _extract_ticker(clean, lower)
    return SlackCommand(type="analyze", ticker=ticker, market=market or "KR", raw=clean)


def _parse_discover(clean: str, lower: str) -> SlackCommand:
    markets = _extract_markets(lower) or ["KR", "US"]
    top_n = _extract_top_n(lower)
    return SlackCommand(type="discover", markets=markets, top_n=top_n, raw=clean)


def _extract_ticker(clean: str, lower: str) -> tuple[Optional[str], Optional[str]]:
    # KR 종목 (6자리 숫자)
    kr_match = _KR_TICKERS.search(clean)
    if kr_match:
        code = kr_match.group(1)
        suffix = kr_match.group(2) or ".KS"
        return f"{code}{suffix}", "KR"

    # US 종목 (대문자 알파벳)
    # 명령어 키워드 제외
    skip = set(_ANALYZE_KEYWORDS + _DISCOVER_KEYWORDS + _HELP_KEYWORDS + ["KR", "US"])
    for word in clean.split():
        if word.upper() in skip:
            continue
        if _US_TICKERS.fullmatch(word) and word.isupper() and len(word) >= 2:
            market = _detect_market(lower) or "US"
            return word.upper(), market

    return None, _detect_market(lower)


def _detect_market(lower: str) -> Optional[str]:
    for market, keywords in _MARKET_KW.items():
        if any(kw in lower for kw in keywords):
            return market
    return None


def _extract_markets(lower: str) -> list[str]:
    markets: list[str] = []
    for market, keywords in _MARKET_KW.items():
        if any(kw in lower for kw in keywords):
            markets.append(market)
    return markets


def _extract_top_n(lower: str) -> int:
    m = _TOP_N.search(lower)
    if m:
        val = m.group(1) or m.group(2)
        return max(1, min(10, int(val)))
    return 5


def _remove_mention(text: str) -> str:
    """<@UXXXXXXX> 형태의 멘션 제거."""
    return re.sub(r"<@[A-Z0-9]+>", "", text).strip()
