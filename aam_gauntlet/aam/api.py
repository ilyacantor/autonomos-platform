"""FastAPI backend for AAM with demo endpoints."""
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from connector import AAM, ConnectorConfig, CredentialDescriptor, RatePolicy, NetworkProfile
from db import MetricsDB
import sys
sys.path.append("..")
from workflows.high_volume_read import high_volume_read_workflow
from workflows.idempotent_write import idempotent_write_workflow
from workflows.drift_sensitive import drift_sensitive_workflow, continuous_drift_monitor


# Request/Response models
class CreateConnectorRequest(BaseModel):
    service_id: str
    tenant_id: str
    base_url: str = "http://localhost:8001"
    auth_type: str = "oauth2_client_credentials"
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    api_key: Optional[str] = None


class RunScenarioRequest(BaseModel):
    mode: str = "mild"  # mild | storm | hell
    duration_seconds: int = 30
    connectors: List[str] = []  # List of service_ids to test


class WorkflowRequest(BaseModel):
    connector_id: str  # format: service_id:tenant_id
    workflow_type: str  # high_volume | idempotent_write | drift_sensitive
    duration_seconds: Optional[int] = 30
    params: Dict[str, Any] = {}


# Global AAM instance
aam = AAM()

# Active workflows tracking
active_workflows = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # Startup
    print("AAM Backend starting...")
    
    # Create some default connectors
    default_services = [
        "salesforce_mock",
        "mongodb_mock",
        "stripe_mock",
        "github_mock"
    ]
    
    for service_id in default_services:
        try:
            config = ConnectorConfig(
                service_id=service_id,
                tenant_id="tenant1",
                base_url="http://localhost:8001",
                credentials=CredentialDescriptor(
                    auth_type="oauth2_client_credentials" if "salesforce" in service_id or "github" in service_id else "api_key",
                    client_id=f"{service_id}:tenant1",
                    client_secret="secret",
                    api_key=f"sk_test_{service_id}_1234"
                )
            )
            aam.create_connector(config)
            print(f"Created default connector: {service_id}:tenant1")
        except Exception as e:
            print(f"Failed to create connector {service_id}: {e}")
    
    yield
    
    # Shutdown
    print("AAM Backend shutting down...")
    await aam.close_all()


app = FastAPI(
    title="AAM Gauntlet - AAM Backend",
    description="Adaptive API Mesh testing backend",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Connector Management
@app.post("/connectors", response_model=Dict[str, str])
async def create_connector(request: CreateConnectorRequest):
    """Create a new AAM connector."""
    try:
        credentials = CredentialDescriptor(
            auth_type=request.auth_type,
            client_id=request.client_id or f"{request.service_id}:{request.tenant_id}",
            client_secret=request.client_secret or "secret",
            api_key=request.api_key
        )
        
        config = ConnectorConfig(
            service_id=request.service_id,
            tenant_id=request.tenant_id,
            base_url=request.base_url,
            credentials=credentials
        )
        
        connector = aam.create_connector(config)
        
        return {
            "connector_id": f"{request.service_id}:{request.tenant_id}",
            "status": "created"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/connectors")
async def list_connectors():
    """List all active connectors."""
    connectors = []
    for connector_id, connector in aam.connectors.items():
        service_id, tenant_id = connector_id.split(":")
        connectors.append({
            "connector_id": connector_id,
            "service_id": service_id,
            "tenant_id": tenant_id,
            "auth_type": connector.config.credentials.auth_type,
            "base_url": connector.config.base_url
        })
    
    return {"connectors": connectors}


@app.delete("/connectors/{connector_id}")
async def delete_connector(connector_id: str):
    """Delete a connector."""
    if connector_id in aam.connectors:
        await aam.connectors[connector_id].close()
        del aam.connectors[connector_id]
        return {"status": "deleted"}
    else:
        raise HTTPException(status_code=404, detail="Connector not found")


# Workflow Management
@app.post("/workflows/run")
async def run_workflow(request: WorkflowRequest, background_tasks: BackgroundTasks):
    """Run a test workflow."""
    if request.connector_id not in aam.connectors:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    connector = aam.connectors[request.connector_id]
    workflow_id = f"{request.workflow_type}_{request.connector_id}_{datetime.utcnow().timestamp()}"
    
    async def run_workflow_task():
        """Background task to run workflow."""
        try:
            if request.workflow_type == "high_volume":
                result = await high_volume_read_workflow(
                    connector,
                    duration_seconds=request.duration_seconds,
                    **request.params
                )
            elif request.workflow_type == "idempotent_write":
                result = await idempotent_write_workflow(
                    connector,
                    **request.params
                )
            elif request.workflow_type == "drift_sensitive":
                result = await drift_sensitive_workflow(
                    connector,
                    **request.params
                )
            elif request.workflow_type == "drift_monitor":
                result = await continuous_drift_monitor(
                    connector,
                    duration_seconds=request.duration_seconds,
                    **request.params
                )
            else:
                result = {"error": "Unknown workflow type"}
            
            active_workflows[workflow_id]["status"] = "completed"
            active_workflows[workflow_id]["result"] = result
            active_workflows[workflow_id]["end_time"] = datetime.utcnow().isoformat()
            
        except Exception as e:
            active_workflows[workflow_id]["status"] = "failed"
            active_workflows[workflow_id]["error"] = str(e)
            active_workflows[workflow_id]["end_time"] = datetime.utcnow().isoformat()
    
    # Track workflow
    active_workflows[workflow_id] = {
        "workflow_id": workflow_id,
        "workflow_type": request.workflow_type,
        "connector_id": request.connector_id,
        "status": "running",
        "start_time": datetime.utcnow().isoformat()
    }
    
    # Start workflow in background
    background_tasks.add_task(run_workflow_task)
    
    return {"workflow_id": workflow_id, "status": "started"}


@app.get("/workflows")
async def list_workflows():
    """List all workflows and their status."""
    return {"workflows": list(active_workflows.values())}


@app.get("/workflows/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """Get status of a specific workflow."""
    if workflow_id not in active_workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return active_workflows[workflow_id]


# Scenario Management
@app.post("/scenarios/run")
async def run_scenario(request: RunScenarioRequest, background_tasks: BackgroundTasks):
    """Run a chaos scenario."""
    # Set chaos level on API Farm
    import httpx
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://localhost:8000/admin/chaos",
            json={"level": request.mode}
        )
    
    # Run workflows for specified connectors
    workflow_ids = []
    
    for service_id in request.connectors:
        connector_id = f"{service_id}:tenant1"
        if connector_id not in aam.connectors:
            continue
        
        # Run high volume workflow
        workflow_request = WorkflowRequest(
            connector_id=connector_id,
            workflow_type="high_volume",
            duration_seconds=request.duration_seconds
        )
        result = await run_workflow(workflow_request, background_tasks)
        workflow_ids.append(result["workflow_id"])
        
        # Run idempotent write workflow
        workflow_request = WorkflowRequest(
            connector_id=connector_id,
            workflow_type="idempotent_write",
            params={"num_writes": 20}
        )
        result = await run_workflow(workflow_request, background_tasks)
        workflow_ids.append(result["workflow_id"])
    
    return {
        "scenario": request.mode,
        "duration": request.duration_seconds,
        "workflow_ids": workflow_ids,
        "status": "started"
    }


# Metrics and Monitoring
@app.get("/metrics")
async def get_metrics():
    """Get overall AAM metrics."""
    metrics = aam.get_metrics()
    
    # Add workflow metrics
    metrics["workflows"] = {
        "total": len(active_workflows),
        "running": sum(1 for w in active_workflows.values() if w["status"] == "running"),
        "completed": sum(1 for w in active_workflows.values() if w["status"] == "completed"),
        "failed": sum(1 for w in active_workflows.values() if w["status"] == "failed")
    }
    
    return metrics


@app.get("/metrics/connectors/{connector_id}")
async def get_connector_metrics(connector_id: str):
    """Get metrics for a specific connector."""
    if connector_id not in aam.connectors:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    # Get metrics from database
    service_id, tenant_id = connector_id.split(":")
    metrics = aam.db.get_metrics_summary(connector_id=connector_id)
    
    # Add rate limiter stats
    metrics["rate_limiter"] = aam.rate_limiter.get_stats(connector_id)
    
    return metrics


@app.get("/dlq")
async def get_dlq_entries(status: str = "pending", limit: int = 100):
    """Get entries from the Dead Letter Queue."""
    entries = aam.db.get_dlq_entries(status=status, limit=limit)
    return {"entries": entries, "count": len(entries)}


@app.post("/dlq/{entry_id}/retry")
async def retry_dlq_entry(entry_id: int):
    """Retry a DLQ entry."""
    # This would trigger DLQ processing for specific entry
    await aam.dlq.process_dlq(aam)
    return {"status": "retry_initiated"}


# Health Check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "connectors": len(aam.connectors),
        "workflows_running": sum(1 for w in active_workflows.values() if w["status"] == "running")
    }


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8080, reload=True)