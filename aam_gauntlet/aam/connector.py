"""Core connector implementation for AAM."""
import httpx
import asyncio
import hashlib
import secrets
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from rate_policy import RatePolicy, AdaptiveRateLimiter
from error_classifier import ErrorClass, ErrorClassifier
from dlq import DeadLetterQueue
from db import MetricsDB


@dataclass
class CredentialDescriptor:
    """Authentication credentials for a service."""
    auth_type: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    api_key: Optional[str] = None
    expires_at: Optional[datetime] = None
    version: int = 1
    client_id: Optional[str] = None
    client_secret: Optional[str] = None


@dataclass
class NetworkProfile:
    """Network behavior configuration."""
    timeout: float = 30.0
    max_retries: int = 3
    retry_on_timeout: bool = True


@dataclass
class ConnectorConfig:
    """Configuration for a connector instance."""
    service_id: str
    tenant_id: str
    base_url: str
    credentials: CredentialDescriptor
    rate_policy: RatePolicy = field(default_factory=RatePolicy)
    network_profile: NetworkProfile = field(default_factory=NetworkProfile)


class ConnectorInstance:
    """A single connector instance to a service."""
    
    def __init__(
        self,
        config: ConnectorConfig,
        db: MetricsDB,
        rate_limiter: AdaptiveRateLimiter,
        dlq: DeadLetterQueue
    ):
        self.config = config
        self.db = db
        self.rate_limiter = rate_limiter
        self.dlq = dlq
        self.connector_id = f"{config.service_id}:{config.tenant_id}"
        
        # HTTP client
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.network_profile.timeout
        )
        
        # Idempotency tracking
        self.idempotency_cache: Dict[str, Any] = {}
        
        # Token refresh tracking
        self.token_refresh_lock = asyncio.Lock()
        self.last_token_refresh = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        await self.close()
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    def _generate_idempotency_key(self, method: str, path: str, payload: Any) -> str:
        """Generate a unique idempotency key for a request."""
        # Create a hash of the request details
        key_parts = [
            self.connector_id,
            method,
            path,
            str(payload)
        ]
        key_string = ":".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    async def _refresh_token(self) -> bool:
        """Refresh OAuth2 token if needed."""
        async with self.token_refresh_lock:
            # Check if token needs refresh
            if self.config.credentials.auth_type != "oauth2_client_credentials":
                return True
            
            if self.config.credentials.expires_at:
                # Refresh if within 5 minutes of expiry
                if datetime.utcnow() < self.config.credentials.expires_at - timedelta(minutes=5):
                    return True
            
            # Perform token refresh
            old_expiry = self.config.credentials.expires_at
            
            try:
                # Make token request
                token_url = f"{self.config.base_url}/oauth2/token"
                response = await self.client.post(
                    token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.config.credentials.client_id or f"{self.config.service_id}:{self.config.tenant_id}",
                        "client_secret": self.config.credentials.client_secret or "secret"
                    }
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    self.config.credentials.access_token = token_data["access_token"]
                    self.config.credentials.refresh_token = token_data.get("refresh_token")
                    
                    # Calculate expiry
                    expires_in = token_data.get("expires_in", 3600)
                    self.config.credentials.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                    
                    # Log success
                    self.db.log_token_refresh(
                        connector_id=self.connector_id,
                        service_id=self.config.service_id,
                        tenant_id=self.config.tenant_id,
                        old_expiry=old_expiry,
                        new_expiry=self.config.credentials.expires_at,
                        success=True
                    )
                    
                    return True
                else:
                    raise Exception(f"Token refresh failed: {response.status_code}")
                    
            except Exception as e:
                # Log failure
                self.db.log_token_refresh(
                    connector_id=self.connector_id,
                    service_id=self.config.service_id,
                    tenant_id=self.config.tenant_id,
                    old_expiry=old_expiry,
                    new_expiry=None,
                    success=False,
                    error_message=str(e)
                )
                return False
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        headers = {}
        
        if self.config.credentials.auth_type == "oauth2_client_credentials":
            if self.config.credentials.access_token:
                headers["Authorization"] = f"Bearer {self.config.credentials.access_token}"
        elif self.config.credentials.auth_type == "api_key":
            if self.config.credentials.api_key:
                headers["Authorization"] = f"Bearer {self.config.credentials.api_key}"
        
        return headers
    
    async def _execute_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json_body: Optional[Dict] = None,
        idempotency_key: Optional[str] = None,
        retry_count: int = 0
    ) -> httpx.Response:
        """Execute an HTTP request with retry logic."""
        start_time = time.time()
        
        # Check idempotency cache
        if idempotency_key and idempotency_key in self.idempotency_cache:
            cached_response = self.idempotency_cache[idempotency_key]
            self.db.log_request(
                connector_id=self.connector_id,
                service_id=self.config.service_id,
                tenant_id=self.config.tenant_id,
                endpoint=path,
                method=method,
                http_status=200,
                error_class=None,
                retries=0,
                idempotency_key=idempotency_key,
                latency_ms=0.1,
                response_data=cached_response
            )
            return cached_response
        
        # Wait for rate limit
        wait_time = await self.rate_limiter.wait_and_acquire(
            self.connector_id,
            self.config.rate_policy
        )
        
        # Refresh token if needed
        if self.config.credentials.auth_type == "oauth2_client_credentials":
            await self._refresh_token()
        
        # Prepare request
        headers = self._get_auth_headers()
        headers["X-Tenant-ID"] = self.config.tenant_id
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        
        try:
            # Execute request
            response = await self.client.request(
                method=method,
                url=path,
                params=params,
                json=json_body,
                headers=headers
            )
            
            # Check for errors
            if response.status_code >= 400:
                error_class = ErrorClassifier.classify_error(
                    response.status_code,
                    response.json() if response.text else None
                )
                
                # Handle retryable errors
                if ErrorClassifier.is_retryable(error_class) and retry_count < self.config.network_profile.max_retries:
                    # Handle rate limits specially
                    if error_class == ErrorClass.RATE_LIMIT:
                        retry_after = response.headers.get("Retry-After")
                        self.rate_limiter.record_rate_limit(
                            self.connector_id,
                            self.config.rate_policy,
                            float(retry_after) if retry_after else None
                        )
                    
                    # Handle auth refresh
                    if error_class == ErrorClass.AUTH_EXPIRED:
                        await self._refresh_token()
                    
                    # Calculate retry delay
                    delay = ErrorClassifier.get_retry_delay(error_class, retry_count)
                    await asyncio.sleep(delay)
                    
                    # Retry
                    return await self._execute_request(
                        method, path, params, json_body,
                        idempotency_key, retry_count + 1
                    )
                
                # Log failed request
                self.db.log_request(
                    connector_id=self.connector_id,
                    service_id=self.config.service_id,
                    tenant_id=self.config.tenant_id,
                    endpoint=path,
                    method=method,
                    http_status=response.status_code,
                    error_class=error_class.value,
                    retries=retry_count,
                    idempotency_key=idempotency_key,
                    latency_ms=(time.time() - start_time) * 1000,
                    request_data=json_body,
                    response_data=response.json() if response.text else None
                )
                
                # Add to DLQ if write operation
                if method in ["POST", "PUT", "PATCH"] and json_body:
                    await self.dlq.add_failed_request(
                        connector_id=self.connector_id,
                        tenant_id=self.config.tenant_id,
                        endpoint=path,
                        method=method,
                        payload=json_body,
                        error_class=error_class,
                        error_message=f"HTTP {response.status_code}",
                        idempotency_key=idempotency_key
                    )
                
                return response
            
            # Successful request
            self.rate_limiter.record_success(self.connector_id)
            
            # Cache if idempotent
            response_data = response.json() if response.text else {}
            if idempotency_key:
                self.idempotency_cache[idempotency_key] = response_data
            
            # Log success
            self.db.log_request(
                connector_id=self.connector_id,
                service_id=self.config.service_id,
                tenant_id=self.config.tenant_id,
                endpoint=path,
                method=method,
                http_status=response.status_code,
                error_class=None,
                retries=retry_count,
                idempotency_key=idempotency_key,
                latency_ms=(time.time() - start_time) * 1000,
                request_data=json_body,
                response_data=response_data
            )
            
            return response
            
        except Exception as e:
            # Handle network/timeout errors
            error_class = ErrorClassifier.classify_error(None, None, e)
            
            # Retry if possible
            if ErrorClassifier.is_retryable(error_class) and retry_count < self.config.network_profile.max_retries:
                delay = ErrorClassifier.get_retry_delay(error_class, retry_count)
                await asyncio.sleep(delay)
                return await self._execute_request(
                    method, path, params, json_body,
                    idempotency_key, retry_count + 1
                )
            
            # Log error
            self.db.log_request(
                connector_id=self.connector_id,
                service_id=self.config.service_id,
                tenant_id=self.config.tenant_id,
                endpoint=path,
                method=method,
                http_status=None,
                error_class=error_class.value,
                retries=retry_count,
                idempotency_key=idempotency_key,
                latency_ms=(time.time() - start_time) * 1000,
                request_data=json_body
            )
            
            raise
    
    async def get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a GET request."""
        response = await self._execute_request("GET", path, params=params)
        return response.json() if response.text else {}
    
    async def post(
        self,
        path: str,
        json_body: Dict[str, Any],
        generate_idempotency: bool = True
    ) -> Dict[str, Any]:
        """Execute a POST request with automatic idempotency."""
        idempotency_key = None
        if generate_idempotency:
            idempotency_key = self._generate_idempotency_key("POST", path, json_body)
        
        response = await self._execute_request(
            "POST",
            path,
            json_body=json_body,
            idempotency_key=idempotency_key
        )
        return response.json() if response.text else {}
    
    async def put(
        self,
        path: str,
        json_body: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a PUT request."""
        response = await self._execute_request("PUT", path, json_body=json_body)
        return response.json() if response.text else {}
    
    async def delete(self, path: str) -> Dict[str, Any]:
        """Execute a DELETE request."""
        response = await self._execute_request("DELETE", path)
        return response.json() if response.text else {}


class AAM:
    """Adaptive API Mesh manager."""
    
    def __init__(self):
        self.db = MetricsDB("aam_metrics.db")
        self.rate_limiter = AdaptiveRateLimiter()
        self.dlq = DeadLetterQueue(self.db)
        self.connectors: Dict[str, ConnectorInstance] = {}
    
    def create_connector(self, config: ConnectorConfig) -> ConnectorInstance:
        """Create a new connector instance."""
        connector = ConnectorInstance(
            config=config,
            db=self.db,
            rate_limiter=self.rate_limiter,
            dlq=self.dlq
        )
        
        connector_id = f"{config.service_id}:{config.tenant_id}"
        self.connectors[connector_id] = connector
        
        return connector
    
    def get_connector(self, service_id: str, tenant_id: str) -> Optional[ConnectorInstance]:
        """Get an existing connector."""
        connector_id = f"{service_id}:{tenant_id}"
        return self.connectors.get(connector_id)
    
    async def close_all(self):
        """Close all connectors."""
        for connector in self.connectors.values():
            await connector.close()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get overall AAM metrics."""
        return {
            "connectors": len(self.connectors),
            "metrics_summary": self.db.get_metrics_summary(),
            "dlq_stats": self.dlq.get_stats(),
            "rate_limiter_stats": {
                conn_id: self.rate_limiter.get_stats(conn_id)
                for conn_id in self.connectors.keys()
            }
        }