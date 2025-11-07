#!/bin/bash
#
# Baseline Stamp Script
# One-time initialization to mark database as being at baseline migration
# IDEMPOTENT: Safe to run multiple times, no-ops if already stamped
# Uses DATABASE_URL (works in both dev and production contexts)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🏷️  AutonomOS Baseline Stamp"
echo "============================"
echo ""

# Define baseline revision (earliest migration)
BASELINE_REV="5a9d6371e18c"

echo "Baseline revision: $BASELINE_REV"
echo ""

# Get database URL
DB_URL="${DATABASE_URL:-}"

if [ -z "$DB_URL" ]; then
  echo "❌ ERROR: DATABASE_URL not set"
  echo ""
  echo "Set the database URL:"
  echo "  export DATABASE_URL='postgresql://user:pass@host/db'"
  echo ""
  exit 1
fi

echo "Target: DATABASE_URL"
echo ""

# Check if alembic_version table exists
echo "🔍 Checking alembic_version table status..."
version_check=$(python3 "$SCRIPT_DIR/_psql.py" "$DB_URL" "SELECT version_num FROM alembic_version LIMIT 1;" 2>&1 || echo "TABLE_MISSING")

if echo "$version_check" | grep -q "ERROR\|TABLE_MISSING\|does not exist"; then
  echo "   → alembic_version table not found"
  echo ""
  echo "📝 Creating alembic_version table and stamping with baseline..."
  
  cd "$PROJECT_ROOT"
  alembic stamp "$BASELINE_REV"
  
  if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Database stamped successfully!"
    echo "   Version: $BASELINE_REV"
  else
    echo ""
    echo "❌ Failed to stamp database"
    exit 1
  fi
else
  # Extract current version
  current_version=$(echo "$version_check" | tail -1 | tr -d '[:space:]')
  
  echo "   → alembic_version exists with value: $current_version"
  echo ""
  
  if [ "$current_version" = "$BASELINE_REV" ]; then
    echo "✅ Database already stamped at baseline ($BASELINE_REV)"
    echo "   No action needed (idempotent no-op)"
  elif [ "$current_version" = "version_num" ]; then
    # Header row only, table exists but is empty
    echo "⚠️  alembic_version table exists but is empty"
    echo ""
    echo "📝 Stamping with baseline..."
    cd "$PROJECT_ROOT"
    alembic stamp "$BASELINE_REV"
    
    if [ $? -eq 0 ]; then
      echo ""
      echo "✅ Database stamped successfully!"
    else
      echo ""
      echo "❌ Failed to stamp database"
      exit 1
    fi
  else
    echo ""
    echo "✅ Database already tracked by Alembic"
    echo ""
    echo "   Current version: $current_version"
    echo "   Baseline version: $BASELINE_REV"
    echo ""
    echo "This database is already being tracked at a different migration."
    echo "This is normal if you've applied migrations after the baseline."
    echo "No stamping needed."
    exit 0
  fi
fi

echo ""
echo "================================"
echo "🧪 Verifying migration status..."
echo "================================"
echo ""

cd "$PROJECT_ROOT"

echo "Current Alembic status:"
alembic current

echo ""
echo "Running: alembic upgrade head"
alembic upgrade head

if [ $? -eq 0 ]; then
  echo ""
  echo "✅ Database migrations up-to-date"
  echo ""
  echo "================================"
  echo "✅ COMPLETE"
  echo "================================"
  echo ""
  echo "Database is now:"
  echo "  • Tracked by Alembic"
  echo "  • All migrations applied"
  echo "  • Ready for incremental schema changes"
else
  echo ""
  echo "⚠️  WARNING: Alembic upgrade encountered issues"
  echo ""
  echo "Review the output above. If it shows destructive operations"
  echo "(DROP TABLE, etc.), DO NOT PROCEED."
  exit 1
fi
