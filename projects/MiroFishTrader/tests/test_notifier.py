"""Tests for slack/notifier.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from mirofish.report_parser import ParsedSignal
from slack.notifier import (
    SlackConfig,
    build_message,
    send_signal,
    send_error,
    _format_direction_line,
    _format_position_line,
)


def _make_signal(**kwargs) -> ParsedSignal:
    defaults = dict(
        long_prob=0.72,
        short_prob=0.18,
        neutral_prob=0.10,
        direction="LONG",
        confidence=0.72,
        position_size=0.10,
        rationale="RSI 68 과매수 근접, MACD 골든크로스.",
    )
    defaults.update(kwargs)
    return ParsedSignal(**defaults)


# ── SlackConfig ───────────────────────────────────────────────────────────────

class TestSlackConfig:
    def test_from_env_raises_without_webhook(self, monkeypatch):
        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        with pytest.raises(EnvironmentError):
            SlackConfig.from_env()

    def test_from_env_reads_webhook(self, monkeypatch):
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        config = SlackConfig.from_env()
        assert config.webhook_url == "https://hooks.slack.com/test"

    def test_from_env_default_channel(self, monkeypatch):
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        monkeypatch.delenv("SLACK_CHANNEL", raising=False)
        config = SlackConfig.from_env()
        assert config.channel == "#investment-ideas"


# ── format helpers ────────────────────────────────────────────────────────────

class TestFormatHelpers:
    def test_long_direction_has_green_emoji(self):
        signal = _make_signal(direction="LONG", confidence=0.72)
        line = _format_direction_line(signal)
        assert "🟢" in line
        assert "LONG" in line
        assert "72%" in line

    def test_short_direction_has_red_emoji(self):
        signal = _make_signal(direction="SHORT", confidence=0.65)
        line = _format_direction_line(signal)
        assert "🔴" in line

    def test_neutral_shows_watchful_message(self):
        signal = _make_signal(direction="NEUTRAL", position_size=0.0)
        line = _format_position_line(signal)
        assert "관망" in line

    def test_position_size_shown(self):
        signal = _make_signal(direction="LONG", position_size=0.072, confidence=0.72)
        line = _format_position_line(signal)
        assert "7.2" in line


# ── build_message ─────────────────────────────────────────────────────────────

class TestBuildMessage:
    def test_returns_dict_with_text_key(self):
        msg = build_message(_make_signal(), "2024-03-15")
        assert "text" in msg
        assert isinstance(msg["text"], str)

    def test_contains_date(self):
        msg = build_message(_make_signal(), "2024-03-15")
        assert "2024-03-15" in msg["text"]

    def test_contains_ticker(self):
        msg = build_message(_make_signal(), "2024-03-15", ticker="SPY ETF")
        assert "SPY ETF" in msg["text"]

    def test_contains_rationale(self):
        signal = _make_signal(rationale="RSI 68 과매수 근접.")
        msg = build_message(signal, "2024-03-15")
        assert "RSI 68" in msg["text"]

    def test_contains_probability_summary(self):
        signal = _make_signal(long_prob=0.72, short_prob=0.18, neutral_prob=0.10)
        msg = build_message(signal, "2024-03-15")
        assert "72%" in msg["text"]
        assert "18%" in msg["text"]


# ── send_signal ───────────────────────────────────────────────────────────────

class TestSendSignal:
    def test_returns_true_on_200(self):
        config = SlackConfig(webhook_url="https://hooks.slack.com/test")
        mock_resp = MagicMock(status_code=200)
        with patch("slack.notifier.requests.post", return_value=mock_resp):
            result = send_signal(_make_signal(), "2024-03-15", config=config)
        assert result is True

    def test_returns_false_on_non_200(self):
        config = SlackConfig(webhook_url="https://hooks.slack.com/test")
        mock_resp = MagicMock(status_code=400)
        with patch("slack.notifier.requests.post", return_value=mock_resp):
            result = send_signal(_make_signal(), "2024-03-15", config=config)
        assert result is False

    def test_posts_to_correct_url(self):
        config = SlackConfig(webhook_url="https://hooks.slack.com/services/XYZ")
        mock_resp = MagicMock(status_code=200)
        with patch("slack.notifier.requests.post", return_value=mock_resp) as mock_post:
            send_signal(_make_signal(), "2024-03-15", config=config)
        call_url = mock_post.call_args[0][0]
        assert call_url == "https://hooks.slack.com/services/XYZ"

    def test_payload_contains_text(self):
        config = SlackConfig(webhook_url="https://hooks.slack.com/test")
        mock_resp = MagicMock(status_code=200)
        with patch("slack.notifier.requests.post", return_value=mock_resp) as mock_post:
            send_signal(_make_signal(), "2024-03-15", config=config)
        payload = mock_post.call_args[1]["json"]
        assert "text" in payload


# ── send_error ────────────────────────────────────────────────────────────────

class TestSendError:
    def test_error_message_in_payload(self):
        config = SlackConfig(webhook_url="https://hooks.slack.com/test")
        mock_resp = MagicMock(status_code=200)
        with patch("slack.notifier.requests.post", return_value=mock_resp) as mock_post:
            send_error("데이터 수집 실패", config=config)
        payload = mock_post.call_args[1]["json"]
        assert "데이터 수집 실패" in payload["text"]
