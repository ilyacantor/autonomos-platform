#!/bin/bash
#
# Production Baseline Stamp Script
# One-time initialization to mark production as being at baseline migration
# IDEMPOTENT: Safe to run multiple times, no-ops if already stamped
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🏷️  AutonomOS Production Baseline Stamp"
echo "========================================"
echo ""

# Define baseline revision (earliest migration)
BASELINE_REV="5a9d6371e18c"

echo "Baseline revision: $BASELINE_REV"
echo ""

# Get production database URL
DB_PROD="${DATABASE_URL_PROD:-}"

if [ -z "$DB_PROD" ]; then
  echo "❌ ERROR: DATABASE_URL_PROD not set"
  echo ""
  echo "Set the production database URL:"
  echo "  export DATABASE_URL_PROD='postgresql://user:pass@host/db'"
  echo ""
  exit 1
fi

echo "Target: Production database"
echo ""

# Check if alembic_version table exists
echo "🔍 Checking alembic_version table status..."
version_check=$(python3 "$SCRIPT_DIR/_psql.py" "$DB_PROD" "SELECT version_num FROM alembic_version LIMIT 1;" 2>&1 || echo "TABLE_MISSING")

if echo "$version_check" | grep -q "ERROR\|TABLE_MISSING\|does not exist"; then
  echo "   → alembic_version table not found in production"
  echo ""
  echo "📝 Creating alembic_version table and stamping with baseline..."
  
  # Use alembic stamp with production database URL
  cd "$PROJECT_ROOT"
  export DATABASE_URL="$DB_PROD"
  
  alembic stamp "$BASELINE_REV"
  
  if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Production database stamped successfully!"
    echo "   Version: $BASELINE_REV"
  else
    echo ""
    echo "❌ Failed to stamp production database"
    exit 1
  fi
else
  # Extract current version
  current_version=$(echo "$version_check" | tail -1 | tr -d '[:space:]')
  
  echo "   → alembic_version exists with value: $current_version"
  echo ""
  
  if [ "$current_version" = "$BASELINE_REV" ]; then
    echo "✅ Production already stamped at baseline ($BASELINE_REV)"
    echo "   No action needed (idempotent no-op)"
  elif [ "$current_version" = "version_num" ]; then
    # Header row only, table exists but is empty
    echo "⚠️  alembic_version table exists but is empty"
    echo ""
    echo "📝 Stamping with baseline..."
    cd "$PROJECT_ROOT"
    export DATABASE_URL="$DB_PROD"
    alembic stamp "$BASELINE_REV"
    
    if [ $? -eq 0 ]; then
      echo ""
      echo "✅ Production database stamped successfully!"
    else
      echo ""
      echo "❌ Failed to stamp production database"
      exit 1
    fi
  else
    echo ""
    echo "❌ ERROR: Production has unexpected Alembic version"
    echo ""
    echo "   Expected: $BASELINE_REV (baseline)"
    echo "   Found:    $current_version"
    echo ""
    echo "This indicates production is already being tracked by Alembic,"
    echo "but at a different migration than the baseline."
    echo ""
    echo "MANUAL INTERVENTION REQUIRED:"
    echo "  1. Review alembic history: alembic history"
    echo "  2. Check production migration status manually"
    echo "  3. Do NOT force-stamp without understanding the state"
    echo ""
    exit 1
  fi
fi

echo ""
echo "================================"
echo "🧪 Verifying migration status..."
echo "================================"
echo ""

# Test alembic upgrade head in dry-run mode first (check for pending migrations)
cd "$PROJECT_ROOT"
export DATABASE_URL="$DB_PROD"

echo "Current Alembic status:"
alembic current

echo ""
echo "Running: alembic upgrade head"
alembic upgrade head

if [ $? -eq 0 ]; then
  echo ""
  echo "✅ Production migrations up-to-date"
  echo ""
  echo "================================"
  echo "✅ COMPLETE"
  echo "================================"
  echo ""
  echo "Production database is now:"
  echo "  • Tracked by Alembic at baseline $BASELINE_REV"
  echo "  • All migrations applied (up-to-date)"
  echo "  • Ready for incremental schema changes"
  echo ""
  echo "Future deployments will only apply NEW migrations."
else
  echo ""
  echo "⚠️  WARNING: Alembic upgrade encountered issues"
  echo ""
  echo "Review the output above. If it shows destructive operations"
  echo "(DROP TABLE, etc.), DO NOT PROCEED with publishing."
  echo ""
  echo "Investigate migration discrepancies before continuing."
  exit 1
fi
