#!/bin/sh
set -e

# EMBEDDED_REDIS=true runs Redis inside this container (free tiers: no Upstash command quota).
export EMBEDDED_REDIS="${EMBEDDED_REDIS:-false}"
if [ "$EMBEDDED_REDIS" = "true" ]; then
  export REDIS_URL="redis://127.0.0.1:6379"
  # Start Redis first so the migration step and the API find it immediately.
  redis-server --save "" --appendonly no --maxmemory 256mb --maxmemory-policy noeviction --daemonize yes
fi

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "running database migrations"
  alembic upgrade head
fi

exec supervisord -c supervisord.conf
