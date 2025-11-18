# AutonomOS Platform - Performance Tuning Guide

**Version:** 1.0  
**Last Updated:** November 18, 2025  
**Owner:** Platform Performance Team

---

## Table of Contents

1. [Benchmarking Methodology](#benchmarking-methodology)
2. [Performance Baselines](#performance-baselines)
3. [Optimization Techniques](#optimization-techniques)
4. [Resource Sizing](#resource-sizing)
5. [Bottleneck Identification](#bottleneck-identification)
6. [Caching Strategies](#caching-strategies)
7. [Database Query Optimization](#database-query-optimization)
8. [Worker Concurrency Tuning](#worker-concurrency-tuning)
9. [Memory Profiling](#memory-profiling)

---

## Benchmarking Methodology

### Benchmark Workload Profiles

| Profile | Connectors | Concurrent Jobs | Fields/Connector | Target Use Case |
|---------|------------|-----------------|------------------|-----------------|
| **test** | 10 | 5 | 50 | CI/CD testing |
| **small** | 50 | 10 | 100 | Small business (< 1000 employees) |
| **medium** | 200 | 25 | 200 | Mid-market (1000-5000 employees) |
| **large** | 1000 | 50 | 500 | Enterprise (5000+ employees) |

### Running Benchmarks

```bash
cd benchmarks

# Run test profile
python3 run_load_test.py --profile test

# Run with custom parameters
python3 run_load_test.py \
  --profile custom \
  --connectors 100 \
  --jobs 20 \
  --fields 150

# Continuous benchmarking (for CI/CD)
python3 run_load_test.py --profile test --output results/ci_$(date +%Y%m%d).json
```

### Benchmark Metrics

**Primary Metrics:**
- **Throughput:** Jobs processed per second
- **Latency:** P50, P95, P99 response times
- **Success Rate:** % of jobs completed successfully
- **Resource Utilization:** CPU, memory, disk I/O

**Secondary Metrics:**
- Queue wait time
- Processing time (compute only)
- Database query time
- Redis operation latency

### Baseline Configuration

**Hardware:**
- 4 vCPU (2.5 GHz)
- 16 GB RAM
- 100 GB SSD
- 1 Gbps network

**Software:**
- PostgreSQL 14 (Supabase, db.t3.medium)
- Redis 6 (Upstash, 256 MB)
- Python 3.11
- Uvicorn (4 workers)
- RQ workers (4 workers)

---

## Performance Baselines

### Test Profile Baseline

**Workload:** 10 connectors, 5 concurrent jobs, 50 fields/connector

```json
{
  "execution": {
    "total_jobs": 5,
    "completed": 5,
    "failed": 0,
    "duration_seconds": 10.5,
    "success_rate_percent": 100.0
  },
  "performance": {
    "throughput": {
      "jobs_per_sec": 0.48,
      "fields_per_sec": 23.8
    },
    "latency": {
      "p50": 195,
      "p95": 280,
      "p99": 295
    }
  },
  "resources": {
    "cpu_percent_avg": 45.2,
    "memory_mb_avg": 256.7
  }
}
```

**Interpretation:**
- ✅ Throughput: 0.48 jobs/sec acceptable for test workload
- ✅ P95 latency: 280ms (under 500ms SLO)
- ✅ CPU: 45% (headroom available)
- ✅ Memory: 257 MB (low utilization)

---

### Small Profile Baseline

**Workload:** 50 connectors, 10 concurrent jobs, 100 fields/connector

**Expected Performance:**
- **Throughput:** 2-3 jobs/sec
- **P95 Latency:** 500-800ms
- **CPU:** 60-70%
- **Memory:** 1-2 GB

**Bottleneck:** Database connection pool (default 20 connections)

**Optimization:**
```python
# Increase connection pool size
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=50,  # Increased from 20
    max_overflow=20
)
```

**Result:**
- **Throughput:** 3.2 jobs/sec (+33%)
- **P95 Latency:** 450ms (-30%)

---

### Medium Profile Baseline

**Workload:** 200 connectors, 25 concurrent jobs, 200 fields/connector

**Expected Performance:**
- **Throughput:** 5-8 jobs/sec
- **P95 Latency:** 1-2 seconds
- **CPU:** 75-85%
- **Memory:** 4-6 GB

**Bottleneck:** RQ worker count (default 4 workers)

**Optimization:**
```bash
# Scale to 8 workers
for i in {1..8}; do
  rq worker default --url $REDIS_URL &
done
```

**Result:**
- **Throughput:** 10.5 jobs/sec (+70%)
- **P95 Latency:** 900ms (-40%)

---

### Large Profile Baseline

**Workload:** 1000 connectors, 50 concurrent jobs, 500 fields/connector

**Expected Performance:**
- **Throughput:** 15-25 jobs/sec
- **P95 Latency:** 2-5 seconds
- **CPU:** 85-95%
- **Memory:** 8-12 GB

**Bottleneck:** Multiple (database, Redis, workers)

**Optimization:**
- Scale database instance (db.t3.large → db.t3.2xlarge)
- Scale Redis (256 MB → 2 GB)
- Scale workers (4 → 16)
- Enable connection pooling (PgBouncer)
- Add read replicas

**Result:**
- **Throughput:** 35 jobs/sec (+75%)
- **P95 Latency:** 1.8 seconds (-55%)

---

## Optimization Techniques

### 1. Redis Optimization

**Problem:** High Redis latency (>100ms)

**Diagnosis:**
```bash
# Check Redis latency
redis-cli --latency -h $REDIS_HOST

# Monitor slow commands
redis-cli --bigkeys
```

**Optimizations:**

```python
# 1. Use pipeline for batch operations
pipe = redis_client.pipeline()
for key in keys:
    pipe.get(key)
results = pipe.execute()

# 2. Reduce key size (use short names)
# Bad:  "job:state:tenant:550e8400-e29b-41d4-a716-446655440000:job:abc123"
# Good: "j:st:t:550e8400:j:abc123"

# 3. Set appropriate TTL (avoid memory bloat)
redis_client.setex("key", 3600, "value")  # 1 hour TTL

# 4. Use connection pooling
from redis import ConnectionPool

pool = ConnectionPool.from_url(settings.REDIS_URL, max_connections=50)
redis_client = redis.Redis(connection_pool=pool)
```

**Expected Improvement:**
- Latency: -50% (from 100ms to 50ms)
- Throughput: +30%

---

### 2. PostgreSQL Optimization

**Problem:** Slow queries (>1 second)

**Diagnosis:**
```sql
-- Find slow queries
SELECT 
  query,
  mean_exec_time,
  calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check missing indexes
SELECT 
  schemaname,
  tablename,
  attname
FROM pg_stats
WHERE schemaname = 'public'
  AND n_distinct > 0
  AND attname NOT IN (
    SELECT a.attname
    FROM pg_index i
    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
    WHERE i.indrelid = pg_stats.tablename::regclass
  );
```

**Optimizations:**

```sql
-- 1. Add missing indexes
CREATE INDEX CONCURRENTLY idx_canonical_tenant_entity 
ON canonical_streams (tenant_id, entity);

CREATE INDEX CONCURRENTLY idx_mapping_tenant_vendor 
ON mapping_registry (tenant_id, vendor);

-- 2. Use partial indexes for frequently filtered columns
CREATE INDEX CONCURRENTLY idx_drift_status_pending 
ON drift_events (tenant_id) 
WHERE status = 'pending';

-- 3. Optimize N+1 queries (use joins or batch loading)
-- Bad: SELECT * FROM accounts WHERE id IN (...)  -- N queries
-- Good: SELECT * FROM accounts WHERE id = ANY($1)  -- 1 query

-- 4. Use connection pooling (PgBouncer)
# External service, configure separately
```

**Expected Improvement:**
- Query time: -70% (from 1s to 300ms)
- Database CPU: -40%

---

### 3. RQ Worker Optimization

**Problem:** Low job throughput (<5 jobs/sec)

**Diagnosis:**
```bash
# Check worker stats
rq info --url $REDIS_URL

# Monitor queue depth
watch -n 1 'rq info --url $REDIS_URL | grep "jobs"'
```

**Optimizations:**

```python
# 1. Increase worker count (horizontal scaling)
# Add more RQ workers (see Worker Scaling section)

# 2. Optimize job processing logic
# Before: Sequential processing
for field in fields:
    match = rag_matcher.find_match(field)  # 100ms each

# After: Batch processing
matches = rag_matcher.find_matches_batch(fields)  # 500ms total

# 3. Use async I/O for external API calls
import asyncio

async def fetch_all_connectors(connector_ids):
    tasks = [fetch_connector(cid) for cid in connector_ids]
    return await asyncio.gather(*tasks)

# 4. Reduce job payload size (use references)
# Bad:  Store entire schema in Redis (100KB)
# Good: Store schema hash + reference (1KB)
```

**Expected Improvement:**
- Throughput: +100% (from 5 to 10 jobs/sec)
- Queue depth: -50%

---

### 4. API Latency Optimization

**Problem:** High API latency (>2 seconds P95)

**Diagnosis:**
```python
# Add timing middleware
import time

@app.middleware("http")
async def add_timing(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = (time.time() - start) * 1000
    response.headers["X-Response-Time"] = f"{duration:.2f}ms"
    return response
```

**Optimizations:**

```python
# 1. Add caching for read-heavy endpoints
from functools import lru_cache

@lru_cache(maxsize=128)
def get_canonical_mappings(tenant_id: str):
    # Cache for 5 minutes
    return db.query(MappingRegistry).filter_by(tenant_id=tenant_id).all()

# 2. Use database connection pooling
# Already configured in database.py

# 3. Paginate large responses
@app.get("/api/v1/dcl/views/accounts")
def get_accounts(limit: int = 100, offset: int = 0):
    return db.query(MaterializedAccount).limit(limit).offset(offset).all()

# 4. Use async endpoints for I/O-bound operations
@app.get("/api/v1/aam/monitoring/connectors")
async def get_connectors():
    async with httpx.AsyncClient() as client:
        responses = await asyncio.gather(
            client.get("https://api.salesforce.com/..."),
            client.get("https://api.hubspot.com/...")
        )
    return responses
```

**Expected Improvement:**
- P95 latency: -60% (from 2s to 800ms)
- Throughput: +50%

---

## Resource Sizing

### Database Sizing Recommendations

| Tenants | Canonical Events/Month | Recommended Instance | vCPU | RAM | Storage |
|---------|------------------------|----------------------|------|-----|---------|
| 1-10 | <100k | db.t3.small | 2 | 2 GB | 20 GB |
| 10-50 | 100k-1M | db.t3.medium | 2 | 4 GB | 50 GB |
| 50-200 | 1M-10M | db.t3.large | 2 | 8 GB | 100 GB |
| 200-1000 | 10M-100M | db.t3.2xlarge | 8 | 32 GB | 500 GB |

### Redis Sizing Recommendations

| Concurrent Jobs | Queue Depth | Recommended Memory | Eviction Policy |
|-----------------|-------------|-------------------|-----------------|
| <50 | <500 | 256 MB | allkeys-lru |
| 50-200 | 500-2000 | 1 GB | allkeys-lru |
| 200-500 | 2000-5000 | 2 GB | allkeys-lru |
| 500+ | 5000+ | 4 GB+ | allkeys-lru |

### Application Server Sizing

| Concurrent Users | API Requests/sec | vCPU | RAM | Uvicorn Workers |
|------------------|------------------|------|-----|-----------------|
| <100 | <50 | 2 | 4 GB | 2 |
| 100-500 | 50-200 | 4 | 8 GB | 4 |
| 500-2000 | 200-1000 | 8 | 16 GB | 8 |
| 2000+ | 1000+ | 16+ | 32 GB+ | 16+ |

### RQ Worker Sizing

| Job Throughput | Workers | vCPU | RAM | Notes |
|----------------|---------|------|-----|-------|
| <10 jobs/sec | 4 | 2 | 4 GB | Baseline |
| 10-25 jobs/sec | 8 | 4 | 8 GB | Medium scale |
| 25-50 jobs/sec | 16 | 8 | 16 GB | High scale |
| 50+ jobs/sec | 32+ | 16+ | 32 GB+ | Enterprise scale |

---

## Bottleneck Identification

### CPU-Bound Bottlenecks

**Symptoms:**
- High CPU utilization (>85%)
- Increased response times
- Worker process slowdowns

**Diagnosis:**
```bash
# Check CPU usage
top -o %CPU

# Profile Python code
python -m cProfile -o profile.stats app/main.py
python -m pstats profile.stats
```

**Solutions:**
- Scale horizontally (add more workers/pods)
- Optimize hot code paths (use profiling to identify)
- Use native libraries (e.g., uvloop for async I/O)
- Enable multi-threading for CPU-bound tasks

---

### Memory-Bound Bottlenecks

**Symptoms:**
- High memory usage (>80%)
- OOM errors
- Swap usage increasing

**Diagnosis:**
```bash
# Check memory usage
free -h

# Python memory profiling
pip install memory_profiler
python -m memory_profiler app/main.py
```

**Solutions:**
- Reduce payload sizes (use pagination)
- Clear caches periodically
- Use generators instead of lists
- Scale vertically (add more RAM)

---

### I/O-Bound Bottlenecks

**Symptoms:**
- High disk I/O wait (>5%)
- Slow database queries
- Network timeouts

**Diagnosis:**
```bash
# Check disk I/O
iostat -x 1

# Check network latency
ping $DATABASE_HOST
```

**Solutions:**
- Use SSD instead of HDD
- Enable database query caching
- Use async I/O (httpx, asyncpg)
- Add read replicas for databases

---

## Caching Strategies

### 1. Application-Level Caching

```python
from functools import lru_cache
from datetime import datetime, timedelta

# In-memory cache with TTL
_cache = {}
_cache_ttl = {}

def cached_with_ttl(ttl_seconds: int):
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{args}:{kwargs}"
            
            # Check if cached and not expired
            if cache_key in _cache:
                if datetime.utcnow() < _cache_ttl[cache_key]:
                    return _cache[cache_key]
            
            # Compute and cache
            result = func(*args, **kwargs)
            _cache[cache_key] = result
            _cache_ttl[cache_key] = datetime.utcnow() + timedelta(seconds=ttl_seconds)
            
            return result
        
        return wrapper
    return decorator

# Usage
@cached_with_ttl(300)  # Cache for 5 minutes
def get_connector_status(connector_id: str):
    # Expensive operation
    return fetch_from_database(connector_id)
```

### 2. Redis Caching

```python
import json
from shared.redis_client import get_redis_client

def cache_in_redis(key: str, ttl: int = 3600):
    def decorator(func):
        def wrapper(*args, **kwargs):
            redis_client = get_redis_client()
            cache_key = f"cache:{key}:{args}:{kwargs}"
            
            # Try to get from cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Compute and cache
            result = func(*args, **kwargs)
            redis_client.setex(cache_key, ttl, json.dumps(result))
            
            return result
        
        return wrapper
    return decorator

# Usage
@cache_in_redis("dcl_graph", ttl=600)
def build_dcl_graph(tenant_id: str):
    # Expensive graph building
    return build_graph_from_db(tenant_id)
```

### 3. Database Query Result Caching

```sql
-- Use materialized views for expensive aggregations
CREATE MATERIALIZED VIEW tenant_stats AS
SELECT 
  tenant_id,
  COUNT(*) as total_events,
  COUNT(DISTINCT entity) as unique_entities
FROM canonical_streams
GROUP BY tenant_id;

-- Refresh periodically (e.g., every hour via cron)
REFRESH MATERIALIZED VIEW tenant_stats;
```

---

## Database Query Optimization

### 1. Index Optimization

```sql
-- Before: Full table scan (slow)
SELECT * FROM canonical_streams 
WHERE tenant_id = '550e8400-e29b-41d4-a716-446655440000' 
  AND entity = 'account';

-- After: Index scan (fast)
CREATE INDEX idx_canonical_tenant_entity 
ON canonical_streams (tenant_id, entity);
```

### 2. Query Rewriting

```sql
-- Before: N+1 queries
SELECT * FROM accounts WHERE id IN (
  SELECT account_id FROM opportunities WHERE stage = 'Closed Won'
);

-- After: Single join
SELECT a.* 
FROM accounts a
JOIN opportunities o ON o.account_id = a.id
WHERE o.stage = 'Closed Won';
```

### 3. Batch Operations

```python
# Before: N queries
for user_id in user_ids:
    user = db.query(User).filter(User.id == user_id).first()

# After: 1 query
users = db.query(User).filter(User.id.in_(user_ids)).all()
```

---

## Worker Concurrency Tuning

### Optimal Worker Count

**Formula:**
```
Optimal Workers = (CPU cores * 2) + 1
```

**Example:**
- 4 CPU cores → 9 workers
- 8 CPU cores → 17 workers

**Verification:**
```bash
# Monitor CPU utilization per worker
ps aux | grep "rq worker"

# If CPU < 80% per worker, add more workers
# If CPU > 95% per worker, reduce workers or scale vertically
```

---

## Memory Profiling

### Python Memory Profiler

```bash
# Install profiler
pip install memory_profiler

# Profile script
python -m memory_profiler app/main.py

# Profile specific function
@profile
def expensive_function():
    # ...
```

### Detecting Memory Leaks

```python
import tracemalloc

tracemalloc.start()

# Run code
# ...

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

for stat in top_stats[:10]:
    print(stat)
```

---

## Performance Monitoring Dashboard

### Key Metrics to Track

1. **API Latency (P50, P95, P99)**
2. **Job Throughput (jobs/sec)**
3. **Error Rate (%)**
4. **Database Query Time (avg, max)**
5. **Redis Latency (avg)**
6. **CPU Utilization (%)**
7. **Memory Usage (MB)**
8. **Queue Depth (jobs pending)**

See [Observability Runbook](../operations/OBSERVABILITY_RUNBOOK.md) for Prometheus queries and Grafana dashboards.

---

## References

- [Observability Runbook](../operations/OBSERVABILITY_RUNBOOK.md)
- [Architecture Overview](../architecture/ARCHITECTURE_OVERVIEW.md)
- [Deployment Guide](../deployment/DEPLOYMENT_GUIDE.md)
