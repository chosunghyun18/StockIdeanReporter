"""각 에이전트 출력 리포트를 Slack으로 전송.

output/ 디렉토리의 .md 파일을 파싱해 에이전트 종류별 Block Kit 메시지로 전송한다.
중복 전송 방지: output/slack_sent_{ticker}_{date}.log 확인.

사용법:
  python -m src.slack.send_reports                   # 미전송 리포트만
  python -m src.slack.send_reports --force            # 전체 재전송
  python -m src.slack.send_reports --ticker NVDA      # 특정 종목만
  python -m src.slack.send_reports --type idea        # idea 리포트만
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.slack.client import SlackClient

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"

# ── 데이터 클래스 ──────────────────────────────────────────────────────────────

@dataclass
class InvestmentIdea:
    ticker: str
    name: str
    date: str
    inv_type: str
    thesis: str
    entry: str
    target1: str
    target2: str
    stop_loss: str
    risk_reward: str
    bull_case: str
    base_case: str
    bear_case: str
    long_pct: str = ""
    short_pct: str = ""


@dataclass
class PriceAnalysis:
    ticker: str
    name: str
    date: str
    current_price: str
    high_52w: str
    low_52w: str
    pct_from_high: str
    rsi: str
    macd: str
    macd_signal: str
    stoch_k: str
    bb_upper: str
    bb_lower: str
    atr: str
    ma20: str
    overall_signal: str = ""


@dataclass
class IndustryAnalysis:
    ticker: str
    name: str
    date: str
    sector: str
    macro_summary: str
    sector_trend: str
    key_risks: str


@dataclass
class MarketBiasReport:
    date: str
    regime: str
    confidence: str
    vix: str
    spy_vs_ma: str
    breadth: str
    momentum: str
    rsi: str
    allow: str
    multiplier: str
    cash_pct: str
    strategy: str
    risks: str


@dataclass
class LeveragedEtfReport:
    date: str
    regime: str
    positions_md: str    # 추천 포지션 테이블 (raw markdown)
    rationale: str
    avoidance: str
    monitoring: str


@dataclass
class ThematicEtfReport:
    date: str
    hot_themes: str
    positions_md: str
    catalysts: str
    rebalance: str
    rs_top: str
    rs_bottom: str


# ── 파서 ──────────────────────────────────────────────────────────────────────

def _first(pattern: str, text: str, group: int = 1, default: str = "", dotall: bool = False) -> str:
    flags = re.DOTALL if dotall else 0
    m = re.search(pattern, text, flags)
    return m.group(group).strip() if m else default


def _clean_md(s: str) -> str:
    """마크다운 볼드/이탤릭 기호 제거."""
    return re.sub(r"\*+", "", s).strip()


def parse_investment_idea(path: Path) -> InvestmentIdea | None:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None

    ticker   = _first(r"### 종목:.+?\((.+?)\)", content)
    name     = _first(r"### 종목: (.+?) \(", content)
    date     = _first(r"### 생성일: ([^\n]+)", content)
    inv_type = _first(r"### 투자 유형: ([^\n]+)", content)

    # 투자 테제: #### 투자 테제 와 --- 사이
    thesis_raw = _first(r"#### 투자 테제\n+(.+?)\n+---", content, dotall=True)
    # 첫 문장만 (300자 제한)
    thesis = re.sub(r"\*+", "", thesis_raw).split(".")[0][:300].strip()

    # 실행 계획 테이블 (같은 줄 안에서만 매칭)
    entry     = _clean_md(_first(r"\| 진입 구간\s*\|\s*\*\*([^\n*|]+?)\*\*", content))
    target1   = _clean_md(_first(r"\| 1차 목표가\s*\|\s*\*\*([^\n*|]+?)\*\*", content))
    target2   = _clean_md(_first(r"\| 2차 목표가\s*\|\s*\*\*([^\n*|]+?)\*\*", content))
    stop_loss = _clean_md(_first(r"\| 손절 기준\s*\|\s*\*\*([^\n*|]+?)\*\*", content))
    rr        = _clean_md(_first(r"\| 리스크-리워드\s*\|\s*\*\*([^\n*|]+?)\*\*", content))

    # 시나리오 — 두 가지 형식 지원
    # 형식1: "- **강세 (확률 X%)**:" (한 줄)  형식2: "**🟢 강세 시나리오..." (제목+본문)
    def _scenario(keyword: str) -> str:
        # 형식1: "- **강세 (확률 30%)**: 텍스트..."
        m = re.search(rf"-\s*\*\*{keyword}[^*]*\*\*\s*:?\s*([^\n]+)", content)
        if m:
            return re.sub(r"\*+", "", m.group(1)).strip()[:200]
        # 형식2: "**🟢 강세 시나리오 (확률 35%): 제목**\n- 내용\n- 내용"
        m = re.search(rf"\*\*[^*]*{keyword}[^*]*\*\*[^\n]*\n+((?:- [^\n]+\n?)+)", content)
        if m:
            lines = [l.lstrip("- ") for l in m.group(1).strip().splitlines() if l.strip()]
            return re.sub(r"\*+", "", " ".join(lines[:2])).strip()[:200]
        return ""

    bull_case = _scenario("강세")
    base_case = _scenario("기본")
    bear_case = _scenario("약세")

    # 롱/숏 확률 (있으면)
    long_pct  = _first(r"롱\s*확률.*?(\d+)%", content)
    short_pct = _first(r"숏\s*확률.*?(\d+)%", content)

    return InvestmentIdea(
        ticker=ticker, name=name, date=date, inv_type=inv_type,
        thesis=thesis, entry=entry, target1=target1, target2=target2,
        stop_loss=stop_loss, risk_reward=rr,
        bull_case=bull_case, base_case=base_case, bear_case=bear_case,
        long_pct=long_pct, short_pct=short_pct,
    )


def parse_price_analysis(path: Path) -> PriceAnalysis | None:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None

    ticker   = _first(r"### 종목:.+?\((.+?)\)", content)
    name     = _first(r"### 종목: (.+?) \(", content)
    date     = _first(r"### 분석 기준일: ([^\n]+)", content)

    current  = _clean_md(_first(r"\| 현재가\s*\|\s*\*\*([^\n*|]+?)\*\*", content))
    high_52  = _clean_md(_first(r"\| 52주 최고가\s*\|\s*\*?\*?([^\n*|]+?)\*?\*?\s*\|", content))
    low_52   = _clean_md(_first(r"\| 52주 최저가\s*\|\s*\*?\*?([^\n*|]+?)\*?\*?\s*\|", content))
    pct_high = _clean_md(_first(r"\| 52주 고점 대비\s*\|\s*\*\*([^\n*|]+?)\*\*", content))

    # RSI: 소수점 포함 실제 값 (괄호 안 "(14)" 숫자 제외)
    rsi         = _first(r"RSI[^\d\n]*(\d{2,3}\.\d+)", content)
    macd        = _first(r"MACD[^\d\n-]*(-?[\d.]+)", content)
    macd_signal = _first(r"Signal[^\d\n-]*(-?[\d.]+)", content)
    stoch_k     = _first(r"Stochastic[^\d\n]*K[^\d\n]*(\d+\.\d+)", content)
    bb_upper    = _clean_md(_first(r"\| 상단[\s밴드]*\|\s*([^\n|]+?)\s*\|", content))
    bb_lower    = _clean_md(_first(r"\| 하단[\s밴드]*\|\s*([^\n|]+?)\s*\|", content))
    atr         = _first(r"ATR\([^\)]+\)[^\d\n]*(\$?[\d.]+)", content)
    ma20        = _clean_md(_first(r"\| MA20\s*\|\s*([^\n|]+?)\s*\|", content))

    # 종합 기술적 신호 추정 (RSI 기반)
    try:
        rsi_val = float(rsi)
        if rsi_val < 30:
            overall = "🟢 과매도 (반등 신호)"
        elif rsi_val < 45:
            overall = "🟡 약세 (매도 우위)"
        elif rsi_val > 70:
            overall = "🔴 과매수 (주의)"
        else:
            overall = "🟡 중립"
    except ValueError:
        overall = ""

    return PriceAnalysis(
        ticker=ticker, name=name, date=date,
        current_price=current, high_52w=high_52, low_52w=low_52,
        pct_from_high=pct_high, rsi=rsi, macd=macd,
        macd_signal=macd_signal, stoch_k=stoch_k,
        bb_upper=bb_upper, bb_lower=bb_lower, atr=atr, ma20=ma20,
        overall_signal=overall,
    )


def parse_industry_analysis(path: Path) -> IndustryAnalysis | None:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None

    ticker = _first(r"### 분석 대상:.+?\((.+?)\)", content)
    name   = _first(r"### 분석 대상: (.+?) \(", content)
    date   = _first(r"### 분석 일시: ([^\n]+)", content)
    sector = _first(r"### 섹터: ([^\n]+)", content)

    # 거시경제 환경 첫 단락
    macro = _first(r"#### 거시경제 환경\n+\*\*[^*\n]+\*\*\n([^\n]+)", content)
    macro = re.sub(r"\*+", "", macro).strip()[:250]

    # 섹터 트렌드 첫 단락
    trend = _first(r"#### 섹터 트렌드\n+\*\*[^*\n]+\*\*\n([^\n]+)", content)
    trend = re.sub(r"\*+", "", trend).strip()[:250]

    # 핵심 리스크
    risks_raw = _first(r"(?:핵심 리스크|주요 리스크|리스크 요인)[^\n]*\n+((?:[-•].+\n?)+)", content, dotall=True)
    risks_lines = [l.lstrip("-• ").strip() for l in risks_raw.splitlines() if l.strip()][:3]
    risks = "\n".join(f"• {l}" for l in risks_lines)

    return IndustryAnalysis(
        ticker=ticker, name=name, date=date, sector=sector,
        macro_summary=macro, sector_trend=trend, key_risks=risks,
    )


def parse_market_bias(path: Path) -> MarketBiasReport | None:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None

    date_val   = _first(r"### 분석 기준일: ([^\n]+)", content)
    regime     = _first(r"#### 현재 레짐: ([^\n]+)", content)
    confidence = _first(r"레짐 신뢰도: (\d+)%", content)

    vix        = _first(r"\| VIX\s*\|\s*([\d.]+)\s*\|", content)
    spy_vs_ma  = _first(r"\| SPY vs MA50/MA200\s*\|\s*([^\n|]+?)\s*\|", content)
    breadth    = _first(r"\| 브레드스\s*\|\s*([^\n|]+?)\s*\|", content)
    momentum   = _first(r"\| 20일 모멘텀\s*\|\s*([^\n|]+?)\s*\|", content)
    rsi        = _first(r"\| RSI\(14\)\s*\|\s*([^\n|]+?)\s*\|", content)

    allow      = _first(r"신규 포지션 허용:\s*([^\n]+)", content)
    multiplier = _first(r"배팅 Multiplier:\s*([^\n]+)", content)
    cash_pct   = _first(r"권장 현금 비중:\s*([^\n]+)", content)
    strategy   = _first(r"우선 전략:\s*([^\n]+)", content)

    risks_raw  = _first(r"#### 핵심 리스크\n+((?:[-•\d].+\n?)+)", content, dotall=True)
    risks_lines = [l.lstrip("-• ").strip() for l in risks_raw.splitlines() if l.strip()][:3]
    risks = "\n".join(f"• {l}" for l in risks_lines)

    return MarketBiasReport(
        date=date_val, regime=regime, confidence=confidence,
        vix=vix, spy_vs_ma=spy_vs_ma, breadth=breadth,
        momentum=momentum, rsi=rsi,
        allow=allow, multiplier=multiplier, cash_pct=cash_pct,
        strategy=strategy, risks=risks,
    )


def parse_leveraged_etf(path: Path) -> LeveragedEtfReport | None:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None

    date_val = _first(r"### 분석 기준일: ([^\n]+)", content)
    regime   = _first(r"### 시장 레짐: ([^\n]+)", content)

    # 추천 포지션 테이블 — | ETF | 방향 | ... 로 시작하는 줄부터 빈 줄까지
    pos_raw  = _first(r"#### 추천 포지션\n+((?:\|.+\n?)+)", content, dotall=True)
    pos_lines = [l for l in pos_raw.splitlines() if l.strip().startswith("|")][:8]
    positions_md = "\n".join(pos_lines)

    rationale  = _first(r"#### 근거\n+([\s\S]+?)(?:\n####|\Z)", content, dotall=True)
    rationale  = re.sub(r"\*+", "", rationale).strip()[:400]

    avoidance  = _first(r"#### 회피 리스트[^\n]*\n+([\s\S]+?)(?:\n####|\Z)", content, dotall=True)
    avoidance  = re.sub(r"\*+", "", avoidance).strip()[:300]

    monitoring = _first(r"#### 모니터링 기준\n+([\s\S]+?)(?:\n####|\Z)", content, dotall=True)
    monitoring = re.sub(r"\*+", "", monitoring).strip()[:300]

    return LeveragedEtfReport(
        date=date_val, regime=regime,
        positions_md=positions_md, rationale=rationale,
        avoidance=avoidance, monitoring=monitoring,
    )


def parse_thematic_etf(path: Path) -> ThematicEtfReport | None:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None

    date_val    = _first(r"### 분석 기준일: ([^\n]+)", content)

    hot_raw     = _first(r"#### 핫 테마[^\n]*\n+((?:[\d.].+\n?)+)", content, dotall=True)
    hot_lines   = [l.strip() for l in hot_raw.splitlines() if l.strip()][:3]
    hot_themes  = "\n".join(hot_lines)

    pos_raw     = _first(r"#### 추천 포지션\n+((?:\|.+\n?)+)", content, dotall=True)
    pos_lines   = [l for l in pos_raw.splitlines() if l.strip().startswith("|")][:8]
    positions_md = "\n".join(pos_lines)

    catalysts   = _first(r"#### 촉매 이벤트[^\n]*\n+([\s\S]+?)(?:\n####|\Z)", content, dotall=True)
    catalysts   = re.sub(r"\*+", "", catalysts).strip()[:300]

    rebalance   = _first(r"#### 리밸런싱 알림\n+([\s\S]+?)(?:\n####|\Z)", content, dotall=True)
    rebalance   = re.sub(r"\*+", "", rebalance).strip()[:200]

    rs_top      = _first(r"상위 테마:\s*([^\n]+)", content)
    rs_bottom   = _first(r"하위 테마:\s*([^\n]+)", content)

    return ThematicEtfReport(
        date=date_val, hot_themes=hot_themes,
        positions_md=positions_md, catalysts=catalysts,
        rebalance=rebalance, rs_top=rs_top, rs_bottom=rs_bottom,
    )


# ── Block Kit 빌더 ───────────────────────────────────────────────────────────

def _section(text: str) -> dict:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}

def _header(text: str) -> dict:
    return {"type": "header", "text": {"type": "plain_text", "text": text}}

def _divider() -> dict:
    return {"type": "divider"}

def _context(text: str) -> dict:
    return {"type": "context", "elements": [{"type": "mrkdwn", "text": text}]}


def build_investment_idea_blocks(d: InvestmentIdea) -> list[dict]:
    type_emoji = {"단기": "🔴", "중기": "🟡", "장기": "🟢"}.get(
        d.inv_type.split()[0] if d.inv_type else "", "⚪"
    )
    long_short = ""
    if d.long_pct or d.short_pct:
        long_short = f"  |  📊 롱 {d.long_pct}% / 숏 {d.short_pct}%"

    blocks: list[dict] = [
        _header("💡 투자 아이디어 리포트"),
        _section(f"*{d.name}* (`{d.ticker}`) | {d.date} | {type_emoji} {d.inv_type}{long_short}"),
        _divider(),
        _section(f"*📌 투자 테제*\n{d.thesis}…"),
        _divider(),
        _section(
            f"*🎯 실행 계획*\n"
            f"진입: `{d.entry}`  |  목표1: `{d.target1}`  |  목표2: `{d.target2}`\n"
            f"손절: `{d.stop_loss}`  |  R/R: *{d.risk_reward}*"
        ),
    ]

    if d.bull_case or d.base_case or d.bear_case:
        blocks += [
            _divider(),
            _section(
                f"*📈 시나리오*\n"
                f"🟢 강세: {d.bull_case or 'N/A'}\n"
                f"🟡 기본: {d.base_case or 'N/A'}\n"
                f"🔴 약세: {d.bear_case or 'N/A'}"
            ),
        ]

    blocks.append(_context("_Generated by Claude Investment Agent — idea-generator_"))
    return blocks


def build_price_analysis_blocks(d: PriceAnalysis) -> list[dict]:
    blocks: list[dict] = [
        _header("📈 주가 분석 리포트"),
        _section(f"*{d.name}* (`{d.ticker}`) | {d.date}"),
        _divider(),
        _section(
            f"*💰 현재가 정보*\n"
            f"현재가: `{d.current_price}`  |  52주 고점: `{d.high_52w}`  |  52주 저점: `{d.low_52w}`\n"
            f"고점 대비: *{d.pct_from_high}*  |  MA20: `{d.ma20}`"
        ),
        _divider(),
        _section(
            f"*📊 기술적 지표*\n"
            f"RSI(14): `{d.rsi}`  |  MACD: `{d.macd}` / Signal: `{d.macd_signal}`\n"
            f"Stoch-K: `{d.stoch_k}`  |  BB 상단: `{d.bb_upper}` / 하단: `{d.bb_lower}`\n"
            f"ATR: `{d.atr}`"
        ),
    ]
    if d.overall_signal:
        blocks.append(_section(f"*🔍 종합 신호*: {d.overall_signal}"))
    blocks.append(_context("_Generated by Claude Investment Agent — price-analyst_"))
    return blocks


def build_market_bias_blocks(d: MarketBiasReport) -> list[dict]:
    regime_emoji = {"BULL": "🐂", "BEAR": "🐻", "SIDEWAYS": "😴", "VOLATILE": "⚡"}.get(d.regime, "❓")
    blocks: list[dict] = [
        _header(f"{regime_emoji} 시장 바이어스 분석 결과"),
        _section(f"*레짐:* {d.regime}  |  *기준일:* {d.date}  |  *신뢰도:* {d.confidence}%"),
        _divider(),
        _section(
            f"*📊 주요 지표*\n"
            f"VIX: `{d.vix}`  |  SPY vs MA: `{d.spy_vs_ma}`\n"
            f"브레드스: `{d.breadth}`  |  20일 모멘텀: `{d.momentum}`  |  RSI: `{d.rsi}`"
        ),
        _divider(),
        _section(
            f"*🎯 운용 지침*\n"
            f"신규 포지션: *{d.allow}*  |  Multiplier: *{d.multiplier}*\n"
            f"현금 비중: *{d.cash_pct}*  |  전략: *{d.strategy}*"
        ),
    ]
    if d.risks:
        blocks += [_divider(), _section(f"*⚠️ 핵심 리스크*\n{d.risks}")]
    blocks.append(_context("_Generated by Claude Investment Agent — market-bias-analyst_"))
    return blocks


def build_leveraged_etf_blocks(d: LeveragedEtfReport) -> list[dict]:
    blocks: list[dict] = [
        _header("⚡ 레버리지 ETF 분석 결과"),
        _section(f"*기준일:* {d.date}  |  *시장 레짐:* {d.regime}"),
        _divider(),
    ]
    if d.positions_md:
        # 테이블을 코드블록으로 표시
        blocks.append(_section(f"*📋 추천 포지션*\n```\n{d.positions_md}\n```"))
        blocks.append(_divider())
    if d.rationale:
        blocks.append(_section(f"*📌 근거*\n{d.rationale}"))
    if d.avoidance:
        blocks += [_divider(), _section(f"*🚫 회피 리스트*\n{d.avoidance}")]
    if d.monitoring:
        blocks += [_divider(), _section(f"*👁 모니터링 기준*\n{d.monitoring}")]
    blocks.append(_context("_Generated by Claude Investment Agent — leveraged-etf-analyst_"))
    return blocks


def build_thematic_etf_blocks(d: ThematicEtfReport) -> list[dict]:
    blocks: list[dict] = [
        _header("🎨 테마 ETF 분석 결과"),
        _section(f"*기준일:* {d.date}"),
        _divider(),
    ]
    if d.hot_themes:
        blocks.append(_section(f"*🔥 핫 테마*\n{d.hot_themes}"))
        blocks.append(_divider())
    if d.positions_md:
        blocks.append(_section(f"*📋 추천 포지션*\n```\n{d.positions_md}\n```"))
        blocks.append(_divider())
    if d.catalysts:
        blocks.append(_section(f"*📅 촉매 이벤트*\n{d.catalysts}"))
    if d.rebalance:
        blocks += [_divider(), _section(f"*🔄 리밸런싱 알림*\n{d.rebalance}")]
    if d.rs_top or d.rs_bottom:
        blocks += [
            _divider(),
            _section(f"*📈 상대 강도*\n상위: {d.rs_top}\n하위: {d.rs_bottom}"),
        ]
    blocks.append(_context("_Generated by Claude Investment Agent — thematic-etf-analyst_"))
    return blocks


def build_industry_analysis_blocks(d: IndustryAnalysis) -> list[dict]:
    blocks: list[dict] = [
        _header("🏭 산업 분석 리포트"),
        _section(f"*{d.name}* (`{d.ticker}`) | {d.date} | 섹터: *{d.sector}*"),
        _divider(),
    ]
    if d.macro_summary:
        blocks.append(_section(f"*🌐 거시경제 환경*\n{d.macro_summary}…"))
    if d.sector_trend:
        blocks.append(_section(f"*📡 섹터 트렌드*\n{d.sector_trend}…"))
    if d.key_risks:
        blocks += [_divider(), _section(f"*⚠️ 핵심 리스크*\n{d.key_risks}")]
    blocks.append(_context("_Generated by Claude Investment Agent — industry-analyst_"))
    return blocks


# ── 전송 로직 ─────────────────────────────────────────────────────────────────

def _log_path(ticker: str, date: str) -> Path:
    return OUTPUT_DIR / f"slack_sent_{ticker}_{date}.log"


def _already_sent(ticker: str, date: str, report_type: str) -> bool:
    lp = _log_path(ticker, date)
    if not lp.exists():
        return False
    return report_type in lp.read_text(encoding="utf-8")


def _mark_sent(ticker: str, date: str, report_type: str) -> None:
    lp = _log_path(ticker, date)
    with lp.open("a", encoding="utf-8") as f:
        from datetime import datetime
        f.write(f"{report_type}:{datetime.now().isoformat()}\n")


def send_all_pending(
    output_dir: Path = OUTPUT_DIR,
    force: bool = False,
    ticker_filter: str | None = None,
    type_filter: str | None = None,
) -> None:
    client = SlackClient()

    # ── 종목별 리포트 수집: (ticker, date) 그룹 ──────────────────────────────
    groups: dict[tuple[str, str], dict[str, Path]] = {}
    for path in sorted(output_dir.glob("*.md")):
        m = re.match(r"(investment_idea|price_analysis|industry_analysis)_(.+)_(\d{4}-\d{2}-\d{2})\.md", path.name)
        if not m:
            continue
        rtype, ticker, file_date = m.group(1), m.group(2), m.group(3)
        if ticker_filter and ticker != ticker_filter:
            continue
        key = (ticker, file_date)
        if key not in groups:
            groups[key] = {}
        groups[key][rtype] = path

    # ── 시장/ETF 단독 리포트 수집: date 키 ───────────────────────────────────
    solo_groups: dict[tuple[str, str], Path] = {}
    for path in sorted(output_dir.glob("*.md")):
        m = re.match(r"(market_bias|leveraged_etf|thematic_etf)_(\d{4}-\d{2}-\d{2})\.md", path.name)
        if not m:
            continue
        rtype, file_date = m.group(1), m.group(2)
        if ticker_filter:
            continue  # 종목 필터 시 시장 리포트는 skip
        solo_groups[(rtype, file_date)] = path

    if not groups and not solo_groups:
        print("전송할 리포트가 없습니다.")
        return

    type_order = ["industry_analysis", "price_analysis", "investment_idea"]
    type_labels = {
        "industry_analysis": "industry",
        "price_analysis":    "price",
        "investment_idea":   "idea",
    }
    type_emoji = {
        "industry_analysis": "🏭",
        "price_analysis":    "📈",
        "investment_idea":   "💡",
    }

    for (ticker, file_date), files in sorted(groups.items()):
        print(f"\n── {ticker} / {file_date} ──────────────────")
        for rtype in type_order:
            label = type_labels[rtype]
            if type_filter and type_filter not in (label, "stock"):
                continue
            if rtype not in files:
                continue
            if not force and _already_sent(ticker, file_date, label):
                print(f"  [{type_emoji[rtype]} {label}] 이미 전송됨 — skip")
                continue

            path = files[rtype]
            print(f"  [{type_emoji[rtype]} {label}] 파싱 중... ", end="", flush=True)

            try:
                if rtype == "investment_idea":
                    data = parse_investment_idea(path)
                    blocks = build_investment_idea_blocks(data) if data else None
                elif rtype == "price_analysis":
                    data = parse_price_analysis(path)
                    blocks = build_price_analysis_blocks(data) if data else None
                else:
                    data = parse_industry_analysis(path)
                    blocks = build_industry_analysis_blocks(data) if data else None

                if not blocks:
                    print("파싱 실패")
                    continue

                ok = client.send_blocks(blocks)
                if ok:
                    _mark_sent(ticker, file_date, label)
                    print("전송 완료 ✓")
                else:
                    print("전송 실패 ✗")

            except Exception as e:
                print(f"오류: {e}")
                logger.exception("전송 중 오류 발생: %s / %s / %s", ticker, file_date, rtype)

    # ── 시장/ETF 단독 리포트 전송 ─────────────────────────────────────────────
    solo_type_map = {
        "market_bias":    ("bias",     "🌐", parse_market_bias,    build_market_bias_blocks),
        "leveraged_etf":  ("lev_etf",  "⚡", parse_leveraged_etf,  build_leveraged_etf_blocks),
        "thematic_etf":   ("them_etf", "🎨", parse_thematic_etf,   build_thematic_etf_blocks),
    }
    solo_order = ["market_bias", "leveraged_etf", "thematic_etf"]

    for rtype in solo_order:
        matching = {k: v for k, v in solo_groups.items() if k[0] == rtype}
        if not matching:
            continue
        label, emoji, parser, builder = solo_type_map[rtype]
        if type_filter and type_filter not in (label, "etf", "bias"):
            continue

        for (_, file_date), path in sorted(matching.items()):
            print(f"\n── {rtype} / {file_date} ──────────────────")
            if not force and _already_sent(rtype, file_date, label):
                print(f"  [{emoji} {label}] 이미 전송됨 — skip")
                continue

            print(f"  [{emoji} {label}] 파싱 중... ", end="", flush=True)
            try:
                data = parser(path)
                blocks = builder(data) if data else None
                if not blocks:
                    print("파싱 실패")
                    continue
                ok = client.send_blocks(blocks)
                if ok:
                    _mark_sent(rtype, file_date, label)
                    print("전송 완료 ✓")
                else:
                    print("전송 실패 ✗")
            except Exception as e:
                print(f"오류: {e}")
                logger.exception("전송 중 오류 발생: %s / %s", rtype, file_date)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="에이전트 리포트를 Slack으로 전송")
    parser.add_argument("--force",  action="store_true", help="이미 전송된 리포트도 재전송")
    parser.add_argument("--ticker", help="특정 종목만 전송 (예: NVDA)")
    parser.add_argument("--type",   choices=["idea", "price", "industry", "bias", "lev_etf", "them_etf", "etf", "stock"], help="특정 리포트 타입만 전송")
    args = parser.parse_args()

    if not os.environ.get("SLACK_WEBHOOK_URL"):
        print("오류: SLACK_WEBHOOK_URL 환경변수를 설정하세요.")
        sys.exit(1)

    send_all_pending(
        force=args.force,
        ticker_filter=args.ticker,
        type_filter=args.type,
    )
    print("\n완료.")


if __name__ == "__main__":
    main()
