"""투자 분석 오케스트레이터.

industry-analyst, price-analyst를 병렬 실행 후
idea-generator, reporter 순으로 파이프라인 조율.
"""
from __future__ import annotations

import concurrent.futures
import logging
import os
from dataclasses import dataclass
from typing import Optional

import anthropic

from .idea_generator import IdeaGenerator
from .industry_analyst import IndustryAnalyst
from .price_analyst import PriceAnalyst
from .reporter import Reporter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnalysisResult:
    """전체 분석 파이프라인 결과."""

    ticker: str
    market: str
    industry_analysis: str
    price_analysis: str
    investment_idea: str
    slack_sent: bool
    error: Optional[str] = None


class Orchestrator:
    """투자 분석 파이프라인 총괄 조율자.

    워크플로우:
    1. industry-analyst + price-analyst 병렬 실행
    2. idea-generator 실행 (1번 결과 활용)
    3. reporter 실행 (Slack 전송)
    """

    def __init__(
        self,
        api_key: str | None = None,
        slack_webhook_url: str | None = None,
        slack_channel: str | None = None,
    ) -> None:
        """초기화.

        Args:
            api_key: Anthropic API 키 (None이면 환경변수 ANTHROPIC_API_KEY 사용)
            slack_webhook_url: Slack Webhook URL
            slack_channel: Slack 채널명
        """
        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        client = anthropic.Anthropic(api_key=resolved_key)

        self.industry_analyst = IndustryAnalyst(client=client)
        self.price_analyst = PriceAnalyst(client=client)
        self.idea_generator = IdeaGenerator(client=client)
        self.reporter = Reporter(
            webhook_url=slack_webhook_url,
            channel=slack_channel,
        )

    def run(self, ticker: str, market: str = "KR") -> AnalysisResult:
        """전체 분석 파이프라인 실행.

        Args:
            ticker: 종목 코드 (예: 005930.KS, AAPL)
            market: 시장 구분 (KR/US)

        Returns:
            AnalysisResult 객체
        """
        logger.info("분석 시작: %s (%s)", ticker, market)

        # Step 1: 병렬 분석 (산업 + 주가)
        industry_result, price_result = self._run_parallel_analysis(ticker, market)

        if isinstance(industry_result, Exception):
            error_msg = f"산업 분석 실패: {industry_result}"
            logger.error(error_msg)
            self.reporter.send_error(ticker, error_msg)
            return AnalysisResult(
                ticker=ticker, market=market,
                industry_analysis="", price_analysis="",
                investment_idea="", slack_sent=False, error=error_msg,
            )

        if isinstance(price_result, Exception):
            error_msg = f"주가 분석 실패: {price_result}"
            logger.error(error_msg)
            self.reporter.send_error(ticker, error_msg)
            return AnalysisResult(
                ticker=ticker, market=market,
                industry_analysis=str(industry_result), price_analysis="",
                investment_idea="", slack_sent=False, error=error_msg,
            )

        industry_analysis = str(industry_result)
        price_analysis = str(price_result)

        # Step 2: 투자 아이디어 생성
        try:
            investment_idea = self.idea_generator.generate(
                ticker=ticker,
                industry_analysis=industry_analysis,
                price_analysis=price_analysis,
            )
        except Exception as e:
            error_msg = f"아이디어 생성 실패: {e}"
            logger.error(error_msg)
            self.reporter.send_error(ticker, error_msg)
            return AnalysisResult(
                ticker=ticker, market=market,
                industry_analysis=industry_analysis,
                price_analysis=price_analysis,
                investment_idea="", slack_sent=False, error=error_msg,
            )

        # Step 3: Slack 전송
        report_fields = self.idea_generator.parse_report_fields(investment_idea, ticker)
        slack_sent = self.reporter.send(ticker, report_fields)

        logger.info("분석 완료: %s (Slack: %s)", ticker, "성공" if slack_sent else "실패")

        return AnalysisResult(
            ticker=ticker,
            market=market,
            industry_analysis=industry_analysis,
            price_analysis=price_analysis,
            investment_idea=investment_idea,
            slack_sent=slack_sent,
        )

    def _run_parallel_analysis(
        self,
        ticker: str,
        market: str,
    ) -> tuple[str | Exception, str | Exception]:
        """산업 분석과 주가 분석을 병렬 실행.

        Args:
            ticker: 종목 코드
            market: 시장 구분

        Returns:
            (industry_result, price_result) 튜플
            각 값은 성공 시 문자열, 실패 시 Exception
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            industry_future = executor.submit(
                self.industry_analyst.analyze, ticker, market
            )
            price_future = executor.submit(
                self.price_analyst.analyze, ticker, market
            )

            industry_result: str | Exception
            price_result: str | Exception

            try:
                industry_result = industry_future.result(timeout=120)
            except Exception as e:
                industry_result = e

            try:
                price_result = price_future.result(timeout=120)
            except Exception as e:
                price_result = e

        return industry_result, price_result
