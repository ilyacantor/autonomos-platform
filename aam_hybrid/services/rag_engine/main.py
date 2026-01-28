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
    title="AAM RAG Engine",
    description="DEPRECATED: This service is a no-op stub. Use DCL Intelligence API directly.",
    version="1.0.0",
    deprecated=True
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
    return HealthResponse(service="rag_engine")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "rag_engine",
        "status": "deprecated",
        "message": "DEPRECATED: This service is a no-op stub. All methods return empty values. Use DCL Intelligence API directly."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.SERVICE_PORT_RAG_ENGINE)
