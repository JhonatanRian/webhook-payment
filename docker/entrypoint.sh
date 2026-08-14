#!/bin/sh
set -e

# Default port for GCP Cloud Run and container environments
export PORT="${PORT:-8080}"
export WEB_CONCURRENCY="${WEB_CONCURRENCY:-2}"
umask 000

echo "[entrypoint] Configuring Nginx for PORT=${PORT} and Uvicorn for WORKERS=${WEB_CONCURRENCY}..."
envsubst '${PORT}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Clean up stale socket file if container restarted
rm -f /tmp/app.sock

# Apply database migrations
echo "[entrypoint] Running database migrations (alembic upgrade head)..."
/app/.venv/bin/alembic upgrade head

# Start Supervisor (orchestrates Uvicorn + Nginx)
echo "[entrypoint] Starting Supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
