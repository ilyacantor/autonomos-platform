# AutonomOS Deployment Policy

## Overview

This document establishes the **single source of truth** for database migrations and deployment procedures for the AutonomOS platform. Following this policy prevents data loss and ensures safe, incremental schema changes.

---

## Core Principle: Alembic Owns All Migrations

**RULE:** Alembic is the **only** owner of database schema migrations.

- ✅ All schema changes MUST go through Alembic migrations
- ❌ NEVER manually edit production database schema via SQL
- ❌ NEVER approve Replit Publishing plans showing `DROP TABLE` statements
- ✅ Production and development databases are tracked by the same migration history

---

## First-Time Production Setup

When deploying Alembic to an **existing** production database with pre-existing tables, you must perform a one-time baseline stamp.

### Why?

Alembic needs to know that production's current state is the "baseline" - otherwise it will try to drop all existing tables to match the empty baseline migration.

### How to Baseline Stamp Production

**Run this script ONCE** before your first Alembic-managed deployment:

```bash
./scripts/stamp_prod_baseline.sh
```

This script:
- ✅ Is **idempotent** - safe to run multiple times
- ✅ Checks if production is already stamped (no-op if correct)
- ✅ Creates `alembic_version` table and marks production as being at baseline
- ✅ Verifies that `alembic upgrade head` completes without destructive operations
- ❌ NEVER issues `DROP TABLE` statements

**After stamping:** Production is tracked by Alembic and ready for incremental migrations.

---

## Pre-Publishing Safety Check

**BEFORE** clicking "Approve and Publish" in Replit's Publishing UI, run:

```bash
./scripts/deploy_guard.sh
```

This guard script:
1. Audits both development and production databases
2. Checks that both have `alembic_version` tracking
3. Compares schema distance (table count differences)
4. **Exits with error** if issues are detected

### Guard Results

| Status | Meaning | Action |
|--------|---------|--------|
| ✅ GUARD PASSED | Schemas synchronized, Alembic tracking in sync | Proceed with Publishing |
| ❌ GUARD FAILED | Issues detected (see output) | Fix issues, re-run guard |

---

## What to Do If Replit Shows Destructive Plans

If Replit's Publishing page displays a migration plan containing:
- `DROP TABLE` statements
- Mass deletions or schema resets
- Warnings about data loss

**DO NOT APPROVE IT.**

### Recovery Steps:

1. **Cancel the publish attempt**
2. Run the audit script to diagnose:
   ```bash
   ./scripts/db_audit.sh
   ```
3. Review audit outputs in `./ops/db_audit/`
4. If production lacks `alembic_version`:
   ```bash
   ./scripts/stamp_prod_baseline.sh
   ```
5. Re-run the guard:
   ```bash
   ./scripts/deploy_guard.sh
   ```
6. Only proceed with Publishing when guard passes

---

## Normal Development Workflow

### Creating New Migrations

1. **Modify models** in `app/models.py` or `aam_hybrid/shared/models.py`
2. **Generate migration:**
   ```bash
   alembic revision --autogenerate -m "description of changes"
   ```
3. **Review the generated migration** in `alembic/versions/`
4. **Test locally:**
   ```bash
   alembic upgrade head
   ```
5. **Commit to git:**
   ```bash
   git add alembic/versions/XXXXX_description.py app/models.py
   git commit -m "feat(db): add new table/column"
   ```

### Deploying Changes

1. **Run pre-publish guard:**
   ```bash
   ./scripts/deploy_guard.sh
   ```
2. If guard passes, proceed with Replit Publishing
3. On deployment, `start.sh` automatically runs `alembic upgrade head`
4. New migrations are applied incrementally to production

---

## Emergency Procedures

### Temporarily Disable Auto-Migrations

If you need to deploy without running migrations (troubleshooting, hotfix, etc.):

**In Replit Secrets or Environment Variables:**
```
DISABLE_AUTO_MIGRATIONS=true
```

With this flag set:
- `start.sh` skips `alembic upgrade head`
- Server starts without touching database schema
- **Remember to remove this flag** after resolving the issue

### Rollback a Migration

```bash
# Rollback last migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# See migration history
alembic history
```

**⚠️ WARNING:** Downgrading in production requires careful planning to avoid data loss.

---

## Database Audit Details

### Manual Audit

Run the audit script anytime to check database health:

```bash
./scripts/db_audit.sh
```

**Outputs:**
- `ops/db_audit/dev-summary.txt` - Development database state
- `ops/db_audit/prod-summary.txt` - Production database state (if `DATABASE_URL_PROD` set)

**Diagnosis codes:**
- `✅ OK` - Schemas synchronized, Alembic versions match
- `⚠️ MISMATCH` - Schema drift or version mismatch detected
- `❌ MISSING` - Production lacks `alembic_version` table

### What the Audit Checks

For each database:
- Current database name and user
- Search path configuration
- List of all tables in `public` schema
- Current Alembic migration version
- Schema distance calculation (table count difference)

---

## Architecture Notes

### Multi-Base Architecture

AutonomOS uses two SQLAlchemy Base objects:
- `app.models.Base` - Main platform tables
- `aam_hybrid.shared.models.Base` - AAM connector tables

Alembic is configured (`alembic/env.py`) to merge metadata from both, ensuring all tables are tracked in a **single migration history**.

### Baseline Migration

The baseline migration (`5a9d6371e18c_baseline_migration_existing_schema.py`) is intentionally **empty**:

```python
def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
```

This preserves the existing production schema without recreating it. All future migrations build incrementally from this baseline.

---

## Troubleshooting

### "Production has unexpected Alembic version"

If `stamp_prod_baseline.sh` reports this error, production is already being tracked by Alembic but at a different migration than expected.

**DO NOT force-stamp.** Instead:
1. Check migration history: `alembic history`
2. Check production version: `alembic current` (with `DATABASE_URL_PROD`)
3. Investigate why versions diverged
4. Manual intervention may be required

### "Database migrations failed - continuing anyway"

If `start.sh` shows this warning:
1. Check the error message above it
2. Look for schema conflicts or syntax errors
3. Review the most recent migration
4. May need to rollback: `alembic downgrade -1`

### Replit Publishing Continues to Show DROP TABLE

If the guard passes but Replit still shows destructive plans:
1. Replit's auto-diff may be comparing against a cached schema
2. Try canceling and re-initiating the publish
3. Check that production database URL is correct in Replit secrets
4. As a last resort, contact Replit support - the platform may need to refresh its schema cache

---

## References

- **Alembic Documentation:** https://alembic.sqlalchemy.org/
- **Replit Database Docs:** https://docs.replit.com/
- **Migration Scripts:** `./scripts/` directory
- **Audit Outputs:** `./ops/db_audit/` directory

---

## Summary Checklist

**First-time setup:**
- [ ] Run `./scripts/stamp_prod_baseline.sh` once

**Before every publish:**
- [ ] Run `./scripts/deploy_guard.sh`
- [ ] Verify guard passes (exit code 0)
- [ ] If Replit shows DROP TABLE, cancel and investigate

**Creating new migrations:**
- [ ] Modify models in code
- [ ] `alembic revision --autogenerate -m "description"`
- [ ] Review generated migration
- [ ] Test locally with `alembic upgrade head`
- [ ] Commit to git

**Emergency:**
- [ ] Set `DISABLE_AUTO_MIGRATIONS=true` to skip migrations temporarily
- [ ] Remove flag after resolving issue

---

*This policy ensures zero data loss and establishes Alembic as the authoritative migration system for AutonomOS.*
