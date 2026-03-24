"""command_parser 단위 테스트."""
from __future__ import annotations

import pytest

from src.slack.command_parser import parse, _remove_mention


class TestRemoveMention:
    def test_removes_mention(self):
        assert _remove_mention("<@U12345> 분석 AAPL") == "분석 AAPL"

    def test_no_mention_unchanged(self):
        assert _remove_mention("분석 AAPL") == "분석 AAPL"

    def test_multiple_mentions(self):
        result = _remove_mention("<@U1> <@U2> 발굴 KR")
        assert "<@" not in result


class TestParseAnalyze:
    def test_kr_ticker_with_suffix(self):
        cmd = parse("분석 005930.KS KR")
        assert cmd.type == "analyze"
        assert cmd.ticker == "005930.KS"
        assert cmd.market == "KR"

    def test_kr_ticker_without_suffix(self):
        cmd = parse("분석 005930 KR")
        assert cmd.type == "analyze"
        assert "005930" in cmd.ticker

    def test_us_ticker(self):
        cmd = parse("분석 AAPL US")
        assert cmd.type == "analyze"
        assert cmd.ticker == "AAPL"
        assert cmd.market == "US"

    def test_us_ticker_no_market_keyword(self):
        cmd = parse("분석 NVDA")
        assert cmd.type == "analyze"
        assert cmd.ticker == "NVDA"

    def test_mention_then_analyze(self):
        cmd = parse("<@U12345> 분석 TSLA US")
        assert cmd.type == "analyze"
        assert cmd.ticker == "TSLA"

    def test_ticker_only_triggers_analyze(self):
        cmd = parse("AAPL")
        assert cmd.type == "analyze"
        assert cmd.ticker == "AAPL"


class TestParseDiscover:
    def test_discover_kr(self):
        cmd = parse("발굴 KR")
        assert cmd.type == "discover"
        assert "KR" in cmd.markets

    def test_discover_us(self):
        cmd = parse("발굴 US")
        assert cmd.type == "discover"
        assert "US" in cmd.markets

    def test_discover_both_markets(self):
        cmd = parse("발굴 KR US")
        assert cmd.type == "discover"
        assert "KR" in cmd.markets
        assert "US" in cmd.markets

    def test_discover_top_n(self):
        cmd = parse("발굴 KR top 3")
        assert cmd.type == "discover"
        assert cmd.top_n == 3

    def test_discover_top_n_korean(self):
        cmd = parse("발굴 KR 5개")
        assert cmd.top_n == 5

    def test_discover_default_top_n(self):
        cmd = parse("발굴 KR")
        assert cmd.top_n == 5

    def test_discover_screening_keyword(self):
        cmd = parse("스크리닝 KR")
        assert cmd.type == "discover"

    def test_discover_drop_keyword(self):
        cmd = parse("급락 종목 찾아줘 KR")
        assert cmd.type == "discover"


class TestParseHelp:
    def test_help_korean(self):
        assert parse("도움말").type == "help"

    def test_help_english(self):
        assert parse("help").type == "help"

    def test_usage(self):
        assert parse("사용법").type == "help"


class TestParseUnknown:
    def test_random_text(self):
        cmd = parse("안녕하세요")
        assert cmd.type == "unknown"

    def test_empty_string(self):
        cmd = parse("")
        assert cmd.type == "unknown"


class TestTopNBounds:
    def test_top_n_max_10(self):
        cmd = parse("발굴 KR top 99")
        assert cmd.top_n == 10

    def test_top_n_min_1(self):
        cmd = parse("발굴 KR top 0")
        assert cmd.top_n == 1
