#!/bin/bash

echo "=========================================="
echo "AutonomOS Production Startup"
echo "=========================================="
echo "Time: $(date -u)"
echo "PORT: ${PORT:-5000}"

# Check critical env vars
if [ -z "$DATABASE_URL" ]; then
  echo "FATAL: DATABASE_URL is not set"
  exit 1
fi

echo "DATABASE_URL: [set]"
echo "REDIS_URL: ${REDIS_URL:+[set]}${REDIS_URL:-[not set]}"
echo "SECRET_KEY: ${SECRET_KEY:+[set]}${SECRET_KEY:-[auto-generated]}"

# Run database migrations with timeout (skip if too slow)
if [ "${DISABLE_AUTO_MIGRATIONS:-false}" = "true" ]; then
  echo "Auto-migrations disabled by DISABLE_AUTO_MIGRATIONS flag"
else
  echo "Running database migrations (30s timeout)..."
  timeout 30 alembic upgrade head 2>&1
  MIGRATION_EXIT=$?
  if [ $MIGRATION_EXIT -eq 0 ]; then
    echo "Database migrations completed successfully"
  elif [ $MIGRATION_EXIT -eq 124 ]; then
    echo "WARNING: Database migrations timed out after 30s - continuing without migrations"
  else
    echo "WARNING: Database migrations failed (exit $MIGRATION_EXIT) - continuing anyway"
  fi
fi

# Start RQ worker in background (non-blocking, optional)
echo "Starting RQ worker (background)..."
python -m app.worker > /dev/null 2>&1 &
WORKER_PID=$!
echo "RQ worker launched (PID: $WORKER_PID)"

# Cleanup on exit
trap "kill $WORKER_PID 2>/dev/null; exit" SIGINT SIGTERM

# Set production env vars
export FEATURE_USE_FILESOURCE=true
export REQUIRED_SOURCES=salesforce,supabase,mongodb,filesource
export DCL_AUTH_ENABLED=false

# Start FastAPI - single worker for PgBouncer compatibility
echo "Starting FastAPI on port ${PORT:-5000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-5000} --proxy-headers --log-level info --workers 1
