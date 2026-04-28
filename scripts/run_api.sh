#!/usr/bin/env sh
set -eu


# export LOG_CURRENT_USER_RESOLUTION=true 
# export UNSAFE_DISABLE_VALIDATION=true
# export DEV_AUTH_BYPASS=true
# export LOG_MP_REPORT_PAYLOADS=true

#export DEV_AUTH_BYPASS=true
#export LOG_MP_REPORT_PAYLOADS=true
#export LOG_MP_REQUESTS=true

# shellcheck disable=SC1091
if [ -f ".env" ]; then
  set -a
  . ".env"
  set +a
fi

CLI_PORT="${1:-}"
PORT="${PORT:-80}"
HOST="${HOST:-0.0.0.0}"

if [ -n "$CLI_PORT" ]; then
  PORT="$CLI_PORT"
fi

uvicorn app.main:app --host "$HOST" --port "$PORT"
