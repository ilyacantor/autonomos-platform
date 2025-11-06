#!/bin/bash

echo "Starting AutonomOS Platform..."

# Only start local Redis if REDIS_URL is not set (development mode)
if [ -z "$REDIS_URL" ]; then
  echo "Starting local Redis server (development mode)..."
  redis-server --port 6379 --daemonize yes
  sleep 2
else
  echo "Using external Redis from REDIS_URL (production mode)..."
fi

# Auto-stamp production on first deploy if needed
echo "Checking if database needs baseline stamping..."
if ! alembic current 2>/dev/null | grep -q "head"; then
  echo "🏷️  First deployment detected - stamping database baseline..."
  alembic stamp head
  if [ $? -eq 0 ]; then
    echo "✅ Database stamped successfully"
  else
    echo "⚠️ Database stamp failed - will try migrations anyway"
  fi
else
  echo "✅ Database already at baseline"
fi

# Run database migrations
echo "Running database migrations..."
alembic upgrade head
if [ $? -eq 0 ]; then
  echo "✅ Database migrations completed successfully"
else
  echo "⚠️ Database migrations failed - continuing anyway"
fi

echo "Starting RQ worker..."
python -m app.worker &
WORKER_PID=$!

sleep 1

# Check if worker is still running
if kill -0 $WORKER_PID 2>/dev/null; then
  echo "✅ RQ worker started successfully (PID: $WORKER_PID)"
else
  echo "⚠️ RQ worker failed to start (harmless - background tasks won't run)"
  WORKER_PID=""
fi

# Trap will kill worker if it started successfully, otherwise just shutdown redis
trap "if [ -n \"$WORKER_PID\" ] && kill -0 $WORKER_PID 2>/dev/null; then kill $WORKER_PID; fi; redis-cli shutdown 2>/dev/null; exit" SIGINT SIGTERM

echo "Starting FastAPI server..."
export DEV_DEBUG=true
export FEATURE_USE_FILESOURCE=true
export REQUIRED_SOURCES=salesforce,supabase,mongodb,filesource
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-5000} --proxy-headers
