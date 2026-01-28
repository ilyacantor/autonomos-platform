#!/usr/bin/env python3
"""
Salesforce Canonical Event Primer
Fetches live data from Salesforce and emits canonical events
"""
import os
import sys
import time
import uuid
import asyncio
import httpx
from datetime import datetime

from sqlalchemy.orm import Session
from app.database import get_db
from app.models import CanonicalStream

DEMO_TENANT_UUID = "9ac5c8c6-1a02-48ff-84a0-122b67f9c3bd"


async def fetch_salesforce_opportunities(access_token, instance_url):
    """Fetch 5 most recent opportunities from Salesforce"""
    if not access_token or not instance_url:
        print("❌ SALESFORCE credentials not configured")
        return []
    
    api_version = "v59.0"
    
    # SOQL query to fetch 5 most recent opportunities with Account data
    # Note: CurrencyIsoCode removed (requires multi-currency feature)
    soql = (
        "SELECT Id, AccountId, Account.Name, Name, StageName, Amount, "
        "CloseDate, OwnerId, Probability, LastModifiedDate "
        "FROM Opportunity "
        "ORDER BY LastModifiedDate DESC "
        "LIMIT 5"
    )
    
    url = f"{instance_url}/services/data/{api_version}/query/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    params = {"q": soql}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params, timeout=30.0)
            response.raise_for_status()
            
            data = response.json()
            records = data.get("records", [])
            
            print(f"📊 Fetched {len(records)} opportunities from Salesforce")
            return records
            
    except httpx.HTTPStatusError as e:
        print(f"❌ Salesforce API error: {e.response.status_code} - {e.response.text}")
        return []
    except Exception as e:
        print(f"❌ Failed to fetch Salesforce opportunities: {e}")
        return []


def normalize_opportunity(sf_opportunity):
    """Normalize Salesforce Opportunity to simple canonical format"""
    return {
        "opportunity_id": sf_opportunity.get("Id"),
        "account_id": sf_opportunity.get("AccountId"),
        "name": sf_opportunity.get("Name"),
        "stage": sf_opportunity.get("StageName"),
        "amount": str(sf_opportunity.get("Amount", "")),
        "currency": sf_opportunity.get("CurrencyIsoCode", "USD"),
        "close_date": str(sf_opportunity.get("CloseDate", "")),
        "owner_id": sf_opportunity.get("OwnerId"),
        "probability": str(sf_opportunity.get("Probability", ""))
    }


async def seed_salesforce_async():
    """Async version of seed_salesforce"""
    from services.aam.connectors.salesforce.oauth_refresh import get_access_token_and_instance
    
    db = next(get_db())
    
    try:
        print("=" * 60)
        print("Salesforce Canonical Event Primer")
        print("=" * 60)
        
        # Get access token - try OAuth refresh first, fall back to direct token
        client_id = os.getenv("SALESFORCE_CLIENT_ID")
        client_secret = os.getenv("SALESFORCE_CLIENT_SECRET")
        refresh_token = os.getenv("SALESFORCE_REFRESH_TOKEN")
        direct_token = os.getenv("SALESFORCE_ACCESS_TOKEN")
        direct_instance_url = os.getenv("SALESFORCE_INSTANCE_URL")
        
        # Get access token and instance URL using OAuth refresh or direct token
        access_token, instance_url = get_access_token_and_instance(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            direct_access_token=direct_token,
            direct_instance_url=direct_instance_url
        )
        
        if not access_token or not instance_url:
            print("⚠️  SALESFORCE credentials not configured")
            print("    Set either SALESFORCE_ACCESS_TOKEN or")
            print("    SALESFORCE_CLIENT_ID + SALESFORCE_CLIENT_SECRET + SALESFORCE_REFRESH_TOKEN")
            return False
        
        print("✅ Salesforce credentials configured (OAuth refresh enabled)" if refresh_token else "✅ Salesforce credentials configured (direct token)")
        print(f"✅ Instance URL: {instance_url}")
        
        # Fetch opportunities from Salesforce
        print("\n📤 Fetching opportunities from Salesforce...")
        opportunities = await fetch_salesforce_opportunities(access_token, instance_url)
        
        if not opportunities:
            print("⚠️  No opportunities fetched from Salesforce")
            return False
        
        # Emit canonical events
        print(f"\n📤 Emitting {len(opportunities)} canonical events...")
        
        total_emitted = 0
        
        for opp in opportunities:
            try:
                canonical_data = normalize_opportunity(opp)
                
                stream_record = CanonicalStream(
                    id=uuid.uuid4(),
                    tenant_id=uuid.UUID(DEMO_TENANT_UUID),
                    entity="opportunity",
                    data=canonical_data,
                    meta={"version": "1.0", "schema": "canonical_v1"},
                    source={"system": "salesforce", "connector": "rest_api"},
                    emitted_at=datetime.utcnow()
                )
                
                db.add(stream_record)
                total_emitted += 1
                print(f"   ✅ Emitted: {opp['Name']}")
                
            except Exception as e:
                print(f"   ⚠️  Error processing opportunity: {e}")
                continue
        
        db.commit()
        print(f"\n📊 Total canonical events emitted: {total_emitted}")
        
        # Wait for materialization
        print("\n⏳ Waiting for DCL materialization (3 seconds)...")
        time.sleep(3)
        
        # Verify canonical_streams records
        from sqlalchemy import func, cast, String
        stream_count = db.query(CanonicalStream).filter(
            CanonicalStream.tenant_id == uuid.UUID(DEMO_TENANT_UUID),
            func.cast(CanonicalStream.source['system'], String) == 'salesforce'
        ).count()
        
        print(f"✅ Verified {stream_count} records in canonical_streams")
        
        print("\n" + "=" * 60)
        print("Salesforce Primer: SUCCESS")
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


def seed_salesforce():
    """Seed canonical events from Salesforce"""
    return asyncio.run(seed_salesforce_async())


if __name__ == "__main__":
    success = seed_salesforce()
    sys.exit(0 if success else 1)
