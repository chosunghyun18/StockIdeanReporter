#!/usr/bin/env bash
# run.sh — MiroFishTrader 전체 파이프라인 실행 스크립트
#
# 사용법:
#   ./run.sh                          # 오늘 날짜, Slack 전송
#   ./run.sh --dry-run                # 오늘 날짜, Slack 미전송
#   ./run.sh --date 2024-03-15        # 특정 날짜
#   ./run.sh --date 2024-03-15 --dry-run
#   ./run.sh --no-mirofish            # MiroFish Docker 기동 스킵 (이미 실행 중일 때)

set -euo pipefail

# ── 경로 설정 ─────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
MIROFISH_DIR="$SCRIPT_DIR/MiroFish"   # MiroFish 소스 위치 (git clone 경로)
MIROFISH_URL="${MIROFISH_BASE_URL:-http://localhost:5001}"
MIROFISH_HEALTH_PATH="/health"
MIROFISH_WAIT_SEC=60                   # 최대 대기 시간(초)

# ── 인수 파싱 ─────────────────────────────────────────────────────────────────
DATE_ARG=""
DRY_RUN=""
SKIP_MIROFISH=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --date)       DATE_ARG="--date $2"; shift 2 ;;
        --dry-run)    DRY_RUN="--dry-run";  shift   ;;
        --no-mirofish) SKIP_MIROFISH=1;      shift   ;;
        *) echo "[ERROR] 알 수 없는 옵션: $1"; exit 1 ;;
    esac
done

# ── 색상 출력 헬퍼 ─────────────────────────────────────────────────────────────
info()  { echo "[INFO]  $*"; }
warn()  { echo "[WARN]  $*"; }
error() { echo "[ERROR] $*" >&2; }
step()  { echo ""; echo "══════════════════════════════════════"; echo "  $*"; echo "══════════════════════════════════════"; }

# ── Step 1: .env 확인 ─────────────────────────────────────────────────────────
step "Step 1/4 — 환경 확인"

if [[ ! -f "$SCRIPT_DIR/.env" ]]; then
    warn ".env 파일이 없습니다. .env.example 을 복사합니다."
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    error ".env 파일을 열어 실제 API 키와 Webhook URL을 입력하세요."
    error "  vi $SCRIPT_DIR/.env"
    exit 1
fi

if [[ ! -d "$VENV" ]]; then
    error "가상환경이 없습니다. 먼저 설정 스크립트를 실행하세요:"
    error "  python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

info ".env: OK"
info "venv:  $VENV"

# ── Step 2: MiroFish Docker 기동 ──────────────────────────────────────────────
step "Step 2/4 — MiroFish Docker"

_mirofish_running() {
    curl -sf "${MIROFISH_URL}${MIROFISH_HEALTH_PATH}" > /dev/null 2>&1
}

if [[ $SKIP_MIROFISH -eq 1 ]]; then
    info "--no-mirofish 옵션: Docker 기동 스킵"
    if ! _mirofish_running; then
        error "MiroFish 서버에 응답 없음: ${MIROFISH_URL}"
        error "서버가 실행 중인지 확인하거나 --no-mirofish 옵션을 제거하세요."
        exit 1
    fi
    info "MiroFish 서버 응답 확인: OK"
elif _mirofish_running; then
    info "MiroFish 이미 실행 중: ${MIROFISH_URL}"
else
    if [[ ! -d "$MIROFISH_DIR" ]]; then
        warn "MiroFish 소스 디렉터리가 없습니다: $MIROFISH_DIR"
        warn "MiroFish를 먼저 클론하세요:"
        warn "  git clone https://github.com/666ghj/MiroFish $MIROFISH_DIR"
        warn "또는 --no-mirofish 옵션으로 외부 실행 서버를 사용하세요."
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        error "Docker가 설치되어 있지 않습니다."
        exit 1
    fi

    info "MiroFish Docker 컨테이너 기동 중..."
    if [[ -f "$MIROFISH_DIR/docker-compose.yml" ]] || [[ -f "$MIROFISH_DIR/compose.yml" ]]; then
        docker compose -f "$MIROFISH_DIR/docker-compose.yml" up -d 2>/dev/null \
            || docker compose -f "$MIROFISH_DIR/compose.yml" up -d
    else
        error "docker-compose.yml 파일을 찾을 수 없습니다: $MIROFISH_DIR"
        exit 1
    fi

    info "MiroFish 서버 준비 대기 (최대 ${MIROFISH_WAIT_SEC}초)..."
    elapsed=0
    while ! _mirofish_running; do
        if [[ $elapsed -ge $MIROFISH_WAIT_SEC ]]; then
            error "MiroFish 서버 기동 타임아웃 (${MIROFISH_WAIT_SEC}초 초과)"
            error "Docker 로그 확인: docker compose -f $MIROFISH_DIR/docker-compose.yml logs"
            exit 1
        fi
        sleep 3
        elapsed=$((elapsed + 3))
        info "  대기 중... ${elapsed}s / ${MIROFISH_WAIT_SEC}s"
    done
    info "MiroFish 서버 준비 완료: ${MIROFISH_URL}"
fi

# ── Step 3: 가상환경 활성화 ───────────────────────────────────────────────────
step "Step 3/4 — Python 환경 활성화"

# shellcheck source=/dev/null
source "$VENV/bin/activate"
info "Python: $(python --version)"

# ── Step 4: 파이프라인 실행 ───────────────────────────────────────────────────
step "Step 4/4 — MiroFishTrader 파이프라인 실행"

cd "$SCRIPT_DIR"

CMD="python main.py $DATE_ARG $DRY_RUN"
info "실행: $CMD"
echo ""

# shellcheck disable=SC2086
exec $CMD
