import logging
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import os

logger = logging.getLogger(__name__)

router = APIRouter()

# Create async engine for Supabase connection
DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL:
    # Convert to asyncpg URL
    async_db_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    try:
        async_engine = create_async_engine(
            async_db_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10
        )
        AsyncSessionLocal = async_sessionmaker(
            async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
        logger.info("✅ AAM Monitoring: Async database engine created")
    except Exception as e:
        logger.error(f"Failed to create async engine: {e}")
        async_engine = None
        AsyncSessionLocal = None
else:
    async_engine = None
    AsyncSessionLocal = None
    logger.warning("DATABASE_URL not set - AAM monitoring endpoints will return mock data")

# Import AAM models - with fallback
AAM_MODELS_AVAILABLE = False
try:
    import sys
    from pathlib import Path
    aam_path = Path(__file__).parent.parent.parent.parent / "aam-hybrid"
    sys.path.insert(0, str(aam_path))
    
    from shared.models import Connection, JobHistory, SyncCatalogVersion, ConnectionStatus, JobStatus
    AAM_MODELS_AVAILABLE = True
    logger.info("✅ AAM models imported successfully")
except Exception as e:
    logger.warning(f"Could not import AAM models: {e}. Using fallback mode.")
    Connection = None  # type: ignore
    JobHistory = None  # type: ignore
    SyncCatalogVersion = None  # type: ignore
    ConnectionStatus = None  # type: ignore
    JobStatus = None  # type: ignore


@router.get("/status")
async def get_aam_status():
    """
    Get AAM services status
    Returns the health status of SchemaObserver, RAGEngine, and DriftRepairAgent
    """
    services = {
        "SchemaObserver": {"port": 8004, "name": "Schema Observer"},
        "RAGEngine": {"port": 8005, "name": "RAG Engine"},
        "DriftRepairAgent": {"port": 8003, "name": "Drift Repair Agent"},
        "Orchestrator": {"port": 8001, "name": "Orchestrator"}
    }
    
    service_status = []
    
    async with httpx.AsyncClient(timeout=2.0) as client:
        for service_key, service_info in services.items():
            try:
                response = await client.get(f"http://localhost:{service_info['port']}/health")
                if response.status_code == 200:
                    service_status.append({
                        "name": service_info["name"],
                        "status": "running",
                        "port": service_info["port"]
                    })
                else:
                    service_status.append({
                        "name": service_info["name"],
                        "status": "error",
                        "port": service_info["port"]
                    })
            except Exception as e:
                service_status.append({
                    "name": service_info["name"],
                    "status": "stopped",
                    "port": service_info["port"],
                    "error": str(e)
                })
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "services": service_status,
        "overall_status": "healthy" if all(s["status"] == "running" for s in service_status) else "degraded"
    }


@router.get("/metrics")
async def get_aam_metrics():
    """
    Get AAM dashboard metrics
    Returns key performance metrics for the AAM system
    """
    if not AsyncSessionLocal or not AAM_MODELS_AVAILABLE:
        # Return mock data if database not available
        return {
            "total_connections": 8,
            "active_drift_detections_24h": 3,
            "successful_repairs_24h": 12,
            "manual_reviews_required_24h": 1,
            "average_confidence_score": 0.94,
            "average_repair_time_seconds": 45.2,
            "timestamp": datetime.utcnow().isoformat(),
            "data_source": "mock"
        }
    
    try:
        async with AsyncSessionLocal() as db:
            # Total connections
            total_connections_result = await db.execute(select(func.count(Connection.id)))  # type: ignore
            total_connections = total_connections_result.scalar() or 0
            
            # Active connections
            active_connections_result = await db.execute(
                select(func.count(Connection.id)).where(Connection.status == ConnectionStatus.ACTIVE)  # type: ignore
            )
            active_connections = active_connections_result.scalar() or 0
            
            # Jobs in last 24 hours
            last_24h = datetime.utcnow() - timedelta(hours=24)
            
            # Failed jobs (drift detections)
            failed_jobs_result = await db.execute(
                select(func.count(JobHistory.id)).where(  # type: ignore
                    and_(
                        JobHistory.started_at >= last_24h,  # type: ignore
                        JobHistory.status == JobStatus.FAILED  # type: ignore
                    )
                )
            )
            drift_detections = failed_jobs_result.scalar() or 0
            
            # Successful jobs (successful repairs)
            successful_jobs_result = await db.execute(
                select(func.count(JobHistory.id)).where(  # type: ignore
                    and_(
                        JobHistory.started_at >= last_24h,  # type: ignore
                        JobHistory.status == JobStatus.SUCCEEDED  # type: ignore
                    )
                )
            )
            successful_repairs = successful_jobs_result.scalar() or 0
            
            # Connections in HEALING status (manual reviews)
            healing_connections_result = await db.execute(
                select(func.count(Connection.id)).where(Connection.status == ConnectionStatus.HEALING)  # type: ignore
            )
            manual_reviews = healing_connections_result.scalar() or 0
            
            # Calculate average repair time from completed jobs
            completed_jobs_result = await db.execute(
                select(JobHistory).where(  # type: ignore
                    and_(
                        JobHistory.completed_at.isnot(None),  # type: ignore
                        JobHistory.started_at >= last_24h  # type: ignore
                    )
                )
            )
            completed_jobs = completed_jobs_result.scalars().all()
            
            if completed_jobs:
                repair_times = [
                    (job.completed_at - job.started_at).total_seconds()
                    for job in completed_jobs
                    if job.completed_at and job.started_at
                ]
                avg_repair_time = sum(repair_times) / len(repair_times) if repair_times else 0
            else:
                avg_repair_time = 0
            
            return {
                "total_connections": total_connections,
                "active_connections": active_connections,
                "active_drift_detections_24h": drift_detections,
                "successful_repairs_24h": successful_repairs,
                "manual_reviews_required_24h": manual_reviews,
                "average_confidence_score": 0.92,  # Placeholder - would come from repair_knowledge_base
                "average_repair_time_seconds": round(avg_repair_time, 2),
                "timestamp": datetime.utcnow().isoformat(),
                "data_source": "database"
            }
    
    except Exception as e:
        logger.error(f"Error fetching AAM metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch metrics: {str(e)}"
        )


@router.get("/events")
async def get_aam_events(limit: int = 50):
    """
    Get recent AAM events from job_history
    Returns the most recent job history events
    """
    if not AsyncSessionLocal or not AAM_MODELS_AVAILABLE:
        # Return mock data
        mock_events = [
            {
                "id": f"event-{i}",
                "connection_name": ["Salesforce", "NetSuite", "SAP", "Snowflake"][i % 4],
                "event_type": ["drift_detected", "repair_success", "sync_completed"][i % 3],
                "status": ["SUCCEEDED", "FAILED", "RUNNING"][i % 3],
                "timestamp": (datetime.utcnow() - timedelta(minutes=i*5)).isoformat(),
                "message": f"Event {i} occurred"
            }
            for i in range(min(limit, 20))
        ]
        return {
            "events": mock_events,
            "total": len(mock_events),
            "data_source": "mock"
        }
    
    try:
        async with AsyncSessionLocal() as db:
            # Fetch recent jobs with connection info
            result = await db.execute(
                select(JobHistory, Connection)  # type: ignore
                .join(Connection, JobHistory.connection_id == Connection.id)  # type: ignore
                .order_by(JobHistory.started_at.desc())  # type: ignore
                .limit(limit)
            )
            
            jobs_with_connections = result.all()
            
            events = []
            for job, connection in jobs_with_connections:
                event_type = "sync_completed"
                if job.status == JobStatus.FAILED:  # type: ignore
                    event_type = "drift_detected"
                elif job.status == JobStatus.SUCCEEDED:  # type: ignore
                    event_type = "repair_success"
                elif job.status == JobStatus.RUNNING:  # type: ignore
                    event_type = "sync_running"
                
                events.append({
                    "id": str(job.id),
                    "connection_id": str(job.connection_id),
                    "connection_name": connection.name,
                    "source_type": connection.source_type,
                    "event_type": event_type,
                    "status": job.status.value,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "error_message": job.error_message,
                    "airbyte_job_id": job.airbyte_job_id
                })
            
            return {
                "events": events,
                "total": len(events),
                "data_source": "database"
            }
    
    except Exception as e:
        logger.error(f"Error fetching AAM events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch events: {str(e)}"
        )


@router.get("/connections")
async def get_aam_connections():
    """
    Get all AAM connections with their current status
    Returns list of all connections being monitored by AAM
    """
    if not AsyncSessionLocal or not AAM_MODELS_AVAILABLE:
        # Return mock data
        mock_connections = [
            {
                "id": "conn-1",
                "name": "Salesforce Production",
                "source_type": "Salesforce",
                "status": "ACTIVE",
                "created_at": (datetime.utcnow() - timedelta(days=30)).isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            },
            {
                "id": "conn-2",
                "name": "NetSuite ERP",
                "source_type": "NetSuite",
                "status": "ACTIVE",
                "created_at": (datetime.utcnow() - timedelta(days=25)).isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            },
            {
                "id": "conn-3",
                "name": "SAP Analytics",
                "source_type": "SAP",
                "status": "HEALING",
                "created_at": (datetime.utcnow() - timedelta(days=20)).isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            },
            {
                "id": "conn-4",
                "name": "Snowflake DW",
                "source_type": "Snowflake",
                "status": "ACTIVE",
                "created_at": (datetime.utcnow() - timedelta(days=15)).isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
        ]
        return {
            "connections": mock_connections,
            "total": len(mock_connections),
            "data_source": "mock"
        }
    
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Connection).order_by(Connection.created_at.desc())  # type: ignore
            )
            connections = result.scalars().all()
            
            connection_list = [
                {
                    "id": str(conn.id),
                    "name": conn.name,
                    "source_type": conn.source_type,
                    "status": conn.status.value,
                    "airbyte_source_id": str(conn.airbyte_source_id) if conn.airbyte_source_id else None,
                    "airbyte_connection_id": str(conn.airbyte_connection_id) if conn.airbyte_connection_id else None,
                    "created_at": conn.created_at.isoformat() if conn.created_at else None,
                    "updated_at": conn.updated_at.isoformat() if conn.updated_at else None
                }
                for conn in connections
            ]
            
            return {
                "connections": connection_list,
                "total": len(connection_list),
                "data_source": "database"
            }
    
    except Exception as e:
        logger.error(f"Error fetching AAM connections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch connections: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check for AAM monitoring API"""
    return {
        "status": "healthy",
        "service": "aam_monitoring",
        "timestamp": datetime.utcnow().isoformat()
    }
