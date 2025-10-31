"""
Verification script for end-to-end platformization integration
"""
import requests
import sys

def test_intelligence_endpoints():
    """Test intelligence API endpoints"""
    print("\n=== Testing Intelligence Endpoints ===")
    
    endpoints = [
        '/api/v1/aam/intelligence/mappings',
        '/api/v1/aam/intelligence/drift_events_24h',
        '/api/v1/aam/intelligence/rag_queue',
        '/api/v1/aam/intelligence/repair_metrics'
    ]
    
    base_url = 'http://localhost:8000'
    all_passed = True
    
    for endpoint in endpoints:
        try:
            response = requests.get(f'{base_url}{endpoint}', timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {endpoint}: {response.status_code} - Data keys: {list(data.keys())}")
            else:
                print(f"❌ {endpoint}: {response.status_code}")
                all_passed = False
        except Exception as e:
            print(f"❌ {endpoint}: Error - {str(e)}")
            all_passed = False
    
    return all_passed

def test_dcl_views():
    """Test DCL views endpoints"""
    print("\n=== Testing DCL Views Endpoints ===")
    
    endpoints = [
        '/api/v1/dcl/views/opportunities',
        '/api/v1/dcl/views/accounts'
    ]
    
    base_url = 'http://localhost:8000'
    all_passed = True
    
    for endpoint in endpoints:
        try:
            response = requests.get(f'{base_url}{endpoint}', timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {endpoint}: {response.status_code} - Total items: {data.get('total', 0)}")
            else:
                print(f"❌ {endpoint}: {response.status_code}")
                all_passed = False
        except Exception as e:
            print(f"❌ {endpoint}: Error - {str(e)}")
            all_passed = False
    
    return all_passed

def verify_canonical_streams():
    """Verify canonical_streams table has data"""
    print("\n=== Verifying Canonical Streams Data ===")
    
    from app.database import SessionLocal
    from app.models import CanonicalStream
    
    db = SessionLocal()
    try:
        total_records = db.query(CanonicalStream).count()
        opportunities = db.query(CanonicalStream).filter(CanonicalStream.entity == 'opportunity').count()
        accounts = db.query(CanonicalStream).filter(CanonicalStream.entity == 'account').count()
        
        print(f"✅ Total canonical_streams records: {total_records}")
        print(f"  - Opportunities: {opportunities}")
        print(f"  - Accounts: {accounts}")
        
        return total_records > 0
        
    except Exception as e:
        print(f"❌ Error querying canonical_streams: {e}")
        return False
    finally:
        db.close()

def main():
    print("=" * 60)
    print("End-to-End Integration Verification")
    print("=" * 60)
    
    results = {
        'canonical_streams': verify_canonical_streams(),
        'intelligence_endpoints': test_intelligence_endpoints(),
        'dcl_views': test_dcl_views()
    }
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    all_passed = all(results.values())
    
    for component, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {component}")
    
    if all_passed:
        print("\n🎉 All components verified successfully!")
        return 0
    else:
        print("\n⚠️  Some components failed verification")
        return 1

if __name__ == "__main__":
    sys.exit(main())
