"""ETF 분석 파이프라인.

market_bias → leveraged_etf + thematic_etf (병렬) → Slack 전송

사용법:
  python -m src.agents.etf_pipeline            # 전체 파이프라인
  python -m src.agents.etf_pipeline --no-slack  # Slack 전송 없이 파일만 생성
  python -m src.agents.etf_pipeline --only bias  # 특정 단계만
"""
from __future__ import annotations

import argparse
import concurrent.futures
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run_market_bias() -> str:
    from src.agents.market_bias_analyst import MarketBiasAnalyst
    analyst = MarketBiasAnalyst()
    content, ind = analyst.analyze()
    print(f"  [바이어스] 레짐: {ind.regime} | VIX: {ind.vix:.2f} | 신뢰도: {ind.confidence}%")
    return ind.regime


def run_leveraged_etf() -> None:
    from src.agents.leveraged_etf_analyst import LeveragedEtfAnalyst
    analyst = LeveragedEtfAnalyst()
    _, signals = analyst.analyze()
    print(f"  [레버리지 ETF] {len(signals)}개 기초지수 분석 완료")


def run_thematic_etf() -> None:
    from src.agents.thematic_etf_analyst import ThematicEtfAnalyst
    analyst = ThematicEtfAnalyst()
    _, scores = analyst.analyze()
    top3 = sorted(scores, key=lambda s: s.score, reverse=True)[:3]
    print(f"  [테마 ETF] {len(scores)}개 ETF 분석 — 상위: {', '.join(s.ticker for s in top3)}")


def run_send_reports() -> None:
    from src.slack.send_reports import send_all_pending
    send_all_pending(type_filter="etf")
    send_all_pending(type_filter="bias")


def main() -> None:
    parser = argparse.ArgumentParser(description="ETF 분석 파이프라인")
    parser.add_argument("--no-slack", action="store_true", help="Slack 전송 건너뜀")
    parser.add_argument(
        "--only",
        choices=["bias", "leveraged", "thematic", "send"],
        help="특정 단계만 실행",
    )
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("오류: ANTHROPIC_API_KEY 환경변수를 설정하세요.")
        sys.exit(1)

    only = args.only

    # 1단계: 시장 바이어스
    if not only or only == "bias":
        print("\n[1/3] 시장 바이어스 분석 중...")
        try:
            regime = run_market_bias()
        except Exception as e:
            print(f"  [바이어스] 오류: {e}")
            regime = "BULL"

    if only == "bias":
        print("완료.")
        return

    # 2단계: 레버리지 + 테마 ETF (병렬)
    if not only or only in ("leveraged", "thematic"):
        print("\n[2/3] ETF 분석 중 (병렬)...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures: list[concurrent.futures.Future] = []
            if not only or only == "leveraged":
                futures.append(executor.submit(run_leveraged_etf))
            if not only or only == "thematic":
                futures.append(executor.submit(run_thematic_etf))
            for f in concurrent.futures.as_completed(futures):
                try:
                    f.result()
                except Exception as e:
                    print(f"  [ETF] 오류: {e}")

    if only in ("leveraged", "thematic"):
        print("완료.")
        return

    # 3단계: Slack 전송
    if not args.no_slack and (not only or only == "send"):
        if not os.environ.get("SLACK_WEBHOOK_URL"):
            print("\n[3/3] SLACK_WEBHOOK_URL 미설정 — Slack 전송 건너뜀")
        else:
            print("\n[3/3] Slack 전송 중...")
            try:
                run_send_reports()
            except Exception as e:
                print(f"  [Slack] 오류: {e}")
    else:
        print("\n[3/3] Slack 전송 건너뜀 (--no-slack)")

    print("\n파이프라인 완료.")


if __name__ == "__main__":
    main()
