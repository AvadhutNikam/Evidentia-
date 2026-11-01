"""add_procedure_rules_and_checklist

Revision ID: e5f9a231b8c2
Revises: d4b8e192f7a1
Create Date: 2026-10-29 18:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f9a231b8c2'
down_revision: Union[str, Sequence[str], None] = 'd4b8e192f7a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Add procedure & expert review columns to statutory_deadline_rules
    if 'statutory_deadline_rules' in tables:
        rule_cols = [c['name'] for c in inspector.get_columns('statutory_deadline_rules')]
        with op.batch_alter_table('statutory_deadline_rules') as batch_op:
            if 'procedure_name' not in rule_cols:
                batch_op.add_column(sa.Column('procedure_name', sa.String(), server_default='Charge Sheet Submission', nullable=True))
            if 'is_reviewed_by_expert' not in rule_cols:
                batch_op.add_column(sa.Column('is_reviewed_by_expert', sa.Boolean(), server_default='1', nullable=False))
            if 'expert_reviewer' not in rule_cols:
                batch_op.add_column(sa.Column('expert_reviewer', sa.String(), server_default='Special Public Prosecutor & Criminal Procedure Legal Board', nullable=True))
            if 'legal_notes' not in rule_cols:
                batch_op.add_column(sa.Column('legal_notes', sa.Text(), nullable=True))

    # 2. Create offence_evidence_protocols table
    if 'offence_evidence_protocols' not in tables:
        op.create_table(
            'offence_evidence_protocols',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('offence_category', sa.String(), nullable=False, index=True),
            sa.Column('offence_section_keywords', sa.String(), nullable=False),
            sa.Column('exhibit_code', sa.String(), nullable=False, index=True),
            sa.Column('title', sa.String(), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('mandatory', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('legal_provision', sa.String(), nullable=False),
            sa.Column('matching_keywords', sa.Text(), nullable=False),
            sa.Column('consequence_if_missing', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'offence_evidence_protocols' in tables:
        op.drop_table('offence_evidence_protocols')

    if 'statutory_deadline_rules' in tables:
        rule_cols = [c['name'] for c in inspector.get_columns('statutory_deadline_rules')]
        with op.batch_alter_table('statutory_deadline_rules') as batch_op:
            if 'procedure_name' in rule_cols:
                batch_op.drop_column('procedure_name')
            if 'is_reviewed_by_expert' in rule_cols:
                batch_op.drop_column('is_reviewed_by_expert')
            if 'expert_reviewer' in rule_cols:
                batch_op.drop_column('expert_reviewer')
            if 'legal_notes' in rule_cols:
                batch_op.drop_column('legal_notes')

