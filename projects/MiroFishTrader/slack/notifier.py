"""Slack notification module.

Sends formatted trading signals to a Slack channel via Webhook.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import requests

from mirofish.report_parser import ParsedSignal


_DIRECTION_EMOJI = {
    "LONG":    "🟢",
    "SHORT":   "🔴",
    "NEUTRAL": "🟡",
}


@dataclass
class SlackConfig:
    """Slack Webhook configuration."""

    webhook_url: str
    channel: str = "#investment-ideas"
    timeout: int = 10

    @classmethod
    def from_env(cls) -> "SlackConfig":
        """Load config from environment variables.

        Raises:
            EnvironmentError: If SLACK_WEBHOOK_URL is not set.
        """
        url = os.getenv("SLACK_WEBHOOK_URL")
        if not url:
            raise EnvironmentError("SLACK_WEBHOOK_URL is not set")
        return cls(
            webhook_url=url,
            channel=os.getenv("SLACK_CHANNEL", "#investment-ideas"),
        )


def _format_direction_line(signal: ParsedSignal) -> str:
    emoji = _DIRECTION_EMOJI.get(signal.direction, "⚪")
    pct = int(signal.confidence * 100)
    return f"{emoji} *{signal.direction}*  |  신뢰도: {pct}%"


def _format_position_line(signal: ParsedSignal) -> str:
    if signal.position_size == 0:
        return "포지션: 관망 (신뢰도 미달)"
    pct = round(signal.position_size * 100, 1)
    base_pct = round(0.10 * 100, 0)
    return f"포지션 크기: *{pct}%* (기본 {int(base_pct)}% × {signal.confidence:.0%})"


def _format_probability_line(signal: ParsedSignal) -> str:
    return (
        f"롱 {signal.long_prob:.0%} / "
        f"숏 {signal.short_prob:.0%} / "
        f"중립 {signal.neutral_prob:.0%}"
    )


def build_message(
    signal: ParsedSignal,
    date: str,
    ticker: str = "SPY ETF",
) -> dict:
    """Build a Slack message payload from a ParsedSignal.

    Args:
        signal: Parsed trading signal.
        date: Analysis date string (YYYY-MM-DD).
        ticker: Target instrument label.

    Returns:
        Slack API-compatible message dict.
    """
    text = (
        f"📊 *MiroFish 매매 판단 — {ticker}*\n"
        f"날짜: {date}\n\n"
        f"{_format_direction_line(signal)}\n"
        f"{_format_position_line(signal)}\n\n"
        f"_{signal.rationale}_\n\n"
        f"{_format_probability_line(signal)}"
    )
    return {"text": text}


def send_signal(
    signal: ParsedSignal,
    date: str,
    config: Optional[SlackConfig] = None,
    ticker: str = "SPY ETF",
) -> bool:
    """Send a trading signal to Slack.

    Args:
        signal: Parsed trading signal from report_parser.
        date: Analysis date string.
        config: Slack config. Loads from env if None.
        ticker: Target instrument label.

    Returns:
        True if the message was sent successfully, False otherwise.
    """
    if config is None:
        config = SlackConfig.from_env()

    payload = build_message(signal, date, ticker)
    resp = requests.post(
        config.webhook_url,
        json=payload,
        timeout=config.timeout,
    )
    return resp.status_code == 200


def send_error(
    error_message: str,
    config: Optional[SlackConfig] = None,
) -> bool:
    """Send an error notification to Slack.

    Args:
        error_message: Error description.
        config: Slack config. Loads from env if None.

    Returns:
        True if sent successfully.
    """
    if config is None:
        config = SlackConfig.from_env()

    payload = {"text": f"⚠️ *MiroFishTrader 오류*\n{error_message}"}
    resp = requests.post(
        config.webhook_url,
        json=payload,
        timeout=config.timeout,
    )
    return resp.status_code == 200
