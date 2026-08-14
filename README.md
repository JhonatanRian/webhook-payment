# Webhook Payment Integration with Stark Bank

FastAPI application built with a **Modular Monolith** architecture for payment and webhook integration with the Stark Bank Sandbox API. The system issues batches of 8 to 12 invoices at configurable intervals (`SCHEDULER_INTERVAL_MINUTES`, default 180 min / 3 hours) via APScheduler over a 24-hour cycle, receives credit notifications via ECDSA-signed Webhooks, and automatically transfers credited net amounts to the designated Stark Bank account.

---

## Getting Started

### 1. Install Dependencies with `uv`

```bash
uv sync --dev
```

---

### 2. Configure Environment Variables (`.env`)

Copy the example configuration file:
```bash
cp .env.example .env
```

Configure your `STARK_PROJECT_ID` and `STARK_PRIVATE_KEY` (or `STARK_PRIVATE_KEY_PATH`) accordingly.

---

### 3. Run Database Migrations (SQLite + Alembic)

```bash
alembic upgrade head
```

---

### 4. Start the Development Server (FastAPI)

```bash
uvicorn app.main:app --reload
```

Interactive API documentation:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Test Suite

Run unit and integration tests with Pytest and coverage report:

```bash
uv run pytest -v --cov=app --cov-report=term-missing
```

---

## 🧹 Code Quality & Linter (Ruff)

* **Check lint and import ordering:**
  ```bash
  uv run ruff check .
  ```

* **Automatically fix lint issues:**
  ```bash
  uv run ruff check --fix .
  ```

* **Format codebase:**
  ```bash
  uv run ruff format .
  ```

---

## 📌 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/webhooks/starkbank` | Webhook endpoint validating ECDSA signatures and dispatching payouts |
| `POST` | `/api/v1/invoices/batch` | Manually triggers issuance of a batch of 8–12 invoices |
| `GET` | `/api/v1/invoices/batches` | Lists all issued invoice batches and items |
| `GET` | `/api/v1/transfers` | Lists recorded payout transfers |
| `GET` | `/api/v1/scheduler/status` | Returns scheduler status (completed cycles, remaining, mode, next run) |
| `POST` | `/api/v1/scheduler/trigger` | Triggers an immediate on-demand invoice cycle |
| `PUT` | `/api/v1/scheduler/mode` | Updates scheduler mode (`once` vs `recurring`) |
| `POST` | `/api/v1/scheduler/reset` | Resets stored cycle execution history in database |
| `GET` | `/health` | Application health check endpoint |
