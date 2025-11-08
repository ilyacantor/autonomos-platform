"""
NLP Gateway Application Entry Point

This script adds the parent directories to sys.path to enable imports
and starts the FastAPI application.
"""
import sys
import os

# Add parent directories to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
workspace_dir = os.path.dirname(parent_dir)

sys.path.insert(0, current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, workspace_dir)

# Now import main with absolute imports fixed
from main import app

__all__ = ['app']
