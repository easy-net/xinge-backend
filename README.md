# xinge-backend

Python-first implementation of the WeChat mini program backend described in `swagger.yaml`.

## Current Scope

- App skeleton with FastAPI
- Unified response envelope and exception handling
- Database/session scaffolding
- Initial MP auth, user, school, and product config APIs
- Pytest-based test layout

## Local Setup

1. Create a virtualenv with Python 3.9+
2. Install dependencies:

```bash
python3 -m pip install -e ".[dev]"
```

Or use conda:

```bash
conda env create -f environment.yml
conda activate xinge-backend
pip install -e ".[dev]"
```

3. Start the API:

```bash
uvicorn app.main:app --reload
```

## Health Endpoints

- `GET /healthz`
- `GET /readyz`

## WeChat Cloud Hosting

This repo now includes:

- `Dockerfile`
- `.dockerignore`
- `container.config.json`

The current default cloud runtime uses `sqlite` in `/tmp/xinge.db` only for smoke deployment. For a persistent production deployment, switch `DATABASE_URL` to MySQL before going live.
# xinge-backend
