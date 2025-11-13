# Complete Environment Variables Reference for AutonomOS

This document lists ALL environment variables used across the AutonomOS platform.

## 📋 Quick Reference

```bash
# Generate random secrets
openssl rand -hex 32  # For SECRET_KEY, JWT_SECRET_KEY, API_KEY
```

---

## 🔴 REQUIRED Variables

These variables are **mandatory** for the application to start.

### Database
```bash
DATABASE_URL=postgresql://user:password@host:5432/dbname
# PostgreSQL connection string
# Format: postgresql://[user[:password]@][host][:port][/dbname]
# Example: postgresql://postgres:mypass@localhost:5432/autonomos
```

### Redis
```bash
REDIS_URL=redis://host:6379/0
# Redis connection string (required for task queue and caching)
# Format: redis://[password@]host[:port][/db]
# Example: redis://localhost:6379/0
# For Upstash: redis://default:password@us1-xxx.upstash.io:6379
```

### Security
```bash
SECRET_KEY=your-secret-key-min-32-characters-long
# JWT signing secret (MUST be 32+ characters)
# Generate with: openssl rand -hex 32
# Used for JWT token encryption and session security
```

---

## 🔵 LLM/AI Provider Keys (at least one required)

The platform requires at least one LLM provider for AI features.

### Google Gemini (Recommended)
```bash
GEMINI_API_KEY=AIzaSy...
# Google Gemini API key for AI-powered schema mapping
# Get from: https://makersuite.google.com/app/apikey
# Used by: DCL Engine, Schema Mapper, Ontology Mapping
```

### OpenAI (Alternative)
```bash
OPENAI_API_KEY=sk-proj-...
# OpenAI API key (alternative to Gemini)
# Get from: https://platform.openai.com/api-keys
# Used for: LLM-based schema proposals
```

### Pinecone (For RAG Features)
```bash
PINECONE_API_KEY=pcsk_...
# Pinecone vector database API key
# Get from: https://app.pinecone.io/
# Used for: RAG-powered schema mapping, embeddings storage

PINECONE_ENVIRONMENT=us-west1-gcp
# Pinecone environment/region
# Options: us-west1-gcp, us-east-1-aws, etc.

PINECONE_INDEX=schema-mappings-e5
# Pinecone index name
# Default: schema-mappings-e5
# Must be created before use
```

---

## 🟢 Optional - Authentication & Security

```bash
JWT_SECRET_KEY=your-jwt-secret-32-chars-minimum
# JWT signing key (defaults to SECRET_KEY if not set)
# Generate with: openssl rand -hex 32

JWT_EXPIRE_MINUTES=30
# JWT token expiration time in minutes
# Default: 30
# Range: 5-1440 (1 day max recommended)

JWT_ISSUER=autonomos.dev
# JWT token issuer claim
# Default: autonomos.dev

JWT_AUDIENCE=aos.agents
# JWT token audience claim
# Default: aos.agents

API_KEY=your-api-key-32-characters-minimum
# API key for service-to-service authentication
# Generate with: openssl rand -hex 32
```

---

## 🟢 Optional - Application Configuration

### Server
```bash
PORT=5000
# HTTP server port
# Default: 5000
# Render uses: 10000

ALLOWED_WEB_ORIGIN=http://localhost:3000
# CORS allowed origin for frontend
# Default: http://localhost:3000
# Production: https://your-domain.com

ENVIRONMENT=production
# Environment identifier
# Options: production, preview, development
# Default: production
```

### Feature Flags
```bash
FEATURE_USE_FILESOURCE=true
# Enable FileSource CSV connector
# Default: true
# Values: true, false

FEATURE_DRIFT_AUTOFIX=false
# Enable automatic drift repair (>=0.85 confidence)
# Default: false
# Values: true, false

MONITOR_POLLING=false
# Enable AAM monitoring dashboard polling
# Default: false
# Values: true, false

DEV_DEBUG=false
# Enable debug mode with verbose logging
# Default: false
# ⚠️ DO NOT use in production

REQUIRED_SOURCES=salesforce,supabase,mongodb,filesource
# Comma-separated list of required data sources
# Default: salesforce,supabase,mongodb,filesource
```

### Event Streaming
```bash
EVENT_STREAM_ENABLED=true
# Enable Server-Sent Events (SSE) for real-time updates
# Default: true

EVENT_STREAM_HEARTBEAT_MS=15000
# SSE heartbeat interval in milliseconds
# Default: 15000 (15 seconds)
```

### DCL Engine
```bash
DCL_DEV_MODE=false
# Enable DCL development mode (uses AI/RAG for mapping)
# Default: false (uses heuristics only - faster)
# Values: true, false

DCL_REGISTRY_PATH=./app/dcl_engine/registry.duckdb
# DuckDB registry database path
# Default: ./app/dcl_engine/registry.duckdb
```

---

## 🟢 Optional - External Integrations

### Slack Notifications
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
# Slack incoming webhook URL for notifications
# Get from: https://api.slack.com/messaging/webhooks
# Used for: Task completion notifications, alerts
```

### Legacy DCL Backend (AOD)
```bash
AOD_BASE_URL=http://localhost:8000
# AOS Discover service (AOD) base URL
# Default: http://localhost:8000
# Used for: Legacy DCL proxy mode
```

---

## 🟢 Optional - AAM Hybrid Services

### Service Ports
```bash
ORCHESTRATOR_PORT=8001
ORCHESTRATOR_URL=http://localhost:8001
# AAM Orchestrator service endpoint

DRIFT_REPAIR_PORT=8003
DRIFT_REPAIR_URL=http://localhost:8003
# Drift Repair Agent endpoint

SCHEMA_OBSERVER_PORT=8004
SCHEMA_OBSERVER_URL=http://localhost:8004
# Schema Observer service endpoint

RAG_ENGINE_PORT=8005
RAG_ENGINE_URL=http://localhost:8005
# RAG Engine service endpoint
```

### Drift Detection
```bash
DRIFT_REPAIR_CONFIDENCE_THRESHOLD=0.85
# Minimum confidence score for automatic drift repair
# Default: 0.85 (85%)
# Range: 0.0-1.0

AAM_BATCH_CHUNK_SIZE=100
# Batch size for AAM data processing
# Default: 100

AAM_MAX_SAMPLES_PER_TABLE=1000
# Maximum samples per table for schema analysis
# Default: 1000

AAM_REDIS_STREAM_MAXLEN=10000
# Redis stream max length for AAM events
# Default: 10000

AAM_IDEMPOTENCY_TTL=3600
# Idempotency key TTL in seconds
# Default: 3600 (1 hour)

AAM_CONNECTORS_SYNC=true
# Enable AAM connectors synchronization
# Default: true
```

---

## 🟢 Optional - Data Source Connectors

### Supabase (PostgreSQL)
```bash
SUPABASE_DB_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres
# Supabase PostgreSQL connection string
# Get from: Supabase Dashboard → Settings → Database
# Format: postgresql://postgres:[password]@[host]:5432/postgres

SUPABASE_URL=https://xxx.supabase.co
# Supabase project URL
# Get from: Supabase Dashboard → Settings → API

SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
# Supabase anonymous key
# Get from: Supabase Dashboard → Settings → API

SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
# Supabase service role key (admin access)
# Get from: Supabase Dashboard → Settings → API
# ⚠️ Keep this secret!

SUPABASE_SCHEMA=public
# Database schema to use
# Default: public
```

### MongoDB
```bash
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/dbname?retryWrites=true&w=majority
# MongoDB connection URI (Atlas or self-hosted)
# Get from: MongoDB Atlas → Connect → Connect your application
# Format: mongodb+srv://[user]:[password]@[cluster]/[database]

MONGODB_DB=autonomos
# MongoDB database name
# Default: autonomos
```

### Salesforce
```bash
SALESFORCE_CLIENT_ID=3MVG9...
# Salesforce Connected App Client ID
# Get from: Salesforce Setup → App Manager → Connected App

SALESFORCE_CLIENT_SECRET=ABC123...
# Salesforce Connected App Client Secret
# Get from: Salesforce Setup → App Manager → Connected App

SALESFORCE_REFRESH_TOKEN=5Aep861...
# Salesforce OAuth refresh token (never expires unless revoked)
# Get from: OAuth 2.0 Web Server Flow
# Used for: Automated authentication without user login

SALESFORCE_ACCESS_TOKEN=00D...
# Salesforce OAuth access token (temporary, refreshes automatically)
# Usually auto-generated from refresh token

SALESFORCE_INSTANCE_URL=https://yourinstance.my.salesforce.com
# Salesforce instance URL
# Example: https://na1.salesforce.com or https://yourcompany.my.salesforce.com
```

---

## 🟢 Optional - Airbyte Integration

```bash
AIRBYTE_API_URL=http://localhost:8000/api/public/v1
# Airbyte API endpoint
# Default: http://localhost:8000/api/public/v1
# For Airbyte Cloud: https://api.airbyte.com/v1

AIRBYTE_CLIENT_ID=your-client-id-here
# Airbyte OAuth client ID
# Get from: abctl local credentials

AIRBYTE_CLIENT_SECRET=your-client-secret-here
# Airbyte OAuth client secret
# Get from: abctl local credentials

AIRBYTE_WORKSPACE_ID=your-workspace-id-here
# Airbyte workspace UUID
# Get from: Airbyte UI after creating workspace

AIRBYTE_DESTINATION_ID=your-destination-id-here
# Airbyte destination UUID for data sync
# Get from: Airbyte UI after creating destination

AIRBYTE_USE_OSS=false
# Use Airbyte OSS (self-hosted) instead of Cloud
# Default: false
# Values: true, false
```

---

## 🟢 Optional - Gateway & Rate Limiting

```bash
RATE_LIMIT_RPM=60
# Rate limit: requests per minute per tenant
# Default: 60

RATE_LIMIT_BURST=10
# Rate limit: burst allowance
# Default: 10

IDEMPOTENCY_CACHE_MINUTES=10
# Idempotency key cache duration in minutes
# Default: 10

BUILD_SHA=local-dev
# Build SHA for health endpoint (auto-generated in CI/CD)
# Default: local-dev
```

---

## 🟢 Optional - Multi-Tenant Configuration

```bash
TENANT_ID_DEMO=demo-tenant
# Demo tenant ID for testing
# Default: demo-tenant

DEMO_TENANT_UUID=550e8400-e29b-41d4-a716-446655440000
# Demo tenant UUID
# Must be valid UUID v4

AOS_DEMO_MODE=false
# Enable demo mode with sample data
# Default: false
```

---

## 🟢 Optional - Logging & Debugging

```bash
LOG_LEVEL=INFO
# Logging level
# Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
# Default: INFO

LOG_FORMAT=json
# Log output format
# Options: json, text
# Default: json

DEBUG=false
# Enable debug mode
# Default: false
# ⚠️ DO NOT use in production

VERBOSE=false
# Enable verbose logging
# Default: false
```

---

## 🟢 Optional - Database Configuration (Alternative Format)

```bash
POSTGRES_URL=postgresql://user:password@localhost:5432/autonomos
# Alternative to DATABASE_URL
# Some configurations use this instead

POSTGRES_USER=your_db_user
# PostgreSQL username (used in Docker Compose)

POSTGRES_PASSWORD=your_db_password
# PostgreSQL password (used in Docker Compose)

POSTGRES_DB=autonomos
# PostgreSQL database name (used in Docker Compose)
```

---

## 🟢 Optional - Redis Configuration (Alternative Format)

```bash
REDIS_HOST=localhost
# Redis server hostname
# Default: localhost

REDIS_PORT=6379
# Redis server port
# Default: 6379

REDIS_DB=0
# Redis database number
# Default: 0
# Range: 0-15
```

---

## 🟢 Optional - Testing Configuration

```bash
TEST_DATABASE_URL=postgresql://postgres:test@localhost:5432/autonomos_test
# Test database connection string
# Used for: pytest, integration tests

TEST_BASE_URL=http://localhost:5001
# Test server base URL
# Used for: functional tests, smoke tests

NODE_ENV=test
# Node environment for frontend tests
# Options: development, test, production
```

---

## 🟢 Optional - Deployment & CI/CD

```bash
REPL_OWNER=username
# Replit owner username (auto-set on Replit)

REPL_SLUG=autonomos-platform
# Replit project slug (auto-set on Replit)

DISABLE_AUTO_MIGRATIONS=false
# Disable automatic Alembic migrations on startup
# Default: false
# Values: true, false
# Use case: Manual migration control in production

ENCRYPTION_KEY=your-encryption-key-32-bytes
# Encryption key for sensitive data at rest
# Generate with: openssl rand -hex 32
```

---

## 📝 Environment-Specific Examples

### Local Development (.env)
```bash
DATABASE_URL=postgresql://postgres:password@localhost:5432/autonomos
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=$(openssl rand -hex 32)
GEMINI_API_KEY=your_gemini_key
PINECONE_API_KEY=your_pinecone_key
ALLOWED_WEB_ORIGIN=http://localhost:3000
DEV_DEBUG=true
DCL_DEV_MODE=false
FEATURE_USE_FILESOURCE=true
PORT=5000
```

### Render Production
```bash
DATABASE_URL=postgresql://user:pass@host:5432/db  # Auto-set by Render
REDIS_URL=redis://default:pass@host:6379  # From Upstash
SECRET_KEY=auto_generated_32_chars
API_KEY=auto_generated_32_chars
GEMINI_API_KEY=your_key_from_secrets
PINECONE_API_KEY=your_key_from_secrets
ALLOWED_WEB_ORIGIN=https://autonomos-platform.onrender.com
ENVIRONMENT=production
PORT=10000
DCL_DEV_MODE=false
FEATURE_USE_FILESOURCE=true
REQUIRED_SOURCES=salesforce,supabase,mongodb,filesource
```

### Render Preview
```bash
DATABASE_URL=auto_from_autonomos-db-preview
REDIS_URL=auto_from_autonomos-redis-preview
SECRET_KEY=auto_generated_unique_per_preview
API_KEY=auto_generated_unique_per_preview
GEMINI_API_KEY=synced_from_production
PINECONE_API_KEY=synced_from_production
ALLOWED_WEB_ORIGIN=auto_from_render_external_url
ENVIRONMENT=preview
PORT=10000
DISABLE_AUTO_MIGRATIONS=false
```

### Docker Compose
```bash
POSTGRES_USER=autonomos_user
POSTGRES_PASSWORD=autonomos_pass
POSTGRES_DB=autonomos
DATABASE_URL=postgresql://autonomos_user:autonomos_pass@db:5432/autonomos
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_URL=redis://redis:6379/0
SECRET_KEY=$(openssl rand -hex 32)
GEMINI_API_KEY=${GEMINI_API_KEY}
PORT=5000
```

---

## 🔍 How to Find Missing Variables

If you get errors about missing environment variables:

1. **Check application logs** for error messages like:
   ```
   ValueError: DATABASE_URL environment variable is required
   ```

2. **Run validation script**:
   ```bash
   python -c "from app.config import settings; print('Config valid!')"
   ```

3. **Check which variables are currently set**:
   ```bash
   env | grep -E "^(DATABASE|REDIS|GEMINI|SECRET|API)" | sort
   ```

4. **Compare against this document** to find missing required variables

---

## 📚 Additional Resources

- **Main README**: `README.md`
- **Render Deployment**: `RENDER_DEPLOYMENT_GUIDE.md`
- **Preview Deployments**: `PREVIEW_DEPLOYMENT_GUIDE.md`
- **AAM Configuration**: `aam_hybrid/README-CONFIGURATION.md`
- **Architecture**: `ARCHITECTURE.md`

---

## 🆘 Troubleshooting

### "DATABASE_URL environment variable is required"
- **Solution**: Set `DATABASE_URL` in environment or .env file
- **Format**: `postgresql://user:password@host:5432/database`

### "SECRET_KEY environment variable is required"
- **Solution**: Generate and set: `export SECRET_KEY=$(openssl rand -hex 32)`

### "Error connecting to Redis"
- **Solution**: Check `REDIS_URL` is set correctly
- **Test**: `redis-cli -u $REDIS_URL ping`

### "GEMINI_API_KEY not set"
- **Solution**: Get API key from https://makersuite.google.com/app/apikey
- **Alternative**: Use `OPENAI_API_KEY` instead

### DCL connections are slow (>10 seconds)
- **Solution**: Ensure `DCL_DEV_MODE=false` (uses heuristics, not AI)
- **Check**: Look for "dev_mode = false" in logs

---

**Last Updated**: November 2025
**Total Variables**: 80+
**Required**: 3 (DATABASE_URL, REDIS_URL, SECRET_KEY)
**LLM Required**: 1+ (GEMINI_API_KEY or OPENAI_API_KEY)
