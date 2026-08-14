# ⚡ Stark Bank Webhook & Payment Integration

[![CI/CD Pipeline](https://github.com/JhonatanRian/webhook-payment/actions/workflows/deploy.yml/badge.svg)](https://github.com/JhonatanRian/webhook-payment/actions/workflows/deploy.yml)
[![codecov](https://codecov.io/gh/JhonatanRian/webhook-payment/branch/master/graph/badge.svg)](https://codecov.io/gh/JhonatanRian/webhook-payment)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Bem-vindo à documentação oficial do **Webhook Payment Integration with Stark Bank**. 

Este sistema foi projetado para operar como um **Monólito Modular assíncrono e resiliente**, realizando a emissão automatizada de faturas Pix no ambiente Sandbox da **Stark Bank**, escutando eventos de crédito assinados digitalmente via Webhook e transferindo automaticamente o valor líquido creditado para a conta destino da instituição.

---

## 🎯 Visão Geral do Sistema

O objetivo principal deste projeto é atender aos requisitos do desafio técnico da Stark Bank com qualidade de software de nível de produção (*production-ready*), arquitetura limpa, testes abrangentes e entrega contínua automatizada.

```mermaid
flowchart LR
    SCHEDULER["⏰ APScheduler Engine"] -->|Dispara a cada 3h| INVOICE["🧾 Módulo Invoice"]
    INVOICE -->|Cria 8 a 12 Faturas Pix| STARK_API["🏦 Stark Bank Sandbox API"]
    
    STARK_API -->|Webhook com Assinatura ECDSA| WEBHOOK["📬 Módulo Webhook"]
    WEBHOOK -->|Valida Assinatura & Idempotência| TRANSFER["💸 Módulo Transfer"]
    TRANSFER -->|Transfere Valor Líquido (Amount - Fee)| STARK_API
```

---

## 🛠️ Stack Tecnológica

| Componente | Tecnologia | Finalidade |
| :--- | :--- | :--- |
| **Linguagem & Runtime** | **Python 3.12** | Tipagem estática moderna (`PEP 695`), performance e sintaxe assíncrona. |
| **Framework Web** | **FastAPI 0.110+** | Framework web moderno, OpenAPI/Swagger automático e validação estrita com Pydantic v2. |
| **Gerenciador de Pacotes** | **Astral `uv`** | Gerenciador de dependências ultra-rápido em Rust, compilação de bytecode e locks determinísticos. |
| **Servidor ASGI & Proxy** | **Uvicorn + Nginx** | Uvicorn nativo com `uvloop` comunicando via Unix Domain Socket (`/tmp/app.sock`) com Nginx reverse proxy. |
| **Banco de Dados & ORM** | **SQLite + SQLAlchemy 2.0 (Async)** | Persistência assíncrona com `aiosqlite`, repositórios genéricos e isolamento transacional. |
| **Migrações de Esquema** | **Alembic** | Versionamento e evolução de schema com execução automática no boot do container. |
| **Agendador em Background** | **APScheduler 3.10+** | Motor assíncrono para controle de ciclos de 24 horas, intervalos dinâmicos e modos configuráveis. |
| **Qualidade & Linters** | **Ruff & Pytest** | Linter e formatador de alto desempenho (Ruff) e suíte de testes com cobertura mínima de 90% (alcançando 100%). |
| **Container & Entrega** | **Docker Alpine + GHCR + Portainer** | Imagem minimalista de 70 MB no GitHub Packages e deploy contínuo automático via Webhook no Portainer. |

---

## 🚀 Como Navegar na Documentação

Explore os tópicos detalhados no menu superior:

1. **[Arquitetura & Design](architecture.md)** — Estrutura em Monólito Modular, separação de camadas e banco de dados.
2. **[Regras de Negócio & Ciclos](business-rules.md)** — Funcionamento dos ciclos de 24h, modos `once` vs `recurring`, liquidação Pix e verificação ECDSA.
3. **[Catálogo de Endpoints](api-reference.md)** — Documentação de rotas, contratos de entrada/saída e códigos HTTP.
4. **[Deploy & Infraestrutura](deployment.md)** — Pipeline de CI/CD no GitHub Actions, GHCR, Portainer e proxy Traefik com SSL automático.
5. **[Estratégia de Testes](testing.md)** — Estrutura de 91 testes, testes adversariais de concorrência, idempotência e cobertura de 100%.
6. **[Ferramental & Configurações](tooling.md)** — Guia do `pyproject.toml`, Astral `uv`, formatação Ruff e Git pre-push hooks.
