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

PORT="${PORT:-80}"
HOST="${HOST:-0.0.0.0}"
SSL_CERTFILE="${SSL_CERTFILE:-}"
SSL_KEYFILE="${SSL_KEYFILE:-}"

if [ -n "$SSL_CERTFILE" ] || [ -n "$SSL_KEYFILE" ]; then
  if [ -z "$SSL_CERTFILE" ] || [ -z "$SSL_KEYFILE" ]; then
    echo "Both SSL_CERTFILE and SSL_KEYFILE must be set to enable HTTPS." >&2
    exit 1
  fi

  uvicorn app.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --ssl-certfile "$SSL_CERTFILE" \
    --ssl-keyfile "$SSL_KEYFILE"
else
  uvicorn app.main:app --host "$HOST" --port 8000 #"$PORT"
fi
