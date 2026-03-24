"""산업 분석 에이전트.

Claude API를 사용하여 산업/섹터 심층 분석 수행.
"""
from __future__ import annotations

import logging
import os
from datetime import date
from pathlib import Path

import anthropic

from src.data.stock_data import StockDataFetcher

logger = logging.getLogger(__name__)

_OUTPUT_DIR = Path("output")
_MODEL = "claude-sonnet-4-6"


class IndustryAnalyst:
    """산업/섹터 분석 에이전트."""

    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        """초기화.

        Args:
            client: Anthropic 클라이언트 (None이면 환경변수 ANTHROPIC_API_KEY 사용)
        """
        self.client = client or anthropic.Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"]
        )
        self.data_fetcher = StockDataFetcher()

    def analyze(self, ticker: str, market: str = "KR") -> str:
        """산업/섹터 분석 수행.

        Args:
            ticker: 종목 코드
            market: 시장 구분 (KR/US)

        Returns:
            분석 결과 마크다운 문자열

        Raises:
            ValueError: 종목 정보를 가져올 수 없는 경우
        """
        stock_info = self.data_fetcher.get_stock_info(ticker)
        sector = self.data_fetcher.get_sector(ticker)
        industry = self.data_fetcher.get_industry(ticker)
        today = date.today().strftime("%Y-%m-%d")

        prompt = _build_industry_prompt(
            ticker=ticker,
            name=stock_info.name,
            market=market,
            sector=sector,
            industry=industry,
            date=today,
        )

        logger.info("산업 분석 시작: %s (%s)", ticker, sector)

        message = self.client.messages.create(
            model=_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        result = message.content[0].text

        # 결과 저장
        _OUTPUT_DIR.mkdir(exist_ok=True)
        output_path = _OUTPUT_DIR / f"industry_analysis_{ticker}_{today}.md"
        output_path.write_text(result, encoding="utf-8")
        logger.info("산업 분석 저장: %s", output_path)

        return result


def _build_industry_prompt(
    ticker: str,
    name: str,
    market: str,
    sector: str,
    industry: str,
    date: str,
) -> str:
    """산업 분석 프롬프트 생성."""
    market_context = "국내 주식 (KRX)" if market == "KR" else "해외 주식 (NYSE/NASDAQ)"

    return f"""당신은 전문 산업 분석가입니다. 다음 종목의 산업/섹터를 심층 분석해 주세요.

종목 정보:
- 기업명: {name}
- 종목코드: {ticker}
- 시장: {market_context}
- 섹터: {sector}
- 산업: {industry}
- 분석일: {date}

다음 형식으로 분석 결과를 작성해 주세요:

## 산업 분석 결과

### 섹터: {sector}
### 분석 대상: {name} ({ticker})
### 분석 일시: {date}

#### 거시경제 환경
[금리, 환율, 인플레이션이 이 산업에 미치는 영향, 정부 정책 및 규제 동향]

#### 섹터 트렌드
[산업 성장률 및 전망, 기술 혁신, 국내외 수요/공급 동향]

#### 경쟁 구도
[주요 경쟁사, 시장점유율, 해당 기업의 경쟁 우위(moat), 신규 진입 위협]

#### 산업 리스크
[구조적 리스크, 규제 리스크, 사이클 리스크 등]

#### 종합 판단
- 산업 매력도: ⭐⭐⭐ (1-5점, 별로 표시)
- 핵심 인사이트: [1-3줄 요약]

사실에 기반하여 분석하되, 불확실한 내용은 명시해 주세요.
"""
