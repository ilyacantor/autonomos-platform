"""
Mapping Registry for vendor → canonical field mappings
Supports YAML/JSON storage with CRUD operations
RACI P1.5: Integrated with DCL mapping API behind feature flag
"""
import os
import json
import yaml
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

from shared.feature_flags import get_feature_flag
from shared.dcl_mapping_client import DCLMappingClient

logger = logging.getLogger(__name__)

ENABLE_DUAL_READ_VALIDATION = os.getenv("ENABLE_DUAL_READ_VALIDATION", "false").lower() == "true"


class MappingRegistry:
    """Registry for managing field mappings from source systems to canonical schemas"""
    
    def __init__(self, registry_path: str = "services/aam/canonical/mappings", dcl_client: Optional[DCLMappingClient] = None):
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(parents=True, exist_ok=True)
        self._mappings_cache: Dict[str, Dict] = {}
        self._load_all_mappings()
        
        self.dcl_client = dcl_client or DCLMappingClient()
        logger.info("MappingRegistry initialized with DCL client support")
    
    def _load_all_mappings(self):
        """Load all mapping files into cache (YAML fallback)"""
        for file_path in self.registry_path.glob("*.yaml"):
            system = file_path.stem
            with open(file_path, 'r') as f:
                self._mappings_cache[system] = yaml.safe_load(f)
        
        for file_path in self.registry_path.glob("*.json"):
            system = file_path.stem
            with open(file_path, 'r') as f:
                self._mappings_cache[system] = json.load(f)
        
        logger.info(f"Loaded {len(self._mappings_cache)} YAML/JSON mappings (fallback)")
    
    def _get_yaml_mapping(self, system: str, entity: str) -> Optional[Dict[str, Any]]:
        """Get mapping from YAML cache (legacy)"""
        if system not in self._mappings_cache:
            return None
        
        mappings = self._mappings_cache[system]
        return mappings.get(entity, {})
    
    def _compare_mappings(self, dcl_mapping: Dict, yaml_mapping: Dict, system: str, entity: str):
        """Compare DCL API vs YAML mappings for validation (dual-read mode)"""
        dcl_fields = dcl_mapping.get('fields', {})
        yaml_fields = yaml_mapping.get('fields', {})
        
        if dcl_fields != yaml_fields:
            logger.warning(
                f"⚠️ Mapping mismatch for {system}.{entity}: "
                f"DCL has {len(dcl_fields)} fields, YAML has {len(yaml_fields)} fields"
            )
            
            dcl_keys = set(dcl_fields.keys())
            yaml_keys = set(yaml_fields.keys())
            
            missing_in_dcl = yaml_keys - dcl_keys
            missing_in_yaml = dcl_keys - yaml_keys
            
            if missing_in_dcl:
                logger.warning(f"  Missing in DCL: {missing_in_dcl}")
            if missing_in_yaml:
                logger.warning(f"  Missing in YAML: {missing_in_yaml}")
            
            from shared.redis_client import get_redis_client
            redis = get_redis_client()
            if redis:
                redis.incr("mapping_mismatch_count")
    
    def get_mapping(self, system: str, entity: str, tenant_id: str = "default") -> Optional[Dict[str, Any]]:
        """
        Get field mapping for a system and entity.
        Uses DCL API if feature flag enabled, falls back to YAML.
        """
        use_dcl = get_feature_flag("USE_DCL_MAPPING_REGISTRY", tenant_id)
        
        if use_dcl and self.dcl_client:
            try:
                logger.debug(f"Using DCL API for {system}.{entity}")
                
                dcl_mapping = self.dcl_client.get_entity_mapping(system, entity, tenant_id)
                
                if dcl_mapping and dcl_mapping.get("fields"):
                    if ENABLE_DUAL_READ_VALIDATION:
                        yaml_mapping = self._get_yaml_mapping(system, entity)
                        if yaml_mapping:
                            self._compare_mappings(dcl_mapping, yaml_mapping, system, entity)
                    
                    return dcl_mapping
                else:
                    logger.warning(f"DCL API returned empty or no mapping for {system}.{entity}, falling back to YAML")
                    return self._get_yaml_mapping(system, entity)
                    
            except Exception as e:
                logger.error(f"DCL API error for {system}.{entity}: {e}, falling back to YAML")
                return self._get_yaml_mapping(system, entity)
        else:
            logger.debug(f"Using YAML for {system}.{entity} (feature flag disabled)")
            return self._get_yaml_mapping(system, entity)
    
    def apply_mapping(
        self, 
        system: str, 
        entity: str, 
        source_row: Dict[str, Any]
    ) -> tuple[Dict[str, Any], List[str]]:
        """
        Apply mapping to transform source row to canonical format
        Returns: (canonical_data, unknown_fields)
        """
        mapping = self.get_mapping(system, entity)
        if not mapping:
            # No mapping found - return source data as-is with high unknown rate
            return source_row, list(source_row.keys())
        
        canonical_data = {}
        unknown_fields = []
        field_mappings = mapping.get('fields', {})
        
        # field_mappings format: {canonical_field: source_field}
        # e.g., {"opportunity_id": "Id", "name": "Name"}
        # Need to invert to find canonical field for each source field
        
        for source_field, source_value in source_row.items():
            # Find which canonical field this source field maps to
            canonical_field = None
            mapping_config = None
            
            for canon_name, source_name in field_mappings.items():
                # Handle simple string mapping
                if isinstance(source_name, str) and source_name == source_field:
                    canonical_field = canon_name
                    canonical_data[canonical_field] = self._coerce_value(source_value, canonical_field)
                    break
                # Handle complex mapping with transforms
                elif isinstance(source_name, dict):
                    if source_name.get('source') == source_field:
                        canonical_field = canon_name
                        transform = source_name.get('transform')
                        value = self._apply_transform(source_value, transform) if transform else source_value
                        canonical_data[canonical_field] = self._coerce_value(value, canonical_field)
                        break
            
            # If no mapping found, add to extras
            if canonical_field is None:
                unknown_fields.append(source_field)
                if 'extras' not in canonical_data:
                    canonical_data['extras'] = {}
                canonical_data['extras'][source_field] = source_value
        
        return canonical_data, unknown_fields
    
    def _coerce_value(self, value: Any, field_name: str) -> Any:
        """Coerce value to expected type based on field name conventions"""
        if value is None or value == '':
            return None
        
        # Date/time fields
        if any(x in field_name for x in ['_at', '_date', 'date', 'created', 'updated', 'modified']):
            try:
                if isinstance(value, str):
                    # Try ISO format first
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                return value
            except:
                return value
        
        # Numeric fields
        if 'amount' in field_name or 'revenue' in field_name:
            try:
                return float(value) if value else None
            except:
                return None
        
        if 'probability' in field_name:
            try:
                prob = float(value) if value else None
                return min(max(prob, 0), 100) if prob is not None else None
            except:
                return None
        
        if 'employees' in field_name or field_name.endswith('_count'):
            try:
                return int(value) if value else None
            except:
                return None
        
        # String fields - trim and clean
        if isinstance(value, str):
            return value.strip()
        
        return value
    
    def _apply_transform(self, value: Any, transform: str) -> Any:
        """Apply transformation function to value"""
        if transform == 'uppercase':
            return str(value).upper() if value else value
        elif transform == 'lowercase':
            return str(value).lower() if value else value
        elif transform == 'trim':
            return str(value).strip() if value else value
        elif transform == 'boolean':
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'active')
            return bool(value)
        return value
    
    def save_mapping(self, system: str, entity: str, mapping: Dict[str, Any], format: str = 'yaml'):
        """Save or update mapping for a system and entity"""
        if system not in self._mappings_cache:
            self._mappings_cache[system] = {}
        
        self._mappings_cache[system][entity] = mapping
        
        file_path = self.registry_path / f"{system}.{format}"
        if format == 'yaml':
            with open(file_path, 'w') as f:
                yaml.dump(self._mappings_cache[system], f, default_flow_style=False)
        else:
            with open(file_path, 'w') as f:
                json.dump(self._mappings_cache[system], f, indent=2)
    
    def list_mappings(self) -> List[Dict[str, str]]:
        """List all available mappings"""
        mappings = []
        for system, entities in self._mappings_cache.items():
            for entity in entities.keys():
                mappings.append({
                    'system': system,
                    'entity': entity,
                    'field_count': len(entities[entity].get('fields', {}))
                })
        return mappings


# Global registry instance
mapping_registry = MappingRegistry()
