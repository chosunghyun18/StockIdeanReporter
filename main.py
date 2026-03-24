"""투자 분석 멀티 에이전트 시스템 진입점.

사용법:
    python main.py --ticker 005930.KS --market KR
    python main.py --ticker AAPL --market US
"""
from __future__ import annotations

import argparse
import logging
import sys

from src.agents.orchestrator import Orchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> int:
    """메인 진입점.

    Returns:
        종료 코드 (0=성공, 1=실패)
    """
    parser = argparse.ArgumentParser(
        description="투자 분석 멀티 에이전트 시스템"
    )
    parser.add_argument(
        "--ticker",
        required=True,
        help="종목 코드 (예: 005930.KS, AAPL)",
    )
    parser.add_argument(
        "--market",
        choices=["KR", "US"],
        default="KR",
        help="시장 구분 (기본값: KR)",
    )
    args = parser.parse_args()

    ticker = args.ticker
    market = args.market

    # KR 종목 suffix 자동 보완
    if market == "KR" and not ticker.endswith((".KS", ".KQ")):
        ticker = f"{ticker}.KS"
        logger.info("KR 종목 suffix 추가: %s", ticker)

    logger.info("분석 시작: %s (%s)", ticker, market)

    orchestrator = Orchestrator()

    try:
        result = orchestrator.run(ticker=ticker, market=market)
    except Exception as e:
        logger.error("예상치 못한 오류: %s", e)
        return 1

    if result.error:
        logger.error("분석 실패: %s", result.error)
        return 1

    logger.info("분석 완료!")
    logger.info("Slack 전송: %s", "성공" if result.slack_sent else "미전송")
    print("\n" + "=" * 60)
    print("📊 투자 아이디어 요약")
    print("=" * 60)
    print(result.investment_idea[:500] + "..." if len(result.investment_idea) > 500 else result.investment_idea)

    return 0


if __name__ == "__main__":
    sys.exit(main())
