#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODE="${1:-dev}"

install_deps() {
  if [ ! -d "node_modules" ]; then
    echo "[AgentDashBoard] node_modules 없음 → npm install 실행"
    npm install
  fi
}

case "$MODE" in
  dev)
    install_deps
    echo "[AgentDashBoard] 개발 서버 시작 (http://localhost:3000) — 크래시 시 자동 재시작"
    while true; do
      npm run dev || true
      echo "[AgentDashBoard] 서버 종료됨. 3초 후 재시작... (Ctrl+C로 중단)"
      sleep 3
    done
    ;;
  build)
    install_deps
    echo "[AgentDashBoard] 빌드 실행"
    npm run build
    ;;
  start)
    install_deps
    echo "[AgentDashBoard] 프로덕션 서버 시작 (http://localhost:3000)"
    npm run build && npm run start
    ;;
  *)
    echo "사용법: $0 [dev|build|start]"
    echo "  dev   — 개발 서버 (기본값)"
    echo "  build — 프로덕션 빌드"
    echo "  start — 빌드 후 프로덕션 서버 실행"
    exit 1
    ;;
esac
