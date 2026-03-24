"""Slack 봇 리스너 진입점.

사용법:
    python listen.py

환경변수 (.env):
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_APP_TOKEN=xapp-...
    ANTHROPIC_API_KEY=sk-ant-...
    SLACK_WEBHOOK_URL=https://hooks.slack.com/...
"""
from __future__ import annotations

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main() -> None:
    try:
        from src.slack.listener import SlackListener
        listener = SlackListener()
        listener.start()
    except ValueError as e:
        print(f"[오류] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n리스너 종료.")


if __name__ == "__main__":
    main()
