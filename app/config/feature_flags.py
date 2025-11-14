"""
Feature Flag Configuration for AutonomOS Architecture Restructuring

This module provides centralized feature flag management for progressive
rollout of the new Data Sources → AAM → DCL → Agents architecture.

Feature flags allow safe, incremental migration without breaking existing functionality.

PRODUCTION-GRADE REDIS-BACKED IMPLEMENTATION:
- Precedence: ENV variable > Redis stored value > hardcoded default
- Cross-worker consistency via shared Redis
- Pub/sub broadcasts for cache invalidation
- Restart persistence via Redis storage
"""

from typing import Dict, Any, Optional
import os
import json
import time
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class FeatureFlag(str, Enum):
    """Available feature flags for AutonomOS"""
    
    USE_AAM_AS_SOURCE = "USE_AAM_AS_SOURCE"
    ENABLE_DRIFT_DETECTION = "ENABLE_DRIFT_DETECTION"
    ENABLE_AUTO_REPAIR = "ENABLE_AUTO_REPAIR"
    ENABLE_HITL_WORKFLOW = "ENABLE_HITL_WORKFLOW"
    ENABLE_CANONICAL_EVENTS = "ENABLE_CANONICAL_EVENTS"
    ENABLE_SCHEMA_FINGERPRINTING = "ENABLE_SCHEMA_FINGERPRINTING"


class FeatureFlagConfig:
    """
    Production-grade feature flag configuration with Redis-backed multi-worker support.
    
    PRECEDENCE MODEL (highest to lowest):
    1. Environment variable (FEATURE_<FLAG_NAME>)
    2. Redis stored value (feature_flags:<FLAG_NAME>)
    3. Hardcoded default value
    
    Default Values (All False for backward compatibility):
    - USE_AAM_AS_SOURCE: Route DCL data through AAM connectors
    - ENABLE_DRIFT_DETECTION: Monitor schema changes in AAM connectors
    - ENABLE_AUTO_REPAIR: Automatically repair low-confidence mappings
    - ENABLE_HITL_WORKFLOW: Require human approval for repairs <90% confidence
    - ENABLE_CANONICAL_EVENTS: Use canonical event normalization
    - ENABLE_SCHEMA_FINGERPRINTING: Track schema versions for drift detection
    
    Environment Variables:
    - Set to "true", "1", "yes" to enable
    - Example: FEATURE_USE_AAM_AS_SOURCE=true
    
    Redis Integration:
    - Keys: feature_flags:<FLAG_NAME>
    - Values: "true" or "false" (string format)
    - Pub/Sub Channel: dcl:feature_flags
    """
    
    # Hardcoded defaults (lowest precedence)
    _defaults: Dict[str, bool] = {
        FeatureFlag.USE_AAM_AS_SOURCE: False,  # Default: False (Legacy demo files) - Toggle to True for AAM connectors (Salesforce, MongoDB, FilesSource)
        FeatureFlag.ENABLE_DRIFT_DETECTION: True,  # Phase 4: ENABLED - Detect schema drift in AAM connectors
        FeatureFlag.ENABLE_AUTO_REPAIR: True,  # Phase 4: ENABLED (Task 8) - Auto-repair with 3-tier confidence scoring
        FeatureFlag.ENABLE_HITL_WORKFLOW: True,
        FeatureFlag.ENABLE_CANONICAL_EVENTS: True,  # Phase 4: ENABLED - Normalize and validate canonical events
        FeatureFlag.ENABLE_SCHEMA_FINGERPRINTING: True,  # Phase 4: ENABLED - Track schema versions for drift
    }
    
    # Redis client (injected from main app)
    _redis_client: Optional[Any] = None
    
    # Redis key prefix for feature flags
    _redis_prefix = "feature_flags:"
    
    # Pub/sub channel for flag changes
    _pubsub_channel = "dcl:feature_flags"
    
    @classmethod
    def set_redis_client(cls, redis_client: Any) -> None:
        """
        Inject Redis client for cross-worker flag persistence.
        Called from main app during startup.
        
        Args:
            redis_client: Redis client instance (with decode_responses=True or wrapper)
        """
        cls._redis_client = redis_client
        print(f"✅ FeatureFlagConfig: Redis client initialized")
    
    @classmethod
    def _get_redis_key(cls, flag: FeatureFlag) -> str:
        """Generate Redis key for a feature flag"""
        return f"{cls._redis_prefix}{flag.value}"
    
    @classmethod
    def _retry_with_backoff(cls, operation, max_retries: int = 3, initial_delay: float = 0.5) -> Any:
        """
        Execute a Redis operation with exponential backoff retry logic.
        
        Args:
            operation: Function to execute
            max_retries: Maximum number of retry attempts (default: 3)
            initial_delay: Initial delay in seconds before first retry (default: 0.5s)
            
        Returns:
            Result of successful operation execution
            
        Raises:
            Exception: Last exception after all retries exhausted
        """
        delay = initial_delay
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return operation()
            except Exception as e:
                last_exception = e
                
                if attempt < max_retries - 1:
                    logger.warning(
                        f"⚠️ Redis operation failed (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    
                    # Exponential backoff
                    delay = min(delay * 2, 5.0)  # Cap at 5 seconds
                else:
                    logger.error(
                        f"❌ Redis operation failed after {max_retries} attempts: {e}"
                    )
        
        raise last_exception
    
    @classmethod
    def _get_from_redis(cls, flag: FeatureFlag) -> Optional[bool]:
        """
        Read flag value from Redis with retry logic.
        
        Returns:
            True/False if value exists in Redis, None if not found or Redis unavailable
        """
        if not cls._redis_client:
            return None
        
        def read_operation():
            key = cls._get_redis_key(flag)
            value = cls._redis_client.get(key)
            if value is None:
                return None
            
            # Handle both bytes and string responses
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            
            return value.lower() == "true"
        
        try:
            return cls._retry_with_backoff(read_operation, max_retries=3)
        except Exception as e:
            logger.error(
                f"⚠️ FeatureFlagConfig: Redis read failed after retries for {flag.value}: {e}. "
                "Falling back to hardcoded default."
            )
            return None
    
    @classmethod
    def _set_to_redis(cls, flag: FeatureFlag, enabled: bool) -> bool:
        """
        Write flag value to Redis with retry logic (persistent storage).
        
        Args:
            flag: Feature flag to set
            enabled: New value
            
        Returns:
            True if successful, False otherwise
        """
        if not cls._redis_client:
            logger.warning(f"⚠️ FeatureFlagConfig: Redis not available, cannot persist {flag.value}")
            return False
        
        def write_operation():
            key = cls._get_redis_key(flag)
            value = "true" if enabled else "false"
            cls._redis_client.set(key, value)
            return True
        
        try:
            return cls._retry_with_backoff(write_operation, max_retries=3)
        except Exception as e:
            logger.error(
                f"⚠️ FeatureFlagConfig: Redis write failed after retries for {flag.value}: {e}. "
                "Flag change will NOT persist across restarts."
            )
            return False
    
    @classmethod
    def _publish_change(cls, flag: FeatureFlag, enabled: bool) -> None:
        """
        Publish flag change to Redis pub/sub with retry logic for cross-worker cache invalidation.
        
        Args:
            flag: Feature flag that changed
            enabled: New value
        """
        if not cls._redis_client:
            return
        
        def publish_operation():
            message = json.dumps({
                "flag": flag.value,
                "value": enabled,
                "timestamp": os.times().elapsed
            })
            
            # Get underlying Redis client if using wrapper
            redis = cls._redis_client
            if hasattr(redis, '_client'):
                redis = redis._client
            
            redis.publish(cls._pubsub_channel, message)
            logger.info(f"📡 Published flag change: {flag.value}={enabled}")
            return True
        
        try:
            cls._retry_with_backoff(publish_operation, max_retries=3)
        except Exception as e:
            logger.error(
                f"⚠️ FeatureFlagConfig: Pub/sub publish failed after retries: {e}. "
                "Other workers may not receive flag change notification."
            )
    
    @classmethod
    def is_enabled(cls, flag: FeatureFlag) -> bool:
        """
        Check if a feature flag is enabled using precedence model:
        1. Environment variable (highest priority)
        2. Redis stored value (persists across restarts)
        3. Hardcoded default (fallback)
        
        Args:
            flag: The feature flag to check
            
        Returns:
            True if enabled, False otherwise
            
        Example:
            >>> if FeatureFlagConfig.is_enabled(FeatureFlag.USE_AAM_AS_SOURCE):
            ...     # Use AAM-backed data path
        """
        # Level 1: Check environment variable (highest precedence)
        env_var = f"FEATURE_{flag.value}"
        env_value = os.getenv(env_var, "").lower()
        
        if env_value in ("true", "1", "yes"):
            return True
        elif env_value in ("false", "0", "no"):
            return False
        
        # Level 2: Check Redis stored value (persists across restarts)
        redis_value = cls._get_from_redis(flag)
        if redis_value is not None:
            return redis_value
        
        # Level 3: Use hardcoded default (fallback)
        return cls._defaults.get(flag, False)
    
    @classmethod
    def set_flag(cls, flag: FeatureFlag, enabled: bool, publish: bool = True) -> None:
        """
        Set a feature flag value (writes to Redis for persistence).
        
        Args:
            flag: The feature flag to set
            enabled: True to enable, False to disable
            publish: Whether to publish change to pub/sub (default: True)
            
        Note:
            - Writes to Redis for cross-worker persistence
            - Publishes to pub/sub for cache invalidation (if publish=True)
            - Environment variables still take precedence over this value
        """
        # Write to Redis for persistence
        success = cls._set_to_redis(flag, enabled)
        
        if success and publish:
            # Publish to pub/sub for cross-worker cache invalidation
            cls._publish_change(flag, enabled)
    
    @classmethod
    def get_all_flags(cls) -> Dict[str, bool]:
        """
        Get current state of all feature flags.
        
        Returns:
            Dictionary mapping flag names to their current state
        """
        return {
            flag.value: cls.is_enabled(flag)
            for flag in FeatureFlag
        }
    
    @classmethod
    def get_migration_phase(cls) -> str:
        """
        Determine current migration phase based on enabled flags.
        
        Returns:
            String describing the current migration phase
        """
        if cls.is_enabled(FeatureFlag.USE_AAM_AS_SOURCE):
            if cls.is_enabled(FeatureFlag.ENABLE_CANONICAL_EVENTS):
                if cls.is_enabled(FeatureFlag.ENABLE_AUTO_REPAIR):
                    return "Phase 3: Canonical Events + Auto-Repair"
                return "Phase 3: Canonical Events Only"
            return "Phase 2: AAM-Backed DCL"
        return "Phase 0/1: Demo Mode (File-Based Sources)"


def require_feature(flag: FeatureFlag):
    """
    Decorator to require a feature flag for endpoint access.
    
    Args:
        flag: The feature flag that must be enabled
        
    Example:
        @require_feature(FeatureFlag.USE_AAM_AS_SOURCE)
        async def aam_backed_endpoint():
            # This endpoint only works when AAM is enabled
            pass
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            if not FeatureFlagConfig.is_enabled(flag):
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=503,
                    detail=f"Feature {flag.value} is not enabled. "
                           f"Current phase: {FeatureFlagConfig.get_migration_phase()}"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


if __name__ == "__main__":
    print("AutonomOS Feature Flags Status:")
    print("=" * 60)
    for flag, enabled in FeatureFlagConfig.get_all_flags().items():
        status = "✅ ENABLED" if enabled else "❌ DISABLED"
        print(f"{flag:30s} {status}")
    print("=" * 60)
    print(f"Migration Phase: {FeatureFlagConfig.get_migration_phase()}")
