"""add alibi verification workflow

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-11-01 19:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3a4b5c6d7e8'
down_revision = 'e2f3a4b5c6d7'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create alibi_claims table
    op.create_table(
        'alibi_claims',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=True),
        sa.Column('suspect_name', sa.String(length=150), nullable=False),
        sa.Column('hypothesis_id', sa.Integer(), nullable=True),
        sa.Column('claim_text', sa.Text(), nullable=False),
        sa.Column('source_statement_id', sa.Integer(), nullable=True),
        sa.Column('source_citation', sa.String(length=255), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('raised_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='open', nullable=False),
        sa.Column('final_verdict', sa.String(length=50), nullable=True),
        sa.Column('verdict_reason', sa.Text(), nullable=True),
        sa.Column('verdict_by_user_id', sa.Integer(), nullable=True),
        sa.Column('verdict_by_name', sa.String(length=150), nullable=True),
        sa.Column('verdict_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_current', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['person_id'], ['case_persons.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['hypothesis_id'], ['hypotheses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_statement_id'], ['interview_statements.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['verdict_by_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alibi_claims_case_id'), 'alibi_claims', ['case_id'], unique=False)
    op.create_index(op.f('ix_alibi_claims_person_id'), 'alibi_claims', ['person_id'], unique=False)
    op.create_index(op.f('ix_alibi_claims_suspect_name'), 'alibi_claims', ['suspect_name'], unique=False)
    op.create_index(op.f('ix_alibi_claims_hypothesis_id'), 'alibi_claims', ['hypothesis_id'], unique=False)
    op.create_index(op.f('ix_alibi_claims_status'), 'alibi_claims', ['status'], unique=False)

    # 2. Create alibi_segments table
    op.create_table(
        'alibi_segments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('claim_id', sa.Integer(), nullable=False),
        sa.Column('segment_order', sa.Integer(), server_default='1', nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('time_uncertainty_mins', sa.Integer(), server_default='15', nullable=False),
        sa.Column('claimed_place_name', sa.String(length=255), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('radius_meters', sa.Float(), server_default='500.0', nullable=False),
        sa.Column('activity', sa.String(length=255), nullable=True),
        sa.Column('travel_mode', sa.String(length=50), server_default='none', nullable=False),
        sa.Column('vouching_persons', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='unverified', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['claim_id'], ['alibi_claims.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alibi_segments_claim_id'), 'alibi_segments', ['claim_id'], unique=False)

    # 3. Create alibi_checks table
    op.create_table(
        'alibi_checks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('claim_id', sa.Integer(), nullable=False),
        sa.Column('segment_id', sa.Integer(), nullable=True),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('requirement_details', sa.Text(), nullable=False),
        sa.Column('legal_process_required', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('investigation_task_id', sa.Integer(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('owner_name', sa.String(length=150), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='to_do', nullable=False),
        sa.Column('result', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('unlocatable_reason', sa.String(length=255), nullable=True),
        sa.Column('supporting_evidence_ids', sa.Text(), nullable=True),
        sa.Column('supporting_citations', sa.Text(), nullable=True),
        sa.Column('clock_offset_seconds', sa.Integer(), server_default='0', nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('is_system_suggested', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('verified_by_id', sa.Integer(), nullable=True),
        sa.Column('verified_by_name', sa.String(length=150), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retention_warning_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['claim_id'], ['alibi_claims.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['segment_id'], ['alibi_segments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['investigation_task_id'], ['investigation_tasks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
        sa.ForeignKeyConstraint(['verified_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alibi_checks_claim_id'), 'alibi_checks', ['claim_id'], unique=False)
    op.create_index(op.f('ix_alibi_checks_segment_id'), 'alibi_checks', ['segment_id'], unique=False)
    op.create_index(op.f('ix_alibi_checks_source_type'), 'alibi_checks', ['source_type'], unique=False)
    op.create_index(op.f('ix_alibi_checks_status'), 'alibi_checks', ['status'], unique=False)
    op.create_index(op.f('ix_alibi_checks_result'), 'alibi_checks', ['result'], unique=False)

    # 4. Create statement_comparisons table
    op.create_table(
        'statement_comparisons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('claim_id', sa.Integer(), nullable=False),
        sa.Column('statement_id', sa.Integer(), nullable=True),
        sa.Column('line_number', sa.Integer(), nullable=False),
        sa.Column('statement_text', sa.Text(), nullable=False),
        sa.Column('quote_citation', sa.String(length=255), nullable=True),
        sa.Column('extracted_facts', sa.Text(), nullable=True),
        sa.Column('result', sa.String(length=50), server_default='unverified', nullable=False),
        sa.Column('matched_evidence_ids', sa.Text(), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('review_state', sa.String(length=50), server_default='proposed', nullable=False),
        sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['claim_id'], ['alibi_claims.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['statement_id'], ['interview_statements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_statement_comparisons_claim_id'), 'statement_comparisons', ['claim_id'], unique=False)
    op.create_index(op.f('ix_statement_comparisons_statement_id'), 'statement_comparisons', ['statement_id'], unique=False)


def downgrade():
    op.drop_table('statement_comparisons')
    op.drop_table('alibi_checks')
    op.drop_table('alibi_segments')
    op.drop_table('alibi_claims')

