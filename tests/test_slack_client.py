"""Slack 클라이언트 테스트."""
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.slack.client import SlackClient, _MAX_RETRIES


def _sample_report() -> dict:
    """테스트용 리포트 딕셔너리."""
    return {
        "name": "삼성전자",
        "ticker": "005930.KS",
        "date": "2026-03-24",
        "investment_type": "중기",
        "thesis": "반도체 사이클 회복과 HBM 수요 급증으로 수혜 예상",
        "entry_price": "72,000~74,000원",
        "target1": "82,000원 (+11%)",
        "target2": "90,000원 (+22%)",
        "stop_loss": "68,000원 (-8%)",
        "risk_reward": "1:2.5",
        "bull_case": "HBM 수주 확대 및 실적 서프라이즈",
        "base_case": "점진적 회복세 유지",
        "bear_case": "글로벌 경기 침체로 수요 위축",
        "industry_score": 4,
        "technical_signal": "매수",
        "valuation": "저평가",
        "opinion": "중기 관점에서 분할 매수 추천",
    }


class TestSlackClient:
    """SlackClient 테스트."""

    def test_send_success(self):
        """정상 전송 성공."""
        client = SlackClient(webhook_url="https://hooks.slack.com/test", channel="#test")
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("src.slack.client.requests.post", return_value=mock_resp):
            result = client.send_investment_report(_sample_report())

        assert result is True

    def test_send_raises_without_webhook(self):
        """Webhook URL 없으면 EnvironmentError."""
        client = SlackClient(webhook_url="", channel="#test")
        with pytest.raises(EnvironmentError, match="SLACK_WEBHOOK_URL"):
            client.send_investment_report(_sample_report())

    def test_send_retries_on_failure(self):
        """실패 시 MAX_RETRIES 횟수만큼 재시도."""
        client = SlackClient(webhook_url="https://hooks.slack.com/test", channel="#test")
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_resp.headers = {}

        with patch("src.slack.client.requests.post", return_value=mock_resp), \
             patch("src.slack.client.time.sleep"):
            result = client.send_investment_report(_sample_report())

        assert result is False

    def test_send_returns_false_on_request_exception(self):
        """요청 오류 시 False 반환."""
        client = SlackClient(webhook_url="https://hooks.slack.com/test", channel="#test")

        with patch("src.slack.client.requests.post", side_effect=requests.RequestException("timeout")), \
             patch("src.slack.client.time.sleep"):
            result = client.send_investment_report(_sample_report())

        assert result is False

    def test_build_blocks_structure(self):
        """Block Kit 구조 검증."""
        client = SlackClient(webhook_url="https://hooks.slack.com/test")
        blocks = client._build_blocks(_sample_report())

        assert isinstance(blocks, list)
        assert len(blocks) > 0
        # 헤더 블록 확인
        assert blocks[0]["type"] == "header"
        # 투자 아이디어 리포트 텍스트 포함 확인
        assert "투자 아이디어" in blocks[0]["text"]["text"]

    def test_build_blocks_investment_type_badge(self):
        """투자 유형별 배지 적용."""
        client = SlackClient(webhook_url="https://hooks.slack.com/test")

        for inv_type, expected_badge in [
            ("단기", "🔴 단기"),
            ("중기", "🟡 중기"),
            ("장기", "🟢 장기"),
        ]:
            report = {**_sample_report(), "investment_type": inv_type}
            blocks = client._build_blocks(report)
            combined = " ".join(
                str(b) for b in blocks
            )
            assert expected_badge in combined

    def test_send_error_notification_success(self):
        """에러 알림 전송."""
        client = SlackClient(webhook_url="https://hooks.slack.com/test", channel="#test")
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("src.slack.client.requests.post", return_value=mock_resp):
            result = client.send_error_notification("AAPL", "데이터 수집 실패")

        assert result is True

    def test_send_error_notification_no_webhook(self):
        """Webhook 없으면 에러 알림 False."""
        client = SlackClient(webhook_url="", channel="#test")
        result = client.send_error_notification("AAPL", "실패")
        assert result is False

    def test_rate_limit_handling(self):
        """429 Rate Limit 처리."""
        client = SlackClient(webhook_url="https://hooks.slack.com/test", channel="#test")

        rate_limit_resp = MagicMock()
        rate_limit_resp.status_code = 429
        rate_limit_resp.headers = {"Retry-After": "1"}

        success_resp = MagicMock()
        success_resp.status_code = 200

        with patch(
            "src.slack.client.requests.post",
            side_effect=[rate_limit_resp, success_resp],
        ), patch("src.slack.client.time.sleep"):
            result = client.send_investment_report(_sample_report())

        assert result is True
