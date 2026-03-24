"""투자 분석 멀티 에이전트 시스템 진입점.

사용법:
    # 종목 지정 분석
    python main.py --ticker 005930.KS --market KR
    python main.py --ticker AAPL --market US

    # 자동 발굴 (스윙 매매 급락 종목)
    python main.py --discover --market KR US --top-n 5
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
    parser = argparse.ArgumentParser(description="투자 분석 멀티 에이전트 시스템")
    parser.add_argument("--ticker", help="종목 코드 (예: 005930.KS, AAPL)")
    parser.add_argument(
        "--market", nargs="+", choices=["KR", "US"], default=["KR"],
        help="시장 구분 (기본값: KR, --discover 시 복수 가능)",
    )
    parser.add_argument(
        "--discover", action="store_true",
        help="종목 자동 발굴 모드 (스윙 매매 급락 종목)",
    )
    parser.add_argument(
        "--top-n", type=int, default=5,
        help="자동 발굴 시 분석 종목 수 (기본값: 5)",
    )
    args = parser.parse_args()

    if not args.discover and not args.ticker:
        parser.error("--ticker 또는 --discover 중 하나를 지정하세요.")

    orchestrator = Orchestrator()

    if args.discover:
        return _run_discovery(orchestrator, args.market, args.top_n)

    return _run_single(orchestrator, args.ticker, args.market[0])


def _run_single(orchestrator: Orchestrator, ticker: str, market: str) -> int:
    """단일 종목 분석."""
    if market == "KR" and not ticker.endswith((".KS", ".KQ")):
        ticker = f"{ticker}.KS"
        logger.info("KR 종목 suffix 추가: %s", ticker)

    logger.info("분석 시작: %s (%s)", ticker, market)

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
    idea = result.investment_idea
    print(idea[:500] + "..." if len(idea) > 500 else idea)
    return 0


def _run_discovery(orchestrator: Orchestrator, markets: list[str], top_n: int) -> int:
    """자동 발굴 모드."""
    logger.info("자동 발굴 시작: %s (top %d)", markets, top_n)

    try:
        results = orchestrator.run_discovery(markets=markets, top_n=top_n)
    except Exception as e:
        logger.error("자동 발굴 오류: %s", e)
        return 1

    if not results:
        logger.warning("발굴된 종목 없음")
        return 1

    print("\n" + "=" * 60)
    print(f"🔍 자동 발굴 완료: {len(results)}개 종목")
    print("=" * 60)
    for r in results:
        status = "✅ Slack 전송" if r.slack_sent else "⚠️ 미전송"
        print(f"  {r.ticker} ({r.market}) — {status}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
