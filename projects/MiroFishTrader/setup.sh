#!/usr/bin/env bash
# setup.sh — MiroFishTrader 최초 환경 세팅 스크립트
#
# 사용법:
#   ./setup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

info()  { echo "[INFO]  $*"; }
error() { echo "[ERROR] $*" >&2; }
step()  { echo ""; echo "══════════════════════════════════════"; echo "  $*"; echo "══════════════════════════════════════"; }

step "MiroFishTrader 환경 세팅"

# ── Python 버전 확인 ──────────────────────────────────────────────────────────
if ! command -v python3.11 &> /dev/null; then
    error "Python 3.11이 필요합니다. 설치 후 다시 실행하세요."
    error "  brew install python@3.11"
    exit 1
fi
info "Python: $(python3.11 --version)"

# ── 가상환경 생성 ─────────────────────────────────────────────────────────────
step "1/3 — 가상환경 생성"
if [[ -d "$SCRIPT_DIR/.venv" ]]; then
    info ".venv 이미 존재 — 스킵"
else
    python3.11 -m venv "$SCRIPT_DIR/.venv"
    info ".venv 생성 완료"
fi

source "$SCRIPT_DIR/.venv/bin/activate"

# ── 패키지 설치 ───────────────────────────────────────────────────────────────
step "2/3 — 패키지 설치"
pip install --upgrade pip -q
pip install -r "$SCRIPT_DIR/requirements.txt"
info "패키지 설치 완료"

# ── .env 파일 ─────────────────────────────────────────────────────────────────
step "3/3 — 환경변수 설정"
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    info ".env 이미 존재 — 스킵"
else
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    info ".env 파일 생성: $SCRIPT_DIR/.env"
    echo ""
    echo "  ┌─────────────────────────────────────────────────────┐"
    echo "  │  .env 파일을 열어 아래 항목을 입력하세요:           │"
    echo "  │                                                     │"
    echo "  │  SLACK_WEBHOOK_URL=https://hooks.slack.com/...      │"
    echo "  │  ANTHROPIC_API_KEY=sk-ant-...                       │"
    echo "  │  REDDIT_CLIENT_ID=...                               │"
    echo "  │  REDDIT_CLIENT_SECRET=...                           │"
    echo "  └─────────────────────────────────────────────────────┘"
fi

echo ""
info "세팅 완료. 실행:"
info "  ./run.sh --dry-run"
