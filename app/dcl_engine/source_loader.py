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
    """
    
    def __init__(self):
        """Initialize AAM adapter with Redis client."""
        from app.dcl_engine.app import redis_client, redis_available
        
        if not redis_available:
            raise RuntimeError("Redis required for AAM source adapter but not available")
        
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)
        self.logger.info("🔌 AAMSourceAdapter initialized with Redis client")
    
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
            pattern = f"aam:dcl:{tenant_id}:*"
            sources = []
            
            # Use SCAN to find matching stream keys
            cursor = 0
            while True:
                cursor, keys = self.redis._client.scan(cursor, match=pattern, count=100)
                
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
        
        Reads from stream using consumer groups for reliable processing.
        Implements idempotency to prevent duplicate processing.
        
        Args:
            source_id: Connector identifier (e.g., 'salesforce')
            tenant_id: Tenant identifier
            
        Returns:
            Dictionary mapping table names to table metadata (same format as FileSourceAdapter)
        """
        stream_key = f"aam:dcl:{tenant_id}:{source_id}"
        group_name = f"dcl_engine:{tenant_id}"
        consumer_name = f"dcl_worker_{os.getpid()}"
        
        try:
            # Ensure consumer group exists
            self._create_consumer_group(stream_key, group_name)
            
            # Read messages from stream using consumer group
            # Use '>' to read only new messages not yet delivered to this group
            messages = self.redis._client.xreadgroup(
                groupname=group_name,
                consumername=consumer_name,
                streams={stream_key: '>'},
                count=10,  # Read up to 10 messages
                block=None  # Non-blocking: return immediately if no messages
            )
            
            if not messages:
                self.logger.info(f"ℹ️ No new messages in stream '{stream_key}' (group: {group_name})")
                return {}
            
            # Process messages and combine tables
            all_tables = {}
            processed_batch_ids = []
            
            for stream, message_list in messages:
                for message_id, data in message_list:
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
                            self.logger.info(f"Skipping already processed batch: {batch_id}")
                            # Acknowledge message even if already processed
                            self.redis._client.xack(stream_key, group_name, message_id)
                            continue
                        
                        # Extract tables from payload
                        tables = payload.get('tables', {})
                        
                        # Merge tables (latest wins if same table name)
                        for table_name, table_data in tables.items():
                            all_tables[table_name] = table_data
                        
                        # Mark batch as processed
                        if batch_id:
                            self._mark_batch_processed(tenant_id, batch_id)
                            processed_batch_ids.append(batch_id)
                        
                        # Acknowledge message after successful processing
                        self.redis._client.xack(stream_key, group_name, message_id)
                        
                        self.logger.info(f"✅ Processed batch {batch_id} from stream '{stream_key}'")
                        
                    except json.JSONDecodeError as e:
                        self.logger.error(f"Failed to parse JSON from message {message_id}: {e}")
                        continue
                    except Exception as e:
                        self.logger.error(f"Error processing message {message_id}: {e}", exc_info=True)
                        continue
            
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
            # Get stream info
            try:
                stream_info = self.redis._client.xinfo_stream(stream_key)
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
            last_messages = self.redis._client.xrevrange(stream_key, count=1)
            
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
            # Try to create consumer group
            # MKSTREAM creates stream if it doesn't exist
            # Start reading from beginning with '0'
            self.redis._client.xgroup_create(stream_key, group_name, id='0', mkstream=True)
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
            set_key = f"dcl:processed_batches:{tenant_id}"
            result = self.redis._client.sismember(set_key, batch_id)
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
            set_key = f"dcl:processed_batches:{tenant_id}"
            self.redis._client.sadd(set_key, batch_id)
            # Set configurable expiry to prevent unbounded growth (default 24h)
            self.redis._client.expire(set_key, AAM_IDEMPOTENCY_TTL)
        except Exception as e:
            self.logger.error(f"Error marking batch as processed: {e}")


def get_source_adapter() -> BaseSourceAdapter:
    """
    Factory function to get appropriate source adapter based on feature flags.
    
    Returns:
        FileSourceAdapter when USE_AAM_AS_SOURCE=False (default)
        AAMSourceAdapter when USE_AAM_AS_SOURCE=True
    """
    if FeatureFlagConfig.is_enabled(FeatureFlag.USE_AAM_AS_SOURCE):
        adapter = AAMSourceAdapter()
        adapter_type = "AAMSourceAdapter"
        logger.info(f"📂 Using {adapter_type} for data ingestion")
    else:
        adapter = FileSourceAdapter()
        adapter_type = "FileSourceAdapter"
        logger.info(f"📂 Using {adapter_type} for data ingestion")
    
    return adapter
