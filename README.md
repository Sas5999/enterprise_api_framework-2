# Enterprise API Automation Framework

A production-grade, 4-layer API test automation framework built for teams. Clone it, configure your target API, and the whole company can start writing and running tests immediately.

---

## Architecture: 4-Layer Design

```
┌────────────────────────────────────────────────────────────┐
│  Layer 4 — TEST LAYER      tests/                          │
│  Smoke · Functional · Schema · Performance · Regression     │
├────────────────────────────────────────────────────────────┤
│  Layer 3 — ACTION LAYER    actions/                        │
│  Business operations (what we do, not how)                 │
├────────────────────────────────────────────────────────────┤
│  Layer 2 — API LAYER       api/                            │
│  HTTP client · Endpoints · Fluent response wrapper         │
├────────────────────────────────────────────────────────────┤
│  Layer 1 — FOUNDATION      config/ · utils/ · schemas/     │
│  Settings · Logging · Factories · Schema contracts         │
└────────────────────────────────────────────────────────────┘
```

| Layer | Folder | Responsibility |
|-------|--------|---------------|
| Foundation | `config/`, `utils/`, `schemas/`, `data/` | Settings, logging, test-data factories, JSON schema contracts |
| API | `api/` | HTTP transport, retry, connection pooling, sensitive field masking, metrics |
| Action | `actions/` | Business-level operations — `user_actions.get_user(2)` not `client.get("/api/users/2")` |
| Test | `tests/` | Pytest classes: smoke, positive, negative, schema, performance, regression |

---

## Project Structure

```
enterprise_api_framework/
├── api/
│   ├── client.py          # Enterprise HTTP client (retry, metrics, masking)
│   └── endpoints.py       # Single source of truth for all API paths
├── actions/
│   ├── user_actions.py    # User resource business operations
│   └── auth_actions.py    # Authentication business operations
├── config/
│   └── settings.py        # Typed singleton config (dev/staging/uat/prod)
├── data/
│   └── factories/
│       └── user_factory.py # Dynamic test-data generation via Faker
├── schemas/
│   └── user_schemas.py    # JSON Schema contracts + validation helper
├── tests/
│   ├── smoke/             # < 30 s gate — runs on every commit
│   ├── users/             # Full user CRUD suite
│   └── auth/              # Login / register suite
├── utils/
│   ├── logger.py          # Rich console + JSON file logging
│   └── helpers.py         # retry decorator, assertion helpers
├── .github/workflows/
│   └── ci.yml             # 4-stage CI: quality → smoke → full → report
├── .pre-commit-config.yaml
├── conftest.py            # Fixtures, metrics, Allure enrichment
├── pytest.ini             # All markers, addopts, discovery settings
├── requirements.txt
└── .env.example
```

---

## Quick Start

### 1. Clone & Install

```bash
git clone <your-org/api-automation-framework>
cd enterprise_api_framework
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — set ENV, BASE_URL_DEV, API_KEY, etc.
```

### 3. Run Tests

```bash
# Smoke suite only (fastest — CI gate)
pytest -m smoke

# Full suite
pytest

# Parallel execution (recommended for large suites)
pytest -n auto

# Specific marker
pytest -m "positive and not performance"

# Single file
pytest tests/users/test_users.py -v

# With Allure report
pytest --alluredir=allure-results
allure serve allure-results
```

---

## Adding a New API Resource

1. **Endpoint** — add a group to `api/endpoints.py`:
   ```python
   @dataclass(frozen=True)
   class _OrderEndpoints:
       base: str = "/api/orders"
       def single(self, order_id: int) -> str: return f"{self.base}/{order_id}"
   ```

2. **Action** — create `actions/order_actions.py`:
   ```python
   class OrderActions:
       def get_order(self, order_id: int) -> APIResponse:
           return self._client.get(endpoints.orders.single(order_id))
   ```

3. **Schema** — add to `schemas/order_schemas.py`

4. **Factory** — add to `data/factories/order_factory.py`

5. **Tests** — create `tests/orders/test_orders.py`

6. **Fixture** — add `order_actions` fixture to `conftest.py`

---

## Test Markers

| Marker | When to run | Time |
|--------|-------------|------|
| `smoke` | Every commit, every PR | < 30 s |
| `positive` | Every PR | ~2 min |
| `negative` | Every PR | ~2 min |
| `schema` | Every PR (detects API drift) | ~1 min |
| `performance` | Nightly / release gate | ~3 min |
| `regression` | Full regression sweep | ~10 min |
| `wip` | Never in CI (dev only) | — |

---

## CI/CD Pipeline

```
push/PR → Quality Gate → Smoke Gate → Full Suite → Allure Report
                          ↑ fails here = no merge
```

- **Quality**: ruff lint + black format + mypy types
- **Smoke**: single-request breadth tests (< 30 s)
- **Full Suite**: parallel across Python 3.11 + 3.12
- **Allure Report**: auto-published to GitHub Pages on `main`

---

## Key Features

### Sensitive Field Masking
Passwords, tokens, and secrets are automatically redacted from all logs. No credentials in CI logs ever.

### Fluent Assertions
```python
user_actions.get_user(2) \
    .assert_status(200) \
    .assert_json_key("data") \
    .assert_response_time(settings.sla_read_ms) \
    .assert_content_type() \
    .attach_to_allure("Get User")
```

### Request Metrics
Every request is recorded to a thread-safe store. A summary is printed at session end and attached to Allure:
```
total=42  avg=180ms  max=620ms  failed=2
```

### JSON Schema Contracts
```python
validate_schema(resp.json(), SINGLE_USER_RESPONSE_SCHEMA, "SingleUserResponse")
```
Tests fail immediately if the API changes its response shape — before any consumer is affected.

### Test Data Factories
```python
payload = UserFactory.create()                # random valid user
payload = UserFactory.special_characters()    # XSS / injection attempt
payload = UserFactory.max_length_strings()    # boundary test
```

### Multi-Environment
```bash
ENV=staging pytest -m smoke    # points at staging base URL
ENV=prod    pytest -m smoke    # points at prod base URL
```

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ENV` | `dev` | Active environment (`dev\|staging\|uat\|prod`) |
| `BASE_URL_DEV` | `https://reqres.in` | Dev base URL |
| `API_KEY` | _(empty)_ | Bearer token injected into every request |
| `REQUEST_TIMEOUT` | `30` | HTTP timeout in seconds |
| `MAX_RETRIES` | `3` | Retry count for 5xx / network errors |
| `SLA_READ_MS` | `2000` | GET response-time budget (ms) |
| `SLA_WRITE_MS` | `3000` | POST/PUT response-time budget (ms) |
| `LOG_JSON` | `false` | Emit JSON logs (for ELK / Datadog / Splunk) |
| `PARALLEL_WORKERS` | `4` | Workers for `pytest -n` |

---

## Contribution Guide

1. Branch from `develop` — name it `feat/<ticket>` or `fix/<ticket>`
2. Run `pre-commit install` once — hooks enforce style automatically
3. Add tests for every new action
4. All smoke tests must pass before opening a PR
5. Mark work-in-progress tests with `@pytest.mark.wip` to keep CI green

---

*Built with Python · pytest · requests · Allure · Faker · jsonschema · Rich*
