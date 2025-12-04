from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aam_hybrid.shared import settings, HealthResponse
from .service import get_salesforce_config, get_credential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AAM Auth Broker",
    description="Authentication and credential management for Adaptive API Mesh",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(service="auth_broker")


@app.get("/credentials/{credential_id}")
async def get_credentials(credential_id: str):
    """
    Retrieve credentials for a given credential ID
    
    Args:
        credential_id: Identifier for the credential (e.g., 'salesforce-prod')
    
    Returns:
        Credential configuration object
    """
    try:
        credential = await get_credential(credential_id)
        if not credential:
            raise HTTPException(status_code=404, detail=f"Credential not found: {credential_id}")
        
        return credential
    except Exception as e:
        logger.error(f"Error retrieving credential {credential_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/credentials/salesforce/{credential_id}")
async def get_salesforce_credentials(credential_id: str):
    """
    Get Salesforce-specific connection configuration
    
    Args:
        credential_id: Salesforce credential identifier
    
    Returns:
        Airbyte Salesforce connector configuration
    """
    try:
        config = await get_salesforce_config(credential_id)
        if not config:
            raise HTTPException(status_code=404, detail=f"Salesforce credential not found: {credential_id}")
        
        return config
    except Exception as e:
        logger.error(f"Error retrieving Salesforce config {credential_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.SERVICE_PORT_AUTH_BROKER)
