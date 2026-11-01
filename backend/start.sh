#!/usr/bin/env bash
set -e
export ENVIRONMENT="${ENVIRONMENT:-production}"
export DISABLE_EMBEDDED_WORKER="true"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-2}"

# Graceful shutdown handler
cleanup() {
    echo "[EVIDENTIA-AI] Stopping background worker (PID: $WORKER_PID)..."
    kill -TERM "$WORKER_PID" 2>/dev/null || true
    wait "$WORKER_PID" 2>/dev/null || true
    echo "[EVIDENTIA-AI] Worker stopped."
}
trap cleanup SIGTERM SIGINT EXIT

echo "[EVIDENTIA-AI] Starting background worker process (worker.py)..."
python worker.py &
WORKER_PID=$!

echo "[EVIDENTIA-AI] Starting production ASGI server on port ${PORT} with ${WORKERS} workers..."
uvicorn app:app --host 0.0.0.0 --port "${PORT}" --workers "${WORKERS}" --proxy-headers --forwarded-allow-ips "*" &
UVICORN_PID=$!

# Wait for uvicorn process
wait "$UVICORN_PID"
