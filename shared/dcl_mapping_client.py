"""
DCL Mapping Client Library
Provides HTTP client for calling DCL mapping registry API with caching
"""
import os
import json
import logging
from typing import Dict, Any, Optional
import httpx

from shared.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class DCLMappingClient:
    """Client for calling DCL mapping registry API"""
    
    def __init__(self, base_url: Optional[str] = None, timeout: float = 5.0):
        """
        Initialize DCL mapping client
        
        Args:
            base_url: DCL API base URL (defaults to localhost:5000 or DCL_API_URL env var)
            timeout: HTTP request timeout in seconds
        """
        self.base_url: str = base_url or os.getenv("DCL_API_URL", "http://localhost:5000")
        self.timeout = timeout
        self.redis = get_redis_client()
        logger.info(f"DCLMappingClient initialized with base_url={self.base_url}")
    
    def get_entity_mapping(self, connector: str, entity: str, tenant_id: str = "default") -> Optional[Dict[str, Any]]:
        """
        Get all field mappings for a connector and entity.
        
        Returns format compatible with existing YAML structure:
        {
            "fields": {
                "canonical_field1": "source_field1",
                "canonical_field2": "source_field2"
            }
        }
        
        Args:
            connector: Connector name (e.g., "salesforce", "mongodb")
            entity: Entity/table name (e.g., "opportunity", "account")
            tenant_id: Tenant identifier for isolation
        
        Returns:
            Mapping dictionary or None if not found
        """
        cache_key = f"dcl_entity_mapping:{tenant_id}:{connector}:{entity}"
        
        if self.redis:
            try:
                cached = self.redis.get(cache_key)
                if cached:
                    logger.debug(f"Cache HIT for {cache_key}")
                    cached_str = cached.decode() if isinstance(cached, bytes) else str(cached)
                    return json.loads(cached_str)
            except Exception as e:
                logger.warning(f"Cache read failed for {cache_key}: {e}")
        
        try:
            url = f"{self.base_url}/api/v1/dcl/mappings/{connector}"
            
            # Database now enforces lowercase source_table (per architect guidance)
            # Normalize entity to lowercase before query
            normalized_entity = entity.lower()
            params = {"source_table": normalized_entity}
            
            logger.debug(f"DCL API request: GET {url}?source_table={normalized_entity}")
            
            response = httpx.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 404:
                logger.warning(f"No mapping found for {connector}.{entity} (normalized to '{normalized_entity}')")
                return None
            
            response.raise_for_status()
            data = response.json()
            
            mappings_list = data.get("mappings", [])
            fields = {}
            for mapping in mappings_list:
                canonical_field = mapping.get("canonical_field")
                source_field = mapping.get("source_field")
                if canonical_field and source_field:
                    fields[canonical_field] = source_field
            
            if not fields:
                logger.warning(f"DCL API returned empty mappings for {connector}.{normalized_entity}")
                return None
            
            logger.info(f"Found {len(fields)} mappings for {connector}.{entity} (normalized to '{normalized_entity}')")
            
            result = {"fields": fields}
            
            if self.redis:
                try:
                    self.redis.setex(cache_key, 300, json.dumps(result))
                    logger.debug(f"Cached mapping for {cache_key} (300s TTL)")
                except Exception as e:
                    logger.warning(f"Cache write failed for {cache_key}: {e}")
            
            return result
            
        except httpx.TimeoutException:
            logger.error(f"DCL API timeout for {connector}.{entity}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"DCL API HTTP error for {connector}.{entity}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"DCL API error for {connector}.{entity}: {e}")
            return None
    
    def get_field_mapping(self, connector: str, entity: str, field: str, tenant_id: str = "default") -> Optional[Dict[str, Any]]:
        """
        Get single field mapping (for future use)
        
        Args:
            connector: Connector name
            entity: Entity/table name
            field: Field name
            tenant_id: Tenant identifier
        
        Returns:
            Mapping details or None if not found
        """
        try:
            url = f"{self.base_url}/api/v1/dcl/mappings/{connector}/{entity}/{field}"
            
            response = httpx.get(url, timeout=self.timeout)
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"DCL API error for {connector}.{entity}.{field}: {e}")
            return None
