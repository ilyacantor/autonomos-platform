import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared import settings

logger = logging.getLogger(__name__)


async def get_credential(credential_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve credential by ID
    
    MVP Implementation: Retrieves from environment variables
    Production: Would integrate with HashiCorp Vault, AWS Secrets Manager, etc.
    
    Args:
        credential_id: Credential identifier
    
    Returns:
        Credential object or None
    """
    if credential_id.startswith("salesforce"):
        return await get_salesforce_config(credential_id)
    
    logger.warning(f"Unknown credential type: {credential_id}")
    return None


async def get_salesforce_config(credential_id: str) -> Optional[Dict[str, Any]]:
    """
    Get Salesforce connection configuration for Airbyte
    
    MVP Implementation: Uses environment variables
    Production: Would retrieve from secure vault (HashiCorp Vault, AWS Secrets Manager)
    
    Args:
        credential_id: Salesforce credential identifier
    
    Returns:
        Airbyte Salesforce connector configuration with full OAuth tokens
    
    Raises:
        Exception if required credentials are missing
    """
    logger.info(f"Retrieving Salesforce configuration for: {credential_id}")
    
    missing_creds = []
    if not settings.SALESFORCE_CLIENT_ID:
        missing_creds.append("SALESFORCE_CLIENT_ID")
    if not settings.SALESFORCE_CLIENT_SECRET:
        missing_creds.append("SALESFORCE_CLIENT_SECRET")
    if not settings.SALESFORCE_REFRESH_TOKEN:
        missing_creds.append("SALESFORCE_REFRESH_TOKEN")
    
    if missing_creds:
        error_msg = f"Missing required Salesforce credentials: {', '.join(missing_creds)}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    config = {
        "client_id": settings.SALESFORCE_CLIENT_ID,
        "client_secret": settings.SALESFORCE_CLIENT_SECRET,
        "refresh_token": settings.SALESFORCE_REFRESH_TOKEN,
        "is_sandbox": False,
        "auth_type": "Client",
        "start_date": "2024-01-01T00:00:00Z"
    }
    
    logger.info("Salesforce configuration retrieved successfully with OAuth tokens")
    return config
