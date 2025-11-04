"""
Automated AAM Schema Drift Test
This test programmatically creates drift scenarios without manual CSV edits
"""
import os
import sys
import csv
import tempfile
import shutil
from pathlib import Path
sys.path.insert(0, os.getcwd())

from sqlalchemy import text
from app.database import SessionLocal
from services.aam.connectors.filesource.connector import FileSourceConnector

def test_aam_schema_drift_automated():
    """
    Automated test that:
    1. Creates a temporary modified CSV with schema drift
    2. Points FileSource to the temp directory
    3. Ingests and validates drift handling
    4. Asserts specific outcomes (15 unknown fields, extras preservation)
    """
    print("\n" + "="*80)
    print("AUTOMATED AAM SCHEMA DRIFT TEST")
    print("="*80)
    print("\nScenario: Programmatic schema drift simulation")
    print("  - Clone opportunities_salesforce.csv to temp directory")
    print("  - Rename 'amount' → 'opportunity_amount' in header")
    print("  - Ingest and verify drift handling\n")
    
    db = SessionLocal()
    temp_dir = None
    
    try:
        # Get existing tenant
        print("📊 Looking for existing tenant...")
        result = db.execute(text("SELECT id FROM tenants LIMIT 1"))
        tenant_row = result.fetchone()
        
        if not tenant_row:
            print("   ❌ No tenants found - cannot run test")
            return False
        
        test_tenant_id = str(tenant_row[0])
        print(f"   Using tenant: {test_tenant_id}")
        
        # Create temporary directory with modified CSV
        temp_dir = tempfile.mkdtemp(prefix="aam_drift_test_")
        print(f"\n📁 Created temp directory: {temp_dir}")
        
        # Copy and modify the opportunities CSV
        source_csv = Path("mock_sources/opportunities_salesforce.csv")
        temp_csv = Path(temp_dir) / "opportunities_salesforce.csv"
        
        with open(source_csv, 'r') as src:
            reader = csv.reader(src)
            rows = list(reader)
        
        # Modify header: amount → opportunity_amount
        header = rows[0]
        if 'amount' in header:
            idx = header.index('amount')
            header[idx] = 'opportunity_amount'
            print(f"   ✏️  Modified header: 'amount' → 'opportunity_amount' at index {idx}")
        else:
            print("   ⚠️  'amount' column not found in CSV")
            return False
        
        # Write modified CSV
        with open(temp_csv, 'w', newline='') as dest:
            writer = csv.writer(dest)
            writer.writerows(rows)
        
        print(f"   ✅ Created modified CSV: {temp_csv}")
        
        # Clear previous canonical_streams data
        print("\n📊 Clearing previous test data...")
        db.execute(text("""
            DELETE FROM canonical_streams 
            WHERE entity = 'opportunity' 
            AND source->>'connection_id' = 'filesource-salesforce-drift-test'
        """))
        db.commit()
        
        # Initialize FileSource with temp directory
        # Note: This requires modifying FileSourceConnector to accept custom base_path
        # For now, we'll temporarily override the mock_sources path
        original_mock_path = Path("mock_sources")
        backup_path = Path("mock_sources_backup")
        
        # Backup original CSV
        if backup_path.exists():
            shutil.rmtree(backup_path)
        backup_path.mkdir(parents=True)
        shutil.copy(original_mock_path / "opportunities_salesforce.csv", 
                   backup_path / "opportunities_salesforce.csv")
        
        try:
            # Replace with test CSV
            shutil.copy(temp_csv, original_mock_path / "opportunities_salesforce.csv")
            
            print("\n🔄 Triggering FileSource ingestion with drifted schema...")
            connector = FileSourceConnector(db=db, tenant_id=test_tenant_id)
            stats = connector.replay_entity(entity='opportunity', system='salesforce')
            
            print(f"\n✅ Ingestion Complete!")
            print(f"   Files processed: {stats.get('files_processed', 0)}")
            print(f"   Total records: {stats.get('records_ingested', 0)}")
            print(f"   Unknown fields: {stats.get('unknown_fields_count', 0)}")
        
        finally:
            # Always restore original CSV, even if ingestion fails
            if backup_path.exists():
                shutil.copy(backup_path / "opportunities_salesforce.csv", 
                           original_mock_path / "opportunities_salesforce.csv")
                shutil.rmtree(backup_path)
                print("   🔄 Restored original opportunities_salesforce.csv")
        
        # Query and validate results
        print("\n📋 Querying canonical_streams...")
        result = db.execute(text("""
            SELECT data, meta
            FROM canonical_streams
            WHERE entity = 'opportunity'
            AND source->>'connection_id' = 'filesource-salesforce'
            ORDER BY data->>'opportunity_id'
            LIMIT 5
        """))
        
        records = result.fetchall()
        print(f"\n📊 Found {len(records)} opportunity records")
        
        # Assertions
        assert_results = {
            'total_records': len(records) >= 3,
            'unknown_fields_count': stats.get('unknown_fields_count', 0) >= 15,
            'extras_preserved': False,
            'canonical_amount_null': False
        }
        
        if records:
            first_record = records[0]
            data = first_record[0]
            
            # Check if canonical amount is None
            assert_results['canonical_amount_null'] = data.get('amount') is None
            
            # Check if opportunity_amount is in extras
            extras = data.get('extras', {})
            assert_results['extras_preserved'] = 'opportunity_amount' in extras
            
            print("\n   Sample Record Analysis:")
            print(f"     Opportunity ID: {data.get('opportunity_id')}")
            print(f"     Name: {data.get('name')}")
            print(f"     Canonical 'amount': {data.get('amount')}")
            print(f"     Extras keys: {list(extras.keys())}")
            if 'opportunity_amount' in extras:
                print(f"     Preserved 'opportunity_amount': {extras['opportunity_amount']}")
        
        # Print assertion results
        print("\n" + "="*80)
        print("AUTOMATED TEST ASSERTIONS")
        print("="*80)
        all_passed = True
        for check, passed in assert_results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {check}: {passed}")
            if not passed:
                all_passed = False
        
        print("\n" + "="*80)
        if all_passed:
            print("✅ ALL ASSERTIONS PASSED - AAM DRIFT DETECTION WORKING")
            print("[POW] AAM_DRIFT_PASS")
        else:
            print("❌ SOME ASSERTIONS FAILED - REVIEW RESULTS ABOVE")
        print("="*80 + "\n")
        
        return all_passed
        
    except Exception as e:
        print(f"\n❌ Error during automated drift test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir)
            print(f"🧹 Cleaned up temp directory")

if __name__ == "__main__":
    success = test_aam_schema_drift_automated()
    sys.exit(0 if success else 1)
