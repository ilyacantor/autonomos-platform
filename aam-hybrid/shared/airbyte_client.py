import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from .config import settings

logger = logging.getLogger(__name__)


class AirbyteClient:
    """
    Async Airbyte API Client
    Handles all interactions with Airbyte OSS API using OAuth2 authentication
    """
    
    def __init__(self):
        self.base_url = settings.AIRBYTE_API_URL
        self.client_id = settings.AIRBYTE_CLIENT_ID
        self.client_secret = settings.AIRBYTE_CLIENT_SECRET
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        
    async def _ensure_token(self):
        """
        Ensure we have a valid access token
        Refresh if expired or missing
        """
        if self.access_token and self.token_expires_at:
            if datetime.utcnow() < self.token_expires_at:
                return
        
        logger.info("Requesting new Airbyte access token...")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url.replace('/api/public/v1', '')}/api/public/v1/applications/token",
                json={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
            )
            response.raise_for_status()
            
            data = response.json()
            self.access_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)
            
            logger.info("Access token obtained successfully")
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make authenticated request to Airbyte API
        """
        await self._ensure_token()
        
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"
        headers["Content-Type"] = "application/json"
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()
    
    async def create_source(
        self,
        workspace_id: str,
        source_definition_id: str,
        connection_configuration: Dict[str, Any],
        name: str
    ) -> Dict[str, Any]:
        """
        Create a new source in Airbyte
        
        Args:
            workspace_id: Airbyte workspace ID
            source_definition_id: Source connector type ID
            connection_configuration: Source-specific configuration
            name: Human-readable source name
        
        Returns:
            Source creation response with sourceId
        """
        logger.info(f"Creating Airbyte source: {name}")
        
        payload = {
            "workspaceId": workspace_id,
            "sourceDefinitionId": source_definition_id,
            "connectionConfiguration": connection_configuration,
            "name": name
        }
        
        result = await self._request("POST", "/sources", json=payload)
        logger.info(f"Source created: {result.get('sourceId')}")
        return result
    
    async def discover_schema(self, source_id: str) -> Dict[str, Any]:
        """
        Discover schema from a source
        
        Args:
            source_id: Airbyte source ID
        
        Returns:
            Schema discovery result with catalog
        """
        logger.info(f"Discovering schema for source: {source_id}")
        
        result = await self._request("POST", f"/sources/{source_id}/discover", json={})
        logger.info(f"Schema discovered: {len(result.get('catalog', {}).get('streams', []))} streams")
        return result
    
    async def create_connection(
        self,
        source_id: str,
        destination_id: str,
        sync_catalog: Dict[str, Any],
        name: str,
        namespace_definition: str = "destination",
        namespace_format: Optional[str] = None,
        prefix: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a connection between source and destination
        
        Args:
            source_id: Source ID
            destination_id: Destination ID
            sync_catalog: syncCatalog configuration
            name: Connection name
            namespace_definition: Namespace strategy
            namespace_format: Custom namespace format
            prefix: Table name prefix
        
        Returns:
            Connection creation response with connectionId
        """
        logger.info(f"Creating Airbyte connection: {name}")
        
        payload = {
            "sourceId": source_id,
            "destinationId": destination_id,
            "syncCatalog": sync_catalog,
            "name": name,
            "namespaceDefinition": namespace_definition,
            "status": "active"
        }
        
        if namespace_format:
            payload["namespaceFormat"] = namespace_format
        if prefix:
            payload["prefix"] = prefix
        
        result = await self._request("POST", "/connections", json=payload)
        logger.info(f"Connection created: {result.get('connectionId')}")
        return result
    
    async def update_connection(
        self,
        connection_id: str,
        sync_catalog: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update connection syncCatalog (for drift repair)
        
        Args:
            connection_id: Connection ID to update
            sync_catalog: New syncCatalog configuration
        
        Returns:
            Update response
        """
        logger.info(f"Updating connection catalog: {connection_id}")
        
        payload = {
            "syncCatalog": sync_catalog
        }
        
        result = await self._request("PATCH", f"/connections/{connection_id}", json=payload)
        logger.info("Connection catalog updated successfully")
        return result
    
    async def trigger_sync(self, connection_id: str) -> Dict[str, Any]:
        """
        Trigger a sync job for a connection
        
        Args:
            connection_id: Connection ID to sync
        
        Returns:
            Job trigger response with jobId
        """
        logger.info(f"Triggering sync for connection: {connection_id}")
        
        result = await self._request("POST", f"/connections/{connection_id}/sync", json={})
        logger.info(f"Sync triggered: {result.get('jobId')}")
        return result
    
    async def get_source_definition_id(self, source_type: str) -> Optional[str]:
        """
        Get source definition ID by source type name
        
        Args:
            source_type: Source type (e.g., "Salesforce")
        
        Returns:
            Source definition ID or None
        """
        logger.info(f"Looking up source definition for: {source_type}")
        
        result = await self._request("GET", "/source_definitions")
        
        for definition in result.get("sourceDefinitions", []):
            if definition.get("name", "").lower() == source_type.lower():
                definition_id = definition.get("sourceDefinitionId")
                logger.info(f"Found definition ID: {definition_id}")
                return definition_id
        
        logger.warning(f"Source definition not found for: {source_type}")
        return None


airbyte_client = AirbyteClient()
