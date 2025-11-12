#!/usr/bin/env python3
"""
FilesSource → mapping_registry ingest script (idempotent)

Processes CSV files from a directory and populates mapping_registry table
with field mappings for a given connection.

Usage:
    python scripts/filesource_ingest.py --connection-id <uuid> --namespace <namespace>
"""

import argparse
import csv
import glob
import os
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def infer_dtype(values):
    """Basic dtype inference from sample values"""
    if not values or all(v == '' for v in values):
        return 'string'
    
    # Try numeric
    try:
        [float(v) for v in values if v]
        # Check if all are integers
        if all(float(v).is_integer() for v in values if v):
            return 'integer'
        return 'float'
    except (ValueError, AttributeError):
        pass
    
    # Check for common date patterns
    for v in values:
        if v and ('-' in v or '/' in v) and len(v) >= 8:
            return 'date'
    
    return 'string'


def process_csv(file_path, connection_id, tenant_id, vendor, session, sample_size=50):
    """Process a single CSV file and upsert mappings"""
    filename = os.path.basename(file_path)
    print(f"  Processing: {filename}")
    
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        
        if not headers:
            print(f"    ⚠️  No headers found, skipping")
            return 0
        
        # Sample rows for dtype inference
        rows = []
        for i, row in enumerate(reader):
            if i >= sample_size:
                break
            rows.append(row)
        
        mappings_created = 0
        
        for field in headers:
            # Get sample values for this field
            sample_values = [row.get(field, '') for row in rows]
            dtype = infer_dtype(sample_values)
            
            # Upsert mapping (idempotent) using ON CONFLICT
            from uuid import uuid4
            result = session.execute(
                text("""
                    INSERT INTO mapping_registry 
                    (id, tenant_id, connection_id, vendor, vendor_field, canonical_field, coercion, confidence, version, created_at)
                    VALUES 
                    (:id, :tenant_id, :connection_id, :vendor, :vendor_field, :canonical_field, :dtype, :confidence, 1, :created_at)
                    ON CONFLICT (connection_id, vendor_field) 
                    DO UPDATE SET
                        canonical_field = EXCLUDED.canonical_field,
                        coercion = EXCLUDED.coercion,
                        confidence = EXCLUDED.confidence,
                        version = mapping_registry.version + 1
                    RETURNING (xmax = 0) AS inserted
                """),
                {
                    "id": str(uuid4()),
                    "tenant_id": str(tenant_id),
                    "connection_id": connection_id,
                    "vendor": vendor,
                    "vendor_field": field,
                    "canonical_field": field,  # Default: same as source
                    "dtype": dtype,
                    "confidence": 0.80,
                    "created_at": datetime.utcnow()
                }
            ).fetchone()
            
            # Track if this was a new insert (xmax = 0 means no UPDATE happened)
            if result and result[0]:
                mappings_created += 1
        
        session.commit()
        print(f"    ✅ {len(headers)} fields, {mappings_created} new mappings")
        return mappings_created


def main():
    parser = argparse.ArgumentParser(description='Ingest FilesSource CSVs into mapping_registry')
    parser.add_argument('--connection-id', default='10ca3a88-5105-4e24-b984-6e350a5fa443',
                        help='Connection UUID (default: FilesSource Demo)')
    parser.add_argument('--namespace', default='demo',
                        help='Namespace for tenant isolation (default: demo)')
    parser.add_argument('--directory', default='mock_sources',
                        help='Directory containing CSV files (default: mock_sources)')
    parser.add_argument('--pattern', default='*filesource*.csv',
                        help='Glob pattern for CSV files (default: *filesource*.csv)')
    
    args = parser.parse_args()
    
    # Get database URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not set")
        sys.exit(1)
    
    # Create engine and session
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # Validate connection exists
        conn_result = session.execute(
            text("SELECT id, source_type FROM connections WHERE id = :conn_id"),
            {"conn_id": args.connection_id}
        ).fetchone()
        
        if not conn_result:
            print(f"❌ Connection {args.connection_id} not found")
            sys.exit(1)
        
        vendor = conn_result[1]
        print(f"✅ Connection found: {args.connection_id} (vendor: {vendor})")
        
        # Get or create tenant for namespace
        tenant_result = session.execute(
            text("SELECT id FROM tenants WHERE name = :namespace LIMIT 1"),
            {"namespace": args.namespace}
        ).fetchone()
        
        if tenant_result:
            tenant_id = tenant_result[0]
        else:
            # Create tenant for this namespace
            tenant_id_str = str(UUID(int=hash(args.namespace) % (2**128)))
            session.execute(
                text("""
                    INSERT INTO tenants (id, name, created_at) 
                    VALUES (:id, :name, :created_at)
                    ON CONFLICT (name) DO NOTHING
                """),
                {
                    "id": tenant_id_str,
                    "name": args.namespace,
                    "created_at": datetime.utcnow()
                }
            )
            session.commit()
            tenant_id = tenant_id_str
        
        print(f"✅ Tenant: {args.namespace} ({tenant_id})")
        
        # Find CSV files
        csv_files = glob.glob(os.path.join(args.directory, args.pattern))
        if not csv_files:
            print(f"⚠️  No CSV files matching '{args.pattern}' in {args.directory}")
            sys.exit(0)
        
        print(f"\n📁 Found {len(csv_files)} CSV file(s)")
        
        total_mappings = 0
        for csv_file in sorted(csv_files):
            mappings = process_csv(csv_file, args.connection_id, tenant_id, vendor, session)
            total_mappings += mappings
        
        # Get final count
        final_count = session.execute(
            text("""
                SELECT COUNT(*) FROM mapping_registry 
                WHERE tenant_id = :tenant_id AND vendor = :vendor
            """),
            {"tenant_id": str(tenant_id), "vendor": vendor}
        ).scalar()
        
        print(f"\n✅ Ingest complete!")
        print(f"   Files processed: {len(csv_files)}")
        print(f"   New mappings created: {total_mappings}")
        print(f"   Total mappings for {vendor}: {final_count}")
        print(f"\n📊 Verify with SQL:")
        print(f"   SELECT COUNT(*) FROM mapping_registry WHERE vendor='{vendor}' AND tenant_id='{tenant_id}';")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == '__main__':
    main()
