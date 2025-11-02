#!/usr/bin/env python3
"""
DoD Primer Script - Runs all seed scripts in sequence
Primes canonical events for all sources and verifies materialization
"""
import os
import sys
import time
import subprocess

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db
from app.models import CanonicalStream
import uuid


def run_seed_script(script_name):
    """Run a seed script and return success status"""
    script_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        script_name
    )
    
    print(f"\n{'=' * 60}")
    print(f"Running {script_name}...")
    print('=' * 60)
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=False,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print(f"✅ {script_name} completed successfully")
            return True
        else:
            print(f"⚠️  {script_name} failed with exit code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ {script_name} timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"❌ {script_name} error: {e}")
        return False


def verify_canonical_streams(source_name):
    """Verify that canonical_streams has data for a given source"""
    from sqlalchemy import text
    db = next(get_db())
    
    try:
        # Use JSON ->> operator with raw SQL (source column is JSON type)
        count = db.query(CanonicalStream).filter(
            text(f"source->>'system' = :source_val")
        ).params(source_val=source_name).count()
        
        print(f"   📊 {source_name}: {count} records in canonical_streams")
        return count > 0
        
    except Exception as e:
        print(f"   ❌ Error querying canonical_streams for {source_name}: {e}")
        return False
    finally:
        db.close()


def main():
    """Prime all sources in sequence"""
    print("=" * 60)
    print("DoD Canonical Event Primer")
    print("Priming all 4 sources...")
    print("=" * 60)
    
    # Seed scripts to run
    sources = [
        ("seed_filesource.py", "filesource"),
        ("seed_supabase.py", "supabase"),
        ("seed_mongo.py", "mongodb"),
        ("seed_salesforce.py", "salesforce")
    ]
    
    results = {}
    
    for script_name, source_name in sources:
        success = run_seed_script(script_name)
        results[source_name] = success
        
        if success:
            # Wait a bit for materialization
            time.sleep(2)
            
            # Verify canonical_streams has data
            has_data = verify_canonical_streams(source_name)
            results[source_name] = has_data
    
    # Final summary
    print("\n" + "=" * 60)
    print("PRIMER SUMMARY")
    print("=" * 60)
    
    for source_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{source_name.upper():15} {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("PRIMER STATUS: PASS")
    else:
        print("PRIMER STATUS: FAIL")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
