"""phase2_intelligence_tables_minimal

Revision ID: f9ac1da2f4b9
Revises: f3a92b1c8e44
Create Date: 2025-11-18 21:46:33.311706

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9ac1da2f4b9'
down_revision: Union[str, Sequence[str], None] = 'f3a92b1c8e44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Phase 2 Intelligence tables for RACI compliance."""
    # Create mapping_proposals table
    op.create_table('mapping_proposals',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('connector', sa.String(length=100), nullable=False),
        sa.Column('source_table', sa.String(length=255), nullable=False),
        sa.Column('source_field', sa.String(length=255), nullable=False),
        sa.Column('canonical_entity', sa.String(length=100), nullable=False),
        sa.Column('canonical_field', sa.String(length=100), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('reasoning', sa.String(), nullable=True),
        sa.Column('alternatives', sa.JSON(), nullable=True),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_proposals_action', 'mapping_proposals', ['tenant_id', 'action', 'created_at'], unique=False)
    op.create_index('idx_proposals_lookup', 'mapping_proposals', ['tenant_id', 'connector', 'source_table', 'source_field'], unique=False)
    op.create_index(op.f('ix_mapping_proposals_tenant_id'), 'mapping_proposals', ['tenant_id'], unique=False)
    
    # Create approval_workflows table
    op.create_table('approval_workflows',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('proposal_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('priority', sa.String(length=20), server_default='normal', nullable=True),
        sa.Column('assigned_to', sa.UUID(), nullable=False),
        sa.Column('approver_id', sa.UUID(), nullable=True),
        sa.Column('approval_notes', sa.String(), nullable=True),
        sa.Column('rejection_reason', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['approver_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ),
        sa.ForeignKeyConstraint(['proposal_id'], ['mapping_proposals.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_workflows_assigned', 'approval_workflows', ['assigned_to', 'status'], unique=False)
    op.create_index('idx_workflows_status', 'approval_workflows', ['tenant_id', 'status', 'created_at'], unique=False)
    op.create_index(op.f('ix_approval_workflows_proposal_id'), 'approval_workflows', ['proposal_id'], unique=False)
    op.create_index(op.f('ix_approval_workflows_tenant_id'), 'approval_workflows', ['tenant_id'], unique=False)
    
    # Create confidence_scores table
    op.create_table('confidence_scores',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('mapping_id', sa.UUID(), nullable=True),
        sa.Column('proposal_id', sa.UUID(), nullable=True),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('factors', sa.JSON(), nullable=False),
        sa.Column('calculated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['mapping_id'], ['field_mappings.id'], ),
        sa.ForeignKeyConstraint(['proposal_id'], ['mapping_proposals.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_confidence_mapping', 'confidence_scores', ['mapping_id'], unique=False)
    op.create_index('idx_confidence_tenant', 'confidence_scores', ['tenant_id', 'calculated_at'], unique=False)
    op.create_index(op.f('ix_confidence_scores_mapping_id'), 'confidence_scores', ['mapping_id'], unique=False)
    op.create_index(op.f('ix_confidence_scores_proposal_id'), 'confidence_scores', ['proposal_id'], unique=False)
    op.create_index(op.f('ix_confidence_scores_tenant_id'), 'confidence_scores', ['tenant_id'], unique=False)
    
    # Add repair proposal columns to drift_events table
    op.add_column('drift_events', sa.Column('repair_proposal_id', sa.UUID(), nullable=True))
    op.add_column('drift_events', sa.Column('repair_status', sa.String(length=20), nullable=True))
    op.create_index('idx_drift_repair', 'drift_events', ['repair_proposal_id'], unique=False)
    op.create_index(op.f('ix_drift_events_repair_proposal_id'), 'drift_events', ['repair_proposal_id'], unique=False)
    op.create_foreign_key(None, 'drift_events', 'mapping_proposals', ['repair_proposal_id'], ['id'])


def downgrade() -> None:
    """Remove Phase 2 Intelligence tables."""
    # Remove drift_events columns
    op.drop_constraint(None, 'drift_events', type_='foreignkey')
    op.drop_index(op.f('ix_drift_events_repair_proposal_id'), table_name='drift_events')
    op.drop_index('idx_drift_repair', table_name='drift_events')
    op.drop_column('drift_events', 'repair_status')
    op.drop_column('drift_events', 'repair_proposal_id')
    
    # Drop confidence_scores table
    op.drop_index(op.f('ix_confidence_scores_tenant_id'), table_name='confidence_scores')
    op.drop_index(op.f('ix_confidence_scores_proposal_id'), table_name='confidence_scores')
    op.drop_index(op.f('ix_confidence_scores_mapping_id'), table_name='confidence_scores')
    op.drop_index('idx_confidence_tenant', table_name='confidence_scores')
    op.drop_index('idx_confidence_mapping', table_name='confidence_scores')
    op.drop_table('confidence_scores')
    
    # Drop approval_workflows table
    op.drop_index(op.f('ix_approval_workflows_tenant_id'), table_name='approval_workflows')
    op.drop_index(op.f('ix_approval_workflows_proposal_id'), table_name='approval_workflows')
    op.drop_index('idx_workflows_status', table_name='approval_workflows')
    op.drop_index('idx_workflows_assigned', table_name='approval_workflows')
    op.drop_table('approval_workflows')
    
    # Drop mapping_proposals table
    op.drop_index(op.f('ix_mapping_proposals_tenant_id'), table_name='mapping_proposals')
    op.drop_index('idx_proposals_lookup', table_name='mapping_proposals')
    op.drop_index('idx_proposals_action', table_name='mapping_proposals')
    op.drop_table('mapping_proposals')
