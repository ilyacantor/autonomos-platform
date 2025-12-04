"""
Startup validation for AAM Orchestrator
Ensures all required credentials are configured before accepting requests
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aam_hybrid.shared import settings

logger = logging.getLogger(__name__)


def validate_configuration():
    """
    Validate that all required configuration is present
    
    Raises:
        Exception if critical configuration is missing
    """
    missing = []
    warnings = []
    
    if not settings.AIRBYTE_CLIENT_ID:
        missing.append("AIRBYTE_CLIENT_ID")
    
    if not settings.AIRBYTE_CLIENT_SECRET:
        missing.append("AIRBYTE_CLIENT_SECRET")
    
    if not settings.AIRBYTE_WORKSPACE_ID:
        missing.append("AIRBYTE_WORKSPACE_ID")
    
    if not settings.AIRBYTE_DESTINATION_ID:
        missing.append("AIRBYTE_DESTINATION_ID")
    
    if not settings.SALESFORCE_CLIENT_ID:
        warnings.append("SALESFORCE_CLIENT_ID (Salesforce onboarding will fail)")
    
    if not settings.SALESFORCE_CLIENT_SECRET:
        warnings.append("SALESFORCE_CLIENT_SECRET (Salesforce onboarding will fail)")
    
    if not settings.SALESFORCE_REFRESH_TOKEN:
        warnings.append("SALESFORCE_REFRESH_TOKEN (Salesforce onboarding will fail)")
    
    if missing:
        error_msg = (
            f"❌ CRITICAL: Missing required Airbyte credentials: {', '.join(missing)}\n\n"
            f"These are REQUIRED for AAM to function. Please:\n"
            f"1. Run: abctl local credentials\n"
            f"2. Set AIRBYTE_CLIENT_ID and AIRBYTE_CLIENT_SECRET from the output\n"
            f"3. Get AIRBYTE_WORKSPACE_ID and AIRBYTE_DESTINATION_ID from Airbyte UI\n"
            f"4. Update your .env file or docker-compose environment variables\n"
        )
        logger.error(error_msg)
        raise Exception(error_msg)
    
    if warnings:
        warning_msg = (
            f"⚠️  WARNING: Missing optional credentials: {', '.join(warnings)}\n"
            f"Some features may not work. Check .env.example for setup instructions.\n"
        )
        logger.warning(warning_msg)
    
    logger.info("✅ Configuration validation passed")
    logger.info(f"Airbyte API: {settings.AIRBYTE_API_URL}")
    logger.info(f"Workspace ID: {settings.AIRBYTE_WORKSPACE_ID}")
    logger.info(f"Destination ID: {settings.AIRBYTE_DESTINATION_ID}")
