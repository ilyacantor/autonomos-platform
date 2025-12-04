#!/usr/bin/env python3
"""
Seed Demo Contacts for DCL Unification Testing
Creates 2 contacts with same email from different sources
"""
import os
import sys
import uuid
from datetime import datetime

from sqlalchemy import text
from app.database import SessionLocal
from app.models import CanonicalStream

DEMO_TENANT_UUID = "9ac5c8c6-1a02-48ff-84a0-122b67f9c3bd"


def seed_demo_contacts(tenant_id=None):
    """
    Seed demo contacts for DCL unification testing
    
    Args:
        tenant_id: Optional tenant UUID string. If not provided, uses DEMO_TENANT_UUID
                   or first tenant from database
    """
    db = SessionLocal()
    
    try:
        print("\n" + "=" * 60)
        print("DCL Demo Contact Seeder")
        print("=" * 60)
        
        # Determine tenant_id
        if tenant_id is None:
            # Try to use demo tenant or first tenant from database
            result = db.execute(text("""
                SELECT id FROM tenants 
                WHERE id = :demo_tenant_id OR name = 'Demo Tenant'
                LIMIT 1
            """), {"demo_tenant_id": DEMO_TENANT_UUID})
            row = result.fetchone()
            
            if not row:
                # Fall back to first tenant
                result = db.execute(text("SELECT id FROM tenants LIMIT 1"))
                row = result.fetchone()
            
            if row:
                tenant_id = str(row.id)
                print(f"   Using tenant: {tenant_id}")
            else:
                print("   ⚠️  No tenants found in database, using default: {DEMO_TENANT_UUID}")
                tenant_id = DEMO_TENANT_UUID
        
        print(f"   Tenant ID: {tenant_id}")
        
        # Clear existing demo data
        print("\n🧹 Clearing existing demo contacts...")
        result = db.execute(text("""
            DELETE FROM canonical_streams
            WHERE entity = 'contact'
            AND data->>'contact_id' LIKE 'DEMO-%'
        """))
        db.commit()
        print(f"   Deleted {result.rowcount} existing demo records")
        
        # Create demo contacts
        demo_contacts = [
            {
                "contact_id": "DEMO-SF-001",
                "email": "sam@acme.com",
                "first_name": "Sam",
                "last_name": "Salesforce",
                "source_system": "filesource",
                "source_connection_id": "salesforce"
            },
            {
                "contact_id": "DEMO-CRM-001",
                "email": "sam@acme.com",
                "first_name": "Samuel",
                "last_name": "CRM",
                "source_system": "filesource",
                "source_connection_id": "crm"
            }
        ]
        
        print(f"\n📊 Creating {len(demo_contacts)} demo contacts...")
        
        for contact in demo_contacts:
            canonical_data = {
                "contact_id": contact["contact_id"],
                "email": contact["email"],
                "first_name": contact["first_name"],
                "last_name": contact["last_name"]
            }
            
            source_data = {
                "system": contact["source_system"],
                "connection_id": contact["source_connection_id"]
            }
            
            stream_record = CanonicalStream(
                id=uuid.uuid4(),
                tenant_id=uuid.UUID(tenant_id),
                entity="contact",
                data=canonical_data,
                meta={"version": "1.0", "schema": "canonical_v1"},
                source=source_data,
                emitted_at=datetime.utcnow()
            )
            
            db.add(stream_record)
            print(f"   ✅ Created: {contact['contact_id']} ({contact['email']}) from {contact['source_system']}-{contact['source_connection_id']}")
        
        db.commit()
        
        # Verify
        print("\n📋 Verifying seeded data...")
        result = db.execute(text("""
            SELECT 
                data->>'contact_id' as contact_id,
                data->>'email' as email,
                data->>'first_name' as first_name,
                source->>'system' as source_system,
                source->>'connection_id' as source_connection_id
            FROM canonical_streams
            WHERE entity = 'contact'
            AND data->>'contact_id' LIKE 'DEMO-%'
        """))
        
        rows = result.fetchall()
        print(f"   Found {len(rows)} demo contacts:")
        for row in rows:
            print(f"     - {row.contact_id}: {row.first_name} ({row.email}) from {row.source_system}-{row.source_connection_id}")
        
        print("\n" + "=" * 60)
        print("✅ Demo Contact Seeding Complete!")
        print("=" * 60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error seeding demo contacts: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    
    finally:
        db.close()


if __name__ == "__main__":
    success = seed_demo_contacts()
    sys.exit(0 if success else 1)
