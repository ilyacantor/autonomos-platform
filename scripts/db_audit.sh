#!/bin/bash
#
# Database Audit Script
# Diagnoses the current database (uses DATABASE_URL)
# Output: ./ops/db_audit/summary.txt
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

# Get database URL from environment
DB_URL="${DATABASE_URL:-}"

if [ -z "$DB_URL" ]; then
  echo "❌ ERROR: DATABASE_URL not set"
  echo "   Set DATABASE_URL environment variable and try again."
  exit 1
fi

OUTPUT_FILE="$OUTPUT_DIR/summary.txt"

echo "📊 Auditing database..."

# Clear output file
> "$OUTPUT_FILE"

# Header
echo "AutonomOS Database Audit" >> "$OUTPUT_FILE"
echo "Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")" >> "$OUTPUT_FILE"
echo "======================================" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Current database
echo "DATABASE INFO:" >> "$OUTPUT_FILE"
python3 "$SCRIPT_DIR/_psql.py" "$DB_URL" "SELECT current_database(), current_user;" >> "$OUTPUT_FILE" 2>&1 || {
  echo "ERROR: Failed to connect to database" >> "$OUTPUT_FILE"
  echo "❌ Failed to connect to database"
  exit 1
}
echo "" >> "$OUTPUT_FILE"

# Search path
echo "SEARCH PATH:" >> "$OUTPUT_FILE"
python3 "$SCRIPT_DIR/_psql.py" "$DB_URL" "SHOW search_path;" >> "$OUTPUT_FILE" 2>&1
echo "" >> "$OUTPUT_FILE"

# Table list
echo "TABLES IN PUBLIC SCHEMA:" >> "$OUTPUT_FILE"
python3 "$SCRIPT_DIR/_psql.py" "$DB_URL" "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;" >> "$OUTPUT_FILE" 2>&1
echo "" >> "$OUTPUT_FILE"

# Alembic version
echo "ALEMBIC VERSION:" >> "$OUTPUT_FILE"
python3 "$SCRIPT_DIR/_psql.py" "$DB_URL" "SELECT version_num FROM alembic_version;" >> "$OUTPUT_FILE" 2>&1 || {
  echo "⚠️  alembic_version table not found or empty" >> "$OUTPUT_FILE"
}
echo "" >> "$OUTPUT_FILE"

echo "✅ Audit complete → $OUTPUT_FILE"

echo ""
echo "================================"
echo "📋 DIAGNOSIS"
echo "================================"

# Check for alembic_version
has_alembic=$(grep -c "version_num" "$OUTPUT_FILE" || echo "0")

if [ "$has_alembic" -gt 0 ]; then
  version=$(grep -A 1 "version_num" "$OUTPUT_FILE" | tail -1 | tr -d '[:space:]')
  echo "✅ OK: Database tracked by Alembic at version: $version"
  exit 0
else
  echo "❌ MISSING: alembic_version table not present"
  echo "   → Run scripts/stamp_prod_baseline.sh to initialize tracking"
  exit 1
fi
