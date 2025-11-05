"""
AAM Data Ingestion Layer

Responsible for:
1. Reading data from source connectors (CSV files for demo)
2. Generating canonical events
3. Publishing to Redis Streams for DCL consumption
"""

import logging
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import csv
import sys

import redis

# Add paths for imports
current_dir = Path(__file__).parent
aam_root = current_dir.parent
project_root = aam_root.parent

sys.path.insert(0, str(project_root))

from .dcl_output_adapter import publish_to_dcl_stream
from .canonical_processor import CanonicalProcessor
from app.contracts.canonical_event import (
    EntityEvent,
    EventType,
    CanonicalEntityType,
    SchemaFingerprint,
    FieldMapping
)
from app.config.feature_flags import FeatureFlagConfig, FeatureFlag

logger = logging.getLogger(__name__)


def generate_schema_fingerprint(
    field_names: List[str],
    connector_name: str,
    entity_type: str
) -> SchemaFingerprint:
    """
    Generate a schema fingerprint for drift detection.
    
    Args:
        field_names: List of field names in the schema
        connector_name: Source connector name
        entity_type: Entity type (e.g., 'opportunities', 'accounts')
        
    Returns:
        SchemaFingerprint object
    """
    sorted_fields = sorted(field_names)
    fingerprint_data = f"{connector_name}:{entity_type}:{','.join(sorted_fields)}"
    fingerprint_hash = hashlib.sha256(fingerprint_data.encode()).hexdigest()
    
    return SchemaFingerprint(
        fingerprint_hash=fingerprint_hash,
        field_count=len(field_names),
        field_names=sorted_fields,
        schema_version="v1.0",
        connector_name=connector_name,
        entity_type=entity_type
    )


def generate_field_mappings(
    source_fields: List[str],
    canonical_fields: Dict[str, str]
) -> List[FieldMapping]:
    """
    Generate field mappings for canonical events.
    
    Args:
        source_fields: List of source field names
        canonical_fields: Mapping of source field -> canonical field
        
    Returns:
        List of FieldMapping objects
    """
    mappings = []
    
    for source_field in source_fields:
        canonical_field = canonical_fields.get(source_field, source_field.lower())
        
        mappings.append(FieldMapping(
            source_field=source_field,
            canonical_field=canonical_field,
            source_type="string",
            canonical_type="string",
            mapping_method="heuristic",
            confidence_score=0.85
        ))
    
    return mappings


def read_csv_as_canonical_events(
    file_path: str,
    connector_name: str,
    entity_type: str,
    tenant_id: str,
    connector_id: str
) -> List[EntityEvent]:
    """
    Read CSV file and convert to canonical events.
    
    Args:
        file_path: Path to CSV file
        connector_name: Name of the connector (e.g., 'salesforce')
        entity_type: Entity type (e.g., 'opportunity', 'account')
        tenant_id: Tenant ID for multi-tenancy
        connector_id: Unique connector instance ID
        
    Returns:
        List of EntityEvent objects
    """
    events = []
    csv_path = Path(file_path)
    
    if not csv_path.exists():
        logger.warning(f"CSV file not found: {file_path}")
        return events
    
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            field_names = reader.fieldnames or []
            
            schema_fingerprint = generate_schema_fingerprint(
                field_names, connector_name, entity_type
            )
            
            canonical_field_map = {field: field.lower() for field in field_names}
            field_mappings = generate_field_mappings(field_names, canonical_field_map)
            
            for row_idx, row in enumerate(reader):
                payload = {k.lower(): v for k, v in row.items()}
                
                entity_id = payload.get('id', f"{connector_name}-{entity_type}-{row_idx}")
                
                event = EntityEvent(
                    event_id=f"evt-{uuid.uuid4()}",
                    event_type=EventType.ENTITY_CREATED,
                    connector_name=connector_name,
                    connector_id=connector_id,
                    entity_type=_map_entity_type(entity_type),
                    entity_id=str(entity_id),
                    tenant_id=tenant_id,
                    schema_fingerprint=schema_fingerprint,
                    payload=payload,
                    field_mappings=field_mappings,
                    overall_confidence=0.85
                )
                
                events.append(event)
        
        logger.info(f"Generated {len(events)} canonical events from {file_path}")
        
    except Exception as e:
        logger.error(f"Error reading CSV file {file_path}: {e}")
    
    return events


def _map_entity_type(entity_type_str: str) -> CanonicalEntityType:
    """
    Map string entity type to CanonicalEntityType enum.
    
    Args:
        entity_type_str: Entity type string
        
    Returns:
        CanonicalEntityType enum value
    """
    entity_map = {
        'opportunity': CanonicalEntityType.OPPORTUNITY,
        'opportunities': CanonicalEntityType.OPPORTUNITY,
        'account': CanonicalEntityType.ACCOUNT,
        'accounts': CanonicalEntityType.ACCOUNT,
        'contact': CanonicalEntityType.CONTACT,
        'contacts': CanonicalEntityType.CONTACT,
    }
    
    return entity_map.get(entity_type_str.lower(), CanonicalEntityType.CUSTOM)


async def ingest_connector_data(
    connector_name: str,
    connector_id: str,
    tenant_id: str,
    redis_client: redis.Redis,
    data_source_paths: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Ingest data from a connector and publish to Redis Streams.
    
    This is the main entry point for AAM data ingestion.
    
    Args:
        connector_name: Name of the connector (e.g., 'salesforce', 'hubspot')
        connector_id: Unique connector instance ID
        tenant_id: Tenant ID for multi-tenancy
        redis_client: Redis client instance
        data_source_paths: Optional dict mapping entity types to CSV file paths
        
    Returns:
        Dictionary with ingestion results
    """
    logger.info(f"Starting data ingestion for {connector_name} (connector_id: {connector_id})")
    
    if data_source_paths is None:
        data_source_paths = get_default_demo_paths(connector_name)
    
    all_events = []
    results = {
        'connector_name': connector_name,
        'connector_id': connector_id,
        'tenant_id': tenant_id,
        'entity_results': {},
        'total_events': 0,
        'success': True,
        'errors': []
    }
    
    for entity_type, file_path in data_source_paths.items():
        try:
            events = read_csv_as_canonical_events(
                file_path=file_path,
                connector_name=connector_name,
                entity_type=entity_type,
                tenant_id=tenant_id,
                connector_id=connector_id
            )
            
            all_events.extend(events)
            
            results['entity_results'][entity_type] = {
                'events_generated': len(events),
                'file_path': file_path
            }
            
        except Exception as e:
            error_msg = f"Error ingesting {entity_type}: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            results['success'] = False
    
    if all_events:
        # Canonical processing (feature-flagged)
        if FeatureFlagConfig.is_enabled(FeatureFlag.ENABLE_CANONICAL_EVENTS):
            try:
                processor = CanonicalProcessor(redis_client)
                all_events = processor.process_events(all_events)
                logger.info(f"✅ Canonical processing complete: {len(all_events)} events validated")
            except Exception as e:
                error_msg = f"Error in canonical processing: {e}"
                logger.error(error_msg, exc_info=True)
                results['errors'].append(error_msg)
                results['success'] = False
        
        try:
            publish_result = publish_to_dcl_stream(
                tenant_id=tenant_id,
                connector_type=connector_name,
                canonical_events=all_events,
                redis_client=redis_client,
                connector_config_id=connector_id
            )
            
            results['publish_result'] = publish_result
            results['total_events'] = len(all_events)
            
            logger.info(
                f"Published {len(all_events)} events to Redis Stream: "
                f"{publish_result.get('stream_key')}"
            )
            
        except Exception as e:
            error_msg = f"Error publishing to Redis Stream: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            results['success'] = False
    
    return results


def get_default_demo_paths(connector_name: str) -> Dict[str, str]:
    """
    Get default demo CSV file paths for a connector.
    
    Args:
        connector_name: Name of the connector
        
    Returns:
        Dictionary mapping entity types to file paths
    """
    base_path = Path(__file__).parent.parent.parent / "app" / "dcl_engine" / "schemas"
    
    connector_paths = {
        'salesforce': {
            'opportunities': str(base_path / "salesforce" / "Opportunity.csv"),
            'accounts': str(base_path / "salesforce" / "Account.csv"),
        },
        'hubspot': {
            'deals': str(base_path / "hubspot" / "Deals.csv"),
        },
        'dynamics': {
            'opportunities': str(base_path / "dynamics" / "opportunities.csv"),
            'accounts': str(base_path / "dynamics" / "accounts.csv"),
        },
        'supabase': {
            'account_health': str(base_path / "supabase" / "account_health.csv"),
        },
        'mongodb': {
            'account_usage': str(base_path / "mongodb" / "account_usage.csv"),
        },
    }
    
    return connector_paths.get(connector_name, {})
