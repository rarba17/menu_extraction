#!/bin/bash
# =============================================================================
# docker/entrypoint.sh - Unified Entrypoint Script
# =============================================================================
# Handles:
#   1. Wait for dependent services (Redis)
#   2. Pre-flight checks (API keys, directories)
#   3. Starts the correct service based on CMD argument
#   4. Graceful shutdown via signal trapping
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------
log_info()  { echo -e "\033[0;34m[INFO ]\033[0m  $(date '+%Y-%m-%d %H:%M:%S') | $*"; }
log_ok()    { echo -e "\033[0;32m[OK   ]\033[0m  $(date '+%Y-%m-%d %H:%M:%S') | $*"; }
log_warn()  { echo -e "\033[0;33m[WARN ]\033[0m  $(date '+%Y-%m-%d %H:%M:%S') | $*"; }
log_error() { echo -e "\033[0;31m[ERROR]\033[0m  $(date '+%Y-%m-%d %H:%M:%S') | $*" >&2; }

# ---------------------------------------------------------------------------
# Signal handling for graceful shutdown
# ---------------------------------------------------------------------------
PID=""
graceful_shutdown() {
    log_info "Received shutdown signal. Gracefully stopping..."
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        kill -SIGTERM "$PID"
        # Wait up to 30s for graceful shutdown
        local TIMEOUT=30
        local ELAPSED=0
        while kill -0 "$PID" 2>/dev/null && [ $ELAPSED -lt $TIMEOUT ]; do
            sleep 1
            ELAPSED=$((ELAPSED + 1))
        done
        if kill -0 "$PID" 2>/dev/null; then
            log_warn "Process did not stop gracefully. Sending SIGKILL..."
            kill -SIGKILL "$PID" 2>/dev/null || true
        fi
    fi
    log_ok "Shutdown complete."
    exit 0
}

trap 'graceful_shutdown' SIGTERM SIGINT SIGQUIT

# ---------------------------------------------------------------------------
# Utility: Wait for a TCP service (non-fatal by default)
# ---------------------------------------------------------------------------
wait_for_service() {
    local HOST="$1"
    local PORT="$2"
    local SERVICE_NAME="${3:-$HOST:$PORT}"
    local MAX_RETRIES="${4:-30}"
    local WAIT_SECONDS="${5:-2}"
    local REQUIRED="${6:-false}"   # Pass 'true' to abort on failure

    log_info "Waiting for $SERVICE_NAME ($HOST:$PORT)..."
    local ATTEMPT=0
    until nc -z "$HOST" "$PORT" 2>/dev/null; do
        ATTEMPT=$((ATTEMPT + 1))
        if [ "$ATTEMPT" -ge "$MAX_RETRIES" ]; then
            if [ "$REQUIRED" = "true" ]; then
                log_error "Service $SERVICE_NAME not available after ${MAX_RETRIES} attempts. Aborting."
                exit 1
            else
                log_warn "Service $SERVICE_NAME not available after ${MAX_RETRIES} attempts."
                log_warn "Continuing without $SERVICE_NAME (in-memory cache will be used as fallback)."
                return 0   # Non-fatal: let the app start anyway
            fi
        fi
        log_warn "  Attempt $ATTEMPT/$MAX_RETRIES - $SERVICE_NAME not ready. Retrying in ${WAIT_SECONDS}s..."
        sleep "$WAIT_SECONDS"
    done
    log_ok "$SERVICE_NAME is ready!"
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
preflight_checks() {
    log_info "Running pre-flight checks..."

    # Ensure output directory exists and is writable
    local OUTPUT_DIR="${OUTPUT_DIR:-/app/outputs}"
    mkdir -p "$OUTPUT_DIR"
    if [ ! -w "$OUTPUT_DIR" ]; then
        log_error "Output directory $OUTPUT_DIR is not writable!"
        exit 1
    fi
    log_ok "Output directory ($OUTPUT_DIR) is ready."

    # Ensure logs directory exists
    mkdir -p /app/logs
    log_ok "Log directory is ready."

    log_ok "Pre-flight checks passed."
}

# ---------------------------------------------------------------------------
# Wait for Redis if REDIS_URL is configured
# Redis is OPTIONAL by default — the app falls back to in-memory LRU cache.
# Set REDIS_REQUIRED=true in env to make it mandatory (e.g. Docker Compose).
# ---------------------------------------------------------------------------
wait_for_dependencies() {
    if [ -n "${REDIS_URL:-}" ]; then
        # Parse host and port from REDIS_URL (format: redis://host:port/db)
        local REDIS_HOST
        local REDIS_PORT
        REDIS_HOST=$(echo "$REDIS_URL" | sed -E 's|redis://([^:@]+@)?([^:]+):.*|\2|')
        REDIS_PORT=$(echo "$REDIS_URL" | sed -E 's|redis://[^:]+:([0-9]+).*|\1|')
        REDIS_PORT="${REDIS_PORT:-6379}"

        # REDIS_REQUIRED=true → fatal if unreachable (default in Docker Compose)
        # REDIS_REQUIRED=false (default) → warn and continue (safe for PaaS/Render)
        local REQUIRED="${REDIS_REQUIRED:-false}"

        wait_for_service "$REDIS_HOST" "$REDIS_PORT" "Redis" 10 2 "$REQUIRED"
    else
        log_warn "REDIS_URL not set — skipping Redis. In-memory LRU cache will be used."
    fi
}

# ---------------------------------------------------------------------------
# Start the FastAPI backend (development - auto-reload)
# ---------------------------------------------------------------------------
start_backend_dev() {
    # Backend requires the Gemini API key
    if [ -z "${GEMINI_API_KEY:-}" ]; then
        log_error "GEMINI_API_KEY is not set! Please provide it via the .env file."
        exit 1
    fi
    log_ok "GEMINI_API_KEY is set."
    log_info "Starting FastAPI backend in DEVELOPMENT mode (auto-reload enabled)..."
    exec python -m uvicorn backend.main:app \
        --host "${BACKEND_HOST:-0.0.0.0}" \
        --port "${BACKEND_PORT:-8000}" \
        --reload \
        --reload-dir /app/backend \
        --log-level "${LOG_LEVEL:-debug}" \
        --access-log \
        &
    PID=$!
    wait "$PID"
}

# ---------------------------------------------------------------------------
# Start the FastAPI backend (production - gunicorn + uvicorn workers)
# ---------------------------------------------------------------------------
start_backend_prod() {
    # Backend requires the Gemini API key
    if [ -z "${GEMINI_API_KEY:-}" ]; then
        log_error "GEMINI_API_KEY is not set! Please provide it via the .env file."
        exit 1
    fi
    log_ok "GEMINI_API_KEY is set."
    log_info "Starting FastAPI backend in PRODUCTION mode (gunicorn + uvicorn workers)..."
    local WORKERS="${WEB_CONCURRENCY:-$(( $(nproc) * 2 + 1 ))}"
    local MAX_WORKERS="${MAX_WORKERS:-8}"
    # Cap workers at MAX_WORKERS
    [ "$WORKERS" -gt "$MAX_WORKERS" ] && WORKERS="$MAX_WORKERS"

    log_info "Using $WORKERS worker(s)."
    exec gunicorn backend.main:app \
        --bind "${BACKEND_HOST:-0.0.0.0}:${BACKEND_PORT:-8000}" \
        --worker-class uvicorn.workers.UvicornWorker \
        --workers "$WORKERS" \
        --timeout "${GUNICORN_TIMEOUT:-120}" \
        --keepalive "${GUNICORN_KEEPALIVE:-5}" \
        --graceful-timeout "${GUNICORN_GRACEFUL_TIMEOUT:-30}" \
        --log-level "${LOG_LEVEL:-warning}" \
        --access-logfile /app/logs/access.log \
        --error-logfile /app/logs/error.log \
        --capture-output \
        --forwarded-allow-ips "*" \
        &
    PID=$!
    wait "$PID"
}

# ---------------------------------------------------------------------------
# Start the Streamlit frontend (development)
# ---------------------------------------------------------------------------
start_frontend_dev() {
    log_info "Starting Streamlit frontend in DEVELOPMENT mode (hot-reload enabled)..."
    exec python -m streamlit run frontend/streamlit_app.py \
        --server.port "${FRONTEND_PORT:-8501}" \
        --server.address "${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}" \
        --server.headless true \
        --server.runOnSave true \
        --logger.level debug \
        &
    PID=$!
    wait "$PID"
}

# ---------------------------------------------------------------------------
# Start the Streamlit frontend (production)
# ---------------------------------------------------------------------------
start_frontend_prod() {
    log_info "Starting Streamlit frontend in PRODUCTION mode..."
    exec python -m streamlit run frontend/streamlit_app.py \
        --server.port "${FRONTEND_PORT:-8501}" \
        --server.address "${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}" \
        --server.headless true \
        --server.runOnSave false \
        --browser.gatherUsageStats false \
        --logger.level "${LOG_LEVEL:-warning}"
}

# ---------------------------------------------------------------------------
# Main entrypoint dispatcher
# ---------------------------------------------------------------------------
main() {
    local COMMAND="${1:-backend}"
    log_info "==================================================================="
    log_info " Menu Extraction System v2.0 - Starting: '$COMMAND'"
    log_info " Environment : ${APP_ENV:-production}"
    log_info " Python      : $(python --version)"
    log_info " Hostname    : $(hostname)"
    log_info "==================================================================="

    # Run pre-flight checks for all services
    preflight_checks

    case "$COMMAND" in
        "backend" | "backend-prod")
            wait_for_dependencies
            start_backend_prod
            ;;
        "backend-dev")
            wait_for_dependencies
            start_backend_dev
            ;;
        "frontend" | "frontend-prod")
            start_frontend_prod
            ;;
        "frontend-dev")
            start_frontend_dev
            ;;
        "shell" | "bash")
            log_info "Starting interactive shell..."
            exec /bin/bash
            ;;
        "test")
            log_info "Running tests..."
            exec python -m pytest tests/ -v --tb=short "${@:2}"
            ;;
        *)
            log_warn "Unknown command '$COMMAND'. Treating as direct exec..."
            exec "$@"
            ;;
    esac
}

main "$@"
