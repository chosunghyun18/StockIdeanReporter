"""StockIdeaReporter FastAPI 백엔드.

엔드포인트:
    GET  /api/results          — 분석 결과 목록
    GET  /api/results/{ticker} — 특정 종목 분석 결과
    POST /api/analyze          — 종목 분석 실행
    POST /api/slack/send       — Slack 전송
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# backend/ 디렉터리를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.orchestrator import Orchestrator
from src.slack.client import SlackClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="StockIdeaReporter API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_OUTPUT_DIR = Path(__file__).parent / "output"
_analysis_cache: dict[str, dict] = {}  # ticker → result


# ---------------------------------------------------------------------------
# 요청/응답 모델
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    ticker: str
    market: str = "US"


class SlackSendRequest(BaseModel):
    ticker: str
    content: str
    report_fields: dict[str, Any] | None = None


class AnalyzeResponse(BaseModel):
    ticker: str
    market: str
    status: str
    investment_idea: str | None = None
    error: str | None = None
    slack_sent: bool = False


class ResultSummary(BaseModel):
    ticker: str
    date: str
    file_type: str  # investment_idea | industry_analysis | price_analysis


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _normalize_ticker(ticker: str, market: str) -> str:
    if market == "KR" and not ticker.endswith((".KS", ".KQ")):
        return f"{ticker}.KS"
    return ticker


def _list_output_files() -> list[ResultSummary]:
    """output/ 폴더의 마크다운 파일을 파싱해 요약 목록 반환."""
    _OUTPUT_DIR.mkdir(exist_ok=True)
    results: list[ResultSummary] = []
    for f in sorted(_OUTPUT_DIR.glob("*.md"), reverse=True):
        parts = f.stem.split("_", 2)
        if len(parts) < 3:
            continue
        file_type_raw = "_".join(parts[:-1])  # e.g. investment_idea
        date_part = parts[-1]
        ticker_part = "_".join(parts[1:-1]) if len(parts) > 2 else parts[1]
        # investment_idea_AAPL_2026-03-26 → type=investment_idea, ticker=AAPL
        # 단순히 stem에서 날짜(YYYY-MM-DD 패턴) 앞 부분으로 파싱
        stem = f.stem
        date_idx = None
        for i, part in enumerate(stem.split("_")):
            if len(part) == 10 and part.count("-") == 2:
                date_idx = i
                break
        if date_idx is None:
            continue
        tokens = stem.split("_")
        date_str = tokens[date_idx]
        ticker_str = "_".join(tokens[date_idx - 1: date_idx])
        type_str = "_".join(tokens[: date_idx - 1])
        results.append(ResultSummary(ticker=ticker_str, date=date_str, file_type=type_str))
    return results


# ---------------------------------------------------------------------------
# 엔드포인트
# ---------------------------------------------------------------------------

@app.get("/api/results", response_model=list[ResultSummary])
async def list_results() -> list[ResultSummary]:
    """분석 결과 파일 목록 반환."""
    return _list_output_files()


@app.get("/api/results/{ticker}")
async def get_result(ticker: str) -> dict:
    """특정 종목의 최신 투자 아이디어 마크다운 반환."""
    _OUTPUT_DIR.mkdir(exist_ok=True)
    # investment_idea 우선, 없으면 다른 파일 탐색
    for prefix in ("investment_idea", "price_analysis", "industry_analysis"):
        matches = sorted(_OUTPUT_DIR.glob(f"{prefix}_{ticker}_*.md"), reverse=True)
        if matches:
            content = matches[0].read_text(encoding="utf-8")
            return {"ticker": ticker, "file": matches[0].name, "content": content}
    raise HTTPException(status_code=404, detail=f"{ticker} 분석 결과를 찾을 수 없습니다.")


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    """종목 분석을 동기 실행하고 결과를 반환.

    Note:
        실제 분석은 30초~수 분이 걸릴 수 있습니다.
        장시간 작업은 프로덕션에서 비동기 큐로 전환 권장.
    """
    ticker = _normalize_ticker(req.ticker.upper(), req.market)
    logger.info("분석 요청: %s (%s)", ticker, req.market)

    orchestrator = Orchestrator()
    try:
        result = orchestrator.run(ticker=ticker, market=req.market)
    except Exception as exc:
        logger.exception("분석 중 예외 발생: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if result.error:
        return AnalyzeResponse(
            ticker=ticker,
            market=req.market,
            status="error",
            error=result.error,
        )

    _analysis_cache[ticker] = {
        "investment_idea": result.investment_idea,
        "slack_sent": result.slack_sent,
    }

    return AnalyzeResponse(
        ticker=ticker,
        market=req.market,
        status="success",
        investment_idea=result.investment_idea,
        slack_sent=result.slack_sent,
    )


@app.post("/api/slack/send")
async def send_to_slack(req: SlackSendRequest) -> dict:
    """분석 결과를 Slack으로 전송."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        raise HTTPException(
            status_code=503,
            detail="SLACK_WEBHOOK_URL 환경변수가 설정되지 않았습니다.",
        )

    client = SlackClient(webhook_url=webhook_url)

    # report_fields가 있으면 Block Kit 형식으로, 없으면 텍스트로 전송
    if req.report_fields:
        success = client.send_investment_report(req.report_fields)
    else:
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"📊 {req.ticker} 투자 아이디어"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": req.content[:2900]},
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": "_Generated by StockIdeaReporter UI_"}
                ],
            },
        ]
        success = client.send_blocks(blocks)

    if not success:
        raise HTTPException(status_code=502, detail="Slack 전송에 실패했습니다.")

    return {"success": True, "ticker": req.ticker}


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
