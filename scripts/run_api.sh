#!/usr/bin/env sh
set -eu

export DEV_AUTH_BYPASS=true
export LOG_MP_REPORT_PAYLOADS=true
export LOG_MP_REQUESTS=true
PORT="${PORT:-8000}"
uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
