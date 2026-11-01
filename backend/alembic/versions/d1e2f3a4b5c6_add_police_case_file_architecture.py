"""add police case file architecture

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-11-01 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1e2f3a4b5c6'
down_revision = 'c0d1e2f3a4b5'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Alter cases table to add police docket header columns
    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.add_column(sa.Column('crime_number', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('police_station', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('district', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('state', sa.String(length=100), server_default='Maharashtra', nullable=True))
        batch_op.add_column(sa.Column('investigating_officer_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('investigating_officer_name', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('supervising_officer_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('supervising_officer_name', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('court_name', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('next_hearing_date', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('next_hearing_purpose', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('bail_status', sa.String(length=50), server_default='None', nullable=True))
        batch_op.add_column(sa.Column('custody_status', sa.String(length=50), server_default='Under Investigation', nullable=True))
        batch_op.add_column(sa.Column('case_stage', sa.String(length=50), server_default='under_investigation', nullable=True))

    # 2. Alter evidence table to add police typed document columns
    with op.batch_alter_table('evidence', schema=None) as batch_op:
        batch_op.add_column(sa.Column('document_type', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('type_details', sa.Text(), nullable=True))

    # 3. Create police_station_lookups table
    op.create_table(
        'police_station_lookups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('station_code', sa.String(length=50), nullable=True),
        sa.Column('district', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=100), server_default='Maharashtra', nullable=False),
        sa.Column('contact_number', sa.String(length=50), nullable=True),
        sa.Column('sp_office', sa.String(length=150), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_police_station_lookups_name'), 'police_station_lookups', ['name'], unique=True)
    op.create_index(op.f('ix_police_station_lookups_district'), 'police_station_lookups', ['district'], unique=False)

    # 4. Create case_persons table
    op.create_table(
        'case_persons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('aliases', sa.String(length=200), nullable=True),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('father_or_spouse_name', sa.String(length=150), nullable=True),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('gender', sa.String(length=20), nullable=True),
        sa.Column('contact_info', sa.Text(), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('is_important', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('linked_entity_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['linked_entity_id'], ['entities.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_case_persons_case_id'), 'case_persons', ['case_id'], unique=False)
    op.create_index(op.f('ix_case_persons_name'), 'case_persons', ['name'], unique=False)
    op.create_index(op.f('ix_case_persons_role'), 'case_persons', ['role'], unique=False)

    # 5. Create accused_status_history table
    op.create_table(
        'accused_status_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('status_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('order_reference', sa.String(length=150), nullable=True),
        sa.Column('custody_days_served', sa.Integer(), server_default='0', nullable=False),
        sa.Column('remand_expiry_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('statutory_filing_deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['person_id'], ['case_persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_accused_status_history_case_id'), 'accused_status_history', ['case_id'], unique=False)
    op.create_index(op.f('ix_accused_status_history_person_id'), 'accused_status_history', ['person_id'], unique=False)

    # 6. Create person_statements table
    op.create_table(
        'person_statements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=False),
        sa.Column('statement_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='recorded', nullable=False),
        sa.Column('statement_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('statement_time', sa.String(length=20), nullable=True),
        sa.Column('place', sa.String(length=200), nullable=True),
        sa.Column('recorded_by', sa.String(length=120), nullable=True),
        sa.Column('language', sa.String(length=50), server_default='Marathi', nullable=True),
        sa.Column('read_over_and_signed', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('magistrate_name', sa.String(length=120), nullable=True),
        sa.Column('linked_evidence_id', sa.Integer(), nullable=True),
        sa.Column('linked_interview_id', sa.Integer(), nullable=True),
        sa.Column('statement_text', sa.Text(), nullable=True),
        sa.Column('key_claims', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['person_id'], ['case_persons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['linked_evidence_id'], ['evidence.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_person_statements_case_id'), 'person_statements', ['case_id'], unique=False)
    op.create_index(op.f('ix_person_statements_person_id'), 'person_statements', ['person_id'], unique=False)

    # 7. Create document_type_definitions table
    op.create_table(
        'document_type_definitions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('label', sa.String(length=120), nullable=False),
        sa.Column('legal_provision', sa.String(length=120), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('required_fields_json', sa.Text(), nullable=False),
        sa.Column('standard_guidance', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_type_definitions_code'), 'document_type_definitions', ['code'], unique=True)

    # 8. Create case_diary_entries table
    op.create_table(
        'case_diary_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('entry_date', sa.Date(), nullable=False),
        sa.Column('serial_number', sa.Integer(), server_default='1', nullable=False),
        sa.Column('time_from', sa.String(length=10), nullable=True),
        sa.Column('time_to', sa.String(length=10), nullable=True),
        sa.Column('place', sa.String(length=200), nullable=True),
        sa.Column('officer_id', sa.Integer(), nullable=True),
        sa.Column('officer_name', sa.String(length=120), nullable=False),
        sa.Column('activities', sa.Text(), nullable=False),
        sa.Column('persons_examined_json', sa.Text(), nullable=True),
        sa.Column('places_visited_json', sa.Text(), nullable=True),
        sa.Column('items_seized_json', sa.Text(), nullable=True),
        sa.Column('instructions_given', sa.Text(), nullable=True),
        sa.Column('next_steps', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='draft', nullable=False),
        sa.Column('signature_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('signature_hash', sa.String(length=64), nullable=True),
        sa.Column('supervisor_notes', sa.Text(), nullable=True),
        sa.Column('parent_entry_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['officer_id'], ['users.id']),
        sa.ForeignKeyConstraint(['parent_entry_id'], ['case_diary_entries.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_case_diary_entries_case_id'), 'case_diary_entries', ['case_id'], unique=False)
    op.create_index(op.f('ix_case_diary_entries_entry_date'), 'case_diary_entries', ['entry_date'], unique=False)

    # 9. Create case_sections table
    op.create_table(
        'case_sections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('act', sa.String(length=50), server_default='BNS', nullable=False),
        sa.Column('section_code', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('punishment_tier', sa.String(length=50), server_default='life_or_death_over_10_years', nullable=False),
        sa.Column('status', sa.String(length=30), server_default='initial', nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('deciding_officer', sa.String(length=120), nullable=True),
        sa.Column('effective_date', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('supervisor_approval', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('supervisor_notes', sa.Text(), nullable=True),
        sa.Column('court_informed_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('court_intimation_memo', sa.String(length=120), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_case_sections_case_id'), 'case_sections', ['case_id'], unique=False)
    op.create_index(op.f('ix_case_sections_section_code'), 'case_sections', ['section_code'], unique=False)

    # 10. Create section_elements table
    op.create_table(
        'section_elements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_section_id', sa.Integer(), nullable=False),
        sa.Column('element_text', sa.String(length=255), nullable=False),
        sa.Column('supporting_evidence_ids', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=30), server_default='missing', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['case_section_id'], ['case_sections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_section_elements_case_section_id'), 'section_elements', ['case_section_id'], unique=False)


def downgrade():
    op.drop_table('section_elements')
    op.drop_table('case_sections')
    op.drop_table('case_diary_entries')
    op.drop_table('document_type_definitions')
    op.drop_table('person_statements')
    op.drop_table('accused_status_history')
    op.drop_table('case_persons')
    op.drop_table('police_station_lookups')

    with op.batch_alter_table('evidence', schema=None) as batch_op:
        batch_op.drop_column('type_details')
        batch_op.drop_column('document_type')

    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.drop_column('case_stage')
        batch_op.drop_column('custody_status')
        batch_op.drop_column('bail_status')
        batch_op.drop_column('next_hearing_purpose')
        batch_op.drop_column('next_hearing_date')
        batch_op.drop_column('court_name')
        batch_op.drop_column('supervising_officer_name')
        batch_op.drop_column('supervising_officer_id')
        batch_op.drop_column('investigating_officer_name')
        batch_op.drop_column('investigating_officer_id')
        batch_op.drop_column('state')
        batch_op.drop_column('district')
        batch_op.drop_column('police_station')
        batch_op.drop_column('crime_number')

