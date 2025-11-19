# Single Database Deployment Setup

## Overview

This project uses **ONE database** (Supabase) for both development and production.

Replit's automatic database migration system is **DISABLED** to prevent destructive schema changes.

---

## Configuration

**Database:** Supabase (external)
- Development: Uses `DATABASE_URL`
- Production: Uses same `DATABASE_URL` 
- Schema managed manually via Alembic

**Replit Auto-Migrations:** DISABLED
- `DISABLE_AUTO_MIGRATIONS=true` in `start.sh`
- Prevents Replit from proposing DROP TABLE operations
- All schema changes managed via Alembic

---

## How to Publish Safely

### Before Publishing:

1. **Ensure schema is up-to-date:**
   ```bash
   alembic upgrade head
   ```

2. **Run deploy guard:**
   ```bash
   make deploy-check
   ```

3. **Proceed to Replit Publishing**

### During Publishing:

**IMPORTANT:** Replit's Publishing page will show:

✅ **Expected:** "Database migrations validated successfully" 
✅ **Expected:** "No database changes detected"

❌ **If you see DROP TABLE warnings:**
- **DO NOT APPROVE**
- The auto-migration disable isn't working
- Contact support or check `start.sh` configuration

---

## Migration Workflow

### Creating New Migrations:

```bash
# 1. Modify models in app/models.py or aam_hybrid/shared/models.py

# 2. Generate migration
alembic revision --autogenerate -m "description"

# 3. Review generated migration in alembic/versions/

# 4. Test locally
alembic upgrade head

# 5. Commit to git
git add alembic/versions/*.py app/models.py
git commit -m "feat(db): add new schema changes"

# 6. Publish (migrations run automatically via start.sh)
```

---

## Why Single Database?

**Benefits:**
- ✅ Simpler - one connection string
- ✅ Lower cost - one database instance
- ✅ Easier management - no sync needed
- ✅ Same data in dev and prod contexts

**Trade-offs:**
- ⚠️ Must be careful with destructive changes
- ⚠️ Test data mixes with production (use tenant isolation)
- ⚠️ Must disable Replit's auto-migration feature

---

## Emergency Procedures

### If Replit Shows DROP TABLE Warnings:

1. **Cancel the publish immediately**
2. **Verify DISABLE_AUTO_MIGRATIONS is set:**
   ```bash
   grep DISABLE_AUTO_MIGRATIONS start.sh
   ```
3. **Check start.sh actually exports it**
4. **Restart workflow to pick up changes**
5. **Try publishing again**

### If Schema Gets Out of Sync:

```bash
# Check current schema version
alembic current

# Apply any pending migrations
alembic upgrade head

# Verify guard passes
make deploy-check
```

---

## Database Access

**Development (workspace):**
- Uses `DATABASE_URL` environment variable
- Points to Supabase

**Production (published):**
- Uses same `DATABASE_URL` 
- Managed by Replit Secrets
- Schema identical to development (via Alembic)

---

## Important Notes

1. **Never manually edit database schema** - Always use Alembic
2. **Replit auto-migrations are disabled** - Don't expect Replit to manage schema
3. **One database for everything** - Use tenant_id for data isolation
4. **Alembic is the single source of truth** - All schema changes go through migrations

---

*Last updated: November 7, 2025*
