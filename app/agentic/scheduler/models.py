"""
Scheduler Data Models

Database models and Pydantic schemas for scheduled jobs.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4


class TriggerType(str, Enum):
    """Types of job triggers."""
    CRON = "cron"           # Cron expression (e.g., "0 9 * * 1-5")
    INTERVAL = "interval"    # Fixed interval (e.g., every 5 minutes)
    ONCE = "once"           # One-time scheduled execution
    WEBHOOK = "webhook"     # HTTP webhook trigger
    EVENT = "event"         # Event-based trigger


class JobStatus(str, Enum):
    """Status of a scheduled job."""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    EXPIRED = "expired"


class ExecutionStatus(str, Enum):
    """Status of a job execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass
class JobTrigger:
    """Trigger configuration for a scheduled job."""
    trigger_type: TriggerType

    # Cron trigger
    cron_expression: Optional[str] = None
    timezone: str = "UTC"

    # Interval trigger
    interval_seconds: Optional[int] = None

    # Once trigger
    run_at: Optional[datetime] = None

    # Webhook trigger
    webhook_secret: Optional[str] = None

    # Event trigger
    event_type: Optional[str] = None
    event_filter: Optional[dict] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "trigger_type": self.trigger_type.value,
            "cron_expression": self.cron_expression,
            "timezone": self.timezone,
            "interval_seconds": self.interval_seconds,
            "run_at": self.run_at.isoformat() if self.run_at else None,
            "webhook_secret": self.webhook_secret,
            "event_type": self.event_type,
            "event_filter": self.event_filter,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobTrigger":
        """Create from dictionary."""
        return cls(
            trigger_type=TriggerType(data["trigger_type"]),
            cron_expression=data.get("cron_expression"),
            timezone=data.get("timezone", "UTC"),
            interval_seconds=data.get("interval_seconds"),
            run_at=datetime.fromisoformat(data["run_at"]) if data.get("run_at") else None,
            webhook_secret=data.get("webhook_secret"),
            event_type=data.get("event_type"),
            event_filter=data.get("event_filter"),
        )


@dataclass
class ScheduledJob:
    """A scheduled job that triggers agent execution."""

    # Identity
    job_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)

    # Job configuration
    name: str = ""
    description: str = ""
    agent_id: str = ""

    # Input to pass to agent
    input_template: str = ""
    input_variables: dict = field(default_factory=dict)

    # Trigger configuration
    trigger: JobTrigger = field(default_factory=lambda: JobTrigger(TriggerType.CRON))

    # Status and scheduling
    status: JobStatus = JobStatus.ACTIVE
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None

    # Execution settings
    timeout_seconds: int = 300
    max_retries: int = 3
    retry_delay_seconds: int = 60

    # Concurrency control
    allow_concurrent: bool = False
    max_concurrent: int = 1

    # Validity period
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = None

    # Statistics
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "job_id": str(self.job_id),
            "tenant_id": str(self.tenant_id),
            "name": self.name,
            "description": self.description,
            "agent_id": self.agent_id,
            "input_template": self.input_template,
            "input_variables": self.input_variables,
            "trigger": self.trigger.to_dict(),
            "status": self.status.value,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "retry_delay_seconds": self.retry_delay_seconds,
            "allow_concurrent": self.allow_concurrent,
            "max_concurrent": self.max_concurrent,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": str(self.created_by) if self.created_by else None,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
        }

    def is_due(self, now: Optional[datetime] = None) -> bool:
        """Check if the job is due to run."""
        now = now or datetime.utcnow()

        if self.status != JobStatus.ACTIVE:
            return False

        if self.start_date and now < self.start_date:
            return False

        if self.end_date and now > self.end_date:
            return False

        if self.next_run_at and now >= self.next_run_at:
            return True

        return False

    def render_input(self, extra_variables: Optional[dict] = None) -> str:
        """Render the input template with variables."""
        variables = {**self.input_variables}
        if extra_variables:
            variables.update(extra_variables)

        # Add built-in variables
        now = datetime.utcnow()
        variables.update({
            "now": now.isoformat(),
            "date": now.date().isoformat(),
            "time": now.time().isoformat(),
            "job_id": str(self.job_id),
            "job_name": self.name,
        })

        try:
            return self.input_template.format(**variables)
        except KeyError:
            return self.input_template


@dataclass
class JobExecution:
    """Record of a job execution."""

    execution_id: UUID = field(default_factory=uuid4)
    job_id: UUID = field(default_factory=uuid4)
    run_id: Optional[UUID] = None  # Agent run ID

    # Timing
    scheduled_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Status
    status: ExecutionStatus = ExecutionStatus.PENDING
    attempt: int = 1

    # Input/Output
    input_rendered: str = ""
    output: Optional[str] = None
    error: Optional[str] = None

    # Metrics
    duration_ms: Optional[int] = None
    tokens_used: int = 0
    cost_usd: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "execution_id": str(self.execution_id),
            "job_id": str(self.job_id),
            "run_id": str(self.run_id) if self.run_id else None,
            "scheduled_at": self.scheduled_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value,
            "attempt": self.attempt,
            "input_rendered": self.input_rendered,
            "output": self.output,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
        }


# Pydantic schemas for API
from pydantic import BaseModel, Field
from typing import List


class JobTriggerCreate(BaseModel):
    """Schema for creating a job trigger."""
    trigger_type: TriggerType
    cron_expression: Optional[str] = None
    timezone: str = "UTC"
    interval_seconds: Optional[int] = None
    run_at: Optional[datetime] = None
    event_type: Optional[str] = None
    event_filter: Optional[dict] = None


class ScheduledJobCreate(BaseModel):
    """Schema for creating a scheduled job."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    agent_id: str = Field(..., min_length=1)
    input_template: str = Field(..., min_length=1)
    input_variables: dict = Field(default_factory=dict)
    trigger: JobTriggerCreate
    timeout_seconds: int = Field(default=300, ge=30, le=3600)
    max_retries: int = Field(default=3, ge=0, le=10)
    allow_concurrent: bool = False
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ScheduledJobUpdate(BaseModel):
    """Schema for updating a scheduled job."""
    name: Optional[str] = None
    description: Optional[str] = None
    input_template: Optional[str] = None
    input_variables: Optional[dict] = None
    trigger: Optional[JobTriggerCreate] = None
    status: Optional[JobStatus] = None
    timeout_seconds: Optional[int] = None
    max_retries: Optional[int] = None
    allow_concurrent: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ScheduledJobResponse(BaseModel):
    """Schema for scheduled job response."""
    job_id: str
    tenant_id: str
    name: str
    description: str
    agent_id: str
    input_template: str
    input_variables: dict
    trigger: dict
    status: str
    next_run_at: Optional[str]
    last_run_at: Optional[str]
    timeout_seconds: int
    max_retries: int
    allow_concurrent: bool
    created_at: str
    total_runs: int
    successful_runs: int
    failed_runs: int

    class Config:
        from_attributes = True


class JobExecutionResponse(BaseModel):
    """Schema for job execution response."""
    execution_id: str
    job_id: str
    run_id: Optional[str]
    scheduled_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    status: str
    attempt: int
    input_rendered: str
    output: Optional[str]
    error: Optional[str]
    duration_ms: Optional[int]
    tokens_used: int
    cost_usd: float

    class Config:
        from_attributes = True
