"""
DCL Engine Integration Module

This module wraps the legacy DCL (Data Connection Layer) engine
and exposes its functionality to the main AutonomOS application.
"""

import os
import sys

# NOTE: This sys.path manipulation is necessary for the DCL engine's internal imports
# The DCL engine is a semi-independent module with its own import structure
# TODO: Refactor DCL engine to use proper package imports in a future phase
dcl_engine_dir = os.path.dirname(os.path.abspath(__file__))
if dcl_engine_dir not in sys.path:
    sys.path.insert(0, dcl_engine_dir)

# Import the DCL FastAPI app and Redis initialization function
from .app import app as dcl_app, set_redis_client

__all__ = ["dcl_app", "set_redis_client"]
