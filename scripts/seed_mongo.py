#!/usr/bin/env python3
"""
MongoDB Canonical Event Primer
Creates collections, seeds data, and emits canonical events
"""
import os
import sys
import time
import uuid
from datetime import datetime



from sqlalchemy.orm import Session
from app.database import get_db
from app.models import CanonicalStream
from services.aam.connectors.mongodb.connector import MongoDBConnector

DEMO_TENANT_UUID = "9ac5c8c6-1a02-48ff-84a0-122b67f9c3bd"


def seed_mongodb():
    """Seed canonical events from MongoDB"""
    db = next(get_db())
    
    try:
        print("=" * 60)
        print("MongoDB Canonical Event Primer")
        print("=" * 60)
        
        # Check if MONGODB_URI is set
        if not os.getenv("MONGODB_URI"):
            print("⚠️  MONGODB_URI not set - skipping")
            return False
        
        connector = MongoDBConnector(db=db, tenant_id=DEMO_TENANT_UUID)
        
        if connector.mongo_db is None:
            print("❌ Failed to connect to MongoDB")
            return False
        
        print("✅ Connected to MongoDB")
        
        # Seed data (creates collections and inserts demo data)
        print("\n📝 Seeding MongoDB collections...")
        connector.seed_data()
        print("✅ MongoDB data seeded")
        
        # Fetch and emit canonical events
        print("\n📤 Fetching and emitting canonical events...")
        
        total_emitted = 0
        
        # Fetch and emit accounts
        accounts = list(connector.mongo_db['accounts'].find())
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
                    source={"system": "mongodb", "connector": "pymongo"},
                    emitted_at=datetime.utcnow()
                )
                
                db.add(stream_record)
                total_emitted += 1
            except Exception as e:
                print(f"   ⚠️  Error processing account: {e}")
                continue
        
        # Fetch and emit opportunities
        opportunities = list(connector.mongo_db['opportunities'].find())
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
                    source={"system": "mongodb", "connector": "pymongo"},
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
            func.cast(CanonicalStream.source['system'], String) == 'mongodb'
        ).count()
        
        print(f"✅ Verified {stream_count} records in canonical_streams")
        
        print("\n" + "=" * 60)
        print("MongoDB Primer: SUCCESS")
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
    success = seed_mongodb()
    sys.exit(0 if success else 1)
