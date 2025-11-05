#!/usr/bin/env python3
"""
Load FileSource CSV data into canonical_streams table

This script directly invokes FileSourceConnector.replay_entity() to load
AWS resources and cost reports CSVs for FinOps Pilot.
"""
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from services.aam.connectors.filesource.connector import FileSourceConnector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Load FileSource AWS cost data for FinOps Pilot"""
    logger.info("Starting FileSource AWS cost data load...")
    
    db = SessionLocal()
    try:
        # Use existing default-tenant UUID from tenants table
        connector = FileSourceConnector(db=db, tenant_id="167e5129-295e-4433-b65e-b8b4d41ffc76")
        
        # Load only AWS entities for FinOps
        logger.info("Loading aws_resources data...")
        stats_resources = connector.replay_entity(entity="aws_resources", system="filesource")
        
        logger.info("Loading cost_reports data...")
        stats_costs = connector.replay_entity(entity="cost_reports", system="filesource")
        
        total_records = stats_resources['total_records'] + stats_costs['total_records']
        total_files = stats_resources['files_processed'] + stats_costs['files_processed']
        
        logger.info(f"✅ FileSource AWS cost data loaded successfully!")
        logger.info(f"   Files processed: {total_files}")
        logger.info(f"   Total records: {total_records}")
        logger.info(f"   AWS Resources: {stats_resources['total_records']}")
        logger.info(f"   Cost Reports: {stats_costs['total_records']}")
        
        return 0
    
    except Exception as e:
        logger.error(f"❌ Failed to load FileSource data: {e}", exc_info=True)
        return 1
    
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
