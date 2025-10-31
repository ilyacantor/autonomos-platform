import os
import csv
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from app.models import CanonicalStream
from services.aam.canonical.mapping_registry import mapping_registry
from services.aam.canonical.schemas import CanonicalEvent, CanonicalMeta, CanonicalSource

logger = logging.getLogger(__name__)


class FileSourceConnector:
    """
    FileSource Connector with auto-discovery and mapping registry integration
    
    Features:
    - Auto-discovers CSV files from mock_sources/ directory
    - Infers entity type from filename prefix (accounts_, opportunities_, contacts_)
    - Extracts system name from filename suffix (_salesforce, _hubspot, etc.)
    - Applies Mapping Registry to transform source data to canonical format
    - Emits CanonicalEvent envelopes to database streams
    - Handles unknown fields in extras
    """
    
    def __init__(self, db: Session, tenant_id: str = "demo-tenant"):
        self.db = db
        self.tenant_id = tenant_id
        # Use root mock_sources/ directory
        self.sources_dir = Path("mock_sources")
        logger.info(f"FileSourceConnector initialized for tenant {tenant_id}, sources_dir: {self.sources_dir}")
    
    def discover_csv_files(self) -> List[Dict[str, str]]:
        """
        Auto-discover CSV files and infer entity/system from filename
        
        Filename convention: {entity}_{system}.csv
        Examples: accounts_salesforce.csv, opportunities_hubspot.csv, contacts_zendesk.csv
        
        Returns:
            List of dicts with keys: filename, entity, system, filepath
        """
        discovered = []
        
        if not self.sources_dir.exists():
            logger.warning(f"Sources directory not found: {self.sources_dir}")
            return discovered
        
        for csv_file in self.sources_dir.glob("*.csv"):
            filename = csv_file.name
            stem = csv_file.stem  # filename without extension
            
            # Parse filename: entity_system
            parts = stem.split('_', 1)
            if len(parts) != 2:
                logger.warning(f"Skipping {filename}: unexpected format (expected entity_system.csv)")
                continue
            
            entity_prefix, system = parts
            
            # Map entity prefix to canonical entity type
            entity_map = {
                'accounts': 'account',
                'opportunities': 'opportunity',
                'contacts': 'contact'
            }
            
            entity = entity_map.get(entity_prefix)
            if not entity:
                logger.warning(f"Skipping {filename}: unknown entity prefix '{entity_prefix}'")
                continue
            
            discovered.append({
                'filename': filename,
                'entity': entity,
                'system': system,
                'filepath': str(csv_file)
            })
            logger.info(f"Discovered: {filename} -> entity={entity}, system={system}")
        
        return discovered
    
    def read_csv(self, filepath: str) -> List[Dict[str, Any]]:
        """Read CSV file and return list of dictionaries"""
        data = []
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(dict(row))
        return data
    
    def build_canonical_event(
        self,
        entity: str,
        system: str,
        source_row: Dict[str, Any],
        trace_id: str
    ) -> Tuple[CanonicalEvent, List[str]]:
        """
        Build CanonicalEvent envelope by applying mapping registry
        
        Returns:
            Tuple of (CanonicalEvent, unknown_fields)
        """
        # Apply mapping registry to transform source data
        canonical_data, unknown_fields = mapping_registry.apply_mapping(
            system=system,
            entity=entity,
            source_row=source_row
        )
        
        # Build metadata
        meta = CanonicalMeta(
            version="1.0.0",
            tenant=self.tenant_id,
            trace_id=trace_id,
            emitted_at=datetime.utcnow()
        )
        
        # Build source metadata
        source = CanonicalSource(
            system="filesource",
            connection_id=f"filesource-{system}",
            schema_version="v1"
        )
        
        # Build canonical event
        event = CanonicalEvent(
            meta=meta,
            source=source,
            entity=entity,
            op="upsert",
            data=canonical_data,
            unknown_fields=unknown_fields
        )
        
        return event, unknown_fields
    
    def emit_canonical_event(self, event: CanonicalEvent):
        """Emit CanonicalEvent to database canonical_streams table"""
        canonical_entry = CanonicalStream(
            tenant_id=self.tenant_id,
            entity=event.entity,
            data=event.data,
            meta=event.meta.dict(),
            source=event.source.dict(),
            emitted_at=event.meta.emitted_at
        )
        self.db.add(canonical_entry)
    
    def replay_entity(self, entity: Optional[str] = None, system: Optional[str] = None) -> Dict[str, Any]:
        """
        Replay CSV files for specified entity/system or all discovered files
        
        Args:
            entity: Filter by entity type (account, opportunity, contact) or None for all
            system: Filter by system name (salesforce, hubspot, etc.) or None for all
        
        Returns:
            Dict with ingestion statistics
        """
        discovered_files = self.discover_csv_files()
        
        # Filter by entity and system if specified
        files_to_process = []
        for file_info in discovered_files:
            if entity and file_info['entity'] != entity:
                continue
            if system and file_info['system'] != system:
                continue
            files_to_process.append(file_info)
        
        if not files_to_process:
            logger.warning(f"No files found matching entity={entity}, system={system}")
            return {
                'files_processed': 0,
                'total_records': 0,
                'records_by_entity': {},
                'records_by_system': {},
                'unknown_fields_count': 0
            }
        
        # Process each file
        trace_id = str(uuid.uuid4())
        stats = {
            'files_processed': 0,
            'total_records': 0,
            'records_by_entity': {},
            'records_by_system': {},
            'unknown_fields_count': 0,
            'files': []
        }
        
        for file_info in files_to_process:
            logger.info(f"Processing {file_info['filename']}...")
            
            # Read CSV data
            rows = self.read_csv(file_info['filepath'])
            
            # Transform and emit each row
            file_unknown_count = 0
            for row in rows:
                event, unknown_fields = self.build_canonical_event(
                    entity=file_info['entity'],
                    system=file_info['system'],
                    source_row=row,
                    trace_id=trace_id
                )
                
                self.emit_canonical_event(event)
                file_unknown_count += len(unknown_fields)
            
            # Update stats
            stats['files_processed'] += 1
            stats['total_records'] += len(rows)
            stats['unknown_fields_count'] += file_unknown_count
            
            # Track by entity
            entity_key = file_info['entity']
            stats['records_by_entity'][entity_key] = stats['records_by_entity'].get(entity_key, 0) + len(rows)
            
            # Track by system
            system_key = file_info['system']
            stats['records_by_system'][system_key] = stats['records_by_system'].get(system_key, 0) + len(rows)
            
            stats['files'].append({
                'filename': file_info['filename'],
                'entity': file_info['entity'],
                'system': file_info['system'],
                'records': len(rows)
            })
            
            logger.info(f"  ✓ Processed {len(rows)} records from {file_info['filename']}")
        
        # Commit all records
        self.db.commit()
        
        logger.info(f"Replay complete: {stats['total_records']} records from {stats['files_processed']} files")
        return stats
    
    def replay_all(self) -> Dict[str, Any]:
        """Replay all discovered CSV files"""
        return self.replay_entity(entity=None, system=None)
