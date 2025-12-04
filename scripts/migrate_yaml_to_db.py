#!/usr/bin/env python3
"""
YAML to PostgreSQL Field Mappings Migration Script

Migrates AAM mapping registry from YAML files to DCL-owned field_mappings table.
Part of RACI Remediation P1 - Architect approved.

Usage:
    python scripts/migrate_yaml_to_db.py --dry-run   # Show migration plan
    python scripts/migrate_yaml_to_db.py             # Execute migration
"""

import yaml
import logging
import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db
from app.models import Tenant, ConnectorDefinition, EntitySchema, FieldMapping

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Connector name mapping: YAML filename → connector_name in database
CONNECTOR_NAME_MAPPING = {
    "salesforce.yaml": "salesforce",
    "mongodb.yaml": "mongodb",
    "dynamics.yaml": "dynamics365",
    "hubspot.yaml": "hubspot",
    "pipedrive.yaml": "pipedrive",
    "zendesk.yaml": "zendesk",
    "filesource.yaml": "filesource",
    "supabase.yaml": "supabase"
}


def load_yaml_mappings(yaml_path: Path) -> Dict[str, Any]:
    """Load YAML mapping file"""
    try:
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
            return data if data else {}
    except Exception as e:
        logger.error(f"Failed to load YAML from {yaml_path}: {e}")
        raise


def get_or_create_tenant(db: Session) -> Tenant:
    """Get tenant for migration - use DEMO_TENANT_UUID to match MockUser"""
    from aam_hybrid.shared.constants import DEMO_TENANT_UUID
    from uuid import UUID
    
    # Try to find tenant matching DEMO_TENANT_UUID (used by MockUser)
    tenant = db.query(Tenant).filter(Tenant.id == UUID(DEMO_TENANT_UUID)).first()
    
    if not tenant:
        # Create tenant with DEMO_TENANT_UUID for MockUser compatibility
        tenant = Tenant(
            id=UUID(DEMO_TENANT_UUID),
            name="Demo Tenant (MockUser)"
        )
        db.add(tenant)
        db.flush()
        logger.info(f"Created demo tenant matching MockUser: {tenant.id}")
    else:
        logger.info(f"Using existing tenant matching MockUser: {tenant.name} ({tenant.id})")
    
    return tenant


def get_connector_by_name(db: Session, connector_name: str, tenant_id) -> ConnectorDefinition:
    """Look up connector definition by connector_name"""
    # First try to find connector for this tenant
    connector = db.query(ConnectorDefinition).filter(
        ConnectorDefinition.connector_name == connector_name,
        ConnectorDefinition.tenant_id == tenant_id
    ).first()
    
    if not connector:
        # Try to find connector for any tenant and create one for current tenant
        any_connector = db.query(ConnectorDefinition).filter(
            ConnectorDefinition.connector_name == connector_name
        ).first()
        
        if any_connector:
            # Create connector for current tenant based on existing one
            connector = ConnectorDefinition(
                tenant_id=tenant_id,
                connector_name=connector_name,
                connector_type=any_connector.connector_type,
                description=any_connector.description,
                metadata_json=any_connector.metadata_json,
                status='active'
            )
            db.add(connector)
            db.flush()
            logger.info(f"Created connector '{connector_name}' for current tenant")
        else:
            raise ValueError(f"Connector '{connector_name}' not found in database")
    
    logger.debug(f"Found connector: {connector_name} (ID: {connector.id})")
    return connector


def get_or_create_entity_schema(db: Session, entity_name: str) -> EntitySchema:
    """Get or create entity schema for canonical entity"""
    schema = db.query(EntitySchema).filter(
        EntitySchema.entity_name == entity_name
    ).first()
    
    if not schema:
        schema = EntitySchema(
            entity_name=entity_name,
            entity_version="1.0.0",
            schema_definition={},
            description=f"Canonical schema for {entity_name}"
        )
        db.add(schema)
        db.flush()
        logger.debug(f"Created entity schema for {entity_name}")
    
    return schema


def parse_field_mapping(canonical_field: str, source_value: Union[str, Dict]) -> Tuple[str, Dict]:
    """
    Parse field mapping from YAML value
    
    Handles two cases:
    1. Simple string: canonical_field: "source_field"
    2. Complex dict: canonical_field: {target: "extras.field", ...}
    
    Returns: (source_field, transformation_rule)
    """
    if isinstance(source_value, str):
        # Simple mapping: source_field is the string value
        return source_value, None
    elif isinstance(source_value, dict):
        # Complex mapping with transformation
        # Source field is same as canonical field, transformation stored in rule
        return canonical_field, source_value
    else:
        logger.warning(f"Unexpected mapping value type for {canonical_field}: {type(source_value)}")
        return str(source_value), None


def migrate_connector(
    db: Session, 
    yaml_file: Path, 
    connector_name: str, 
    tenant: Tenant,
    dry_run: bool
) -> Tuple[int, int]:
    """
    Migrate mappings from YAML file to database
    
    Returns: (yaml_count, db_count)
    """
    logger.info(f"Processing {connector_name} from {yaml_file.name}")
    
    # Load YAML
    try:
        mappings_data = load_yaml_mappings(yaml_file)
    except Exception as e:
        logger.error(f"Failed to load {yaml_file}: {e}")
        return 0, 0
    
    if not mappings_data:
        logger.warning(f"No mappings found in {yaml_file}")
        return 0, 0
    
    # Get connector definition
    try:
        connector = get_connector_by_name(db, connector_name, tenant.id)
    except ValueError as e:
        logger.warning(f"Skipping {connector_name}: {e}")
        return 0, 0
    
    yaml_count = 0
    db_count = 0
    
    # Process each entity
    for entity_name, entity_data in mappings_data.items():
        if not entity_data or 'fields' not in entity_data:
            logger.warning(f"No fields found for entity '{entity_name}' in {connector_name}")
            continue
        
        # Get or create entity schema
        entity_schema = get_or_create_entity_schema(db, entity_name)
        
        # NORMALIZE to lowercase (per architect guidance - prevent casing duplicates)
        source_table = entity_name.lower()
        
        # IDEMPOTENT DELETE: Remove all existing mappings for this connector+entity
        # This ensures clean re-migration without duplicates (per architect guidance)
        if not dry_run:
            deleted_count = db.query(FieldMapping).filter(
                FieldMapping.tenant_id == tenant.id,
                FieldMapping.connector_id == connector.id,
                FieldMapping.source_table == source_table
            ).delete(synchronize_session=False)
            if deleted_count > 0:
                logger.info(f"  Idempotent cleanup: Deleted {deleted_count} existing mappings for {connector_name}.{source_table}")
        
        # Process each field mapping
        fields = entity_data.get('fields', {})
        for canonical_field, source_value in fields.items():
            yaml_count += 1
            
            # Parse the mapping
            source_field, transformation_rule = parse_field_mapping(canonical_field, source_value)
            
            if dry_run:
                logger.info(
                    f"  [DRY RUN] Would migrate: {connector_name}.{source_table}.{source_field} "
                    f"-> {entity_name}.{canonical_field}"
                )
                db_count += 1
                continue
            
            # Check if mapping already exists (idempotent)
            existing = db.query(FieldMapping).filter(
                FieldMapping.tenant_id == tenant.id,
                FieldMapping.connector_id == connector.id,
                FieldMapping.source_table == source_table,
                FieldMapping.source_field == source_field
            ).first()
            
            if existing:
                # Update existing mapping
                existing.canonical_entity = entity_name
                existing.canonical_field = canonical_field
                existing.confidence_score = 1.0
                existing.mapping_type = "direct"
                existing.transformation_rule = transformation_rule
                existing.metadata = {
                    "migrated_from": "yaml",
                    "migration_date": datetime.now().isoformat(),
                    "original_version": existing.version
                }
                existing.version = existing.version + 1
                existing.mapping_source = "yaml_migration"
                logger.debug(f"  Updated: {source_table}.{source_field}")
            else:
                # Create new mapping
                new_mapping = FieldMapping(
                    tenant_id=tenant.id,
                    connector_id=connector.id,
                    entity_schema_id=entity_schema.id,
                    source_table=source_table,
                    source_field=source_field,
                    canonical_entity=entity_name,
                    canonical_field=canonical_field,
                    confidence_score=1.0,
                    mapping_type="direct",
                    transformation_rule=transformation_rule,
                    metadata={
                        "migrated_from": "yaml",
                        "migration_date": datetime.now().isoformat()
                    },
                    mapping_source="yaml_migration",
                    version=1
                )
                db.add(new_mapping)
                logger.debug(f"  Created: {source_table}.{source_field}")
            
            db_count += 1
    
    # Commit changes
    if not dry_run:
        try:
            db.commit()
            logger.info(f"Committed {db_count} mappings for {connector_name}")
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error for {connector_name}: {e}")
            raise
    
    return yaml_count, db_count


def verify_migration(db: Session, connector_name: str, tenant_id, expected_count: int) -> bool:
    """Verify that migration was successful"""
    connector = db.query(ConnectorDefinition).filter(
        ConnectorDefinition.connector_name == connector_name,
        ConnectorDefinition.tenant_id == tenant_id
    ).first()
    
    if not connector:
        return False
    
    actual_count = db.query(FieldMapping).filter(
        FieldMapping.connector_id == connector.id,
        FieldMapping.tenant_id == tenant_id
    ).count()
    
    return actual_count >= expected_count


def print_migration_report(
    results: List[Tuple[str, int, int, str]], 
    total_yaml: int, 
    total_db: int,
    dry_run: bool
):
    """Print formatted migration report"""
    print("\n" + "="*60)
    print("YAML→PostgreSQL Migration Report")
    print("="*60)
    
    for connector_name, yaml_count, db_count, status in results:
        print(f"\nConnector: {connector_name}")
        print(f"  - YAML mappings: {yaml_count}")
        print(f"  - DB records inserted/updated: {db_count}")
        print(f"  - Status: {status}")
    
    print("\n" + "="*60)
    print(f"Total: {len(results)} connectors, {total_yaml} YAML mappings")
    print(f"       {total_db} database records {'would be ' if dry_run else ''}inserted/updated")
    
    if dry_run:
        print("\n🔍 [DRY RUN] No changes committed to database")
    else:
        success_count = sum(1 for _, _, _, status in results if "✅" in status)
        print(f"\n✅ Migration complete! ({success_count}/{len(results)} connectors successful)")
    
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Migrate YAML mapping files to PostgreSQL field_mappings table',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/migrate_yaml_to_db.py --dry-run    # Preview migration
  python scripts/migrate_yaml_to_db.py              # Execute migration
        """
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true', 
        help='Show what would be migrated without committing changes'
    )
    args = parser.parse_args()
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - Showing migration plan without committing\n")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get or create tenant
        tenant = get_or_create_tenant(db)
        
        # Mapping files directory
        mappings_dir = Path("services/aam/canonical/mappings")
        
        if not mappings_dir.exists():
            logger.error(f"Mappings directory not found: {mappings_dir}")
            print(f"❌ Error: Mappings directory not found: {mappings_dir}")
            return 1
        
        # Results tracking
        results = []
        total_yaml = 0
        total_db = 0
        
        # Process each connector
        for yaml_filename, connector_name in CONNECTOR_NAME_MAPPING.items():
            yaml_file = mappings_dir / yaml_filename
            
            if not yaml_file.exists():
                logger.warning(f"YAML file not found: {yaml_file}")
                results.append((connector_name, 0, 0, "❌ FILE_NOT_FOUND"))
                continue
            
            try:
                yaml_count, db_count = migrate_connector(
                    db, yaml_file, connector_name, tenant, args.dry_run
                )
                
                total_yaml += yaml_count
                total_db += db_count
                
                # Verify if not dry run
                if not args.dry_run and yaml_count > 0:
                    verified = verify_migration(db, connector_name, tenant.id, db_count)
                    status = "✅ VERIFIED" if verified else "⚠️  VERIFY_FAILED"
                else:
                    status = "✅ SUCCESS" if yaml_count > 0 else "⚠️  NO_MAPPINGS"
                
                results.append((connector_name, yaml_count, db_count, status))
                
            except Exception as e:
                logger.error(f"Failed to migrate {connector_name}: {e}", exc_info=True)
                results.append((connector_name, 0, 0, f"❌ FAILED: {str(e)[:40]}"))
        
        # Print migration report
        print_migration_report(results, total_yaml, total_db, args.dry_run)
        
        # Return success if we migrated at least something
        if total_yaml == 0:
            logger.warning("No mappings were migrated!")
            return 1
        
        # Check for any failures
        failed_count = sum(1 for _, _, _, status in results if "❌" in status or "FAILED" in status)
        if failed_count > 0:
            logger.warning(f"{failed_count} connector(s) failed to migrate")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        db.rollback()
        print(f"\n❌ Migration failed: {e}\n")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
