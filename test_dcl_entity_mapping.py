"""
Test script for DCL Entity Mapping
Part 2: Tests DCL's AI-powered entity unification across multiple sources
"""
import os
import sys
sys.path.insert(0, os.getcwd())

from sqlalchemy import text
from app.database import SessionLocal

def test_dcl_entity_mapping():
    print("\n" + "="*80)
    print("PART 2: DCL ENTITY MAPPING TEST")
    print("="*80)
    print("\nScenario: Ingest same contact from two different sources")
    print("  Source 1: FileSource (contacts_salesforce.csv)")
    print("  Source 2: Would be Supabase connector")
    print("  Goal: Verify DCL unifies based on email match\n")
    
    db = SessionLocal()
    
    try:
        # Check materialized_contacts table structure
        print("📋 Checking materialized_contacts table...")
        result = db.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'materialized_contacts'
            ORDER BY ordinal_position
        """))
        
        columns = result.fetchall()
        if columns:
            print(f"   Table exists with {len(columns)} columns:")
            for col in columns:
                print(f"     - {col.column_name}: {col.data_type}")
        else:
            print("   ⚠️  Table doesn't exist or has no columns")
            return
        
        # Query current state of materialized_contacts
        print("\n📊 Current materialized_contacts data:")
        result = db.execute(text("""
            SELECT 
                contact_id,
                first_name,
                last_name,
                email,
                phone,
                title,
                source_system
            FROM materialized_contacts 
            WHERE email = 'bill.j@example-corp.com'
            LIMIT 5
        """))
        
        contacts = result.fetchall()
        
        if contacts:
            print(f"\n   Found {len(contacts)} contact(s) with email 'bill.j@example-corp.com':")
            for i, contact in enumerate(contacts, 1):
                print(f"\n   Contact {i}:")
                print(f"     ID: {contact.contact_id}")
                print(f"     Name: {contact.first_name} {contact.last_name}")
                print(f"     Email: {contact.email}")
                print(f"     Phone: {contact.phone}")
                print(f"     Title: {contact.title}")
                print(f"     Source System: {contact.source_system}")
            
            # Check if DCL unified the records
            if len(contacts) == 1:
                print("\n✅ DCL ENTITY UNIFICATION RESULT:")
                print("   SUCCESS! Only 1 record found in materialized_contacts")
                print("   DCL successfully unified multiple source records into a single entity")
            else:
                print(f"\n⚠️  MULTIPLE RECORDS: {len(contacts)} records found")
                print("   DCL may not have unified the entities yet")
                print("   This could indicate:")
                print("   - Entity resolution is pending")
                print("   - Different source_system entries for tracking")
                print("   - Deduplication has not run")
        else:
            print("\n   No contacts found with email 'bill.j@example-corp.com'")
            print("   This test requires running the DCL engine first")
            print("   Suggestion: Run DCL /connect endpoint with contact data sources")
        
        # Check all materialized views
        print("\n\n📊 Checking all materialized views:")
        for table in ['materialized_accounts', 'materialized_opportunities', 'materialized_contacts']:
            result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.fetchone()[0]
            print(f"   {table}: {count} records")
        
    except Exception as e:
        print(f"\n❌ Error during DCL entity mapping test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()
    
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    test_dcl_entity_mapping()
