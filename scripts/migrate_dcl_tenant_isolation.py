#!/usr/bin/env python3
"""
Migration: Add tenant_id to DCL unified contact tables
This is a critical security fix for multi-tenant data isolation
"""
import os
import sys

from sqlalchemy import text
from app.database import SessionLocal, engine
from app.models import Base, DCLUnifiedContact, DCLUnifiedContactLink


def migrate_dcl_tenant_isolation():
    """
    Drop and recreate DCL unified contact tables with tenant_id columns.
    This is necessary because we're changing unique constraints.
    """
    db = SessionLocal()
    
    try:
        print("\n" + "=" * 80)
        print("DCL TENANT ISOLATION MIGRATION")
        print("=" * 80)
        
        # Step 1: Check if tables exist and have data
        print("\n🔍 Step 1: Checking existing tables...")
        
        result = db.execute(text("""
            SELECT COUNT(*) as count FROM dcl_unified_contact_link
        """))
        link_count = result.scalar()
        
        result = db.execute(text("""
            SELECT COUNT(*) as count FROM dcl_unified_contact
        """))
        contact_count = result.scalar()
        
        print(f"   Found {contact_count} unified contacts")
        print(f"   Found {link_count} links")
        
        if contact_count > 0 or link_count > 0:
            print("\n⚠️  WARNING: Tables contain data that will be deleted!")
            print("   This migration drops and recreates the tables.")
            print("   In production, you would need to migrate the data.")
            print("   Proceeding with drop (OK for dev/demo)...")
        
        # Step 2: Drop existing tables
        print("\n🗑️  Step 2: Dropping existing DCL tables...")
        
        db.execute(text("""
            DROP TABLE IF EXISTS dcl_unified_contact_link CASCADE
        """))
        print("   ✅ Dropped dcl_unified_contact_link")
        
        db.execute(text("""
            DROP TABLE IF EXISTS dcl_unified_contact CASCADE
        """))
        print("   ✅ Dropped dcl_unified_contact")
        
        db.commit()
        
        # Step 3: Recreate tables with tenant_id using SQLAlchemy models
        print("\n🔨 Step 3: Creating tables with tenant_id columns...")
        
        # Create only the DCL tables
        DCLUnifiedContact.__table__.create(engine, checkfirst=True)
        print("   ✅ Created dcl_unified_contact with tenant_id")
        
        DCLUnifiedContactLink.__table__.create(engine, checkfirst=True)
        print("   ✅ Created dcl_unified_contact_link with tenant_id")
        
        # Step 4: Verify schema
        print("\n✅ Step 4: Verifying new schema...")
        
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'dcl_unified_contact'
            ORDER BY ordinal_position
        """))
        
        print("\n   dcl_unified_contact columns:")
        for row in result:
            nullable = "NULL" if row.is_nullable == "YES" else "NOT NULL"
            print(f"     - {row.column_name}: {row.data_type} {nullable}")
        
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'dcl_unified_contact_link'
            ORDER BY ordinal_position
        """))
        
        print("\n   dcl_unified_contact_link columns:")
        for row in result:
            nullable = "NULL" if row.is_nullable == "YES" else "NOT NULL"
            print(f"     - {row.column_name}: {row.data_type} {nullable}")
        
        # Step 5: Verify unique constraints
        print("\n   Unique constraints:")
        result = db.execute(text("""
            SELECT
                tc.table_name,
                tc.constraint_name,
                kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.constraint_type = 'UNIQUE'
            AND tc.table_name IN ('dcl_unified_contact', 'dcl_unified_contact_link')
            ORDER BY tc.table_name, tc.constraint_name, kcu.ordinal_position
        """))
        
        constraints = {}
        for row in result:
            key = (row.table_name, row.constraint_name)
            if key not in constraints:
                constraints[key] = []
            constraints[key].append(row.column_name)
        
        for (table, constraint), columns in constraints.items():
            print(f"     - {table}.{constraint}: ({', '.join(columns)})")
        
        print("\n" + "=" * 80)
        print("✅ MIGRATION COMPLETE")
        print("=" * 80)
        print("\nNext steps:")
        print("  1. Update app/api/v1/dcl_unify.py to use tenant_id")
        print("  2. Update scripts/seed_demo_contacts.py to use tenant_id")
        print("  3. Update tests to verify multi-tenant isolation")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    
    finally:
        db.close()


if __name__ == "__main__":
    success = migrate_dcl_tenant_isolation()
    sys.exit(0 if success else 1)
