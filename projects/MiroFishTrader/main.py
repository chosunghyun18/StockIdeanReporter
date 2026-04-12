"""MiroFishTrader — main pipeline orchestrator.

Entry point that wires together:
  data collection → indicator calculation → seed building
  → MiroFish simulation → report parsing → Slack notification

Usage:
  python main.py                  # runs for today
  python main.py --date 2024-03-15
  python main.py --dry-run        # skips Slack send
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from data.collector import load_or_fetch
from signals.indicators import build_features
from mirofish.seed_builder import snapshot_from_features, build_all_seeds
from mirofish.client import MiroFishClient, MiroFishError
from mirofish.report_parser import parse_report
from slack.notifier import SlackConfig, send_signal, send_error

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def _build_project_id(target_date: str) -> str:
    return f"mirofish_trader_{target_date.replace('-', '')}"


def run(target_date: str, dry_run: bool = False) -> dict:
    """Execute the full analysis pipeline for a given date.

    Args:
        target_date: ISO date string (YYYY-MM-DD).
        dry_run: If True, skip the Slack notification.

    Returns:
        Dict with keys: direction, confidence, position_size, rationale.

    Raises:
        MiroFishError: If the MiroFish simulation or report fails.
    """
    log.info("=== MiroFishTrader pipeline start [%s] ===", target_date)

    # ── Step 1: Collect market data ───────────────────────────────────────────
    log.info("Step 1: Collecting market data...")
    spy_df = load_or_fetch("SPY")
    vix_df = load_or_fetch("^VIX")
    tnx_df = load_or_fetch("^TNX")

    # ── Step 2: Build features ────────────────────────────────────────────────
    log.info("Step 2: Calculating technical indicators...")
    features = build_features(spy_df)

    # ── Step 3: Build seed texts ──────────────────────────────────────────────
    log.info("Step 3: Building agent seed texts...")
    snapshot = snapshot_from_features(
        features,
        vix_series=vix_df["Close"],
        tnx_series=tnx_df["Close"],
        date=target_date,
    )
    seeds = build_all_seeds(snapshot)
    for agent, text in seeds.items():
        log.debug("[%s seed]\n%s", agent, text)

    # ── Step 4: MiroFish simulation ───────────────────────────────────────────
    log.info("Step 4: Running MiroFish simulation...")
    client = MiroFishClient(
        base_url=os.getenv("MIROFISH_BASE_URL", "http://localhost:5001"),
        timeout=int(os.getenv("MIROFISH_TIMEOUT", "300")),
    )
    project_id = _build_project_id(target_date)
    result = client.run_full_pipeline(
        project_id=project_id,
        seed_texts=seeds,
        max_rounds=10,
        report_requirement=(
            f"{target_date} 기준 SPY ETF의 롱/숏/중립 방향과 확률(%)을 분석하고 "
            "핵심 근거를 3문장 이내로 요약해줘."
        ),
    )
    log.info("Simulation done. report_id=%s", result.report_id)
    log.debug("[Report text]\n%s", result.report_text)

    # ── Step 5: Parse report ──────────────────────────────────────────────────
    log.info("Step 5: Parsing report...")
    signal = parse_report(result.report_text)
    log.info(
        "Signal: %s | confidence=%.0f%% | position=%.1f%%",
        signal.direction,
        signal.confidence * 100,
        signal.position_size * 100,
    )

    # ── Step 6: Notify Slack ──────────────────────────────────────────────────
    if dry_run:
        log.info("Step 6: [dry-run] Skipping Slack notification.")
    else:
        log.info("Step 6: Sending Slack notification...")
        config = SlackConfig.from_env()
        success = send_signal(signal, date=target_date, config=config)
        if success:
            log.info("Slack message sent.")
        else:
            log.warning("Slack send failed (non-200 response).")

    log.info("=== Pipeline complete ===")
    return {
        "direction":     signal.direction,
        "confidence":    signal.confidence,
        "position_size": signal.position_size,
        "rationale":     signal.rationale,
        "long_prob":     signal.long_prob,
        "short_prob":    signal.short_prob,
        "neutral_prob":  signal.neutral_prob,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="MiroFishTrader pipeline")
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Analysis date (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without sending Slack notification.",
    )
    args = parser.parse_args()

    try:
        result = run(target_date=args.date, dry_run=args.dry_run)
        print(f"\nResult: {result}")
    except MiroFishError as e:
        log.error("MiroFish error: %s", e)
        try:
            send_error(str(e))
        except Exception:
            pass
        sys.exit(1)
    except Exception as e:
        log.error("Unexpected error: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
