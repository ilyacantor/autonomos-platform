# Production Baseline Setup

**Last Updated:** November 19, 2025

## IMPORTANT: Run this ONCE in production shell

When you deploy for the first time with Alembic, you need to tell production 
that its current schema is the "baseline."

### Steps:

1. Open Replit Console (not deploying, just the Shell tab)
2. Make sure you're connected to production database
3. Run: `./scripts/stamp_baseline.sh`

This tells Alembic: "Production is already at this migration level."

### What This Does:
- Marks production as being at baseline migration
- Future deployments will only apply NEW migrations
- Prevents data loss from table drops

### After This:
- Alembic will manage schema changes going forward
- Replit deployments won't try to recreate tables
- Safe, incremental migrations only
