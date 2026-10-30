#!/bin/sh
# =========================================================================
# Nexus Social — Production Docker Container Entrypoint
# =========================================================================
# Supports:
#   - Default: Runs database migrations (alembic upgrade head) & starts Uvicorn
#   - migrate: Runs migrations only
#   - seed: Runs database seed script (e.g. ./scripts/entrypoint.sh seed --demo)
#   - Custom command: Passes arguments directly to exec
# =========================================================================

set -e

PORT="${PORT:-8000}"

if [ "$1" = "migrate" ]; then
    echo "[Entrypoint] Running database migrations..."
    exec alembic upgrade head
elif [ "$1" = "seed" ]; then
    shift
    echo "[Entrypoint] Running database seed script..."
    exec python scripts/seed.py "$@"
elif [ -n "$1" ]; then
    echo "[Entrypoint] Executing custom command: $@"
    exec "$@"
else
    echo "[Entrypoint] Applying latest database migrations..."
    alembic upgrade head

    echo "[Entrypoint] Starting Nexus Social API on 0.0.0.0:${PORT}..."
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
fi
