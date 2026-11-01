"""add_interview_module

Revision ID: a1b2c3d4e5f6
Revises: f6a1c843b9e4
Create Date: 2026-10-29 19:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f6a1c843b9e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create interviews table
    if 'interviews' not in tables:
        op.create_table(
            'interviews',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('session_code', sa.String(), nullable=False, index=True),
            sa.Column('interviewee_name', sa.String(), nullable=False),
            sa.Column('interviewee_role', sa.String(), server_default='suspect', nullable=False),
            sa.Column('interviewer_name', sa.String(), nullable=False),
            sa.Column('interview_date', sa.String(), nullable=True),
            sa.Column('duration', sa.String(), server_default='00:00 mins', nullable=False),
            sa.Column('status', sa.String(), server_default='Transcribed', nullable=False),
            sa.Column('audio_url', sa.String(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )

    # 2. Create interview_statements table
    if 'interview_statements' not in tables:
        op.create_table(
            'interview_statements',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('interview_id', sa.Integer(), sa.ForeignKey('interviews.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('sequence_order', sa.Integer(), server_default='1', nullable=False),
            sa.Column('speaker', sa.String(), nullable=False),
            sa.Column('role', sa.String(), server_default='interviewee', nullable=False),
            sa.Column('timestamp_marker', sa.String(), server_default='00:00', nullable=False),
            sa.Column('seconds', sa.Integer(), server_default='0', nullable=False),
            sa.Column('question', sa.Text(), nullable=True),
            sa.Column('question_source_type', sa.String(), nullable=True),
            sa.Column('question_source_id', sa.String(), nullable=True),
            sa.Column('text', sa.Text(), nullable=False),
            sa.Column('tag', sa.String(), nullable=True),
            sa.Column('is_contradiction_flag', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )

    # 3. Create interview_contradictions table
    if 'interview_contradictions' not in tables:
        op.create_table(
            'interview_contradictions',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('interview_id', sa.Integer(), sa.ForeignKey('interviews.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('statement_id', sa.Integer(), sa.ForeignKey('interview_statements.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('quote_new', sa.Text(), nullable=False),
            sa.Column('source_new', sa.String(), nullable=False),
            sa.Column('quote_prior', sa.Text(), nullable=False),
            sa.Column('source_prior', sa.String(), nullable=False),
            sa.Column('prior_statement_id', sa.Integer(), sa.ForeignKey('interview_statements.id', ondelete='SET NULL'), nullable=True),
            sa.Column('prior_evidence_id', sa.Integer(), sa.ForeignKey('evidence.id', ondelete='SET NULL'), nullable=True),
            sa.Column('conflict_type', sa.String(), server_default='Direct Contradiction', nullable=False),
            sa.Column('reasoning', sa.Text(), nullable=False),
            sa.Column('confidence', sa.Float(), server_default='95.0', nullable=False),
            sa.Column('severity', sa.String(), server_default='critical', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )


def downgrade() -> None:
    op.drop_table('interview_contradictions')
    op.drop_table('interview_statements')
    op.drop_table('interviews')

