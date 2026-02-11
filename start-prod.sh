#!/bin/bash

echo "Starting AutonomOS Platform (Production)..."

# Production uses external Redis
if [ -n "$REDIS_URL" ]; then
  echo "Using external Redis from REDIS_URL..."
else
  echo "WARNING: No REDIS_URL set in production"
fi

# Run database migrations (unless disabled)
if [ "${DISABLE_AUTO_MIGRATIONS:-false}" = "true" ]; then
  echo "Auto-migrations disabled by DISABLE_AUTO_MIGRATIONS flag"
else
  echo "Running database migrations..."
  alembic upgrade head
  if [ $? -eq 0 ]; then
    echo "Database migrations completed successfully"
  else
    echo "Database migrations failed - continuing anyway"
  fi
fi

echo "Starting RQ worker..."
python -m app.worker &
WORKER_PID=$!

sleep 1

if kill -0 $WORKER_PID 2>/dev/null; then
  echo "RQ worker started (PID: $WORKER_PID)"
else
  echo "RQ worker failed to start - background tasks won't run"
  WORKER_PID=""
fi

trap "if [ -n \"$WORKER_PID\" ] && kill -0 $WORKER_PID 2>/dev/null; then kill $WORKER_PID; fi; exit" SIGINT SIGTERM

echo "Starting FastAPI server (production)..."
export FEATURE_USE_FILESOURCE=true
export REQUIRED_SOURCES=salesforce,supabase,mongodb,filesource
export DCL_AUTH_ENABLED=false
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-5000} --proxy-headers --log-level info --workers 2
