#!/usr/bin/env python3
"""
FilesSource drift simulation script

Simulates schema drift by adding a new column to a CSV file,
re-ingesting it, and creating a DRIFT_DETECTED event.

Usage:
    python scripts/filesource_drift_sim.py --connection-id <uuid> --namespace <namespace>
"""

import argparse
import csv
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def modify_csv_add_column(csv_path):
    """Add a new column to CSV header and first data row"""
    # Read existing CSV
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    if len(rows) < 2:
        print(f"⚠️  CSV has <2 rows, skipping: {csv_path}")
        return None
    
    # Add new column to header
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    new_col = f"new_col_{timestamp}"
    rows[0].append(new_col)
    
    # Add sample value to first data row
    rows[1].append("drift_value")
    
    # Write back
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    
    print(f"  ✅ Added column '{new_col}' to {os.path.basename(csv_path)}")
    return new_col


def get_mapping_count(session, connection_id):
    """Get current mapping count for connection"""
    result = session.execute(
        text("SELECT COUNT(*) FROM mapping_registry WHERE connection_id = :conn_id"),
        {"conn_id": connection_id}
    ).scalar()
    return result or 0


def create_drift_event(session, connection_id, namespace, new_field):
    """Insert DRIFT_DETECTED event into drift_events"""
    # Get tenant_id for namespace
    tenant_result = session.execute(
        text("SELECT id FROM tenants WHERE name = :namespace LIMIT 1"),
        {"namespace": namespace}
    ).fetchone()
    
    if not tenant_result:
        print(f"❌ Tenant not found for namespace: {namespace}")
        return None
    
    tenant_id = tenant_result[0]
    event_id = str(uuid4())
    
    session.execute(
        text("""
            INSERT INTO drift_events 
            (id, tenant_id, connection_id, event_type, new_schema, confidence, status, created_at)
            VALUES 
            (:id, :tenant_id, :connection_id, :event_type, :new_schema, :confidence, :status, :created_at)
        """),
        {
            "id": event_id,
            "tenant_id": str(tenant_id),
            "connection_id": connection_id,
            "event_type": "DRIFT_DETECTED",
            "new_schema": f'{{"added_field": "{new_field}"}}',
            "confidence": 1.0,
            "status": "DETECTED",
            "created_at": datetime.utcnow()
        }
    )
    session.commit()
    
    print(f"  ✅ Created DRIFT_DETECTED event: {event_id}")
    return event_id


def main():
    parser = argparse.ArgumentParser(description='Simulate FilesSource schema drift')
    parser.add_argument('--connection-id', default='10ca3a88-5105-4e24-b984-6e350a5fa443',
                        help='Connection UUID (default: FilesSource Demo)')
    parser.add_argument('--namespace', default='demo',
                        help='Namespace for tenant isolation (default: demo)')
    parser.add_argument('--directory', default='mock_sources',
                        help='Directory containing CSV files (default: mock_sources)')
    
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
        print(f"🔄 FilesSource Drift Simulation")
        print(f"   Connection: {args.connection_id}")
        print(f"   Namespace: {args.namespace}")
        
        # Get pre-drift mapping count
        old_count = get_mapping_count(session, args.connection_id)
        print(f"\n📊 Pre-drift mapping_count: {old_count}")
        
        # Find first filesource CSV
        csv_path = os.path.join(args.directory, 'aws_resources_filesource.csv')
        if not os.path.exists(csv_path):
            print(f"❌ CSV not found: {csv_path}")
            sys.exit(1)
        
        # Modify CSV (add column)
        print(f"\n📝 Modifying CSV...")
        new_field = modify_csv_add_column(csv_path)
        if not new_field:
            sys.exit(1)
        
        # Run ingest script
        print(f"\n📥 Running ingest...")
        ingest_script = os.path.join(Path(__file__).parent, 'filesource_ingest.py')
        result = subprocess.run([
            sys.executable, ingest_script,
            '--connection-id', args.connection_id,
            '--namespace', args.namespace,
            '--directory', args.directory
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Ingest failed:\n{result.stderr}")
            sys.exit(1)
        
        print(result.stdout)
        
        # Get post-drift mapping count
        new_count = get_mapping_count(session, args.connection_id)
        print(f"📊 Post-drift mapping_count: {new_count}")
        
        # Create drift event
        print(f"\n📡 Creating DRIFT_DETECTED event...")
        event_id = create_drift_event(session, args.connection_id, args.namespace, new_field)
        
        # Summary
        print(f"\n✅ Drift simulation complete!")
        print(f"   Old mapping_count: {old_count}")
        print(f"   New mapping_count: {new_count}")
        print(f"   Drift delta: +{new_count - old_count}")
        print(f"   Event ID: {event_id}")
        
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
