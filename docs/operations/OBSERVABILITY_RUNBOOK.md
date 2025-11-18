# AutonomOS Platform - Observability Runbook

**Version:** 1.0  
**Last Updated:** November 18, 2025  
**Owner:** Platform Operations Team

---

## Table of Contents

1. [Key Metrics](#key-metrics)
2. [Prometheus Metrics](#prometheus-metrics)
3. [Grafana Dashboards](#grafana-dashboards)
4. [Log Aggregation](#log-aggregation)
5. [Alerting Rules](#alerting-rules)
6. [Distributed Tracing](#distributed-tracing)
7. [Performance Troubleshooting](#performance-troubleshooting)
8. [Common Issues](#common-issues)

---

## Key Metrics

### Critical Metrics (P0)

| Metric | Threshold | Alert Level | Impact |
|--------|-----------|-------------|--------|
| **Job Queue Depth** | > 500 jobs | CRITICAL | Backlog building, users experience delays |
| **Semaphore Leak** | Active jobs != Redis semaphore | CRITICAL | System deadlock, no new jobs accepted |
| **Error Rate** | > 5% | CRITICAL | Data quality degradation |
| **Worker Crash Rate** | > 10% in 5min | CRITICAL | Job processing halted |
| **Database Connection Pool** | > 90% utilization | WARNING | Imminent connection exhaustion |
| **Redis Memory** | > 80% | WARNING | Risk of eviction or OOM |

### Important Metrics (P1)

| Metric | Threshold | Alert Level | Impact |
|--------|-----------|-------------|--------|
| **API Latency P95** | > 2s | WARNING | User experience degradation |
| **Job Throughput** | < 10 jobs/min | WARNING | Processing slowdown |
| **DCL Graph Build Time** | > 5s | WARNING | Slow UI updates |
| **AAM Drift Detection Rate** | > 50 events/hour | INFO | High schema churn |
| **WebSocket Disconnects** | > 10/min | WARNING | Real-time updates failing |

### Health Metrics (P2)

| Metric | Expected | Alert Level | Impact |
|--------|----------|-------------|--------|
| **Uptime** | > 99.9% | INFO | Service availability |
| **CPU Utilization** | < 70% | INFO | Resource capacity |
| **Memory Usage** | < 80% | INFO | Resource capacity |
| **Disk I/O Wait** | < 5% | WARNING | Storage bottleneck |

---

## Prometheus Metrics

> **⚠️ PLANNED FEATURE - NOT YET IMPLEMENTED**  
> The metrics described below are recommended for implementation but are not currently exported by the application.

### Recommended Metrics Endpoint

**Planned Endpoint:** `http://localhost:5000/metrics`

**Example Output (when implemented):**
```
# HELP autonomos_job_queue_depth Number of jobs in queue per tenant
# TYPE autonomos_job_queue_depth gauge
autonomos_job_queue_depth{tenant_id="tenant-123",queue="mappings"} 42

# HELP autonomos_job_processing_seconds Time spent processing jobs
# TYPE autonomos_job_processing_seconds histogram
autonomos_job_processing_seconds_bucket{le="0.5"} 123
autonomos_job_processing_seconds_bucket{le="1.0"} 234
autonomos_job_processing_seconds_bucket{le="5.0"} 456
autonomos_job_processing_seconds_sum 1234.56
autonomos_job_processing_seconds_count 500
```

### Recommended Metrics to Implement

To implement these metrics, add to `app/main.py`:

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Job metrics
job_counter = Counter(
    'autonomos_jobs_total',
    'Total number of jobs processed',
    ['tenant_id', 'status']
)

job_duration = Histogram(
    'autonomos_job_duration_seconds',
    'Job processing duration in seconds',
    ['tenant_id', 'job_type']
)

queue_depth = Gauge(
    'autonomos_queue_depth',
    'Number of jobs in queue',
    ['tenant_id', 'queue_name']
)

# Semaphore metrics
semaphore_active = Gauge(
    'autonomos_semaphore_active_jobs',
    'Number of active jobs (semaphore counter)',
    ['tenant_id']
)

semaphore_leaked = Gauge(
    'autonomos_semaphore_leaked_slots',
    'Difference between actual active jobs and semaphore counter',
    ['tenant_id']
)

# API metrics
api_requests = Counter(
    'autonomos_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status_code']
)

api_latency = Histogram(
    'autonomos_api_latency_seconds',
    'API request latency',
    ['method', 'endpoint']
)

# DCL metrics
dcl_graph_nodes = Gauge(
    'autonomos_dcl_graph_nodes',
    'Number of nodes in DCL graph',
    ['tenant_id']
)

dcl_graph_edges = Gauge(
    'autonomos_dcl_graph_edges',
    'Number of edges in DCL graph',
    ['tenant_id']
)

dcl_build_time = Histogram(
    'autonomos_dcl_build_seconds',
    'DCL graph build time',
    ['tenant_id']
)

# AAM metrics
aam_drift_events = Counter(
    'autonomos_aam_drift_events_total',
    'Total drift events detected',
    ['tenant_id', 'connector_type', 'event_type']
)

aam_repair_success = Counter(
    'autonomos_aam_repairs_total',
    'Total auto-repair attempts',
    ['tenant_id', 'success']
)

# Database metrics
db_connections = Gauge(
    'autonomos_db_connections',
    'Active database connections',
    ['state']
)

db_query_duration = Histogram(
    'autonomos_db_query_seconds',
    'Database query duration',
    ['query_type']
)

# Redis metrics
redis_commands = Counter(
    'autonomos_redis_commands_total',
    'Total Redis commands executed',
    ['command']
)

redis_memory_bytes = Gauge(
    'autonomos_redis_memory_bytes',
    'Redis memory usage in bytes'
)
```

### Prometheus Configuration

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'autonomos'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
    scrape_interval: 10s
```

### Key Prometheus Queries

**Job Queue Depth by Tenant:**
```promql
autonomos_queue_depth{queue_name="mappings"}
```

**Job Error Rate (Last 5min):**
```promql
rate(autonomos_jobs_total{status="failed"}[5m]) 
/ 
rate(autonomos_jobs_total[5m]) * 100
```

**P95 API Latency:**
```promql
histogram_quantile(0.95, 
  rate(autonomos_api_latency_seconds_bucket[5m])
)
```

**Job Throughput (jobs/sec):**
```promql
rate(autonomos_jobs_total{status="completed"}[1m])
```

**Semaphore Leak Detection:**
```promql
abs(autonomos_semaphore_active_jobs - 
    count(autonomos_jobs_total{status="running"}) by (tenant_id))
> 0
```

**Database Connection Pool Utilization:**
```promql
autonomos_db_connections{state="active"} 
/ 
(autonomos_db_connections{state="active"} + autonomos_db_connections{state="idle"}) 
* 100
```

**Redis Memory Growth Rate:**
```promql
deriv(autonomos_redis_memory_bytes[5m])
```

---

## Grafana Dashboards

### Dashboard 1: System Overview

**Panels:**

1. **Uptime (Single Stat)**
   ```promql
   up{job="autonomos"}
   ```

2. **Total Requests (Graph)**
   ```promql
   sum(rate(autonomos_api_requests_total[5m]))
   ```

3. **Error Rate (Graph)**
   ```promql
   sum(rate(autonomos_api_requests_total{status_code=~"5.."}[5m])) 
   / 
   sum(rate(autonomos_api_requests_total[5m])) * 100
   ```

4. **API Latency P50/P95/P99 (Graph)**
   ```promql
   histogram_quantile(0.50, rate(autonomos_api_latency_seconds_bucket[5m]))
   histogram_quantile(0.95, rate(autonomos_api_latency_seconds_bucket[5m]))
   histogram_quantile(0.99, rate(autonomos_api_latency_seconds_bucket[5m]))
   ```

5. **CPU & Memory (Graph)**
   ```promql
   process_cpu_seconds_total
   process_resident_memory_bytes
   ```

### Dashboard 2: Job Queue Monitoring

**Panels:**

1. **Queue Depth by Tenant (Graph)**
   ```promql
   autonomos_queue_depth
   ```

2. **Job Throughput (Graph)**
   ```promql
   sum(rate(autonomos_jobs_total{status="completed"}[1m])) by (tenant_id)
   ```

3. **Job Duration P95 (Graph)**
   ```promql
   histogram_quantile(0.95, 
     rate(autonomos_job_duration_seconds_bucket[5m])
   ) by (job_type)
   ```

4. **Semaphore Utilization (Gauge)**
   ```promql
   autonomos_semaphore_active_jobs / 5 * 100
   ```

5. **Failed Jobs (Table)**
   ```promql
   topk(10, 
     sum(increase(autonomos_jobs_total{status="failed"}[1h])) by (tenant_id)
   )
   ```

### Dashboard 3: AAM Intelligence

**Panels:**

1. **Drift Events (Graph)**
   ```promql
   sum(rate(autonomos_aam_drift_events_total[5m])) by (connector_type, event_type)
   ```

2. **Auto-Repair Success Rate (Gauge)**
   ```promql
   sum(rate(autonomos_aam_repairs_total{success="true"}[5m])) 
   / 
   sum(rate(autonomos_aam_repairs_total[5m])) * 100
   ```

3. **DCL Graph Size (Graph)**
   ```promql
   autonomos_dcl_graph_nodes
   autonomos_dcl_graph_edges
   ```

4. **DCL Build Time (Graph)**
   ```promql
   histogram_quantile(0.95, 
     rate(autonomos_dcl_build_seconds_bucket[5m])
   )
   ```

### Grafana Dashboard JSON Export

See `grafana/autonomos_system_overview.json` for complete dashboard definition.

---

## Log Aggregation

### Structured Logging Format

AutonomOS uses `structlog` for structured JSON logging:

```json
{
  "timestamp": "2025-11-18T12:00:00.123Z",
  "level": "INFO",
  "logger": "app.api.v1.bulk_mappings",
  "message": "Job created",
  "tenant_id": "tenant-123",
  "job_id": "job-456",
  "trace_id": "trace-789",
  "latency_ms": 42
}
```

### Log Levels

| Level | Usage | Examples |
|-------|-------|----------|
| **DEBUG** | Detailed debugging | Variable values, flow control |
| **INFO** | Normal operations | Request received, job completed |
| **WARNING** | Unexpected but recoverable | Retry attempt, high latency |
| **ERROR** | Error requiring attention | Job failed, validation error |
| **CRITICAL** | System failure | Database down, OOM |

### Log Retention

- **Production:** 30 days
- **Staging:** 7 days
- **Development:** 1 day

### Loki Configuration

Create `loki-config.yaml`:

```yaml
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
  chunk_idle_period: 5m
  chunk_retain_period: 30s

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/index
    cache_location: /loki/cache
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h

chunk_store_config:
  max_look_back_period: 720h
```

### Promtail Configuration

Create `promtail-config.yaml`:

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://localhost:3100/loki/api/v1/push

scrape_configs:
  - job_name: autonomos
    static_configs:
      - targets:
          - localhost
        labels:
          job: autonomos
          __path__: /var/log/autonomos/*.log
    pipeline_stages:
      - json:
          expressions:
            timestamp: timestamp
            level: level
            message: message
            tenant_id: tenant_id
            job_id: job_id
            trace_id: trace_id
      - labels:
          level:
          tenant_id:
```

### Useful Log Queries (LogQL)

**All errors in last hour:**
```logql
{job="autonomos"} | json | level="ERROR" | __error__=""
```

**Jobs failing for specific tenant:**
```logql
{job="autonomos"} | json 
| tenant_id="tenant-123" 
| message=~".*failed.*"
```

**High latency requests:**
```logql
{job="autonomos"} | json 
| latency_ms > 2000
```

**Semaphore leak events:**
```logql
{job="autonomos"} | json 
| message=~".*semaphore.*leak.*"
```

---

## Alerting Rules

### Prometheus Alert Rules

Create `alerts.yml`:

```yaml
groups:
  - name: autonomos_critical
    interval: 30s
    rules:
      # CRITICAL: Semaphore leak detected
      - alert: SemaphoreLeakDetected
        expr: autonomos_semaphore_leaked_slots > 0
        for: 5m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Semaphore leak detected for tenant {{ $labels.tenant_id }}"
          description: "Semaphore counter mismatch: {{ $value }} leaked slots. System may deadlock."
          runbook: "https://docs.autonomos.dev/runbooks/semaphore-leak"

      # CRITICAL: High error rate
      - alert: HighErrorRate
        expr: |
          (sum(rate(autonomos_jobs_total{status="failed"}[5m])) 
           / 
           sum(rate(autonomos_jobs_total[5m])) * 100) > 5
        for: 5m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "High job error rate: {{ $value }}%"
          description: "Error rate exceeded 5% threshold"

      # CRITICAL: Worker crash detected
      - alert: WorkerCrashRate
        expr: |
          (sum(rate(autonomos_worker_crashes_total[5m])) 
           / 
           sum(rate(autonomos_jobs_total[5m])) * 100) > 10
        for: 2m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "High worker crash rate: {{ $value }}%"
          description: "Workers are crashing frequently"

      # CRITICAL: Database connection pool exhausted
      - alert: DatabasePoolExhausted
        expr: |
          (autonomos_db_connections{state="active"} 
           / 
           (autonomos_db_connections{state="active"} + autonomos_db_connections{state="idle"}) 
           * 100) > 90
        for: 5m
        labels:
          severity: critical
          team: database
        annotations:
          summary: "Database connection pool at {{ $value }}% utilization"
          description: "Risk of connection exhaustion"

  - name: autonomos_warning
    interval: 1m
    rules:
      # WARNING: High queue depth
      - alert: HighQueueDepth
        expr: autonomos_queue_depth > 500
        for: 10m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "High queue depth for {{ $labels.tenant_id }}: {{ $value }} jobs"
          description: "Job backlog building up"

      # WARNING: High API latency
      - alert: HighAPILatency
        expr: |
          histogram_quantile(0.95, 
            rate(autonomos_api_latency_seconds_bucket[5m])
          ) > 2
        for: 5m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "P95 API latency is {{ $value }}s"
          description: "API response time degraded"

      # WARNING: Redis memory high
      - alert: RedisMemoryHigh
        expr: autonomos_redis_memory_bytes / (8 * 1024^3) * 100 > 80
        for: 10m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "Redis memory at {{ $value }}%"
          description: "Risk of OOM or eviction"
```

### Alertmanager Configuration

Create `alertmanager.yml`:

```yaml
global:
  resolve_timeout: 5m
  slack_api_url: 'YOUR_SLACK_WEBHOOK_URL'

route:
  group_by: ['alertname', 'tenant_id']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 3h
  receiver: 'slack-critical'
  routes:
    - match:
        severity: critical
      receiver: slack-critical
      continue: true
    - match:
        severity: warning
      receiver: slack-warning

receivers:
  - name: 'slack-critical'
    slack_configs:
      - channel: '#alerts-critical'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
        send_resolved: true

  - name: 'slack-warning'
    slack_configs:
      - channel: '#alerts-warning'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
        send_resolved: true
```

---

## Distributed Tracing

### OpenTelemetry Integration

Add to `app/main.py`:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Configure tracer
trace.set_tracer_provider(TracerProvider())
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(app)
```

### Trace ID Propagation

All API responses include `X-Trace-ID` header:

```python
from opentelemetry import trace

@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    span = trace.get_current_span()
    trace_id = format(span.get_span_context().trace_id, '032x')
    
    response = await call_next(request)
    response.headers["X-Trace-ID"] = trace_id
    
    return response
```

### Viewing Traces

Access Jaeger UI at `http://localhost:16686`

**Useful Queries:**
- `service=autonomos operation=POST /api/v1/bulk-mappings`
- `tags.tenant_id=tenant-123 tags.error=true`
- `duration>2s`

---

## Performance Troubleshooting

### Symptom: High API Latency

**Diagnosis:**

1. Check P95 latency:
   ```promql
   histogram_quantile(0.95, rate(autonomos_api_latency_seconds_bucket[5m]))
   ```

2. Identify slow endpoints:
   ```promql
   topk(5, histogram_quantile(0.95, 
     rate(autonomos_api_latency_seconds_bucket[5m])) by (endpoint)
   )
   ```

3. Check database query times:
   ```promql
   histogram_quantile(0.95, rate(autonomos_db_query_seconds_bucket[5m]))
   ```

**Remediation:**

- Add database indexes
- Optimize N+1 queries
- Enable query result caching
- Scale up database instance
- Add read replicas

---

### Symptom: Job Queue Backlog

**Diagnosis:**

1. Check queue depth:
   ```promql
   autonomos_queue_depth
   ```

2. Check worker throughput:
   ```promql
   rate(autonomos_jobs_total{status="completed"}[5m])
   ```

3. Check worker utilization:
   ```bash
   rq info --url $REDIS_URL
   ```

**Remediation:**

- Scale workers horizontally (add more RQ workers)
- Optimize job processing logic
- Reduce RAG similarity search scope
- Batch job processing
- Increase worker concurrency

---

### Symptom: Semaphore Leak

**Diagnosis:**

1. Check for leaked slots:
   ```promql
   autonomos_semaphore_leaked_slots
   ```

2. Review failed jobs without cleanup:
   ```bash
   rq info --url $REDIS_URL --only-failures
   ```

**Remediation:**

```python
# Manual semaphore reset
from shared.redis_client import get_redis_client

redis_client = get_redis_client()
tenant_id = "tenant-123"

# Reset semaphore
redis_client.set(f"job:semaphore:tenant:{tenant_id}", 0)

# Verify
print(redis_client.get(f"job:semaphore:tenant:{tenant_id}"))  # Should be 0
```

---

## Common Issues

### Issue: Redis Connection Timeout

**Symptoms:**
- `redis.exceptions.TimeoutError`
- Jobs not enqueueing

**Diagnosis:**
```bash
redis-cli -u $REDIS_URL ping
```

**Resolution:**
1. Check Redis server status
2. Verify TLS certificate (if using rediss://)
3. Check network connectivity
4. Increase timeout in `shared/redis_client.py`

---

### Issue: Database Connection Pool Exhausted

**Symptoms:**
- `FATAL: sorry, too many clients already`
- API 503 errors

**Diagnosis:**
```sql
SELECT count(*) FROM pg_stat_activity;
```

**Resolution:**
1. Use connection pooling (PgBouncer)
2. Increase max_connections in PostgreSQL
3. Optimize long-running queries
4. Scale database instance

---

### Issue: WebSocket Connections Dropping

**Symptoms:**
- Frequent reconnects in browser
- Real-time updates missing

**Diagnosis:**
```bash
# Check nginx/caddy timeout settings
grep proxy_read_timeout /etc/nginx/sites-enabled/autonomos
```

**Resolution:**
1. Increase proxy timeouts (3600s recommended)
2. Implement heartbeat/ping mechanism
3. Add reconnection logic in frontend

---

## Escalation

### On-Call Rotation

- **Primary:** Platform Team
- **Secondary:** Database Team
- **Escalation:** Engineering Manager

### Incident Severity Levels

| Level | Response Time | Examples |
|-------|---------------|----------|
| **P0 - Critical** | 15 minutes | Complete outage, data loss |
| **P1 - High** | 1 hour | Semaphore leak, high error rate |
| **P2 - Medium** | 4 hours | High latency, queue backlog |
| **P3 - Low** | Next business day | Minor performance degradation |

---

## References

- [Performance Tuning Guide](../performance/PERFORMANCE_TUNING.md)
- [Operational Procedures](./OPERATIONAL_PROCEDURES.md)
- [Architecture Overview](../architecture/ARCHITECTURE_OVERVIEW.md)
