# AutonomOS Platform - Operational Procedures

**Version:** 1.0  
**Last Updated:** November 18, 2025  
**Owner:** Platform Operations Team

---

## Table of Contents

1. [Tenant Onboarding](#tenant-onboarding)
2. [Tenant Offboarding](#tenant-offboarding)
3. [Job Reconciliation](#job-reconciliation)
4. [Redis Cache Invalidation](#redis-cache-invalidation)
5. [Database Backup and Restore](#database-backup-and-restore)
6. [Worker Scaling](#worker-scaling)
7. [Rolling Deployments](#rolling-deployments)
8. [Incident Response](#incident-response)
9. [Disaster Recovery](#disaster-recovery)
10. [Security Incident Handling](#security-incident-handling)

---

## Tenant Onboarding

### Standard Onboarding Procedure

**Duration:** 15-30 minutes  
**Prerequisites:** Admin access, database credentials, valid email

### Step 1: Create Tenant Account

**Via API:**

```bash
# Register new tenant via API
curl -X POST https://your-domain.repl.co/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@newcustomer.com",
    "password": "TemporaryPassword123!",
    "name": "New Customer Inc"
  }'
```

**Via Database:**

```sql
-- Direct database insertion (for bulk onboarding)
BEGIN;

INSERT INTO tenants (id, name, created_at)
VALUES (
  gen_random_uuid(),
  'New Customer Inc',
  NOW()
)
RETURNING id;

-- Save the returned tenant_id for next step
-- Example: 550e8400-e29b-41d4-a716-446655440000

INSERT INTO users (id, email, hashed_password, tenant_id, created_at)
VALUES (
  gen_random_uuid(),
  'admin@newcustomer.com',
  '$argon2id$v=19$m=65536,t=3,p=4$...',  -- Pre-hashed password
  '550e8400-e29b-41d4-a716-446655440000',  -- Tenant ID from above
  NOW()
);

COMMIT;
```

### Step 2: Initialize Tenant Resources

```python
# Python script: scripts/provision_demo_tenant.py
from app.database import SessionLocal
from app import crud, schemas
from uuid import UUID

def provision_tenant(tenant_id: str, tenant_name: str):
    """
    Provision tenant resources:
    - Initialize Redis namespace
    - Create default connector definitions
    - Seed canonical mappings
    """
    db = SessionLocal()
    
    try:
        # Create tenant record
        tenant = crud.create_tenant(db, schemas.TenantCreate(name=tenant_name))
        
        # Initialize Redis namespace
        from shared.redis_client import get_redis_client
        redis_client = get_redis_client()
        redis_client.set(f"tenant:{tenant.id}:initialized", "true")
        
        # Seed default mappings
        from services.aam.initializer import run_aam_initializer
        run_aam_initializer(tenant_id=str(tenant.id))
        
        print(f"✅ Tenant {tenant.name} provisioned successfully")
        print(f"   Tenant ID: {tenant.id}")
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        print(f"❌ Provisioning failed: {e}")
        raise
    
    finally:
        db.close()

# Usage
provision_tenant(
    tenant_id="550e8400-e29b-41d4-a716-446655440000",
    tenant_name="New Customer Inc"
)
```

### Step 3: Configure Connectors

```bash
# Add connector credentials to environment
cat >> .env << EOF

# New Customer Inc - Salesforce
SALESFORCE_CLIENT_ID_550e8400=your_client_id
SALESFORCE_CLIENT_SECRET_550e8400=your_client_secret
SALESFORCE_REFRESH_TOKEN_550e8400=your_refresh_token

# New Customer Inc - Supabase
SUPABASE_URL_550e8400=https://newcustomer.supabase.co
SUPABASE_KEY_550e8400=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
EOF
```

### Step 4: Verify Onboarding

```bash
# Test login
curl -X POST https://your-domain.repl.co/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@newcustomer.com",
    "password": "TemporaryPassword123!"
  }'

# Verify tenant isolation
curl -X GET https://your-domain.repl.co/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"

# Expected output:
# {
#   "id": "...",
#   "email": "admin@newcustomer.com",
#   "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
#   "created_at": "..."
# }
```

### Step 5: Send Welcome Email

```python
# Send onboarding email with credentials and documentation links
import smtplib
from email.mime.text import MIMEText

def send_welcome_email(email: str, tenant_id: str, temp_password: str):
    msg = MIMEText(f"""
    Welcome to AutonomOS!
    
    Your account has been created:
    - Email: {email}
    - Temporary Password: {temp_password}
    - Tenant ID: {tenant_id}
    
    Next steps:
    1. Login at https://your-domain.repl.co
    2. Change your password immediately
    3. Review documentation: https://docs.autonomos.dev
    4. Configure your first connector
    
    Support: support@autonomos.dev
    """)
    
    msg['Subject'] = 'Welcome to AutonomOS'
    msg['From'] = 'noreply@autonomos.dev'
    msg['To'] = email
    
    # Send email (configure SMTP settings)
    # ...
```

---

## Tenant Offboarding

### Offboarding Checklist

- [ ] Export tenant data for archival
- [ ] Terminate active sessions
- [ ] Cancel running jobs
- [ ] Delete tenant-scoped data
- [ ] Remove Redis keys
- [ ] Clean up connector credentials
- [ ] Archive logs
- [ ] Send confirmation email

### Step 1: Export Tenant Data

```bash
# Export all tenant data to JSON
python3 << EOF
from app.database import SessionLocal
from app.models import *
import json

tenant_id = "550e8400-e29b-41d4-a716-446655440000"
db = SessionLocal()

export_data = {
    "users": [u.__dict__ for u in db.query(User).filter(User.tenant_id == tenant_id).all()],
    "canonical_streams": [c.__dict__ for c in db.query(CanonicalStream).filter(CanonicalStream.tenant_id == tenant_id).all()],
    "mapping_registry": [m.__dict__ for m in db.query(MappingRegistry).filter(MappingRegistry.tenant_id == tenant_id).all()],
    "drift_events": [d.__dict__ for d in db.query(DriftEvent).filter(DriftEvent.tenant_id == tenant_id).all()],
}

with open(f"tenant_{tenant_id}_export.json", "w") as f:
    json.dump(export_data, f, indent=2, default=str)

print(f"✅ Data exported to tenant_{tenant_id}_export.json")
EOF
```

### Step 2: Terminate Active Sessions

```python
from shared.redis_client import get_redis_client

redis_client = get_redis_client()
tenant_id = "550e8400-e29b-41d4-a716-446655440000"

# Delete all session tokens
for key in redis_client.keys(f"session:{tenant_id}:*"):
    redis_client.delete(key)

print(f"✅ All sessions terminated for tenant {tenant_id}")
```

### Step 3: Cancel Running Jobs

```bash
# Cancel all running jobs for tenant
python3 << EOF
from shared.redis_client import get_redis_client
from services.mapping_intelligence.job_state import BulkMappingJobState

redis_client = get_redis_client()
job_state = BulkMappingJobState(redis_client)

tenant_id = "550e8400-e29b-41d4-a716-446655440000"

jobs = job_state.get_all_jobs_for_tenant(tenant_id)
for job in jobs:
    if job['status'] in ['pending', 'running']:
        job_state.set_error(tenant_id, job['job_id'], "Tenant offboarded")

print(f"✅ Cancelled {len(jobs)} jobs for tenant {tenant_id}")
EOF
```

### Step 4: Delete Tenant Data

```sql
-- ⚠️ CAUTION: This is irreversible!
-- Verify tenant_id before executing

BEGIN;

SET LOCAL tenant_id = '550e8400-e29b-41d4-a716-446655440000';

DELETE FROM dcl_unified_contact_link WHERE tenant_id = current_setting('tenant_id')::uuid;
DELETE FROM dcl_unified_contact WHERE tenant_id = current_setting('tenant_id')::uuid;
DELETE FROM materialized_contacts WHERE tenant_id = current_setting('tenant_id')::uuid;
DELETE FROM materialized_opportunities WHERE tenant_id = current_setting('tenant_id')::uuid;
DELETE FROM materialized_accounts WHERE tenant_id = current_setting('tenant_id')::uuid;
DELETE FROM hitl_repair_audit WHERE tenant_id = current_setting('tenant_id')::uuid;
DELETE FROM field_mappings WHERE tenant_id = current_setting('tenant_id')::uuid;
DELETE FROM connector_definitions WHERE tenant_id = current_setting('tenant_id')::uuid;
DELETE FROM schema_changes WHERE tenant_id = current_setting('tenant_id')::uuid;
DELETE FROM drift_events WHERE tenant_id = current_setting('tenant_id')::uuid;
DELETE FROM mapping_registry WHERE tenant_id = current_setting('tenant_id')::uuid;
DELETE FROM canonical_streams WHERE tenant_id = current_setting('tenant_id');
DELETE FROM task_logs WHERE tenant_id = current_setting('tenant_id')::uuid;
DELETE FROM tasks WHERE tenant_id = current_setting('tenant_id')::uuid;
DELETE FROM users WHERE tenant_id = current_setting('tenant_id')::uuid;
DELETE FROM tenants WHERE id = current_setting('tenant_id')::uuid;

COMMIT;

-- Verify deletion
SELECT count(*) FROM users WHERE tenant_id = '550e8400-e29b-41d4-a716-446655440000';
-- Should return 0
```

### Step 5: Clean Up Redis

```bash
# Delete all Redis keys for tenant
redis-cli --eval - tenant_id , << EOF
local tenant_id = ARGV[1]
local cursor = "0"
local deleted = 0

repeat
    local result = redis.call("SCAN", cursor, "MATCH", "*" .. tenant_id .. "*")
    cursor = result[1]
    local keys = result[2]
    
    for i, key in ipairs(keys) do
        redis.call("DEL", key)
        deleted = deleted + 1
    end
until cursor == "0"

return deleted
EOF 550e8400-e29b-41d4-a716-446655440000
```

---

## Job Reconciliation

### When to Reconcile

- Semaphore leak detected (active jobs != Redis counter)
- Worker crash (jobs stuck in "running" state)
- Manual cleanup after incident

### Manual Job Reconciliation

```python
# scripts/job_reconciliation.py
from shared.redis_client import get_redis_client
from services.mapping_intelligence.job_state import BulkMappingJobState
import logging

logger = logging.getLogger(__name__)

def reconcile_jobs(tenant_id: str, dry_run: bool = True):
    """
    Reconcile job state and semaphore counter.
    
    Fixes:
    - Leaked semaphore slots (jobs completed but semaphore not decremented)
    - Stuck jobs (running > 1 hour)
    - Orphaned jobs (no worker, but marked running)
    """
    redis_client = get_redis_client()
    job_state = BulkMappingJobState(redis_client)
    
    # Get all jobs for tenant
    jobs = job_state.get_all_jobs_for_tenant(tenant_id)
    
    running_jobs = [j for j in jobs if j['status'] == 'running']
    completed_jobs = [j for j in jobs if j['status'] == 'completed']
    failed_jobs = [j for j in jobs if j['status'] == 'failed']
    
    # Get semaphore count
    semaphore_count = job_state.get_active_job_count(tenant_id)
    
    logger.info(f"Tenant {tenant_id}:")
    logger.info(f"  Running jobs: {len(running_jobs)}")
    logger.info(f"  Completed jobs: {len(completed_jobs)}")
    logger.info(f"  Failed jobs: {len(failed_jobs)}")
    logger.info(f"  Semaphore count: {semaphore_count}")
    
    # Detect semaphore leak
    if semaphore_count != len(running_jobs):
        logger.warning(f"⚠️  Semaphore leak detected: {semaphore_count} != {len(running_jobs)}")
        
        if not dry_run:
            # Reset semaphore to actual running jobs
            redis_client.set(
                f"job:semaphore:tenant:{tenant_id}",
                len(running_jobs)
            )
            logger.info(f"✅ Semaphore reset to {len(running_jobs)}")
    
    # Find stuck jobs (running > 1 hour)
    from datetime import datetime, timedelta
    
    stuck_jobs = []
    for job in running_jobs:
        started_at = datetime.fromisoformat(job.get('started_at', ''))
        if datetime.utcnow() - started_at > timedelta(hours=1):
            stuck_jobs.append(job)
    
    if stuck_jobs:
        logger.warning(f"⚠️  Found {len(stuck_jobs)} stuck jobs")
        
        for job in stuck_jobs:
            logger.info(f"  - {job['job_id']} (started {job.get('started_at')})")
            
            if not dry_run:
                job_state.set_error(
                    tenant_id,
                    job['job_id'],
                    "Job stuck for >1 hour, auto-failed during reconciliation"
                )
                logger.info(f"    ✅ Marked as failed")
    
    logger.info(f"Reconciliation complete (dry_run={dry_run})")

# Usage
reconcile_jobs("550e8400-e29b-41d4-a716-446655440000", dry_run=False)
```

---

## Redis Cache Invalidation

### Invalidate Feature Flags

```python
from app.config.feature_flags import FeatureFlagConfig

# Clear all feature flags (forces reload from defaults)
FeatureFlagConfig.clear_all()
```

### Invalidate DCL Graph Cache

```python
from shared.redis_client import get_redis_client

redis_client = get_redis_client()

# Invalidate graph cache for specific tenant
redis_client.delete("dcl:graph:tenant:550e8400-e29b-41d4-a716-446655440000")

# Invalidate all graph caches
for key in redis_client.keys("dcl:graph:*"):
    redis_client.delete(key)
```

### Invalidate Mapping Cache

```bash
# Clear all mapping caches
redis-cli --eval - << EOF
local cursor = "0"
local deleted = 0

repeat
    local result = redis.call("SCAN", cursor, "MATCH", "mapping:*")
    cursor = result[1]
    local keys = result[2]
    
    for i, key in ipairs(keys) do
        redis.call("DEL", key)
        deleted = deleted + 1
    end
until cursor == "0"

return deleted
EOF
```

---

## Database Backup and Restore

### Automated Backups (PostgreSQL)

**Daily Backup Script:**

```bash
#!/bin/bash
# /etc/cron.daily/autonomos-backup.sh

BACKUP_DIR="/var/backups/autonomos"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/autonomos_$DATE.sql.gz"

# Create backup directory
mkdir -p $BACKUP_DIR

# Dump database
pg_dump $SUPABASE_DB_URL | gzip > $BACKUP_FILE

# Upload to S3 (optional)
aws s3 cp $BACKUP_FILE s3://autonomos-backups/

# Delete local backups older than 7 days
find $BACKUP_DIR -name "autonomos_*.sql.gz" -mtime +7 -delete

echo "✅ Backup complete: $BACKUP_FILE"
```

### Manual Backup

```bash
# Full database backup
pg_dump $SUPABASE_DB_URL > autonomos_backup_$(date +%Y%m%d).sql

# Backup with compression
pg_dump $SUPABASE_DB_URL | gzip > autonomos_backup_$(date +%Y%m%d).sql.gz

# Backup specific tenant data only
pg_dump $SUPABASE_DB_URL \
  --table=users \
  --table=canonical_streams \
  --table=mapping_registry \
  --where="tenant_id='550e8400-e29b-41d4-a716-446655440000'" \
  > tenant_550e8400_backup.sql
```

### Restore from Backup

```bash
# Restore full database (⚠️ CAUTION: This will overwrite existing data!)
gunzip < autonomos_backup_20251118.sql.gz | psql $SUPABASE_DB_URL

# Restore specific tenant
psql $SUPABASE_DB_URL < tenant_550e8400_backup.sql
```

### Point-in-Time Recovery (PITR)

For Supabase:

1. Go to Supabase Dashboard → Database → Backups
2. Select restore point (up to 7 days ago on Pro plan)
3. Click "Restore" → Creates new database instance
4. Update `SUPABASE_DB_URL` to new instance
5. Restart application

---

## Worker Scaling

### Horizontal Scaling (Add More Workers)

```bash
# Start additional workers
rq worker default --url $REDIS_URL &
rq worker default --url $REDIS_URL &

# Via systemd (production)
sudo systemctl start rq-worker@{5..8}

# Verify workers
rq info --url $REDIS_URL

# Expected output:
# default       |██████████████████ 0
# 8 workers, 0 queues
```

### Vertical Scaling (Increase Worker Concurrency)

```python
# Update worker.py to use multiprocessing
from rq import Worker
from rq.worker_pool import WorkerPool

# Start worker pool with 4 workers
with WorkerPool([Worker(['default'])], num_workers=4).run():
    pass
```

### Auto-Scaling (Kubernetes)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: rq-worker-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: rq-worker
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: External
      external:
        metric:
          name: autonomos_queue_depth
        target:
          type: AverageValue
          averageValue: "100"
```

---

## Rolling Deployments

### Zero-Downtime Deployment Strategy

**Step 1: Prepare New Version**

```bash
# Build new version
git pull origin main
pip install -r requirements.txt
alembic upgrade head

# Build frontend
cd frontend && npm install && npm run build && cd ..
cp -r frontend/dist/* static/
```

**Step 2: Health Check**

```bash
# Verify new version health
curl http://localhost:5000/api/v1/health
```

**Step 3: Rolling Restart (Kubernetes)**

```bash
# Update deployment
kubectl set image deployment/autonomos-api autonomos=autonomos:v1.2.0

# Monitor rollout
kubectl rollout status deployment/autonomos-api

# Rollback if needed
kubectl rollout undo deployment/autonomos-api
```

**Step 4: Rolling Restart (Systemd)**

```bash
# Restart workers one by one (10s delay between each)
for i in {1..4}; do
  sudo systemctl restart rq-worker@$i
  sleep 10
done

# Restart application (graceful shutdown)
sudo systemctl reload autonomos
```

---

## Incident Response

### Incident Severity Levels

| Level | Definition | Response Time | Examples |
|-------|------------|---------------|----------|
| **P0** | Complete outage | 15 minutes | Database down, application crash |
| **P1** | Major degradation | 1 hour | Semaphore leak, high error rate |
| **P2** | Partial degradation | 4 hours | High latency, queue backlog |
| **P3** | Minor issue | Next business day | UI bug, cosmetic issue |

### Incident Response Procedure

**Step 1: Incident Declaration**

```bash
# Post to #incidents Slack channel
INCIDENT DECLARED - P1
Title: High job error rate (25%)
Impact: Bulk mapping jobs failing
Started: 2025-11-18 14:30 UTC
Incident Commander: @john.doe
```

**Step 2: Initial Assessment**

```bash
# Check system health
curl http://localhost:5000/api/v1/health

# Check error rate
curl http://localhost:9090/api/v1/query?query='rate(autonomos_jobs_total{status="failed"}[5m])'

# Check logs
tail -f /var/log/autonomos/app.log | grep ERROR
```

**Step 3: Mitigation**

```bash
# Common mitigations:

# 1. Restart workers
sudo systemctl restart rq-worker@{1..4}

# 2. Clear Redis cache
redis-cli FLUSHDB

# 3. Reset semaphore
python3 scripts/job_reconciliation.py --tenant-id all --fix

# 4. Scale workers
kubectl scale deployment rq-worker --replicas=8
```

**Step 4: Communication**

```bash
# Update status page
curl -X POST https://status.autonomos.dev/api/incidents \
  -H "Authorization: Bearer $STATUS_API_KEY" \
  -d '{
    "title": "High job error rate",
    "status": "investigating",
    "message": "We are investigating elevated error rates. Jobs may be delayed."
  }'
```

**Step 5: Resolution & Postmortem**

```markdown
# Incident Postmortem: High Job Error Rate

## Summary
- **Incident:** P1 - High job error rate (25%)
- **Duration:** 45 minutes (14:30 - 15:15 UTC)
- **Root Cause:** Redis connection pool exhaustion
- **Impact:** 523 jobs failed, affecting 12 tenants

## Timeline
- 14:30: Alert fired: High error rate
- 14:35: Incident declared (P1)
- 14:40: Redis connection errors identified in logs
- 14:50: Redis restarted, connection pool reset
- 15:00: Error rate normalized
- 15:15: Incident resolved

## Action Items
- [ ] Increase Redis max connections from 100 to 500
- [ ] Add alerting on Redis connection pool utilization
- [ ] Document Redis scaling procedures

## Lessons Learned
- Need better Redis monitoring
- Connection pool defaults too conservative for production load
```

---

## Disaster Recovery

### Disaster Scenarios

1. **Complete database loss**
2. **Redis data loss**
3. **Application code corruption**
4. **Infrastructure failure (region outage)**

### Recovery Procedure

**Scenario 1: Database Loss**

```bash
# 1. Provision new database instance
# (Supabase, RDS, etc.)

# 2. Restore from latest backup
gunzip < autonomos_backup_20251118.sql.gz | psql $NEW_DATABASE_URL

# 3. Run migrations
SUPABASE_DB_URL=$NEW_DATABASE_URL alembic upgrade head

# 4. Update environment variable
export SUPABASE_DB_URL=$NEW_DATABASE_URL

# 5. Restart application
sudo systemctl restart autonomos

# 6. Verify data integrity
python3 scripts/verify_data_integrity.py
```

**Scenario 2: Redis Data Loss**

```bash
# Redis data is ephemeral and can be rebuilt

# 1. Restart Redis
sudo systemctl restart redis

# 2. Clear application cache
redis-cli FLUSHALL

# 3. Restart workers (they will repopulate queues)
sudo systemctl restart rq-worker@{1..4}

# 4. Resync feature flags
python3 scripts/resync_feature_flags.py
```

---

## Security Incident Handling

### Security Incident Types

1. **Unauthorized access**
2. **Data breach**
3. **API key leak**
4. **DDoS attack**

### Incident Response

**Unauthorized Access Detected:**

```bash
# 1. Revoke all active sessions
python3 << EOF
from shared.redis_client import get_redis_client

redis_client = get_redis_client()

# Delete all session tokens
for key in redis_client.keys("session:*"):
    redis_client.delete(key)

print("✅ All sessions revoked")
EOF

# 2. Rotate JWT secret
# Generate new secret
NEW_SECRET=$(openssl rand -hex 32)

# Update environment
sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$NEW_SECRET/" .env

# Restart application
sudo systemctl restart autonomos

# 3. Force password reset for all users
psql $SUPABASE_DB_URL << EOF
UPDATE users 
SET hashed_password = '$argon2id$v=19$...'  -- Placeholder forcing reset
WHERE id IS NOT NULL;
EOF
```

**API Key Leak:**

```bash
# 1. Rotate compromised keys immediately
# Update .env with new keys
# Example for Salesforce:
SALESFORCE_CLIENT_SECRET=new_secret_here

# 2. Revoke old keys in provider
# (Salesforce, Google, etc.)

# 3. Audit access logs
grep "SALESFORCE" /var/log/autonomos/audit.log | tail -100
```

---

## Escalation Contacts

| Severity | Contact | Response Time |
|----------|---------|---------------|
| P0 | On-call engineer (PagerDuty) | 15 min |
| P1 | Platform team lead | 1 hour |
| P2 | Platform team | 4 hours |
| P3 | Support ticket | Next business day |

**On-Call Rotation:** See PagerDuty schedule

---

## References

- [Observability Runbook](./OBSERVABILITY_RUNBOOK.md)
- [Deployment Guide](../deployment/DEPLOYMENT_GUIDE.md)
- [Security Hardening Guide](../security/SECURITY_HARDENING.md)
