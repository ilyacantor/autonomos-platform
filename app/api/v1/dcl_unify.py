"""
DCL Contact Unification Endpoint
Unifies contacts across sources using exact email matching
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.models import User, DCLUnifiedContact, DCLUnifiedContactLink
from app.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/unify/run")
async def run_unification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Unify contacts across all sources using exact email matching.
    TENANT-ISOLATED: Only unifies contacts within the current tenant.
    
    Algorithm:
    1. Query all contacts from canonical_streams with non-null emails (TENANT-SCOPED)
    2. Group by LOWER(TRIM(email))
    3. For each email group:
       - Find or create unified_contact record (with tenant_id)
       - Upsert links for each source contact (with tenant_id)
    
    Returns:
        {"status": "ok", "unified_contacts": N, "links": M}
    
    Idempotent: Can be run multiple times safely.
    """
    try:
        tenant_id = current_user.tenant_id
        logger.info(f"Starting DCL contact unification for tenant: {tenant_id}")
        
        # Query all contacts with non-null emails from canonical_streams
        query = text("""
            SELECT 
                data->>'contact_id' as contact_id,
                data->>'email' as email,
                data->>'first_name' as first_name,
                data->>'last_name' as last_name,
                source->>'system' as source_system,
                source->>'connection_id' as source_connection_id
            FROM canonical_streams
            WHERE entity = 'contact'
            AND data->>'email' IS NOT NULL
            AND TRIM(data->>'email') != ''
            AND tenant_id = :tenant_id
        """)
        
        result = db.execute(query, {"tenant_id": str(tenant_id)})
        contacts = result.fetchall()
        
        logger.info(f"Found {len(contacts)} contacts with emails for tenant {tenant_id}")
        
        # Group contacts by normalized email
        email_groups: Dict[str, list] = {}
        for contact in contacts:
            if contact.email:
                normalized_email = contact.email.lower().strip()
                if normalized_email not in email_groups:
                    email_groups[normalized_email] = []
                email_groups[normalized_email].append(contact)
        
        logger.info(f"Grouped into {len(email_groups)} unique emails")
        
        unified_count = 0
        link_count = 0
        
        # Process each email group
        for email, contact_list in email_groups.items():
            # Check if unified contact already exists FOR THIS TENANT
            existing_unified = db.query(DCLUnifiedContact).filter(
                DCLUnifiedContact.tenant_id == tenant_id,
                DCLUnifiedContact.email == email
            ).first()
            
            if existing_unified:
                unified_contact_id = existing_unified.unified_contact_id
                logger.debug(f"Reusing existing unified contact {unified_contact_id} for {email} (tenant {tenant_id})")
            else:
                # Create new unified contact WITH TENANT_ID
                # Use first contact's first_name and last_name
                first_contact = contact_list[0]
                new_unified = DCLUnifiedContact(
                    tenant_id=tenant_id,
                    email=email,
                    first_name=first_contact.first_name,
                    last_name=first_contact.last_name
                )
                db.add(new_unified)
                db.flush()  # Get the ID
                unified_contact_id = new_unified.unified_contact_id
                unified_count += 1
                logger.debug(f"Created new unified contact {unified_contact_id} for {email} (tenant {tenant_id})")
            
            # Upsert links for each source contact
            for contact in contact_list:
                # Build source_system from source JSON
                source_system = contact.source_system or "unknown"
                if contact.source_connection_id:
                    source_system = f"{source_system}-{contact.source_connection_id}"
                
                # Check if link already exists FOR THIS TENANT
                existing_link = db.query(DCLUnifiedContactLink).filter(
                    DCLUnifiedContactLink.tenant_id == tenant_id,
                    DCLUnifiedContactLink.source_system == source_system,
                    DCLUnifiedContactLink.source_contact_id == contact.contact_id
                ).first()
                
                if not existing_link:
                    # Create new link WITH TENANT_ID
                    new_link = DCLUnifiedContactLink(
                        tenant_id=tenant_id,
                        unified_contact_id=unified_contact_id,
                        source_system=source_system,
                        source_contact_id=contact.contact_id
                    )
                    db.add(new_link)
                    link_count += 1
                    logger.debug(f"Created link: {source_system}:{contact.contact_id} -> {unified_contact_id} (tenant {tenant_id})")
                else:
                    # Update existing link if unified_contact_id changed
                    if existing_link.unified_contact_id != unified_contact_id:
                        existing_link.unified_contact_id = unified_contact_id
                        logger.debug(f"Updated link: {source_system}:{contact.contact_id} -> {unified_contact_id} (tenant {tenant_id})")
        
        # Commit all changes
        db.commit()
        
        logger.info(f"Unification complete for tenant {tenant_id}: {unified_count} new unified contacts, {link_count} new links")
        
        return {
            "status": "ok",
            "unified_contacts": unified_count,
            "links": link_count
        }
    
    except Exception as e:
        logger.error(f"Error during unification: {e}", exc_info=True)
        db.rollback()
        return {
            "status": "error",
            "error": str(e),
            "unified_contacts": 0,
            "links": 0
        }
