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

Or:

```bash
sh scripts/run_api.sh
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

## Production Config

Use `.env.example` as the baseline:

- set `DATABASE_URL` to a real MySQL instance
- set `ENCRYPTION_KEY` to a secret with at least 32 characters
- set `ALLOW_EPHEMERAL_DB=false`
- set `WECHAT_APP_ID` and `WECHAT_APP_SECRET` for real mini program login
- `/mp/auth/bind-phone` will call WeChat `getuserphonenumber` with the `phone_code` from `wx.getPhoneNumber()`

The app now validates production settings on startup. If you keep `APP_ENV=production` and `ALLOW_EPHEMERAL_DB=false`, `sqlite` is rejected.

## Dev Auth Bypass

For local or test-only curl debugging, you can enable:

```bash
export DEV_AUTH_BYPASS=true
export LOG_MP_REPORT_PAYLOADS=true
export UNSAFE_DISABLE_VALIDATION=true
export LOG_CURRENT_USER_RESOLUTION=true
```

When enabled, the app derives a stable fake `openid` from `X-Login-Code` so private endpoints can be exercised without calling real WeChat login. Do not enable this in production.

With `LOG_MP_REPORT_PAYLOADS=true`, the `/mp/reports` create API logs sanitized request and response payloads with the same `request_id`, which is helpful when debugging `create_report` in local runs or cloud logs.

With `UNSAFE_DISABLE_VALIDATION=true`, private endpoints bypass auth and required MP headers, and a synthetic user is auto-created from the request context. This mode is intentionally blocked in `production` and should only be used for local debugging.

With `LOG_CURRENT_USER_RESOLUTION=true`, every private request logs which `user_id/open_id` the server resolved, along with request path and request id. This is useful when checking why `create_report` and `reports/list` do not appear to hit the same user context.
