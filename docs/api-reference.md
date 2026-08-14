# 📌 Catálogo Completo de Endpoints da API

Abaixo está a documentação detalhada de todas as rotas HTTP disponibilizadas pela aplicação.

---

## 🧾 Módulo: Invoices (Faturas Pix)

### `POST /api/v1/invoices/batch`
Gera e emite imediatamente um lote de faturas Pix no Sandbox da Stark Bank.

- **Query Parameters:**
  - `count` *(opcional, int, 1 a 50)*: Quantidade customizada de faturas. Se omitido, gera um número aleatório entre 8 e 12.
- **Resposta Sucesso (`201 Created`):**
```json
{
  "id": "e8d47b6a12c3498bb892471629abc123",
  "total_amount": 145020,
  "invoice_count": 10,
  "created_at": "2026-08-14T03:00:00.123456Z",
  "items": [
    {
      "id": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d",
      "stark_invoice_id": "5839201948572019",
      "amount": 15000,
      "tax_id": "12345678909",
      "name": "Maria Silva",
      "status": "created"
    }
  ]
}
```

---

### `GET /api/v1/invoices/batches`
Retorna uma lista paginada de todos os lotes de faturas emitidos e seus itens associados.

- **Query Parameters:**
  - `page` *(opcional, int, padrão: 1)*: Número da página (1-indexed).
  - `size` *(opcional, int, padrão: 20, máx: 100)*: Quantidade de itens por página.
- **Resposta Sucesso (`200 OK`):**
```json
{
  "items": [
    {
      "id": "e8d47b6a12c3498bb892471629abc123",
      "cycle_index": 1,
      "invoice_count": 10,
      "status": "completed",
      "created": "2026-08-14T03:00:00.123456Z",
      "invoices": [...]
    }
  ],
  "total": 8,
  "page": 1,
  "size": 20,
  "pages": 1,
  "has_next": false,
  "has_previous": false
}
```

---

### `GET /api/v1/invoices`
Retorna uma lista paginada de todas as faturas individuais com suporte a filtro opcional por status.

- **Query Parameters:**
  - `status` *(opcional, str)*: Filtrar por status (ex: `created`, `credited`).
  - `page` *(opcional, int, padrão: 1)*: Número da página.
  - `size` *(opcional, int, padrão: 20, máx: 100)*: Quantidade de faturas por página.
- **Resposta Sucesso (`200 OK`):**
```json
{
  "items": [
    {
      "id": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d",
      "stark_invoice_id": "5839201948572019",
      "batch_id": "e8d47b6a12c3498bb892471629abc123",
      "amount": 15000,
      "tax_id": "12345678909",
      "name": "Maria Silva",
      "status": "credited",
      "created": "2026-08-14T03:00:00.123456Z"
    }
  ],
  "total": 80,
  "page": 1,
  "size": 20,
  "pages": 4,
  "has_next": true,
  "has_previous": false
}
```

---

## 📬 Módulo: Webhook

### `POST /api/v1/webhooks/starkbank`
Endpoint receptor dos eventos da Stark Bank. Valida a assinatura ECDSA e despacha transferências de liquidação para faturas creditadas.

- **Headers Obrigatórios:**
  - `Digital-Signature`: Assinatura digital ECDSA gerada pela Stark Bank.
- **Resposta Sucesso (`200 OK`):**
```json
{
  "status": "processed",
  "event_id": "5738291048592018",
  "event_type": "credited",
  "subscription": "invoice",
  "transfer_id": "4728193847291048"
}
```
- **Resposta Assinatura Inválida (`400 Bad Request`):**
```json
{
  "error": "invalid_signature",
  "code": "invalid_signature",
  "detail": "Failed to verify ECDSA signature: Digital signature verification failed."
}
```

---

## 💸 Módulo: Transfers (Transferências)

### `GET /api/v1/transfers`
Retorna uma lista paginada de todas as transferências de liquidação realizadas pelo sistema após recebimento de webhooks.

- **Query Parameters:**
  - `page` *(opcional, int, padrão: 1)*: Número da página (1-indexed).
  - `size` *(opcional, int, padrão: 20, máx: 100)*: Quantidade de transferências por página.
- **Resposta Sucesso (`200 OK`):**
```json
{
  "items": [
    {
      "id": "9f8e7d6c5b4a39281726354433221100",
      "stark_transfer_id": "4728193847291048",
      "stark_invoice_id": "5839201948572019",
      "event_id": "5738291048592018",
      "amount": 15000,
      "fee": 50,
      "net_amount": 14950,
      "status": "success",
      "created": "2026-08-14T03:15:22.000000Z"
    }
  ],
  "total": 12,
  "page": 1,
  "size": 20,
  "pages": 1,
  "has_next": false,
  "has_previous": false
}
```

---

## ⏰ Módulo: Scheduler (Agendador)

### `GET /api/v1/scheduler/status`
Retorna o estado operacional do agendador, contadores de ciclos e horário da próxima execução.

- **Resposta Sucesso (`200 OK`):**
```json
{
  "scheduled_cycles_completed": 3,
  "manual_triggers_completed": 1,
  "max_cycles": 8,
  "interval_minutes": 180,
  "remaining_cycles": 5,
  "mode": "once",
  "is_running": true,
  "next_run_time": "2026-08-14T06:00:00.000000Z"
}
```

---

### `POST /api/v1/scheduler/trigger`
Dispara um ciclo manual sob demanda. O lote é emitido e gravado como `trigger_type: "manual"`, sem consumir a cota dos ciclos agendados de 24 horas.

- **Resposta Sucesso (`202 Accepted`):**
```json
{
  "message": "Manual invoice batch cycle triggered successfully."
}
```

---

### `PUT /api/v1/scheduler/mode`
Altera dinamicamente o modo de operação do agendador sem precisar reiniciar a aplicação.

- **Payload de Entrada:**
```json
{
  "mode": "recurring"
}
```
- **Resposta Sucesso (`200 OK`):**
```json
{
  "message": "Scheduler mode successfully updated to 'recurring'.",
  "mode": "recurring"
}
```

---

### `POST /api/v1/scheduler/reset`
Limpa o histórico de ciclos armazenados na tabela `schedule_cycles`, reiniciando os contadores de 24h.

- **Resposta Sucesso (`200 OK`):**
```json
{
  "message": "Scheduler cycles reset successfully. Removed 8 record(s).",
  "mode": "once"
}
```

---

## 🩺 Módulo: Health Check

### `GET /health`
Verificação de integridade (*liveness / readiness probe*) utilizada pelo Nginx, Docker e orquestradores.

- **Resposta Sucesso (`200 OK`):**
```json
{
  "status": "ok",
  "service": "webhook-payment"
}
```
