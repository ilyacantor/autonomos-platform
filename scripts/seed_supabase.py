#!/usr/bin/env python3
"""
Supabase Canonical Event Primer
Creates tables, seeds data, and emits canonical events
"""
import os
import sys
import time
import uuid
from datetime import datetime

from sqlalchemy.orm import Session
from app.database import get_db
from app.models import CanonicalStream
from services.aam.connectors.supabase.connector import SupabaseConnector

DEMO_TENANT_UUID = "9ac5c8c6-1a02-48ff-84a0-122b67f9c3bd"


def seed_supabase():
    """Seed canonical events from Supabase"""
    db = next(get_db())
    
    try:
        print("=" * 60)
        print("Supabase Canonical Event Primer")
        print("=" * 60)
        
        # Check if SUPABASE_DB_URL is set and valid
        supabase_url = os.getenv("SUPABASE_DB_URL")
        if not supabase_url:
            print("⚠️  SUPABASE_DB_URL not set - skipping")
            print("SUPABASE_URL_INVALID: Please provide real URL")
            return False
        
        # Validate URL doesn't contain placeholder values
        if "xxx" in supabase_url or "<" in supabase_url or ">" in supabase_url:
            print("⚠️  SUPABASE_DB_URL contains invalid placeholder values")
            print("SUPABASE_URL_INVALID: Please provide real URL")
            return False
        
        print("✅ SUPABASE_DB_URL is valid")
        
        connector = SupabaseConnector(db=db, tenant_id=DEMO_TENANT_UUID)
        
        if not connector.engine:
            print("❌ Failed to connect to Supabase")
            print("SUPABASE_URL_INVALID: Connection failed")
            return False
        
        # Test connection with SELECT 1
        from sqlalchemy import text
        try:
            with connector.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("✅ Connected to Supabase - connection test passed")
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            print("SUPABASE_URL_INVALID: Connection test failed")
            return False
        
        # Seed data (creates tables and inserts demo data)
        print("\n📝 Seeding Supabase tables...")
        connector.seed_data()
        print("✅ Supabase data seeded")
        
        # Fetch and emit canonical events
        print("\n📤 Fetching and emitting canonical events...")
        
        total_emitted = 0
        
        # Fetch and emit accounts
        with connector.engine.connect() as conn:
            result = conn.execute(text(f"SELECT * FROM {connector.schema}.accounts"))
            accounts = [dict(row._mapping) for row in result]
        
        print(f"📊 Found {len(accounts)} accounts")
        
        for account in accounts:
            try:
                canonical_data = {
                    "account_id": account.get("account_id"),
                    "name": account.get("name"),
                    "type": account.get("type"),
                    "industry": account.get("industry"),
                    "owner_id": account.get("owner_id"),
                    "status": account.get("status")
                }
                
                stream_record = CanonicalStream(
                    id=uuid.uuid4(),
                    tenant_id=uuid.UUID(DEMO_TENANT_UUID),
                    entity="account",
                    data=canonical_data,
                    meta={"version": "1.0", "schema": "canonical_v1"},
                    source={"system": "supabase", "connector": "postgres"},
                    emitted_at=datetime.utcnow()
                )
                
                db.add(stream_record)
                total_emitted += 1
            except Exception as e:
                print(f"   ⚠️  Error processing account: {e}")
                continue
        
        # Fetch and emit opportunities
        with connector.engine.connect() as conn:
            result = conn.execute(text(f"SELECT * FROM {connector.schema}.opportunities"))
            opportunities = [dict(row._mapping) for row in result]
        
        print(f"📊 Found {len(opportunities)} opportunities")
        
        for opportunity in opportunities:
            try:
                canonical_data = {
                    "opportunity_id": opportunity.get("opportunity_id"),
                    "account_id": opportunity.get("account_id"),
                    "name": opportunity.get("name"),
                    "stage": opportunity.get("stage"),
                    "amount": str(opportunity.get("amount", "")),
                    "currency": opportunity.get("currency", "USD"),
                    "close_date": str(opportunity.get("close_date", "")),
                    "owner_id": opportunity.get("owner_id"),
                    "probability": str(opportunity.get("probability", ""))
                }
                
                stream_record = CanonicalStream(
                    id=uuid.uuid4(),
                    tenant_id=uuid.UUID(DEMO_TENANT_UUID),
                    entity="opportunity",
                    data=canonical_data,
                    meta={"version": "1.0", "schema": "canonical_v1"},
                    source={"system": "supabase", "connector": "postgres"},
                    emitted_at=datetime.utcnow()
                )
                
                db.add(stream_record)
                total_emitted += 1
            except Exception as e:
                print(f"   ⚠️  Error processing opportunity: {e}")
                continue
        
        db.commit()
        print(f"\n📊 Total canonical events emitted: {total_emitted}")
        
        # Wait for materialization
        print("\n⏳ Waiting for DCL materialization (3 seconds)...")
        time.sleep(3)
        
        # Verify canonical_streams records
        from sqlalchemy import func, cast, String
        stream_count = db.query(CanonicalStream).filter(
            CanonicalStream.tenant_id == uuid.UUID(DEMO_TENANT_UUID),
            func.cast(CanonicalStream.source['system'], String) == 'supabase'
        ).count()
        
        print(f"✅ Verified {stream_count} records in canonical_streams")
        
        print("\n" + "=" * 60)
        print("Supabase Primer: SUCCESS")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = seed_supabase()
    sys.exit(0 if success else 1)
