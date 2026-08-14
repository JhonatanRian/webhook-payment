# 🧪 Estratégia de Testes & Qualidade de Software

A suíte de testes foi construída com foco em **confiabilidade financeira**, **idempotência** e **resiliência a falhas**, alcançando mais de **98% de cobertura** real de código.

---

## 📊 Métricas da Suíte de Testes

- **Total de Testes:** **91 testes automatizados**.
- **Tempo de Execução:** ~8.4 segundos.
- **Cobertura de Código (Coverage):** **100.00%** *(com barreira mínima de 90% configurada no `pyproject.toml`)*.
- **Integração com Codecov:** Relatórios detalhados de cobertura (`coverage.xml`) e resultados de execução JUnit (`junit.xml`).

---

## 🗂️ Estrutura e Divisão dos Testes

Os testes em [`tests/`](file:///home/jhonatan/projects/webhook-payment/tests) são divididos em camadas lógicas:

```text
tests/
├── conftest.py                             # Fixtures assíncronas do banco em memória e mocks
├── integration/                            # Testes de Integração Ponta a Ponta
│   ├── test_adversarial_concurrency.py    # Testes de concorrência massiva e race conditions
│   ├── test_invoice_flow.py               # Fluxo completo de emissão de faturas
│   ├── test_scheduler_flow.py             # Ciclos de agendamento e modos de operação
│   └── test_webhook_flow.py               # Fluxo de webhook -> validação -> transferência
└── unit/                                   # Testes Unitários de Domínio e Core
    ├── modules/
    │   ├── test_invoice_service.py        # Geração aleatória e lotes de faturas
    │   ├── test_scheduler_service.py      # Agendador, modos 'once'/'recurring' e falhas
    │   ├── test_transfer_service.py       # Cálculo de valor líquido e regras de saldo
    │   ├── test_webhook_service.py        # Assinatura ECDSA, eventos ignorados e duplicidades
    │   └── test_adversarial_invoice_transfer.py # Casos extremos de liquidação
    ├── test_base_repository.py            # Operações CRUD assíncronas genéricas
    ├── test_concurrency.py                # Wrapper async to_thread
    ├── test_config.py                     # Sanitização de settings e parsing de chaves
    ├── test_db_session.py                 # Inicialização do banco e generators de sessão
    ├── test_exceptions.py                 # Hierarquia de exceções de domínio
    ├── test_starkbank_exceptions.py       # Mapeamento de erros do SDK da Stark Bank
    ├── test_logging.py                    # Formatação de logs em JSON e texto
    └── test_middleware.py                 # Rastreamento de Correlation ID e logs HTTP
```

---

## 🥊 Testes Adversariais & Casos Extremos

Além dos cenários de sucesso (*happy path*), a suíte testa exaustivamente condições adversas:

### 1. Concorrência e Race Conditions (`test_adversarial_concurrency.py`)
Simula 10 a 20 requisições disparadas no exato mesmo milissegundo tentando emitir lotes ou disparar ciclos, garantindo que o banco de dados e as sessões assíncronas não sofram *deadlocks* ou inconsistências.

### 2. Idempotência de Webhook
Garante que se o Stark Bank reenviar o mesmo `event_id` múltiplas vezes (devido a retentativas de rede), a aplicação reconhece a duplicidade, retorna `200 OK` e **não duplica a transferência de dinheiro**.

### 3. Falhas de Rede e Timeouts do SDK
Simula exceções de timeout e indisponibilidade do Stark Bank SDK (`starkcore.error.InputErrors`, `InternalServerError`), validando que a API mapeia o erro para o formato JSON correto e nunca expõe tracebacks internos.

### 4. Valores Líquidos Não-Positivos
Valida que se uma fatura com taxa (`fee`) igual ou superior ao valor bruto for recebida, o sistema bloqueia a transferência de valor zero ou negativo.

---

## 🚀 Como Rodar os Testes Localmente

```bash
# Executar toda a suíte com relatório de cobertura no terminal
uv run pytest -v

# Executar com relatório HTML detalhado (abre em htmlcov/index.html)
uv run pytest -v --cov=app --cov-report=html
```
