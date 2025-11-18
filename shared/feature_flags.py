"""
Tenant-scoped feature flag management for AutonomOS.

This module provides functional API for feature flags with:
- Tenant isolation (per-tenant flags)
- Percentage rollout support (gradual feature enablement)
- Redis-backed persistence
- Fallback to global/default flags

Usage:
    from shared.feature_flags import set_feature_flag, get_feature_flag
    
    # Set flag for tenant
    set_feature_flag("USE_DCL_MAPPING_REGISTRY", True, tenant_id="acme-corp")
    
    # Get flag for tenant
    enabled = get_feature_flag("USE_DCL_MAPPING_REGISTRY", tenant_id="acme-corp")
    
    # Percentage rollout
    set_feature_flag_percentage("USE_DCL_MAPPING_REGISTRY", 50, tenant_id="default")
    is_enabled = is_feature_enabled_for_user("USE_DCL_MAPPING_REGISTRY", "user123")
"""

import hashlib
import logging
from typing import Optional
from shared.redis_client import get_redis_client

logger = logging.getLogger(__name__)


def set_feature_flag(flag_name: str, enabled: bool, tenant_id: str = "default") -> bool:
    """
    Set feature flag value in Redis for a specific tenant.
    
    Args:
        flag_name: Name of the feature flag (e.g., "USE_DCL_MAPPING_REGISTRY")
        enabled: True to enable, False to disable
        tenant_id: Tenant identifier (default: "default")
    
    Returns:
        True if successfully set, False if Redis unavailable
    
    Example:
        >>> set_feature_flag("USE_DCL_MAPPING_REGISTRY", True, "acme-corp")
        True
    """
    redis = get_redis_client()
    if redis is None:
        logger.warning(f"Redis unavailable, cannot set feature flag {flag_name}")
        return False
    
    try:
        key = f"feature_flag:{flag_name}:{tenant_id}"
        value = "1" if enabled else "0"
        redis.set(key, value)
        logger.info(f"Set feature flag: {flag_name}={enabled} for tenant={tenant_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to set feature flag {flag_name}: {e}")
        return False


def get_feature_flag(flag_name: str, tenant_id: str = "default") -> bool:
    """
    Get feature flag value from Redis for a specific tenant.
    
    Falls back to "default" tenant if tenant-specific flag not found.
    Returns False if flag not set in Redis.
    
    Args:
        flag_name: Name of the feature flag
        tenant_id: Tenant identifier (default: "default")
    
    Returns:
        True if enabled, False otherwise
    
    Example:
        >>> get_feature_flag("USE_DCL_MAPPING_REGISTRY", "acme-corp")
        True
    """
    redis = get_redis_client()
    if redis is None:
        logger.warning(f"Redis unavailable, returning False for feature flag {flag_name}")
        return False
    
    try:
        key = f"feature_flag:{flag_name}:{tenant_id}"
        value = redis.get(key)
        
        if value is None:
            if tenant_id != "default":
                logger.debug(f"Flag {flag_name} not found for tenant {tenant_id}, checking default tenant")
                return get_feature_flag(flag_name, "default")
            
            logger.debug(f"Flag {flag_name} not set, returning False (default)")
            return False
        
        if isinstance(value, bytes):
            value = value.decode()
        
        return value == "1"
    except Exception as e:
        logger.error(f"Failed to get feature flag {flag_name}: {e}")
        return False


def set_feature_flag_percentage(flag_name: str, percentage: int, tenant_id: str = "default") -> bool:
    """
    Set feature flag with percentage rollout (0-100).
    
    Enables gradual rollout to a percentage of users based on consistent hashing.
    
    Args:
        flag_name: Name of the feature flag
        percentage: Percentage of users to enable (0-100)
        tenant_id: Tenant identifier (default: "default")
    
    Returns:
        True if successfully set, False if Redis unavailable
    
    Raises:
        ValueError: If percentage not in range 0-100
    
    Example:
        >>> set_feature_flag_percentage("USE_DCL_MAPPING_REGISTRY", 50, "default")
        True
    """
    if not 0 <= percentage <= 100:
        raise ValueError(f"Percentage must be 0-100, got {percentage}")
    
    redis = get_redis_client()
    if redis is None:
        logger.warning(f"Redis unavailable, cannot set percentage for {flag_name}")
        return False
    
    try:
        key = f"feature_flag:{flag_name}:{tenant_id}:percentage"
        redis.set(key, str(percentage))
        logger.info(f"Set feature flag percentage: {flag_name}={percentage}% for tenant={tenant_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to set feature flag percentage {flag_name}: {e}")
        return False


def get_feature_flag_percentage(flag_name: str, tenant_id: str = "default") -> Optional[int]:
    """
    Get current percentage rollout value for a feature flag.
    
    Args:
        flag_name: Name of the feature flag
        tenant_id: Tenant identifier (default: "default")
    
    Returns:
        Percentage (0-100) if set, None if not set
    
    Example:
        >>> get_feature_flag_percentage("USE_DCL_MAPPING_REGISTRY", "default")
        50
    """
    redis = get_redis_client()
    if redis is None:
        return None
    
    try:
        key = f"feature_flag:{flag_name}:{tenant_id}:percentage"
        value = redis.get(key)
        
        if value is None:
            return None
        
        if isinstance(value, bytes):
            value = value.decode()
        
        return int(value)
    except Exception as e:
        logger.error(f"Failed to get percentage for {flag_name}: {e}")
        return None


def is_feature_enabled_for_user(flag_name: str, user_id: str, tenant_id: str = "default") -> bool:
    """
    Check if feature is enabled for a specific user (supports percentage rollout).
    
    Uses consistent hashing to ensure the same user always gets the same result
    for a given percentage value.
    
    Args:
        flag_name: Name of the feature flag
        user_id: User identifier for consistent hashing
        tenant_id: Tenant identifier (default: "default")
    
    Returns:
        True if enabled for this user, False otherwise
    
    Example:
        >>> set_feature_flag_percentage("USE_DCL_MAPPING_REGISTRY", 50, "default")
        >>> is_feature_enabled_for_user("USE_DCL_MAPPING_REGISTRY", "user123")
        True  # ~50% of users will get True
    """
    redis = get_redis_client()
    if redis is None:
        return False
    
    try:
        percentage_key = f"feature_flag:{flag_name}:{tenant_id}:percentage"
        percentage_value = redis.get(percentage_key)
        
        if percentage_value is None:
            return get_feature_flag(flag_name, tenant_id)
        
        if isinstance(percentage_value, bytes):
            percentage_value = percentage_value.decode()
        
        percentage = int(percentage_value)
        
        if percentage == 0:
            return False
        if percentage == 100:
            return True
        
        user_hash = int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16)
        return (user_hash % 100) < percentage
    except Exception as e:
        logger.error(f"Failed to check feature for user {user_id}: {e}")
        return False


def clear_feature_flag(flag_name: str, tenant_id: str = "default") -> bool:
    """
    Clear/delete a feature flag and its percentage setting from Redis.
    
    Args:
        flag_name: Name of the feature flag
        tenant_id: Tenant identifier (default: "default")
    
    Returns:
        True if successfully cleared, False if Redis unavailable
    
    Example:
        >>> clear_feature_flag("USE_DCL_MAPPING_REGISTRY", "acme-corp")
        True
    """
    redis = get_redis_client()
    if redis is None:
        logger.warning(f"Redis unavailable, cannot clear feature flag {flag_name}")
        return False
    
    try:
        flag_key = f"feature_flag:{flag_name}:{tenant_id}"
        percentage_key = f"feature_flag:{flag_name}:{tenant_id}:percentage"
        
        redis.delete(flag_key, percentage_key)
        logger.info(f"Cleared feature flag: {flag_name} for tenant={tenant_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to clear feature flag {flag_name}: {e}")
        return False


def list_all_flags(tenant_id: str = "default") -> dict:
    """
    List all feature flags for a specific tenant.
    
    Args:
        tenant_id: Tenant identifier (default: "default")
    
    Returns:
        Dictionary mapping flag names to their values
    
    Example:
        >>> list_all_flags("default")
        {"USE_DCL_MAPPING_REGISTRY": True, "USE_AAM_AS_SOURCE": False}
    """
    redis = get_redis_client()
    if redis is None:
        return {}
    
    try:
        pattern = f"feature_flag:*:{tenant_id}"
        keys = redis.keys(pattern)
        
        flags = {}
        for key in keys:
            if isinstance(key, bytes):
                key = key.decode()
            
            if key.endswith(":percentage"):
                continue
            
            parts = key.split(":")
            if len(parts) >= 3:
                flag_name = parts[1]
                value = redis.get(key)
                
                if isinstance(value, bytes):
                    value = value.decode()
                
                flags[flag_name] = (value == "1")
        
        return flags
    except Exception as e:
        logger.error(f"Failed to list flags for tenant {tenant_id}: {e}")
        return {}
