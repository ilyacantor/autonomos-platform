"""
Mapping Registry for vendor → canonical field mappings
Supports YAML/JSON storage with CRUD operations
"""
import os
import json
import yaml
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime


class MappingRegistry:
    """Registry for managing field mappings from source systems to canonical schemas"""
    
    def __init__(self, registry_path: str = "services/aam/canonical/mappings"):
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(parents=True, exist_ok=True)
        self._mappings_cache: Dict[str, Dict] = {}
        self._load_all_mappings()
    
    def _load_all_mappings(self):
        """Load all mapping files into cache"""
        for file_path in self.registry_path.glob("*.yaml"):
            system = file_path.stem
            with open(file_path, 'r') as f:
                self._mappings_cache[system] = yaml.safe_load(f)
        
        for file_path in self.registry_path.glob("*.json"):
            system = file_path.stem
            with open(file_path, 'r') as f:
                self._mappings_cache[system] = json.load(f)
    
    def get_mapping(self, system: str, entity: str) -> Optional[Dict[str, Any]]:
        """Get field mapping for a system and entity"""
        if system not in self._mappings_cache:
            return None
        
        mappings = self._mappings_cache[system]
        return mappings.get(entity, {})
    
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
        
        for source_field, source_value in source_row.items():
            if source_field in field_mappings:
                mapping_config = field_mappings[source_field]
                
                # Handle simple string mapping
                if isinstance(mapping_config, str):
                    canonical_field = mapping_config
                    canonical_data[canonical_field] = self._coerce_value(source_value, canonical_field)
                
                # Handle complex mapping with transforms
                elif isinstance(mapping_config, dict):
                    canonical_field = mapping_config.get('target')
                    transform = mapping_config.get('transform')
                    
                    if canonical_field:
                        value = self._apply_transform(source_value, transform) if transform else source_value
                        canonical_data[canonical_field] = self._coerce_value(value, canonical_field)
            else:
                # Unknown field - add to extras
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
