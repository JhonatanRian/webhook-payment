# ==============================================================================
# Stage 1: Build Dependencies using Astral uv
# ==============================================================================
FROM ghcr.io/astral-sh/uv:python3.12-alpine AS builder

WORKDIR /app

# Enable bytecode compilation and copy link mode for optimal container performance
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install dependencies before copying source code to leverage Docker layer caching
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Copy source code, README, and migrations to install the application package
COPY app ./app
COPY README.md ./README.md
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ==============================================================================
# Stage 2: Production Minimal Alpine Runtime
# ==============================================================================
FROM python:3.12-alpine AS runtime

WORKDIR /app

# Install production system utilities (Nginx, Supervisor, gettext for envsubst, curl for healthcheck)
RUN apk add --no-cache \
    nginx \
    supervisor \
    gettext \
    curl \
    tzdata \
    && mkdir -p /run/nginx /etc/supervisor /var/log/supervisor /tmp

# Environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    WEB_CONCURRENCY=2

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application and migration files
COPY app ./app
COPY README.md ./README.md
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

# Copy container configurations
COPY docker/nginx.conf.template /etc/nginx/nginx.conf.template
COPY docker/supervisord.conf /etc/supervisor/supervisord.conf
COPY docker/entrypoint.sh /app/docker/entrypoint.sh

# Make entrypoint executable
RUN chmod +x /app/docker/entrypoint.sh

# Default container port
EXPOSE 8080

# Health check against Nginx ingress
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

ENTRYPOINT ["/app/docker/entrypoint.sh"]
