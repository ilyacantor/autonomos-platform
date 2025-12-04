#!/usr/bin/env python3
"""
AAM Ingest Seed Script
Seeds Supabase and MongoDB, emits events, and verifies DCL materialization
"""
import os
import sys
import time
import uuid
import httpx

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import SessionLocal
from services.aam.connectors.supabase.connector import SupabaseConnector
from services.aam.connectors.mongodb.connector import MongoDBConnector


def main():
    """Seed Supabase and MongoDB, emit events, verify DCL materialization"""
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Initialize connectors
        supabase_connector = SupabaseConnector(db=db, tenant_id="demo-tenant")
        mongodb_connector = MongoDBConnector(db=db, tenant_id="demo-tenant")
        
        # Seed Supabase
        print("Seeding Supabase...")
        supabase_connector.seed_data()
        
        # Seed MongoDB
        print("Seeding MongoDB...")
        mongodb_connector.seed_data()
        
        # Get latest opportunities and emit to canonical streams
        print("\nEmitting canonical events...")
        
        # Emit Supabase opportunities
        supabase_opportunities = supabase_connector.get_latest_opportunities(limit=5)
        supabase_count = 0
        for opp in supabase_opportunities:
            trace_id = str(uuid.uuid4())
            event = supabase_connector.normalize_opportunity(opp, trace_id)
            supabase_connector.emit_canonical_event(event)
            supabase_count += 1
        
        # Emit MongoDB opportunities
        mongo_opportunities = mongodb_connector.get_latest_opportunities(limit=5)
        mongo_count = 0
        for opp in mongo_opportunities:
            trace_id = str(uuid.uuid4())
            event = mongodb_connector.normalize_opportunity(opp, trace_id)
            mongodb_connector.emit_canonical_event(event)
            mongo_count += 1
        
        print(f"INGEST_SUPABASE: OK items={supabase_count}")
        print(f"INGEST_MONGO: OK items={mongo_count}")
        
        # Wait for DCL materialization
        print("\nWaiting 10s for DCL materialization...")
        time.sleep(10)
        
        # Check DCL views
        try:
            response = httpx.get("http://localhost:5000/api/v1/dcl/views/opportunities", timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                opportunities = data.get('opportunities', [])
                print(f"DCL_OPPORTUNITIES_COUNT: {len(opportunities)}")
                print("INGEST_SMOKE: PASS")
            else:
                print(f"DCL_OPPORTUNITIES_COUNT: 0")
                print("INGEST_SMOKE: FAIL (DCL API error)")
        except Exception as e:
            print(f"DCL_OPPORTUNITIES_COUNT: 0")
            print(f"INGEST_SMOKE: FAIL ({e})")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
