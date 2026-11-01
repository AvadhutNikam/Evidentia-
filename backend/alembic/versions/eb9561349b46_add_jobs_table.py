"""add_jobs_table

Revision ID: eb9561349b46
Revises: 341441164f3d
Create Date: 2026-10-29 15:11:55.452936

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb9561349b46'
down_revision: Union[str, Sequence[str], None] = '341441164f3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'jobs' not in tables:
        op.create_table(
            'jobs',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id'), nullable=False, index=True),
            sa.Column('exhibit_id', sa.Integer(), sa.ForeignKey('evidence.id', ondelete='CASCADE'), nullable=True, index=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('created_by', sa.String(), nullable=True),
            sa.Column('job_type', sa.String(), default='process_evidence', index=True),
            sa.Column('status', sa.String(), default='queued', index=True),
            sa.Column('current_stage', sa.String(), default='queued'),
            sa.Column('progress_pct', sa.Float(), default=0.0),
            sa.Column('attempt_count', sa.Integer(), default=0),
            sa.Column('max_attempts', sa.Integer(), default=3),
            sa.Column('error_message', sa.String(), nullable=True),
            sa.Column('error_detail', sa.Text(), nullable=True),
            sa.Column('stage_results', sa.Text(), nullable=True),
            sa.Column('heartbeat', sa.DateTime(timezone=True), nullable=True),
            sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True, index=True),
            sa.Column('priority', sa.Integer(), default=0, index=True),
            sa.Column('cancel_requested', sa.Boolean(), default=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('jobs')
