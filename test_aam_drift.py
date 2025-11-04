"""
Test script for AAM Schema Drift Detection
Part 1: Tests FileSource with schema drift (amount -> opportunity_amount)
"""
import os
import sys
sys.path.insert(0, os.getcwd())

from sqlalchemy import text
from app.database import SessionLocal
from services.aam.connectors.filesource.connector import FileSourceConnector

def test_schema_drift():
    print("\n" + "="*80)
    print("PART 1: AAM SCHEMA DRIFT TEST")
    print("="*80)
    print("\nScenario: Modified opportunities_salesforce.csv")
    print("  - Renamed column 'amount' -> 'opportunity_amount'")
    print("  - Testing AAM's handling of unmapped fields\n")
    
    db = SessionLocal()
    
    try:
        # Clear previous data for clean test
        print("📊 Clearing previous canonical_streams data for opportunity/salesforce...")
        db.execute(text("DELETE FROM canonical_streams WHERE entity = 'opportunity' AND source->>'connection_id' = 'filesource-salesforce'"))
        db.commit()
        
        # Initialize FileSource connector
        connector = FileSourceConnector(db=db, tenant_id="test-tenant")
        
        # Run ingestion for salesforce opportunities only
        print("\n🔄 Triggering FileSource ingestion for Salesforce opportunities...")
        stats = connector.replay_entity(entity='opportunity', system='salesforce')
        
        # Display results
        print("\n✅ Ingestion Complete!")
        print(f"   Files processed: {stats['files_processed']}")
        print(f"   Total records: {stats['total_records']}")
        print(f"   Unknown fields count: {stats['unknown_fields_count']}")
        
        # Query canonical_streams to check how unmapped field was handled
        print("\n📋 Querying canonical_streams for ingested records...")
        result = db.execute(text("""
            SELECT 
                entity,
                data->>'opportunity_id' as opp_id,
                data->>'name' as name,
                data->>'amount' as canonical_amount,
                data->'extras' as extras,
                meta
            FROM canonical_streams 
            WHERE entity = 'opportunity' 
            AND source->>'connection_id' = 'filesource-salesforce'
            ORDER BY id DESC
            LIMIT 3
        """))
        
        records = result.fetchall()
        
        print(f"\n📊 Found {len(records)} opportunity records:")
        for i, record in enumerate(records, 1):
            print(f"\n   Record {i}:")
            print(f"     Opportunity ID: {record.opp_id}")
            print(f"     Name: {record.name}")
            print(f"     Canonical 'amount' field: {record.canonical_amount}")
            print(f"     Extras (unmapped fields): {record.extras}")
        
        # Check if opportunity_amount is in extras
        if records:
            first_extras = records[0].extras
            if first_extras and 'opportunity_amount' in first_extras:
                print("\n✅ DRIFT DETECTION RESULT:")
                print("   'opportunity_amount' was detected as an UNKNOWN FIELD")
                print("   It was preserved in 'extras' dictionary")
                print(f"   Value: {first_extras['opportunity_amount']}")
                print("\n   Note: AAM detected the drift and preserved the data")
                print("   In production, this would trigger a drift event for auto-repair")
            else:
                print("\n⚠️  WARNING: 'opportunity_amount' not found in extras")
                print("   The unmapped field may have been dropped")
        
    except Exception as e:
        print(f"\n❌ Error during ingestion: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()
    
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    test_schema_drift()
