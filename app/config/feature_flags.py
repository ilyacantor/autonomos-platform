"""
Feature Flag Configuration for AutonomOS Architecture Restructuring

This module provides centralized feature flag management for progressive
rollout of the new Data Sources → AAM → DCL → Agents architecture.

Feature flags allow safe, incremental migration without breaking existing functionality.
"""

from typing import Dict, Any
import os
from enum import Enum


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
    Feature flag configuration with environment variable override support.
    
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
    """
    
    _flags: Dict[str, bool] = {
        FeatureFlag.USE_AAM_AS_SOURCE: True,  # Phase 2.5: ENABLED - Testing AAM → DCL bridge with correct tenant
        FeatureFlag.ENABLE_DRIFT_DETECTION: True,  # Phase 4: ENABLED - Detect schema drift in AAM connectors
        FeatureFlag.ENABLE_AUTO_REPAIR: True,  # Phase 4: ENABLED (Task 8) - Auto-repair with 3-tier confidence scoring
        FeatureFlag.ENABLE_HITL_WORKFLOW: True,
        FeatureFlag.ENABLE_CANONICAL_EVENTS: True,  # Phase 4: ENABLED - Normalize and validate canonical events
        FeatureFlag.ENABLE_SCHEMA_FINGERPRINTING: True,  # Phase 4: ENABLED - Track schema versions for drift
    }
    
    @classmethod
    def is_enabled(cls, flag: FeatureFlag) -> bool:
        """
        Check if a feature flag is enabled.
        
        Args:
            flag: The feature flag to check
            
        Returns:
            True if enabled, False otherwise
            
        Example:
            >>> if FeatureFlagConfig.is_enabled(FeatureFlag.USE_AAM_AS_SOURCE):
            ...     # Use AAM-backed data path
        """
        env_var = f"FEATURE_{flag.value}"
        env_value = os.getenv(env_var, "").lower()
        
        if env_value in ("true", "1", "yes"):
            return True
        elif env_value in ("false", "0", "no"):
            return False
        
        return cls._flags.get(flag, False)
    
    @classmethod
    def set_flag(cls, flag: FeatureFlag, enabled: bool) -> None:
        """
        Programmatically set a feature flag (for testing).
        
        Args:
            flag: The feature flag to set
            enabled: True to enable, False to disable
            
        Note:
            Environment variables take precedence over programmatic settings.
        """
        cls._flags[flag] = enabled
    
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
