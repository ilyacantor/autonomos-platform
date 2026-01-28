"""
AAM Connectors Module - Connector status and management endpoints

This module provides API endpoints for managing AAM connectors,
including listing connectors, viewing details, and triggering discovery.
"""
import logging
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Request, Depends
from sqlalchemy import select, func, and_, text
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_async_db, AsyncSessionLocal

# Import sync activity helpers from aam_sync
from app.api.v1.aam_sync import (
    get_airbyte_sync_activity,
    get_airbyte_sync_activity_async
)

logger = logging.getLogger(__name__)

router = APIRouter()


# OpenAPI DTOs for /aam/connectors endpoint
class ConnectorDTO(BaseModel):
    """Connector data transfer object with drift metadata and sync activity"""
    id: str = Field(..., description="Unique connector identifier")
    name: str = Field(..., description="Connector name")
    source_type: str = Field(..., description="Data source type (e.g., salesforce, filesource)")
    status: str = Field(..., description="Connection status (ACTIVE, PENDING, FAILED, etc.)")
    mapping_count: int = Field(..., description="Number of field mappings for this connector")
    last_event_type: Optional[str] = Field(None, description="Type of last drift event (e.g., DRIFT_DETECTED)")
    last_event_at: Optional[datetime] = Field(None, description="Timestamp of last drift event")
    has_drift: bool = Field(..., description="Whether connector has detected drift")
    last_sync_status: Optional[str] = Field(None, description="Status of most recent Airbyte sync (succeeded, failed, running)")
    last_sync_records: Optional[int] = Field(None, description="Number of records synced in last job")
    last_sync_bytes: Optional[int] = Field(None, description="Bytes transferred in last sync")
    last_sync_at: Optional[datetime] = Field(None, description="Timestamp of last sync job")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "10ca3a88-5105-4e24-b984-6e350a5fa443",
                "name": "FilesSource Demo",
                "source_type": "filesource",
                "status": "ACTIVE",
                "mapping_count": 36,
                "last_event_type": "DRIFT_DETECTED",
                "last_event_at": "2025-11-12T00:14:13Z",
                "has_drift": True,
                "last_sync_status": "succeeded",
                "last_sync_records": 245,
                "last_sync_bytes": 2177200,
                "last_sync_at": "2025-11-12T11:48:00Z"
            }
        }


class ConnectorsResponse(BaseModel):
    """Response model for GET /aam/connectors"""
    connectors: List[ConnectorDTO] = Field(..., description="List of connectors")
    total: int = Field(..., description="Total number of connectors")


# Feature flag: Use sync code path for connectors endpoint (default: true)
# Set AAM_CONNECTORS_SYNC=false to use async code path
AAM_CONNECTORS_SYNC = os.getenv("AAM_CONNECTORS_SYNC", "true").lower() in ("true", "1", "yes")

# Import AAM models - with fallback
AAM_MODELS_AVAILABLE = False
try:
    from aam_hybrid.shared.models import Connection, JobHistory, SyncCatalogVersion, ConnectionStatus, JobStatus
    AAM_MODELS_AVAILABLE = True
    logger.info("aam_connectors: AAM models imported successfully")
except Exception as e:
    logger.warning(f"aam_connectors: Could not import AAM models: {e}. Using fallback mode.")
    Connection = None  # type: ignore
    JobHistory = None  # type: ignore
    SyncCatalogVersion = None  # type: ignore
    ConnectionStatus = None  # type: ignore
    JobStatus = None  # type: ignore


def _serialize_connector(
    conn,
    mapping_count: int,
    drift_info: Optional[Dict[str, Any]] = None,
    sync_activity: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Shared serialization logic for connector objects with drift metadata and sync activity"""
    return {
        "id": str(conn.id),
        "name": conn.name,
        "source_type": conn.source_type,
        "status": conn.status.value if hasattr(conn.status, 'value') else conn.status,
        "last_discovery_at": conn.updated_at.isoformat() if conn.updated_at else None,
        "mapping_count": mapping_count,
        "last_event_type": drift_info.get("event_type") if drift_info else None,
        "last_event_at": drift_info["created_at"].isoformat() if drift_info and drift_info.get("created_at") else None,
        "has_drift": bool(drift_info) if drift_info else False,
        "last_sync_status": sync_activity.get("status") if sync_activity else None,
        "last_sync_records": sync_activity.get("records") if sync_activity else None,
        "last_sync_bytes": sync_activity.get("bytes") if sync_activity else None,
        "last_sync_at": sync_activity["timestamp"].isoformat() if sync_activity and sync_activity.get("timestamp") else None
    }


def _get_connectors_sync(tenant_id: str) -> Dict[str, Any]:
    """Sync implementation using psycopg2 (PgBouncer-safe)"""
    from app.models import MappingRegistry, DriftEvent
    from app.database import SessionLocal
    from sqlalchemy import func

    with SessionLocal() as db:
        # Set 3s statement timeout for this session
        db.execute(text("SET LOCAL statement_timeout='3s'"))

        # Filter connections by tenant_id for multi-tenant isolation
        connections = db.query(Connection).filter(
            Connection.tenant_id == tenant_id
        ).order_by(Connection.name).all()  # type: ignore

        if not connections:
            return {"connectors": [], "total": 0}

        connection_ids = [str(conn.id) for conn in connections]

        # Batched drift query: get latest drift event per connection using window function
        # Use raw SQL for window function compatibility across dialects
        drift_query = text("""
            SELECT DISTINCT ON (connection_id)
                connection_id, event_type, created_at
            FROM drift_events
            WHERE tenant_id = :tenant_id
                AND connection_id::text = ANY(:connection_ids)
            ORDER BY connection_id, created_at DESC
        """)

        drift_results = db.execute(
            drift_query,
            {"tenant_id": tenant_id, "connection_ids": connection_ids}
        ).fetchall()

        # Build drift lookup map
        drift_map = {
            str(row.connection_id): {
                "event_type": row.event_type,
                "created_at": row.created_at
            }
            for row in drift_results
        }

        connectors_list = []
        for conn in connections:
            mapping_count = db.query(func.count(MappingRegistry.id)).filter(
                and_(
                    MappingRegistry.tenant_id == tenant_id,
                    MappingRegistry.connection_id == conn.id
                )
            ).scalar() or 0

            drift_info = drift_map.get(str(conn.id))

            # Get Airbyte sync activity if connection has airbyte_connection_id
            sync_activity = None
            if hasattr(conn, 'airbyte_connection_id') and conn.airbyte_connection_id:
                sync_activity = get_airbyte_sync_activity(conn.airbyte_connection_id)

            connectors_list.append(_serialize_connector(conn, mapping_count, drift_info, sync_activity))

        return {
            "connectors": connectors_list,
            "total": len(connectors_list)
        }


async def _get_connectors_async(tenant_id: str) -> Dict[str, Any]:
    """Async implementation using asyncpg"""
    from app.models import MappingRegistry, DriftEvent

    async with AsyncSessionLocal() as db:
        conn_result = await db.execute(
            select(Connection).order_by(Connection.name)  # type: ignore
        )
        connections = conn_result.scalars().all()

        if not connections:
            return {"connectors": [], "total": 0}

        connection_ids = [str(conn.id) for conn in connections]

        # Batched drift query: get latest drift event per connection
        drift_query = text("""
            SELECT DISTINCT ON (connection_id)
                connection_id, event_type, created_at
            FROM drift_events
            WHERE tenant_id = :tenant_id
                AND connection_id::text = ANY(:connection_ids)
            ORDER BY connection_id, created_at DESC
        """)

        drift_results = await db.execute(
            drift_query,
            {"tenant_id": tenant_id, "connection_ids": connection_ids}
        )
        drift_rows = drift_results.fetchall()

        # Build drift lookup map
        drift_map = {
            str(row.connection_id): {
                "event_type": row.event_type,
                "created_at": row.created_at
            }
            for row in drift_rows
        }

        connectors_list = []
        for conn in connections:
            mapping_count_result = await db.execute(
                select(func.count(MappingRegistry.id))
                .where(
                    and_(
                        MappingRegistry.tenant_id == tenant_id,
                        MappingRegistry.connection_id == conn.id
                    )
                )
            )
            mapping_count = mapping_count_result.scalar() or 0

            drift_info = drift_map.get(str(conn.id))

            # Get Airbyte sync activity if connection has airbyte_connection_id
            sync_activity = None
            if hasattr(conn, 'airbyte_connection_id') and conn.airbyte_connection_id:
                sync_activity = await get_airbyte_sync_activity_async(conn.airbyte_connection_id)

            connectors_list.append(_serialize_connector(conn, mapping_count, drift_info, sync_activity))

        return {
            "connectors": connectors_list,
            "total": len(connectors_list)
        }


def _healthz_sync() -> Dict[str, bool]:
    """Sync health check using psycopg2 (PgBouncer-safe)"""
    from app.database import SessionLocal
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
        return {"ok": True}


async def _healthz_async() -> Dict[str, bool]:
    """Async health check using asyncpg"""
    async with AsyncSessionLocal() as db:
        await db.execute(text("SELECT 1"))
        return {"ok": True}


@router.get("/healthz")
async def healthz_aam():
    """
    Lightweight AAM health check

    Respects AAM_CONNECTORS_SYNC feature flag to test the same DB path
    used by /aam/connectors endpoint
    """
    try:
        if AAM_CONNECTORS_SYNC:
            result = _healthz_sync()
        else:
            result = await _healthz_async()
        return result
    except Exception as e:
        logger.error(f"AAM healthz failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AAM health check failed: {str(e)}"
        )


@router.get("/connectors", response_model=ConnectorsResponse)
async def get_connectors(request: Request):
    """
    Get all AAM connectors for the tenant with mapping counts and drift metadata

    Feature flag AAM_CONNECTORS_SYNC controls sync vs async implementation:
    - true (default): Use sync psycopg2 (PgBouncer-safe)
    - false: Use async asyncpg (may conflict with PgBouncer transaction mode)

    Returns:
        ConnectorsResponse: List of connectors with drift metadata
    """
    if not AAM_MODELS_AVAILABLE:
        logger.error("AAM: AAM models not available")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AAM models not configured"
        )

    tenant_id = getattr(request.state, "tenant_id", None)

    # DEMO MODE: Use fallback tenant UUID for unauthenticated/public access
    demo_mode = False
    if not tenant_id:
        from uuid import UUID
        demo_tenant_uuid = os.getenv("DEMO_TENANT_UUID", "f8ab4417-86a1-4dd2-a049-ea423063850e")
        tenant_id = UUID(demo_tenant_uuid) if isinstance(demo_tenant_uuid, str) else demo_tenant_uuid
        demo_mode = True
        logger.info(f"AAM list: DEMO MODE (unauthenticated), tenant_id={tenant_id}")
    else:
        logger.info(f"AAM list: authenticated, tenant_id={tenant_id}, mode={'sync' if AAM_CONNECTORS_SYNC else 'async'}")

    try:
        start_ms = time.time() * 1000

        if AAM_CONNECTORS_SYNC:
            # Sync path: psycopg2 (PgBouncer-safe)
            result = _get_connectors_sync(tenant_id)
        else:
            # Async path: asyncpg (may have PgBouncer issues)
            result = await _get_connectors_async(tenant_id)

        latency_ms = int(time.time() * 1000 - start_ms)

        # Log WARN if latency exceeds 3s threshold
        if latency_ms > 3000:
            logger.warning(f"AAM connectors list SLOW: tenant_id={tenant_id}, count={result['total']}, latency_ms={latency_ms} (threshold: 3000ms)")
        else:
            logger.info(f"AAM connectors list: tenant_id={tenant_id}, count={result['total']}, latency_ms={latency_ms}")

        return result

    except Exception as e:
        logger.error(f"Error fetching connectors: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch connectors: {str(e)}"
        )


@router.get("/connector_details")
async def get_connector_details(request: Request, db: Session = Depends(lambda: next(__import__('app.database').database.get_db()))):
    """
    Get detailed field-level mappings, drift events, and repair history for each connector
    Returns comprehensive connector intelligence similar to Ontology view
    """
    from app.models import MappingRegistry, DriftEvent, SchemaChange

    try:
        tenant_id = getattr(request.state, "tenant_id", None)
        if not tenant_id:
            logger.warning("AAM: missing tenant_id")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="missing tenant_id"
            )

        logger.info(f"AAM details: tenant_id={tenant_id}")

        # Query MappingRegistry grouped by vendor
        mappings = db.query(MappingRegistry).filter(MappingRegistry.tenant_id == tenant_id).all()

        # Group mappings by vendor
        vendor_mappings = {}
        for mapping in mappings:
            vendor = mapping.vendor or "unknown"
            if vendor not in vendor_mappings:
                vendor_mappings[vendor] = []
            vendor_mappings[vendor].append({
                "source_field": mapping.vendor_field,
                "canonical_field": mapping.canonical_field,
                "confidence": round(mapping.confidence, 2) if mapping.confidence else 0.0,
                "transform": mapping.coercion or "direct",
                "version": mapping.version
            })

        # Query recent drift events (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        drift_events = db.query(DriftEvent).filter(
            DriftEvent.tenant_id == tenant_id,
            DriftEvent.created_at >= seven_days_ago
        ).order_by(DriftEvent.created_at.desc()).all()

        # Group drift events by vendor
        vendor_drift = {}
        for event in drift_events:
            vendor = "unknown"
            if event.old_schema and isinstance(event.old_schema, dict):
                vendor = event.old_schema.get("source_type", "unknown")

            if vendor not in vendor_drift:
                vendor_drift[vendor] = []

            vendor_drift[vendor].append({
                "event_type": event.event_type or "unknown",
                "detected_at": event.created_at.isoformat() if event.created_at else None,
                "status": event.status or "unknown",
                "confidence": round(event.confidence, 2) if event.confidence else 0.0,
                "old_schema": event.old_schema,
                "new_schema": event.new_schema
            })

        # Query schema changes (repair history)
        schema_changes = db.query(SchemaChange).filter(
            SchemaChange.tenant_id == tenant_id
        ).order_by(SchemaChange.applied_at.desc()).limit(50).all()

        # Group repairs by vendor
        vendor_repairs = {}
        for change in schema_changes:
            vendor = "unknown"
            if change.details and isinstance(change.details, dict):
                vendor = change.details.get("vendor", "unknown")

            if vendor not in vendor_repairs:
                vendor_repairs[vendor] = []

            vendor_repairs[vendor].append({
                "change_type": change.change_type,
                "applied_at": change.applied_at.isoformat() if change.applied_at else None,
                "details": change.details
            })

        # Build connector list
        connectors = []
        all_vendors = set(list(vendor_mappings.keys()) + list(vendor_drift.keys()) + list(vendor_repairs.keys()))

        for vendor in all_vendors:
            vendor_mapping_list = vendor_mappings.get(vendor, [])
            high_confidence_count = sum(1 for m in vendor_mapping_list if m["confidence"] >= 0.9)

            connectors.append({
                "vendor": vendor,
                "status": "ACTIVE",
                "total_mappings": len(vendor_mapping_list),
                "high_confidence_mappings": high_confidence_count,
                "field_mappings": vendor_mapping_list[:20],  # Limit to 20 for display
                "recent_drift_events": vendor_drift.get(vendor, [])[:10],
                "repair_history": vendor_repairs.get(vendor, [])[:10]
            })

        return {
            "connectors": connectors,
            "data_source": "database"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in connector_details endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch connector details: {str(e)}"
        )


@router.get("/connections")
async def get_aam_connections():
    """
    Get all AAM connections with their current status
    Returns list of all connections being monitored by AAM
    """
    if not AAM_MODELS_AVAILABLE:
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
        # Return mock data on database error instead of raising exception
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
            "data_source": "mock_fallback"
        }


@router.post("/connectors/{connector_id}/discover")
async def trigger_discovery(connector_id: str, request: Request):
    """
    Trigger schema discovery for a specific connector
    Returns job_id for tracking progress
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        logger.warning("AAM: missing tenant_id")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing tenant_id"
        )

    # TODO: Implement actual discovery job queue
    # For now, return a stub job_id
    import uuid
    job_id = str(uuid.uuid4())

    logger.info(f"AAM: Discovery triggered for connector {connector_id} (tenant: {tenant_id})")

    return {
        "job_id": job_id,
        "connector_id": connector_id,
        "status": "queued",
        "message": "Discovery job queued (stub implementation)"
    }


@router.get("/discovery/jobs/{job_id}")
async def get_discovery_job(job_id: str, request: Request):
    """
    Get status of a discovery job
    Returns job status: queued|running|done|error
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        logger.warning("AAM: missing tenant_id")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing tenant_id"
        )

    # TODO: Implement actual job tracking
    # For now, return stub status
    return {
        "job_id": job_id,
        "status": "done",
        "message": "Discovery job completed (stub implementation)"
    }


@router.get("/debug/state")
async def get_debug_state(request: Request):
    """
    Read-only debug endpoint to verify AAM state without changing data
    Returns connections and mapping counts per connector (tenant-scoped)
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        logger.warning("AAM: missing tenant_id")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing tenant_id"
        )

    if not AAM_MODELS_AVAILABLE:
        return {
            "error": "AAM models not configured",
            "connections": [],
            "mappings_by_connector": {}
        }

    try:
        async with AsyncSessionLocal() as db:
            from app.models import MappingRegistry
            from sqlalchemy import func

            # Get all connections (no tenant filter on connections table)
            conn_result = await db.execute(select(Connection))  # type: ignore
            connections = conn_result.scalars().all()

            conn_list = [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "type": c.source_type,
                    "status": c.status.value if hasattr(c.status, 'value') else c.status,
                    "created_at": c.created_at.isoformat() if c.created_at else None
                }
                for c in connections
            ]

            # Get mapping counts by connector (tenant-scoped)
            mapping_result = await db.execute(
                select(
                    MappingRegistry.vendor,
                    func.count(MappingRegistry.id).label('count')
                )
                .where(MappingRegistry.tenant_id == tenant_id)
                .group_by(MappingRegistry.vendor)
            )

            mappings_by_connector = {row.vendor: row.count for row in mapping_result}

            return {
                "connections": conn_list,
                "mappings_by_connector": mappings_by_connector,
                "tenant_id": tenant_id
            }

    except Exception as e:
        logger.error(f"Error in debug/state endpoint: {e}")
        return {
            "error": str(e),
            "connections": [],
            "mappings_by_connector": {}
        }
