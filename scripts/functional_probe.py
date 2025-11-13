"""
Functional Probe: Salesforce → AAM → DCL End-to-End Test

This script proves the end-to-end flow from live Salesforce through AAM normalization into DCL views.
Includes exponential backoff verification and detailed status output.
"""
import asyncio
import os
import sys
import uuid
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
from sqlalchemy.orm import Session
from app.database import SessionLocal
from services.aam.connectors.salesforce.connector import SalesforceConnector
from services.aam.canonical.subscriber import process_canonical_streams


async def verify_dcl_materialization(opportunity_id: str, max_retries: int = 10) -> int:
    """
    Verify that the canonical event has been materialized in DCL views
    Uses exponential backoff (0.5s, 1s, 2s, 4s, 8s)
    
    Args:
        opportunity_id: Salesforce Opportunity ID
        max_retries: Maximum number of retries (default 10)
    
    Returns:
        Count of records found in DCL views (0 or 1)
    """
    base_url = os.getenv("BASE_URL", "http://localhost:5000")
    dcl_url = f"{base_url}/api/v1/dcl/views/opportunities"
    
    delay = 0.5  # Start with 500ms
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    dcl_url,
                    params={"opportunity_id": opportunity_id},
                    timeout=10.0
                )
                response.raise_for_status()
                
                data = response.json()
                records = data.get("records", [])
                count = len(records)
                
                if count > 0:
                    print(f"✅ Found {count} record(s) in DCL views (attempt {attempt + 1})")
                    return count
                
                print(f"⏳ Attempt {attempt + 1}/{max_retries}: No records yet, retrying in {delay}s...")
                await asyncio.sleep(delay)
                delay = min(delay * 2, 10)  # Exponential backoff, max 10s
                
        except Exception as e:
            print(f"❌ Error querying DCL views (attempt {attempt + 1}): {e}")
            await asyncio.sleep(delay)
            delay = min(delay * 2, 10)
    
    print(f"❌ No records found after {max_retries} attempts")
    return 0


async def run_functional_probe():
    """
    Execute the functional probe:
    1. Fetch latest Salesforce Opportunity
    2. Normalize through AAM
    3. Emit canonical event
    4. Process through DCL subscriber
    5. Verify materialization
    6. Print verification output
    """
    print("=" * 80)
    print("FUNCTIONAL PROBE: Salesforce → AAM → DCL")
    print("=" * 80)
    
    # Generate trace ID for tracking
    trace_id = str(uuid.uuid4())
    print(f"🔍 Trace ID: {trace_id}\n")
    
    # Create database session
    db: Session = SessionLocal()
    
    try:
        # Use the demo tenant UUID (matches provision_demo_tenant.py)
        probe_tenant_id = "9ac5c8c6-1a02-48ff-84a0-122b67f9c3bd"  # Demo tenant
        
        # Initialize Salesforce connector
        sf_connector = SalesforceConnector(db=db, tenant_id=probe_tenant_id)
        
        # Step 1: Fetch latest Salesforce Opportunity
        print("📡 Step 1: Fetching latest Salesforce Opportunity...")
        sf_opportunity = await sf_connector.get_latest_opportunity()
        
        if not sf_opportunity:
            print("❌ Failed to fetch Salesforce opportunity - check SALESFORCE_ACCESS_TOKEN and SALESFORCE_INSTANCE_URL")
            print("\nAOS_FUNC_STATUS: FAIL")
            return
        
        opportunity_id = sf_opportunity.get("Id", "unknown")
        name = sf_opportunity.get("Name", "unknown")
        amount = sf_opportunity.get("Amount")
        
        print(f"✅ Fetched Opportunity: {opportunity_id} - {name}")
        print(f"   Amount: {amount}, Stage: {sf_opportunity.get('StageName', 'unknown')}\n")
        
        # Step 2: Normalize through AAM
        print("🔄 Step 2: Normalizing through AAM (Salesforce → Canonical)...")
        canonical_event = sf_connector.normalize_opportunity(sf_opportunity, trace_id)
        print(f"✅ Normalized to canonical format")
        print(f"   Entity: {canonical_event.entity}")
        print(f"   Opportunity ID: {canonical_event.data.opportunity_id}")
        print(f"   Account ID: {canonical_event.data.account_id}\n")
        
        # Step 3: Emit canonical event
        print("📤 Step 3: Emitting canonical event to AAM streams...")
        sf_connector.emit_canonical_event(canonical_event)
        print(f"✅ Canonical event emitted\n")
        
        # Step 4: Process through DCL subscriber (materialize)
        print("🔨 Step 4: Processing through DCL subscriber (materializing)...")
        try:
            result = process_canonical_streams(db, tenant_id=probe_tenant_id)
            print(f"✅ DCL subscriber processed canonical streams")
            print(f"   Processed: {result.get('accounts_processed', 0)} accounts, {result.get('opportunities_processed', 0)} opportunities\n")
        except Exception as e:
            print(f"⚠️ DCL subscriber processing error: {e}\n")
        
        # Step 5: Verify materialization with exponential backoff
        print("🔍 Step 5: Verifying DCL materialization (exponential backoff)...")
        view_count = await verify_dcl_materialization(opportunity_id, max_retries=10)
        print()
        
        # Step 6: Print verification output (EXACT FORMAT)
        print("=" * 80)
        print("VERIFICATION OUTPUT")
        print("=" * 80)
        print(f"AOS_FUNC_CANONICAL_ID: {opportunity_id}")
        print(f"AOS_FUNC_CANONICAL_NAME: {name}")
        print(f"AOS_FUNC_CANONICAL_AMOUNT: {amount if amount is not None else 'null'}")
        print(f"AOS_FUNC_TRACE_ID: {trace_id}")
        print(f"AOS_FUNC_VIEW_COUNT: {view_count}")
        print(f"AOS_FUNC_STATUS: {'PASS' if view_count == 1 else 'FAIL'}")
        print("=" * 80)
        
        # Print debug endpoint URL
        base_url = os.getenv("BASE_URL", "http://localhost:5000")
        debug_url = f"{base_url}/api/v1/debug/last-canonical?entity=opportunity&limit=1"
        print(f"\n📊 Debug Endpoint: {debug_url}")
        print()
        
    except Exception as e:
        print(f"\n❌ Functional probe failed: {e}")
        import traceback
        traceback.print_exc()
        print(f"\nAOS_FUNC_STATUS: FAIL")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(run_functional_probe())
