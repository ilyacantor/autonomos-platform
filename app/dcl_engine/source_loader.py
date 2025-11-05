"""
DCL Source Adapter Abstraction Layer

Provides pluggable source adapters for DCL data ingestion:
- FileSourceAdapter: Demo CSV file-based sources (existing path)
- AAMSourceAdapter: AAM Redis Streams-backed sources (new path)

Routing controlled by USE_AAM_AS_SOURCE feature flag.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path
import glob
import os
import json
import pandas as pd
import logging
import warnings

from app.config.feature_flags import FeatureFlagConfig, FeatureFlag

logger = logging.getLogger(__name__)

# Constants (matching app.py)
DCL_BASE_PATH = Path(__file__).parent
SCHEMAS_DIR = str(DCL_BASE_PATH / "schemas")

# Configuration: Externalized for replay workflows and reprocessing scenarios
AAM_IDEMPOTENCY_TTL = int(os.getenv("AAM_IDEMPOTENCY_TTL", "86400"))  # 24 hours default, configurable for longer retention


def infer_types(df: pd.DataFrame) -> Dict[str, str]:
    """
    Infer column types from pandas DataFrame.
    
    Args:
        df: DataFrame to analyze
        
    Returns:
        Dictionary mapping column names to type strings
        (integer, numeric, datetime, string)
    """
    mapping = {}
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_integer_dtype(series):
            mapping[col] = "integer"
        elif pd.api.types.is_float_dtype(series):
            mapping[col] = "numeric"
        else:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    pd.to_datetime(series.dropna().head(50),
                                   format="%Y-%m-%d %H:%M:%S",
                                   errors="raise")
                mapping[col] = "datetime"
            except Exception:
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        pd.to_datetime(series.dropna().head(50), errors="coerce")
                    mapping[col] = "datetime"
                except Exception:
                    mapping[col] = "string"
    return mapping


class BaseSourceAdapter(ABC):
    """Abstract base class for DCL data source adapters"""
    
    @abstractmethod
    def discover_sources(self, tenant_id: str) -> List[str]:
        """
        Discover available data sources for tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            List of available source IDs (e.g., ['salesforce', 'hubspot'])
        """
        pass
    
    @abstractmethod
    def load_tables(self, source_id: str, tenant_id: str) -> Dict[str, Any]:
        """
        Load tables from source with schema and samples.
        
        Args:
            source_id: Source system identifier (e.g., 'salesforce')
            tenant_id: Tenant identifier
            
        Returns:
            Dictionary mapping table names to table metadata:
            {
                "table_name": {
                    "path": "/path/to/file.csv",  # For file sources
                    "schema": {"col1": "string", "col2": "integer", ...},
                    "samples": [{...}, {...}, ...]  # Sample rows
                }
            }
        """
        pass
    
    @abstractmethod  
    def get_source_metadata(self, source_id: str) -> Dict[str, Any]:
        """
        Get metadata about the source.
        
        Args:
            source_id: Source system identifier
            
        Returns:
            Dictionary with source metadata (connector type, last_sync, etc.)
        """
        pass


class FileSourceAdapter(BaseSourceAdapter):
    """
    Demo file-based source adapter (CSV files).
    
    Loads data from CSV files in schemas/{source_id}/ directory.
    Maintains backward compatibility with existing DCL demo mode.
    """
    
    def discover_sources(self, tenant_id: str) -> List[str]:
        """
        Discover available source directories.
        
        Args:
            tenant_id: Tenant identifier (unused in file mode)
            
        Returns:
            List of source directory names in schemas/
        """
        schemas_path = Path(SCHEMAS_DIR)
        if not schemas_path.exists():
            logger.warning(f"Schemas directory not found: {SCHEMAS_DIR}")
            return []
        
        sources = []
        for item in schemas_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                csv_files = list(item.glob("*.csv"))
                if csv_files:
                    sources.append(item.name)
        
        logger.info(f"📂 Discovered {len(sources)} file-based sources: {sources}")
        return sources
    
    def load_tables(self, source_id: str, tenant_id: str) -> Dict[str, Any]:
        """
        Load CSV tables from schemas/{source_id}/ directory.
        
        Replicates logic from snapshot_tables_from_dir() for backward compatibility.
        
        Args:
            source_id: Source directory name (e.g., 'salesforce')
            tenant_id: Tenant identifier (unused in file mode)
            
        Returns:
            Dictionary mapping table names to table metadata
        """
        dir_path = os.path.join(SCHEMAS_DIR, source_id)
        
        if not os.path.exists(dir_path):
            logger.warning(f"Source directory not found: {dir_path}")
            return {}
        
        tables = {}
        csv_pattern = os.path.join(dir_path, "*.csv")
        
        for path in glob.glob(csv_pattern):
            tname = os.path.splitext(os.path.basename(path))[0]
            
            try:
                df = pd.read_csv(path)
                tables[tname] = {
                    "path": path,
                    "schema": infer_types(df),
                    "samples": df.head(8).to_dict(orient="records")
                }
                logger.debug(f"  Loaded table '{tname}' from {path}")
            except Exception as e:
                logger.error(f"  Failed to load table '{tname}' from {path}: {e}")
                continue
        
        logger.info(f"📂 Loaded {len(tables)} tables from source '{source_id}'")
        return tables
    
    def get_source_metadata(self, source_id: str) -> Dict[str, Any]:
        """
        Get metadata about file-based source.
        
        Args:
            source_id: Source directory name
            
        Returns:
            Dictionary with source metadata
        """
        dir_path = os.path.join(SCHEMAS_DIR, source_id)
        
        if not os.path.exists(dir_path):
            return {
                "source_id": source_id,
                "type": "file",
                "status": "not_found",
                "path": dir_path
            }
        
        csv_files = glob.glob(os.path.join(dir_path, "*.csv"))
        
        return {
            "source_id": source_id,
            "type": "file",
            "status": "available",
            "path": dir_path,
            "table_count": len(csv_files),
            "tables": [os.path.splitext(os.path.basename(f))[0] for f in csv_files]
        }


class AAMSourceAdapter(BaseSourceAdapter):
    """
    AAM-backed source adapter (Redis Streams).
    
    Reads canonical events from AAM connectors via Redis Streams:
    - Stream key format: aam:dcl:{tenant_id}:{connector_type}
    - Consumer group: dcl_engine:{tenant_id}
    - Idempotent batch processing with batch_id tracking
    - Real-time data from live AAM connectors
    - Phase 4: Extracts data quality metadata (drift_status, repair_summary, data_lineage)
    """
    
    def __init__(self):
        """Initialize AAM adapter (Redis client loaded lazily to avoid circular import)."""
        self.redis = None
        self.logger = logging.getLogger(__name__)
        self.logger.info("🔌 AAMSourceAdapter initialized (Redis will be loaded on first use)"  )
    
    def _get_redis_client(self):
        """
        Get Redis client, loading it lazily to avoid circular import issues.
        
        Returns:
            Redis client wrapper
            
        Raises:
            RuntimeError: If Redis is not available
        """
        if self.redis is None:
            import app.dcl_engine.app as dcl_app
            
            if not dcl_app.redis_available or not dcl_app.redis_client:
                raise RuntimeError("Redis required for AAM source adapter but not available")
            
            self.redis = dcl_app.redis_client
            self.logger.info("✅ AAMSourceAdapter connected to Redis")
        
        return self.redis
    
    def discover_sources(self, tenant_id: str) -> List[str]:
        """
        Discover available AAM connectors for tenant by scanning Redis streams.
        
        Scans for streams matching pattern: aam:dcl:{tenant_id}:*
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            List of available connector IDs (e.g., ['salesforce', 'supabase'])
        """
        try:
            redis = self._get_redis_client()
            pattern = f"aam:dcl:{tenant_id}:*"
            sources = []
            
            # Use SCAN to find matching stream keys
            cursor = 0
            while True:
                cursor, keys = redis._client.scan(cursor, match=pattern, count=100)
                
                # Extract connector type from each key
                for key in keys:
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    # Parse: aam:dcl:{tenant_id}:{connector_type}
                    parts = key_str.split(':')
                    if len(parts) >= 4:
                        connector_type = parts[3]
                        if connector_type not in sources:
                            sources.append(connector_type)
                
                if cursor == 0:
                    break
            
            self.logger.info(f"📡 Discovered {len(sources)} AAM sources for tenant '{tenant_id}': {sources}")
            return sorted(sources)
            
        except Exception as e:
            self.logger.error(f"Failed to discover AAM sources for tenant '{tenant_id}': {e}", exc_info=True)
            return []
    
    def load_tables(self, source_id: str, tenant_id: str) -> Dict[str, Any]:
        """
        Load tables from AAM Redis Stream.
        
        Reads all messages from stream using XRANGE (no consumer groups for demo data).
        Implements idempotency to prevent duplicate processing.
        
        Args:
            source_id: Connector identifier (e.g., 'salesforce')
            tenant_id: Tenant identifier
            
        Returns:
            Dictionary mapping table names to table metadata (same format as FileSourceAdapter)
        """
        stream_key = f"aam:dcl:{tenant_id}:{source_id}"
        
        try:
            redis = self._get_redis_client()
            self.logger.info(f"🔍 Loading tables from stream '{stream_key}'...")
            
            # Read ALL messages from stream using XRANGE (from beginning '-' to end '+')
            # This is simpler than consumer groups and works well for demo/development
            messages = redis._client.xrange(
                stream_key,
                min='-',  # Start from beginning
                max='+',  # Read to end
                count=100  # Read up to 100 messages
            )
            
            self.logger.info(f"📦 XRANGE returned {len(messages)} messages from '{stream_key}'")
            
            if not messages:
                self.logger.info(f"ℹ️ No messages in stream '{stream_key}'")
                return {}
            
            # Process messages and combine tables
            all_tables = {}
            processed_batch_ids = []
            
            # Aggregate metadata across all events for this source
            aggregated_metadata = {
                "drift_detected": False,
                "repair_processed": False,
                "auto_applied_count": 0,
                "hitl_queued_count": 0,
                "rejected_count": 0,
                "processing_stages": set(),
                "transformations_applied": set(),
                "sources_with_drift": [],
                "low_confidence_sources": [],
                "events_processed": 0,
                "data_quality_scores": []
            }
            
            # XRANGE returns list of (message_id, data) tuples directly
            for message_id, data in messages:
                try:
                    # Parse payload from message
                    payload_json = data.get(b'payload')
                    if not payload_json:
                        self.logger.warning(f"Message {message_id} missing 'payload' field")
                        continue
                    
                    payload = json.loads(payload_json)
                    batch_id = payload.get('batch_id')
                    
                    # Check idempotency
                    if batch_id and self._is_batch_processed(tenant_id, batch_id):
                        self.logger.debug(f"Skipping already processed batch: {batch_id}")
                        continue
                    
                    # Extract tables from payload - handle both flat and envelope formats
                    # Phase 4 canonical events may nest tables under canonical_event/canonical_data envelope
                    tables = {}
                    
                    # Try envelope format first (Phase 4)
                    if 'canonical_event' in payload:
                        # Format: payload['canonical_event']['data']['tables']
                        canonical_event = payload['canonical_event']
                        if isinstance(canonical_event, dict) and 'data' in canonical_event:
                            tables = canonical_event['data'].get('tables', {})
                        elif isinstance(canonical_event, dict) and 'tables' in canonical_event:
                            tables = canonical_event.get('tables', {})
                    elif 'canonical_data' in payload:
                        # Format: payload['canonical_data']['tables']
                        canonical_data = payload['canonical_data']
                        if isinstance(canonical_data, dict):
                            tables = canonical_data.get('tables', {})
                    else:
                        # Flat format (current demo data): payload['tables']
                        tables = payload.get('tables', {})
                    
                    self.logger.info(f"📦 Extracted {len(tables)} tables from {source_id} (batch: {batch_id})")
                    
                    # Merge tables (latest wins if same table name)
                    for table_name, table_data in tables.items():
                        all_tables[table_name] = table_data
                    
                    # Extract Phase 4 metadata from canonical event
                    event_metadata = self.extract_metadata(payload)
                    
                    # Aggregate metadata across events
                    if event_metadata.get("drift_detected"):
                        aggregated_metadata["drift_detected"] = True
                        if source_id not in aggregated_metadata["sources_with_drift"]:
                            aggregated_metadata["sources_with_drift"].append(source_id)
                    
                    if event_metadata.get("repair_processed"):
                        aggregated_metadata["repair_processed"] = True
                    
                    aggregated_metadata["auto_applied_count"] += event_metadata.get("auto_applied_count", 0)
                    aggregated_metadata["hitl_queued_count"] += event_metadata.get("hitl_queued_count", 0)
                    aggregated_metadata["rejected_count"] += event_metadata.get("rejected_count", 0)
                    
                    # Collect processing stages
                    for stage in event_metadata.get("processing_stages", []):
                        aggregated_metadata["processing_stages"].add(stage)
                    
                    # Collect transformations
                    for transform in event_metadata.get("transformations_applied", []):
                        aggregated_metadata["transformations_applied"].add(transform)
                    
                    # Track data quality scores for averaging
                    if event_metadata.get("data_quality_score") is not None:
                        aggregated_metadata["data_quality_scores"].append(event_metadata["data_quality_score"])
                    
                    # Track low confidence sources
                    if event_metadata.get("overall_confidence") is not None and event_metadata["overall_confidence"] < 0.7:
                        if source_id not in aggregated_metadata["low_confidence_sources"]:
                            aggregated_metadata["low_confidence_sources"].append(source_id)
                    
                    aggregated_metadata["events_processed"] += 1
                    
                    # Mark batch as processed
                    if batch_id:
                        self._mark_batch_processed(tenant_id, batch_id)
                        processed_batch_ids.append(batch_id)
                    
                    self.logger.info(f"✅ Processed batch {batch_id} from stream '{stream_key}'")
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse JSON from message {message_id}: {e}")
                    continue
                except Exception as e:
                    self.logger.error(f"Error processing message {message_id}: {e}", exc_info=True)
                    continue
            
            # Finalize aggregated metadata
            aggregated_metadata["processing_stages"] = list(aggregated_metadata["processing_stages"])
            aggregated_metadata["transformations_applied"] = list(aggregated_metadata["transformations_applied"])
            
            # Calculate overall data quality score
            if aggregated_metadata["data_quality_scores"]:
                aggregated_metadata["overall_data_quality_score"] = sum(aggregated_metadata["data_quality_scores"]) / len(aggregated_metadata["data_quality_scores"])
            else:
                aggregated_metadata["overall_data_quality_score"] = None
            
            # Remove temporary list
            del aggregated_metadata["data_quality_scores"]
            
            # Store aggregated metadata in Redis for AgentExecutor access
            if aggregated_metadata["events_processed"] > 0:
                self.store_metadata_in_redis(tenant_id, source_id, aggregated_metadata)
                self.logger.info(f"📊 Aggregated metadata: {aggregated_metadata['events_processed']} events, drift={aggregated_metadata['drift_detected']}, repairs={aggregated_metadata['auto_applied_count']}")
            
            self.logger.info(f"📡 Loaded {len(all_tables)} tables from AAM source '{source_id}' (processed {len(processed_batch_ids)} batches)")
            return all_tables
            
        except Exception as e:
            self.logger.error(f"Failed to load tables from AAM source '{source_id}': {e}", exc_info=True)
            return {}
    
    def get_source_metadata(self, source_id: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metadata about AAM connector from stream info.
        
        Args:
            source_id: Connector identifier
            tenant_id: Tenant identifier (optional, for future use)
            
        Returns:
            Dictionary with connector metadata
        """
        # If tenant_id not provided, try to infer from context or use default
        if not tenant_id:
            tenant_id = "default"
        
        stream_key = f"aam:dcl:{tenant_id}:{source_id}"
        
        try:
            redis = self._get_redis_client()
            # Get stream info
            try:
                stream_info = redis._client.xinfo_stream(stream_key)
            except Exception as e:
                # Stream doesn't exist or error
                return {
                    "source_id": source_id,
                    "type": "aam",
                    "status": "not_found",
                    "stream_key": stream_key,
                    "error": str(e)
                }
            
            # Read last message to get payload metadata
            last_messages = redis._client.xrevrange(stream_key, count=1)
            
            metadata = {
                "source_id": source_id,
                "type": "aam",
                "status": "available",
                "stream_key": stream_key,
                "message_count": stream_info.get(b'length', 0) if isinstance(stream_info.get(b'length'), int) else 0,
                "first_entry_id": stream_info.get(b'first-entry'),
                "last_entry_id": stream_info.get(b'last-entry'),
            }
            
            # Extract metadata from last message if available
            if last_messages:
                message_id, data = last_messages[0]
                try:
                    payload_json = data.get(b'payload')
                    if payload_json:
                        payload = json.loads(payload_json)
                        
                        metadata.update({
                            "connector_type": payload.get('connector_type'),
                            "schema_version": payload.get('schema_version'),
                            "last_batch_id": payload.get('batch_id'),
                            "record_count": payload.get('record_count'),
                            "lineage": payload.get('lineage', {}),
                            "table_count": len(payload.get('tables', {})),
                            "tables": list(payload.get('tables', {}).keys())
                        })
                except Exception as e:
                    self.logger.warning(f"Failed to parse last message metadata: {e}")
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to get metadata for AAM source '{source_id}': {e}", exc_info=True)
            return {
                "source_id": source_id,
                "type": "aam",
                "status": "error",
                "error": str(e)
            }
    
    def _create_consumer_group(self, stream_key: str, group_name: str):
        """
        Create consumer group if it doesn't exist.
        
        Args:
            stream_key: Redis stream key
            group_name: Consumer group name
        """
        try:
            redis = self._get_redis_client()
            # Try to create consumer group
            # MKSTREAM creates stream if it doesn't exist
            # Start reading from beginning with '0'
            redis._client.xgroup_create(stream_key, group_name, id='0', mkstream=True)
            self.logger.info(f"Created consumer group '{group_name}' for stream '{stream_key}'")
        except Exception as e:
            # Group likely already exists (BUSYGROUP error)
            error_msg = str(e).lower()
            if 'busygroup' in error_msg or 'exists' in error_msg:
                self.logger.debug(f"Consumer group '{group_name}' already exists for stream '{stream_key}'")
            else:
                self.logger.warning(f"Error creating consumer group: {e}")
    
    def _is_batch_processed(self, tenant_id: str, batch_id: str) -> bool:
        """
        Check if batch has already been processed.
        
        Uses Redis SET to track processed batch IDs for idempotency.
        
        Args:
            tenant_id: Tenant identifier
            batch_id: Batch identifier
            
        Returns:
            True if batch already processed, False otherwise
        """
        try:
            redis = self._get_redis_client()
            set_key = f"dcl:processed_batches:{tenant_id}"
            result = redis._client.sismember(set_key, batch_id)
            return bool(result)
        except Exception as e:
            self.logger.error(f"Error checking batch processed status: {e}")
            return False
    
    def _mark_batch_processed(self, tenant_id: str, batch_id: str):
        """
        Mark batch as processed for idempotency tracking.
        
        Adds batch_id to Redis SET with 24-hour expiry on the set.
        
        Args:
            tenant_id: Tenant identifier
            batch_id: Batch identifier
        """
        try:
            redis = self._get_redis_client()
            set_key = f"dcl:processed_batches:{tenant_id}"
            redis._client.sadd(set_key, batch_id)
            # Set configurable expiry to prevent unbounded growth (default 24h)
            redis._client.expire(set_key, AAM_IDEMPOTENCY_TTL)
        except Exception as e:
            self.logger.error(f"Error marking batch as processed: {e}")
    
    def extract_metadata(self, canonical_event: dict) -> dict:
        """
        Extract Phase 4 metadata (drift_status, repair_summary, data_lineage) from canonical event.
        
        Handles backward compatibility - gracefully handles events without Phase 4 fields.
        
        Args:
            canonical_event: Canonical event payload from Redis stream
            
        Returns:
            Dictionary with extracted metadata:
            {
                "drift_detected": bool,
                "drift_severity": str,
                "repair_processed": bool,
                "auto_applied_count": int,
                "hitl_queued_count": int,
                "processing_stages": list,
                "data_quality_score": float,
                ...
            }
        """
        metadata = {
            "drift_detected": False,
            "repair_processed": False,
            "auto_applied_count": 0,
            "hitl_queued_count": 0,
            "rejected_count": 0,
            "processing_stages": [],
            "data_quality_score": None
        }
        
        try:
            # Extract drift_status if present
            drift_status = canonical_event.get("drift_status")
            if drift_status and isinstance(drift_status, dict):
                metadata["drift_detected"] = drift_status.get("drift_detected", False)
                metadata["drift_severity"] = drift_status.get("drift_severity")
                metadata["drift_type"] = drift_status.get("drift_type")
                metadata["drift_event_id"] = drift_status.get("drift_event_id")
                metadata["repair_attempted"] = drift_status.get("repair_attempted", False)
                metadata["repair_successful"] = drift_status.get("repair_successful", False)
                metadata["requires_human_review"] = drift_status.get("requires_human_review", False)
                
                if drift_status.get("detected_at"):
                    metadata["drift_detected_at"] = drift_status["detected_at"]
                if drift_status.get("resolved_at"):
                    metadata["drift_resolved_at"] = drift_status["resolved_at"]
            
            # Extract repair_summary if present
            repair_summary = canonical_event.get("repair_summary")
            if repair_summary and isinstance(repair_summary, dict):
                metadata["repair_processed"] = repair_summary.get("repair_processed", False)
                metadata["auto_applied_count"] = repair_summary.get("auto_applied_count", 0)
                metadata["hitl_queued_count"] = repair_summary.get("hitl_queued_count", 0)
                metadata["rejected_count"] = repair_summary.get("rejected_count", 0)
                metadata["overall_confidence"] = repair_summary.get("overall_confidence")
                
                # Extract repair history for detailed tracking
                repair_history = repair_summary.get("repair_history", [])
                if repair_history:
                    metadata["repair_history_count"] = len(repair_history)
                    metadata["repair_methods"] = list(set([r.get("applied_by") for r in repair_history if r.get("applied_by")]))
            
            # Extract data_lineage if present
            data_lineage = canonical_event.get("data_lineage")
            if data_lineage and isinstance(data_lineage, dict):
                metadata["processing_stages"] = data_lineage.get("processing_stages", [])
                metadata["data_quality_score"] = data_lineage.get("data_quality_score")
                metadata["source_system"] = data_lineage.get("source_system")
                metadata["source_connector_id"] = data_lineage.get("source_connector_id")
                metadata["transformations_applied"] = data_lineage.get("transformations_applied", [])
                metadata["processor_version"] = data_lineage.get("processor_version", "1.0")
                
                if data_lineage.get("processing_timestamp"):
                    metadata["processing_timestamp"] = data_lineage["processing_timestamp"]
            
            # Add metadata extraction timestamp
            from datetime import datetime
            metadata["metadata_extracted_at"] = datetime.utcnow().isoformat()
            
        except Exception as e:
            self.logger.warning(f"Error extracting metadata from canonical event: {e}")
        
        return metadata
    
    def store_metadata_in_redis(self, tenant_id: str, source_id: str, metadata: dict):
        """
        Store aggregated metadata in Redis for fast access by AgentExecutor.
        
        Uses hybrid storage approach:
        - Redis: Fast access for real-time agent execution
        - Key format: dcl:metadata:{tenant_id}:{source_id}
        - TTL: 24 hours (configurable)
        
        Args:
            tenant_id: Tenant identifier
            source_id: Source connector identifier
            metadata: Extracted metadata dictionary
        """
        try:
            redis = self._get_redis_client()
            redis_key = f"dcl:metadata:{tenant_id}:{source_id}"
            
            # Store as JSON string
            metadata_json = json.dumps(metadata)
            
            # Store with 24-hour expiry
            redis._client.setex(redis_key, AAM_IDEMPOTENCY_TTL, metadata_json)
            
            self.logger.debug(f"📊 Stored metadata in Redis: {redis_key}")
            
        except Exception as e:
            self.logger.error(f"Failed to store metadata in Redis for {source_id}: {e}")


def get_source_adapter() -> BaseSourceAdapter:
    """
    Factory function to get appropriate source adapter based on feature flags.
    
    Returns:
        FileSourceAdapter when USE_AAM_AS_SOURCE=False (default)
        AAMSourceAdapter when USE_AAM_AS_SOURCE=True
    """
    if FeatureFlagConfig.is_enabled(FeatureFlag.USE_AAM_AS_SOURCE):
        try:
            adapter = AAMSourceAdapter()
            adapter_type = "AAMSourceAdapter"
            logger.info(f"📂 Using {adapter_type} for data ingestion")
        except Exception as e:
            logger.error(f"❌ Failed to initialize AAMSourceAdapter: {e}", exc_info=True)
            logger.warning(f"⚠️ Falling back to FileSourceAdapter due to AAM init failure")
            adapter = FileSourceAdapter()
            adapter_type = "FileSourceAdapter (fallback)"
            logger.info(f"📂 Using {adapter_type} for data ingestion")
    else:
        adapter = FileSourceAdapter()
        adapter_type = "FileSourceAdapter"
        logger.info(f"📂 Using {adapter_type} for data ingestion")
    
    return adapter
