"""add_decision_quality_features

Revision ID: e5f6a1b2c3d4
Revises: d4e5f6a1b2c3
Create Date: 2026-10-29 22:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a1b2c3d4'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a1b2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create decision_signoffs table
    if 'decision_signoffs' not in tables:
        op.create_table(
            'decision_signoffs',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('item_type', sa.String(length=64), nullable=False, index=True),
            sa.Column('item_id', sa.Integer(), nullable=False, index=True),
            sa.Column('item_summary', sa.Text(), nullable=False),
            sa.Column('maker_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('maker_name', sa.String(length=128), nullable=False),
            sa.Column('checker_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('checker_name', sa.String(length=128), nullable=True),
            sa.Column('checker_role', sa.String(length=64), nullable=True),
            sa.Column('status', sa.String(length=32), server_default='pending', nullable=False, index=True),
            sa.Column('review_notes', sa.Text(), nullable=True),
            sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True)
        )

    # 2. Add columns to hypotheses table
    if 'hypotheses' in tables:
        hypo_cols = [c['name'] for c in inspector.get_columns('hypotheses')]
        with op.batch_alter_table('hypotheses') as batch_op:
            if 'plain_language_summary' not in hypo_cols:
                batch_op.add_column(sa.Column('plain_language_summary', sa.Text(), nullable=True))
            if 'plain_language_verdict' not in hypo_cols:
                batch_op.add_column(sa.Column('plain_language_verdict', sa.String(), nullable=True))
            if 'plain_language_drivers' not in hypo_cols:
                batch_op.add_column(sa.Column('plain_language_drivers', sa.Text(), nullable=True))
            if 'plain_language_doubts' not in hypo_cols:
                batch_op.add_column(sa.Column('plain_language_doubts', sa.Text(), nullable=True))

    # 3. Add columns to evidence_assessments table
    if 'evidence_assessments' in tables:
        ea_cols = [c['name'] for c in inspector.get_columns('evidence_assessments')]
        with op.batch_alter_table('evidence_assessments') as batch_op:
            if 'second_signoff_status' not in ea_cols:
                batch_op.add_column(sa.Column('second_signoff_status', sa.String(), server_default='not_required', nullable=True))
            if 'second_signoff_by_id' not in ea_cols:
                batch_op.add_column(sa.Column('second_signoff_by_id', sa.Integer(), nullable=True))
            if 'second_signoff_by_name' not in ea_cols:
                batch_op.add_column(sa.Column('second_signoff_by_name', sa.String(), nullable=True))
            if 'second_signoff_at' not in ea_cols:
                batch_op.add_column(sa.Column('second_signoff_at', sa.DateTime(timezone=True), nullable=True))
            if 'second_signoff_notes' not in ea_cols:
                batch_op.add_column(sa.Column('second_signoff_notes', sa.Text(), nullable=True))
            if 'is_key_classification' not in ea_cols:
                batch_op.add_column(sa.Column('is_key_classification', sa.Boolean(), server_default='0', nullable=True))

    # 4. Add columns to chargesheet_drafts table
    if 'chargesheet_drafts' in tables:
        cd_cols = [c['name'] for c in inspector.get_columns('chargesheet_drafts')]
        with op.batch_alter_table('chargesheet_drafts') as batch_op:
            if 'second_signoff_status' not in cd_cols:
                batch_op.add_column(sa.Column('second_signoff_status', sa.String(), server_default='pending_signoff', nullable=True))
            if 'second_signoff_by_id' not in cd_cols:
                batch_op.add_column(sa.Column('second_signoff_by_id', sa.Integer(), nullable=True))
            if 'second_signoff_by_name' not in cd_cols:
                batch_op.add_column(sa.Column('second_signoff_by_name', sa.String(), nullable=True))
            if 'second_signoff_at' not in cd_cols:
                batch_op.add_column(sa.Column('second_signoff_at', sa.DateTime(timezone=True), nullable=True))
            if 'second_signoff_notes' not in cd_cols:
                batch_op.add_column(sa.Column('second_signoff_notes', sa.Text(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'decision_signoffs' in tables:
        op.drop_table('decision_signoffs')

    if 'hypotheses' in tables:
        with op.batch_alter_table('hypotheses') as batch_op:
            batch_op.drop_column('plain_language_doubts')
            batch_op.drop_column('plain_language_drivers')
            batch_op.drop_column('plain_language_verdict')
            batch_op.drop_column('plain_language_summary')

    if 'evidence_assessments' in tables:
        with op.batch_alter_table('evidence_assessments') as batch_op:
            batch_op.drop_column('is_key_classification')
            batch_op.drop_column('second_signoff_notes')
            batch_op.drop_column('second_signoff_at')
            batch_op.drop_column('second_signoff_by_name')
            batch_op.drop_column('second_signoff_by_id')
            batch_op.drop_column('second_signoff_status')

    if 'chargesheet_drafts' in tables:
        with op.batch_alter_table('chargesheet_drafts') as batch_op:
            batch_op.drop_column('second_signoff_notes')
            batch_op.drop_column('second_signoff_at')
            batch_op.drop_column('second_signoff_by_name')
            batch_op.drop_column('second_signoff_by_id')
            batch_op.drop_column('second_signoff_status')

