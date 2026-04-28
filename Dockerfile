FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    APP_ENV=development \
    ENCRYPTION_KEY=replace-with-a-32-char-or-longer-secret-key \
    ALLOW_EPHEMERAL_DB=false \
    HOST=0.0.0.0 \
    PORT=80 \
    PAYMENT_MODE=real \
    WECHAT_APP_ID=wx119f24d9ccbc9c30 \
    WECHAT_APP_SECRET=48fefa624916686de082e1062f01350f \
    WECHAT_MCH_ID=1557360721 \
    WECHAT_NOTIFY_URL=https://api.xgt.news/api/v1/payments/notify \
    WECHAT_TRANSFER_NOTIFY_URL=https://api.xgt.news/api/v1/payments/transfer/notify \
    WECHAT_PRIVATE_KEY_PATH=./certs/apiclient_key.pem \
    WECHAT_SERIAL_NO=4C314C9C5A11927DB816A1958B3566A41BC0B8B0 \
    WECHAT_API_V3_KEY=fc3c7483b4847565cfdf8ed61684dd90 \
    WECHAT_PLATFORM_CERT_PATH=./certs/wechatpay_platform.pem \
    WECHAT_PLATFORM_SERIAL_NO= \
    WECHAT_CALLBACK_TOLERANCE=300 \
    WECHAT_TRANSFER_SCENE_ID=1005 \
    WECHAT_TRANSFER_REMARK=xinge \
    DISTRIBUTOR_WITHDRAW_AUTO_APPROVE_FEN=10000 \
    WECHAT_VERIFY_SSL=true \
    WECHAT_CA_BUNDLE_PATH= \
    DEV_AUTH_BYPASS=false \
    LOG_MP_REPORT_PAYLOADS=false \
    UNSAFE_DISABLE_VALIDATION=false \
    LOG_CURRENT_USER_RESOLUTION=false \
    LOG_ALL_API_PAYLOADS=true \
    UNSAFE_ADMIN_WITHDRAW_APPROVE=false

WORKDIR /app

COPY pyproject.toml setup.py README.md /app/
COPY app /app/app
COPY .env.example /app/.env.example
COPY scripts /app/scripts
COPY static /app/static
COPY migrations /app/migrations
COPY alembic.ini /app/alembic.ini

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && update-ca-certificates \
    && apt-get clean \
    && rm -rf /var/cache/apt/archives/* \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip \
    && pip install .

EXPOSE 80

CMD ["sh", "/app/scripts/run_api.sh"]
