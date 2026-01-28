"""
Models package - Re-exports all models for backward compatibility.

Import models from this package to maintain compatibility with existing code:
    from app.models import User, Tenant, Task, ...

Or import from specific domain modules:
    from app.models.user import User
    from app.models.tenant import Tenant
"""

# Core entities
from app.models.tenant import Tenant
from app.models.user import User

# Task management
from app.models.task import Task, TaskLog

# Agent orchestration
from app.models.agent import (
    Agent,
    AgentRun,
    AgentApproval,
    AgentCheckpoint,
    AgentEvalRun,
)

# Connection and mapping
from app.models.connection import (
    ApiJournal,
    IdempotencyKey,
    RateLimitCounter,
    CanonicalStream,
    MappingRegistry,
    DriftEvent,
    SchemaChange,
    MaterializedAccount,
    MaterializedOpportunity,
    MaterializedContact,
    DCLUnifiedContact,
    DCLUnifiedContactLink,
    MappingProposal,
    ConfidenceScore,
    ConnectorDefinition,
    EntitySchema,
    FieldMapping,
)

# Workflow and approval
from app.models.workflow import (
    HITLRepairAudit,
    ApprovalWorkflow,
)

# Re-export Base for migrations and other uses
from app.models.base import Base

__all__ = [
    # Base
    'Base',
    # Core entities
    'Tenant',
    'User',
    # Task management
    'Task',
    'TaskLog',
    # Agent orchestration
    'Agent',
    'AgentRun',
    'AgentApproval',
    'AgentCheckpoint',
    'AgentEvalRun',
    # Connection and mapping
    'ApiJournal',
    'IdempotencyKey',
    'RateLimitCounter',
    'CanonicalStream',
    'MappingRegistry',
    'DriftEvent',
    'SchemaChange',
    'MaterializedAccount',
    'MaterializedOpportunity',
    'MaterializedContact',
    'DCLUnifiedContact',
    'DCLUnifiedContactLink',
    'MappingProposal',
    'ConfidenceScore',
    'ConnectorDefinition',
    'EntitySchema',
    'FieldMapping',
    # Workflow and approval
    'HITLRepairAudit',
    'ApprovalWorkflow',
]
