# AutonomOS Platform - Deployment Guide

**Version:** 1.0  
**Last Updated:** November 18, 2025  
**Target Environment:** Production on Replit, Cloud VPS, or Kubernetes

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Database Setup](#database-setup)
4. [Redis Configuration](#redis-configuration)
5. [Worker Deployment](#worker-deployment)
6. [Frontend Deployment](#frontend-deployment)
7. [Health Checks](#health-checks)
8. [Reverse Proxy Configuration](#reverse-proxy-configuration)
9. [SSL/TLS Certificate Setup](#ssltls-certificate-setup)
10. [Production Checklist](#production-checklist)

---

## Prerequisites

### System Requirements

**Minimum:**
- **CPU:** 2 vCPU
- **RAM:** 4GB
- **Disk:** 20GB SSD
- **OS:** Linux (Ubuntu 22.04 LTS recommended)

**Recommended (Production):**
- **CPU:** 4 vCPU
- **RAM:** 16GB
- **Disk:** 100GB SSD
- **OS:** Linux (Ubuntu 22.04 LTS)

### Software Dependencies

```bash
# Python 3.11+
python3 --version  # Should be 3.11 or higher

# PostgreSQL 14+
psql --version

# Redis 6+
redis-cli --version

# Node.js 20+ (for frontend build)
node --version

# Nginx (optional, for reverse proxy)
nginx -v
```

### External Services

1. **PostgreSQL Database:**
   - Supabase (recommended)
   - Amazon RDS
   - Self-hosted PostgreSQL 14+
   - Minimum: `db.t3.small` (2 vCPU, 2GB RAM)

2. **Redis Instance:**
   - Upstash (recommended for TLS)
   - Amazon ElastiCache
   - Self-hosted Redis 6+
   - Minimum: 256MB memory

---

## Environment Configuration

### Complete .env Template

Create a `.env` file in the project root with the following variables:

```bash
# ========================================
# DATABASE CONFIGURATION
# ========================================

# PostgreSQL connection string
# Format: postgresql://username:password@host:port/database
# For Supabase: Use the "Connection pooling" URL (port 6543)
SUPABASE_DB_URL=postgresql://postgres.xxxxxxxxxxxx:password@aws-0-us-west-1.pooler.supabase.com:6543/postgres

# Fallback DATABASE_URL (Replit managed or legacy)
DATABASE_URL=postgresql://user:pass@localhost:5432/autonomos


# ========================================
# REDIS CONFIGURATION
# ========================================

# Redis URL with TLS support
# For Upstash: rediss://default:password@region.upstash.io:6379
# For local: redis://localhost:6379
REDIS_URL=rediss://default:AbCdEf1234567890@us1-modern-wombat-12345.upstash.io:6379

# Redis connection parameters (used if REDIS_URL not set)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0


# ========================================
# AUTHENTICATION & SECURITY
# ========================================

# JWT secret key for token signing (REQUIRED)
# Generate with: openssl rand -hex 32
JWT_SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6

# Legacy secret key (fallback)
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6

# JWT token expiration in minutes
JWT_EXPIRE_MINUTES=30

# Enable/disable authentication (production: true, dev: false)
DCL_AUTH_ENABLED=true


# ========================================
# AI/LLM CONFIGURATION
# ========================================

# Google Gemini API key (for RAG intelligence)
GOOGLE_API_KEY=AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ1234567

# OpenAI API key (optional, for alternative LLM)
OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz1234567890

# Pinecone API key (optional, for vector storage)
PINECONE_API_KEY=12345678-abcd-4321-efgh-567890123456


# ========================================
# CORS & WEB ORIGIN
# ========================================

# Allowed web origin for CORS
# Production: https://your-domain.com
# Development: http://localhost:3000
ALLOWED_WEB_ORIGIN=https://your-domain.repl.co


# ========================================
# EVENT STREAMING
# ========================================

# Enable Server-Sent Events for real-time updates
EVENT_STREAM_ENABLED=true

# SSE heartbeat interval in milliseconds
EVENT_STREAM_HEARTBEAT_MS=15000


# ========================================
# EXTERNAL INTEGRATIONS (Optional)
# ========================================

# Slack webhook for HITL alerts
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX

# AOS Discover service URL (for auto-onboarding)
AOD_BASE_URL=http://localhost:8000


# ========================================
# CONNECTOR CREDENTIALS (Example)
# ========================================

# Salesforce OAuth credentials
SALESFORCE_CLIENT_ID=your_salesforce_client_id
SALESFORCE_CLIENT_SECRET=your_salesforce_client_secret
SALESFORCE_REFRESH_TOKEN=your_salesforce_refresh_token

# Supabase connector credentials
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# MongoDB connector credentials
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/database?retryWrites=true&w=majority


# ========================================
# PRODUCTION SETTINGS
# ========================================

# Server host (0.0.0.0 for production)
HOST=0.0.0.0

# Server port (5000 is required for Replit webview)
PORT=5000

# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Uvicorn workers (for production)
UVICORN_WORKERS=4

# RQ worker concurrency
RQ_WORKER_COUNT=2
```

### Environment Variable Validation

Manually verify all required environment variables are set:

```bash
# Check critical variables are set
echo "DATABASE_URL: ${DATABASE_URL:0:20}..."
echo "JWT_SECRET_KEY length: ${#JWT_SECRET_KEY}"
echo "REDIS_URL: ${REDIS_URL:0:20}..."
echo "GOOGLE_API_KEY: ${GOOGLE_API_KEY:0:15}..."

# Validate JWT_SECRET_KEY length (should be 32+ characters)
if [ ${#JWT_SECRET_KEY} -lt 32 ]; then
  echo "❌ JWT_SECRET_KEY too short (${#JWT_SECRET_KEY} chars, need 32+)"
else
  echo "✅ JWT_SECRET_KEY is adequate length"
fi
```

---

## Database Setup

### Step 1: Create PostgreSQL Database

**Supabase (Recommended):**

1. Create a new project at https://supabase.com
2. Go to **Settings** > **Database**
3. Copy the **Connection pooling** string (port 6543)
4. Set `SUPABASE_DB_URL` in `.env`

**Self-Hosted:**

```bash
# Create database and user
sudo -u postgres psql

CREATE DATABASE autonomos;
CREATE USER autonomos_user WITH ENCRYPTED PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE autonomos TO autonomos_user;
\q
```

### Step 2: Install PostgreSQL Extensions

```sql
-- Connect to database
psql -U autonomos_user -d autonomos

-- Install required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- Verify extensions
\dx
```

Expected output:
```
                  List of installed extensions
   Name    | Version | Schema |         Description
-----------+---------+--------+------------------------------
 pgvector  | 0.5.1   | public | vector data type and functions
 uuid-ossp | 1.1     | public | generate universally unique identifiers
```

### Step 3: Run Alembic Migrations

```bash
# Install dependencies
pip install -r requirements.txt

# Run all migrations
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 5a9d6371e18c, baseline_migration
INFO  [alembic.runtime.migration] Running upgrade 5a9d6371e18c -> 7ed0ab069a63, add_phase0_mapping_registry
INFO  [alembic.runtime.migration] Running upgrade 7ed0ab069a63 -> b15b4a5021b3, add_kb_tables_with_pgvector
...
✅ Database schema initialized successfully
```

### Step 4: Verify Database Schema

```bash
# Check tables
psql $SUPABASE_DB_URL -c "\dt"
```

Expected tables:
```
 tenants
 users
 tasks
 task_logs
 canonical_streams
 mapping_registry
 drift_events
 materialized_accounts
 materialized_opportunities
 materialized_contacts
 dcl_unified_contact
 dcl_unified_contact_link
 connector_definitions
 entity_schemas
 field_mappings
 hitl_repair_audit
```

### Step 5: Seed Initial Data (Optional)

```bash
# Create demo tenant and user
python3 scripts/provision_demo_tenant.py

# Seed canonical mappings
python3 scripts/seed_aam_test_data.py
```

---

## Redis Configuration

### Option A: Upstash (Managed TLS Redis)

1. Create account at https://upstash.com
2. Create new Redis database
3. Enable TLS
4. Copy connection string (starts with `rediss://`)
5. Download CA certificate:

```bash
mkdir -p certs
curl -o certs/redis_ca.pem https://console.upstash.com/static/trust/redis_ca.pem
```

6. Set `REDIS_URL` in `.env`:
```bash
REDIS_URL=rediss://default:AbCdEf1234567890@us1-modern-wombat-12345.upstash.io:6379
```

### Option B: Amazon ElastiCache

```bash
# Get ElastiCache endpoint
aws elasticache describe-cache-clusters --cache-cluster-id my-cluster --show-cache-node-info

# Set REDIS_URL
REDIS_URL=redis://my-cluster.abc123.0001.use1.cache.amazonaws.com:6379
```

### Option C: Self-Hosted Redis

```bash
# Install Redis
sudo apt update
sudo apt install redis-server

# Enable Redis service
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Configure password
sudo vi /etc/redis/redis.conf
# Set: requirepass your_secure_password

# Restart Redis
sudo systemctl restart redis-server

# Set REDIS_URL
REDIS_URL=redis://:your_secure_password@localhost:6379
```

### Redis TLS/SSL Setup

If using TLS (recommended for production):

```bash
# Generate self-signed certificate (for self-hosted)
openssl req -x509 -nodes -newkey rsa:4096 \
  -keyout certs/redis-server.key \
  -out certs/redis-server.crt \
  -days 3650 \
  -subj "/CN=redis-server"

# Configure Redis for TLS
# Add to /etc/redis/redis.conf:
port 0
tls-port 6379
tls-cert-file /path/to/certs/redis-server.crt
tls-key-file /path/to/certs/redis-server.key
tls-ca-cert-file /path/to/certs/redis_ca.pem
```

### Verify Redis Connection

```bash
# Test Redis connection
python3 << EOF
from shared.redis_client import get_redis_client
redis_client = get_redis_client()
if redis_client:
    redis_client.ping()
    print("✅ Redis connection successful")
else:
    print("❌ Redis connection failed")
EOF
```

---

## Worker Deployment

### RQ Worker Setup

The platform uses **Python RQ** for background job processing (bulk mappings, RAG intelligence).

### Step 1: Install Worker Dependencies

```bash
pip install redis rq
```

### Step 2: Start RQ Worker

```bash
# Single worker
rq worker default --url $REDIS_URL

# Multiple workers (recommended for production)
rq worker default --url $REDIS_URL &
rq worker default --url $REDIS_URL &
rq worker default --url $REDIS_URL &
```

### Step 3: Worker Systemd Service (Production)

Create `/etc/systemd/system/rq-worker@.service`:

```ini
[Unit]
Description=RQ Worker %i
After=network.target redis.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/autonomos
Environment="PATH=/var/www/autonomos/venv/bin"
EnvironmentFile=/var/www/autonomos/.env
ExecStart=/var/www/autonomos/venv/bin/rq worker default --url ${REDIS_URL}
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

Enable and start workers:

```bash
# Start 4 workers
sudo systemctl enable rq-worker@{1..4}
sudo systemctl start rq-worker@{1..4}

# Check status
sudo systemctl status rq-worker@1
```

### Worker Scaling Guidelines

| Workload | Workers | CPU | RAM |
|----------|---------|-----|-----|
| Light (< 100 jobs/day) | 2 | 1 vCPU | 512MB |
| Medium (100-1000 jobs/day) | 4 | 2 vCPU | 2GB |
| Heavy (1000+ jobs/day) | 8+ | 4+ vCPU | 4GB+ |

### Monitoring Workers

```bash
# Monitor worker activity
rq info --url $REDIS_URL

# Output:
default       |██████████████████ 523
0 workers, 0 queues

# Monitor job failures
rq info --url $REDIS_URL --only-failures
```

---

## Frontend Deployment

⚠️ **IMPORTANT**: The `static/` directory contains **pre-built, checked-in assets**. Do NOT delete this directory.

### Current Deployment Workflow (Demo Mode)

**Status**: Frontend assets are **manually built** and **committed to the repository**.

**To Deploy**:
```bash
# Simply start the server - static assets are already in place
bash start.sh
```

The FastAPI backend automatically serves the frontend from `/static`:

```python
# In app/main.py
app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

### Frontend Development Workflow

If you need to make changes to the frontend:

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (first time only)
npm install

# Build for production
npm run build
```

Expected output:
```
vite v5.0.0 building for production...
✓ 1234 modules transformed.
dist/index.html                   0.45 kB
dist/assets/index-BSbhE7iQ.css   12.34 kB │ gzip: 3.45 kB
dist/assets/index-OM46INTd.js   234.56 kB │ gzip: 78.90 kB
✓ built in 15.32s
```

**Copy built assets to static directory** (manual for now):
```bash
# ⚠️ WARNING: Do NOT use 'rm -rf static' - it deletes checked-in assets!
# Instead, copy only the new files:
cp -r frontend/dist/* static/
```

**Guardrails**:
- ❌ **NEVER** run `rm -rf static/` - this deletes committed assets
- ✅ **DO** use `cp -r frontend/dist/* static/` to update files
- ✅ **DO** commit updated `static/` assets to version control
- ⚠️ Manual build/copy workflow is temporary - CI/CD automation is planned

### Verify Frontend

```bash
# Start server
bash start.sh

# Or manually:
# python3 -m uvicorn app.main:app --host 0.0.0.0 --port 5000

# Test in browser
open http://localhost:5000
```

---

## Health Checks

### Application Health Endpoint

```bash
# Check backend health
curl http://localhost:5000/api/v1/health

# Expected response
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-11-18T12:00:00Z"
}
```

### Database Health Check

```bash
# Check PostgreSQL connection
python3 << EOF
from app.database import engine
try:
    with engine.connect() as conn:
        conn.execute("SELECT 1")
    print("✅ Database connection healthy")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
EOF
```

### Redis Health Check

```bash
# Check Redis connection
redis-cli -u $REDIS_URL ping

# Expected output
PONG
```

### Kubernetes Readiness Probe

```yaml
readinessProbe:
  httpGet:
    path: /api/v1/health
    port: 5000
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3
```

### Kubernetes Liveness Probe

```yaml
livenessProbe:
  httpGet:
    path: /api/v1/health
    port: 5000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

---

## Reverse Proxy Configuration

### Nginx Configuration

Create `/etc/nginx/sites-available/autonomos`:

```nginx
upstream autonomos_backend {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy settings
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # WebSocket support
    location /dcl {
        proxy_pass http://autonomos_backend;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    location /api/v1/events/stream {
        proxy_pass http://autonomos_backend;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
    }

    # API routes
    location /api/ {
        proxy_pass http://autonomos_backend;
        proxy_read_timeout 60s;
    }

    # Static files
    location / {
        proxy_pass http://autonomos_backend;
        proxy_cache_valid 200 1d;
        proxy_cache_use_stale error timeout invalid_header updating;
    }

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json;
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/autonomos /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Caddy Configuration (Alternative)

Create `Caddyfile`:

```caddyfile
your-domain.com {
    reverse_proxy localhost:5000
    
    # WebSocket support
    @websockets {
        path /dcl
        path /api/v1/events/stream
    }
    reverse_proxy @websockets localhost:5000 {
        header_up Connection "Upgrade"
        header_up Upgrade "websocket"
    }
    
    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
    }
    
    # Gzip compression
    encode gzip
    
    # TLS (automatic with Let's Encrypt)
    tls {
        protocols tls1.2 tls1.3
    }
}
```

Start Caddy:

```bash
sudo caddy run --config Caddyfile
```

---

## SSL/TLS Certificate Setup

### Let's Encrypt (Free, Recommended)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Test automatic renewal
sudo certbot renew --dry-run
```

### Self-Signed Certificate (Development)

```bash
# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/autonomos.key \
  -out /etc/ssl/certs/autonomos.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=your-domain.com"
```

---

## Production Checklist

### Pre-Deployment

- [ ] All `.env` variables are set correctly
- [ ] `DCL_AUTH_ENABLED=true` in production
- [ ] Strong JWT secret (32+ characters)
- [ ] Database migrations run successfully (`alembic upgrade head`)
- [ ] Redis connection verified
- [ ] SSL/TLS certificates installed
- [ ] Reverse proxy configured
- [ ] Frontend built and copied to `static/`
- [ ] Health checks passing

### Post-Deployment

- [ ] Application accessible via HTTPS
- [ ] WebSocket connections working (`/dcl`)
- [ ] Server-Sent Events working (`/api/v1/events/stream`)
- [ ] User registration working
- [ ] JWT authentication working
- [ ] DCL views returning data
- [ ] AAM connectors operational
- [ ] Bulk mapping jobs processing
- [ ] RQ workers running
- [ ] Logs being written correctly

### Security Hardening

- [ ] Firewall configured (allow only 80, 443, 22)
- [ ] SSH key-based authentication enabled
- [ ] Fail2ban installed and configured
- [ ] Database user has minimal permissions
- [ ] Redis password authentication enabled
- [ ] Secrets stored in environment variables (not code)
- [ ] CORS restricted to known origins
- [ ] Rate limiting enabled
- [ ] Audit logging enabled

### Monitoring & Alerting

- [ ] Prometheus metrics endpoint exposed (`/metrics`)
- [ ] Grafana dashboards configured
- [ ] Alerting rules configured (see Observability Runbook)
- [ ] Log aggregation setup (Loki, CloudWatch, etc.)
- [ ] Uptime monitoring (UptimeRobot, Pingdom)
- [ ] Error tracking (Sentry, Rollbar)

### Backup & Recovery

- [ ] Database backups automated (daily)
- [ ] Redis persistence enabled (AOF + RDB)
- [ ] Backup restoration tested
- [ ] Disaster recovery plan documented

---

## Troubleshooting

### Application Won't Start

```bash
# Check logs
journalctl -u autonomos.service -f

# Common issues:
# 1. Missing environment variables - check manually
env | grep -E "DATABASE_URL|JWT_SECRET_KEY|REDIS_URL|GOOGLE_API_KEY"

# 2. Database connection failed
psql $SUPABASE_DB_URL -c "SELECT 1"

# 3. Redis connection failed
redis-cli -u $REDIS_URL ping
```

### Workers Not Processing Jobs

```bash
# Check worker status
rq info --url $REDIS_URL

# Restart workers
sudo systemctl restart rq-worker@{1..4}

# Check for job failures
rq info --url $REDIS_URL --only-failures
```

### Frontend Not Loading

```bash
# Check if static files exist
ls -la static/

# Rebuild frontend
cd frontend && npm run build && cd ..
cp -r frontend/dist/* static/
```

---

## 📋 Planned Features

This appendix documents deployment-related features currently in development or planned for future releases.

### Deployment Automation (v1.5 - Q1 2025)

**CI/CD Pipeline**:
- [ ] Automated frontend build pipeline (GitHub Actions/GitLab CI)
- [ ] Automated static asset deployment (`frontend/dist` → `static/`)
- [ ] Pre-deployment validation (linting, type checking, tests)
- [ ] Automated database migration testing before production deployment
- [ ] Blue-green deployment support for zero-downtime updates
- [ ] Automated rollback procedures on deployment failure
- [ ] Container registry integration (Docker Hub, ECR, GCR)
- [ ] Performance regression testing in CI pipeline

**Current Status**: Frontend assets are manually built and committed to `static/` directory. Deployments require manual steps (build, copy, commit). Full CI/CD automation is planned for v1.5.

---

### Infrastructure as Code (v1.5 - Q1 2025)

**Terraform/Pulumi Configuration**:
- [ ] IaC templates for AWS/GCP/Azure provisioning
- [ ] Kubernetes Helm charts for orchestration
- [ ] Automated infrastructure provisioning (VPC, RDS, ElastiCache)
- [ ] Environment replication (staging, production, DR)
- [ ] Secret management automation (AWS Secrets Manager, Vault)
- [ ] Load balancer and DNS configuration (Route53, CloudFlare)

**Current Status**: Manual infrastructure setup. See this guide for manual deployment steps.

---

### Observability & Monitoring (v1.5 - Q1 2025)

**Enhanced Monitoring**:
- [ ] Prometheus metrics endpoint (`/metrics`) with custom metrics
- [ ] Pre-built Grafana dashboards for key metrics
- [ ] Distributed tracing (Jaeger, OpenTelemetry)
- [ ] Log aggregation (Loki, CloudWatch, Datadog)
- [ ] Custom alerting rules (PagerDuty, Slack, email)
- [ ] Error tracking integration (Sentry, Rollbar)
- [ ] SLA/SLO monitoring and reporting
- [ ] Cost optimization insights and recommendations

**Current Status**: Basic health checks available (`/api/v1/health`). Advanced observability stack is planned.

---

### Security Enhancements (v2.0 - Q2 2025)

**Production Hardening**:
- [ ] WAF (Web Application Firewall) configuration
- [ ] DDoS protection (CloudFlare, AWS Shield)
- [ ] Automated security scanning (Snyk, Trivy, OWASP ZAP)
- [ ] Secrets rotation automation
- [ ] Compliance reporting (SOC2, HIPAA, GDPR)
- [ ] Intrusion detection systems (IDS)
- [ ] Automated vulnerability patching
- [ ] Security audit logging and SIEM integration

**Current Status**: Demo mode with `DCL_AUTH_ENABLED=false`. Production security features require enabling authentication and implementing additional hardening measures.

---

### Scalability & Performance (v2.0 - Q2 2025)

**Auto-Scaling & Optimization**:
- [ ] Horizontal auto-scaling (HPA for Kubernetes, ASG for AWS)
- [ ] Database connection pooling (PgBouncer)
- [ ] Query result caching (Redis-backed)
- [ ] CDN integration for static assets (CloudFront, Fastly)
- [ ] Database read replicas for query distribution
- [ ] Materialized view refresh optimization
- [ ] Background job queue optimization (RQ → Celery)
- [ ] Rate limiting per tenant (Redis-based)

**Current Status**: Single-instance deployment. Scalability features planned for high-traffic production environments.

---

### Backup & Recovery (v1.5 - Q1 2025)

**Disaster Recovery**:
- [ ] Automated database backups with retention policies
- [ ] Point-in-time recovery (PITR) for PostgreSQL
- [ ] Redis persistence (AOF + RDB) with automated backups
- [ ] Cross-region backup replication
- [ ] Automated backup restoration testing
- [ ] Disaster recovery runbooks and playbooks
- [ ] RTO/RPO monitoring and compliance

**Current Status**: Manual backup procedures. Automated backup/recovery systems are planned.

---

### Timeline & Roadmap

| Feature | Target Release | Status |
|---------|---------------|--------|
| Automated CI/CD Pipeline | v1.5 (Q1 2025) | Planned |
| Infrastructure as Code | v1.5 (Q1 2025) | Planned |
| Enhanced Observability | v1.5 (Q1 2025) | Planned |
| Backup & Recovery Automation | v1.5 (Q1 2025) | Planned |
| Production Security Hardening | v2.0 (Q2 2025) | Planned |
| Auto-Scaling & Performance | v2.0 (Q2 2025) | Planned |

For the latest roadmap updates, see `PLAN.md` in the repository root.

---

## Support

For deployment support:
- **Documentation:** See `/docs` directory
- **Issues:** File bug reports with deployment logs
- **Production Incidents:** Follow Incident Response in OPERATIONAL_PROCEDURES.md
