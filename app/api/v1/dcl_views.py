"""
DCL View Endpoints
Provides read access to materialized canonical data
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.models import MaterializedAccount, MaterializedOpportunity, MaterializedContact
from services.aam.canonical.subscriber import process_canonical_streams

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/accounts")
async def get_accounts(
    tenant_id: str = Query("demo-tenant", description="Tenant identifier"),
    limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    db: Session = Depends(get_db)
):
    """
    Get materialized accounts
    
    Returns paginated list of canonical accounts from materialized table
    """
    try:
        # Process any pending canonical streams first
        try:
            process_canonical_streams(db, tenant_id, limit=1000)
        except Exception as e:
            logger.warning(f"Failed to process canonical streams: {e}")
        
        # Query materialized accounts
        query = db.query(MaterializedAccount).filter(
            MaterializedAccount.tenant_id == tenant_id
        ).order_by(desc(MaterializedAccount.synced_at))
        
        total = query.count()
        accounts = query.offset(offset).limit(limit).all()
        
        # Convert to dict
        results = []
        for account in accounts:
            results.append({
                'account_id': account.account_id,
                'name': account.name,
                'type': account.type,
                'industry': account.industry,
                'owner_id': account.owner_id,
                'status': account.status,
                'external_ids': account.external_ids,
                'extras': account.extras,
                'source_system': account.source_system,
                'source_connection_id': account.source_connection_id,
                'created_at': account.created_at.isoformat() if account.created_at else None,
                'updated_at': account.updated_at.isoformat() if account.updated_at else None,
                'synced_at': account.synced_at.isoformat() if account.synced_at else None
            })
        
        return {
            'success': True,
            'data': results,
            'meta': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'count': len(results)
            }
        }
    
    except Exception as e:
        logger.error(f"Error fetching accounts: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'data': [],
            'meta': {'total': 0, 'limit': limit, 'offset': offset, 'count': 0}
        }


@router.get("/opportunities")
async def get_opportunities(
    tenant_id: str = Query("demo-tenant", description="Tenant identifier"),
    limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    db: Session = Depends(get_db)
):
    """
    Get materialized opportunities
    
    Returns paginated list of canonical opportunities from materialized table
    """
    try:
        # Process any pending canonical streams first
        try:
            process_canonical_streams(db, tenant_id, limit=1000)
        except Exception as e:
            logger.warning(f"Failed to process canonical streams: {e}")
        
        # Query materialized opportunities
        query = db.query(MaterializedOpportunity).filter(
            MaterializedOpportunity.tenant_id == tenant_id
        ).order_by(desc(MaterializedOpportunity.synced_at))
        
        total = query.count()
        opportunities = query.offset(offset).limit(limit).all()
        
        # Convert to dict
        results = []
        for opp in opportunities:
            results.append({
                'opportunity_id': opp.opportunity_id,
                'account_id': opp.account_id,
                'name': opp.name,
                'stage': opp.stage,
                'amount': float(opp.amount) if opp.amount else None,
                'currency': opp.currency,
                'close_date': opp.close_date.isoformat() if opp.close_date else None,
                'owner_id': opp.owner_id,
                'probability': float(opp.probability) if opp.probability is not None else None,
                'extras': opp.extras,
                'source_system': opp.source_system,
                'source_connection_id': opp.source_connection_id,
                'created_at': opp.created_at.isoformat() if opp.created_at else None,
                'updated_at': opp.updated_at.isoformat() if opp.updated_at else None,
                'synced_at': opp.synced_at.isoformat() if opp.synced_at else None
            })
        
        return {
            'success': True,
            'data': results,
            'meta': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'count': len(results)
            }
        }
    
    except Exception as e:
        logger.error(f"Error fetching opportunities: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'data': [],
            'meta': {'total': 0, 'limit': limit, 'offset': offset, 'count': 0}
        }


@router.get("/contacts")
async def get_contacts(
    tenant_id: str = Query("demo-tenant", description="Tenant identifier"),
    limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    db: Session = Depends(get_db)
):
    """
    Get materialized contacts
    
    Returns paginated list of canonical contacts from materialized table
    """
    try:
        # Process any pending canonical streams first
        try:
            process_canonical_streams(db, tenant_id, limit=1000)
        except Exception as e:
            logger.warning(f"Failed to process canonical streams: {e}")
        
        # Query materialized contacts
        query = db.query(MaterializedContact).filter(
            MaterializedContact.tenant_id == tenant_id
        ).order_by(desc(MaterializedContact.synced_at))
        
        total = query.count()
        contacts = query.offset(offset).limit(limit).all()
        
        # Convert to dict
        results = []
        for contact in contacts:
            results.append({
                'contact_id': contact.contact_id,
                'account_id': contact.account_id,
                'first_name': contact.first_name,
                'last_name': contact.last_name,
                'name': contact.name,
                'email': contact.email,
                'phone': contact.phone,
                'title': contact.title,
                'department': contact.department,
                'role': contact.role,
                'extras': contact.extras,
                'source_system': contact.source_system,
                'source_connection_id': contact.source_connection_id,
                'created_at': contact.created_at.isoformat() if contact.created_at else None,
                'updated_at': contact.updated_at.isoformat() if contact.updated_at else None,
                'synced_at': contact.synced_at.isoformat() if contact.synced_at else None
            })
        
        return {
            'success': True,
            'data': results,
            'meta': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'count': len(results)
            }
        }
    
    except Exception as e:
        logger.error(f"Error fetching contacts: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'data': [],
            'meta': {'total': 0, 'limit': limit, 'offset': offset, 'count': 0}
        }
