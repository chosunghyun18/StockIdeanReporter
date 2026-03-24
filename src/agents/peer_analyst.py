"""경쟁사 비교 분석 에이전트.

동종업계 밸류에이션 비교 데이터를 Claude API로 분석해 보고서를 생성한다.
"""
from __future__ import annotations

import logging
import os
from datetime import date
from pathlib import Path
from typing import Optional

import anthropic

from src.analysis.peer_comparator import PeerComparator, PeerComparisonResult

logger = logging.getLogger(__name__)
_OUTPUT_DIR = Path("output")
_MODEL = "claude-sonnet-4-6"


class PeerAnalyst:
    """경쟁사 비교 분석 에이전트."""

    def __init__(self, client: Optional[anthropic.Anthropic] = None) -> None:
        """초기화.

        Args:
            client: Anthropic 클라이언트 (None이면 환경변수 ANTHROPIC_API_KEY 사용)
        """
        self.client = client or anthropic.Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"]
        )
        self._comparator = PeerComparator()

    def analyze(self, ticker: str, market: str) -> str:
        """경쟁사 비교 분석 보고서 생성.

        Args:
            ticker: 종목 코드
            market: "KR" / "US"

        Returns:
            마크다운 분석 보고서 문자열
        """
        logger.info("경쟁사 분석 시작: %s", ticker)
        comparison = self._comparator.compare(ticker, market)
        prompt = _build_prompt(comparison)

        message = self.client.messages.create(
            model=_MODEL,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        result = message.content[0].text

        self._save(ticker, result)
        logger.info("경쟁사 분석 저장: %s", ticker)
        return result

    def _save(self, ticker: str, result: str) -> None:
        _OUTPUT_DIR.mkdir(exist_ok=True)
        today = date.today().strftime("%Y-%m-%d")
        path = _OUTPUT_DIR / f"peer_analysis_{ticker}_{today}.md"
        path.write_text(result, encoding="utf-8")


def _build_prompt(c: PeerComparisonResult) -> str:
    """경쟁사 비교 프롬프트 생성."""
    peer_str = ", ".join(c.peer_names) if c.peer_names else "데이터 없음"

    def fmt(v: Optional[float]) -> str:
        return f"{v:.1f}" if v is not None else "N/A"

    return f"""당신은 전문 주식 분석가입니다. 다음 데이터를 바탕으로 {c.ticker}의 동종업계 비교 분석 보고서를 작성하세요.

## 종목 정보
- 섹터: {c.sector} / 산업: {c.industry}
- 주요 비교 대상: {peer_str}

## 밸류에이션 비교
| 지표 | {c.ticker} | 동종업계 중앙값 | 할인율 |
|------|-----------|--------------|--------|
| PER  | {fmt(c.target_per)} | {fmt(c.peer_avg_per)} | {fmt(c.per_discount)}% |
| PBR  | {fmt(c.target_pbr)} | {fmt(c.peer_avg_pbr)} | {fmt(c.pbr_discount)}% |
| ROE  | {fmt(c.target_roe)} | {fmt(c.peer_avg_roe)} | - |

- 1개월 상대 강도: {c.relative_strength_1m:+.1f}%
- 밸류에이션 판단: **{c.relative_valuation}**

## 작성 지침
1. 저평가/고평가 원인 분석 (2~3문장)
2. 동종업계 대비 경쟁 우위/열위 핵심 요인 2가지
3. 스윙 매매(3~20일 관점) 측면에서 밸류에이션 매력도 평가
4. 주요 리스크 요인 1~2가지

한국어, 마크다운 형식, 400자 이내로 간결하게 작성하세요.
"""
