"""
DCL Output Adapter for AAM

Transforms AAM canonical events into DCL-compatible format and publishes to Redis Streams.
This module serves as the bridge between the Adaptive API Mesh (AAM) and the Data Connection Layer (DCL).

Features:
- Transforms CanonicalEvent objects to DCL format
- Groups events by entity_type to create table structures
- Infers schema from canonical event payloads
- Batch processing with configurable chunk sizes
- Redis Streams integration with automatic stream management
- Comprehensive error handling and logging
"""

import json
import time
import uuid
import hashlib
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

BATCH_CHUNK_SIZE = 200
MAX_SAMPLES_PER_TABLE = 8


def publish_to_dcl_stream(
    tenant_id: str,
    connector_type: str,
    canonical_events: List[Any],
    redis_client,
    connector_config_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Transform AAM canonical events to DCL format and publish to Redis Streams.
    
    This is the main entry point for AAM→DCL data transfer. It:
    1. Groups events by entity_type
    2. Chunks large batches for manageable message sizes
    3. Creates DCL-compatible payloads
    4. Publishes to Redis Streams with proper keys
    
    Args:
        tenant_id: Tenant identifier for multi-tenant isolation
        connector_type: Type of connector (salesforce, supabase, mongodb, filesource)
        canonical_events: List of CanonicalEvent objects from AAM
        redis_client: Redis client instance
        connector_config_id: Optional connector configuration ID
    
    Returns:
        Dict with:
            - success: bool
            - stream_key: str
            - batches_published: int
            - total_records: int
            - batch_ids: List[str]
            - errors: List[str]
    
    Example:
        >>> result = publish_to_dcl_stream(
        ...     tenant_id="demo-tenant",
        ...     connector_type="salesforce",
        ...     canonical_events=[event1, event2, ...],
        ...     redis_client=redis_client
        ... )
        >>> print(result['total_records'])
        100
    """
    try:
        if not canonical_events:
            logger.warning("No canonical events provided to publish")
            return {
                "success": True,
                "stream_key": None,
                "batches_published": 0,
                "total_records": 0,
                "batch_ids": [],
                "errors": []
            }
        
        logger.info(f"Publishing {len(canonical_events)} events to DCL stream for tenant={tenant_id}, connector={connector_type}")
        
        stream_key = f"aam:dcl:{tenant_id}:{connector_type}"
        
        events_by_entity = _group_events_by_entity(canonical_events)
        logger.info(f"Grouped events into {len(events_by_entity)} entity types")
        
        chunks = _create_event_chunks(canonical_events, BATCH_CHUNK_SIZE)
        logger.info(f"Split {len(canonical_events)} events into {len(chunks)} chunks (max {BATCH_CHUNK_SIZE} per chunk)")
        
        batch_ids = []
        errors = []
        total_published = 0
        
        for chunk_num, chunk_events in enumerate(chunks, start=1):
            try:
                timestamp = int(time.time() * 1000)
                batch_id = f"{connector_type}_{timestamp}_{chunk_num}"
                
                chunk_events_by_entity = _group_events_by_entity(chunk_events)
                
                dcl_payload = _create_dcl_payload(
                    tenant_id=tenant_id,
                    connector_type=connector_type,
                    events_by_entity=chunk_events_by_entity,
                    batch_id=batch_id,
                    connector_config_id=connector_config_id or f"{connector_type}-default"
                )
                
                payload_json = json.dumps(dcl_payload)
                
                message_id = redis_client.xadd(
                    stream_key,
                    {"payload": payload_json},
                    maxlen=1000,
                    approximate=True
                )
                
                batch_ids.append(batch_id)
                total_published += len(chunk_events)
                
                logger.info(f"Published batch {chunk_num}/{len(chunks)}: {batch_id} ({len(chunk_events)} records) -> {message_id.decode()}")
                
            except Exception as chunk_error:
                error_msg = f"Failed to publish chunk {chunk_num}: {str(chunk_error)}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
        
        success = len(errors) == 0
        
        return {
            "success": success,
            "stream_key": stream_key,
            "batches_published": len(batch_ids),
            "total_records": total_published,
            "batch_ids": batch_ids,
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"Failed to publish to DCL stream: {e}", exc_info=True)
        return {
            "success": False,
            "stream_key": None,
            "batches_published": 0,
            "total_records": 0,
            "batch_ids": [],
            "errors": [str(e)]
        }


def _group_events_by_entity(events: List[Any]) -> Dict[str, List[Any]]:
    """
    Group canonical events by entity_type to create table structures.
    
    Each entity_type becomes a separate table in the DCL payload.
    
    Args:
        events: List of CanonicalEvent objects
    
    Returns:
        Dict mapping entity_type to list of events
    
    Example:
        {
            "opportunity": [event1, event2, ...],
            "account": [event3, event4, ...]
        }
    """
    grouped = defaultdict(list)
    
    for event in events:
        entity_type = _get_entity_type(event)
        grouped[entity_type].append(event)
    
    return dict(grouped)


def _get_entity_type(event: Any) -> str:
    """
    Extract entity_type from a canonical event.
    
    Handles both string enum values and direct string attributes.
    """
    if hasattr(event, 'entity_type'):
        entity_type = event.entity_type
        if hasattr(entity_type, 'value'):
            return entity_type.value
        return str(entity_type)
    
    if hasattr(event, 'entity'):
        return str(event.entity)
    
    return "unknown"


def _create_event_chunks(events: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split events into chunks for batch processing.
    
    Args:
        events: List of canonical events
        chunk_size: Maximum events per chunk
    
    Returns:
        List of event chunks
    """
    chunks = []
    for i in range(0, len(events), chunk_size):
        chunks.append(events[i:i + chunk_size])
    return chunks


def _infer_schema_from_events(events: List[Any]) -> Dict[str, str]:
    """
    Infer schema from canonical event payloads.
    
    Analyzes the payload/data fields to determine column types.
    
    Args:
        events: List of canonical events of the same entity_type
    
    Returns:
        Dict mapping field names to inferred types
    
    Example:
        {
            "id": "string",
            "name": "string",
            "amount": "number",
            "created_at": "datetime"
        }
    """
    schema = {}
    
    if not events:
        return schema
    
    for event in events:
        payload = _extract_payload(event)
        
        for field_name, field_value in payload.items():
            if field_name in schema:
                continue
            
            field_type = _infer_field_type(field_value)
            schema[field_name] = field_type
    
    return schema


def _extract_payload(event: Any) -> Dict[str, Any]:
    """
    Extract the data payload from a canonical event.
    
    Handles different event structures (EntityEvent, CanonicalEvent, etc.)
    """
    if hasattr(event, 'payload') and isinstance(event.payload, dict):
        return event.payload
    
    if hasattr(event, 'data'):
        data = event.data
        if isinstance(data, dict):
            return data
        if hasattr(data, 'dict'):
            return data.dict()
        if hasattr(data, 'model_dump'):
            return data.model_dump()
    
    return {}


def _infer_field_type(value: Any) -> str:
    """
    Infer DCL-compatible type from a field value.
    
    Maps Python types to DCL schema types.
    """
    if value is None:
        return "string"
    
    if isinstance(value, bool):
        return "boolean"
    
    if isinstance(value, int):
        return "integer"
    
    if isinstance(value, float):
        return "number"
    
    if isinstance(value, (datetime, str)):
        value_str = str(value)
        if any(sep in value_str for sep in ['T', '-', ':']):
            return "datetime"
        return "string"
    
    if isinstance(value, list):
        return "array"
    
    if isinstance(value, dict):
        return "object"
    
    return "string"


def _extract_samples(events: List[Any], max_samples: int = MAX_SAMPLES_PER_TABLE) -> List[Dict[str, Any]]:
    """
    Extract sample records from canonical events.
    
    Args:
        events: List of canonical events
        max_samples: Maximum number of samples to extract
    
    Returns:
        List of sample records (dicts)
    """
    samples = []
    
    for event in events[:max_samples]:
        payload = _extract_payload(event)
        
        if hasattr(event, 'event_id'):
            payload['_event_id'] = event.event_id
        
        if hasattr(event, 'timestamp'):
            timestamp = event.timestamp
            if isinstance(timestamp, datetime):
                payload['_timestamp'] = timestamp.isoformat()
            else:
                payload['_timestamp'] = str(timestamp)
        
        samples.append(payload)
    
    return samples


def _compute_schema_fingerprint(schema: Dict[str, str]) -> str:
    """
    Compute a fingerprint hash for a schema.
    
    Args:
        schema: Schema dict mapping field names to types
    
    Returns:
        SHA-256 hash of schema structure
    """
    sorted_fields = sorted(schema.items())
    schema_str = json.dumps(sorted_fields, sort_keys=True)
    
    fingerprint = hashlib.sha256(schema_str.encode()).hexdigest()
    
    return fingerprint[:16]


def _create_dcl_payload(
    tenant_id: str,
    connector_type: str,
    events_by_entity: Dict[str, List[Any]],
    batch_id: str,
    connector_config_id: str
) -> Dict[str, Any]:
    """
    Create DCL-compatible payload from grouped events.
    
    Builds the complete payload structure expected by DCL, including:
    - Metadata (schema_version, batch_id, etc.)
    - Lineage information
    - Table structures with schemas and samples
    
    Args:
        tenant_id: Tenant identifier
        connector_type: Connector type
        events_by_entity: Events grouped by entity_type
        batch_id: Unique batch identifier
        connector_config_id: Connector configuration ID
    
    Returns:
        DCL-compatible payload dict
    """
    total_records = sum(len(events) for events in events_by_entity.values())
    
    first_event = None
    for events in events_by_entity.values():
        if events:
            first_event = events[0]
            break
    
    schema_fingerprint = "unknown"
    if first_event and hasattr(first_event, 'schema_fingerprint'):
        fp = first_event.schema_fingerprint
        if hasattr(fp, 'fingerprint_hash'):
            schema_fingerprint = fp.fingerprint_hash[:16]
    
    tables = {}
    
    for entity_type, events in events_by_entity.items():
        schema = _infer_schema_from_events(events)
        samples = _extract_samples(events)
        
        table_fingerprint = _compute_schema_fingerprint(schema)
        
        tables[entity_type] = {
            "path": "aam://stream",
            "schema": schema,
            "samples": samples,
            "record_count": len(events),
            "schema_fingerprint": table_fingerprint
        }
    
    payload = {
        "schema_version": "v1.0",
        "batch_id": batch_id,
        "connector_type": connector_type,
        "tenant_id": tenant_id,
        "record_count": total_records,
        "lineage": {
            "source": "AAM",
            "connector_config_id": connector_config_id,
            "ingestion_timestamp": datetime.utcnow().isoformat(),
            "schema_fingerprint": schema_fingerprint
        },
        "tables": tables
    }
    
    return payload


def get_dcl_stream_key(tenant_id: str, connector_type: str) -> str:
    """
    Get the Redis Stream key for a tenant/connector combination.
    
    Args:
        tenant_id: Tenant identifier
        connector_type: Connector type
    
    Returns:
        Redis Stream key in format: aam:dcl:{tenant_id}:{connector_type}
    """
    return f"aam:dcl:{tenant_id}:{connector_type}"


def clear_dcl_stream(redis_client, tenant_id: str, connector_type: str) -> bool:
    """
    Clear all messages from a DCL stream.
    
    Useful for testing and development.
    
    Args:
        redis_client: Redis client instance
        tenant_id: Tenant identifier
        connector_type: Connector type
    
    Returns:
        True if stream was deleted, False otherwise
    """
    try:
        stream_key = get_dcl_stream_key(tenant_id, connector_type)
        result = redis_client.delete(stream_key)
        logger.info(f"Cleared DCL stream: {stream_key} (deleted={result})")
        return bool(result)
    except Exception as e:
        logger.error(f"Failed to clear DCL stream: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    print("AAM DCL Output Adapter")
    print("=" * 60)
    print()
    print("This module transforms AAM canonical events into DCL-compatible")
    print("format and publishes them to Redis Streams.")
    print()
    print("Key Functions:")
    print("  - publish_to_dcl_stream(): Main entry point for AAM→DCL transfer")
    print("  - _group_events_by_entity(): Groups events by entity_type")
    print("  - _infer_schema_from_events(): Infers schema from event payloads")
    print("  - _create_dcl_payload(): Creates DCL-compatible payload structure")
    print()
    print("Stream Key Format: aam:dcl:{tenant_id}:{connector_type}")
    print(f"Batch Chunk Size: {BATCH_CHUNK_SIZE} records per message")
    print(f"Max Samples: {MAX_SAMPLES_PER_TABLE} samples per table")
