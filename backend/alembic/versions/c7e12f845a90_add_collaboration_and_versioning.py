"""add_collaboration_and_versioning

Revision ID: c7e12f845a90
Revises: eb9561349b46
Create Date: 2026-10-29 17:31:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e12f845a90'
down_revision: Union[str, Sequence[str], None] = 'eb9561349b46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Add version column to existing editable tables if not present
    tables_to_version = [
        'users',
        'cases',
        'evidence',
        'hypotheses',
        'evidence_assessments',
        'suspect_profile_factors',
        'prior_records',
        'investigation_tasks'
    ]

    for table_name in tables_to_version:
        if table_name in tables:
            columns = [c['name'] for c in inspector.get_columns(table_name)]
            if 'version' not in columns:
                with op.batch_alter_table(table_name) as batch_op:
                    batch_op.add_column(
                        sa.Column('version', sa.Integer(), nullable=False, server_default='1')
                    )

    # 2. Create edit_locks table
    if 'edit_locks' not in tables:
        op.create_table(
            'edit_locks',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('item_type', sa.String(), nullable=False, index=True),
            sa.Column('item_id', sa.String(), nullable=False, index=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('user_name', sa.String(), nullable=False),
            sa.Column('user_role', sa.String(), default='investigator'),
            sa.Column('acquired_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False, index=True),
            sa.Column('client_token', sa.String(), nullable=True)
        )

    # 3. Create case_presence table
    if 'case_presence' not in tables:
        op.create_table(
            'case_presence',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('user_name', sa.String(), nullable=False),
            sa.Column('user_role', sa.String(), nullable=False),
            sa.Column('current_location', sa.String(), default='Case Overview'),
            sa.Column('item_id', sa.String(), nullable=True),
            sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True)
        )

    # 4. Create collaboration_events table
    if 'collaboration_events' not in tables:
        op.create_table(
            'collaboration_events',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('event_type', sa.String(), nullable=False, index=True),
            sa.Column('item_type', sa.String(), nullable=True),
            sa.Column('item_id', sa.String(), nullable=True),
            sa.Column('version', sa.Integer(), nullable=True),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('user_name', sa.String(), nullable=True),
            sa.Column('summary', sa.String(), nullable=False),
            sa.Column('payload', sa.Text(), nullable=True),
            sa.Column('is_restricted', sa.Boolean(), default=False, nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True)
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'collaboration_events' in tables:
        op.drop_table('collaboration_events')
    if 'case_presence' in tables:
        op.drop_table('case_presence')
    if 'edit_locks' in tables:
        op.drop_table('edit_locks')

    tables_to_unversion = [
        'investigation_tasks',
        'prior_records',
        'suspect_profile_factors',
        'evidence_assessments',
        'hypotheses',
        'evidence',
        'cases'
    ]
    for table_name in tables_to_unversion:
        if table_name in tables:
            columns = [c['name'] for c in inspector.get_columns(table_name)]
            if 'version' in columns:
                with op.batch_alter_table(table_name) as batch_op:
                    batch_op.drop_column('version')
