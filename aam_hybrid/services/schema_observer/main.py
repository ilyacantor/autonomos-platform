from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aam_hybrid.shared import settings, HealthResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AAM Schema Observer",
    description="Schema drift detection and monitoring (Skeleton Service)",
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
    return HealthResponse(service="schema_observer")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "schema_observer",
        "status": "skeleton",
        "message": "Schema Observer service - Implementation coming in future phases"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.SERVICE_PORT_SCHEMA_OBSERVER)
