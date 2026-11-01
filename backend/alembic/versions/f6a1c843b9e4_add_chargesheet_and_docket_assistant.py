"""add_chargesheet_and_docket_assistant

Revision ID: f6a1c843b9e4
Revises: e5f9a231b8c2
Create Date: 2026-10-29 18:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a1c843b9e4'
down_revision: Union[str, Sequence[str], None] = 'e5f9a231b8c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create chargesheet_drafts table
    if 'chargesheet_drafts' not in tables:
        op.create_table(
            'chargesheet_drafts',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('title', sa.String(), server_default='Draft Final Police Report / Chargesheet (u/s 193 BNSS / 173 CrPC)', nullable=False),
            sa.Column('court_name', sa.String(), server_default='Court of the Chief Judicial Magistrate / Sessions Court', nullable=False),
            sa.Column('police_station', sa.String(), server_default='Special Crime Investigation Branch', nullable=False),
            sa.Column('fir_number', sa.String(), nullable=True),
            sa.Column('offence_section', sa.String(), nullable=True),
            sa.Column('investigating_officer', sa.String(), nullable=True),
            sa.Column('status', sa.String(), server_default='draft', nullable=False, index=True),
            sa.Column('legal_review_status', sa.String(), server_default='pending_legal_review', nullable=False),
            sa.Column('is_draft', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('version', sa.Integer(), server_default='1', nullable=False),
            sa.Column('facts_narrative', sa.Text(), nullable=False),
            sa.Column('evidence_inventory', sa.Text(), nullable=False),
            sa.Column('witness_statements', sa.Text(), nullable=False),
            sa.Column('forensic_findings', sa.Text(), nullable=False),
            sa.Column('analysis_and_charges', sa.Text(), nullable=False),
            sa.Column('source_citations', sa.Text(), nullable=True),
            sa.Column('legal_disclaimer', sa.Text(), nullable=False),
            sa.Column('created_by', sa.String(), server_default='Investigating Officer', nullable=False),
            sa.Column('last_edited_by', sa.String(), nullable=True),
            sa.Column('last_edit_summary', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )

    # 2. Create chargesheet_edit_logs table
    if 'chargesheet_edit_logs' not in tables:
        op.create_table(
            'chargesheet_edit_logs',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('chargesheet_id', sa.Integer(), sa.ForeignKey('chargesheet_drafts.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('version', sa.Integer(), nullable=False),
            sa.Column('section_edited', sa.String(), nullable=False),
            sa.Column('edit_summary', sa.Text(), nullable=False),
            sa.Column('edited_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('edited_by_name', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'chargesheet_edit_logs' in tables:
        op.drop_table('chargesheet_edit_logs')
    if 'chargesheet_drafts' in tables:
        op.drop_table('chargesheet_drafts')

