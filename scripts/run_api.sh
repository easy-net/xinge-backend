#!/usr/bin/env sh
set -eu


# export LOG_CURRENT_USER_RESOLUTION=true 
# export UNSAFE_DISABLE_VALIDATION=true
# export DEV_AUTH_BYPASS=true
# export LOG_MP_REPORT_PAYLOADS=true

#export DEV_AUTH_BYPASS=true
#export LOG_MP_REPORT_PAYLOADS=true
#export LOG_MP_REQUESTS=true

# source .env
PORT="${PORT:-8000}"
uvicorn app.main:app --host 0.0.0.0 --port "$PORT"


