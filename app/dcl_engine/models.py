"""
Data models and types for DCL Engine.
"""
from dataclasses import dataclass
from typing import Dict, Any, List, Optional


@dataclass
class Scorecard:
    """Scorecard for tracking mapping quality and issues."""
    confidence: float
    blockers: List[str]
    issues: List[str]
    joins: List[Dict[str, str]]


# Type aliases for clarity
TableSchema = Dict[str, Any]
SourceTables = Dict[str, TableSchema]
MappingPlan = Dict[str, Any]
GraphState = Dict[str, Any]
