"""
NLP Gateway Application Entry Point

Entry point for the NLP Gateway FastAPI application.
Requires proper package installation (pip install -e .)
"""

# Import with proper package path
from services.nlp_gateway.main import app

__all__ = ['app']
