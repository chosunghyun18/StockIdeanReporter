"""기본적 분석 모듈 테스트."""
import pytest

from src.analysis.fundamental import FundamentalAnalyzer, _avg_not_none
from src.data.financial_data import FundamentalData


def _make_data(**kwargs) -> FundamentalData:
    """테스트용 FundamentalData 생성."""
    defaults = dict(
        ticker="TEST",
        per=15.0,
        pbr=1.5,
        ev_ebitda=10.0,
        psr=2.0,
        roe=0.18,
        roa=0.09,
        operating_margin=0.12,
        net_margin=0.08,
        revenue_growth=0.10,
        earnings_growth=0.15,
        debt_to_equity=80.0,
        current_ratio=2.0,
        interest_coverage=None,
        dividend_yield=0.02,
        payout_ratio=0.30,
        eps=5000.0,
        forward_eps=5500.0,
    )
    defaults.update(kwargs)
    return FundamentalData(**defaults)


class TestFundamentalAnalyzer:
    """FundamentalAnalyzer 테스트."""

    def test_analyze_returns_summary(self):
        analyzer = FundamentalAnalyzer()
        data = _make_data()
        summary = analyzer.analyze(data, current_price=75000, sector="Technology")

        assert summary is not None
        assert summary.valuation in ("저평가", "적정", "고평가")
        assert summary.profitability in ("우수", "보통", "미흡")
        assert summary.growth in ("고성장", "성장", "정체", "역성장")
        assert summary.financial_health in ("건전", "보통", "위험")

    def test_undervalued_low_per(self):
        """낮은 PER → 저평가."""
        analyzer = FundamentalAnalyzer()
        data = _make_data(per=8.0, pbr=0.8)
        summary = analyzer.analyze(data, current_price=50000, sector="Technology")
        assert summary.valuation == "저평가"

    def test_overvalued_high_per(self):
        """높은 PER → 고평가."""
        analyzer = FundamentalAnalyzer()
        data = _make_data(per=80.0, pbr=5.0)
        summary = analyzer.analyze(data, current_price=50000, sector="Technology")
        assert summary.valuation == "고평가"

    def test_high_growth(self):
        """20% 이상 성장률 → 고성장."""
        analyzer = FundamentalAnalyzer()
        data = _make_data(revenue_growth=0.25, earnings_growth=0.30)
        summary = analyzer.analyze(data, current_price=50000)
        assert summary.growth == "고성장"

    def test_negative_growth(self):
        """음수 성장률 → 역성장."""
        analyzer = FundamentalAnalyzer()
        data = _make_data(revenue_growth=-0.10, earnings_growth=-0.20)
        summary = analyzer.analyze(data, current_price=50000)
        assert summary.growth == "역성장"

    def test_financial_risk(self):
        """고부채 + 낮은 유동비율 → 위험."""
        analyzer = FundamentalAnalyzer()
        data = _make_data(debt_to_equity=300.0, current_ratio=0.8)
        summary = analyzer.analyze(data, current_price=50000)
        assert summary.financial_health == "위험"

    def test_financial_healthy(self):
        """낮은 부채 + 높은 유동비율 → 건전."""
        analyzer = FundamentalAnalyzer()
        data = _make_data(debt_to_equity=50.0, current_ratio=3.0)
        summary = analyzer.analyze(data, current_price=50000)
        assert summary.financial_health == "건전"

    def test_target_price_with_eps(self):
        """EPS 있으면 목표가 계산."""
        analyzer = FundamentalAnalyzer()
        data = _make_data(forward_eps=5000.0)
        summary = analyzer.analyze(data, current_price=50000, sector="Technology")
        assert summary.target_price_low is not None
        assert summary.target_price_high is not None
        assert summary.target_price_low < summary.target_price_high

    def test_target_price_none_without_eps(self):
        """EPS 없으면 목표가 없음."""
        analyzer = FundamentalAnalyzer()
        data = _make_data(eps=None, forward_eps=None)
        summary = analyzer.analyze(data, current_price=50000)
        assert summary.target_price_low is None
        assert summary.target_price_high is None

    def test_key_metrics_has_required_keys(self):
        """key_metrics에 필수 키 포함."""
        analyzer = FundamentalAnalyzer()
        data = _make_data()
        summary = analyzer.analyze(data, current_price=50000)
        required = {"PER", "PBR", "ROE", "ROA", "영업이익률", "배당수익률"}
        assert required.issubset(summary.key_metrics.keys())

    def test_none_per_defaults_to_fair(self):
        """PER None 시 기본 평가 '적정'."""
        analyzer = FundamentalAnalyzer()
        data = _make_data(per=None, pbr=None)
        summary = analyzer.analyze(data, current_price=50000)
        assert summary.valuation == "적정"


class TestHelpers:
    """헬퍼 함수 테스트."""

    def test_avg_not_none_basic(self):
        assert _avg_not_none([1.0, 2.0, 3.0]) == pytest.approx(2.0)

    def test_avg_not_none_filters_none(self):
        assert _avg_not_none([None, 2.0, None, 4.0]) == pytest.approx(3.0)

    def test_avg_not_none_all_none(self):
        assert _avg_not_none([None, None]) is None

    def test_avg_not_none_empty(self):
        assert _avg_not_none([]) is None
