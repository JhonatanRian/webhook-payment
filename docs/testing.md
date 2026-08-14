# 🧪 Estratégia de Testes & Qualidade

Para garantir a confiabilidade de um sistema financeiro, construímos uma suíte de testes focada não apenas no caminho feliz (*happy path*), mas especialmente em **idempotência**, **falhas de rede** e **concorrência adversarial**.

---

## 📊 Visão Geral dos Testes

- **Total de Testes**: **103 testes automatizados**.
- **Tempo de Execução**: ~10 segundos.
- **Cobertura de Código**: **100%** (com trava mínima de 90% configurada no `pyproject.toml`).
- **Relatórios**: Integração com Codecov gerando `coverage.xml` e `junit.xml`.

---

## 🗂️ Como os Testes Estão Divididos

Os testes na pasta [`tests/`](../tests) são organizados em duas frentes:

```text
tests/
├── conftest.py                             # Fixtures assíncronas de banco em memória e mocks do Stark Bank
├── integration/                            # Testes de Integração Ponta a Ponta
│   ├── test_adversarial_concurrency.py    # Disparo simultâneo de múltiplos webhooks / faturas
│   ├── test_invoice_flow.py               # Fluxo completo de emissão e persistência de lotes
│   ├── test_scheduler_flow.py             # Máquina de estados do agendador e modos de execução
│   └── test_webhook_flow.py               # Ciclo: Webhook -> Assinatura ECDSA -> Transferência
└── unit/                                   # Testes Unitários Isolados
    ├── modules/
    │   ├── test_invoice_service.py        # Geração aleatória de dados com Faker e lotes
    │   ├── test_scheduler_service.py      # Lógica de contagem de ciclos e limites em 24h
    │   ├── test_transfer_service.py       # Cálculo de valor líquido e bloqueio de saldos <= 0
    │   └── test_webhook_service.py        # Validação de assinaturas e eventos duplicados
    ├── test_base_repository.py            # Operações CRUD genéricas e paginação
    ├── test_concurrency.py                # Wrapper async com threadpool
    ├── test_config.py                     # Leitura e sanitização de variáveis de ambiente
    ├── test_db_session.py                 # Sessões e conexões do SQLite
    ├── test_exceptions.py                 # Hierarquia de exceções de domínio
    ├── test_starkbank_exceptions.py       # Mapeamento de erros do SDK externo
    ├── test_logging.py                    # Formatação de logs estruturados
    └── test_middleware.py                 # Rastreamento de Request-ID e logs HTTP
```

---

## 🥊 Testes Adversariais & Casos Extremos

Alguns dos cenários críticos que cobrimos:

1. **Concorrência Massiva (`test_adversarial_concurrency.py`)**:
   Simulamos 10 a 20 requisições disparadas no mesmo milissegundo tentando processar o mesmo webhook ou disparar ciclos, garantindo que o banco de dados e os locks assíncronos não sofram deadlocks nem dupliquem transferências.
2. **Idempotência de Webhook**:
   Se a Stark Bank reenviar o mesmo `event_id` por retry de rede, a aplicação reconhece a duplicidade, responde `200 OK` e **não repete a transferência**.
3. **Falhas de Rede & Erros da Stark Bank**:
   Simulamos timeouts e respostas de erro da API externa para garantir que a aplicação trate as exceções de forma limpa, sem expor tracebacks sensíveis.
4. **Tarifas Maiores que o Valor da Fatura**:
   Garantimos que se uma fatura tiver taxa bancária superior ao valor bruto, o sistema rejeite a operação e não tente transferir valores negativos.

---

## 🚀 Como Rodar os Testes Localmente

```bash
# Executar toda a suíte de testes
uv run pytest -v

# Executar com relatório de cobertura no terminal
uv run pytest -v --cov=app --cov-report=term-missing

# Gerar relatório visual em HTML (abre na pasta htmlcov/index.html)
uv run pytest -v --cov=app --cov-report=html
```
