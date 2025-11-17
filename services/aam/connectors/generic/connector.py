"""
Generic REST Connector for AAM - Phase 0 Prototype
Configuration-driven connector supporting multiple REST API patterns

Features:
- YAML/JSON configuration for API endpoints, auth, and field mappings
- Multiple auth methods: API key, Bearer token, OAuth2
- Pagination support: limit/offset, cursor-based
- Automatic normalization to canonical format using mapping registry
- Event emission to canonical_streams table

Configuration Schema:
    connector_id: str - Unique identifier for this connector
    base_url: str - Base URL for the API
    auth: AuthConfig - Authentication configuration
    endpoints: List[EndpointConfig] - API endpoints to query
    field_mappings: Dict[str, Dict] - Field mappings for normalization
"""

import os
import json
import yaml
import logging
import uuid
import httpx
from datetime import datetime
from typing import Optional, Dict, Any, List, Literal, Union
from pathlib import Path
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from app.models import CanonicalStream
from services.aam.canonical.mapping_registry import mapping_registry
from services.aam.canonical.schemas import (
    CanonicalEvent, CanonicalMeta, CanonicalSource,
    CanonicalAccount, CanonicalOpportunity, CanonicalContact
)

logger = logging.getLogger(__name__)


# ========== Pydantic Configuration Models ==========

class ApiKeyAuthConfig(BaseModel):
    """API Key authentication configuration"""
    type: Literal["api_key"] = "api_key"
    header: str = Field(..., description="Header name (e.g., 'Authorization', 'X-API-Key')")
    prefix: Optional[str] = Field(None, description="Optional prefix (e.g., 'Bearer', 'token')")
    key_env_var: str = Field(..., description="Environment variable containing the API key")


class BearerAuthConfig(BaseModel):
    """Bearer token authentication configuration"""
    type: Literal["bearer"] = "bearer"
    token_env_var: str = Field(..., description="Environment variable containing the bearer token")


class OAuth2AuthConfig(BaseModel):
    """OAuth2 authentication configuration"""
    type: Literal["oauth2"] = "oauth2"
    token_url: str = Field(..., description="OAuth2 token endpoint")
    client_id_env_var: str = Field(..., description="Environment variable for client ID")
    client_secret_env_var: str = Field(..., description="Environment variable for client secret")
    grant_type: str = Field("client_credentials", description="OAuth2 grant type")
    scope: Optional[str] = Field(None, description="OAuth2 scope")


class LimitOffsetPaginationConfig(BaseModel):
    """Limit/offset pagination configuration"""
    type: Literal["limit_offset"] = "limit_offset"
    limit_param: str = Field("limit", description="Query parameter for page size")
    offset_param: str = Field("offset", description="Query parameter for offset")
    max_limit: int = Field(100, description="Maximum records per page")


class CursorPaginationConfig(BaseModel):
    """Cursor-based pagination configuration"""
    type: Literal["cursor"] = "cursor"
    cursor_param: str = Field("cursor", description="Query parameter for cursor")
    limit_param: str = Field("limit", description="Query parameter for page size")
    max_limit: int = Field(100, description="Maximum records per page")
    next_cursor_path: str = Field("pagination.next_cursor", description="JSON path to next cursor in response")


class EndpointConfig(BaseModel):
    """API endpoint configuration"""
    path: str = Field(..., description="API endpoint path (supports {variables})")
    entity: str = Field(..., description="Entity type (account, opportunity, contact)")
    method: str = Field("GET", description="HTTP method")
    pagination: Optional[Union[LimitOffsetPaginationConfig, CursorPaginationConfig]] = Field(
        None, description="Pagination configuration"
    )
    data_path: str = Field("data", description="JSON path to data array in response (use '.' for root)")
    params: Dict[str, Any] = Field(default_factory=dict, description="Additional query parameters")
    headers: Dict[str, str] = Field(default_factory=dict, description="Additional headers")


class ConnectorConfig(BaseModel):
    """Complete connector configuration"""
    connector_id: str = Field(..., description="Unique connector identifier")
    base_url: str = Field(..., description="Base URL for API")
    auth: Union[ApiKeyAuthConfig, BearerAuthConfig, OAuth2AuthConfig] = Field(
        ..., description="Authentication configuration"
    )
    endpoints: List[EndpointConfig] = Field(..., description="API endpoints to query")
    timeout: int = Field(30, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum retry attempts")
    
    class Config:
        extra = "allow"


# ========== Generic REST Connector ==========

class GenericRESTConnector:
    """
    Generic REST API connector for AAM
    
    Supports configuration-driven integration with any REST API that follows
    common patterns for authentication, pagination, and data structure.
    
    Usage:
        config = ConnectorConfig.parse_file("config.yaml")
        connector = GenericRESTConnector(db, config, tenant_id="demo")
        await connector.fetch_and_emit(endpoint_index=0)
    """
    
    def __init__(
        self,
        db: Session,
        config: Union[ConnectorConfig, Dict, str, Path],
        tenant_id: str = "demo-tenant"
    ):
        """
        Initialize generic connector
        
        Args:
            db: SQLAlchemy database session
            config: ConnectorConfig object, dict, or path to YAML/JSON config file
            tenant_id: Tenant identifier for multi-tenancy
        """
        self.db = db
        self.tenant_id = tenant_id
        
        # Load and validate configuration
        if isinstance(config, (str, Path)):
            self.config = self._load_config_file(config)
        elif isinstance(config, dict):
            self.config = ConnectorConfig(**config)
        else:
            self.config = config
        
        # Initialize HTTP client
        self.client = None
        self.access_token = None
        
        logger.info(f"✅ GenericRESTConnector initialized: {self.config.connector_id}")
    
    def _load_config_file(self, config_path: Union[str, Path]) -> ConnectorConfig:
        """Load configuration from YAML or JSON file"""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            if config_path.suffix in ['.yaml', '.yml']:
                config_dict = yaml.safe_load(f)
            elif config_path.suffix == '.json':
                config_dict = json.load(f)
            else:
                raise ValueError(f"Unsupported config format: {config_path.suffix}")
        
        return ConnectorConfig(**config_dict)
    
    async def _authenticate(self) -> Dict[str, str]:
        """
        Perform authentication and return headers
        
        Returns:
            Dictionary of authentication headers
        """
        auth_config = self.config.auth
        
        if isinstance(auth_config, ApiKeyAuthConfig):
            # API Key authentication
            api_key = os.getenv(auth_config.key_env_var)
            if not api_key:
                raise ValueError(f"API key not found in env var: {auth_config.key_env_var}")
            
            header_value = f"{auth_config.prefix} {api_key}" if auth_config.prefix else api_key
            return {auth_config.header: header_value}
        
        elif isinstance(auth_config, BearerAuthConfig):
            # Bearer token authentication
            token = os.getenv(auth_config.token_env_var)
            if not token:
                raise ValueError(f"Bearer token not found in env var: {auth_config.token_env_var}")
            
            return {"Authorization": f"Bearer {token}"}
        
        elif isinstance(auth_config, OAuth2AuthConfig):
            # OAuth2 client credentials flow
            client_id = os.getenv(auth_config.client_id_env_var)
            client_secret = os.getenv(auth_config.client_secret_env_var)
            
            if not client_id or not client_secret:
                raise ValueError(f"OAuth2 credentials not found in env vars")
            
            # Request access token
            async with httpx.AsyncClient() as client:
                data = {
                    "grant_type": auth_config.grant_type,
                    "client_id": client_id,
                    "client_secret": client_secret,
                }
                if auth_config.scope:
                    data["scope"] = auth_config.scope
                
                response = await client.post(auth_config.token_url, data=data)
                response.raise_for_status()
                
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                
                return {"Authorization": f"Bearer {self.access_token}"}
        
        return {}
    
    def _extract_data(self, response_json: Dict, data_path: str) -> List[Dict]:
        """
        Extract data array from response using JSON path
        
        Args:
            response_json: Full JSON response
            data_path: Dot-notation path to data (e.g., "data.items" or "." for root)
        
        Returns:
            List of data records
        """
        if data_path == "." or not data_path:
            # Data is at root level
            if isinstance(response_json, list):
                return response_json
            return [response_json]
        
        # Navigate JSON path
        current = response_json
        for part in data_path.split('.'):
            if isinstance(current, dict):
                current = current.get(part)
            else:
                logger.warning(f"Cannot navigate path {data_path} in response")
                return []
        
        if isinstance(current, list):
            return current
        elif current is not None:
            return [current]
        
        return []
    
    def _extract_next_cursor(self, response_json: Dict, cursor_path: str) -> Optional[str]:
        """Extract next cursor from response using JSON path"""
        current = response_json
        for part in cursor_path.split('.'):
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        
        return current if isinstance(current, str) else None
    
    async def fetch_data(
        self,
        endpoint: EndpointConfig,
        path_params: Optional[Dict[str, str]] = None,
        max_pages: int = 5
    ) -> List[Dict]:
        """
        Fetch data from an API endpoint with pagination support
        
        Args:
            endpoint: Endpoint configuration
            path_params: Path parameter substitutions (e.g., {"owner": "octocat", "repo": "hello-world"})
            max_pages: Maximum number of pages to fetch
        
        Returns:
            List of all fetched records
        """
        # Build URL with path parameters
        path = endpoint.path
        if path_params:
            for key, value in path_params.items():
                path = path.replace(f"{{{key}}}", str(value))
        
        url = f"{self.config.base_url}{path}"
        
        # Get authentication headers
        auth_headers = await self._authenticate()
        headers = {**auth_headers, **endpoint.headers}
        
        # Initialize HTTP client
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=self.config.timeout)
        
        all_records = []
        page = 0
        cursor = None
        
        try:
            while page < max_pages:
                # Build query parameters
                params = {**endpoint.params}
                
                if endpoint.pagination:
                    if isinstance(endpoint.pagination, LimitOffsetPaginationConfig):
                        params[endpoint.pagination.limit_param] = endpoint.pagination.max_limit
                        params[endpoint.pagination.offset_param] = page * endpoint.pagination.max_limit
                    
                    elif isinstance(endpoint.pagination, CursorPaginationConfig):
                        params[endpoint.pagination.limit_param] = endpoint.pagination.max_limit
                        if cursor:
                            params[endpoint.pagination.cursor_param] = cursor
                
                # Make request
                response = await self.client.request(
                    method=endpoint.method,
                    url=url,
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                
                response_json = response.json()
                
                # Extract data
                records = self._extract_data(response_json, endpoint.data_path)
                
                if not records:
                    break
                
                all_records.extend(records)
                logger.info(f"Fetched page {page + 1}: {len(records)} records")
                
                # Handle pagination
                if endpoint.pagination:
                    if isinstance(endpoint.pagination, CursorPaginationConfig):
                        cursor = self._extract_next_cursor(
                            response_json,
                            endpoint.pagination.next_cursor_path
                        )
                        if not cursor:
                            break
                    elif isinstance(endpoint.pagination, LimitOffsetPaginationConfig):
                        if len(records) < endpoint.pagination.max_limit:
                            break
                else:
                    # No pagination - single page
                    break
                
                page += 1
            
            logger.info(f"✅ Fetched total {len(all_records)} records from {endpoint.path}")
            return all_records
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to fetch data from {url}: {e}")
            raise
    
    def normalize_record(
        self,
        record: Dict[str, Any],
        entity: str,
        trace_id: str
    ) -> CanonicalEvent:
        """
        Normalize a single record to canonical format
        
        Args:
            record: Raw API record
            entity: Entity type (account, opportunity, contact)
            trace_id: Trace ID for tracking
        
        Returns:
            CanonicalEvent with normalized data
        """
        # Apply mapping registry
        canonical_data, unknown_fields = mapping_registry.apply_mapping(
            system=self.config.connector_id,
            entity=entity,
            source_row=record
        )
        
        # Instantiate canonical model
        try:
            if entity == "account":
                typed_data = CanonicalAccount(**canonical_data)
            elif entity == "opportunity":
                typed_data = CanonicalOpportunity(**canonical_data)
            elif entity == "contact":
                typed_data = CanonicalContact(**canonical_data)
            else:
                raise ValueError(f"Unsupported entity type: {entity}")
        except Exception as e:
            logger.error(f"Failed to validate canonical {entity}: {e}")
            logger.error(f"Source data: {record}")
            logger.error(f"Canonical data: {canonical_data}")
            raise ValueError(f"Canonical validation failed: {e}")
        
        # Build metadata
        meta = CanonicalMeta(
            version="1.0.0",
            tenant=self.tenant_id,
            trace_id=trace_id,
            emitted_at=datetime.utcnow()
        )
        
        # Build source metadata
        source = CanonicalSource(
            system=self.config.connector_id,
            connection_id=f"{self.config.connector_id}-generic",
            schema_version="v1"
        )
        
        # Build canonical event
        event = CanonicalEvent(
            meta=meta,
            source=source,
            entity=entity,
            op="upsert",
            data=typed_data,
            unknown_fields=unknown_fields
        )
        
        return event
    
    def emit_to_stream(self, event: CanonicalEvent) -> None:
        """
        Emit canonical event to canonical_streams table
        
        Args:
            event: Canonical event to emit
        """
        try:
            stream_record = CanonicalStream(
                tenant_id=self.tenant_id,
                entity=event.entity,
                data=event.data.dict() if hasattr(event.data, 'dict') else event.data,
                meta=event.meta.dict(),
                source=event.source.dict(),
                emitted_at=event.meta.emitted_at
            )
            
            self.db.add(stream_record)
            self.db.commit()
            
            logger.debug(f"✅ Emitted {event.entity} to canonical_streams")
        
        except Exception as e:
            logger.error(f"Failed to emit event to canonical_streams: {e}")
            self.db.rollback()
            raise
    
    async def fetch_and_emit(
        self,
        endpoint_index: int = 0,
        path_params: Optional[Dict[str, str]] = None,
        max_pages: int = 5,
        emit: bool = True
    ) -> List[CanonicalEvent]:
        """
        Fetch data from endpoint, normalize, and emit to canonical streams
        
        Args:
            endpoint_index: Index of endpoint in config.endpoints
            path_params: Path parameter substitutions
            max_pages: Maximum pages to fetch
            emit: Whether to emit to database (False for testing)
        
        Returns:
            List of canonical events
        """
        if endpoint_index >= len(self.config.endpoints):
            raise ValueError(f"Invalid endpoint index: {endpoint_index}")
        
        endpoint = self.config.endpoints[endpoint_index]
        trace_id = str(uuid.uuid4())
        
        logger.info(f"🔄 Fetching from {endpoint.path} (entity: {endpoint.entity})")
        
        # Fetch data
        start_time = datetime.utcnow()
        records = await self.fetch_data(endpoint, path_params, max_pages)
        fetch_duration = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info(f"⏱️  Fetch completed in {fetch_duration:.2f}s")
        
        # Normalize and emit
        events = []
        for record in records:
            try:
                event = self.normalize_record(record, endpoint.entity, trace_id)
                events.append(event)
                
                if emit:
                    self.emit_to_stream(event)
            
            except Exception as e:
                logger.error(f"Failed to process record: {e}")
                continue
        
        logger.info(f"✅ Processed {len(events)}/{len(records)} records successfully")
        
        return events
    
    async def close(self):
        """Close HTTP client"""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
