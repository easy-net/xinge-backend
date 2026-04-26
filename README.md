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
- if you want real WeChat Pay, also set:
  - `PAYMENT_MODE=real`
  - `WECHAT_MCH_ID`
  - `WECHAT_NOTIFY_URL`
  - `WECHAT_PRIVATE_KEY_PATH`
  - `WECHAT_SERIAL_NO`
  - `WECHAT_API_V3_KEY`
  - `WECHAT_PLATFORM_CERT_PATH`
  - optionally `WECHAT_PLATFORM_SERIAL_NO`

The app now validates production settings on startup. If you keep `APP_ENV=production` and `ALLOW_EPHEMERAL_DB=false`, `sqlite` is rejected.

## Auth Flow

The backend now supports a two-step mini program auth flow:

1. Call `/api/v1/mp/auth/login` with a fresh `X-Login-Code`
2. Read `data.access_token` from the response
3. Call subsequent private APIs with `Authorization: Bearer <access_token>`

The issued access token lifetime defaults to 24 hours and can be changed with `AUTH_TOKEN_TTL_SECONDS`.

For backward compatibility, the older `X-Login-Code`-based private API flow still works, but it will continue to consume a fresh WeChat code on every request.

## WeChat SSL Troubleshooting

If `jscode2session` fails with `SSLCertVerificationError` or `self-signed certificate`, check the startup environment logs for proxy-related variables such as `HTTPS_PROXY`, `HTTP_PROXY`, `ALL_PROXY`, `REQUESTS_CA_BUNDLE`, and `SSL_CERT_FILE`.

This project now supports:

- `WECHAT_VERIFY_SSL=true|false`
- `WECHAT_CA_BUNDLE_PATH=/path/to/custom-ca.pem`

Use `WECHAT_CA_BUNDLE_PATH` when your cloud environment uses a custom outbound proxy certificate. Avoid setting `WECHAT_VERIFY_SSL=false` except as a temporary diagnostic step.

## Real WeChat Pay Setup

If you already have a verified payment setup under `payment-backend`, you can reuse its certificate files directly.

Example local paths:

```bash
WECHAT_PRIVATE_KEY_PATH=../xinge/payment-backend/certs/apiclient_key.pem
WECHAT_PLATFORM_CERT_PATH=../xinge/payment-backend/certs/wechatpay_platform.pem
```

Or if you start `xinge-backend` from this repo root, these also work:

```bash
WECHAT_PRIVATE_KEY_PATH=./xinge-backend/payment-backend/certs/apiclient_key.pem
WECHAT_PLATFORM_CERT_PATH=./xinge-backend/payment-backend/certs/wechatpay_platform.pem
```

Current payment behavior:

- `/mp/orders` returns real `payment_params` for `wx.requestPayment()` when `PAYMENT_MODE=real` and all required WeChat Pay config is present.
- `/mp/orders/notify/wechat` accepts both the existing mock callback body and the real WeChat Pay v3 callback body.
- if payment config is incomplete, the backend automatically falls back to mock payment params.

## Dev Auth Bypass

For local or test-only curl debugging, you can enable:

```bash
export DEV_AUTH_BYPASS=true
export LOG_MP_REPORT_PAYLOADS=true
export LOG_ALL_API_PAYLOADS=true
export UNSAFE_DISABLE_VALIDATION=true
export LOG_CURRENT_USER_RESOLUTION=true
```

When enabled, the app derives a stable fake `openid` from `X-Login-Code` so private endpoints can be exercised without calling real WeChat login. Do not enable this in production.

With `LOG_MP_REPORT_PAYLOADS=true`, the `/mp/reports` create API logs sanitized request and response payloads with the same `request_id`, which is helpful when debugging `create_report` in local runs or cloud logs.

With `LOG_ALL_API_PAYLOADS=true`, every API request under `/api/` logs its request and response payloads together with request id, method, path, status code, and a few key headers. This is the easiest switch to turn on when you want to debug all interfaces end to end.

With `UNSAFE_DISABLE_VALIDATION=true`, private endpoints bypass auth and required MP headers, and a synthetic user is auto-created from the request context. This mode is intentionally blocked in `production` and should only be used for local debugging.

With `LOG_CURRENT_USER_RESOLUTION=true`, every private request logs which `user_id/open_id` the server resolved, along with request path and request id. This is useful when checking why `create_report` and `reports/list` do not appear to hit the same user context.

If you want the withdrawal admin page to approve requests without calling real WeChat transfer validation for a while, set:

```bash
export UNSAFE_ADMIN_WITHDRAW_APPROVE=true
```

When this switch is enabled, the admin withdrawal approval endpoint marks the request as `paid` directly and writes a mock `transfer_bill_no`. This switch is intended only for temporary internal testing.
