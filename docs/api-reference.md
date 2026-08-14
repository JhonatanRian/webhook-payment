# 📌 Catálogo de Endpoints da API

Abaixo você encontra o guia prático de todas as rotas HTTP disponibilizadas pela aplicação.

---

## 🧾 Módulo de Invoices (Faturas Pix)

### `POST /api/v1/invoices/batch`
Gera e emite imediatamente um lote de faturas Pix no Sandbox da Stark Bank.

- **Query Parameters:**
  - `count` *(opcional, int)*: Quantidade de faturas a gerar. Se não informado, gera entre 8 e 12 aleatoriamente.
- **Resposta (`201 Created`):**
```json
{
  "id": "e8d47b6a-12c3-498b-b892-471629abc123",
  "cycle_index": 1,
  "invoice_count": 10,
  "status": "completed",
  "created_at": "2026-08-14T03:00:00.123456Z"
}
```

---

### `GET /api/v1/invoices/batches`
Retorna uma lista paginada de todos os lotes de faturas emitidos.

- **Query Parameters:**
  - `page` *(opcional, int, padrão: 1)*: Página atual.
  - `size` *(opcional, int, padrão: 20)*: Quantidade de itens por página.
- **Resposta (`200 OK`):**
```json
{
  "items": [
    {
      "id": "e8d47b6a-12c3-498b-b892-471629abc123",
      "cycle_index": 1,
      "invoice_count": 10,
      "status": "completed",
      "created_at": "2026-08-14T03:00:00.123456Z"
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
Retorna uma lista paginada de faturas individuais com suporte a filtro por status.

- **Query Parameters:**
  - `status` *(opcional, string)*: Filtrar por status (ex: `created`, `credited`).
  - `page` *(opcional, int, padrão: 1)*: Página atual.
  - `size` *(opcional, int, padrão: 20)*: Quantidade por página.

---

## 📬 Módulo de Webhook

### `POST /api/v1/webhooks/starkbank`
Endpoint receptor dos eventos da Stark Bank. Valida a assinatura digital ECDSA e despacha transferências de liquidação para faturas creditadas.

- **Headers Obrigatórios:**
  - `Digital-Signature`: Assinatura criptográfica enviada pelo Stark Bank.
- **Resposta Sucesso (`200 OK`):**
```json
{
  "status": "success",
  "message": "Webhook processed successfully.",
  "event_id": "5738291048592018",
  "transfer_id": "4728193847291048"
}
```
- **Resposta Assinatura Inválida (`400 Bad Request`):**
```json
{
  "error": "invalid_signature",
  "code": "invalid_signature",
  "detail": "Digital signature validation failed."
}
```

---

## 💸 Módulo de Transfers (Transferências)

### `GET /api/v1/transfers`
Retorna uma lista paginada de todas as transferências de liquidação realizadas após o recebimento de webhooks.

- **Query Parameters:**
  - `page` *(opcional, int, padrão: 1)*: Página atual.
  - `size` *(opcional, int, padrão: 20)*: Quantidade por página.
- **Resposta (`200 OK`):**
```json
{
  "items": [
    {
      "id": "9f8e7d6c-5b4a-3928-1726-354433221100",
      "stark_transfer_id": "4728193847291048",
      "stark_invoice_id": "5839201948572019",
      "event_id": "5738291048592018",
      "amount": 15000,
      "fee": 50,
      "net_amount": 14950,
      "status": "success",
      "created_at": "2026-08-14T03:15:22.000000Z"
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

## ⏰ Módulo de Scheduler (Agendador)

### `GET /api/v1/scheduler/status`
Retorna o estado do agendador, quantidade de ciclos concluídos e horário da próxima execução.

- **Resposta (`200 OK`):**
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
Dispara um ciclo manual sob demanda. O lote é gravado como `trigger_type: "manual"` e não consome a cota agendada de 24 horas.

- **Resposta (`200 OK`):**
```json
{
  "status": "success",
  "message": "Manual cycle triggered successfully."
}
```

---

### `PUT /api/v1/scheduler/mode`
Altera o modo de operação do agendador em runtime.

- **Payload:**
```json
{
  "mode": "recurring"
}
```
- **Resposta (`200 OK`):**
```json
{
  "status": "success",
  "message": "Scheduler mode updated to recurring.",
  "mode": "recurring"
}
```

---

### `POST /api/v1/scheduler/reset`
Limpa o histórico de ciclos armazenados no banco, reiniciando os contadores de 24 horas.

- **Resposta (`200 OK`):**
```json
{
  "status": "success",
  "message": "Scheduler cycle history reset successfully."
}
```

---

## 🩺 Health Check

### `GET /health`
Verificação de integridade (*liveness / readiness probe*) usada pelo Docker e proxies.

- **Resposta (`200 OK`):**
```json
{
  "status": "ok",
  "service": "webhook-payment"
}
```
