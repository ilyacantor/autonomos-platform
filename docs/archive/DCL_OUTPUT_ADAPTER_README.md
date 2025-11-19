# AAM DCL Output Adapter

## Overview

The DCL Output Adapter serves as the bridge between the Adaptive API Mesh (AAM) and the Data Connection Layer (DCL). It transforms AAM canonical events into DCL-compatible format and publishes them to Redis Streams for consumption by the DCL engine.

## Architecture

```
┌─────────────────┐
│  AAM Connectors │  (Salesforce, MongoDB, Supabase, FileSource)
└────────┬────────┘
         │ Canonical Events
         ▼
┌─────────────────┐
│ DCL Output      │  Transform → Group → Chunk → Publish
│ Adapter         │
└────────┬────────┘
         │ DCL Payload (JSON)
         ▼
┌─────────────────┐
│ Redis Streams   │  aam:dcl:{tenant_id}:{connector_type}
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  DCL Engine     │  Consume and process data
└─────────────────┘
```

## Key Features

### 1. **Data Transformation**
- Converts AAM `CanonicalEvent` objects to DCL-compatible JSON format
- Preserves data lineage and provenance information
- Includes schema fingerprints for drift detection

### 2. **Batch Processing**
- Automatically chunks large batches (200 records per message)
- Each chunk gets a unique `batch_id`: `{connector}_{timestamp}_{chunk_num}`
- Tracks total records processed across all chunks

### 3. **Schema Inference**
- Groups events by `entity_type` (becomes table name in DCL)
- Infers schema from event payloads
- Includes up to 8 sample records per table
- Computes schema fingerprints for change detection

### 4. **Redis Streams Integration**
- Stream key format: `aam:dcl:{tenant_id}:{connector_type}`
- Uses `XADD` with `MAXLEN ~ 1000` to bound stream history
- Stores payload as JSON string in `payload` field

### 5. **Multi-Tenant Support**
- Isolated streams per tenant
- Tenant ID included in stream key and payload

### 6. **Error Handling**
- Validates canonical events
- Graceful Redis error handling
- Comprehensive logging
- Returns detailed status and error messages

## Installation

No additional dependencies required beyond the AAM core dependencies:
- `redis` Python client
- Standard library modules (`json`, `hashlib`, `datetime`, `typing`)

## Usage

### Basic Usage

```python
import redis
from aam_hybrid.core.dcl_output_adapter import publish_to_dcl_stream

# Connect to Redis
redis_client = redis.Redis.from_url("redis://localhost:6379", decode_responses=False)

# Publish canonical events to DCL stream
result = publish_to_dcl_stream(
    tenant_id="demo-tenant",
    connector_type="salesforce",
    canonical_events=events,  # List of CanonicalEvent objects
    redis_client=redis_client,
    connector_config_id="sf-prod-001"
)

print(f"Success: {result['success']}")
print(f"Stream: {result['stream_key']}")
print(f"Records: {result['total_records']}")
print(f"Batches: {result['batches_published']}")
```

### Response Structure

```python
{
    "success": True,
    "stream_key": "aam:dcl:demo-tenant:salesforce",
    "batches_published": 2,
    "total_records": 250,
    "batch_ids": ["salesforce_1699123456789_1", "salesforce_1699123456790_2"],
    "errors": []
}
```

### Reading from DCL Stream

```python
import redis
import json

redis_client = redis.Redis.from_url("redis://localhost:6379", decode_responses=True)

# Read messages from stream
messages = redis_client.xread({'aam:dcl:demo-tenant:salesforce': '0'}, count=10)

for stream, msgs in messages:
    for msg_id, fields in msgs:
        payload = json.loads(fields['payload'])
        
        print(f"Batch ID: {payload['batch_id']}")
        print(f"Records: {payload['record_count']}")
        print(f"Tables: {list(payload['tables'].keys())}")
```

## DCL Payload Format

The adapter produces DCL-compatible payloads with the following structure:

```json
{
  "schema_version": "v1.0",
  "batch_id": "salesforce_1699123456789_1",
  "connector_type": "salesforce",
  "tenant_id": "demo-tenant",
  "record_count": 100,
  "lineage": {
    "source": "AAM",
    "connector_config_id": "sf-prod-001",
    "ingestion_timestamp": "2025-11-04T22:30:00.000Z",
    "schema_fingerprint": "abc123def456"
  },
  "tables": {
    "opportunity": {
      "path": "aam://stream",
      "schema": {
        "id": "string",
        "name": "string",
        "amount": "number",
        "stage": "string",
        "close_date": "datetime"
      },
      "samples": [
        {
          "id": "SF-OPP-001",
          "name": "Enterprise Deal",
          "amount": 100000.0,
          "stage": "Proposal",
          "close_date": "2025-12-31",
          "_event_id": "evt-001",
          "_timestamp": "2025-11-04T22:30:00.000Z"
        }
      ],
      "record_count": 100,
      "schema_fingerprint": "def456abc789"
    }
  }
}
```

## API Reference

### `publish_to_dcl_stream()`

Main entry point for publishing AAM events to DCL.

**Parameters:**
- `tenant_id` (str): Tenant identifier for multi-tenant isolation
- `connector_type` (str): Connector type (salesforce, supabase, mongodb, filesource)
- `canonical_events` (List[Any]): List of CanonicalEvent objects
- `redis_client`: Redis client instance
- `connector_config_id` (Optional[str]): Connector configuration ID

**Returns:**
- `Dict[str, Any]` with keys:
  - `success`: bool - Whether operation succeeded
  - `stream_key`: str - Redis stream key
  - `batches_published`: int - Number of batches created
  - `total_records`: int - Total records published
  - `batch_ids`: List[str] - List of batch IDs
  - `errors`: List[str] - Any errors encountered

### `get_dcl_stream_key()`

Get the Redis Stream key for a tenant/connector combination.

**Parameters:**
- `tenant_id` (str): Tenant identifier
- `connector_type` (str): Connector type

**Returns:**
- `str`: Redis Stream key in format `aam:dcl:{tenant_id}:{connector_type}`

### `clear_dcl_stream()`

Clear all messages from a DCL stream (useful for testing).

**Parameters:**
- `redis_client`: Redis client instance
- `tenant_id` (str): Tenant identifier
- `connector_type` (str): Connector type

**Returns:**
- `bool`: True if stream was deleted

## Configuration

### Batch Chunk Size

The default chunk size is 200 records per message. To modify:

```python
# In dcl_output_adapter.py
BATCH_CHUNK_SIZE = 200  # Adjust as needed
```

### Max Samples Per Table

The default is 8 sample records per table. To modify:

```python
# In dcl_output_adapter.py
MAX_SAMPLES_PER_TABLE = 8  # Adjust as needed
```

## Testing

### Run Tests

```bash
cd aam-hybrid
python3 tests/test_dcl_output_simple.py
```

### Run Examples

```bash
cd aam-hybrid/core
python3 dcl_output_example.py
```

## Performance Considerations

### Batch Chunking
- Large batches are automatically split into chunks of 200 records
- Prevents Redis message size limits
- Improves processing parallelism in DCL

### Stream Trimming
- Streams are automatically trimmed to ~1000 messages using `MAXLEN ~ 1000`
- Prevents unbounded memory growth
- Maintains recent history for recovery

### Schema Fingerprinting
- SHA-256 hashing of schema structure
- Enables efficient schema change detection
- 16-character truncated hash for readability

## Error Handling

The adapter handles errors gracefully:

1. **Empty Event List**: Returns success with zero records
2. **Redis Connection Errors**: Logged and returned in errors array
3. **Chunk Publishing Failures**: Individual chunk errors don't stop other chunks
4. **Invalid Events**: Logged with details

## Integration with AAM

The adapter is designed to be called after AAM connectors normalize data:

```python
# In AAM connector code
from aam_hybrid.core.dcl_output_adapter import publish_to_dcl_stream

# After creating canonical events
canonical_events = connector.fetch_and_normalize()

# Publish to DCL
result = publish_to_dcl_stream(
    tenant_id=tenant_id,
    connector_type="salesforce",
    canonical_events=canonical_events,
    redis_client=redis_client
)
```

## Monitoring

Key metrics to monitor:

- **Batch Success Rate**: `result['success']`
- **Records Published**: `result['total_records']`
- **Error Rate**: `len(result['errors'])`
- **Stream Length**: `redis_client.xlen(stream_key)`

## Troubleshooting

### Problem: No messages in stream
- **Check**: Redis connection
- **Check**: `result['errors']` for error messages
- **Verify**: Events list is not empty

### Problem: Messages too large
- **Solution**: Reduce `BATCH_CHUNK_SIZE`
- **Check**: Sample data size in events

### Problem: Schema inference incorrect
- **Check**: Event payload structure
- **Verify**: All events have consistent fields

## Future Enhancements

- [ ] Configurable sample count per table
- [ ] Schema evolution tracking
- [ ] Dead letter queue for failed batches
- [ ] Metrics and monitoring integration
- [ ] Compression for large payloads
- [ ] Custom transformation functions

## License

Part of the AutonomOS AAM system.
