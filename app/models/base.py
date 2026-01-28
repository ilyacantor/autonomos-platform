"""
Base model configuration and common imports for all models.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, JSON, DateTime, Integer, Float, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from shared.database import Base

# Re-export Base and common imports for use in domain modules
__all__ = [
    'uuid',
    'datetime',
    'Column',
    'String',
    'JSON',
    'DateTime',
    'Integer',
    'Float',
    'ForeignKey',
    'func',
    'Index',
    'UUID',
    'relationship',
    'Base',
]
