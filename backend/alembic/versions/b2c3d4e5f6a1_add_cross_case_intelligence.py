"""add_cross_case_intelligence

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-10-29 20:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a1'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create cross_case_entity_links table
    if 'cross_case_entity_links' not in tables:
        op.create_table(
            'cross_case_entity_links',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('source_case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('source_entity_id', sa.Integer(), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=True, index=True),
            sa.Column('target_case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('target_entity_id', sa.Integer(), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=True, index=True),
            sa.Column('entity_type', sa.String(64), nullable=False, index=True),
            sa.Column('match_type', sa.String(64), nullable=False),
            sa.Column('match_value', sa.String(255), nullable=False),
            sa.Column('similarity_score', sa.Float(), server_default='1.0', nullable=False),
            sa.Column('status', sa.String(32), server_default='pending_review', nullable=False, index=True),
            sa.Column('confidence_reason', sa.Text(), nullable=False),
            sa.Column('reviewed_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('reviewed_by_name', sa.String(), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('reviewer_notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )
        op.create_index(
            'ix_cross_case_pair',
            'cross_case_entity_links',
            ['source_case_id', 'target_case_id']
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'cross_case_entity_links' in tables:
        op.drop_table('cross_case_entity_links')

