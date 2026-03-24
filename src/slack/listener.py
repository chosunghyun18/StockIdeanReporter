"""Slack Socket Mode 메시지 리스너.

사용자가 Slack에서 메시지를 보내면 명령을 파싱하고
투자 분석 파이프라인을 실행한 뒤 결과를 Slack으로 응답한다.

지원 명령어:
    분석 005930 KR         → 삼성전자 분석
    분석 AAPL US           → 애플 분석
    발굴 KR US             → 자동 발굴 (스윙 매매)
    발굴 KR top 3          → KR 상위 3개 발굴
    도움말                 → 사용 가능한 명령어 안내
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Any

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from src.agents.orchestrator import Orchestrator
from src.slack.command_parser import parse, SlackCommand

logger = logging.getLogger(__name__)

_HELP_TEXT = """:wave: *투자 분석 봇 사용법*

*종목 분석*
> `분석 005930 KR` — 삼성전자 분석
> `분석 AAPL US` — 애플 분석
> `분석 NVDA` — 종목명만 입력 (미국 주식 기본)

*자동 발굴 (스윙 매매 급락 종목)*
> `발굴 KR` — 국내 급락 종목 발굴
> `발굴 US` — 미국 급락 종목 발굴
> `발굴 KR US top 3` — 국내+미국 상위 3개

*기타*
> `도움말` — 이 메시지 표시

_분석에는 1~3분 소요됩니다. 결과는 채널로 전송됩니다._"""


class SlackListener:
    """Slack Socket Mode 기반 메시지 리스너."""

    def __init__(self) -> None:
        bot_token = os.environ.get("SLACK_BOT_TOKEN", "")
        app_token = os.environ.get("SLACK_APP_TOKEN", "")

        if not bot_token or not app_token:
            raise ValueError(
                "SLACK_BOT_TOKEN, SLACK_APP_TOKEN 환경변수가 필요합니다.\n"
                ".env 파일에 추가 후 다시 실행하세요."
            )

        self.app = App(token=bot_token)
        self.app_token = app_token
        self.orchestrator = Orchestrator()
        self._register_handlers()

    def start(self) -> None:
        """Socket Mode 리스너 시작 (블로킹)."""
        logger.info("Slack 리스너 시작...")
        handler = SocketModeHandler(self.app, self.app_token)
        handler.start()

    def _register_handlers(self) -> None:
        """이벤트 핸들러 등록."""

        @self.app.event("app_mention")
        def handle_mention(event: dict, say: Any) -> None:
            self._handle_message(event, say)

        @self.app.event("message")
        def handle_dm(event: dict, say: Any) -> None:
            # DM만 처리 (채널 메시지는 멘션으로만)
            if event.get("channel_type") == "im":
                self._handle_message(event, say)

    def _handle_message(self, event: dict, say: Any) -> None:
        """메시지 파싱 후 명령 실행."""
        text = event.get("text", "")
        if not text:
            return

        cmd = parse(text)
        logger.info("명령 수신: type=%s raw='%s'", cmd.type, cmd.raw)

        if cmd.type == "help":
            say(_HELP_TEXT)
        elif cmd.type == "analyze":
            self._run_analyze_async(cmd, say)
        elif cmd.type == "discover":
            self._run_discover_async(cmd, say)
        else:
            say(
                f"명령을 이해하지 못했습니다: `{cmd.raw}`\n"
                "`도움말` 을 입력하면 사용법을 안내해 드립니다."
            )

    def _run_analyze_async(self, cmd: SlackCommand, say: Any) -> None:
        """분석을 별도 스레드에서 실행 (응답 지연 방지)."""
        ticker = cmd.ticker
        market = cmd.market or "KR"
        say(f":mag: *{ticker}* ({market}) 분석을 시작합니다. 잠시 기다려 주세요...")

        def run() -> None:
            try:
                result = self.orchestrator.run(ticker=ticker, market=market)
                if result.error:
                    say(f":x: 분석 실패: {result.error}")
                else:
                    status = "✅ Slack 리포트 전송 완료" if result.slack_sent else "⚠️ Slack 전송 미완료"
                    say(f":white_check_mark: *{ticker}* 분석 완료! {status}")
            except Exception as e:
                logger.error("분석 오류: %s", e)
                say(f":x: 오류 발생: {e}")

        threading.Thread(target=run, daemon=True).start()

    def _run_discover_async(self, cmd: SlackCommand, say: Any) -> None:
        """자동 발굴을 별도 스레드에서 실행."""
        markets = cmd.markets or ["KR", "US"]
        top_n = cmd.top_n
        markets_str = " + ".join(markets)
        say(f":satellite: *{markets_str}* 급락 종목 발굴 중... (Top {top_n}) 잠시 기다려 주세요...")

        def run() -> None:
            try:
                results = self.orchestrator.run_discovery(markets=markets, top_n=top_n)
                if not results:
                    say(":warning: 조건에 맞는 종목이 없습니다.")
                    return
                lines = [f":white_check_mark: *발굴 완료* — {len(results)}개 종목 분석 및 Slack 전송"]
                for r in results:
                    icon = "✅" if r.slack_sent else "⚠️"
                    lines.append(f"  {icon} {r.ticker} ({r.market})")
                say("\n".join(lines))
            except Exception as e:
                logger.error("발굴 오류: %s", e)
                say(f":x: 오류 발생: {e}")

        threading.Thread(target=run, daemon=True).start()
