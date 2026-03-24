"""투자 아이디어 생성 에이전트.

산업 분석 + 주가 분석 결과를 통합하여 투자 아이디어 도출.
"""
from __future__ import annotations

import logging
import os
from datetime import date
from pathlib import Path

import anthropic

logger = logging.getLogger(__name__)

_OUTPUT_DIR = Path("output")
_MODEL = "claude-opus-4-6"


class IdeaGenerator:
    """투자 아이디어 생성 에이전트."""

    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        """초기화.

        Args:
            client: Anthropic 클라이언트 (None이면 환경변수 ANTHROPIC_API_KEY 사용)
        """
        self.client = client or anthropic.Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"]
        )

    def generate(
        self,
        ticker: str,
        industry_analysis: str,
        price_analysis: str,
    ) -> str:
        """투자 아이디어 생성.

        Args:
            ticker: 종목 코드
            industry_analysis: 산업 분석 결과 텍스트
            price_analysis: 주가 분석 결과 텍스트

        Returns:
            투자 아이디어 마크다운 문자열
        """
        today = date.today().strftime("%Y-%m-%d")
        prompt = _build_idea_prompt(ticker, industry_analysis, price_analysis, today)

        logger.info("투자 아이디어 생성 시작: %s", ticker)

        message = self.client.messages.create(
            model=_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        result = message.content[0].text

        # 결과 저장
        _OUTPUT_DIR.mkdir(exist_ok=True)
        output_path = _OUTPUT_DIR / f"investment_idea_{ticker}_{today}.md"
        output_path.write_text(result, encoding="utf-8")
        logger.info("투자 아이디어 저장: %s", output_path)

        return result

    def parse_report_fields(self, idea_text: str, ticker: str) -> dict:
        """생성된 아이디어 텍스트에서 Slack 전송용 필드 추출.

        Args:
            idea_text: 투자 아이디어 마크다운
            ticker: 종목 코드

        Returns:
            SlackClient.send_investment_report()에 전달할 딕셔너리
        """
        today = date.today().strftime("%Y-%m-%d")

        prompt = f"""다음 투자 아이디어 보고서에서 정보를 추출하여 JSON으로 반환해 주세요.

보고서:
{idea_text}

다음 JSON 형식으로만 응답하세요 (코드블록 없이):
{{
  "name": "기업명",
  "ticker": "{ticker}",
  "date": "{today}",
  "investment_type": "단기|중기|장기",
  "thesis": "투자 테제 2-3문장",
  "entry_price": "진입 가격대",
  "target1": "1차 목표가",
  "target2": "2차 목표가",
  "stop_loss": "손절 기준",
  "risk_reward": "R/R 비율",
  "bull_case": "강세 시나리오 한 줄",
  "base_case": "기본 시나리오 한 줄",
  "bear_case": "약세 시나리오 한 줄",
  "industry_score": 3,
  "technical_signal": "매수|중립|매도",
  "valuation": "저평가|적정|고평가",
  "opinion": "최종 투자 의견 한 줄"
}}"""

        message = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        import json
        try:
            return json.loads(message.content[0].text)
        except (json.JSONDecodeError, IndexError):
            logger.warning("JSON 파싱 실패, 기본값 반환")
            return {
                "name": ticker,
                "ticker": ticker,
                "date": today,
                "investment_type": "중기",
                "thesis": idea_text[:200],
                "entry_price": "N/A",
                "target1": "N/A",
                "target2": "N/A",
                "stop_loss": "N/A",
                "risk_reward": "N/A",
                "bull_case": "N/A",
                "base_case": "N/A",
                "bear_case": "N/A",
                "industry_score": 3,
                "technical_signal": "중립",
                "valuation": "적정",
                "opinion": "분석 결과를 참고하세요.",
            }


def _build_idea_prompt(
    ticker: str,
    industry_analysis: str,
    price_analysis: str,
    today: str,
) -> str:
    """투자 아이디어 생성 프롬프트."""
    return f"""당신은 전문 투자 분석가입니다. 아래 산업 분석과 주가 분석 결과를 종합하여 구체적인 투자 아이디어를 도출해 주세요.

=== 산업 분석 결과 ===
{industry_analysis}

=== 주가 분석 결과 ===
{price_analysis}

다음 형식으로 투자 아이디어를 작성해 주세요:

## 투자 아이디어

### 종목: [기업명] ({ticker})
### 생성일: {today}
### 투자 유형: [단기(1-4주)/중기(1-3개월)/장기(6개월+) 중 하나]

#### 투자 테제
[왜 지금 이 종목인지, 핵심 촉매(catalyst)는 무엇인지, 시장이 간과하는 점은 무엇인지 3-5문장]

#### 실행 계획
| 항목 | 내용 |
|------|------|
| 진입 구간 | [가격대] |
| 1차 목표가 | [가격] (+[%]) |
| 2차 목표가 | [가격] (+[%]) |
| 손절 기준 | [가격] (-[%]) |
| 리스크-리워드 | [비율] |

#### 시나리오별 전망
- 강세: [긍정적 촉매 발생 시 전망]
- 기본: [현재 흐름 지속 시 전망]
- 약세: [리스크 현실화 시 전망]

#### 핵심 모니터링 지표
1. [지표 1]
2. [지표 2]
3. [지표 3]

#### 투자 의견
[최종 한 줄 요약]
"""
