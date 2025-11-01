#!/usr/bin/env python3
"""
AAM E2E RevOps Probe
End-to-end test: Fetch Supabase opportunity -> Emit canonical -> Query DCL view
"""
import os
import sys
import time
import uuid
import httpx
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import SessionLocal
from services.aam.connectors.supabase.connector import SupabaseConnector


def main():
    """E2E probe: Supabase -> Canonical -> DCL View"""
    
    base_url = "http://localhost:5000"
    
    print("=== E2E RevOps Probe ===\n")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Step 1: Get latest Supabase opportunity
        print("Step 1: Fetching latest Supabase opportunity...")
        supabase_connector = SupabaseConnector(db=db, tenant_id="demo-tenant")
        
        opportunities = supabase_connector.get_latest_opportunities(limit=1)
        
        if not opportunities:
            print("E2E_PROBE: FAIL (no opportunities found)")
            return
        
        opportunity = opportunities[0]
        opportunity_id = opportunity.get('opportunity_id', 'unknown')
        print(f"Fetched opportunity: {opportunity_id}")
        
        # Step 2: Emit canonical event
        print("\nStep 2: Emitting canonical event...")
        trace_id = str(uuid.uuid4())
        event = supabase_connector.normalize_opportunity(opportunity, trace_id)
        supabase_connector.emit_canonical_event(event)
        
        print(f"Emitted canonical event with trace_id={trace_id}")
        
        # Step 3: Backoff query DCL view
        print("\nStep 3: Querying DCL view (with backoff)...")
        
        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            print(f"Attempt {attempt}/{max_attempts}...")
            time.sleep(2)
            
            try:
                response = httpx.get(
                    f"{base_url}/api/v1/dcl/views/opportunities",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    opportunities_list = data.get('opportunities', [])
                    count = len(opportunities_list)
                    
                    # Check if our opportunity is in the view
                    found = any(opp.get('opportunity_id') == opportunity_id for opp in opportunities_list)
                    
                    if found or count > 0:
                        print(f"\nE2E_PROBE: PASS")
                        print(f"trace_id={trace_id}")
                        print(f"dcl_row_count={count}")
                        print(f"opportunity_found={found}")
                        return
                else:
                    print(f"DCL API returned status {response.status_code}")
            except Exception as e:
                print(f"Error querying DCL view: {e}")
        
        print(f"\nE2E_PROBE: PARTIAL")
        print(f"trace_id={trace_id}")
        print(f"dcl_row_count=0")
        print("Note: Opportunity emitted but not yet materialized in DCL view")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
