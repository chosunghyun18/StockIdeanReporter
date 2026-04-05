#!/usr/bin/env bash
# StockIdeaReporter — 백엔드 + 프론트엔드 동시 실행

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

cleanup() {
  echo ""
  echo "종료 중..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  exit 0
}
trap cleanup SIGINT SIGTERM

# .env 로드
if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
  echo "[환경변수] $ROOT_DIR/.env 로드 완료"
else
  echo "[경고] .env 파일을 찾을 수 없습니다: $ROOT_DIR/.env"
fi

# 백엔드
echo "[백엔드] uvicorn 시작 (http://localhost:8000)"
cd "$BACKEND_DIR"
uvicorn api:app --reload --port 8000 &
BACKEND_PID=$!

# 프론트엔드
echo "[프론트] npm run dev 시작 (http://localhost:5173)"
cd "$FRONTEND_DIR"
if [ ! -d node_modules ]; then
  echo "[프론트] node_modules 없음 — npm install 실행"
  npm install
fi
npm run dev &
FRONTEND_PID=$!

echo ""
echo "백엔드  → http://localhost:8000"
echo "프론트  → http://localhost:5173"
echo "종료하려면 Ctrl+C"

wait
