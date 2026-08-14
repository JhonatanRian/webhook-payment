# Webhook Payment Integration with Stark Bank

[![CI/CD Pipeline](https://github.com/JhonatanRian/webhook-payment/actions/workflows/deploy.yml/badge.svg)](https://github.com/JhonatanRian/webhook-payment/actions/workflows/deploy.yml)
[![codecov](https://codecov.io/gh/JhonatanRian/webhook-payment/branch/master/graph/badge.svg)](https://codecov.io/gh/JhonatanRian/webhook-payment)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

FastAPI application built with a **Modular Monolith** architecture for payment and webhook integration with the Stark Bank Sandbox API. The system issues batches of 8 to 12 invoices at configurable intervals (`SCHEDULER_INTERVAL_MINUTES`, default 180 min / 3 hours) via APScheduler over a 24-hour cycle, receives credit notifications via ECDSA-signed Webhooks, and automatically transfers credited net amounts to the designated Stark Bank account.

---

## 🔑 Prerequisites: ECDSA Private & Public Keys

To authenticate and operate with Stark Bank (Sandbox or Production), you need an **ECDSA key pair** (`secp256k1`).

1. **Generate your keys**:
   Follow the official Stark Bank guide: **[How to Create ECDSA Keys](https://docs.starkbank.com/how-to-create-ecdsa-keys)**

   Alternatively, you can generate them using the Python SDK:
   ```python
   import starkbank

   private_key, public_key = starkbank.key.create()
   print("Private Key:\n", private_key)
   print("Public Key:\n", public_key)
   ```

2. **Register the Public Key**:
   Copy the generated `public_key` and register it in the [Stark Bank Sandbox Dashboard](https://sandbox.starkbank.com) under **Settings > Keys / Projects**.

3. **Save your Private Key**:
   Keep your `private_key` safe. You can supply it via the `.env` file or environment variables (`STARK_PRIVATE_KEY` or `STARK_PRIVATE_KEY_PATH`).

---

## 🐳 Running with Docker (Recommended)

The project includes an ultra-lightweight, production-grade **Alpine Linux** container image built with **Astral `uv`**, **Nginx Unix Domain Socket Reverse Proxy**, and **Pure Uvicorn** multi-workers.

### 1. Build the Docker Image

```bash
docker build -t webhook-payment:alpine-uv .
```

### 2. Run the Container

* **Using `.env` file:**
  ```bash
  docker run -d --rm --name webhook-payment \
    -p 8080:8080 \
    --env-file .env \
    webhook-payment:alpine-uv
  ```

* **Or using inline environment variables:**
  ```bash
  docker run -d --rm --name webhook-payment \
    -p 8080:8080 \
    -e ENVIRONMENT=sandbox \
    -e STARK_PROJECT_ID="<YOUR_PROJECT_ID>" \
    -e STARK_PRIVATE_KEY="$(cat privateKey.pem)" \
    webhook-payment:alpine-uv
  ```

### 3. Access Interactive API Documentation

- **Swagger UI:** [http://localhost:8080/docs](http://localhost:8080/docs)
- **ReDoc:** [http://localhost:8080/redoc](http://localhost:8080/redoc)
- **Health Check:** [http://localhost:8080/health](http://localhost:8080/health)

---

## 💻 Local Development Setup (Without Docker)

### 1. Install Dependencies with `uv`

```bash
uv sync --dev
```

### 2. Configure Environment Variables (`.env`)

Copy the example configuration file and fill in your credentials:
```bash
cp .env.example .env
```

### 3. Run Database Migrations (SQLite + Alembic)

```bash
alembic upgrade head
```

### 4. Start the Development Server (FastAPI)

```bash
uvicorn app.main:app --reload
```

---

## 🧪 Test Suite

Run all unit, integration, and adversarial tests with Pytest and coverage report:

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
