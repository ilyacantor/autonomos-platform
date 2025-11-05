#!/bin/bash
# 
# Stamp Baseline Migration Script
# 
# This script stamps the production database with the baseline migration.
# Use this ONCE when first deploying Alembic to an existing database.
# 
# This tells Alembic: "The current state of production is considered migrated to this point"
# From here forward, only schema CHANGES will generate migrations.
# 

echo "🏷️  Stamping database with baseline migration..."
echo ""
echo "This marks the current production schema as the starting point for Alembic."
echo "Run this ONCE on first deploy, then let alembic upgrade head handle future migrations."
echo ""

alembic stamp head

if [ $? -eq 0 ]; then
  echo ""
  echo "✅ Database stamped successfully!"
  echo ""
  echo "Next steps:"
  echo "  1. From now on, 'alembic upgrade head' will run automatically on startup"
  echo "  2. To create new migrations: alembic revision --autogenerate -m 'description'"
  echo "  3. Test migrations locally before deploying to production"
else
  echo ""
  echo "❌ Failed to stamp database"
  echo ""
  echo "Make sure DATABASE_URL environment variable is set correctly"
fi
