#!/usr/bin/env python3
"""
FileSource Canonical Event Primer
Reads CSV files from services/aam/connectors/filesource/mock_sources/ and emits canonical events
"""
import os
import sys
import csv
import time
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session
from app.database import get_db
from app.models import CanonicalStream

DEMO_TENANT_UUID = "9ac5c8c6-1a02-48ff-84a0-122b67f9c3bd"


def read_csv(filepath):
    """Read CSV file and return list of dicts"""
    data = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(dict(row))
    return data


def seed_filesource():
    """Seed canonical events from FileSource CSV files"""
    db = next(get_db())
    
    try:
        print("=" * 60)
        print("FileSource Canonical Event Primer")
        print("=" * 60)
        
        # Look for CSV files in services/aam/connectors/filesource/mock_sources/
        sources_dir = Path("services/aam/connectors/filesource/mock_sources")
        
        if not sources_dir.exists():
            print(f"❌ Sources directory not found: {sources_dir}")
            return False
        
        total_emitted = 0
        
        # Process accounts.csv
        accounts_file = sources_dir / "accounts.csv"
        if accounts_file.exists():
            print(f"\n📄 Processing: accounts.csv")
            accounts_data = read_csv(str(accounts_file))
            print(f"   Rows found: {len(accounts_data)}")
            
            rows_to_process = accounts_data[:25]
            for row in rows_to_process:
                try:
                    canonical_data = {
                        "account_id": row.get("account_id"),
                        "name": row.get("name"),
                        "type": row.get("type"),
                        "industry": row.get("industry"),
                        "owner_id": row.get("owner_id"),
                        "status": row.get("status")
                    }
                    
                    stream_record = CanonicalStream(
                        id=uuid.uuid4(),
                        tenant_id=uuid.UUID(DEMO_TENANT_UUID),
                        entity="account",
                        data=canonical_data,
                        meta={"version": "1.0", "schema": "canonical_v1"},
                        source={"system": "filesource", "connector": "csv"},
                        emitted_at=datetime.utcnow()
                    )
                    
                    db.add(stream_record)
                    total_emitted += 1
                    
                except Exception as e:
                    print(f"   ⚠️  Error processing row: {e}")
                    continue
            
            db.commit()
            print(f"   ✅ Emitted {min(len(rows_to_process), 25)} account events")
        
        # Process opportunities.csv
        opps_file = sources_dir / "opportunities.csv"
        if opps_file.exists():
            print(f"\n📄 Processing: opportunities.csv")
            opps_data = read_csv(str(opps_file))
            print(f"   Rows found: {len(opps_data)}")
            
            rows_to_process = opps_data[:25]
            for row in rows_to_process:
                try:
                    canonical_data = {
                        "opportunity_id": row.get("opportunity_id"),
                        "account_id": row.get("account_id"),
                        "name": row.get("name"),
                        "stage": row.get("stage"),
                        "amount": row.get("amount"),
                        "currency": row.get("currency", "USD"),
                        "close_date": row.get("close_date"),
                        "owner_id": row.get("owner_id"),
                        "probability": row.get("probability")
                    }
                    
                    stream_record = CanonicalStream(
                        id=uuid.uuid4(),
                        tenant_id=uuid.UUID(DEMO_TENANT_UUID),
                        entity="opportunity",
                        data=canonical_data,
                        meta={"version": "1.0", "schema": "canonical_v1"},
                        source={"system": "filesource", "connector": "csv"},
                        emitted_at=datetime.utcnow()
                    )
                    
                    db.add(stream_record)
                    total_emitted += 1
                    
                except Exception as e:
                    print(f"   ⚠️  Error processing row: {e}")
                    continue
            
            db.commit()
            print(f"   ✅ Emitted {min(len(rows_to_process), 25)} opportunity events")
        
        print(f"\n📊 Total canonical events emitted: {total_emitted}")
        
        # Wait for materialization
        print("\n⏳ Waiting for DCL materialization (3 seconds)...")
        time.sleep(3)
        
        # Verify canonical_streams records
        from sqlalchemy import func, cast, String
        stream_count = db.query(CanonicalStream).filter(
            CanonicalStream.tenant_id == uuid.UUID(DEMO_TENANT_UUID),
            func.cast(CanonicalStream.source['system'], String) == 'filesource'
        ).count()
        
        print(f"✅ Verified {stream_count} records in canonical_streams")
        
        print("\n" + "=" * 60)
        print("FileSource Primer: SUCCESS")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = seed_filesource()
    sys.exit(0 if success else 1)
