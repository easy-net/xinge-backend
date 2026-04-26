FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=80

WORKDIR /app

COPY pyproject.toml setup.py README.md /app/
COPY app /app/app
COPY certs /app/certs
COPY .env /app/.env
COPY scripts /app/scripts
COPY static /app/static
COPY migrations /app/migrations
COPY alembic.ini /app/alembic.ini

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip \
    && pip install .

EXPOSE 80

CMD ["sh", "/app/scripts/run_api.sh"]
