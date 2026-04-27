FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    WECHAT_VERIFY_SSL=true \
    WECHAT_CA_BUNDLE_PATH= \
    HOST=0.0.0.0 \
    PORT=80

WORKDIR /app

COPY pyproject.toml setup.py README.md /app/
COPY app /app/app
COPY certs /app/certs
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
