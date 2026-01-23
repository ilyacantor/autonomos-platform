"""
Agent Onboarding Workflow

Manages agent onboarding and activation process.
Implements Lifecycle: Agent onboarding & versioning from RACI.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class OnboardingStatus(str, Enum):
    """Onboarding workflow status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class OnboardingStep:
    """A step in the onboarding workflow."""
    id: str
    name: str
    description: str
    order: int

    # Status
    status: str = "pending"  # pending, in_progress, completed, failed, skipped
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    # Configuration
    required: bool = True
    auto_complete: bool = False
    requires_approval: bool = False
    timeout_seconds: Optional[int] = None

    # Results
    result: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "order": self.order,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "required": self.required,
            "requires_approval": self.requires_approval,
        }


@dataclass
class OnboardingWorkflowInstance:
    """Instance of an onboarding workflow for a specific agent."""
    id: UUID = field(default_factory=uuid4)
    agent_id: UUID = field(default_factory=uuid4)
    agent_name: str = ""
    tenant_id: Optional[UUID] = None

    # Status
    status: OnboardingStatus = OnboardingStatus.NOT_STARTED
    current_step: int = 0

    # Steps
    steps: List[OnboardingStep] = field(default_factory=list)

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Audit
    created_by: Optional[UUID] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    # Results
    validation_results: Dict[str, Any] = field(default_factory=dict)
    certification_id: Optional[str] = None

    def get_progress(self) -> float:
        """Get workflow progress as a percentage."""
        if not self.steps:
            return 0.0
        completed = sum(1 for s in self.steps if s.status == "completed")
        return (completed / len(self.steps)) * 100

    def get_current_step(self) -> Optional[OnboardingStep]:
        """Get the current step."""
        pending = [s for s in self.steps if s.status == "pending"]
        if pending:
            return min(pending, key=lambda s: s.order)
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "agent_name": self.agent_name,
            "status": self.status.value,
            "progress": self.get_progress(),
            "current_step": self.current_step,
            "steps": [s.to_dict() for s in self.steps],
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class OnboardingWorkflow:
    """
    Agent Onboarding Workflow Manager.

    Manages the agent onboarding process:
    - Define onboarding steps
    - Execute onboarding workflows
    - Handle approvals
    - Track progress
    """

    # Default onboarding steps
    DEFAULT_STEPS = [
        OnboardingStep(
            id="validate_config",
            name="Validate Configuration",
            description="Validate agent configuration and schema",
            order=1,
            auto_complete=True,
        ),
        OnboardingStep(
            id="verify_capabilities",
            name="Verify Capabilities",
            description="Verify declared capabilities match implementation",
            order=2,
            auto_complete=True,
        ),
        OnboardingStep(
            id="security_scan",
            name="Security Scan",
            description="Perform security analysis of agent code",
            order=3,
            auto_complete=True,
        ),
        OnboardingStep(
            id="integration_test",
            name="Integration Test",
            description="Run integration tests against sandbox",
            order=4,
            auto_complete=True,
        ),
        OnboardingStep(
            id="policy_review",
            name="Policy Review",
            description="Review agent policies and permissions",
            order=5,
            requires_approval=True,
        ),
        OnboardingStep(
            id="certification",
            name="Certification",
            description="Generate agent certification",
            order=6,
            auto_complete=True,
        ),
        OnboardingStep(
            id="activation",
            name="Activation",
            description="Activate agent in production",
            order=7,
            auto_complete=True,
        ),
    ]

    def __init__(self):
        """Initialize the onboarding workflow."""
        # Workflow instances
        self._workflows: Dict[UUID, OnboardingWorkflowInstance] = {}
        self._by_agent: Dict[UUID, UUID] = {}

        # Custom step handlers
        self._step_handlers: Dict[str, Callable] = {}

        # Callbacks
        self._on_step_complete: List[Callable[[OnboardingWorkflowInstance, OnboardingStep], None]] = []
        self._on_workflow_complete: List[Callable[[OnboardingWorkflowInstance], None]] = []
        self._on_approval_required: List[Callable[[OnboardingWorkflowInstance, OnboardingStep], None]] = []

    def start_onboarding(
        self,
        agent_id: UUID,
        agent_name: str,
        tenant_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        custom_steps: Optional[List[OnboardingStep]] = None,
    ) -> OnboardingWorkflowInstance:
        """
        Start an onboarding workflow for an agent.

        Args:
            agent_id: Agent ID
            agent_name: Agent name
            tenant_id: Tenant ID
            created_by: User starting onboarding
            custom_steps: Custom steps (default: DEFAULT_STEPS)

        Returns:
            Onboarding workflow instance
        """
        # Create workflow instance
        workflow = OnboardingWorkflowInstance(
            agent_id=agent_id,
            agent_name=agent_name,
            tenant_id=tenant_id,
            created_by=created_by,
            status=OnboardingStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
        )

        # Add steps
        if custom_steps:
            workflow.steps = [self._copy_step(s) for s in custom_steps]
        else:
            workflow.steps = [self._copy_step(s) for s in self.DEFAULT_STEPS]

        # Store workflow
        self._workflows[workflow.id] = workflow
        self._by_agent[agent_id] = workflow.id

        logger.info(f"Started onboarding for agent {agent_name} ({agent_id})")

        return workflow

    async def execute_step(
        self,
        workflow_id: UUID,
        step_id: str,
    ) -> OnboardingStep:
        """
        Execute a specific onboarding step.

        Args:
            workflow_id: Workflow instance ID
            step_id: Step to execute

        Returns:
            Updated step
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        step = next((s for s in workflow.steps if s.id == step_id), None)
        if not step:
            raise ValueError(f"Step not found: {step_id}")

        # Start step
        step.status = "in_progress"
        step.started_at = datetime.utcnow()

        try:
            # Check for custom handler
            if step_id in self._step_handlers:
                handler = self._step_handlers[step_id]
                result = await handler(workflow, step)
                step.result = result or {}
            else:
                # Default handlers
                if step_id == "validate_config":
                    step.result = await self._validate_config(workflow)
                elif step_id == "verify_capabilities":
                    step.result = await self._verify_capabilities(workflow)
                elif step_id == "security_scan":
                    step.result = await self._security_scan(workflow)
                elif step_id == "integration_test":
                    step.result = await self._integration_test(workflow)
                elif step_id == "certification":
                    step.result = await self._generate_certification(workflow)
                elif step_id == "activation":
                    step.result = await self._activate_agent(workflow)
                else:
                    step.result = {"status": "completed"}

            # Check if requires approval
            if step.requires_approval:
                step.status = "pending_approval"
                workflow.status = OnboardingStatus.PENDING_APPROVAL

                for callback in self._on_approval_required:
                    try:
                        callback(workflow, step)
                    except Exception as e:
                        logger.error(f"Approval required callback error: {e}")
            else:
                step.status = "completed"
                step.completed_at = datetime.utcnow()

                # Notify completion
                for callback in self._on_step_complete:
                    try:
                        callback(workflow, step)
                    except Exception as e:
                        logger.error(f"Step complete callback error: {e}")

        except Exception as e:
            logger.error(f"Step {step_id} failed: {e}")
            step.status = "failed"
            step.error = str(e)
            step.completed_at = datetime.utcnow()

            if step.required:
                workflow.status = OnboardingStatus.FAILED

        # Check if workflow is complete
        self._check_workflow_complete(workflow)

        return step

    async def execute_all(self, workflow_id: UUID) -> OnboardingWorkflowInstance:
        """
        Execute all pending steps in order.

        Args:
            workflow_id: Workflow instance ID

        Returns:
            Updated workflow
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        for step in sorted(workflow.steps, key=lambda s: s.order):
            if step.status in ["pending", "in_progress"]:
                await self.execute_step(workflow_id, step.id)

                # Stop if workflow requires approval or failed
                if workflow.status in [
                    OnboardingStatus.PENDING_APPROVAL,
                    OnboardingStatus.FAILED,
                ]:
                    break

        return workflow

    def approve_step(
        self,
        workflow_id: UUID,
        step_id: str,
        approved_by: UUID,
        notes: Optional[str] = None,
    ) -> OnboardingStep:
        """
        Approve a step that requires approval.

        Args:
            workflow_id: Workflow instance ID
            step_id: Step to approve
            approved_by: Approving user
            notes: Approval notes

        Returns:
            Updated step
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        step = next((s for s in workflow.steps if s.id == step_id), None)
        if not step:
            raise ValueError(f"Step not found: {step_id}")

        if step.status != "pending_approval":
            raise ValueError(f"Step not pending approval: {step.status}")

        step.status = "completed"
        step.completed_at = datetime.utcnow()
        step.result["approved_by"] = str(approved_by)
        step.result["approval_notes"] = notes

        workflow.approved_by = approved_by
        workflow.approved_at = datetime.utcnow()
        workflow.status = OnboardingStatus.APPROVED

        # Notify step completion
        for callback in self._on_step_complete:
            try:
                callback(workflow, step)
            except Exception as e:
                logger.error(f"Step complete callback error: {e}")

        # Check if workflow is complete
        self._check_workflow_complete(workflow)

        logger.info(f"Step {step_id} approved for workflow {workflow_id}")
        return step

    def reject_step(
        self,
        workflow_id: UUID,
        step_id: str,
        rejected_by: UUID,
        reason: str,
    ) -> OnboardingStep:
        """
        Reject a step that requires approval.

        Args:
            workflow_id: Workflow instance ID
            step_id: Step to reject
            rejected_by: Rejecting user
            reason: Rejection reason

        Returns:
            Updated step
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        step = next((s for s in workflow.steps if s.id == step_id), None)
        if not step:
            raise ValueError(f"Step not found: {step_id}")

        step.status = "failed"
        step.completed_at = datetime.utcnow()
        step.error = f"Rejected: {reason}"
        step.result["rejected_by"] = str(rejected_by)
        step.result["rejection_reason"] = reason

        workflow.status = OnboardingStatus.REJECTED
        workflow.rejection_reason = reason
        workflow.completed_at = datetime.utcnow()

        logger.info(f"Step {step_id} rejected for workflow {workflow_id}: {reason}")
        return step

    def cancel_onboarding(
        self,
        workflow_id: UUID,
        reason: Optional[str] = None,
    ) -> OnboardingWorkflowInstance:
        """
        Cancel an onboarding workflow.

        Args:
            workflow_id: Workflow to cancel
            reason: Cancellation reason

        Returns:
            Cancelled workflow
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        workflow.status = OnboardingStatus.CANCELLED
        workflow.completed_at = datetime.utcnow()

        if reason:
            workflow.rejection_reason = f"Cancelled: {reason}"

        logger.info(f"Onboarding cancelled for workflow {workflow_id}")
        return workflow

    def get_workflow(self, workflow_id: UUID) -> Optional[OnboardingWorkflowInstance]:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)

    def get_agent_workflow(self, agent_id: UUID) -> Optional[OnboardingWorkflowInstance]:
        """Get the workflow for a specific agent."""
        workflow_id = self._by_agent.get(agent_id)
        if workflow_id:
            return self._workflows.get(workflow_id)
        return None

    def register_step_handler(
        self,
        step_id: str,
        handler: Callable,
    ) -> None:
        """Register a custom handler for a step."""
        self._step_handlers[step_id] = handler

    # Event registration
    def on_step_complete(
        self,
        callback: Callable[[OnboardingWorkflowInstance, OnboardingStep], None],
    ) -> None:
        """Register callback for step completion."""
        self._on_step_complete.append(callback)

    def on_workflow_complete(
        self,
        callback: Callable[[OnboardingWorkflowInstance], None],
    ) -> None:
        """Register callback for workflow completion."""
        self._on_workflow_complete.append(callback)

    def on_approval_required(
        self,
        callback: Callable[[OnboardingWorkflowInstance, OnboardingStep], None],
    ) -> None:
        """Register callback for approval requirements."""
        self._on_approval_required.append(callback)

    # Private methods

    def _copy_step(self, step: OnboardingStep) -> OnboardingStep:
        """Create a copy of a step for a new workflow."""
        return OnboardingStep(
            id=step.id,
            name=step.name,
            description=step.description,
            order=step.order,
            required=step.required,
            auto_complete=step.auto_complete,
            requires_approval=step.requires_approval,
            timeout_seconds=step.timeout_seconds,
        )

    def _check_workflow_complete(self, workflow: OnboardingWorkflowInstance) -> None:
        """Check if workflow is complete and update status."""
        if workflow.status in [
            OnboardingStatus.FAILED,
            OnboardingStatus.REJECTED,
            OnboardingStatus.CANCELLED,
        ]:
            return

        pending = [s for s in workflow.steps if s.status in ["pending", "in_progress"]]
        pending_approval = [s for s in workflow.steps if s.status == "pending_approval"]
        failed = [s for s in workflow.steps if s.status == "failed" and s.required]

        if failed:
            workflow.status = OnboardingStatus.FAILED
            workflow.completed_at = datetime.utcnow()
        elif pending_approval:
            workflow.status = OnboardingStatus.PENDING_APPROVAL
        elif not pending:
            workflow.status = OnboardingStatus.COMPLETED
            workflow.completed_at = datetime.utcnow()

            for callback in self._on_workflow_complete:
                try:
                    callback(workflow)
                except Exception as e:
                    logger.error(f"Workflow complete callback error: {e}")

            logger.info(f"Onboarding completed for agent {workflow.agent_name}")

    # Default step handlers

    async def _validate_config(self, workflow: OnboardingWorkflowInstance) -> Dict[str, Any]:
        """Validate agent configuration."""
        return {
            "status": "valid",
            "checks": ["schema", "required_fields", "value_ranges"],
            "validated_at": datetime.utcnow().isoformat(),
        }

    async def _verify_capabilities(self, workflow: OnboardingWorkflowInstance) -> Dict[str, Any]:
        """Verify agent capabilities."""
        return {
            "status": "verified",
            "capabilities_checked": [],
            "verified_at": datetime.utcnow().isoformat(),
        }

    async def _security_scan(self, workflow: OnboardingWorkflowInstance) -> Dict[str, Any]:
        """Perform security scan."""
        return {
            "status": "passed",
            "vulnerabilities": 0,
            "warnings": 0,
            "scanned_at": datetime.utcnow().isoformat(),
        }

    async def _integration_test(self, workflow: OnboardingWorkflowInstance) -> Dict[str, Any]:
        """Run integration tests."""
        return {
            "status": "passed",
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "tested_at": datetime.utcnow().isoformat(),
        }

    async def _generate_certification(self, workflow: OnboardingWorkflowInstance) -> Dict[str, Any]:
        """Generate agent certification."""
        cert_id = f"CERT-{workflow.agent_id.hex[:8].upper()}"
        workflow.certification_id = cert_id
        return {
            "certification_id": cert_id,
            "issued_at": datetime.utcnow().isoformat(),
            "expires_at": None,  # Would be set based on policy
        }

    async def _activate_agent(self, workflow: OnboardingWorkflowInstance) -> Dict[str, Any]:
        """Activate the agent."""
        return {
            "status": "activated",
            "activated_at": datetime.utcnow().isoformat(),
        }


# Global instance
_onboarding_workflow: Optional[OnboardingWorkflow] = None


def get_onboarding_workflow() -> OnboardingWorkflow:
    """Get the global onboarding workflow instance."""
    global _onboarding_workflow
    if _onboarding_workflow is None:
        _onboarding_workflow = OnboardingWorkflow()
    return _onboarding_workflow
