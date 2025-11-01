"""
Supabase (Postgres) Connector for AAM
Fetches data from Supabase Postgres tables and normalizes to canonical format
"""
import os
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine, text, MetaData, Table, Column, String, Float, DateTime, Integer
from sqlalchemy.orm import Session
from app.models import CanonicalStream
from services.aam.canonical.mapping_registry import mapping_registry
from services.aam.canonical.schemas import (
    CanonicalEvent, CanonicalMeta, CanonicalSource,
    CanonicalAccount, CanonicalOpportunity
)

logger = logging.getLogger(__name__)


class SupabaseConnector:
    """
    Supabase Postgres connector for AAM
    
    Features:
    - Connects to Supabase Postgres via SUPABASE_DB_URL
    - Queries accounts and opportunities tables
    - Automatic normalization to canonical format
    - Event emission to canonical_streams table
    - Idempotent seed data method
    """
    
    def __init__(self, db: Session, tenant_id: str = "demo-tenant"):
        self.db = db
        self.tenant_id = tenant_id
        self.db_url = os.getenv("SUPABASE_DB_URL", "")
        self.schema = os.getenv("SUPABASE_SCHEMA", "public")
        self.engine = None
        
        if self.db_url:
            try:
                self.engine = create_engine(self.db_url, pool_pre_ping=True)
                logger.info(f"✅ SupabaseConnector initialized for schema={self.schema}")
            except Exception as e:
                logger.error(f"Failed to create Supabase engine: {e}")
        else:
            logger.warning("SUPABASE_DB_URL not set - connector will not be able to fetch data")
    
    def seed_data(self):
        """
        Idempotent seed data method
        Creates tables if they don't exist and inserts demo data
        """
        if not self.engine:
            logger.error("No Supabase engine available")
            return
        
        try:
            with self.engine.connect() as conn:
                # Create accounts table if not exists
                conn.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS {self.schema}.accounts (
                        account_id VARCHAR(255) PRIMARY KEY,
                        name VARCHAR(500) NOT NULL,
                        type VARCHAR(100),
                        industry VARCHAR(100),
                        owner_id VARCHAR(255),
                        status VARCHAR(50),
                        annual_revenue FLOAT,
                        employees INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create opportunities table if not exists
                conn.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS {self.schema}.opportunities (
                        opportunity_id VARCHAR(255) PRIMARY KEY,
                        account_id VARCHAR(255),
                        name VARCHAR(500) NOT NULL,
                        stage VARCHAR(100),
                        amount FLOAT,
                        currency VARCHAR(10) DEFAULT 'USD',
                        close_date TIMESTAMP,
                        owner_id VARCHAR(255),
                        probability FLOAT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (account_id) REFERENCES {self.schema}.accounts(account_id)
                    )
                """))
                
                conn.commit()
                
                # Check if accounts table is empty
                result = conn.execute(text(f"SELECT COUNT(*) FROM {self.schema}.accounts"))
                count = result.scalar()
                
                if count == 0:
                    logger.info("Seeding Supabase accounts table...")
                    
                    # Insert 3 demo accounts
                    accounts = [
                        {
                            'account_id': 'SUPA-ACC-001',
                            'name': 'TechCorp Industries',
                            'type': 'Enterprise',
                            'industry': 'Technology',
                            'owner_id': 'owner-001',
                            'status': 'active',
                            'annual_revenue': 5000000.0,
                            'employees': 250
                        },
                        {
                            'account_id': 'SUPA-ACC-002',
                            'name': 'Global Dynamics LLC',
                            'type': 'Mid-Market',
                            'industry': 'Manufacturing',
                            'owner_id': 'owner-002',
                            'status': 'active',
                            'annual_revenue': 2500000.0,
                            'employees': 150
                        },
                        {
                            'account_id': 'SUPA-ACC-003',
                            'name': 'Innovation Partners',
                            'type': 'SMB',
                            'industry': 'Consulting',
                            'owner_id': 'owner-003',
                            'status': 'prospect',
                            'annual_revenue': 1000000.0,
                            'employees': 50
                        }
                    ]
                    
                    for acc in accounts:
                        conn.execute(text(f"""
                            INSERT INTO {self.schema}.accounts 
                            (account_id, name, type, industry, owner_id, status, annual_revenue, employees)
                            VALUES (:account_id, :name, :type, :industry, :owner_id, :status, :annual_revenue, :employees)
                        """), acc)
                    
                    conn.commit()
                    logger.info(f"✅ Inserted {len(accounts)} accounts")
                else:
                    logger.info(f"Accounts table already has {count} records, skipping seed")
                
                # Check if opportunities table is empty
                result = conn.execute(text(f"SELECT COUNT(*) FROM {self.schema}.opportunities"))
                count = result.scalar()
                
                if count == 0:
                    logger.info("Seeding Supabase opportunities table...")
                    
                    # Insert 5 demo opportunities
                    opportunities = [
                        {
                            'opportunity_id': 'SUPA-OPP-001',
                            'account_id': 'SUPA-ACC-001',
                            'name': 'Q4 Enterprise License',
                            'stage': 'Negotiation',
                            'amount': 250000.0,
                            'currency': 'USD',
                            'close_date': '2025-12-15',
                            'owner_id': 'owner-001',
                            'probability': 75.0
                        },
                        {
                            'opportunity_id': 'SUPA-OPP-002',
                            'account_id': 'SUPA-ACC-001',
                            'name': 'Platform Expansion',
                            'stage': 'Proposal',
                            'amount': 180000.0,
                            'currency': 'USD',
                            'close_date': '2026-01-20',
                            'owner_id': 'owner-001',
                            'probability': 60.0
                        },
                        {
                            'opportunity_id': 'SUPA-OPP-003',
                            'account_id': 'SUPA-ACC-002',
                            'name': 'Manufacturing Suite',
                            'stage': 'Discovery',
                            'amount': 95000.0,
                            'currency': 'USD',
                            'close_date': '2026-02-28',
                            'owner_id': 'owner-002',
                            'probability': 40.0
                        },
                        {
                            'opportunity_id': 'SUPA-OPP-004',
                            'account_id': 'SUPA-ACC-003',
                            'name': 'Starter Package',
                            'stage': 'Closed Won',
                            'amount': 25000.0,
                            'currency': 'USD',
                            'close_date': '2025-11-01',
                            'owner_id': 'owner-003',
                            'probability': 100.0
                        },
                        {
                            'opportunity_id': 'SUPA-OPP-005',
                            'account_id': 'SUPA-ACC-002',
                            'name': 'Annual Renewal',
                            'stage': 'Closed Won',
                            'amount': 120000.0,
                            'currency': 'USD',
                            'close_date': '2025-10-30',
                            'owner_id': 'owner-002',
                            'probability': 100.0
                        }
                    ]
                    
                    for opp in opportunities:
                        conn.execute(text(f"""
                            INSERT INTO {self.schema}.opportunities 
                            (opportunity_id, account_id, name, stage, amount, currency, close_date, owner_id, probability)
                            VALUES (:opportunity_id, :account_id, :name, :stage, :amount, :currency, :close_date, :owner_id, :probability)
                        """), opp)
                    
                    conn.commit()
                    logger.info(f"✅ Inserted {len(opportunities)} opportunities")
                else:
                    logger.info(f"Opportunities table already has {count} records, skipping seed")
                    
        except Exception as e:
            logger.error(f"Failed to seed Supabase data: {e}")
            raise
    
    def get_latest_opportunities(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch latest opportunities from Supabase"""
        if not self.engine:
            logger.error("No Supabase engine available")
            return []
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT * FROM {self.schema}.opportunities 
                    ORDER BY updated_at DESC 
                    LIMIT :limit
                """), {'limit': limit})
                
                opportunities = []
                for row in result:
                    opportunities.append(dict(row._mapping))
                
                logger.info(f"Fetched {len(opportunities)} opportunities from Supabase")
                return opportunities
        except Exception as e:
            logger.error(f"Failed to fetch opportunities: {e}")
            return []
    
    def get_accounts(self) -> List[Dict[str, Any]]:
        """Fetch all accounts from Supabase"""
        if not self.engine:
            logger.error("No Supabase engine available")
            return []
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT * FROM {self.schema}.accounts 
                    ORDER BY created_at DESC
                """))
                
                accounts = []
                for row in result:
                    accounts.append(dict(row._mapping))
                
                logger.info(f"Fetched {len(accounts)} accounts from Supabase")
                return accounts
        except Exception as e:
            logger.error(f"Failed to fetch accounts: {e}")
            return []
    
    def normalize_account(
        self,
        supabase_account: Dict[str, Any],
        trace_id: str
    ) -> CanonicalEvent:
        """
        Normalize Supabase account to canonical format
        
        Args:
            supabase_account: Raw Supabase account data
            trace_id: Trace ID for tracking
        
        Returns:
            CanonicalEvent with strict typing
        """
        canonical_data, unknown_fields = mapping_registry.apply_mapping(
            system="supabase",
            entity="account",
            source_row=supabase_account
        )
        
        try:
            typed_data = CanonicalAccount(**canonical_data)
        except Exception as e:
            logger.error(f"Failed to validate canonical account: {e}")
            logger.error(f"Source data: {supabase_account}")
            logger.error(f"Canonical data: {canonical_data}")
            raise ValueError(f"Canonical validation failed: {e}")
        
        meta = CanonicalMeta(
            version="1.0.0",
            tenant=self.tenant_id,
            trace_id=trace_id,
            emitted_at=datetime.utcnow()
        )
        
        source = CanonicalSource(
            system="supabase",
            connection_id="supabase",
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
        supabase_opportunity: Dict[str, Any],
        trace_id: str
    ) -> CanonicalEvent:
        """
        Normalize Supabase opportunity to canonical format
        
        Args:
            supabase_opportunity: Raw Supabase opportunity data
            trace_id: Trace ID for tracking
        
        Returns:
            CanonicalEvent with strict typing
        """
        canonical_data, unknown_fields = mapping_registry.apply_mapping(
            system="supabase",
            entity="opportunity",
            source_row=supabase_opportunity
        )
        
        try:
            typed_data = CanonicalOpportunity(**canonical_data)
        except Exception as e:
            logger.error(f"Failed to validate canonical opportunity: {e}")
            logger.error(f"Source data: {supabase_opportunity}")
            logger.error(f"Canonical data: {canonical_data}")
            raise ValueError(f"Canonical validation failed: {e}")
        
        meta = CanonicalMeta(
            version="1.0.0",
            tenant=self.tenant_id,
            trace_id=trace_id,
            emitted_at=datetime.utcnow()
        )
        
        source = CanonicalSource(
            system="supabase",
            connection_id="supabase",
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
        """Emit CanonicalEvent to database canonical_streams table"""
        canonical_entry = CanonicalStream(
            tenant_id=self.tenant_id,
            entity=event.entity,
            data=event.data.model_dump(),
            meta=event.meta.model_dump(),
            source=event.source.model_dump(),
            emitted_at=event.meta.emitted_at
        )
        
        self.db.add(canonical_entry)
        self.db.commit()
        
        logger.info(
            f"✅ Emitted canonical {event.entity} event: "
            f"trace_id={event.meta.trace_id}, "
            f"system={event.source.system}"
        )
