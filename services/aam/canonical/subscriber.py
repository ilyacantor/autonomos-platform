from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    CanonicalStream, 
    MaterializedAccount, 
    MaterializedOpportunity, 
    MaterializedContact
)
import logging

logger = logging.getLogger(__name__)


def upsert_account(db: Session, tenant_id: str, canonical_data: Dict[str, Any], source_meta: Dict[str, Any]) -> MaterializedAccount:
    """Upsert account into materialized_accounts table"""
    account_id = canonical_data.get('account_id')
    if not account_id:
        raise ValueError("account_id is required")
    
    existing = db.query(MaterializedAccount).filter(
        and_(
            MaterializedAccount.tenant_id == tenant_id,
            MaterializedAccount.account_id == account_id,
            MaterializedAccount.source_system == source_meta.get('system')
        )
    ).first()
    
    if existing:
        existing.name = canonical_data.get('name', existing.name)
        existing.type = canonical_data.get('type', existing.type)
        existing.industry = canonical_data.get('industry', existing.industry)
        existing.owner_id = canonical_data.get('owner_id', existing.owner_id)
        existing.status = canonical_data.get('status', existing.status)
        existing.external_ids = canonical_data.get('external_ids', existing.external_ids)
        existing.extras = canonical_data.get('extras', existing.extras)
        existing.updated_at = canonical_data.get('updated_at', datetime.utcnow())
        existing.synced_at = datetime.utcnow()
        db.commit()
        return existing
    else:
        new_account = MaterializedAccount(
            tenant_id=tenant_id,
            account_id=account_id,
            name=canonical_data.get('name'),
            type=canonical_data.get('type'),
            industry=canonical_data.get('industry'),
            owner_id=canonical_data.get('owner_id'),
            status=canonical_data.get('status'),
            external_ids=canonical_data.get('external_ids', []),
            extras=canonical_data.get('extras', {}),
            source_system=source_meta.get('system'),
            source_connection_id=source_meta.get('connection_id'),
            created_at=canonical_data.get('created_at', datetime.utcnow()),
            updated_at=canonical_data.get('updated_at', datetime.utcnow()),
            synced_at=datetime.utcnow()
        )
        db.add(new_account)
        db.commit()
        return new_account


def upsert_opportunity(db: Session, tenant_id: str, canonical_data: Dict[str, Any], source_meta: Dict[str, Any]) -> MaterializedOpportunity:
    """Upsert opportunity into materialized_opportunities table"""
    opportunity_id = canonical_data.get('opportunity_id')
    if not opportunity_id:
        raise ValueError("opportunity_id is required")
    
    existing = db.query(MaterializedOpportunity).filter(
        and_(
            MaterializedOpportunity.tenant_id == tenant_id,
            MaterializedOpportunity.opportunity_id == opportunity_id,
            MaterializedOpportunity.source_system == source_meta.get('system')
        )
    ).first()
    
    if existing:
        existing.account_id = canonical_data.get('account_id', existing.account_id)
        existing.name = canonical_data.get('name', existing.name)
        existing.stage = canonical_data.get('stage', existing.stage)
        existing.amount = float(canonical_data['amount']) if canonical_data.get('amount') else existing.amount
        existing.currency = canonical_data.get('currency', existing.currency)
        existing.close_date = canonical_data.get('close_date', existing.close_date)
        existing.owner_id = canonical_data.get('owner_id', existing.owner_id)
        existing.probability = float(canonical_data['probability']) if canonical_data.get('probability') is not None else existing.probability
        existing.extras = canonical_data.get('extras', existing.extras)
        existing.updated_at = canonical_data.get('updated_at', datetime.utcnow())
        existing.synced_at = datetime.utcnow()
        db.commit()
        return existing
    else:
        new_opp = MaterializedOpportunity(
            tenant_id=tenant_id,
            opportunity_id=opportunity_id,
            account_id=canonical_data.get('account_id'),
            name=canonical_data.get('name'),
            stage=canonical_data.get('stage'),
            amount=float(canonical_data['amount']) if canonical_data.get('amount') else None,
            currency=canonical_data.get('currency', 'USD'),
            close_date=canonical_data.get('close_date'),
            owner_id=canonical_data.get('owner_id'),
            probability=float(canonical_data['probability']) if canonical_data.get('probability') is not None else None,
            extras=canonical_data.get('extras', {}),
            source_system=source_meta.get('system'),
            source_connection_id=source_meta.get('connection_id'),
            created_at=canonical_data.get('created_at', datetime.utcnow()),
            updated_at=canonical_data.get('updated_at', datetime.utcnow()),
            synced_at=datetime.utcnow()
        )
        db.add(new_opp)
        db.commit()
        return new_opp


def upsert_contact(db: Session, tenant_id: str, canonical_data: Dict[str, Any], source_meta: Dict[str, Any]) -> MaterializedContact:
    """Upsert contact into materialized_contacts table"""
    contact_id = canonical_data.get('contact_id')
    if not contact_id:
        raise ValueError("contact_id is required")
    
    existing = db.query(MaterializedContact).filter(
        and_(
            MaterializedContact.tenant_id == tenant_id,
            MaterializedContact.contact_id == contact_id,
            MaterializedContact.source_system == source_meta.get('system')
        )
    ).first()
    
    if existing:
        existing.account_id = canonical_data.get('account_id', existing.account_id)
        existing.first_name = canonical_data.get('first_name', existing.first_name)
        existing.last_name = canonical_data.get('last_name', existing.last_name)
        existing.name = canonical_data.get('name', existing.name)
        existing.email = canonical_data.get('email', existing.email)
        existing.phone = canonical_data.get('phone', existing.phone)
        existing.title = canonical_data.get('title', existing.title)
        existing.department = canonical_data.get('department', existing.department)
        existing.role = canonical_data.get('role', existing.role)
        existing.extras = canonical_data.get('extras', existing.extras)
        existing.updated_at = canonical_data.get('updated_at', datetime.utcnow())
        existing.synced_at = datetime.utcnow()
        db.commit()
        return existing
    else:
        new_contact = MaterializedContact(
            tenant_id=tenant_id,
            contact_id=contact_id,
            account_id=canonical_data.get('account_id'),
            first_name=canonical_data.get('first_name'),
            last_name=canonical_data.get('last_name'),
            name=canonical_data.get('name'),
            email=canonical_data.get('email'),
            phone=canonical_data.get('phone'),
            title=canonical_data.get('title'),
            department=canonical_data.get('department'),
            role=canonical_data.get('role'),
            extras=canonical_data.get('extras', {}),
            source_system=source_meta.get('system'),
            source_connection_id=source_meta.get('connection_id'),
            created_at=canonical_data.get('created_at', datetime.utcnow()),
            updated_at=canonical_data.get('updated_at', datetime.utcnow()),
            synced_at=datetime.utcnow()
        )
        db.add(new_contact)
        db.commit()
        return new_contact


def process_canonical_streams(db: Session, tenant_id: str, limit: int = 1000) -> Dict[str, int]:
    """
    Process canonical streams and upsert into materialized tables
    
    Returns: Dict with processing statistics
    """
    stats = {
        'accounts_processed': 0,
        'opportunities_processed': 0,
        'contacts_processed': 0,
        'errors': 0
    }
    
    try:
        streams = db.query(CanonicalStream).filter(
            CanonicalStream.tenant_id == tenant_id
        ).order_by(CanonicalStream.emitted_at.desc()).limit(limit).all()
        
        for stream in streams:
            try:
                source_meta = stream.source or {}
                
                if stream.entity == 'account':
                    upsert_account(db, tenant_id, stream.data, source_meta)
                    stats['accounts_processed'] += 1
                
                elif stream.entity == 'opportunity':
                    upsert_opportunity(db, tenant_id, stream.data, source_meta)
                    stats['opportunities_processed'] += 1
                
                elif stream.entity == 'contact':
                    upsert_contact(db, tenant_id, stream.data, source_meta)
                    stats['contacts_processed'] += 1
            
            except Exception as e:
                logger.error(f"Error processing stream {stream.id}: {e}")
                stats['errors'] += 1
        
        logger.info(f"Processed {len(streams)} canonical streams: {stats}")
        return stats
    
    except Exception as e:
        logger.error(f"Error processing canonical streams: {e}")
        raise


def get_canonical_opportunities(tenant_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get opportunities from canonical_streams table"""
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
        
        return opportunities
    except Exception as e:
        logger.error(f"Error fetching canonical opportunities: {e}")
        return []
    finally:
        db.close()


def get_materialized_opportunities(tenant_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Get opportunities from materialized_opportunities table"""
    db = next(get_db())
    try:
        result = db.execute(
            select(MaterializedOpportunity)
            .where(MaterializedOpportunity.tenant_id == tenant_id)
            .order_by(MaterializedOpportunity.synced_at.desc())
            .limit(limit)
            .offset(offset)
        )
        opportunities = result.scalars().all()
        
        return [
            {
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
                'synced_at': opp.synced_at.isoformat() if opp.synced_at else None,
            }
            for opp in opportunities
        ]
    except Exception as e:
        logger.error(f"Error fetching materialized opportunities: {e}", exc_info=True)
        return []
    finally:
        db.close()


def get_canonical_accounts(tenant_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get accounts from canonical_streams table"""
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
        
        return accounts
    except Exception as e:
        logger.error(f"Error fetching canonical accounts: {e}")
        return []
    finally:
        db.close()


def get_materialized_accounts(tenant_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Get accounts from materialized_accounts table"""
    db = next(get_db())
    try:
        result = db.execute(
            select(MaterializedAccount)
            .where(MaterializedAccount.tenant_id == tenant_id)
            .order_by(MaterializedAccount.synced_at.desc())
            .limit(limit)
            .offset(offset)
        )
        accounts = result.scalars().all()
        
        return [
            {
                'account_id': acc.account_id,
                'name': acc.name,
                'type': acc.type,
                'industry': acc.industry,
                'owner_id': acc.owner_id,
                'status': acc.status,
                'external_ids': acc.external_ids,
                'extras': acc.extras,
                'source_system': acc.source_system,
                'source_connection_id': acc.source_connection_id,
                'created_at': acc.created_at.isoformat() if acc.created_at else None,
                'updated_at': acc.updated_at.isoformat() if acc.updated_at else None,
                'synced_at': acc.synced_at.isoformat() if acc.synced_at else None,
            }
            for acc in accounts
        ]
    except Exception as e:
        logger.error(f"Error fetching materialized accounts: {e}", exc_info=True)
        return []
    finally:
        db.close()
