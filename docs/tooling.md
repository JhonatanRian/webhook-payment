# 🛠️ Ferramental, Linters & Configurações

Aqui detalhamos as ferramentas e práticas adotadas no desenvolvimento do projeto para manter o código padronizado e limpo.

---

## ⚡ Gerenciamento de Dependências com Astral `uv`

Optamos pelo **Astral `uv`**, um gerenciador de pacotes ultra-rápido escrito em Rust:

- **Instalação Determinística**: O arquivo `uv.lock` garante que todo mundo (desenvolvedores, CI e container Docker) utilize exatamente as mesmas versões das bibliotecas.
- **Execução Direta**: O comando `uv run` executa ferramentas (`pytest`, `ruff`, `alembic`) no ambiente virtual automaticamente, sem você precisar ativar a virtualenv na mão (`source .venv/bin/activate`).

### Comandos do Dia a Dia:
```bash
# Sincronizar o ambiente com todas as dependências
uv sync --dev

# Adicionar uma nova biblioteca
uv add nome-do-pacote

# Adicionar uma dependência apenas para desenvolvimento
uv add --dev nome-do-pacote
```

---

## 🧹 Linter & Formatador de Código (Ruff)

Usamos o **Ruff** para substituir ferramentas tradicionais como Flake8, Black e isort em um único utilitário rápido:

### Configuração no `pyproject.toml`:
```toml
[tool.ruff]
target-version = "py312"
line-length = 100
exclude = [".venv", "alembic/versions"]

[tool.ruff.lint]
select = [
    "E",   # Erros de estilo PEP 8
    "W",   # Avisos PEP 8
    "F",   # Checagens do Pyflakes (variáveis não usadas, imports)
    "I",   # Ordenação automática de imports (isort)
    "C90", # Complexidade ciclomática
    "UP",  # Modernização de sintaxe para Python 3.12+ (pyupgrade)
]
```

### Comandos Úteis do Ruff:
```bash
# Verificar problemas de código e ordenação de imports
uv run ruff check .

# Corrigir problemas automaticamente
uv run ruff check --fix .

# Formatar todos os arquivos do projeto
uv run ruff format .

# Validar se o código está formatado (usado no CI)
uv run ruff format --check .
```

---

## 🛡️ Git Hook de `pre-push`

Para garantir que nenhum commit quebrado ou fora do padrão de código suba para o GitHub, o repositório inclui um hook nativo em [`.githooks/pre-push`](../.githooks/pre-push):

```bash
#!/bin/sh
set -e

echo "🔍 [git-hook] Rodando Ruff e Pytest via uv..."

uv run ruff format --check .
uv run ruff check .
uv run pytest --maxfail=1 -q

echo "✅ [git-hook] Tudo certo! Push liberado."
```

### Como Ativar na sua Máquina:
Basta rodar uma vez no terminal:
```bash
git config core.hooksPath .githooks
```
A partir daí, todo `git push` executará a formatação, lint e testes antes de enviar o código.
