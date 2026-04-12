"""Tests for mirofish/report_parser.py."""

from __future__ import annotations

import pytest

from mirofish.report_parser import (
    parse_report,
    ParsedSignal,
    _extract_probabilities,
    _calc_position_size,
    BASE_BET,
)


# ── _extract_probabilities ────────────────────────────────────────────────────

class TestExtractProbabilities:
    def test_explicit_korean_percentages(self):
        text = "롱 72% / 숏 18% / 중립 10%"
        long_p, short_p, neutral_p = _extract_probabilities(text)
        assert long_p == pytest.approx(0.72, abs=0.01)
        assert short_p == pytest.approx(0.18, abs=0.01)
        assert neutral_p == pytest.approx(0.10, abs=0.01)

    def test_explicit_english_percentages(self):
        text = "Long: 65%, Short: 25%, Neutral: 10%"
        long_p, short_p, neutral_p = _extract_probabilities(text)
        assert long_p == pytest.approx(0.65, abs=0.01)
        assert short_p == pytest.approx(0.25, abs=0.01)

    def test_probabilities_sum_to_one(self):
        text = "롱 70% 숏 20% 중립 10%"
        probs = _extract_probabilities(text)
        assert sum(probs) == pytest.approx(1.0, abs=0.01)

    def test_two_found_infers_third(self):
        text = "롱 60%, 숏 30%"
        long_p, short_p, neutral_p = _extract_probabilities(text)
        assert neutral_p == pytest.approx(0.10, abs=0.01)

    def test_keyword_fallback_bullish_text(self):
        text = "상승 추세입니다. 매수 신호. bullish. 롱 포지션 권장. 롱 롱."
        long_p, short_p, neutral_p = _extract_probabilities(text)
        assert long_p > short_p

    def test_keyword_fallback_bearish_text(self):
        text = "하락 추세. 매도 신호. bearish. 숏 포지션. 숏 숏 숏."
        long_p, short_p, neutral_p = _extract_probabilities(text)
        assert short_p > long_p

    def test_empty_text_returns_equal_thirds(self):
        long_p, short_p, neutral_p = _extract_probabilities("")
        assert long_p == pytest.approx(0.33, abs=0.02)


# ── _calc_position_size ───────────────────────────────────────────────────────

class TestCalcPositionSize:
    def test_full_position_at_75_pct(self):
        assert _calc_position_size(0.75) == pytest.approx(BASE_BET * 1.0)

    def test_full_position_above_75(self):
        assert _calc_position_size(0.90) == pytest.approx(BASE_BET * 1.0)

    def test_medium_position_at_65_pct(self):
        assert _calc_position_size(0.65) == pytest.approx(BASE_BET * 0.6)

    def test_small_position_at_55_pct(self):
        assert _calc_position_size(0.55) == pytest.approx(BASE_BET * 0.3)

    def test_no_position_below_55_pct(self):
        assert _calc_position_size(0.50) == 0.0
        assert _calc_position_size(0.0) == 0.0


# ── parse_report ──────────────────────────────────────────────────────────────

class TestParseReport:
    def test_returns_parsed_signal(self):
        text = "롱 72% / 숏 18% / 중립 10%. RSI 68 과매수 근접, MACD 골든크로스."
        signal = parse_report(text)
        assert isinstance(signal, ParsedSignal)

    def test_direction_long(self):
        text = "롱 72% / 숏 18% / 중립 10%"
        signal = parse_report(text)
        assert signal.direction == "LONG"
        assert signal.long_prob == pytest.approx(0.72, abs=0.01)

    def test_direction_short(self):
        text = "롱 20% / 숏 68% / 중립 12%"
        signal = parse_report(text)
        assert signal.direction == "SHORT"

    def test_direction_neutral(self):
        text = "롱 25% / 숏 25% / 중립 50%"
        signal = parse_report(text)
        assert signal.direction == "NEUTRAL"
        assert signal.position_size == 0.0

    def test_position_size_zero_for_low_confidence(self):
        text = "롱 50% 숏 30% 중립 20%"
        signal = parse_report(text)
        assert signal.position_size == 0.0

    def test_position_size_full_for_high_confidence(self):
        text = "롱 80% / 숏 10% / 중립 10%"
        signal = parse_report(text)
        assert signal.position_size == pytest.approx(BASE_BET)

    def test_rationale_is_non_empty(self):
        text = "롱 72% / 숏 18% / 중립 10%. RSI 68 과매수 근접. MACD 골든크로스. VIX 14 안정."
        signal = parse_report(text)
        assert len(signal.rationale) > 5

    def test_probabilities_approximately_sum_to_one(self):
        text = "롱 70% / 숏 20% / 중립 10%"
        signal = parse_report(text)
        total = signal.long_prob + signal.short_prob + signal.neutral_prob
        assert total == pytest.approx(1.0, abs=0.02)

    def test_handles_empty_report(self):
        signal = parse_report("")
        assert signal.direction in {"LONG", "SHORT", "NEUTRAL"}
        assert 0 <= signal.long_prob <= 1

    def test_handles_real_style_report(self):
        text = """
        SPY ETF 분석 결과:

        거시경제 에이전트: 연준 금리 동결 기대로 상승 모멘텀 유효.
        실적 에이전트: S&P500 어닝 컨센서스 상향 조정 중.
        심리 에이전트: RSI 68로 과매수 근접, VIX 14 저변동성.

        종합 판단: 롱 72% / 숏 18% / 중립 10%
        포지션 크기: 7.2% (신뢰도 72%)
        """
        signal = parse_report(text)
        assert signal.direction == "LONG"
        assert signal.confidence >= 0.70
        assert signal.position_size > 0
