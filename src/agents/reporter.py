"""Slack 리포트 에이전트.

투자 아이디어를 Slack으로 전송하고 결과를 로깅.
"""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from src.slack.client import SlackClient

logger = logging.getLogger(__name__)

_OUTPUT_DIR = Path("output")


class Reporter:
    """Slack 리포트 전송 에이전트."""

    def __init__(
        self,
        slack_client: SlackClient | None = None,
        webhook_url: str | None = None,
        channel: str | None = None,
    ) -> None:
        """초기화.

        Args:
            slack_client: SlackClient 인스턴스 (None이면 환경변수 기반 생성)
            webhook_url: Slack Webhook URL
            channel: Slack 채널
        """
        self.slack = slack_client or SlackClient(
            webhook_url=webhook_url,
            channel=channel,
        )

    def send(self, ticker: str, report_fields: dict) -> bool:
        """투자 리포트를 Slack으로 전송.

        Args:
            ticker: 종목 코드
            report_fields: IdeaGenerator.parse_report_fields() 결과 딕셔너리

        Returns:
            전송 성공 여부
        """
        today = date.today().strftime("%Y-%m-%d")

        if not self.slack.webhook_url:
            logger.warning(
                "SLACK_WEBHOOK_URL 미설정. 리포트를 로컬 파일로 저장합니다."
            )
            self._save_fallback(ticker, report_fields, today)
            return False

        success = self.slack.send_investment_report(report_fields)

        if success:
            self._write_log(ticker, today, status="성공")
            logger.info("Slack 전송 완료: %s", ticker)
        else:
            self._write_log(ticker, today, status="실패")
            logger.error("Slack 전송 실패: %s", ticker)

        return success

    def send_error(self, ticker: str, error_msg: str) -> None:
        """분석 실패 알림 전송.

        Args:
            ticker: 종목 코드
            error_msg: 오류 메시지
        """
        if self.slack.webhook_url:
            self.slack.send_error_notification(ticker, error_msg)
        logger.error("분석 실패 알림: %s - %s", ticker, error_msg)

    def _write_log(self, ticker: str, date_str: str, status: str) -> None:
        """전송 결과 로그 파일 기록."""
        _OUTPUT_DIR.mkdir(exist_ok=True)
        log_path = _OUTPUT_DIR / f"slack_sent_{ticker}_{date_str}.log"
        log_path.write_text(
            f"ticker={ticker}\ndate={date_str}\nstatus={status}\n",
            encoding="utf-8",
        )

    def _save_fallback(self, ticker: str, report_fields: dict, date_str: str) -> None:
        """Webhook 미설정 시 로컬 파일로 저장."""
        import json

        _OUTPUT_DIR.mkdir(exist_ok=True)
        fallback_path = _OUTPUT_DIR / f"slack_fallback_{ticker}_{date_str}.json"
        fallback_path.write_text(
            json.dumps(report_fields, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Slack fallback 저장: %s", fallback_path)
