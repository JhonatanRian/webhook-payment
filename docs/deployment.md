# 🚢 Deploy, Infraestrutura & CI/CD

A infraestrutura e o processo de deploy contínuo foram desenhados para aliar **máxima leveza**, **segurança**, **zero-downtime** e **automação total**.

---

## 🏗️ Arquitetura do Container Docker

A imagem Docker é baseada em um **Multi-Stage Build** de dois estágios:

```mermaid
flowchart TD
    subgraph Builder ["Estágio 1: Builder (ghcr.io/astral-sh/uv:python3.12-alpine)"]
        SYNC["uv sync --frozen --no-dev\nCompilação de Bytecode (UV_COMPILE_BYTECODE=1)"]
    end

    subgraph Runtime ["Estágio 2: Runtime (python:3.12-alpine)"]
        PKGS["Instala Nginx, Supervisor, tzdata, gettext"]
        COPY["Copia /app/.venv pré-compilado (Zero compiladores no runtime)"]
        ENTRY["docker/entrypoint.sh\n- Executa alembic upgrade head\n- Inicia Supervisord (PID 1)"]
    end

    Builder -->|Apenas .venv compilado| Runtime
```

### Destaques da Imagem:
- **Tamanho Total Comprimido:** Apenas **~70.5 MB**.
- **Segurança Máxima:** Não contém compiladores (`gcc`, `musl-dev`) no runtime final.
- **Performance:** Bytecode Python pré-compilado acelera o tempo de inicialização (*cold start*).
- **Socket Unix de Alta Velocidade:** Nginx comunica diretamente com o Uvicorn via socket Unix local (`unix:/tmp/app.sock`), eliminando overhead de rede TCP interna.

---

## 🤖 Pipeline de CI/CD (GitHub Actions)

A pipeline em [`.github/workflows/deploy.yml`](file:///home/jhonatan/projects/webhook-payment/.github/workflows/deploy.yml) é acionada a cada commit ou merge na branch `master`:

```mermaid
flowchart LR
    PUSH["Git Push to 'master'"] --> TEST["1. Quality Gate\n- Ruff Format & Lint\n- Pytest (103 Testes)\n- Codecov Upload"]
    TEST --> BUILD["2. Build & Push GHCR\n- Docker Buildx + GHA Cache\n- ghcr.io/jhonatanrian/webhook-payment"]
    BUILD --> PORTAINER["3. Portainer Webhook\n- POST https://portainer.../api/webhooks/...\n- VPS atualiza container em 3s"]
```

---

## 🌐 Deploy em VPS com Portainer & Traefik v3

A aplicação roda em uma VPS própria integrada com o **Portainer** e o proxy reverso **Traefik v3**:

```yaml
version: "3.8"

services:
  app:
    image: ghcr.io/jhonatanrian/webhook-payment:latest
    restart: always
    environment:
      - ENVIRONMENT=sandbox
      - DATABASE_URL=sqlite+aiosqlite:////data/webhook_payment.db
      - STARK_PROJECT_ID=${STARK_PROJECT_ID}
      - STARK_PRIVATE_KEY=${STARK_PRIVATE_KEY}
      - SCHEDULER_MODE=once
      - SCHEDULER_INTERVAL_MINUTES=180
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

### Vantagens Desta Configuração:
1. **IP Fixo Estático Garantido:** A VPS possui um IP público fixo cadastrado com perfil de Admin no Stark Bank, permitindo emissões e transferências sem bloqueios de IP.
2. **Persistência do SQLite:** O volume Docker nomeado (`webhook_payment_data`) persiste os dados no disco da VPS independentemente de reinicializações ou updates de versão.
3. **SSL Automático com Let's Encrypt:** O Traefik emite e renova os certificados HTTPS automaticamente sem intervenção manual.
4. **Deploy sem Downtime:** O webhook do Portainer recria o container preservando o volume de dados em poucos segundos.
