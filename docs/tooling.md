# 🛠️ Ferramental, Linters & Configurações

O projeto segue os padrões mais modernos de engenharia de software no ecossistema Python, unificando dependências, linters, testes e hooks em um único arquivo de configuração padronizado ([`pyproject.toml`](file:///home/jhonatan/projects/webhook-payment/pyproject.toml)).

---

## ⚡ Gerenciamento de Dependências com Astral `uv`

O projeto utiliza o **Astral `uv`**, um gerenciador de pacotes ultra-rápido escrito em Rust:

- **Instalação Determinística:** O arquivo `uv.lock` garante que as exatas mesmas versões sejam instaladas em desenvolvimento, testes e no container Docker.
- **Ambiente Isolado Automático:** O comando `uv run` executa ferramentas (`pytest`, `ruff`, `alembic`) diretamente dentro do virtualenv sem necessidade de ativação manual (`source .venv/bin/activate`).

### Comandos Úteis do `uv`:
```bash
# Sincronizar todas as dependências de desenvolvimento
uv sync --dev

# Adicionar uma nova biblioteca de produção
uv add nome-do-pacote

# Adicionar uma biblioteca de desenvolvimento
uv add --dev nome-do-pacote
```

---

## 🧹 Linter & Formatador de Código (Ruff)

Substituímos múltiplas ferramentas legadas (como Flake8, Black e isort) pelo **Ruff**, que é centenas de vezes mais rápido e garante conformidade com as PEPs mais recentes.

### Configuração no `pyproject.toml`:
```toml
[tool.ruff]
target-version = "py312"
line-length = 100
exclude = [".venv", "alembic/versions"]

[tool.ruff.lint]
select = [
    "E",   # Erros de sintaxe e estilo PEP 8
    "W",   # Avisos PEP 8
    "F",   # Checagens do Pyflakes (variáveis não usadas, imports soltos)
    "I",   # Organização e ordenação automática de imports (isort)
    "C90", # Complexidade ciclomática de funções
    "UP",  # Modernização de sintaxe para Python 3.12+ (pyupgrade)
]
```

### Comandos do Ruff:
```bash
# Checar conformidade de linter e ordenação de imports
uv run ruff check .

# Corrigir automaticamente problemas de linter
uv run ruff check --fix .

# Formatar todo o código do projeto (substituto do Black)
uv run ruff format .

# Validar se o código está formatado (usado no CI)
uv run ruff format --check .
```

---

## 🛡️ Git Hook de `pre-push` Automatizado

Para evitar que códigos fora do padrão ou testes quebrados sejam enviados para o GitHub, o repositório conta com um hook nativo em [`.githooks/pre-push`](file:///home/jhonatan/projects/webhook-payment/.githooks/pre-push):

```bash
#!/bin/sh
set -e

echo "🔍 [git-hook] Running Ruff format check and linter via uv..."

uv run ruff format --check .
uv run ruff check .
uv run pytest --maxfail=1 -q

echo "✅ [git-hook] Code quality and test checks passed!"
```

### Como Ativar Localmente:
```bash
git config core.hooksPath .githooks
```
A partir desse momento, qualquer `git push` executará a validação completa antes de enviar as alterações para o repositório remoto.
