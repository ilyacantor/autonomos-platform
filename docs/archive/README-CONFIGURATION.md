# AAM → DCL Configuration Guide

## Overview

This document describes the configuration options for the AAM (Adaptive API Mesh) → DCL (Data Connection Layer) bridge. All settings are externalized via environment variables for production tuning.

---

## Configuration Parameters

### 1. Batch Processing

**AAM_BATCH_CHUNK_SIZE**
- **Default:** `200`
- **Description:** Maximum number of records per Redis Stream message
- **Use Case:** Tune for high-volume connectors to balance message size vs. throughput
- **Example:** 
  ```bash
  export AAM_BATCH_CHUNK_SIZE=500  # For high-volume sales data
  ```
- **Impact:** Larger chunks = fewer messages but larger payloads

---

### 2. Schema Sampling

**AAM_MAX_SAMPLES_PER_TABLE**
- **Default:** `8`
- **Description:** Maximum number of sample records to include in schema inference payloads
- **Use Case:** Control metadata size in Redis Streams
- **Example:**
  ```bash
  export AAM_MAX_SAMPLES_PER_TABLE=15  # For more detailed schema inference
  ```
- **Impact:** More samples = better type inference but larger messages

---

### 3. Redis Streams Memory Management

**AAM_REDIS_STREAM_MAXLEN**
- **Default:** `1000`
- **Description:** Maximum number of entries to retain in each Redis Stream (uses approximate trimming)
- **Use Case:** Prevent unbounded memory growth in high-throughput scenarios
- **Example:**
  ```bash
  export AAM_REDIS_STREAM_MAXLEN=5000  # For replay/audit scenarios
  ```
- **Impact:** 
  - **Too low:** May lose unprocessed events if DCL lags
  - **Too high:** Increased Redis memory usage
  - **Recommendation:** Set to 2-3x expected peak throughput per hour

**MAXLEN Policy:**
- Uses **approximate trimming** (`~`) for better performance
- Applied per connector stream: `aam:dcl:{tenant_id}:{connector}`
- Streams are trimmed on each `XADD` operation
- Older events are automatically removed once threshold is exceeded

**Monitoring Streams:**
```bash
# Check stream length
redis-cli XLEN aam:dcl:default:salesforce

# Inspect stream info
redis-cli XINFO STREAM aam:dcl:default:salesforce
```

---

### 4. Idempotency & Duplicate Prevention

**AAM_IDEMPOTENCY_TTL**
- **Default:** `86400` (24 hours)
- **Description:** Time-to-live (seconds) for processed batch tracking
- **Use Case:** Prevent duplicate processing in replay/reprocessing workflows
- **Example:**
  ```bash
  export AAM_IDEMPOTENCY_TTL=172800  # 48 hours for replay scenarios
  ```
- **Impact:**
  - **Too low:** Risk of duplicate processing if DCL restarts within TTL window
  - **Too high:** Increased Redis memory for tracking sets
  - **Recommendation:** Set to 2x expected maximum processing delay

**Idempotency Mechanism:**
- Batch IDs are tracked in Redis SET: `dcl:processed_batches:{tenant_id}`
- Each batch ID is format: `{connector}_{timestamp}_{chunk_number}`
- SET automatically expires after TTL to prevent unbounded growth
- Consumer groups ensure at-least-once delivery with acknowledgment (XACK)

---

### 5. Tenant Configuration

**TENANT_ID**
- **Default:** `default`
- **Description:** Tenant identifier for multi-tenancy isolation
- **Use Case:** Override default tenant for testing or multi-tenant deployments
- **Example:**
  ```bash
  export TENANT_ID=customer-acme-corp  # For specific tenant testing
  ```
- **Impact:** All Redis Streams keys are scoped by tenant ID

---

## Production Tuning Examples

### High-Volume Scenario (1M+ events/day)
```bash
export AAM_BATCH_CHUNK_SIZE=500
export AAM_REDIS_STREAM_MAXLEN=10000
export AAM_IDEMPOTENCY_TTL=172800  # 48 hours
```

### Low-Latency Scenario (Real-time processing)
```bash
export AAM_BATCH_CHUNK_SIZE=50
export AAM_REDIS_STREAM_MAXLEN=1000
export AAM_IDEMPOTENCY_TTL=3600  # 1 hour
```

### Audit/Replay Scenario (Long retention)
```bash
export AAM_BATCH_CHUNK_SIZE=200
export AAM_REDIS_STREAM_MAXLEN=50000  # Keep more history
export AAM_IDEMPOTENCY_TTL=604800  # 7 days
```

---

## Redis Streams Architecture

### Key Format
```
aam:dcl:{tenant_id}:{connector}
```

**Examples:**
- `aam:dcl:default:salesforce`
- `aam:dcl:default:hubspot`
- `aam:dcl:acme-corp:dynamics`

### Consumer Groups
```
dcl_engine:{tenant_id}
```

**Examples:**
- `dcl_engine:default`
- `dcl_engine:acme-corp`

### Message Format
```json
{
  "payload": "{\"batch_id\":\"salesforce_1762299908994_1\",\"connector\":\"salesforce\",\"connector_config_id\":\"salesforce-demo-001\",\"tables\":[{\"name\":\"opportunities\",\"schema\":{\"columns\":[{\"name\":\"account_name\",\"type\":\"string\"},{\"name\":\"opportunity_id\",\"type\":\"string\"},{\"name\":\"opportunity_name\",\"type\":\"string\"},{\"name\":\"stage\",\"type\":\"string\"},{\"name\":\"amount\",\"type\":\"numeric\"},{\"name\":\"close_date\",\"type\":\"datetime\"},{\"name\":\"created_at\",\"type\":\"datetime\"}]},\"samples\":[...],\"stats\":{\"total_count\":7,\"sample_count\":7}}]}"
}
```

---

## Monitoring & Observability

### Key Metrics to Track

1. **Stream Length** (per connector):
   ```bash
   redis-cli XLEN aam:dcl:default:salesforce
   ```

2. **Pending Messages** (unacknowledged):
   ```bash
   redis-cli XPENDING aam:dcl:default:salesforce dcl_engine:default
   ```

3. **Idempotency Set Size**:
   ```bash
   redis-cli SCARD dcl:processed_batches:default
   ```

4. **Consumer Group Info**:
   ```bash
   redis-cli XINFO GROUPS aam:dcl:default:salesforce
   ```

### Health Check Queries
```python
# Check stream health
stream_length = redis_client.xlen(f"aam:dcl:{tenant_id}:{connector}")
pending_info = redis_client.xpending(f"aam:dcl:{tenant_id}:{connector}", f"dcl_engine:{tenant_id}")

# Check idempotency tracking
processed_count = redis_client.scard(f"dcl:processed_batches:{tenant_id}")
```

---

## Troubleshooting

### Issue: Events not being processed
**Diagnosis:**
```bash
# Check stream has data
redis-cli XLEN aam:dcl:default:salesforce

# Check consumer group exists
redis-cli XINFO GROUPS aam:dcl:default:salesforce
```

**Solution:**
- Verify tenant_id matches between ingestion and DCL
- Check USE_AAM_AS_SOURCE feature flag is enabled
- Inspect DCL logs for consumer group errors

### Issue: Duplicate events
**Diagnosis:**
```bash
# Check idempotency TTL
redis-cli TTL dcl:processed_batches:default
```

**Solution:**
- Increase AAM_IDEMPOTENCY_TTL if processing takes longer than current TTL
- Verify XACK is being called after successful processing

### Issue: Redis memory growing unbounded
**Diagnosis:**
```bash
# Check all stream lengths
redis-cli --scan --pattern "aam:dcl:*" | xargs -I {} redis-cli XLEN {}
```

**Solution:**
- Reduce AAM_REDIS_STREAM_MAXLEN to trim more aggressively
- Verify approximate trimming is working (check XINFO STREAM output)
- Consider manual XTRIM for emergency cleanup:
  ```bash
  redis-cli XTRIM aam:dcl:default:salesforce MAXLEN ~ 1000
  ```

---

## Migration & Upgrades

### Changing Configuration Without Downtime

1. **Update environment variables**
2. **Restart workflows** (graceful shutdown ensures consumer groups commit offsets)
3. **Monitor stream depths** to verify new settings take effect

### Breaking Changes
- Changing TENANT_ID requires re-running ingestion scripts
- Reducing AAM_REDIS_STREAM_MAXLEN may lose unprocessed events (increase gradually)
- Reducing AAM_IDEMPOTENCY_TTL may cause duplicates in active processing windows

---

## Security Considerations

- **Redis TLS:** Use `rediss://` protocol for production (automatically handled by code)
- **Tenant Isolation:** All keys are scoped by tenant_id to prevent cross-tenant access
- **Data Retention:** Configure MAXLEN and TTL based on compliance requirements

---

## References

- **Redis Streams Documentation:** https://redis.io/docs/data-types/streams/
- **Consumer Groups:** https://redis.io/docs/manual/data-types/streams/#consumer-groups
- **Feature Flags:** See `app/config/feature_flags.py` for USE_AAM_AS_SOURCE control

---

**Last Updated:** 2025-11-04  
**Phase:** 2.5 - AAM Connector Integration Complete
