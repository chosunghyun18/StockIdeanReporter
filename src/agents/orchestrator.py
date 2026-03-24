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
from .peer_analyst import PeerAnalyst
from .price_analyst import PriceAnalyst
from .reporter import Reporter
from .stock_screener import StockScreener, ScreeningResult

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
        self.peer_analyst = PeerAnalyst(client=client)
        self.idea_generator = IdeaGenerator(client=client)
        self.reporter = Reporter(
            webhook_url=slack_webhook_url,
            channel=slack_channel,
        )
        self.screener = StockScreener()

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

    def run_discovery(
        self,
        markets: list[str] | None = None,
        top_n: int = 5,
    ) -> list[AnalysisResult]:
        """종목 자동 발굴 후 전체 분석 파이프라인 실행.

        Args:
            markets: 대상 시장 리스트 (None이면 ["KR", "US"])
            top_n: 발굴 종목 수

        Returns:
            AnalysisResult 리스트 (발굴 종목 수만큼)
        """
        markets = markets or ["KR", "US"]
        logger.info("자동 발굴 시작: %s (top %d)", markets, top_n)

        screening: ScreeningResult = self.screener.screen(markets=markets, top_n=top_n)

        if not screening.top_candidates:
            logger.warning("스크리닝 결과 없음")
            return []

        results: list[AnalysisResult] = []
        for candidate in screening.top_candidates:
            ticker = candidate.drop.ticker
            market = candidate.drop.market
            swing_ctx = screening.swing_context(candidate)
            logger.info("[%d/%d] 분석: %s", candidate.rank, top_n, ticker)
            result = self._run_with_context(ticker, market, swing_ctx, candidate)
            results.append(result)

        logger.info("자동 발굴 완료: %d 종목 분석", len(results))
        return results

    def _run_with_context(
        self,
        ticker: str,
        market: str,
        swing_context: str,
        candidate,
    ) -> AnalysisResult:
        """스크리닝 맥락을 포함한 단일 종목 분석."""
        logger.info("분석 시작: %s (%s)", ticker, market)

        industry_result, price_result, peer_result = self._run_triple_parallel(ticker, market)

        if isinstance(industry_result, Exception) or isinstance(price_result, Exception):
            error_msg = f"분석 실패: {industry_result if isinstance(industry_result, Exception) else price_result}"
            self.reporter.send_error(ticker, error_msg)
            return AnalysisResult(
                ticker=ticker, market=market,
                industry_analysis="", price_analysis="",
                investment_idea="", slack_sent=False, error=error_msg,
            )

        peer_text = str(peer_result) if not isinstance(peer_result, Exception) else ""
        sentiment_text = candidate.sentiment.summary if candidate.sentiment else ""

        try:
            investment_idea = self.idea_generator.generate(
                ticker=ticker,
                industry_analysis=str(industry_result),
                price_analysis=str(price_result),
                peer_analysis=peer_text,
                sentiment_summary=sentiment_text,
                swing_context=swing_context,
            )
        except Exception as e:
            error_msg = f"아이디어 생성 실패: {e}"
            self.reporter.send_error(ticker, error_msg)
            return AnalysisResult(
                ticker=ticker, market=market,
                industry_analysis=str(industry_result),
                price_analysis=str(price_result),
                investment_idea="", slack_sent=False, error=error_msg,
            )

        report_fields = self.idea_generator.parse_report_fields(investment_idea, ticker)
        slack_sent = self.reporter.send(ticker, report_fields)
        logger.info("분석 완료: %s (Slack: %s)", ticker, "성공" if slack_sent else "실패")

        return AnalysisResult(
            ticker=ticker, market=market,
            industry_analysis=str(industry_result),
            price_analysis=str(price_result),
            investment_idea=investment_idea,
            slack_sent=slack_sent,
        )

    def _run_triple_parallel(
        self, ticker: str, market: str
    ) -> tuple[str | Exception, str | Exception, str | Exception]:
        """산업/주가/경쟁사 분석 3개 병렬 실행."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            f_industry = executor.submit(self.industry_analyst.analyze, ticker, market)
            f_price = executor.submit(self.price_analyst.analyze, ticker, market)
            f_peer = executor.submit(self.peer_analyst.analyze, ticker, market)

            def _get(future):
                try:
                    return future.result(timeout=120)
                except Exception as e:
                    return e

            return _get(f_industry), _get(f_price), _get(f_peer)

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
