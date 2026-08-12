# Webhook Payment Integration with Stark Bank

Aplicação FastAPI desenvolvida em arquitectura de Monólito Modular (*Modular Monolith*) para integração de pagamentos e webhooks com a API Sandbox da Stark Bank. O sistema emite faturas em lote a cada 3 horas via APScheduler, recebe notificações de crédito via Webhook POST ECDSA e realiza transferências automáticas de saldo para a conta destino da Stark Bank.

---

## Como Rodar o Projeto

### 1. Ativar o Ambiente Virtual (Python 3.12+)

```bash
source /home/jhonatan/projects/webhook-payment/.venv/bin/activate
```

*(Ou crie/instale as dependências usando `uv`)*:
```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

---

### 2. Configurar Variáveis de Ambiente (`.env`)

Copie o arquivo de exemplo `.env.example` para `.env`:
```bash
cp .env.example .env
```

Ajuste as credenciais `STARK_PROJECT_ID` e `STARK_PRIVATE_KEY` conforme necessário.

---

### 3. Rodar Migrações do Banco de Dados (SQLite + Alembic)

Para aplicar as migrações e criar o esquema das tabelas SQLite:

```bash
alembic upgrade head
```

---

### 4. Executar o Servidor de Desenvolvimento (FastAPI)

```bash
uvicorn app.main:app --reload
```

Acesse a documentação interativa das APIs:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Suíte de Testes

Executar todos os testes unitários e de integração com Pytest:

```bash
pytest -v
```

---

## 🧹 Qualidade de Código & Linter (Ruff)

O projeto utiliza o **Ruff** configurado com as regras PEP 8 (`E`, `F`, `W`), complexidade ciclomática (`C90`), ordenação de imports (`I` / `isort`) e modernização de tipagem Python (`UP` / `pyupgrade`):

* **Verificar linter e imports não utilizados/desorganizados:**
  ```bash
  ruff check .
  ```

* **Corrigir automaticamente regras do linter e ordenar imports:**
  ```bash
  ruff check --fix .
  ```

* **Formatar o código:**
  ```bash
  ruff format .
  ```

---

## 📌 Principais Endpoints da API

| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| `POST` | `/api/v1/webhooks/starkbank` | Endpoint principal de Webhook que valida assinatura ECDSA e agenda transferência |
| `POST` | `/api/v1/invoices/batch` | Dispara manualmente um lote de 8 a 12 faturas com dados fictícios (`Faker`) |
| `GET` | `/api/v1/invoices/batches` | Lista todos os lotes de faturas emitidos |
| `GET` | `/api/v1/transfers` | Lista os registros de transferências realizadas |
| `GET` | `/api/v1/scheduler/status` | Retorna o status do agendador (ciclos executados de 1 a 8) |
| `POST` | `/api/v1/scheduler/trigger` | Dispara manualmente o ciclo do agendador |
| `GET` | `/health` | Health check da aplicação |
