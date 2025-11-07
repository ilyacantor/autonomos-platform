#!/bin/bash
#
# Deploy Guard Script
# Pre-publish safety check - runs database audit and blocks if issues detected
# Run this BEFORE approving any Replit Publishing plan
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🛡️  AutonomOS Deploy Guard"
echo "================================"
echo ""
echo "Running pre-publish safety checks..."
echo ""

# Run database audit
"$SCRIPT_DIR/db_audit.sh"

audit_exit_code=$?

echo ""
echo "================================"

if [ $audit_exit_code -eq 0 ]; then
  echo "✅ GUARD PASSED"
  echo ""
  echo "Database schema is tracked by Alembic."
  echo "Safe to proceed with Replit Publishing."
  echo ""
  echo "⚠️  IMPORTANT: If Replit's Publishing page shows a plan with"
  echo "   DROP TABLE statements, DO NOT APPROVE IT."
  echo "   Cancel and investigate the discrepancy."
  exit 0
else
  echo "❌ GUARD FAILED"
  echo ""
  echo "Database audit detected issues that must be resolved before publishing."
  echo ""
  echo "REQUIRED ACTIONS:"
  echo "  1. Review the audit output above"
  echo "  2. If database lacks alembic_version, run: ./scripts/stamp_prod_baseline.sh"
  echo "  3. Re-run this guard script after fixes"
  echo "  4. Only then proceed with Replit Publishing"
  echo ""
  echo "DO NOT approve any Replit plan showing DROP TABLE statements."
  exit 1
fi
