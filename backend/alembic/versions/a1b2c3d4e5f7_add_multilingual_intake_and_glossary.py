"""add multilingual intake and legal glossary tables

Revision ID: a1b2c3d4e5f7
Revises: f3a4b5c6d7e8
Create Date: 2026-11-01 20:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, Sequence[str], None] = 'f3a4b5c6d7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create legal_terms table
    if 'legal_terms' not in tables:
        op.create_table(
            'legal_terms',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('term_en', sa.String(length=150), nullable=False, index=True),
            sa.Column('term_hi', sa.String(length=150), nullable=False, index=True),
            sa.Column('term_mr', sa.String(length=150), nullable=False, index=True),
            sa.Column('plain_explanation_en', sa.Text(), nullable=False),
            sa.Column('plain_explanation_hi', sa.Text(), nullable=True),
            sa.Column('plain_explanation_mr', sa.Text(), nullable=True),
            sa.Column('legal_provision_new', sa.String(length=100), nullable=True),
            sa.Column('legal_provision_old', sa.String(length=100), nullable=True),
            sa.Column('category', sa.String(length=50), nullable=False, index=True),
            sa.Column('is_verified', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('verified_by', sa.String(length=100), server_default='Special Legal Advisor', nullable=True),
            sa.Column('version', sa.Integer(), server_default='1', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )

    # 2. Create person_aliases table
    if 'person_aliases' not in tables:
        op.create_table(
            'person_aliases',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('person_id', sa.Integer(), sa.ForeignKey('case_persons.id', ondelete='CASCADE'), nullable=True, index=True),
            sa.Column('canonical_name', sa.String(length=150), nullable=False, index=True),
            sa.Column('alias_name', sa.String(length=150), nullable=False, index=True),
            sa.Column('script', sa.String(length=30), server_default='devanagari', nullable=False),
            sa.Column('phonetic_key', sa.String(length=64), nullable=False, index=True),
            sa.Column('source_exhibit_id', sa.Integer(), sa.ForeignKey('evidence.id', ondelete='SET NULL'), nullable=True),
            sa.Column('confirmed_by', sa.String(length=100), nullable=True),
            sa.Column('is_verified', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )

    # 3. Create intake_items table
    if 'intake_items' not in tables:
        op.create_table(
            'intake_items',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('channel', sa.String(length=50), nullable=False, index=True),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('original_file_name', sa.String(length=255), nullable=True),
            sa.Column('storage_path', sa.String(length=500), nullable=True),
            sa.Column('file_hash', sa.String(length=64), nullable=True),
            sa.Column('file_size_bytes', sa.Integer(), server_default='0', nullable=False),
            sa.Column('mime_type', sa.String(length=100), nullable=True),
            sa.Column('detected_language', sa.String(length=20), server_default='mr', nullable=False),
            sa.Column('detected_script', sa.String(length=30), server_default='devanagari', nullable=False),
            sa.Column('status', sa.String(length=50), server_default='ready_for_review', nullable=False, index=True),
            sa.Column('confidence_score', sa.Float(), server_default='0.85', nullable=False),
            sa.Column('proposed_fields', sa.Text(), nullable=False),
            sa.Column('raw_text', sa.Text(), nullable=True),
            sa.Column('submitter_name', sa.String(length=150), server_default='Officer on Duty', nullable=False),
            sa.Column('submitter_role', sa.String(length=50), server_default='lead_investigator', nullable=False),
            sa.Column('reviewed_by', sa.String(length=150), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('review_notes', sa.Text(), nullable=True),
            sa.Column('applied_entities_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )

    # 4. Create intake_feedback table
    if 'intake_feedback' not in tables:
        op.create_table(
            'intake_feedback',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('intake_item_id', sa.Integer(), sa.ForeignKey('intake_items.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('channel', sa.String(length=50), nullable=False),
            sa.Column('language', sa.String(length=20), server_default='mr', nullable=False),
            sa.Column('field_group', sa.String(length=50), nullable=False),
            sa.Column('field_key', sa.String(length=100), nullable=False),
            sa.Column('ai_proposed_value', sa.Text(), nullable=True),
            sa.Column('final_confirmed_value', sa.Text(), nullable=True),
            sa.Column('was_edited', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('is_rejected', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('correction_notes', sa.Text(), nullable=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('user_name', sa.String(length=150), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    for tbl in ['intake_feedback', 'intake_items', 'person_aliases', 'legal_terms']:
        if tbl in tables:
            op.drop_table(tbl)

