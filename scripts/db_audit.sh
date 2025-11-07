#!/bin/bash
#
# Database Audit Script
# Diagnoses both development and production databases
# Outputs: ./ops/db_audit/{dev,prod}-summary.txt
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$PROJECT_ROOT/ops/db_audit"

echo "🔍 AutonomOS Database Audit"
echo "================================"
echo ""

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Get database URLs from environment
DB_DEV="${DATABASE_URL:-}"
DB_PROD="${DATABASE_URL_PROD:-}"

# Fallback: if DATABASE_URL_PROD not set, check if we're in dev mode
if [ -z "$DB_PROD" ]; then
  echo "⚠️  DATABASE_URL_PROD not set. Will only audit development database."
  DB_PROD=""
fi

if [ -z "$DB_DEV" ]; then
  echo "❌ ERROR: DATABASE_URL not set (development database)"
  echo "   Set DATABASE_URL environment variable and try again."
  exit 1
fi

# Function to audit a single database
audit_database() {
  local db_url="$1"
  local env_name="$2"
  local output_file="$OUTPUT_DIR/${env_name}-summary.txt"
  
  echo "📊 Auditing $env_name database..."
  
  # Clear output file
  > "$output_file"
  
  # Header
  echo "AutonomOS Database Audit - $env_name" >> "$output_file"
  echo "Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")" >> "$output_file"
  echo "======================================" >> "$output_file"
  echo "" >> "$output_file"
  
  # Current database
  echo "DATABASE INFO:" >> "$output_file"
  python3 "$SCRIPT_DIR/_psql.py" "$db_url" "SELECT current_database(), current_user;" >> "$output_file" 2>&1 || {
    echo "ERROR: Failed to connect to $env_name database" >> "$output_file"
    echo "❌ Failed to connect to $env_name database"
    return 1
  }
  echo "" >> "$output_file"
  
  # Search path
  echo "SEARCH PATH:" >> "$output_file"
  python3 "$SCRIPT_DIR/_psql.py" "$db_url" "SHOW search_path;" >> "$output_file" 2>&1
  echo "" >> "$output_file"
  
  # Table list
  echo "TABLES IN PUBLIC SCHEMA:" >> "$output_file"
  python3 "$SCRIPT_DIR/_psql.py" "$db_url" "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;" >> "$output_file" 2>&1
  echo "" >> "$output_file"
  
  # Alembic version
  echo "ALEMBIC VERSION:" >> "$output_file"
  python3 "$SCRIPT_DIR/_psql.py" "$db_url" "SELECT version_num FROM alembic_version;" >> "$output_file" 2>&1 || {
    echo "⚠️  alembic_version table not found or empty" >> "$output_file"
  }
  echo "" >> "$output_file"
  
  echo "✅ $env_name audit complete → $output_file"
}

# Audit development database
audit_database "$DB_DEV" "dev"

# Audit production database if URL is provided
if [ -n "$DB_PROD" ]; then
  audit_database "$DB_PROD" "prod"
else
  echo ""
  echo "⚠️  Skipping production audit (DATABASE_URL_PROD not set)"
fi

echo ""
echo "================================"
echo "📋 DIAGNOSIS"
echo "================================"

# Diagnosis logic
if [ -n "$DB_PROD" ]; then
  # Extract table counts
  dev_tables=$(grep -A 999 "TABLES IN PUBLIC SCHEMA:" "$OUTPUT_DIR/dev-summary.txt" | grep -v "TABLES IN PUBLIC SCHEMA:" | grep -v "ALEMBIC VERSION:" | grep -v "^$" | wc -l)
  prod_tables=$(grep -A 999 "TABLES IN PUBLIC SCHEMA:" "$OUTPUT_DIR/prod-summary.txt" | grep -v "TABLES IN PUBLIC SCHEMA:" | grep -v "ALEMBIC VERSION:" | grep -v "^$" | wc -l)
  
  # Check for alembic_version
  dev_has_alembic=$(grep -c "version_num" "$OUTPUT_DIR/dev-summary.txt" || echo "0")
  prod_has_alembic=$(grep -c "version_num" "$OUTPUT_DIR/prod-summary.txt" || echo "0")
  
  # Extract versions if they exist
  dev_version=""
  prod_version=""
  if [ "$dev_has_alembic" -gt 0 ]; then
    dev_version=$(grep -A 1 "version_num" "$OUTPUT_DIR/dev-summary.txt" | tail -1 | tr -d '[:space:]')
  fi
  if [ "$prod_has_alembic" -gt 0 ]; then
    prod_version=$(grep -A 1 "version_num" "$OUTPUT_DIR/prod-summary.txt" | tail -1 | tr -d '[:space:]')
  fi
  
  echo "Dev tables: $dev_tables"
  echo "Prod tables: $prod_tables"
  echo "Dev Alembic version: ${dev_version:-MISSING}"
  echo "Prod Alembic version: ${prod_version:-MISSING}"
  echo ""
  
  # Compute table count difference
  table_diff=$((dev_tables - prod_tables))
  if [ $table_diff -lt 0 ]; then
    table_diff=$((-table_diff))
  fi
  
  # Final diagnosis
  if [ "$prod_has_alembic" -eq 0 ]; then
    echo "❌ MISSING: alembic_version not present on prod"
    echo "   → Run scripts/stamp_prod_baseline.sh to initialize production tracking"
    exit 1
  elif [ "$dev_version" != "$prod_version" ]; then
    echo "⚠️  MISMATCH: Dev/prod at different Alembic versions"
    echo "   Dev: $dev_version | Prod: $prod_version"
    echo "   → Review migration status before publishing"
    exit 1
  elif [ $table_diff -gt 5 ]; then
    echo "⚠️  MISMATCH: Dev/prod schemas differ substantially ($table_diff table difference)"
    echo "   → Investigate schema drift before publishing"
    exit 1
  else
    echo "✅ OK: Both have alembic_version and comparable table counts"
    echo "   Schema distance: $table_diff tables"
    exit 0
  fi
else
  # Only dev database audited
  dev_has_alembic=$(grep -c "version_num" "$OUTPUT_DIR/dev-summary.txt" || echo "0")
  if [ "$dev_has_alembic" -gt 0 ]; then
    dev_version=$(grep -A 1 "version_num" "$OUTPUT_DIR/dev-summary.txt" | tail -1 | tr -d '[:space:]')
    echo "✅ Dev database has Alembic version: $dev_version"
  else
    echo "⚠️  Dev database missing alembic_version table"
  fi
  echo ""
  echo "ℹ️  Production database not audited (DATABASE_URL_PROD not set)"
  exit 0
fi
