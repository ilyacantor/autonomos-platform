"""Add agent orchestration tables

Creates tables for the Agentic Orchestration Platform:
- agents: Agent configuration and definitions
- agent_runs: Execution records for agent runs
- agent_approvals: Human-in-the-loop approval requests

Revision ID: a8c7d2e9f1b3
Revises: 1afcfed1bbf5
Create Date: 2026-01-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = 'a8c7d2e9f1b3'
down_revision: Union[str, Sequence[str], None] = '1afcfed1bbf5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create agent orchestration tables."""

    # ==========================================================================
    # agents table - Agent configuration and definitions
    # ==========================================================================
    op.create_table(
        'agents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('agent_type', sa.String(50), nullable=False, server_default='general'),
        sa.Column('graph_definition', JSONB, nullable=True),
        sa.Column('system_prompt', sa.Text, nullable=True),
        sa.Column('mcp_servers', JSONB, nullable=False, server_default='[]'),
        sa.Column('model', sa.String(100), nullable=False, server_default='claude-sonnet-4-20250514'),
        sa.Column('temperature', sa.Float, nullable=False, server_default='0.7'),
        sa.Column('max_tokens', sa.Integer, nullable=False, server_default='4096'),
        sa.Column('max_steps', sa.Integer, nullable=False, server_default='20'),
        sa.Column('max_cost_usd', sa.Float, nullable=False, server_default='1.0'),
        sa.Column('require_approval_for', JSONB, nullable=False, server_default='[]'),
        sa.Column('forbidden_actions', JSONB, nullable=False, server_default='[]'),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Indexes for agents
    op.create_index('idx_agents_tenant_status', 'agents', ['tenant_id', 'status'])
    op.create_index('idx_agents_tenant_name', 'agents', ['tenant_id', 'name'])
    op.create_index('idx_agents_type', 'agents', ['agent_type'])

    # ==========================================================================
    # agent_runs table - Execution records
    # ==========================================================================
    op.create_table(
        'agent_runs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('agent_id', UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('input_data', JSONB, nullable=True),
        sa.Column('output_data', JSONB, nullable=True),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('triggered_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('trigger_type', sa.String(20), nullable=False, server_default='api'),
        sa.Column('tokens_input', sa.Integer, nullable=False, server_default='0'),
        sa.Column('tokens_output', sa.Integer, nullable=False, server_default='0'),
        sa.Column('cost_usd', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('steps_executed', sa.Integer, nullable=False, server_default='0'),
        # OBO token tracking for ARB Condition 1
        sa.Column('obo_token_issued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('obo_token_expires_at', sa.DateTime(timezone=True), nullable=True),
        # Timing
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Indexes for agent_runs
    op.create_index('idx_agent_runs_tenant_status', 'agent_runs', ['tenant_id', 'status'])
    op.create_index('idx_agent_runs_agent_status', 'agent_runs', ['agent_id', 'status'])
    op.create_index('idx_agent_runs_created', 'agent_runs', ['created_at'])
    op.create_index('idx_agent_runs_user', 'agent_runs', ['triggered_by', 'created_at'])

    # ==========================================================================
    # agent_approvals table - Human-in-the-loop approval requests
    # ==========================================================================
    op.create_table(
        'agent_approvals',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('run_id', UUID(as_uuid=True), sa.ForeignKey('agent_runs.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('action_details', JSONB, nullable=False),
        sa.Column('step_number', sa.Integer, nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('responded_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('approval_notes', sa.Text, nullable=True),
        sa.Column('rejection_reason', sa.Text, nullable=True),
        sa.Column('auto_action', sa.String(20), nullable=False, server_default='reject'),
        sa.Column('escalate_to', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )

    # Indexes for agent_approvals
    op.create_index('idx_agent_approvals_tenant_status', 'agent_approvals', ['tenant_id', 'status'])
    op.create_index('idx_agent_approvals_run', 'agent_approvals', ['run_id', 'step_number'])
    op.create_index('idx_agent_approvals_pending', 'agent_approvals', ['status', 'expires_at'])

    # ==========================================================================
    # agent_checkpoints table - LangGraph checkpoint storage (ARB Condition 3)
    # ==========================================================================
    op.create_table(
        'agent_checkpoints',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('run_id', UUID(as_uuid=True), sa.ForeignKey('agent_runs.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('thread_id', sa.String(255), nullable=False, index=True),
        sa.Column('thread_ts', sa.String(255), nullable=False),
        sa.Column('parent_ts', sa.String(255), nullable=True),
        # Checkpoint data - small payloads stored inline
        sa.Column('checkpoint_data', JSONB, nullable=True),
        # Large blobs offloaded to S3/MinIO (ARB Condition 3)
        sa.Column('blob_key', sa.String(500), nullable=True),
        sa.Column('blob_size_bytes', sa.Integer, nullable=True),
        # Metadata
        sa.Column('step_number', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Indexes for agent_checkpoints
    op.create_index('idx_agent_checkpoints_thread', 'agent_checkpoints', ['thread_id', 'thread_ts'])
    op.create_index('idx_agent_checkpoints_run', 'agent_checkpoints', ['run_id', 'step_number'])

    # ==========================================================================
    # agent_eval_runs table - TDAD Golden Dataset evaluation runs
    # ==========================================================================
    op.create_table(
        'agent_eval_runs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('agent_id', UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_cases', sa.Integer, nullable=False, server_default='0'),
        sa.Column('passed_cases', sa.Integer, nullable=False, server_default='0'),
        sa.Column('failed_cases', sa.Integer, nullable=False, server_default='0'),
        sa.Column('pass_rate', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('total_cost_usd', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('results', JSONB, nullable=False, server_default='[]'),
        sa.Column('triggered_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )

    # Indexes for agent_eval_runs
    op.create_index('idx_agent_eval_runs_agent', 'agent_eval_runs', ['agent_id', 'started_at'])
    op.create_index('idx_agent_eval_runs_tenant', 'agent_eval_runs', ['tenant_id', 'started_at'])


def downgrade() -> None:
    """Drop agent orchestration tables."""

    op.drop_table('agent_eval_runs')
    op.drop_table('agent_checkpoints')
    op.drop_table('agent_approvals')
    op.drop_table('agent_runs')
    op.drop_table('agents')
