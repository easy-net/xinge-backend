# WeChat Mini Program API Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first Python implementation of the WeChat mini program backend API defined in `swagger.yaml`, including async report/payment/distributor flows and a complete automated test suite.

**Architecture:** Use a Python single-repo, dual-process design with a FastAPI-based HTTP API and a worker process for async jobs. Keep route/schema code thin, isolate business rules in services, and abstract WeChat/COS/payment integrations so the system can later migrate to Go with minimal business-logic churn.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, MySQL, Redis, Celery or RQ, pytest, httpx, testcontainers-go equivalent in Python if needed, Docker for local parity.

---

### Task 1: Project Skeleton

**Files:**
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `app/api/__init__.py`
- Create: `app/api/routes/__init__.py`
- Create: `app/api/schemas/__init__.py`
- Create: `app/services/__init__.py`
- Create: `app/repositories/__init__.py`
- Create: `app/domain/__init__.py`
- Create: `app/integrations/__init__.py`
- Create: `app/tasks/__init__.py`
- Create: `app/core/__init__.py`
- Create: `app/db/__init__.py`
- Create: `app/db/models/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/integration/__init__.py`
- Create: `tests/contract/__init__.py`
- Create: `tests/fixtures/__init__.py`
- Create: `pyproject.toml`
- Create: `README.md`

**Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_health_route_exists():
    client = TestClient(create_app())
    response = client.get("/healthz")
    assert response.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_health.py -v`
Expected: FAIL because app entrypoint does not exist.

**Step 3: Write minimal implementation**

- Create `create_app()` factory in `app/main.py`
- Register `/healthz` and `/readyz`
- Add dependency metadata in `pyproject.toml`

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_health.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app tests pyproject.toml README.md
git commit -m "chore: bootstrap python api project skeleton"
```

### Task 2: App Config, Logging, Response Envelope, Error Handling

**Files:**
- Create: `app/core/config.py`
- Create: `app/core/logging.py`
- Create: `app/core/errors.py`
- Create: `app/core/response.py`
- Create: `app/api/middleware.py`
- Create: `tests/unit/test_response_envelope.py`
- Create: `tests/unit/test_error_handling.py`

**Step 1: Write the failing tests**

Write tests for:

- success response structure: `code`, `message`, `data`, `timestamp`
- public response without `user_info`
- error mapping from domain exception to swagger-style JSON

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_response_envelope.py tests/unit/test_error_handling.py -v`
Expected: FAIL because response helpers and exception handlers are missing.

**Step 3: Write minimal implementation**

- Add typed settings loader
- Implement response builders for public/private mp responses
- Implement custom exceptions and FastAPI exception handlers
- Add request ID logging middleware

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_response_envelope.py tests/unit/test_error_handling.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/core app/api/middleware.py tests/unit
git commit -m "feat: add app config response envelope and error handling"
```

### Task 3: Database Session, Base Models, Alembic Setup

**Files:**
- Create: `app/db/session.py`
- Create: `app/db/base.py`
- Create: `alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/script.py.mako`
- Create: `tests/unit/test_db_session.py`

**Step 1: Write the failing test**

Write a test that imports the DB session factory and verifies a session can be constructed with a test DSN.

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_db_session.py -v`
Expected: FAIL because DB setup is missing.

**Step 3: Write minimal implementation**

- Add SQLAlchemy engine/session factory
- Add declarative base
- Wire Alembic config

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_db_session.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/db alembic.ini migrations tests/unit/test_db_session.py
git commit -m "feat: add database session and migration scaffolding"
```

### Task 4: Core Data Models and Initial Migration

**Files:**
- Create: `app/db/models/user.py`
- Create: `app/db/models/device.py`
- Create: `app/db/models/report.py`
- Create: `app/db/models/order.py`
- Create: `app/db/models/payment_callback.py`
- Create: `app/db/models/distributor.py`
- Create: `app/db/models/message.py`
- Create: `app/db/models/school.py`
- Create: `migrations/versions/0001_initial_mp_schema.py`
- Create: `tests/unit/test_models_import.py`

**Step 1: Write the failing test**

Write a test that imports all ORM models and asserts table metadata includes expected table names.

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_models_import.py -v`
Expected: FAIL because models are missing.

**Step 3: Write minimal implementation**

- Define ORM models from the confirmed spec
- Include indexes and unique constraints for `openid`, `order_id`, `application_id`, `withdraw_id`
- Add initial Alembic migration

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_models_import.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/db/models migrations/versions tests/unit/test_models_import.py
git commit -m "feat: add core mp data models and initial migration"
```

### Task 5: Shared Test Fixtures and Integration Harness

**Files:**
- Create: `tests/fixtures/db.py`
- Create: `tests/fixtures/app.py`
- Create: `tests/fixtures/fakes.py`
- Create: `tests/conftest.py`
- Create: `tests/integration/test_app_boot.py`

**Step 1: Write the failing test**

Write an integration test that boots the app with fake settings and verifies `/healthz` returns 200.

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_app_boot.py -v`
Expected: FAIL because fixture wiring is missing.

**Step 3: Write minimal implementation**

- Add reusable app fixture
- Add fake WeChat, fake COS, fake payment gateway adapters
- Add transactional test DB fixture

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_app_boot.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/fixtures tests/conftest.py tests/integration/test_app_boot.py
git commit -m "test: add shared fixtures and integration harness"
```

### Task 6: WeChat Auth Adapter and Request Identity Dependency

**Files:**
- Create: `app/integrations/wechat_auth.py`
- Create: `app/api/deps.py`
- Create: `app/repositories/user_repository.py`
- Create: `app/services/auth_service.py`
- Create: `tests/unit/test_auth_service.py`
- Create: `tests/integration/test_mp_auth_login.py`

**Step 1: Write the failing tests**

Write tests for:

- code2session adapter interface behavior
- login creates a new user on first login
- login reuses existing user on repeated login
- missing `X-Login-Code` returns 401 or validation error per implementation choice

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_auth_service.py tests/integration/test_mp_auth_login.py -v`
Expected: FAIL because auth dependency and service are missing.

**Step 3: Write minimal implementation**

- Add WeChat auth adapter interface
- Add current-user dependency using `X-Login-Code`
- Persist user and device metadata
- Return swagger-compatible `/mp/auth/login` payload

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_auth_service.py tests/integration/test_mp_auth_login.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/integrations app/api/deps.py app/repositories/user_repository.py app/services/auth_service.py tests
git commit -m "feat: implement wechat login and user identity dependency"
```

### Task 7: Phone Binding and User Profile APIs

**Files:**
- Create: `app/api/routes/mp_auth.py`
- Create: `app/api/routes/mp_users.py`
- Create: `app/api/schemas/mp_auth.py`
- Create: `app/api/schemas/mp_users.py`
- Create: `app/core/security.py`
- Create: `tests/unit/test_phone_crypto.py`
- Create: `tests/integration/test_mp_bind_phone.py`
- Create: `tests/integration/test_mp_users.py`

**Step 1: Write the failing tests**

Write tests for:

- phone encryption and masking
- bind-phone updates user phone data
- `/mp/users/me`
- `/mp/users/me/update`

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_phone_crypto.py tests/integration/test_mp_bind_phone.py tests/integration/test_mp_users.py -v`
Expected: FAIL because routes and security helpers are missing.

**Step 3: Write minimal implementation**

- Add AES-256-GCM helper
- Add bind-phone service flow
- Add current user profile read/update endpoints

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_phone_crypto.py tests/integration/test_mp_bind_phone.py tests/integration/test_mp_users.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/api/routes app/api/schemas app/core/security.py tests
git commit -m "feat: add phone binding and user profile apis"
```

### Task 8: Public School Search APIs

**Files:**
- Create: `app/repositories/school_repository.py`
- Create: `app/services/school_service.py`
- Create: `app/api/routes/mp_schools.py`
- Create: `app/api/schemas/mp_schools.py`
- Create: `tests/integration/test_mp_schools.py`

**Step 1: Write the failing tests**

Write integration tests for:

- `/mp/schools/list`
- `/mp/schools/detail`
- 404 when school does not exist

**Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_mp_schools.py -v`
Expected: FAIL because school routes and repository are missing.

**Step 3: Write minimal implementation**

- Add school query repository methods
- Add public routes and schemas
- Seed test fixture school data

**Step 4: Run tests to verify they pass**

Run: `pytest tests/integration/test_mp_schools.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/repositories/school_repository.py app/services/school_service.py app/api/routes/mp_schools.py app/api/schemas/mp_schools.py tests
git commit -m "feat: implement public school search apis"
```

### Task 9: Product Config API

**Files:**
- Create: `app/db/models/product_config.py`
- Create: `app/repositories/product_config_repository.py`
- Create: `app/services/product_config_service.py`
- Create: `app/api/routes/mp_config.py`
- Create: `app/api/schemas/mp_config.py`
- Create: `tests/integration/test_mp_product_config.py`

**Step 1: Write the failing test**

Write an integration test for `/mp/config/product` covering pricing, discount, and display stats.

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_mp_product_config.py -v`
Expected: FAIL because the config API is missing.

**Step 3: Write minimal implementation**

- Add product config model and repository
- Add route and response schema
- Seed test config

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_mp_product_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/db/models/product_config.py app/repositories/product_config_repository.py app/services/product_config_service.py app/api/routes/mp_config.py app/api/schemas/mp_config.py tests
git commit -m "feat: add product config api"
```

### Task 10: Report Create/List/Detail APIs

**Files:**
- Create: `app/repositories/report_repository.py`
- Create: `app/services/report_service.py`
- Create: `app/api/routes/mp_reports.py`
- Create: `app/api/schemas/mp_reports.py`
- Create: `tests/unit/test_report_service.py`
- Create: `tests/integration/test_mp_reports_crud.py`

**Step 1: Write the failing tests**

Write tests for:

- creating a report
- listing reports in descending created order
- fetching report detail using the confirmed custom response structure
- ownership check returning 403

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_report_service.py tests/integration/test_mp_reports_crud.py -v`
Expected: FAIL because report domain logic is missing.

**Step 3: Write minimal implementation**

- Implement report creation and persistence
- Implement list and detail endpoints
- Keep `report_id` equal to internal report primary key

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_report_service.py tests/integration/test_mp_reports_crud.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/repositories/report_repository.py app/services/report_service.py app/api/routes/mp_reports.py app/api/schemas/mp_reports.py tests
git commit -m "feat: implement report create list and detail apis"
```

### Task 11: Payment Adapter and Order Create/Detail APIs

**Files:**
- Create: `app/integrations/wechat_pay.py`
- Create: `app/repositories/order_repository.py`
- Create: `app/services/order_service.py`
- Modify: `app/api/routes/mp_orders.py`
- Create: `app/api/schemas/mp_orders.py`
- Create: `tests/unit/test_order_service.py`
- Create: `tests/integration/test_mp_orders.py`

**Step 1: Write the failing tests**

Write tests for:

- create order rejects mismatched amount
- create order rejects duplicate pending order
- create order returns payment params
- order detail returns latest status

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_order_service.py tests/integration/test_mp_orders.py -v`
Expected: FAIL because order APIs and payment adapter are missing.

**Step 3: Write minimal implementation**

- Add payment adapter interface
- Implement order service validation logic
- Implement `/mp/orders` and `/mp/orders/detail`
- Update report state to `unpaid` after successful pending order creation

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_order_service.py tests/integration/test_mp_orders.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/integrations/wechat_pay.py app/repositories/order_repository.py app/services/order_service.py app/api/routes/mp_orders.py app/api/schemas/mp_orders.py tests
git commit -m "feat: implement order creation and detail apis"
```

### Task 12: Payment Callback Idempotency and Async Job Dispatch

**Files:**
- Create: `app/repositories/payment_callback_repository.py`
- Create: `app/tasks/report_tasks.py`
- Create: `app/tasks/commission_tasks.py`
- Create: `app/services/payment_notify_service.py`
- Create: `tests/unit/test_payment_notify_service.py`
- Create: `tests/integration/test_mp_payment_notify.py`

**Step 1: Write the failing tests**

Write tests for:

- valid notify marks order paid
- notify creates only one payment callback record
- duplicate notify does not duplicate report generation dispatch

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_payment_notify_service.py tests/integration/test_mp_payment_notify.py -v`
Expected: FAIL because callback processing is missing.

**Step 3: Write minimal implementation**

- Add callback verification and payload handling interface
- Implement idempotent payment processing
- Dispatch async report and commission jobs

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_payment_notify_service.py tests/integration/test_mp_payment_notify.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/repositories/payment_callback_repository.py app/tasks app/services/payment_notify_service.py tests
git commit -m "feat: implement wechat payment callback and async dispatch"
```

### Task 13: Report Progress, Asset Links, and Worker Flow

**Files:**
- Create: `app/services/report_generation_service.py`
- Modify: `app/tasks/report_tasks.py`
- Modify: `app/api/routes/mp_reports.py`
- Create: `tests/unit/test_report_generation_service.py`
- Create: `tests/integration/test_mp_report_status_links.py`

**Step 1: Write the failing tests**

Write tests for:

- report status transitions across stages
- failure stores `fail_stage`
- links endpoint returns only preview when unpaid
- links endpoint returns full assets when paid/completed

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_report_generation_service.py tests/integration/test_mp_report_status_links.py -v`
Expected: FAIL because worker flow and link generation are incomplete.

**Step 3: Write minimal implementation**

- Implement report stage progression
- Implement links endpoint using fake COS signed URLs
- Support success and failure transitions

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_report_generation_service.py tests/integration/test_mp_report_status_links.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/report_generation_service.py app/tasks/report_tasks.py app/api/routes/mp_reports.py tests
git commit -m "feat: add report progress and result link apis"
```

### Task 14: Message Center APIs

**Files:**
- Create: `app/repositories/message_repository.py`
- Create: `app/services/message_service.py`
- Create: `app/api/routes/mp_messages.py`
- Create: `app/api/schemas/mp_messages.py`
- Create: `tests/integration/test_mp_messages.py`

**Step 1: Write the failing tests**

Write tests for:

- listing unread and all messages
- marking only owned messages as read

**Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_mp_messages.py -v`
Expected: FAIL because message APIs are missing.

**Step 3: Write minimal implementation**

- Add message list/read routes
- Add ownership validation
- Add unread count support for `/mp/users/me`

**Step 4: Run tests to verify they pass**

Run: `pytest tests/integration/test_mp_messages.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/repositories/message_repository.py app/services/message_service.py app/api/routes/mp_messages.py app/api/schemas/mp_messages.py tests
git commit -m "feat: add message center apis"
```

### Task 15: Distributor Join, Apply, Status, Me

**Files:**
- Create: `app/repositories/distributor_repository.py`
- Create: `app/services/distributor_service.py`
- Create: `app/api/routes/mp_distributor.py`
- Create: `app/api/schemas/mp_distributor.py`
- Create: `tests/unit/test_distributor_service.py`
- Create: `tests/integration/test_mp_distributor_basic.py`

**Step 1: Write the failing tests**

Write tests for:

- join distributor by invite
- reject duplicate join
- apply distributor creates pending application
- application status returns latest record
- distributor me returns stats structure

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_distributor_service.py tests/integration/test_mp_distributor_basic.py -v`
Expected: FAIL because distributor flows are missing.

**Step 3: Write minimal implementation**

- Add join/apply/status/me routes
- Add basic distributor aggregate calculations
- Add message creation hooks for later approval notification

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_distributor_service.py tests/integration/test_mp_distributor_basic.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/repositories/distributor_repository.py app/services/distributor_service.py app/api/routes/mp_distributor.py app/api/schemas/mp_distributor.py tests
git commit -m "feat: implement basic distributor apis"
```

### Task 16: Distributor Downlines, Team, Quota Allocation

**Files:**
- Modify: `app/services/distributor_service.py`
- Modify: `app/api/routes/mp_distributor.py`
- Create: `tests/integration/test_mp_distributor_team_quota.py`

**Step 1: Write the failing tests**

Write tests for:

- direct downline listing
- grouped team response using the confirmed custom structure
- quota allocation success
- campus distributor forbidden to allocate
- non-direct-downline allocation forbidden

**Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_mp_distributor_team_quota.py -v`
Expected: FAIL because team and quota logic is incomplete.

**Step 3: Write minimal implementation**

- Implement downlines and grouped team queries
- Implement transactional quota allocation
- Add Redis-based or DB-lock-based anti-oversubscription protection

**Step 4: Run tests to verify they pass**

Run: `pytest tests/integration/test_mp_distributor_team_quota.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/distributor_service.py app/api/routes/mp_distributor.py tests/integration/test_mp_distributor_team_quota.py
git commit -m "feat: add distributor team and quota allocation apis"
```

### Task 17: Commissions and Withdrawals

**Files:**
- Modify: `app/services/distributor_service.py`
- Modify: `app/tasks/commission_tasks.py`
- Modify: `app/api/routes/mp_distributor.py`
- Create: `tests/integration/test_mp_distributor_finance.py`

**Step 1: Write the failing tests**

Write tests for:

- commission list pagination
- withdrawal creation
- insufficient withdrawable amount rejection
- withdrawal history listing

**Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_mp_distributor_finance.py -v`
Expected: FAIL because commission/withdraw APIs are incomplete.

**Step 3: Write minimal implementation**

- Implement commission list route
- Implement withdrawal application and history
- Store bank account encrypted and masked

**Step 4: Run tests to verify they pass**

Run: `pytest tests/integration/test_mp_distributor_finance.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/distributor_service.py app/tasks/commission_tasks.py app/api/routes/mp_distributor.py tests/integration/test_mp_distributor_finance.py
git commit -m "feat: implement distributor commissions and withdrawals"
```

### Task 18: Contract Test Suite for All `/mp/*` Endpoints

**Files:**
- Create: `tests/contract/test_mp_contract.py`
- Create: `tests/contract/swagger_parser.py`

**Step 1: Write the failing tests**

Write contract tests that assert:

- all implemented `/mp/*` routes exist
- required headers match for private APIs
- success/error envelopes match swagger style
- custom confirmed responses for `/mp/reports/detail` and `/mp/distributor/team` match the approved spec

**Step 2: Run tests to verify they fail**

Run: `pytest tests/contract/test_mp_contract.py -v`
Expected: FAIL until all endpoints are implemented and wired.

**Step 3: Write minimal implementation**

- Add contract introspection helper from `swagger.yaml`
- Normalize route registration if needed

**Step 4: Run tests to verify they pass**

Run: `pytest tests/contract/test_mp_contract.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/contract
git commit -m "test: add swagger contract coverage for mp apis"
```

### Task 19: End-to-End Core Flow Regression Suite

**Files:**
- Create: `tests/integration/test_mp_e2e_core_flow.py`

**Step 1: Write the failing test**

Write one end-to-end integration test covering:

- login
- bind phone
- create report
- create order
- fake payment notify
- poll report status
- fetch result links

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_mp_e2e_core_flow.py -v`
Expected: FAIL until all core flows are joined up correctly.

**Step 3: Write minimal implementation**

- Fix any missing wiring, transaction issues, or test fixtures found by the regression

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_mp_e2e_core_flow.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/integration/test_mp_e2e_core_flow.py app
git commit -m "test: add end to end mp core flow regression"
```

### Task 20: Local Dev, Worker Startup, and Cloud Hosting Docs

**Files:**
- Modify: `README.md`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `scripts/run_api.sh`
- Create: `scripts/run_worker.sh`
- Create: `tests/unit/test_settings_loading.py`

**Step 1: Write the failing test**

Write a test ensuring required settings load from environment and missing critical values fail fast.

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_settings_loading.py -v`
Expected: FAIL until settings validation is complete.

**Step 3: Write minimal implementation**

- Add `.env.example`
- Add local compose file for MySQL/Redis
- Add run scripts for api and worker
- Document WeChat cloud hosting deployment variables

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_settings_loading.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add README.md docker-compose.yml .env.example scripts tests/unit/test_settings_loading.py
git commit -m "docs: add local setup and cloud hosting runtime docs"
```

### Task 21: Full Test Run and Stabilization

**Files:**
- Modify: any previously touched files as needed

**Step 1: Run the full suite**

Run: `pytest tests -v`
Expected: identify any residual failures, flaky tests, or missing fixtures.

**Step 2: Fix minimal issues**

- Resolve deterministic failures only
- Keep behavior aligned with the confirmed spec

**Step 3: Re-run the full suite**

Run: `pytest tests -v`
Expected: PASS

**Step 4: Commit**

```bash
git add app tests README.md
git commit -m "test: stabilize full mp api suite"
```
