#!/bin/bash
# 
# Stamp Production Database with Baseline Migration
# 
# This script stamps the PRODUCTION database specifically.
# Run this from your workspace to stamp production remotely.
# 

if [ -z "$DATABASE_URL" ]; then
  echo "❌ ERROR: DATABASE_URL environment variable not set"
  echo ""
  echo "To stamp production database:"
  echo "  1. Get your production DATABASE_URL from Replit Secrets"
  echo "  2. Run: DATABASE_URL='your-production-url' ./scripts/stamp_production.sh"
  exit 1
fi

echo "🏷️  Stamping PRODUCTION database with baseline migration..."
echo ""
echo "Database URL: ${DATABASE_URL:0:30}..."
echo ""
echo "This marks the current production schema as the starting point for Alembic."
echo ""

# Use the DATABASE_URL from environment to target production
alembic stamp head

if [ $? -eq 0 ]; then
  echo ""
  echo "✅ Production database stamped successfully!"
  echo ""
  echo "You can now deploy without DROP TABLE warnings."
else
  echo ""
  echo "❌ Failed to stamp production database"
  echo ""
  echo "Make sure you're using the correct production DATABASE_URL"
fi
