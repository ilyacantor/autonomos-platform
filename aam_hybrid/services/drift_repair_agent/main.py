from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from aam_hybrid.shared.config import settings
from aam_hybrid.shared.database import get_db, init_db
from app.schemas.health import HealthResponse
from aam_hybrid.shared.models import CatalogUpdate
from aam_hybrid.services.drift_repair_agent.service import apply_catalog_update

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AAM Drift Repair Agent",
    description="Configuration drift detection and repair for Adaptive API Mesh",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info("Drift Repair Agent starting...")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(service="drift_repair_agent")


@app.post("/repair/apply_new_catalog")
async def update_catalog(
    catalog_update: CatalogUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Apply a new syncCatalog to a connection (Drift Repair)
    
    Flow:
    1. Retrieve connection from Registry
    2. Update status to HEALING
    3. Call Airbyte API to update connection catalog
    4. Create new catalog version in Registry
    5. Update status to ACTIVE
    
    Args:
        catalog_update: Connection ID and new catalog
    
    Returns:
        Update confirmation with new version number
    """
    try:
        result = await apply_catalog_update(db, catalog_update)
        return result
    except Exception as e:
        logger.error(f"Catalog update failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.SERVICE_PORT_DRIFT_REPAIR)
