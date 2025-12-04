#!/usr/bin/env python3
"""
Backfill tenant_id for connections with NULL values.

This script safely updates all connections with NULL tenant_id to use the demo tenant UUID.
Provides pre/post counts for verification.

Usage:
    python scripts/backfill_tenant_ids.py
    make prod-backfill-tenants
"""

import os
import sys

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Demo tenant UUID (matches migration default)
DEMO_TENANT_UUID = "f8ab4417-86a1-4dd2-a049-ea423063850e"


def main():
    """Execute tenant_id backfill with pre/post counts."""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    print("=" * 60)
    print("🔧 AAM Connections - Tenant ID Backfill")
    print("=" * 60)
    print(f"Database: {database_url.split('@')[-1] if '@' in database_url else 'local'}")
    print(f"Demo Tenant UUID: {DEMO_TENANT_UUID}")
    print()
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Pre-backfill counts
                print("📊 Pre-Backfill Status:")
                print("-" * 60)
                
                total_count = conn.execute(
                    text("SELECT COUNT(*) FROM connections")
                ).scalar()
                print(f"   Total connections: {total_count}")
                
                null_count = conn.execute(
                    text("SELECT COUNT(*) FROM connections WHERE tenant_id IS NULL")
                ).scalar()
                print(f"   Connections with NULL tenant_id: {null_count}")
                
                demo_count = conn.execute(
                    text("SELECT COUNT(*) FROM connections WHERE tenant_id = :tenant_id"),
                    {"tenant_id": DEMO_TENANT_UUID}
                ).scalar()
                print(f"   Connections with demo tenant_id: {demo_count}")
                print()
                
                if null_count == 0:
                    print("✅ No NULL tenant_id values found. Database is clean!")
                    trans.rollback()
                    return 0
                
                # Execute backfill
                print(f"🔄 Backfilling {null_count} connections...")
                result = conn.execute(
                    text("""
                        UPDATE connections 
                        SET tenant_id = :tenant_id 
                        WHERE tenant_id IS NULL
                    """),
                    {"tenant_id": DEMO_TENANT_UUID}
                )
                
                rows_updated = result.rowcount
                print(f"   Updated {rows_updated} rows")
                print()
                
                # Post-backfill counts
                print("📊 Post-Backfill Status:")
                print("-" * 60)
                
                null_count_after = conn.execute(
                    text("SELECT COUNT(*) FROM connections WHERE tenant_id IS NULL")
                ).scalar()
                print(f"   Connections with NULL tenant_id: {null_count_after}")
                
                demo_count_after = conn.execute(
                    text("SELECT COUNT(*) FROM connections WHERE tenant_id = :tenant_id"),
                    {"tenant_id": DEMO_TENANT_UUID}
                ).scalar()
                print(f"   Connections with demo tenant_id: {demo_count_after}")
                print()
                
                # Verify success
                if null_count_after == 0:
                    print("✅ SUCCESS: All connections now have tenant_id assigned")
                    trans.commit()
                    print("✅ Changes committed to database")
                    return 0
                else:
                    print(f"⚠️  WARNING: Still {null_count_after} NULL tenant_id values remain")
                    trans.rollback()
                    print("❌ Changes rolled back")
                    return 1
                    
            except Exception as e:
                trans.rollback()
                print(f"❌ ERROR during backfill: {e}")
                print("❌ Changes rolled back")
                raise
                
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
        return 1
    finally:
        print("=" * 60)


if __name__ == "__main__":
    sys.exit(main())
