"""기본적 분석 모듈.

밸류에이션, 수익성, 성장성, 재무 건전성 평가.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.data.financial_data import FundamentalData


@dataclass(frozen=True)
class FundamentalSummary:
    """기본적 분석 결과 요약."""

    ticker: str
    valuation: str      # "저평가" / "적정" / "고평가"
    valuation_score: int  # 1-5 (5=매우 저평가)
    profitability: str  # "우수" / "보통" / "미흡"
    growth: str         # "고성장" / "성장" / "정체" / "역성장"
    financial_health: str  # "건전" / "보통" / "위험"
    key_metrics: dict
    target_price_low: Optional[float]
    target_price_high: Optional[float]
    summary: str


# 섹터별 적정 PER 벤치마크 (대략값)
_SECTOR_PER_BENCHMARK: dict[str, float] = {
    "Technology": 30.0,
    "Consumer Cyclical": 20.0,
    "Healthcare": 25.0,
    "Financial Services": 15.0,
    "Communication Services": 22.0,
    "Industrials": 18.0,
    "Consumer Defensive": 20.0,
    "Energy": 12.0,
    "Basic Materials": 14.0,
    "Real Estate": 25.0,
    "Utilities": 18.0,
    "Unknown": 20.0,
}


class FundamentalAnalyzer:
    """기본적 분석기."""

    def analyze(
        self,
        data: FundamentalData,
        current_price: float,
        sector: str = "Unknown",
    ) -> FundamentalSummary:
        """재무 데이터를 바탕으로 기본적 분석을 수행한다.

        Args:
            data: FundamentalData 객체
            current_price: 현재 주가
            sector: 섹터명 (벤치마크 PER 적용에 사용)

        Returns:
            FundamentalSummary 객체
        """
        valuation, val_score = self._eval_valuation(data, sector)
        profitability = self._eval_profitability(data)
        growth = self._eval_growth(data)
        financial_health = self._eval_health(data)

        target_low, target_high = self._estimate_target_price(data, current_price, sector)

        key_metrics = self._build_key_metrics(data)
        summary = _build_summary(valuation, profitability, growth, financial_health)

        return FundamentalSummary(
            ticker=data.ticker,
            valuation=valuation,
            valuation_score=val_score,
            profitability=profitability,
            growth=growth,
            financial_health=financial_health,
            key_metrics=key_metrics,
            target_price_low=target_low,
            target_price_high=target_high,
            summary=summary,
        )

    def _eval_valuation(
        self,
        data: FundamentalData,
        sector: str,
    ) -> tuple[str, int]:
        """밸류에이션 평가."""
        benchmark_per = _SECTOR_PER_BENCHMARK.get(sector, 20.0)
        score = 3  # 기본 적정

        if data.per is not None:
            ratio = data.per / benchmark_per
            if ratio < 0.6:
                score = 5
            elif ratio < 0.8:
                score = 4
            elif ratio < 1.2:
                score = 3
            elif ratio < 1.5:
                score = 2
            else:
                score = 1

        if data.pbr is not None:
            if data.pbr < 1.0:
                score = min(5, score + 1)
            elif data.pbr > 3.0:
                score = max(1, score - 1)

        if score >= 4:
            return "저평가", score
        elif score <= 2:
            return "고평가", score
        else:
            return "적정", score

    def _eval_profitability(self, data: FundamentalData) -> str:
        """수익성 평가."""
        good_count = 0

        if data.roe is not None and data.roe > 0.15:
            good_count += 1
        if data.operating_margin is not None and data.operating_margin > 0.10:
            good_count += 1
        if data.net_margin is not None and data.net_margin > 0.05:
            good_count += 1

        if good_count >= 2:
            return "우수"
        elif good_count == 1:
            return "보통"
        else:
            return "미흡"

    def _eval_growth(self, data: FundamentalData) -> str:
        """성장성 평가."""
        rev = data.revenue_growth
        earn = data.earnings_growth

        if rev is None and earn is None:
            return "정체"

        avg = _avg_not_none([rev, earn])
        if avg is None:
            return "정체"

        if avg > 0.20:
            return "고성장"
        elif avg > 0.05:
            return "성장"
        elif avg >= 0:
            return "정체"
        else:
            return "역성장"

    def _eval_health(self, data: FundamentalData) -> str:
        """재무 건전성 평가."""
        risk_count = 0

        if data.debt_to_equity is not None and data.debt_to_equity > 200:
            risk_count += 1
        if data.current_ratio is not None and data.current_ratio < 1.0:
            risk_count += 1

        if risk_count == 0:
            return "건전"
        elif risk_count == 1:
            return "보통"
        else:
            return "위험"

    def _estimate_target_price(
        self,
        data: FundamentalData,
        current_price: float,
        sector: str,
    ) -> tuple[Optional[float], Optional[float]]:
        """PER 기반 목표가 추정.

        Returns:
            (low, high) 목표가 튜플
        """
        if data.forward_eps is None and data.eps is None:
            return None, None

        eps = data.forward_eps or data.eps
        if eps is None or eps <= 0:
            return None, None

        benchmark_per = _SECTOR_PER_BENCHMARK.get(sector, 20.0)
        target_low = round(eps * benchmark_per * 0.8, 2)
        target_high = round(eps * benchmark_per * 1.2, 2)

        return target_low, target_high

    def _build_key_metrics(self, data: FundamentalData) -> dict:
        """주요 지표 딕셔너리 구성."""
        def fmt_pct(v: Optional[float]) -> str:
            return f"{v:.1%}" if v is not None else "N/A"

        def fmt_x(v: Optional[float]) -> str:
            return f"{v:.1f}x" if v is not None else "N/A"

        return {
            "PER": fmt_x(data.per),
            "PBR": fmt_x(data.pbr),
            "EV/EBITDA": fmt_x(data.ev_ebitda),
            "PSR": fmt_x(data.psr),
            "ROE": fmt_pct(data.roe),
            "ROA": fmt_pct(data.roa),
            "영업이익률": fmt_pct(data.operating_margin),
            "순이익률": fmt_pct(data.net_margin),
            "매출성장률": fmt_pct(data.revenue_growth),
            "이익성장률": fmt_pct(data.earnings_growth),
            "부채비율": f"{data.debt_to_equity:.0f}%" if data.debt_to_equity is not None else "N/A",
            "유동비율": fmt_x(data.current_ratio),
            "배당수익률": fmt_pct(data.dividend_yield),
            "EPS": str(data.eps) if data.eps is not None else "N/A",
        }


def _avg_not_none(values: list[Optional[float]]) -> Optional[float]:
    """None을 제외한 평균 계산."""
    valid = [v for v in values if v is not None]
    return sum(valid) / len(valid) if valid else None


def _build_summary(
    valuation: str,
    profitability: str,
    growth: str,
    health: str,
) -> str:
    """종합 한 줄 요약 생성."""
    return (
        f"밸류에이션 {valuation}, 수익성 {profitability}, "
        f"성장성 {growth}, 재무 {health}"
    )
