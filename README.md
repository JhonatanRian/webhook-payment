# Webhook Payment Integration with Stark Bank

[![CI/CD Pipeline](https://github.com/JhonatanRian/webhook-payment/actions/workflows/deploy.yml/badge.svg)](https://github.com/JhonatanRian/webhook-payment/actions/workflows/deploy.yml)
[![codecov](https://codecov.io/gh/JhonatanRian/webhook-payment/branch/master/graph/badge.svg)](https://codecov.io/gh/JhonatanRian/webhook-payment)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

FastAPI application built with a **Modular Monolith** architecture for payment and webhook integration with the Stark Bank Sandbox API. The system issues batches of 8 to 12 invoices at configurable intervals (`SCHEDULER_INTERVAL_MINUTES`, default 180 min / 3 hours) via APScheduler over a 24-hour cycle, receives credit notifications via ECDSA-signed Webhooks, and automatically transfers credited net amounts to the designated Stark Bank account.

---

## 📖 Conheça o Projeto (Documentação Completa)

Acesse o portal completo de documentação publicado no **[GitHub Pages](https://jhonatanrian.github.io/webhook-payment/)** ou navegue pelos tópicos na pasta [`docs/`](docs/index.md):

* 🏛️ **[Arquitetura & Design de Software](docs/architecture.md)** — Estrutura em Monólito Modular, separação em 4 camadas e banco assíncrono.
* 📋 **[Regras de Negócio & Ciclos de 24h](docs/business-rules.md)** — Motor do agendador, modos `once` vs `recurring`, cálculo de valor líquido e assinaturas ECDSA.
* 📌 **[Catálogo Completo de Endpoints](docs/api-reference.md)** — Especificação de rotas, contratos de entrada/saída e códigos de status.
* 🚢 **[Deploy, Infraestrutura & CI/CD](docs/deployment.md)** — Imagem Alpine de 70 MB com `uv`, GHCR, Portainer Webhooks e Traefik v3.
* 🧪 **[Estratégia de Testes & Qualidade](docs/testing.md)** — 78 testes automatizados, concorrência adversarial, idempotência e cobertura de 98%.
* 🛠️ **[Ferramental, Linters & Configurações](docs/tooling.md)** — Astral `uv`, Ruff, configurações do `pyproject.toml` e Git pre-push hooks.

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

## 🐳 Deployment with Docker & Portainer (VPS + Traefik)

The project includes an ultra-lightweight, production-grade **Alpine Linux** container image (`ghcr.io/jhonatanrian/webhook-payment:latest`) built with **Astral `uv`**, **Nginx Unix Domain Socket Reverse Proxy**, and **Pure Uvicorn**.

### 1. Portainer Stack (Recommended for VPS)

Create a new stack in Portainer using the provided [`docker-compose.yml`](docker-compose.yml):

```yaml
version: "3.8"

services:
  app:
    image: ghcr.io/jhonatanrian/webhook-payment:latest
    restart: always
    environment:
      - ENVIRONMENT=${ENVIRONMENT:-sandbox}
      - DATABASE_URL=sqlite+aiosqlite:////data/webhook_payment.db
      - STARK_PROJECT_ID=${STARK_PROJECT_ID}
      - STARK_PRIVATE_KEY=${STARK_PRIVATE_KEY}
      - SCHEDULER_MODE=${SCHEDULER_MODE:-once}
      - SCHEDULER_INTERVAL_MINUTES=${SCHEDULER_INTERVAL_MINUTES:-180}
    volumes:
      - payment_data:/data
    networks:
      - public
    deploy:
      replicas: 1
      labels:
        - "traefik.enable=true"
        - "traefik.docker.network=public"
        - "traefik.http.routers.payment.rule=Host(`${DOMAIN:-payment.jrmdev.com.br}`)"
        - "traefik.http.routers.payment.entrypoints=websecure"
        - "traefik.http.routers.payment.tls.certresolver=myresolver"
        - "traefik.http.services.payment.loadbalancer.server.port=8080"

volumes:
  payment_data:
    name: webhook_payment_data

networks:
  public:
    external: true
```

### 2. Auto-Deploy with Portainer Webhooks

Enable **Auto-update / Webhook** in your Portainer stack and set the secret `PORTAINER_WEBHOOK_URL` in GitHub Secrets. Every merge to `master` will build the image to GHCR and notify Portainer to redeploy automatically!

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
