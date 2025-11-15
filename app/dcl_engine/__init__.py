"""
DCL Engine Integration Module

This module wraps the legacy DCL (Data Connection Layer) engine
and exposes its functionality to the main AutonomOS application.
"""

# Import the DCL FastAPI app and Redis initialization function
from .app import app as dcl_app, set_redis_client

__all__ = ["dcl_app", "set_redis_client"]
