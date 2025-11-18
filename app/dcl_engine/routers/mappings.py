"""
DCL Mapping Registry API Router
RACI Phase 1 - Mapping registry access with Redis caching, PostgreSQL backend, JWT auth

Provides 3 endpoints:
1. GET /dcl/mappings/{connector}/{source_table}/{source_field} - Get single mapping
2. GET /dcl/mappings/{connector} - List all mappings for connector
3. POST /dcl/mappings - Create/update mapping (admin only)
"""
import json
import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import FieldMapping, ConnectorDefinition, EntitySchema, User
from app.security import get_current_user
from app.schemas.mapping import (
    MappingResponse,
    MappingListResponse,
    MappingSummary,
    MappingCreateRequest,
    MappingCreateResponse
)
from shared.redis_client import get_redis_client

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_connector_by_name(db: Session, tenant_id: UUID, connector_name: str) -> Optional[ConnectorDefinition]:
    """
    Helper function to get connector definition by name
    
    Args:
        db: Database session
        tenant_id: Tenant ID for isolation
        connector_name: Connector name (e.g., 'salesforce')
    
    Returns:
        ConnectorDefinition or None
    """
    return db.query(ConnectorDefinition).filter(
        ConnectorDefinition.tenant_id == tenant_id,
        ConnectorDefinition.connector_name == connector_name,
        ConnectorDefinition.status == 'active'
    ).first()


def _mapping_to_response(mapping: FieldMapping, connector_name: str) -> dict:
    """
    Convert FieldMapping ORM object to API response dict
    
    Args:
        mapping: FieldMapping ORM object
        connector_name: Connector name string
    
    Returns:
        Dict matching MappingResponse schema
    """
    return {
        "mapping_id": mapping.id,
        "connector_id": connector_name,
        "source_table": mapping.source_table,
        "source_field": mapping.source_field,
        "canonical_entity": mapping.canonical_entity,
        "canonical_field": mapping.canonical_field,
        "confidence": mapping.confidence_score,
        "mapping_type": mapping.mapping_type,
        "transform_expr": mapping.transformation_rule,
        "metadata": {
            "source_data_type": mapping.source_data_type,
            "canonical_data_type": mapping.canonical_data_type,
            "validation_status": mapping.validation_status,
            "mapping_source": mapping.mapping_source,
            "version": mapping.version
        },
        "created_at": mapping.created_at,
        "updated_at": mapping.updated_at
    }


def _invalidate_mapping_cache(tenant_id: UUID, connector_name: str, source_table: str, source_field: str) -> bool:
    """
    Invalidate Redis cache for a specific mapping
    
    Args:
        tenant_id: Tenant ID
        connector_name: Connector name
        source_table: Source table
        source_field: Source field
    
    Returns:
        True if cache was invalidated, False if Redis unavailable
    """
    redis = get_redis_client()
    if not redis:
        logger.warning("Redis unavailable - cache invalidation skipped")
        return False
    
    try:
        cache_key = f"mapping:{tenant_id}:{connector_name}:{source_table}:{source_field}"
        redis.delete(cache_key)
        
        # Also invalidate list cache for this connector
        list_cache_pattern = f"mapping_list:{tenant_id}:{connector_name}:*"
        cursor = 0
        while True:
            cursor, keys = redis.scan(cursor, match=list_cache_pattern, count=100)
            if keys:
                redis.delete(*keys)
            if cursor == 0:
                break
        
        logger.info(f"Cache invalidated for {cache_key}")
        return True
    except Exception as e:
        logger.error(f"Cache invalidation failed: {e}")
        return False


@router.get("/mappings/{connector}/{source_table}/{source_field}", response_model=MappingResponse)
async def get_field_mapping(
    connector: str,
    source_table: str,
    source_field: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get single field mapping with Redis caching
    
    Args:
        connector: Connector name (e.g., 'salesforce')
        source_table: Source table name
        source_field: Source field name
        current_user: Authenticated user (JWT)
        db: Database session
    
    Returns:
        MappingResponse with mapping details
    
    Raises:
        404: Mapping not found
        500: Database/Redis error
    """
    try:
        tenant_id = current_user.tenant_id
        
        # 1. Check Redis cache first
        redis = get_redis_client()
        if redis:
            cache_key = f"mapping:{tenant_id}:{connector}:{source_table}:{source_field}"
            try:
                cached = redis.get(cache_key)
                if cached:
                    logger.debug(f"Cache HIT for {cache_key}")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")
        
        # 2. Get connector definition
        connector_def = _get_connector_by_name(db, tenant_id, connector)
        if not connector_def:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector '{connector}' not found for tenant"
            )
        
        # 3. Query database for mapping
        mapping = db.query(FieldMapping).filter(
            FieldMapping.tenant_id == tenant_id,
            FieldMapping.connector_id == connector_def.id,
            FieldMapping.source_table == source_table,
            FieldMapping.source_field == source_field,
            FieldMapping.status == 'active'
        ).first()
        
        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": f"No mapping found for {connector}.{source_table}.{source_field}",
                    "suggestion": "Use POST /dcl/rag/propose-mapping for AI-suggested mapping"
                }
            )
        
        # 4. Convert to response dict
        result = _mapping_to_response(mapping, connector)
        
        # 5. Cache result with 5 minute TTL
        if redis:
            try:
                redis.setex(cache_key, 300, json.dumps(result, default=str))
                logger.debug(f"Cached mapping for {cache_key} (300s TTL)")
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching mapping: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error fetching mapping: {str(e)}"
        )


@router.get("/mappings/{connector}", response_model=MappingListResponse)
async def list_connector_mappings(
    connector: str,
    source_table: Optional[str] = Query(None, description="Filter by source table"),
    canonical_entity: Optional[str] = Query(None, description="Filter by canonical entity"),
    limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all mappings for a connector with optional filters
    
    Args:
        connector: Connector name (e.g., 'salesforce')
        source_table: Optional filter by source table
        canonical_entity: Optional filter by canonical entity
        limit: Max records to return (default 100, max 1000)
        offset: Pagination offset
        current_user: Authenticated user (JWT)
        db: Database session
    
    Returns:
        MappingListResponse with paginated mappings
    
    Raises:
        404: Connector not found
        500: Database error
    """
    try:
        tenant_id = current_user.tenant_id
        
        # 1. Get connector definition
        connector_def = _get_connector_by_name(db, tenant_id, connector)
        if not connector_def:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector '{connector}' not found for tenant"
            )
        
        # 2. Build query with filters
        query = db.query(FieldMapping).filter(
            FieldMapping.tenant_id == tenant_id,
            FieldMapping.connector_id == connector_def.id,
            FieldMapping.status == 'active'
        )
        
        if source_table:
            query = query.filter(FieldMapping.source_table == source_table)
        
        if canonical_entity:
            query = query.filter(FieldMapping.canonical_entity == canonical_entity)
        
        # 3. Get total count and paginated results
        total_count = query.count()
        mappings = query.order_by(FieldMapping.created_at.desc()).offset(offset).limit(limit).all()
        
        # 4. Convert to summary dicts
        mapping_summaries = [
            MappingSummary(
                mapping_id=m.id,
                source_table=m.source_table,
                source_field=m.source_field,
                canonical_entity=m.canonical_entity,
                canonical_field=m.canonical_field,
                confidence=m.confidence_score,
                mapping_type=m.mapping_type
            )
            for m in mappings
        ]
        
        return MappingListResponse(
            connector_id=connector,
            total_count=total_count,
            mappings=mapping_summaries
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing mappings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error listing mappings: {str(e)}"
        )


@router.post("/mappings", response_model=MappingCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_mapping(
    request: MappingCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create or update field mapping (admin only)
    
    Args:
        request: Mapping creation request
        current_user: Authenticated user (JWT)
        db: Database session
    
    Returns:
        MappingCreateResponse with created mapping ID
    
    Raises:
        403: User is not admin
        404: Connector or entity not found
        422: Invalid request data
        500: Database error
    """
    try:
        tenant_id = current_user.tenant_id
        
        # 1. Admin-only check
        is_admin = getattr(current_user, 'is_admin', False)
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required to create/update mappings"
            )
        
        # 2. Get connector definition
        connector_def = _get_connector_by_name(db, tenant_id, request.connector_id)
        if not connector_def:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connector '{request.connector_id}' not found for tenant"
            )
        
        # 3. Get or create entity schema
        entity_schema = db.query(EntitySchema).filter(
            EntitySchema.entity_name == request.canonical_entity
        ).first()
        
        if not entity_schema:
            # Create minimal entity schema if it doesn't exist
            entity_schema = EntitySchema(
                entity_name=request.canonical_entity,
                entity_version='1.0.0',
                schema_definition={
                    "type": "object",
                    "properties": {
                        request.canonical_field: {"type": "string"}
                    }
                },
                description=f"Auto-created schema for {request.canonical_entity}"
            )
            db.add(entity_schema)
            db.flush()  # Get the ID without committing
        
        # 4. Check if mapping already exists (upsert logic)
        existing_mapping = db.query(FieldMapping).filter(
            FieldMapping.tenant_id == tenant_id,
            FieldMapping.connector_id == connector_def.id,
            FieldMapping.source_table == request.source_table,
            FieldMapping.source_field == request.source_field,
            FieldMapping.canonical_entity == request.canonical_entity,
            FieldMapping.canonical_field == request.canonical_field
        ).first()
        
        if existing_mapping:
            # Update existing mapping
            existing_mapping.confidence_score = request.confidence
            existing_mapping.mapping_type = request.mapping_type
            existing_mapping.transformation_rule = request.transform_expr
            # Only set updated_by if user exists in database (not MockUser)
            if hasattr(current_user, '__class__') and current_user.__class__.__name__ != 'MockUser':
                existing_mapping.updated_by = current_user.id
            existing_mapping.version = existing_mapping.version + 1
            
            db.commit()
            db.refresh(existing_mapping)
            
            mapping_id = existing_mapping.id
            response_status = "updated"
        else:
            # Create new mapping
            # Only set created_by/updated_by if user exists in database (not MockUser)
            user_id = None
            if hasattr(current_user, '__class__') and current_user.__class__.__name__ != 'MockUser':
                user_id = current_user.id
            
            new_mapping = FieldMapping(
                tenant_id=tenant_id,
                connector_id=connector_def.id,
                entity_schema_id=entity_schema.id,
                source_table=request.source_table,
                source_field=request.source_field,
                canonical_entity=request.canonical_entity,
                canonical_field=request.canonical_field,
                mapping_type=request.mapping_type,
                transformation_rule=request.transform_expr,
                confidence_score=request.confidence,
                mapping_source='manual',
                status='active',
                created_by=user_id,
                updated_by=user_id
            )
            
            db.add(new_mapping)
            db.commit()
            db.refresh(new_mapping)
            
            mapping_id = new_mapping.id
            response_status = "created"
        
        # 5. Invalidate cache
        cache_invalidated = _invalidate_mapping_cache(
            tenant_id, request.connector_id, request.source_table, request.source_field
        )
        
        logger.info(f"Mapping {response_status}: {mapping_id} by user {current_user.id}")
        
        return MappingCreateResponse(
            mapping_id=mapping_id,
            status=response_status,
            cache_invalidated=cache_invalidated
        )
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating mapping: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error creating mapping: {str(e)}"
        )
