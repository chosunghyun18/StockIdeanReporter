"""에이전트 클래스 단위 테스트 (외부 API 모킹)."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agents.idea_generator import IdeaGenerator, _build_idea_prompt
from src.agents.industry_analyst import IndustryAnalyst, _build_industry_prompt
from src.agents.reporter import Reporter


# ── helpers ──────────────────────────────────────────────────────────────────

def _anthropic_message(text: str) -> MagicMock:
    """Anthropic messages.create() 반환값 모킹."""
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    return msg


# ── IndustryAnalyst ───────────────────────────────────────────────────────────

class TestIndustryAnalyst:
    def test_analyze_returns_and_saves(self, tmp_path):
        """analyze() 결과 반환 및 파일 저장 확인."""
        expected = "## 산업 분석 결과\n테스트 내용"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _anthropic_message(expected)

        mock_info = MagicMock()
        mock_info.name = "삼성전자"

        analyst = IndustryAnalyst(client=mock_client)
        analyst.data_fetcher = MagicMock()
        analyst.data_fetcher.get_stock_info.return_value = mock_info
        analyst.data_fetcher.get_sector.return_value = "Technology"
        analyst.data_fetcher.get_industry.return_value = "Semiconductors"

        with patch("src.agents.industry_analyst._OUTPUT_DIR", tmp_path):
            result = analyst.analyze("005930.KS", market="KR")

        assert result == expected
        # 파일 저장 확인
        saved_files = list(tmp_path.glob("industry_analysis_*.md"))
        assert len(saved_files) == 1
        assert saved_files[0].read_text(encoding="utf-8") == expected

    def test_analyze_calls_claude_once(self):
        """Claude API 정확히 1회 호출."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _anthropic_message("분석 결과")

        mock_info = MagicMock()
        mock_info.name = "Apple"

        analyst = IndustryAnalyst(client=mock_client)
        analyst.data_fetcher = MagicMock()
        analyst.data_fetcher.get_stock_info.return_value = mock_info
        analyst.data_fetcher.get_sector.return_value = "Technology"
        analyst.data_fetcher.get_industry.return_value = "Consumer Electronics"

        with patch("src.agents.industry_analyst._OUTPUT_DIR", Path("/tmp")):
            analyst.analyze("AAPL", market="US")

        mock_client.messages.create.assert_called_once()

    def test_build_industry_prompt_contains_ticker(self):
        """프롬프트에 티커와 기업명 포함."""
        prompt = _build_industry_prompt(
            ticker="005930.KS",
            name="삼성전자",
            market="KR",
            sector="Technology",
            industry="Semiconductors",
            date="2026-03-24",
        )
        assert "005930.KS" in prompt
        assert "삼성전자" in prompt
        assert "Technology" in prompt


# ── IdeaGenerator ─────────────────────────────────────────────────────────────

class TestIdeaGenerator:
    def test_generate_returns_and_saves(self, tmp_path):
        """generate() 결과 반환 및 파일 저장."""
        expected = "## 투자 아이디어\n테스트 아이디어"

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _anthropic_message(expected)

        generator = IdeaGenerator(client=mock_client)

        with patch("src.agents.idea_generator._OUTPUT_DIR", tmp_path):
            result = generator.generate(
                ticker="005930.KS",
                industry_analysis="산업 분석",
                price_analysis="주가 분석",
            )

        assert result == expected
        saved_files = list(tmp_path.glob("investment_idea_*.md"))
        assert len(saved_files) == 1

    def test_parse_report_fields_valid_json(self):
        """JSON 응답을 올바르게 파싱."""
        import json

        fields = {
            "name": "삼성전자",
            "ticker": "005930.KS",
            "date": "2026-03-24",
            "investment_type": "중기",
            "thesis": "반도체 업황 회복",
            "entry_price": "72,000~74,000원",
            "target1": "82,000원",
            "target2": "90,000원",
            "stop_loss": "68,000원",
            "risk_reward": "1:2.5",
            "bull_case": "HBM 수주 확대",
            "base_case": "점진적 회복",
            "bear_case": "수요 위축",
            "industry_score": 4,
            "technical_signal": "매수",
            "valuation": "저평가",
            "opinion": "분할 매수 추천",
        }

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _anthropic_message(
            json.dumps(fields, ensure_ascii=False)
        )

        generator = IdeaGenerator(client=mock_client)
        result = generator.parse_report_fields("아이디어 텍스트", "005930.KS")

        assert result["name"] == "삼성전자"
        assert result["investment_type"] == "중기"
        assert result["industry_score"] == 4

    def test_parse_report_fields_fallback_on_invalid_json(self):
        """JSON 파싱 실패 시 기본값 반환."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _anthropic_message(
            "이것은 JSON이 아닙니다"
        )

        generator = IdeaGenerator(client=mock_client)
        result = generator.parse_report_fields("아이디어", "AAPL")

        assert result["ticker"] == "AAPL"
        assert result["investment_type"] == "중기"
        assert "technical_signal" in result

    def test_build_idea_prompt_contains_analyses(self):
        """프롬프트에 산업/주가 분석 포함."""
        prompt = _build_idea_prompt(
            ticker="AAPL",
            industry_analysis="## 산업 분석",
            price_analysis="## 주가 분석",
            today="2026-03-24",
        )
        assert "## 산업 분석" in prompt
        assert "## 주가 분석" in prompt
        assert "AAPL" in prompt


# ── Reporter ──────────────────────────────────────────────────────────────────

class TestReporter:
    def test_send_success(self):
        """Slack 전송 성공."""
        mock_slack = MagicMock()
        mock_slack.webhook_url = "https://hooks.slack.com/test"
        mock_slack.send_investment_report.return_value = True

        reporter = Reporter(slack_client=mock_slack)

        with patch("src.agents.reporter._OUTPUT_DIR") as mock_dir:
            mock_dir.__truediv__ = lambda self, other: MagicMock()
            result = reporter.send("005930.KS", {"name": "삼성전자"})

        assert result is True
        mock_slack.send_investment_report.assert_called_once()

    def test_send_failure_logs_error(self):
        """전송 실패 시 False 반환."""
        mock_slack = MagicMock()
        mock_slack.webhook_url = "https://hooks.slack.com/test"
        mock_slack.send_investment_report.return_value = False

        reporter = Reporter(slack_client=mock_slack)

        with patch("src.agents.reporter._OUTPUT_DIR") as mock_dir:
            mock_dir.__truediv__ = lambda self, other: MagicMock()
            result = reporter.send("AAPL", {})

        assert result is False

    def test_send_no_webhook_saves_fallback(self, tmp_path):
        """Webhook 없으면 로컬 파일로 저장."""
        mock_slack = MagicMock()
        mock_slack.webhook_url = ""

        reporter = Reporter(slack_client=mock_slack)

        with patch("src.agents.reporter._OUTPUT_DIR", tmp_path):
            result = reporter.send("005930.KS", {"name": "삼성전자", "ticker": "005930.KS"})

        assert result is False
        fallback_files = list(tmp_path.glob("slack_fallback_*.json"))
        assert len(fallback_files) == 1

    def test_send_error_with_webhook(self):
        """에러 알림 전송."""
        mock_slack = MagicMock()
        mock_slack.webhook_url = "https://hooks.slack.com/test"

        reporter = Reporter(slack_client=mock_slack)
        reporter.send_error("AAPL", "API 오류")

        mock_slack.send_error_notification.assert_called_once_with("AAPL", "API 오류")

    def test_send_error_no_webhook(self):
        """Webhook 없어도 에러 알림은 로깅만."""
        mock_slack = MagicMock()
        mock_slack.webhook_url = ""

        reporter = Reporter(slack_client=mock_slack)
        reporter.send_error("AAPL", "오류")  # 예외 없이 실행돼야 함

        mock_slack.send_error_notification.assert_not_called()
