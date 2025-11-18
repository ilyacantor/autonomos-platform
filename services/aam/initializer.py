"""
AAM Connector Initialization Service
Populates Redis Streams with canonical events on startup
"""
import asyncio
import uuid as uuid_lib
import logging
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session

from app.database import SessionLocal
from services.aam.connectors.supabase.connector import SupabaseConnector
from services.aam.connectors.mongodb.connector import MongoDBConnector
from services.aam.connectors.salesforce.connector import SalesforceConnector
from services.aam.connectors.filesource.connector import FileSourceConnector

logger = logging.getLogger(__name__)


class AAMInitializer:
    """Initialize AAM connectors and populate Redis Streams on startup"""
    
    def __init__(self, tenant_id: str = "default"):
        """
        Initialize AAM connector system
        
        Args:
            tenant_id: Tenant identifier (defaults to "default")
        """
        self.tenant_id = tenant_id
        self.connectors: List = []
    
    async def initialize_all_connectors(self):
        """Initialize all AAM connectors and populate streams"""
        logger.info("🚀 AAM Initializer: Starting connector initialization...")
        
        db = SessionLocal()
        try:
            # Initialize connectors
            self.connectors = [
                SupabaseConnector(db=db, tenant_id=self.tenant_id),
                MongoDBConnector(db=db, tenant_id=self.tenant_id),
                SalesforceConnector(db=db, tenant_id=self.tenant_id),
                FileSourceConnector(db=db, tenant_id=self.tenant_id),
            ]
            
            total_events = 0
            
            # Seed and emit events for each connector
            for connector in self.connectors:
                try:
                    connector_name = connector.__class__.__name__.replace('Connector', '')
                    logger.info(f"  Initializing {connector_name}...")
                    
                    # Seed data in external system (only for connectors that support it)
                    if hasattr(connector, 'seed_data') and callable(getattr(connector, 'seed_data')):
                        connector.seed_data()
                    
                    # Fetch and emit canonical events
                    events_count = await self._emit_connector_events(connector)
                    total_events += events_count
                    
                    logger.info(f"  ✅ {connector_name}: Emitted {events_count} canonical events")
                    
                except Exception as e:
                    logger.warning(f"  ⚠️ {connector_name} initialization failed: {e}")
                    continue
            
            logger.info(f"✅ AAM Initializer: Emitted {total_events} total canonical events across {len(self.connectors)} connectors")
            
        except Exception as e:
            logger.error(f"❌ AAM Initializer failed: {e}", exc_info=True)
        finally:
            db.close()
    
    async def _emit_connector_events(self, connector) -> int:
        """
        Emit canonical events for a specific connector
        
        Args:
            connector: AAM connector instance
        
        Returns:
            Number of events emitted
        """
        events_count = 0
        
        try:
            # Get latest data (implementation varies per connector)
            if hasattr(connector, 'get_latest_opportunities'):
                items = connector.get_latest_opportunities(limit=10)
                normalize_method = connector.normalize_opportunity
            elif hasattr(connector, 'get_accounts'):
                items = connector.get_accounts()[:10]
                normalize_method = connector.normalize_account
            elif hasattr(connector, 'get_latest_files'):
                # FileSource: Use CSV replay workflow instead of file metadata
                # This processes actual CSV data with correct entity types
                stats = await connector.replay_all()
                return stats.get('total_records', 0)
            else:
                logger.warning(f"  No data fetch method found for {connector.__class__.__name__}")
                return 0
            
            # Normalize and emit each item
            for item in items:
                trace_id = str(uuid_lib.uuid4())
                event = await normalize_method(item, trace_id)
                connector.emit_canonical_event(event)
                events_count += 1
        
        except Exception as e:
            logger.error(f"  Failed to emit events for {connector.__class__.__name__}: {e}")
        
        return events_count


async def run_aam_initializer():
    """Run AAM initialization as a background task"""
    initializer = AAMInitializer()
    await initializer.initialize_all_connectors()
