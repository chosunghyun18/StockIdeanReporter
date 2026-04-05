"""오케스트레이터 테스트."""
from unittest.mock import MagicMock, patch

import pytest

from src.agents.orchestrator import AnalysisResult, Orchestrator


def _make_orchestrator() -> Orchestrator:
    """테스트용 Orchestrator (API 호출 없이)."""
    with patch("src.agents.orchestrator.anthropic.Anthropic"):
        return Orchestrator(api_key="test-key")


class TestOrchestrator:
    """Orchestrator 테스트."""

    def test_run_success_full_pipeline(self):
        """전체 파이프라인 정상 실행."""
        orch = _make_orchestrator()

        industry_text = "## 산업 분석 결과\n테스트 산업 분석"
        price_text = "## 주가 분석 결과\n테스트 주가 분석"
        idea_text = "## 투자 아이디어\n테스트 아이디어"
        report_fields = {"ticker": "005930.KS", "name": "삼성전자"}

        orch.industry_analyst.analyze = MagicMock(return_value=industry_text)
        orch.price_analyst.analyze = MagicMock(return_value=price_text)
        orch.idea_generator.generate = MagicMock(return_value=idea_text)
        orch.idea_generator.parse_report_fields = MagicMock(return_value=report_fields)
        orch.reporter.send = MagicMock(return_value=True)

        result = orch.run("005930.KS", market="KR")

        assert result.ticker == "005930.KS"
        assert result.market == "KR"
        assert result.industry_analysis == industry_text
        assert result.price_analysis == price_text
        assert result.investment_idea == idea_text
        assert result.slack_sent is True
        assert result.error is None

    def test_run_industry_failure(self):
        """산업 분석 실패 시 에러 처리."""
        orch = _make_orchestrator()

        orch.industry_analyst.analyze = MagicMock(side_effect=ValueError("데이터 없음"))
        orch.price_analyst.analyze = MagicMock(return_value="주가 분석")
        orch.reporter.send_error = MagicMock()

        result = orch.run("INVALID", market="US")

        assert result.error is not None
        assert "산업 분석 실패" in result.error
        assert result.slack_sent is False
        orch.reporter.send_error.assert_called_once()

    def test_run_price_failure(self):
        """주가 분석 실패 시 에러 처리."""
        orch = _make_orchestrator()

        orch.industry_analyst.analyze = MagicMock(return_value="산업 분석")
        orch.price_analyst.analyze = MagicMock(side_effect=ValueError("데이터 없음"))
        orch.reporter.send_error = MagicMock()

        result = orch.run("INVALID", market="US")

        assert result.error is not None
        assert "주가 분석 실패" in result.error
        assert result.slack_sent is False

    def test_run_idea_generation_failure(self):
        """아이디어 생성 실패 시 에러 처리."""
        orch = _make_orchestrator()

        orch.industry_analyst.analyze = MagicMock(return_value="산업 분석")
        orch.price_analyst.analyze = MagicMock(return_value="주가 분석")
        orch.idea_generator.generate = MagicMock(side_effect=RuntimeError("API 오류"))
        orch.reporter.send_error = MagicMock()

        result = orch.run("AAPL", market="US")

        assert result.error is not None
        assert "아이디어 생성 실패" in result.error
        assert result.slack_sent is False

    def test_run_parallel_calls_both_analysts(self):
        """병렬 분석 시 두 에이전트 모두 호출."""
        orch = _make_orchestrator()

        orch.industry_analyst.analyze = MagicMock(return_value="산업")
        orch.price_analyst.analyze = MagicMock(return_value="주가")
        orch.idea_generator.generate = MagicMock(return_value="아이디어")
        orch.idea_generator.parse_report_fields = MagicMock(return_value={})
        orch.reporter.send = MagicMock(return_value=False)

        orch.run("AAPL", market="US")

        orch.industry_analyst.analyze.assert_called_once_with("AAPL", "US")
        orch.price_analyst.analyze.assert_called_once_with("AAPL", "US")

    def test_analysis_result_frozen(self):
        """AnalysisResult는 불변 객체."""
        result = AnalysisResult(
            ticker="AAPL",
            market="US",
            industry_analysis="산업",
            price_analysis="주가",
            investment_idea="아이디어",
            slack_sent=True,
        )
        with pytest.raises(Exception):
            result.ticker = "GOOG"  # type: ignore[misc]
