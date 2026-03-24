"""PeerComparator 단위 테스트."""
from __future__ import annotations

import pytest

from src.analysis.peer_comparator import (
    _safe_median,
    _discount,
    _assess_valuation,
)


class TestSafeMedian:
    def test_normal_values(self):
        result = _safe_median([10.0, 20.0, 30.0])
        assert result == pytest.approx(20.0)

    def test_filters_none(self):
        result = _safe_median([None, 10.0, 20.0])
        assert result == pytest.approx(15.0)

    def test_filters_outliers(self):
        # 1000 초과는 제외
        result = _safe_median([10.0, 1500.0, 20.0])
        assert result == pytest.approx(15.0)

    def test_all_none_returns_none(self):
        assert _safe_median([None, None]) is None

    def test_empty_returns_none(self):
        assert _safe_median([]) is None

    def test_single_value(self):
        assert _safe_median([15.0]) == pytest.approx(15.0)


class TestDiscount:
    def test_undervalued(self):
        # target=8, peer=10 → -20%
        result = _discount(8.0, 10.0)
        assert result == pytest.approx(-20.0)

    def test_overvalued(self):
        # target=12, peer=10 → +20%
        result = _discount(12.0, 10.0)
        assert result == pytest.approx(20.0)

    def test_none_target_returns_none(self):
        assert _discount(None, 10.0) is None

    def test_none_peer_returns_none(self):
        assert _discount(10.0, None) is None

    def test_zero_peer_returns_none(self):
        assert _discount(10.0, 0.0) is None


class TestAssessValuation:
    def test_undervalued(self):
        assert _assess_valuation(-30.0, -25.0) == "저평가"

    def test_overvalued(self):
        assert _assess_valuation(25.0, 30.0) == "고평가"

    def test_fair(self):
        assert _assess_valuation(-10.0, 5.0) == "적정"

    def test_no_data(self):
        assert _assess_valuation(None, None) == "데이터 부족"

    def test_one_none_uses_available(self):
        # per_disc=-30, pbr_disc=None → avg=-30 → 저평가
        assert _assess_valuation(-30.0, None) == "저평가"

    def test_boundary_exactly_minus_20(self):
        # avg = -20 → < -20 조건 미달, 적정
        assert _assess_valuation(-20.0, -20.0) == "적정"

    def test_boundary_exactly_plus_20(self):
        # avg = 20 → > 20 조건 미달, 적정
        assert _assess_valuation(20.0, 20.0) == "적정"
