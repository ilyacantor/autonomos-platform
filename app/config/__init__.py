"""
AutonomOS Configuration Module

Centralized configuration for feature flags and system settings.

This module provides:
- Unified Pydantic settings (app.config.settings)
- Legacy backward-compatible settings wrapper (app.config.py)
- Feature flag configuration
"""

from app.config.feature_flags import FeatureFlagConfig, FeatureFlag

# Import settings from parent config module for backward compatibility
# This resolves the conflict between app/config/__init__.py and app/config.py
import sys
import os
import importlib.util

# Load config.py as a separate module for backward compatibility
_config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.py')
_spec = importlib.util.spec_from_file_location("_app_config_settings", _config_file)
_config_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_config_mod)

# Backward-compatible settings (wraps unified settings)
settings = _config_mod.settings
Settings = _config_mod.Settings

# Also export unified settings for new code
try:
    from app.config.settings import settings as unified_settings
    from app.config.settings import Settings as UnifiedSettings
except ImportError:
    # If pydantic_settings not installed, unified_settings will be None
    unified_settings = None
    UnifiedSettings = None

__all__ = [
    "FeatureFlagConfig",
    "FeatureFlag",
    "settings",
    "Settings",
    "unified_settings",
    "UnifiedSettings",
]
