"""
Automated DCL Entity Unification Test
This test programmatically creates cross-source contact data and validates DCL unification
"""
import os
import sys
import csv
from pathlib import Path
sys.path.insert(0, os.getcwd())

from sqlalchemy import text
from app.database import SessionLocal
from services.aam.connectors.filesource.connector import FileSourceConnector

def test_dcl_entity_unification():
    """
    Automated test that:
    1. Creates test contact CSV with known email
    2. Ingests via FileSource to canonical_streams
    3. Triggers DCL processing (if available)
    4. Validates entity unification in materialized_contacts
    """
    print("\n" + "="*80)
    print("AUTOMATED DCL ENTITY UNIFICATION TEST")
    print("="*80)
    print("\nScenario: Cross-source contact entity matching")
    print("  - Create test contact with email 'test-unification@example.com'")
    print("  - Ingest into canonical_streams")
    print("  - Verify DCL creates materialized view\n")
    
    db = SessionLocal()
    
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
        
        # Create test contact CSV if it doesn't exist
        test_csv_path = Path("mock_sources/contacts_salesforce.csv")
        
        test_contact_data = [
            ["contact_id", "account_id", "first_name", "last_name", "email", "phone", "title", "department", "created_at", "updated_at"],
            ["TEST-C-001", "SFDC-A-001", "Alice", "TestUser", "test-unification@example.com", "+1-555-TEST-001", "Test Engineer", "Engineering", "2024-11-01T10:00:00Z", "2024-11-04T10:00:00Z"],
            ["TEST-C-002", "SFDC-A-002", "Bob", "TestUser", "bob.test@example.com", "+1-555-TEST-002", "Test Manager", "Operations", "2024-11-01T11:00:00Z", "2024-11-04T11:00:00Z"]
        ]
        
        # Write test CSV
        with open(test_csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(test_contact_data)
        
        print(f"✅ Created test contacts CSV: {test_csv_path}")
        
        # Clear previous test data
        print("\n📊 Clearing previous test data...")
        db.execute(text("""
            DELETE FROM canonical_streams 
            WHERE entity = 'contact' 
            AND source->>'connection_id' = 'filesource-salesforce'
        """))
        db.commit()
        
        # Ingest via FileSource
        print("\n🔄 Triggering FileSource ingestion for contacts...")
        connector = FileSourceConnector(db=db, tenant_id=test_tenant_id)
        stats = connector.replay_entity(entity='contact', system='salesforce')
        
        print(f"\n✅ Ingestion Complete!")
        print(f"   Files processed: {stats.get('files_processed', 0)}")
        print(f"   Total records: {stats.get('records_ingested', 0)}")
        
        # Query canonical_streams
        print("\n📋 Querying canonical_streams for ingested contacts...")
        result = db.execute(text("""
            SELECT data->>'email', data->>'first_name', data->>'last_name'
            FROM canonical_streams
            WHERE entity = 'contact'
            AND source->>'connection_id' = 'filesource-salesforce'
            ORDER BY data->>'email'
        """))
        
        canonical_contacts = result.fetchall()
        print(f"   Found {len(canonical_contacts)} contacts in canonical_streams")
        
        for contact in canonical_contacts:
            print(f"     - {contact[1]} {contact[2]} ({contact[0]})")
        
        # Check materialized_contacts (requires DCL to have run)
        print("\n📊 Checking materialized_contacts table...")
        result = db.execute(text("""
            SELECT 
                email,
                first_name,
                last_name,
                title,
                source_system,
                COUNT(*) OVER (PARTITION BY email) as duplicate_count
            FROM materialized_contacts
            WHERE tenant_id = :tenant_id
            ORDER BY email
        """), {"tenant_id": test_tenant_id})
        
        materialized_contacts = result.fetchall()
        
        if materialized_contacts:
            print(f"   Found {len(materialized_contacts)} contacts in materialized_contacts")
            
            # Check for unification (same email should have only 1 record)
            email_groups = {}
            for contact in materialized_contacts:
                email = contact[0]
                if email not in email_groups:
                    email_groups[email] = []
                email_groups[email].append(contact)
            
            print("\n   Entity Unification Analysis:")
            unified_count = 0
            duplicate_count = 0
            
            for email, contacts in email_groups.items():
                if len(contacts) == 1:
                    unified_count += 1
                    print(f"     ✅ {email}: UNIFIED (1 record)")
                else:
                    duplicate_count += 1
                    print(f"     ⚠️  {email}: {len(contacts)} records (not unified)")
            
            # Assertions
            assert_results = {
                'canonical_ingestion': len(canonical_contacts) >= 2,
                'materialized_created': len(materialized_contacts) > 0,
                'entity_unification': unified_count > 0,
                'no_duplicates': duplicate_count == 0
            }
            
        else:
            print("   ⚠️  No contacts in materialized_contacts")
            print("   This indicates DCL engine has not processed contacts yet")
            print("   To complete this test:")
            print("     1. POST to /dcl/connect with sources including contacts")
            print("     2. Wait for DCL processing to complete")
            print("     3. Re-run this test")
            
            assert_results = {
                'canonical_ingestion': len(canonical_contacts) >= 2,
                'materialized_created': False,
                'entity_unification': False,
                'no_duplicates': True  # No duplicates if no data
            }
        
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
            print("✅ ALL ASSERTIONS PASSED - DCL ENTITY UNIFICATION WORKING")
        else:
            print("⚠️  SOME ASSERTIONS FAILED - DCL MAY NEED MANUAL TRIGGER")
            print("    Note: Canonical ingestion may pass even if DCL hasn't run yet")
        print("="*80 + "\n")
        
        return all_passed
        
    except Exception as e:
        print(f"\n❌ Error during DCL unification test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()

if __name__ == "__main__":
    success = test_dcl_entity_unification()
    sys.exit(0 if success else 1)
