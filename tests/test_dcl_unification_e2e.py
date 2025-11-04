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


def test_multi_tenant_isolation():
    """
    Test that contacts are properly isolated by tenant.
    
    1. Create 2 tenants (A and B)
    2. Create sam@acme.com for tenant A
    3. Create sam@acme.com for tenant B
    4. Run unification for both tenants
    5. Assert: 2 separate unified contacts (one per tenant)
    6. Assert: No cross-tenant link sharing
    """
    import uuid
    from passlib.context import CryptContext
    from app.models import CanonicalStream
    from datetime import datetime
    
    db = SessionLocal()
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # Generate UUIDs for test tenants
    tenant_a_id = str(uuid.uuid4())
    tenant_b_id = str(uuid.uuid4())
    
    try:
        print("\n" + "="*80)
        print("DCL MULTI-TENANT ISOLATION TEST")
        print("="*80)
        
        # Step 1: Create 2 tenants with unique names
        print("\n🏢 Step 1: Creating test tenants...")
        tenant_a_name = f"Test Tenant A {uuid.uuid4().hex[:8]}"
        tenant_b_name = f"Test Tenant B {uuid.uuid4().hex[:8]}"
        
        db.execute(text("""
            INSERT INTO tenants (id, name)
            VALUES (:tenant_a_id, :name)
        """), {"tenant_a_id": tenant_a_id, "name": tenant_a_name})
        
        db.execute(text("""
            INSERT INTO tenants (id, name)
            VALUES (:tenant_b_id, :name)
        """), {"tenant_b_id": tenant_b_id, "name": tenant_b_name})
        db.commit()
        print(f"   ✅ Created Tenant A: {tenant_a_id}")
        print(f"   ✅ Created Tenant B: {tenant_b_id}")
        
        # Step 2: Create users for each tenant
        print("\n👤 Step 2: Creating test users...")
        hashed_password = pwd_context.hash("testpass123")
        
        user_a_email = f"user_a_{uuid.uuid4().hex[:8]}@test.com"
        user_b_email = f"user_b_{uuid.uuid4().hex[:8]}@test.com"
        
        db.execute(text("""
            INSERT INTO users (id, email, hashed_password, tenant_id)
            VALUES (gen_random_uuid(), :email, :hashed_password, :tenant_id)
        """), {"email": user_a_email, "hashed_password": hashed_password, "tenant_id": tenant_a_id})
        
        db.execute(text("""
            INSERT INTO users (id, email, hashed_password, tenant_id)
            VALUES (gen_random_uuid(), :email, :hashed_password, :tenant_id)
        """), {"email": user_b_email, "hashed_password": hashed_password, "tenant_id": tenant_b_id})
        db.commit()
        print(f"   ✅ Created user for Tenant A: {user_a_email}")
        print(f"   ✅ Created user for Tenant B: {user_b_email}")
        
        # Step 3: Seed contacts with SAME EMAIL for both tenants
        print("\n📊 Step 3: Seeding contacts with same email for both tenants...")
        
        # Tenant A contact
        contact_a = CanonicalStream(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(tenant_a_id),
            entity="contact",
            data={
                "contact_id": "MULTI-TEST-A-001",
                "email": "sam@acme.com",
                "first_name": "Sam",
                "last_name": "TenantA"
            },
            meta={"version": "1.0", "schema": "canonical_v1"},
            source={"system": "filesource", "connection_id": "test-a"},
            emitted_at=datetime.utcnow()
        )
        db.add(contact_a)
        print(f"   ✅ Created contact for Tenant A: sam@acme.com")
        
        # Tenant B contact (SAME EMAIL, different tenant)
        contact_b = CanonicalStream(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(tenant_b_id),
            entity="contact",
            data={
                "contact_id": "MULTI-TEST-B-001",
                "email": "sam@acme.com",
                "first_name": "Sam",
                "last_name": "TenantB"
            },
            meta={"version": "1.0", "schema": "canonical_v1"},
            source={"system": "filesource", "connection_id": "test-b"},
            emitted_at=datetime.utcnow()
        )
        db.add(contact_b)
        db.commit()
        print(f"   ✅ Created contact for Tenant B: sam@acme.com")
        
        # Step 4: Get tokens for both users
        print("\n🔐 Step 4: Authenticating both users...")
        
        login_a = requests.post(
            "http://localhost:5000/token",
            data={"username": user_a_email, "password": "testpass123"}
        )
        assert login_a.status_code == 200, f"Login failed for Tenant A: {login_a.text}"
        token_a = login_a.json()["access_token"]
        print(f"   ✅ Authenticated Tenant A user")
        
        login_b = requests.post(
            "http://localhost:5000/token",
            data={"username": user_b_email, "password": "testpass123"}
        )
        assert login_b.status_code == 200, f"Login failed for Tenant B: {login_b.text}"
        token_b = login_b.json()["access_token"]
        print(f"   ✅ Authenticated Tenant B user")
        
        # Step 5: Run unification for Tenant A
        print("\n🔄 Step 5: Running unification for Tenant A...")
        response_a = requests.post(
            "http://localhost:5000/api/v1/dcl/unify/run",
            headers={"Authorization": f"Bearer {token_a}"}
        )
        assert response_a.status_code == 200, f"Unification failed for Tenant A: {response_a.text}"
        result_a = response_a.json()
        print(f"   ✅ Tenant A: {result_a['unified_contacts']} unified, {result_a['links']} links")
        
        # Step 6: Run unification for Tenant B
        print("\n🔄 Step 6: Running unification for Tenant B...")
        response_b = requests.post(
            "http://localhost:5000/api/v1/dcl/unify/run",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        assert response_b.status_code == 200, f"Unification failed for Tenant B: {response_b.text}"
        result_b = response_b.json()
        print(f"   ✅ Tenant B: {result_b['unified_contacts']} unified, {result_b['links']} links")
        
        # Step 7: Verify tenant isolation - should have 2 separate unified contacts
        print("\n🔍 Step 7: Verifying tenant isolation...")
        
        unified_result = db.execute(text("""
            SELECT tenant_id, unified_contact_id, email, first_name, last_name
            FROM dcl_unified_contact
            WHERE email = 'sam@acme.com'
            ORDER BY tenant_id
        """))
        unified_contacts = unified_result.fetchall()
        
        print(f"   Found {len(unified_contacts)} unified contact(s) for sam@acme.com")
        assert len(unified_contacts) == 2, f"Expected 2 unified contacts (one per tenant), found {len(unified_contacts)}"
        
        # Verify one contact per tenant
        tenant_ids = [str(c.tenant_id) for c in unified_contacts]
        assert tenant_a_id in tenant_ids, "Missing unified contact for Tenant A"
        assert tenant_b_id in tenant_ids, "Missing unified contact for Tenant B"
        print(f"   ✅ Found separate unified contacts for both tenants")
        
        for contact in unified_contacts:
            print(f"      - Tenant {contact.tenant_id}: {contact.first_name} {contact.last_name} ({contact.email})")
        
        # Step 8: Verify no cross-tenant link sharing
        print("\n🔗 Step 8: Verifying no cross-tenant link sharing...")
        
        # Get links for Tenant A's unified contact
        contact_a_unified = [c for c in unified_contacts if str(c.tenant_id) == tenant_a_id][0]
        links_a = db.execute(text("""
            SELECT tenant_id, source_system, source_contact_id
            FROM dcl_unified_contact_link
            WHERE unified_contact_id = :unified_id
        """), {"unified_id": contact_a_unified.unified_contact_id}).fetchall()
        
        print(f"   Tenant A unified contact has {len(links_a)} link(s):")
        for link in links_a:
            print(f"      - {link.source_system}:{link.source_contact_id} (tenant: {link.tenant_id})")
            assert str(link.tenant_id) == tenant_a_id, "Tenant A link has wrong tenant_id!"
        
        # Get links for Tenant B's unified contact
        contact_b_unified = [c for c in unified_contacts if str(c.tenant_id) == tenant_b_id][0]
        links_b = db.execute(text("""
            SELECT tenant_id, source_system, source_contact_id
            FROM dcl_unified_contact_link
            WHERE unified_contact_id = :unified_id
        """), {"unified_id": contact_b_unified.unified_contact_id}).fetchall()
        
        print(f"   Tenant B unified contact has {len(links_b)} link(s):")
        for link in links_b:
            print(f"      - {link.source_system}:{link.source_contact_id} (tenant: {link.tenant_id})")
            assert str(link.tenant_id) == tenant_b_id, "Tenant B link has wrong tenant_id!"
        
        print(f"   ✅ No cross-tenant link sharing detected")
        
        # Step 9: Verify links point to correct source contacts
        print("\n✅ Step 9: Verifying link correctness...")
        assert any(link.source_contact_id == "MULTI-TEST-A-001" for link in links_a), "Tenant A missing correct link"
        assert any(link.source_contact_id == "MULTI-TEST-B-001" for link in links_b), "Tenant B missing correct link"
        print(f"   ✅ All links point to correct source contacts")
        
        print("\n" + "="*80)
        print("✅ MULTI-TENANT ISOLATION TEST PASSED")
        print("="*80 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Multi-tenant test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        print("\n🧹 Cleaning up multi-tenant test data...")
        try:
            # Delete test links
            db.execute(text("""
                DELETE FROM dcl_unified_contact_link
                WHERE source_contact_id LIKE 'MULTI-TEST-%'
            """))
            
            # Delete test unified contacts
            db.execute(text("""
                DELETE FROM dcl_unified_contact
                WHERE tenant_id IN (:tenant_a_id, :tenant_b_id)
            """), {"tenant_a_id": tenant_a_id, "tenant_b_id": tenant_b_id})
            
            # Delete test canonical streams
            db.execute(text("""
                DELETE FROM canonical_streams
                WHERE data->>'contact_id' LIKE 'MULTI-TEST-%'
            """))
            
            # Delete test users
            db.execute(text("""
                DELETE FROM users
                WHERE tenant_id IN (:tenant_a_id, :tenant_b_id)
            """), {"tenant_a_id": tenant_a_id, "tenant_b_id": tenant_b_id})
            
            # Delete test tenants
            db.execute(text("""
                DELETE FROM tenants
                WHERE id IN (:tenant_a_id, :tenant_b_id)
            """), {"tenant_a_id": tenant_a_id, "tenant_b_id": tenant_b_id})
            
            db.commit()
            print("   ✅ Cleanup complete")
        except Exception as e:
            print(f"   ⚠️  Cleanup error: {e}")
        finally:
            db.close()


if __name__ == "__main__":
    import sys
    
    # Run both tests
    print("\n" + "="*80)
    print("RUNNING DCL UNIFICATION TESTS")
    print("="*80)
    
    test1_passed = test_dcl_unification_e2e()
    test2_passed = test_multi_tenant_isolation()
    
    if test1_passed and test2_passed:
        print("\n" + "="*80)
        print("✅✅ ALL DCL TESTS PASSED ✅✅")
        print("[POW] DCL_UNIFY_E2E_PASS")
        print("="*80 + "\n")
        sys.exit(0)
    else:
        print("\n" + "="*80)
        print("❌ SOME TESTS FAILED")
        print("="*80 + "\n")
        sys.exit(1)
