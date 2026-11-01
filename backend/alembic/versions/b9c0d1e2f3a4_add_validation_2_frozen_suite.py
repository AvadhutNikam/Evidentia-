"""add validation 2 frozen suite and run records

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-10-30 00:22:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b9c0d1e2f3a4'
down_revision = 'a8b9c0d1e2f3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'validation_suites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('suite_version', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_frozen', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('frozen_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('frozen_by', sa.String(length=100), nullable=False, server_default='Independent Review Board'),
        sa.Column('checksum_sha256', sa.String(length=64), nullable=False),
        sa.Column('total_blind_cases', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('authors_meta', sa.Text(), nullable=False),
        sa.Column('reviewers_meta', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('baseline_metrics', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('suite_version')
    )
    with op.batch_alter_table('validation_suites', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_validation_suites_id'), ['id'], unique=False)

    op.create_table(
        'validation_run_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('suite_version', sa.String(length=50), nullable=False, server_default='v2.0-FROZEN-2026'),
        sa.Column('run_timestamp', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('run_by', sa.String(length=100), nullable=False, server_default='admin'),
        sa.Column('run_type', sa.String(length=50), nullable=False, server_default='blind_evaluation'),
        sa.Column('top1_accuracy', sa.Float(), nullable=False),
        sa.Column('top3_accuracy', sa.Float(), nullable=False),
        sa.Column('mrr', sa.Float(), nullable=False),
        sa.Column('avg_culprit_rank', sa.Float(), nullable=False),
        sa.Column('calibration_ece', sa.Float(), nullable=False),
        sa.Column('brier_score', sa.Float(), nullable=False),
        sa.Column('stability_score', sa.Float(), nullable=False),
        sa.Column('is_regression', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('regression_details', sa.Text(), nullable=True),
        sa.Column('case_results', sa.Text(), nullable=False),
        sa.Column('reviewer_comparison', sa.Text(), nullable=True),
        sa.Column('failure_notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('validation_run_records', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_validation_run_records_id'), ['id'], unique=False)


def downgrade():
    with op.batch_alter_table('validation_run_records', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_validation_run_records_id'))
    op.drop_table('validation_run_records')

    with op.batch_alter_table('validation_suites', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_validation_suites_id'))
    op.drop_table('validation_suites')

