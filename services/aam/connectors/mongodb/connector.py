"""
MongoDB Connector for AAM
Fetches data from MongoDB collections and normalizes to canonical format
"""
import os
import logging
import uuid
import json
import redis
from datetime import datetime
from typing import Optional, Dict, Any, List
from bson import ObjectId
from pymongo import MongoClient
from sqlalchemy.orm import Session
from app.models import CanonicalStream
from services.aam.canonical.mapping_registry import mapping_registry
from services.aam.canonical.schemas import (
    CanonicalEvent, CanonicalMeta, CanonicalSource,
    CanonicalAccount, CanonicalOpportunity
)

logger = logging.getLogger(__name__)


class MongoDBConnector:
    """
    MongoDB connector for AAM
    
    Features:
    - Connects to MongoDB via MONGODB_URI
    - Queries accounts and opportunities collections
    - Automatic normalization to canonical format
    - Event emission to canonical_streams table
    - Idempotent seed data method
    """
    
    def __init__(self, db: Session, tenant_id: str = "default"):
        self.db = db
        self.tenant_id = tenant_id
        self.mongo_uri = os.getenv("MONGODB_URI", "")
        self.mongo_db_name = os.getenv("MONGODB_DB", "autonomos")
        self.client = None
        self.mongo_db = None
        self.redis_client = None
        
        # Initialize Redis client for stream publishing
        redis_url = os.getenv('REDIS_URL')
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                logger.info("✅ MongoDBConnector: Redis client initialized")
            except Exception as e:
                logger.error(f"Failed to create Redis client: {e}")
        
        if self.mongo_uri:
            try:
                self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
                # Test connection
                self.client.server_info()
                self.mongo_db = self.client[self.mongo_db_name]
                logger.info(f"✅ MongoDBConnector initialized for database={self.mongo_db_name}")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                self.client = None
                self.mongo_db = None
        else:
            logger.warning("MONGODB_URI not set - connector will not be able to fetch data")
    
    def seed_data(self):
        """
        Idempotent seed data method
        Inserts demo data into accounts and opportunities collections
        """
        if self.mongo_db is None:
            logger.error("No MongoDB connection available")
            return
        
        try:
            accounts_collection = self.mongo_db['accounts']
            opportunities_collection = self.mongo_db['opportunities']
            
            # Check if accounts collection is empty
            count = accounts_collection.count_documents({})
            
            if count == 0:
                logger.info("Seeding MongoDB accounts collection...")
                
                # Insert 3 demo accounts with ObjectId
                accounts = [
                    {
                        '_id': ObjectId(),
                        'account_id': 'MONGO-ACC-001',
                        'name': 'CloudScale Solutions',
                        'type': 'Enterprise',
                        'industry': 'Cloud Services',
                        'owner_id': 'owner-101',
                        'status': 'active',
                        'annual_revenue': 8000000.0,
                        'employees': 400,
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    },
                    {
                        '_id': ObjectId(),
                        'account_id': 'MONGO-ACC-002',
                        'name': 'DataDriven Analytics',
                        'type': 'Mid-Market',
                        'industry': 'Analytics',
                        'owner_id': 'owner-102',
                        'status': 'active',
                        'annual_revenue': 3500000.0,
                        'employees': 180,
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    },
                    {
                        '_id': ObjectId(),
                        'account_id': 'MONGO-ACC-003',
                        'name': 'Startup Ventures Inc',
                        'type': 'SMB',
                        'industry': 'Venture Capital',
                        'owner_id': 'owner-103',
                        'status': 'prospect',
                        'annual_revenue': 800000.0,
                        'employees': 25,
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    }
                ]
                
                accounts_collection.insert_many(accounts)
                logger.info(f"✅ Inserted {len(accounts)} accounts into MongoDB")
            else:
                logger.info(f"Accounts collection already has {count} documents, skipping seed")
            
            # Check if opportunities collection is empty
            count = opportunities_collection.count_documents({})
            
            if count == 0:
                logger.info("Seeding MongoDB opportunities collection...")
                
                # Insert 5 demo opportunities
                opportunities = [
                    {
                        '_id': ObjectId(),
                        'opportunity_id': 'MONGO-OPP-001',
                        'account_id': 'MONGO-ACC-001',
                        'name': 'Cloud Migration Project',
                        'stage': 'Qualification',
                        'amount': 450000.0,
                        'currency': 'USD',
                        'close_date': datetime(2025, 12, 20),
                        'owner_id': 'owner-101',
                        'probability': 70.0,
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    },
                    {
                        '_id': ObjectId(),
                        'opportunity_id': 'MONGO-OPP-002',
                        'account_id': 'MONGO-ACC-001',
                        'name': 'Enterprise Support Package',
                        'stage': 'Negotiation',
                        'amount': 200000.0,
                        'currency': 'USD',
                        'close_date': datetime(2026, 1, 15),
                        'owner_id': 'owner-101',
                        'probability': 85.0,
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    },
                    {
                        '_id': ObjectId(),
                        'opportunity_id': 'MONGO-OPP-003',
                        'account_id': 'MONGO-ACC-002',
                        'name': 'Analytics Platform License',
                        'stage': 'Proposal',
                        'amount': 150000.0,
                        'currency': 'USD',
                        'close_date': datetime(2026, 2, 10),
                        'owner_id': 'owner-102',
                        'probability': 55.0,
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    },
                    {
                        '_id': ObjectId(),
                        'opportunity_id': 'MONGO-OPP-004',
                        'account_id': 'MONGO-ACC-003',
                        'name': 'Seed Round Advisory',
                        'stage': 'Closed Won',
                        'amount': 50000.0,
                        'currency': 'USD',
                        'close_date': datetime(2025, 10, 25),
                        'owner_id': 'owner-103',
                        'probability': 100.0,
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    },
                    {
                        '_id': ObjectId(),
                        'opportunity_id': 'MONGO-OPP-005',
                        'account_id': 'MONGO-ACC-002',
                        'name': 'Professional Services',
                        'stage': 'Closed Won',
                        'amount': 75000.0,
                        'currency': 'USD',
                        'close_date': datetime(2025, 11, 5),
                        'owner_id': 'owner-102',
                        'probability': 100.0,
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    }
                ]
                
                opportunities_collection.insert_many(opportunities)
                logger.info(f"✅ Inserted {len(opportunities)} opportunities into MongoDB")
            else:
                logger.info(f"Opportunities collection already has {count} documents, skipping seed")
                
        except Exception as e:
            logger.error(f"Failed to seed MongoDB data: {e}")
            raise
    
    def get_latest_opportunities(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch latest opportunities from MongoDB"""
        if self.mongo_db is None:
            logger.error("No MongoDB connection available")
            return []
        
        try:
            opportunities_collection = self.mongo_db['opportunities']
            cursor = opportunities_collection.find().sort('updated_at', -1).limit(limit)
            
            opportunities = []
            for doc in cursor:
                # Convert ObjectId to string for JSON serialization
                if '_id' in doc and isinstance(doc['_id'], ObjectId):
                    doc['_id'] = str(doc['_id'])
                opportunities.append(doc)
            
            logger.info(f"Fetched {len(opportunities)} opportunities from MongoDB")
            return opportunities
        except Exception as e:
            logger.error(f"Failed to fetch opportunities: {e}")
            return []
    
    def get_accounts(self) -> List[Dict[str, Any]]:
        """Fetch all accounts from MongoDB"""
        if self.mongo_db is None:
            logger.error("No MongoDB connection available")
            return []
        
        try:
            accounts_collection = self.mongo_db['accounts']
            cursor = accounts_collection.find().sort('created_at', -1)
            
            accounts = []
            for doc in cursor:
                # Convert ObjectId to string for JSON serialization
                if '_id' in doc and isinstance(doc['_id'], ObjectId):
                    doc['_id'] = str(doc['_id'])
                accounts.append(doc)
            
            logger.info(f"Fetched {len(accounts)} accounts from MongoDB")
            return accounts
        except Exception as e:
            logger.error(f"Failed to fetch accounts: {e}")
            return []
    
    def normalize_account(
        self,
        mongo_account: Dict[str, Any],
        trace_id: str
    ) -> CanonicalEvent:
        """
        Normalize MongoDB account to canonical format
        
        Args:
            mongo_account: Raw MongoDB account data
            trace_id: Trace ID for tracking
        
        Returns:
            CanonicalEvent with strict typing
        """
        canonical_data, unknown_fields = mapping_registry.apply_mapping(
            system="mongodb",
            entity="account",
            source_row=mongo_account
        )
        
        try:
            typed_data = CanonicalAccount(**canonical_data)
        except Exception as e:
            logger.error(f"Failed to validate canonical account: {e}")
            logger.error(f"Source data: {mongo_account}")
            logger.error(f"Canonical data: {canonical_data}")
            raise ValueError(f"Canonical validation failed: {e}")
        
        meta = CanonicalMeta(
            version="1.0.0",
            tenant=self.tenant_id,
            trace_id=trace_id,
            emitted_at=datetime.utcnow()
        )
        
        source = CanonicalSource(
            system="mongodb",
            connection_id="mongo-main",
            schema_version="v1"
        )
        
        event = CanonicalEvent(
            meta=meta,
            source=source,
            entity="account",
            op="upsert",
            data=typed_data,
            unknown_fields=unknown_fields
        )
        
        return event
    
    def normalize_opportunity(
        self,
        mongo_opportunity: Dict[str, Any],
        trace_id: str
    ) -> CanonicalEvent:
        """
        Normalize MongoDB opportunity to canonical format
        
        Args:
            mongo_opportunity: Raw MongoDB opportunity data
            trace_id: Trace ID for tracking
        
        Returns:
            CanonicalEvent with strict typing
        """
        canonical_data, unknown_fields = mapping_registry.apply_mapping(
            system="mongodb",
            entity="opportunity",
            source_row=mongo_opportunity
        )
        
        try:
            typed_data = CanonicalOpportunity(**canonical_data)
        except Exception as e:
            logger.error(f"Failed to validate canonical opportunity: {e}")
            logger.error(f"Source data: {mongo_opportunity}")
            logger.error(f"Canonical data: {canonical_data}")
            raise ValueError(f"Canonical validation failed: {e}")
        
        meta = CanonicalMeta(
            version="1.0.0",
            tenant=self.tenant_id,
            trace_id=trace_id,
            emitted_at=datetime.utcnow()
        )
        
        source = CanonicalSource(
            system="mongodb",
            connection_id="mongo-main",
            schema_version="v1"
        )
        
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
        """Emit CanonicalEvent to Redis Stream for DCL consumption"""
        if not self.redis_client:
            logger.error("Redis client not initialized - cannot emit canonical event")
            return
        
        stream_key = f"aam:dcl:{self.tenant_id}:mongodb"
        
        # Create payload matching AAMSourceAdapter expected format
        payload = {
            'batch_id': str(uuid.uuid4()),
            'timestamp': datetime.utcnow().isoformat(),
            'source_system': 'mongodb',
            'tenant_id': self.tenant_id,
            'entity': event.entity,
            'data': event.data.model_dump(mode='json'),
            'meta': event.meta.model_dump(mode='json'),
            'source': event.source.model_dump(mode='json')
        }
        
        try:
            message_id = self.redis_client.xadd(stream_key, {'payload': json.dumps(payload)})
            logger.info(
                f"✅ Emitted canonical {event.entity} to Redis Stream {stream_key}: "
                f"trace_id={event.meta.trace_id}, message_id={message_id}"
            )
        except Exception as e:
            logger.error(f"Failed to emit canonical event to Redis: {e}")
