"""
에이전트 뷰어 웹서버

에이전트 목록 조회, 내용 확인, Claude로 파일 수정 지원.
파이프라인 정의는 config/pipelines.json에서 로드 (server.py에 하드코딩 없음).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Optional

import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR    = Path(__file__).parent.parent
AGENTS_DIR  = BASE_DIR / "agents"
PIPELINES_FILE = BASE_DIR / "config" / "pipelines.json"
SESSIONS_FILE  = BASE_DIR / "output" / "sessions.jsonl"

app = FastAPI(title="Agent Viewer")
app.mount("/static", StaticFiles(directory=Path(__file__).parent), name="static")


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "index.html")

@app.get("/graph")
def graph_page():
    return FileResponse(Path(__file__).parent / "graph.html")

@app.get("/it")
def it_page():
    return FileResponse(Path(__file__).parent / "it.html")

@app.get("/sessions")
def sessions_page():
    return FileResponse(Path(__file__).parent / "sessions.html")


# ── Frontmatter parser ─────────────────────────────────────────────────────────
def parse_frontmatter(content: str) -> dict[str, Any]:
    """
    YAML frontmatter 파싱. 스칼라/배열/목록 값을 자동 감지한다.

    지원 형식:
      key: single value
      key: [a, b, c]               # 인라인 배열
      key: item1, item2            # 쉼표 구분 배열 (값에 스페이스 없는 경우)
    """
    meta: dict[str, Any] = {}
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return meta

    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        val = raw.strip().strip('"')

        if val.startswith("[") and val.endswith("]"):
            # [a, b, c] 형식
            items = [x.strip().strip('"').strip("'") for x in val[1:-1].split(",") if x.strip()]
            meta[key] = items
        else:
            meta[key] = val

    return meta


# ── Agent type classifier ──────────────────────────────────────────────────────
def agent_type(name: str) -> str:
    n = name.lower()
    if "orchestrator" in n or n.endswith("-manager"):
        return "orchestrator"
    if "analyst" in n:
        return "analyst"
    if "reviewer" in n:
        return "reviewer"
    if "etf" in n:
        return "etf"
    if "reporter" in n or "writer" in n:
        return "reporter"
    if "resolver" in n or "builder" in n:
        return "builder"
    return "other"


# ── Load helpers ──────────────────────────────────────────────────────────────
def load_all_agents() -> dict[str, dict]:
    """agents/ 디렉토리의 모든 .md 파일을 파싱해 dict 반환 (slug → data)."""
    agents: dict[str, dict] = {}
    for path in sorted(AGENTS_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        meta    = parse_frontmatter(content)
        name    = meta.get("name") or path.stem
        agents[path.stem] = {
            "slug":        path.stem,
            "name":        name,
            "description": meta.get("description", ""),
            "model":       meta.get("model", ""),
            "type":        agent_type(name),
            # 관계 메타데이터 (없으면 빈 리스트)
            "calls":   meta.get("calls", []),
            "inputs":  meta.get("inputs", []),
            "outputs": meta.get("outputs", []),
            "content": content,
        }
    return agents


def load_pipelines() -> list[dict]:
    """config/pipelines.json 에서 파이프라인 정의를 로드."""
    if not PIPELINES_FILE.exists():
        return []
    with PIPELINES_FILE.open(encoding="utf-8") as f:
        data = json.load(f)
    return data.get("pipelines", [])


# ── API: agents ────────────────────────────────────────────────────────────────
@app.get("/api/agents")
def list_agents():
    agents = load_all_agents()
    result = [
        {k: v for k, v in a.items() if k != "content"}
        for a in agents.values()
    ]
    return JSONResponse(result)


@app.get("/api/agents/{slug}")
def get_agent(slug: str):
    path = AGENTS_DIR / f"{slug}.md"
    if not path.exists():
        raise HTTPException(404, "Agent not found")
    content = path.read_text(encoding="utf-8")
    meta    = parse_frontmatter(content)
    name    = meta.get("name", slug)
    return JSONResponse({
        "slug":        slug,
        "name":        name,
        "description": meta.get("description", ""),
        "model":       meta.get("model", ""),
        "type":        agent_type(name),
        "calls":       meta.get("calls", []),
        "inputs":      meta.get("inputs", []),
        "outputs":     meta.get("outputs", []),
        "content":     content,
    })


# ── API: graph ─────────────────────────────────────────────────────────────────
@app.get("/api/graph")
def get_graph():
    """
    에이전트 그래프 데이터 반환.

    노드: 전체 에이전트 목록 (frontmatter 메타데이터 포함)
    엣지: `calls` 필드 기반 (하드코딩 없음, 에이전트 파일만 보면 됨)
    파이프라인: config/pipelines.json 에서 로드
    """
    agents    = load_all_agents()
    pipelines = load_pipelines()

    # edges: calls 필드로부터 자동 생성
    edges: list[dict] = []
    for src in agents.values():
        for tgt_slug in src.get("calls", []):
            if tgt_slug in agents:
                edges.append({
                    "source":   src["slug"],
                    "target":   tgt_slug,
                    "parallel": False,  # pipeline 정의에서 parallel 여부 판단
                })

    # nodes: content 제외
    nodes = [
        {k: v for k, v in a.items() if k != "content"}
        for a in agents.values()
    ]

    return JSONResponse({
        "nodes":     nodes,
        "edges":     edges,
        "pipelines": pipelines,
    })


# ── API: edit ──────────────────────────────────────────────────────────────────
class EditRequest(BaseModel):
    instruction: str
    preview: Optional[bool] = False


@app.post("/api/agents/{slug}/edit")
def edit_agent(slug: str, req: EditRequest):
    path = AGENTS_DIR / f"{slug}.md"
    if not path.exists():
        raise HTTPException(404, "Agent not found")

    original = path.read_text(encoding="utf-8")
    api_key  = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(500, "ANTHROPIC_API_KEY 환경변수가 없습니다")

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=(
            "당신은 Claude Code 에이전트 파일(.md) 편집 전문가입니다.\n"
            "사용자의 수정 지시에 따라 에이전트 파일을 수정하세요.\n\n"
            "규칙:\n"
            "1. YAML frontmatter는 필요한 경우만 수정\n"
            "2. frontmatter의 calls/inputs/outputs 필드는 배열 형식 유지: [a, b, c]\n"
            "3. 수정하지 않은 부분은 그대로 유지\n"
            "4. 응답은 수정된 전체 파일 내용만 출력 (설명 없이, 코드블록 없이)\n"
            "5. 한국어 주석/설명 유지\n"
        ),
        messages=[{
            "role": "user",
            "content": f"## 수정 지시\n{req.instruction}\n\n## 현재 파일\n{original}",
        }],
    )
    new_content = msg.content[0].text.strip()

    if not req.preview:
        path.write_text(new_content, encoding="utf-8")

    return JSONResponse({"slug": slug, "content": new_content, "saved": not req.preview})


# ── API: save ──────────────────────────────────────────────────────────────────
class SaveRequest(BaseModel):
    content: str


@app.put("/api/agents/{slug}/content")
def save_agent_content(slug: str, req: SaveRequest):
    path = AGENTS_DIR / f"{slug}.md"
    if not path.exists():
        raise HTTPException(404, "Agent not found")
    path.write_text(req.content, encoding="utf-8")
    return JSONResponse({"saved": True})


# ── API: pipelines (설정 파일 직접 조회) ──────────────────────────────────────
@app.get("/api/pipelines")
def get_pipelines():
    return JSONResponse(load_pipelines())


# ── API: sessions (터미널 요청 히스토리) ──────────────────────────────────────
@app.get("/api/sessions")
def get_sessions():
    """output/sessions.jsonl 읽어 session_id 기준으로 머지 후 반환 (최신순)."""
    if not SESSIONS_FILE.exists():
        return JSONResponse([])

    merged: dict[str, dict] = {}
    for line in SESSIONS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        sid = entry.get("session_id", "")
        if sid not in merged:
            merged[sid] = {
                "session_id": sid,
                "timestamp":  entry.get("timestamp", ""),
                "prompt":     entry.get("prompt", ""),
                "agents":     list(entry.get("agents", [])),
            }
        else:
            # Merge agents from later entries in same session
            existing = set(merged[sid]["agents"])
            for a in entry.get("agents", []):
                existing.add(a)
            merged[sid]["agents"] = list(existing)
            # Keep latest timestamp
            if entry.get("timestamp", "") > merged[sid]["timestamp"]:
                merged[sid]["timestamp"] = entry["timestamp"]

    result = sorted(merged.values(), key=lambda x: x["timestamp"], reverse=True)
    return JSONResponse(result)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8765, reload=True)
