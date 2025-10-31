from typing import List, Dict, Any
from app.database import get_db
from sqlalchemy import select
from app.models import CanonicalStream
import logging

logger = logging.getLogger(__name__)

def get_canonical_opportunities(tenant_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Subscribe to canonical_streams table and fetch opportunities
    
    Args:
        tenant_id: Tenant UUID
        limit: Max records to return
        
    Returns:
        List of canonical opportunity records
    """
    db = next(get_db())
    try:
        result = db.execute(
            select(CanonicalStream)
            .where(CanonicalStream.tenant_id == tenant_id)
            .where(CanonicalStream.entity == 'opportunity')
            .order_by(CanonicalStream.emitted_at.desc())
            .limit(limit)
        )
        streams = result.scalars().all()
        
        opportunities = []
        for stream in streams:
            opp = stream.data.copy() if isinstance(stream.data, dict) else {}
            opp['_meta'] = stream.meta
            opp['_source'] = stream.source
            opportunities.append(opp)
        
        logger.info(f"Retrieved {len(opportunities)} canonical opportunities for tenant {tenant_id}")
        return opportunities
        
    except Exception as e:
        logger.error(f"Error fetching canonical opportunities: {e}")
        return []
    finally:
        db.close()


def get_canonical_accounts(tenant_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Subscribe to canonical_streams table and fetch accounts
    
    Args:
        tenant_id: Tenant UUID
        limit: Max records to return
        
    Returns:
        List of canonical account records
    """
    db = next(get_db())
    try:
        result = db.execute(
            select(CanonicalStream)
            .where(CanonicalStream.tenant_id == tenant_id)
            .where(CanonicalStream.entity == 'account')
            .order_by(CanonicalStream.emitted_at.desc())
            .limit(limit)
        )
        streams = result.scalars().all()
        
        accounts = []
        for stream in streams:
            acc = stream.data.copy() if isinstance(stream.data, dict) else {}
            acc['_meta'] = stream.meta
            acc['_source'] = stream.source
            accounts.append(acc)
        
        logger.info(f"Retrieved {len(accounts)} canonical accounts for tenant {tenant_id}")
        return accounts
        
    except Exception as e:
        logger.error(f"Error fetching canonical accounts: {e}")
        return []
    finally:
        db.close()
