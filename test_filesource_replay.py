"""
Test script to populate canonical_streams table using FileSource replay
"""
import sys
import uuid
from app.database import SessionLocal
from app.models import Tenant
from services.aam.connectors.filesource.connector import FileSourceConnector

def get_or_create_default_tenant(db):
    """Get or create a default tenant for testing"""
    tenant = db.query(Tenant).filter(Tenant.name == "default-tenant").first()
    
    if not tenant:
        print("Creating default tenant...")
        tenant = Tenant(
            id=uuid.uuid4(),
            name="default-tenant"
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
        print(f"Created tenant with ID: {tenant.id}")
    else:
        print(f"Using existing tenant with ID: {tenant.id}")
    
    return str(tenant.id)

def test_filesource_replay():
    """Test FileSource replay to populate canonical_streams"""
    db = SessionLocal()
    
    try:
        print("Starting FileSource replay test...")
        
        tenant_id = get_or_create_default_tenant(db)
        
        connector = FileSourceConnector(db, tenant_id=tenant_id)
        
        print("\nReplaying all CSV files...")
        results = connector.replay_all()
        
        print("\n=== Replay Results ===")
        print(f"Accounts loaded: {results.get('accounts', 0)}")
        print(f"Opportunities loaded: {results.get('opportunities', 0)}")
        print(f"Total records: {sum(results.values())}")
        
        print("\n✅ FileSource replay completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error during replay: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    success = test_filesource_replay()
    sys.exit(0 if success else 1)
