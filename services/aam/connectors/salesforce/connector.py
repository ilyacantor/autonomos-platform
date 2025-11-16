"""
Salesforce Connector for AAM
Fetches live data from Salesforce REST API and normalizes to canonical format
"""
import os
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
import httpx
from sqlalchemy.orm import Session
from app.models import CanonicalStream
from services.aam.canonical.mapping_registry import mapping_registry
from services.aam.canonical.schemas import (
    CanonicalEvent, CanonicalMeta, CanonicalSource,
    CanonicalOpportunity
)

logger = logging.getLogger(__name__)


class SalesforceConnector:
    """
    Salesforce REST API connector for AAM
    
    Features:
    - OAuth 2.0 authentication with refresh token support
    - REST API queries for Opportunities
    - Automatic normalization to canonical format
    - Event emission to canonical_streams table
    - Auto-refresh on 401 errors
    """
    
    def __init__(self, db: Session, tenant_id: str = "demo-tenant"):
        from services.aam.connectors.salesforce.oauth_refresh import get_access_token
        
        self.db = db
        self.tenant_id = tenant_id
        self.instance_url = os.getenv("SALESFORCE_INSTANCE_URL", "https://login.salesforce.com")
        self.api_version = "v59.0"
        
        # OAuth credentials
        self.client_id = os.getenv("SALESFORCE_CLIENT_ID")
        self.client_secret = os.getenv("SALESFORCE_CLIENT_SECRET")
        self.refresh_token = os.getenv("SALESFORCE_REFRESH_TOKEN")
        direct_token = os.getenv("SALESFORCE_ACCESS_TOKEN")
        
        # Get access token using OAuth refresh or direct token
        self.access_token = get_access_token(
            client_id=self.client_id,
            client_secret=self.client_secret,
            refresh_token=self.refresh_token,
            direct_access_token=direct_token
        )
        
        if not self.access_token:
            logger.warning("SALESFORCE credentials not configured - set either ACCESS_TOKEN or (CLIENT_ID + CLIENT_SECRET + REFRESH_TOKEN)")
    
    def _refresh_token_if_needed(self):
        """Refresh access token if using OAuth refresh flow"""
        from services.aam.connectors.salesforce.oauth_refresh import get_access_token
        
        if self.refresh_token and self.client_id and self.client_secret:
            new_token = get_access_token(
                client_id=self.client_id,
                client_secret=self.client_secret,
                refresh_token=self.refresh_token,
                direct_access_token=None
            )
            if new_token:
                self.access_token = new_token
                logger.info("Access token refreshed successfully")
                return True
        return False
    
    async def get_latest_opportunity(self) -> Optional[Dict[str, Any]]:
        """
        Fetch the most recent Salesforce Opportunity using REST API
        Auto-refreshes token on 401 errors
        
        Returns:
            Dict with opportunity data or None if not available
        """
        if not self.access_token or not self.instance_url:
            logger.error("Salesforce credentials not configured")
            return None
        
        # SOQL query to fetch the most recent opportunity
        soql = (
            "SELECT Id, AccountId, Name, StageName, Amount, "
            "CloseDate, OwnerId, Probability, LastModifiedDate "
            "FROM Opportunity "
            "ORDER BY LastModifiedDate DESC "
            "LIMIT 1"
        )
        
        url = f"{self.instance_url}/services/data/{self.api_version}/query/"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        params = {"q": soql}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params, timeout=30.0)
                
                # Handle 401 - try to refresh token
                if response.status_code == 401:
                    logger.warning("Received 401, attempting to refresh token")
                    if self._refresh_token_if_needed():
                        # Retry with new token
                        headers["Authorization"] = f"Bearer {self.access_token}"
                        response = await client.get(url, headers=headers, params=params, timeout=30.0)
                
                response.raise_for_status()
                
                data = response.json()
                records = data.get("records", [])
                
                if not records:
                    logger.warning("No opportunities found in Salesforce")
                    return None
                
                opportunity = records[0]
                logger.info(f"Fetched Salesforce Opportunity: {opportunity['Id']} - {opportunity['Name']}")
                return opportunity
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Salesforce API error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch Salesforce opportunity: {e}")
            return None
    
    def get_latest_opportunities(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch multiple recent Salesforce Opportunities (sync wrapper for AAM initializer)
        
        Args:
            limit: Maximum number of opportunities to fetch
        
        Returns:
            List of opportunity dictionaries
        """
        if not self.access_token or not self.instance_url:
            logger.error("Salesforce credentials not configured")
            return []
        
        soql = (
            f"SELECT Id, AccountId, Name, StageName, Amount, "
            f"CloseDate, OwnerId, Probability, LastModifiedDate "
            f"FROM Opportunity "
            f"ORDER BY LastModifiedDate DESC "
            f"LIMIT {limit}"
        )
        
        url = f"{self.instance_url}/services/data/{self.api_version}/query/"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        params = {"q": soql}
        
        try:
            import httpx
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=headers, params=params)
                
                # Handle 401 - try to refresh token
                if response.status_code == 401:
                    logger.warning("Received 401, attempting to refresh token")
                    if self._refresh_token_if_needed():
                        headers["Authorization"] = f"Bearer {self.access_token}"
                        response = client.get(url, headers=headers, params=params)
                
                response.raise_for_status()
                data = response.json()
                records = data.get("records", [])
                
                logger.info(f"Fetched {len(records)} Salesforce opportunities")
                return records
                
        except Exception as e:
            logger.error(f"Failed to fetch Salesforce opportunities: {e}")
            return []
    
    def normalize_opportunity(
        self,
        sf_opportunity: Dict[str, Any],
        trace_id: str
    ) -> CanonicalEvent:
        """
        Normalize Salesforce Opportunity to canonical format
        
        Args:
            sf_opportunity: Raw Salesforce opportunity data
            trace_id: Trace ID for tracking
        
        Returns:
            CanonicalEvent with strict typing
        """
        # Apply mapping registry to transform Salesforce data to canonical format
        canonical_data, unknown_fields = mapping_registry.apply_mapping(
            system="salesforce",
            entity="opportunity",
            source_row=sf_opportunity
        )
        
        # Instantiate canonical model (enforces strict typing)
        try:
            typed_data = CanonicalOpportunity(**canonical_data)
        except Exception as e:
            logger.error(f"Failed to validate canonical opportunity: {e}")
            logger.error(f"Source data: {sf_opportunity}")
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
            system="salesforce",
            connection_id="salesforce-live",
            schema_version="v1"
        )
        
        # Build canonical event
        event = CanonicalEvent(
            meta=meta,
            source=source,
            entity="opportunity",
            op="upsert",
            data=typed_data,
            unknown_fields=unknown_fields
        )
        
        return event
    
    def emit_canonical_event(self, event: CanonicalEvent):
        """Emit CanonicalEvent to database canonical_streams table"""
        import json
        from decimal import Decimal
        
        # Convert Pydantic models to dicts with Decimal/datetime conversion
        def convert_types(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: convert_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_types(item) for item in obj]
            return obj
        
        data_dict = event.data.dict() if hasattr(event.data, 'dict') else event.data
        data_dict = convert_types(data_dict)
        meta_dict = convert_types(event.meta.dict())
        source_dict = convert_types(event.source.dict())
        
        canonical_entry = CanonicalStream(
            tenant_id=self.tenant_id,
            entity=event.entity,
            data=data_dict,
            meta=meta_dict,
            source=source_dict,
            emitted_at=event.meta.emitted_at
        )
        self.db.add(canonical_entry)
        self.db.commit()
        logger.info(f"✅ Emitted canonical event: {event.entity} - {event.meta.trace_id}")
