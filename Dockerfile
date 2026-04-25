FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=80

WORKDIR /app

COPY pyproject.toml setup.py README.md /app/
COPY app /app/app
COPY static /app/static
COPY migrations /app/migrations
COPY alembic.ini /app/alembic.ini

RUN pip install --upgrade pip && pip install .

EXPOSE 80

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-80}"]
