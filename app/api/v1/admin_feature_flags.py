"""
Admin Feature Flag Management API

Endpoints for managing feature flags in production.
Requires authentication.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict

from app.security import get_current_user
from app.models import User
from shared.feature_flags import set_feature_flag, get_feature_flag, list_all_flags
from app.config.feature_flags import FeatureFlag

logger = logging.getLogger(__name__)

router = APIRouter()


class ToggleFlagRequest(BaseModel):
    """Request to toggle a feature flag"""
    flag_name: str
    enabled: bool
    tenant_id: str = "default"


class ToggleFlagResponse(BaseModel):
    """Response from toggling a feature flag"""
    success: bool
    flag_name: str
    enabled: bool
    tenant_id: str
    message: str


@router.post(
    "/feature-flags/toggle",
    response_model=ToggleFlagResponse,
    summary="Toggle a feature flag",
    description="Enable or disable a feature flag for a specific tenant"
)
async def toggle_feature_flag(
    request: ToggleFlagRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Toggle a feature flag on or off
    
    **Authentication Required**: Bearer token
    
    **Examples**:
    ```json
    {
      "flag_name": "USE_AAM_AS_SOURCE",
      "enabled": true,
      "tenant_id": "default"
    }
    ```
    """
    try:
        success = set_feature_flag(
            request.flag_name,
            request.enabled,
            request.tenant_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis unavailable - cannot set feature flag"
            )
        
        logger.info(
            f"User {current_user.email} toggled flag {request.flag_name}={request.enabled} "
            f"for tenant {request.tenant_id}"
        )
        
        return ToggleFlagResponse(
            success=True,
            flag_name=request.flag_name,
            enabled=request.enabled,
            tenant_id=request.tenant_id,
            message=f"Feature flag '{request.flag_name}' {'enabled' if request.enabled else 'disabled'} for tenant '{request.tenant_id}'"
        )
        
    except Exception as e:
        logger.error(f"Failed to toggle feature flag: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle feature flag: {str(e)}"
        )


@router.get(
    "/feature-flags",
    response_model=Dict[str, bool],
    summary="List all feature flags",
    description="Get current status of all feature flags for a tenant"
)
async def get_feature_flags(
    tenant_id: str = "default",
    current_user: User = Depends(get_current_user)
):
    """
    List all feature flags and their current status
    
    **Authentication Required**: Bearer token
    """
    try:
        flags = list_all_flags(tenant_id)
        
        logger.info(f"User {current_user.email} listed feature flags for tenant {tenant_id}")
        
        return flags
        
    except Exception as e:
        logger.error(f"Failed to list feature flags: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list feature flags: {str(e)}"
        )


@router.post(
    "/feature-flags/enable-aam",
    response_model=ToggleFlagResponse,
    summary="Enable AAM production connectors",
    description="Switch from legacy/mock data to real AAM connectors (Salesforce, MongoDB, FileSource, Supabase)"
)
async def enable_aam_connectors(
    tenant_id: str = "default",
    current_user: User = Depends(get_current_user)
):
    """
    Quick toggle to enable AAM production connectors
    
    **Authentication Required**: Bearer token
    
    This enables the USE_AAM_AS_SOURCE feature flag, which switches the platform
    from legacy file sources to real production AAM connectors:
    - Salesforce
    - MongoDB  
    - FileSource
    - Supabase
    """
    try:
        success = set_feature_flag(
            FeatureFlag.USE_AAM_AS_SOURCE.value,
            True,
            tenant_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis unavailable - cannot enable AAM"
            )
        
        logger.info(
            f"User {current_user.email} enabled AAM production connectors "
            f"for tenant {tenant_id}"
        )
        
        return ToggleFlagResponse(
            success=True,
            flag_name=FeatureFlag.USE_AAM_AS_SOURCE.value,
            enabled=True,
            tenant_id=tenant_id,
            message=f"✅ AAM production connectors enabled! Platform now uses real data from Salesforce, MongoDB, FileSource, and Supabase."
        )
        
    except Exception as e:
        logger.error(f"Failed to enable AAM: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable AAM: {str(e)}"
        )


@router.post(
    "/feature-flags/disable-aam",
    response_model=ToggleFlagResponse,
    summary="Disable AAM production connectors",
    description="Switch back to legacy/mock data sources"
)
async def disable_aam_connectors(
    tenant_id: str = "default",
    current_user: User = Depends(get_current_user)
):
    """
    Quick toggle to disable AAM production connectors (return to legacy mode)
    
    **Authentication Required**: Bearer token
    """
    try:
        success = set_feature_flag(
            FeatureFlag.USE_AAM_AS_SOURCE.value,
            False,
            tenant_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis unavailable - cannot disable AAM"
            )
        
        logger.info(
            f"User {current_user.email} disabled AAM production connectors "
            f"for tenant {tenant_id}"
        )
        
        return ToggleFlagResponse(
            success=True,
            flag_name=FeatureFlag.USE_AAM_AS_SOURCE.value,
            enabled=False,
            tenant_id=tenant_id,
            message=f"AAM production connectors disabled. Platform now uses legacy file sources."
        )
        
    except Exception as e:
        logger.error(f"Failed to disable AAM: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable AAM: {str(e)}"
        )
