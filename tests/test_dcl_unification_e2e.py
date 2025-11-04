"""
DCL Contact Unification E2E Test
Tests the complete contact unification workflow
"""
import os
import sys
sys.path.insert(0, os.getcwd())

from sqlalchemy import text
from app.database import SessionLocal
from scripts.seed_demo_contacts import seed_demo_contacts
import requests


def test_dcl_unification_e2e():
    """
    E2E test for DCL contact unification:
    1. Seed 2 demo contacts with same email (sam@acme.com)
    2. Trigger POST /api/v1/dcl/unify/run
    3. Assert exactly 1 unified contact
    4. Assert exactly 2 links
    5. Cleanup in finally block
    """
    db = SessionLocal()
    
    try:
        print("\n" + "="*80)
        print("DCL CONTACT UNIFICATION E2E TEST")
        print("="*80)
        
        # Step 1: Seed demo contacts
        print("\n📊 Step 1: Seeding demo contacts...")
        seed_success = seed_demo_contacts()
        assert seed_success, "Failed to seed demo contacts"
        print("   ✅ Demo contacts seeded")
        
        # Step 2: Get authentication token
        print("\n🔐 Step 2: Getting authentication token...")
        # Ensure demo tenant exists
        result = db.execute(text("""
            INSERT INTO tenants (id, name)
            VALUES ('9ac5c8c6-1a02-48ff-84a0-122b67f9c3bd', 'Demo Tenant')
            ON CONFLICT (id) DO NOTHING
        """))
        db.commit()
        
        # Create demo user with known password
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password = pwd_context.hash("testpass123")
        
        demo_email = 'dcltest@test.com'
        db.execute(text("""
            INSERT INTO users (id, email, hashed_password, tenant_id)
            VALUES (
                gen_random_uuid(),
                :email,
                :hashed_password,
                '9ac5c8c6-1a02-48ff-84a0-122b67f9c3bd'
            )
            ON CONFLICT (email) DO UPDATE SET hashed_password = :hashed_password
        """), {"email": demo_email, "hashed_password": hashed_password})
        db.commit()
        print(f"   ✅ Created/updated test user: {demo_email}")
        
        # Login to get token
        login_response = requests.post(
            "http://localhost:5000/token",
            data={"username": demo_email, "password": "testpass123"}
        )
        
        if login_response.status_code != 200:
            print(f"   ❌ Login failed: {login_response.status_code}")
            print(f"   Response: {login_response.text}")
            raise Exception("Failed to authenticate test user")
        
        token = login_response.json()["access_token"]
        print(f"   ✅ Authenticated as {demo_email}")
        
        # Step 3: Trigger unification endpoint
        print("\n🔄 Step 3: Triggering unification endpoint...")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        
        response = requests.post(
            "http://localhost:5000/api/v1/dcl/unify/run",
            headers=headers
        )
        
        print(f"   Response status: {response.status_code}")
        print(f"   Response body: {response.json()}")
        
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
        result_data = response.json()
        assert result_data["status"] == "ok", f"Unification failed: {result_data}"
        
        print(f"   ✅ Unified {result_data['unified_contacts']} contacts")
        print(f"   ✅ Created {result_data['links']} links")
        
        # Step 4: Verify unified contact
        print("\n🔍 Step 4: Verifying unified contact...")
        unified_result = db.execute(text("""
            SELECT unified_contact_id, email, first_name, last_name
            FROM dcl_unified_contact
            WHERE email = 'sam@acme.com'
        """))
        unified_contacts = unified_result.fetchall()
        
        print(f"   Found {len(unified_contacts)} unified contact(s) for sam@acme.com")
        assert len(unified_contacts) == 1, f"Expected exactly 1 unified contact, found {len(unified_contacts)}"
        
        unified_contact = unified_contacts[0]
        unified_id = unified_contact.unified_contact_id
        print(f"   ✅ Unified contact ID: {unified_id}")
        print(f"      Email: {unified_contact.email}")
        print(f"      Name: {unified_contact.first_name} {unified_contact.last_name}")
        
        # Step 5: Verify links
        print("\n🔗 Step 5: Verifying links...")
        links_result = db.execute(text("""
            SELECT source_system, source_contact_id
            FROM dcl_unified_contact_link
            WHERE unified_contact_id = :unified_id
            ORDER BY source_system
        """), {"unified_id": unified_id})
        links = links_result.fetchall()
        
        print(f"   Found {len(links)} link(s) for unified contact {unified_id}")
        assert len(links) == 2, f"Expected exactly 2 links, found {len(links)}"
        
        for link in links:
            print(f"   ✅ Link: {link.source_system} -> {link.source_contact_id}")
        
        # Verify expected links exist
        link_pairs = [(link.source_system, link.source_contact_id) for link in links]
        expected_links = [
            ("filesource-salesforce", "DEMO-SF-001"),
            ("filesource-crm", "DEMO-CRM-001")
        ]
        
        for expected in expected_links:
            assert expected in link_pairs, f"Expected link not found: {expected}"
            print(f"   ✅ Verified: {expected[0]} -> {expected[1]}")
        
        # Step 6: Test idempotency
        print("\n🔁 Step 6: Testing idempotency (running unification again)...")
        response2 = requests.post(
            "http://localhost:5000/api/v1/dcl/unify/run",
            headers=headers
        )
        
        assert response2.status_code == 200, "Second run failed"
        result_data2 = response2.json()
        print(f"   Response: {result_data2}")
        
        # Should create 0 new contacts and 0 new links
        assert result_data2["unified_contacts"] == 0, "Should not create new contacts on second run"
        assert result_data2["links"] == 0, "Should not create new links on second run"
        print("   ✅ Idempotency verified: no duplicates created")
        
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED")
        print("[POW] DCL_UNIFY_E2E_PASS")
        print("="*80 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        print("\n🧹 Cleaning up test data...")
        try:
            # Delete demo links
            db.execute(text("""
                DELETE FROM dcl_unified_contact_link
                WHERE source_contact_id LIKE 'DEMO-%'
            """))
            
            # Delete demo unified contacts
            db.execute(text("""
                DELETE FROM dcl_unified_contact
                WHERE email = 'sam@acme.com'
            """))
            
            # Delete demo canonical streams
            db.execute(text("""
                DELETE FROM canonical_streams
                WHERE entity = 'contact'
                AND data->>'contact_id' LIKE 'DEMO-%'
            """))
            
            db.commit()
            print("   ✅ Cleanup complete")
        except Exception as e:
            print(f"   ⚠️  Cleanup error: {e}")
        finally:
            db.close()


if __name__ == "__main__":
    import sys
    success = test_dcl_unification_e2e()
    sys.exit(0 if success else 1)
