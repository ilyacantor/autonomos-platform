"""
DCL Mapping Client Stubs

DCL v1 has been removed from this repo. These stubs provide no-op implementations
that allow existing code to function with YAML fallbacks.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DCLMappingClient:
    """
    Stub DCL mapping client. DCL v1 has been removed.
    All operations return None, triggering YAML fallback in MappingRegistry.
    """
    
    def __init__(self, base_url: str = ""):
        logger.debug("DCL v1 removed - DCLMappingClient is a no-op stub")
    
    def get_entity_mapping(
        self, 
        system: str, 
        entity: str, 
        tenant_id: str = "default"
    ) -> Optional[Dict[str, Any]]:
        """Returns None to trigger YAML fallback"""
        return None
    
    def list_mappings(self, tenant_id: str = "default") -> list:
        """Returns empty list"""
        return []


class AsyncDCLMappingClient:
    """
    Stub async DCL mapping client. DCL v1 has been removed.
    All operations return None, triggering YAML fallback in MappingRegistry.
    """
    
    def __init__(self, http_client=None):
        logger.debug("DCL v1 removed - AsyncDCLMappingClient is a no-op stub")
        self._http_client = http_client
    
    async def get_entity_mapping(
        self, 
        system: str, 
        entity: str, 
        tenant_id: str = "default"
    ) -> Optional[Dict[str, Any]]:
        """Returns None to trigger YAML fallback"""
        return None
    
    async def list_mappings(self, tenant_id: str = "default") -> list:
        """Returns empty list"""
        return []
    
    async def close(self):
        """Close the HTTP client if it exists"""
        if self._http_client:
            try:
                await self._http_client.aclose()
            except Exception:
                pass
