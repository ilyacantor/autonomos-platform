#!/usr/bin/env python3
"""
Provision a demo tenant with UUID-based tenant_id for DoD verification testing.

Creates:
- Demo tenant with UUID
- Demo user with credentials
- Seeded canonical opportunity data
- Reusable JWT token for testing
"""
import os
import sys
import uuid
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import engine, get_db
from app import models
from app.security import get_password_hash, create_access_token

# Demo credentials
DEMO_TENANT_UUID = "9ac5c8c6-1a02-48ff-84a0-122b67f9c3bd"
DEMO_TENANT_NAME = "demo-corp"
DEMO_USER_EMAIL = "demo@autonomos.dev"
DEMO_USER_PASSWORD = "demo-password-2024"

def provision_demo_tenant():
    """Provision demo tenant, user, and seed data"""
    db = next(get_db())
    
    try:
        # 1. Check if demo tenant already exists (by UUID or by name)
        existing_tenant = db.query(models.Tenant).filter(
            (models.Tenant.id == uuid.UUID(DEMO_TENANT_UUID)) | 
            (models.Tenant.name == DEMO_TENANT_NAME)
        ).first()
        
        if existing_tenant:
            print(f"✅ Demo tenant already exists: {existing_tenant.id}")
            # Update to correct UUID if needed
            if str(existing_tenant.id) != DEMO_TENANT_UUID:
                print(f"⚠️  Updating tenant UUID from {existing_tenant.id} to {DEMO_TENANT_UUID}")
                # Delete old and create new with correct UUID
                db.delete(existing_tenant)
                tenant = models.Tenant(
                    id=uuid.UUID(DEMO_TENANT_UUID),
                    name=DEMO_TENANT_NAME
                )
                db.add(tenant)
                db.commit()
                db.refresh(tenant)
                print(f"✅ Created demo tenant with correct UUID: {tenant.id}")
            else:
                tenant = existing_tenant
        else:
            # Create new demo tenant with specific UUID
            tenant = models.Tenant(
                id=uuid.UUID(DEMO_TENANT_UUID),
                name=DEMO_TENANT_NAME
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            print(f"✅ Created demo tenant: {tenant.id}")
        
        # 2. Check if demo user already exists
        existing_user = db.query(models.User).filter(
            models.User.email == DEMO_USER_EMAIL
        ).first()
        
        if existing_user:
            print(f"✅ Demo user already exists: {existing_user.id}")
            user = existing_user
        else:
            # Create new demo user
            user = models.User(
                id=uuid.uuid4(),
                email=DEMO_USER_EMAIL,
                hashed_password=get_password_hash(DEMO_USER_PASSWORD),
                tenant_id=tenant.id
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✅ Created demo user: {user.id}")
        
        # 3. Seed canonical opportunity data for this tenant
        existing_opps = db.query(models.CanonicalStream).filter(
            models.CanonicalStream.tenant_id == tenant.id,
            models.CanonicalStream.entity == "opportunity"
        ).count()
        
        if existing_opps > 0:
            print(f"✅ Canonical opportunities already seeded: {existing_opps} records")
        else:
            # Seed opportunity data
            opportunities = [
                {
                    "opportunity_id": "OPP001",
                    "account_id": "ACC001",
                    "name": "Enterprise License Renewal",
                    "stage": "Closed Won",
                    "amount": "125000",
                    "currency": "USD",
                    "close_date": "2024-11-15",
                    "owner_id": "USR001",
                    "probability": "1.00"
                },
                {
                    "opportunity_id": "OPP002",
                    "account_id": "ACC002",
                    "name": "New Customer Onboarding",
                    "stage": "Proposal",
                    "amount": "45000",
                    "currency": "USD",
                    "close_date": "2024-12-01",
                    "owner_id": "USR002",
                    "probability": "0.65"
                },
                {
                    "opportunity_id": "OPP003",
                    "account_id": "ACC003",
                    "name": "Platform Migration",
                    "stage": "Negotiation",
                    "amount": "89000",
                    "currency": "USD",
                    "close_date": "2024-11-30",
                    "owner_id": "USR001",
                    "probability": "0.80"
                }
            ]
            
            for opp_data in opportunities:
                canonical_opp = models.CanonicalStream(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    entity="opportunity",
                    data=opp_data,
                    meta={"version": "1.0", "schema": "canonical_v1"},
                    source={"system": "filesource", "connector": "demo"},
                    emitted_at=datetime.utcnow()
                )
                db.add(canonical_opp)
            
            db.commit()
            print(f"✅ Seeded {len(opportunities)} canonical opportunities")
        
        # 4. Generate JWT token for testing (long expiry for development)
        token_data = {
            "user_id": str(user.id),
            "tenant_id": str(tenant.id),
            "email": user.email
        }
        
        # Create token with 7 day expiry for testing
        access_token = create_access_token(
            data=token_data,
            expires_delta=timedelta(days=7)
        )
        
        print("\n" + "="*70)
        print("DEMO TENANT PROVISIONED SUCCESSFULLY")
        print("="*70)
        print(f"Tenant ID:  {tenant.id}")
        print(f"Tenant Name: {tenant.name}")
        print(f"User Email:  {user.email}")
        print(f"User Password: {DEMO_USER_PASSWORD}")
        print(f"\nJWT Token (valid for 7 days):")
        print(f"{access_token}")
        print("="*70)
        print("\nUsage:")
        print(f'  export DEMO_JWT="{access_token}"')
        print('  curl -H "Authorization: Bearer $DEMO_JWT" \\')
        print('    http://localhost:5000/api/v1/dcl/views/opportunities')
        print("="*70)
        
        # Write token to file for easy access
        token_file = os.path.join(os.path.dirname(__file__), ".demo_token")
        with open(token_file, "w") as f:
            f.write(access_token)
        print(f"\n💾 Token saved to: {token_file}")
        
        return {
            "tenant_id": str(tenant.id),
            "user_id": str(user.id),
            "access_token": access_token
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error provisioning demo tenant: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    provision_demo_tenant()
