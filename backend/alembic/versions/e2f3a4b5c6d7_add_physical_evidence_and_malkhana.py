"""add physical evidence and malkhana

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-11-01 18:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2f3a4b5c6d7'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Alter evidence table to support physical evidence items
    with op.batch_alter_table('evidence', schema=None) as batch_op:
        batch_op.add_column(sa.Column('evidence_kind', sa.String(length=20), server_default='digital', nullable=False))
        batch_op.alter_column('file_name', existing_type=sa.String(), nullable=True)

    # 2. Alter custody_logs table to support extended chained ledger
    with op.batch_alter_table('custody_logs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('from_person_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('from_person_name', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('from_location', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('to_person_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('to_person_name', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('to_location', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('purpose', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('condition_at_handover', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('seal_status_check', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('expected_return_date', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('authority_order_ref', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('acknowledgement_type', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('acknowledgement_data', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('attached_photos', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('previous_log_hash', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('current_log_hash', sa.String(length=64), nullable=True))

    # 3. Create physical_items table
    op.create_table(
        'physical_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('evidence_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('identifying_marks', sa.Text(), nullable=True),
        sa.Column('quantity_or_weight', sa.String(length=100), nullable=True),
        sa.Column('condition', sa.String(length=100), server_default='intact', nullable=False),
        sa.Column('packaging', sa.String(length=100), server_default='sealed_plastic_bag', nullable=False),
        sa.Column('seized_from', sa.String(length=255), nullable=True),
        sa.Column('seized_at', sa.String(length=255), nullable=True),
        sa.Column('seized_by_id', sa.Integer(), nullable=True),
        sa.Column('seized_by_name', sa.String(length=255), nullable=True),
        sa.Column('seizure_memo_id', sa.Integer(), nullable=True),
        sa.Column('panch_witness_1_id', sa.Integer(), nullable=True),
        sa.Column('panch_witness_2_id', sa.Integer(), nullable=True),
        sa.Column('current_location', sa.String(length=100), server_default='malkhana', nullable=False),
        sa.Column('current_custodian', sa.String(length=255), nullable=True),
        sa.Column('malkhana_entry_number', sa.String(length=100), nullable=True),
        sa.Column('rack_or_shelf', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='deposited_malkhana', nullable=False),
        sa.Column('is_perishable', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('is_biological', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('is_firearm', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('is_narcotics', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('dispatch_time_limit_days', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['seized_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['seizure_memo_id'], ['evidence.id'], ),
        sa.ForeignKeyConstraint(['panch_witness_1_id'], ['case_persons.id'], ),
        sa.ForeignKeyConstraint(['panch_witness_2_id'], ['case_persons.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('evidence_id')
    )
    with op.batch_alter_table('physical_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_physical_items_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_physical_items_evidence_id'), ['evidence_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_physical_items_malkhana_entry_number'), ['malkhana_entry_number'], unique=False)

    # 4. Create seals table
    op.create_table(
        'seals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('evidence_id', sa.Integer(), nullable=False),
        sa.Column('seal_number', sa.String(length=100), nullable=False),
        sa.Column('owner_mark', sa.String(length=255), nullable=False),
        sa.Column('package_description', sa.String(length=255), nullable=True),
        sa.Column('applied_by_id', sa.Integer(), nullable=True),
        sa.Column('applied_by_name', sa.String(length=255), nullable=False),
        sa.Column('applied_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('applied_in_presence_of', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='intact', nullable=False),
        sa.Column('replaced_seal_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['applied_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['replaced_seal_id'], ['seals.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('seals', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_seals_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_seals_case_id'), ['case_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_seals_evidence_id'), ['evidence_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_seals_seal_number'), ['seal_number'], unique=False)

    # 5. Create seal_events table
    op.create_table(
        'seal_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('seal_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('actor_name', sa.String(length=255), nullable=False),
        sa.Column('witnesses', sa.Text(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('new_seal_id', sa.Integer(), nullable=True),
        sa.Column('photos', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['seal_id'], ['seals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['new_seal_id'], ['seals.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('seal_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_seal_events_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_seal_events_seal_id'), ['seal_id'], unique=False)

    # 6. Create fsl_dispatches table
    op.create_table(
        'fsl_dispatches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('forwarding_letter_number', sa.String(length=100), nullable=False),
        sa.Column('forwarding_letter_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('fsl_name', sa.String(length=255), nullable=False),
        sa.Column('examination_requested', sa.String(length=255), nullable=False),
        sa.Column('sent_date', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('carried_by_name', sa.String(length=255), nullable=False),
        sa.Column('carried_by_role', sa.String(length=100), nullable=True),
        sa.Column('carried_by_id_card', sa.String(length=100), nullable=True),
        sa.Column('mode_of_transit', sa.String(length=50), server_default='police_messenger', nullable=False),
        sa.Column('expected_report_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='prepared', nullable=False),
        sa.Column('lab_acknowledgement_receipt_path', sa.String(length=500), nullable=True),
        sa.Column('lab_acknowledgement_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('report_evidence_id', sa.Integer(), nullable=True),
        sa.Column('return_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('return_carried_by', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['report_evidence_id'], ['evidence.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('fsl_dispatches', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_fsl_dispatches_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_fsl_dispatches_case_id'), ['case_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_fsl_dispatches_forwarding_letter_number'), ['forwarding_letter_number'], unique=False)

    # 7. Create fsl_dispatch_items table
    op.create_table(
        'fsl_dispatch_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dispatch_id', sa.Integer(), nullable=False),
        sa.Column('evidence_id', sa.Integer(), nullable=False),
        sa.Column('seal_number_at_dispatch', sa.String(length=100), nullable=False),
        sa.Column('seal_status_at_dispatch', sa.String(length=50), server_default='intact', nullable=False),
        sa.Column('return_seal_number', sa.String(length=100), nullable=True),
        sa.Column('return_seal_status', sa.String(length=50), nullable=True),
        sa.Column('condition_on_return', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['dispatch_id'], ['fsl_dispatches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('fsl_dispatch_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_fsl_dispatch_items_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_fsl_dispatch_items_dispatch_id'), ['dispatch_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_fsl_dispatch_items_evidence_id'), ['evidence_id'], unique=False)

    # 8. Create malkhana_stock_checks table
    op.create_table(
        'malkhana_stock_checks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('police_station', sa.String(length=100), nullable=False),
        sa.Column('check_date', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('conducted_by_id', sa.Integer(), nullable=True),
        sa.Column('conducted_by_name', sa.String(length=255), nullable=False),
        sa.Column('total_items_expected', sa.Integer(), server_default='0', nullable=False),
        sa.Column('items_verified_present', sa.Integer(), server_default='0', nullable=False),
        sa.Column('discrepancies_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('discrepancies_details', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='in_progress', nullable=False),
        sa.Column('supervisor_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['conducted_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('malkhana_stock_checks', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_malkhana_stock_checks_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_malkhana_stock_checks_police_station'), ['police_station'], unique=False)


def downgrade():
    op.drop_table('malkhana_stock_checks')
    op.drop_table('fsl_dispatch_items')
    op.drop_table('fsl_dispatches')
    op.drop_table('seal_events')
    op.drop_table('seals')
    op.drop_table('physical_items')

    with op.batch_alter_table('custody_logs', schema=None) as batch_op:
        batch_op.drop_column('current_log_hash')
        batch_op.drop_column('previous_log_hash')
        batch_op.drop_column('attached_photos')
        batch_op.drop_column('acknowledgement_data')
        batch_op.drop_column('acknowledgement_type')
        batch_op.drop_column('authority_order_ref')
        batch_op.drop_column('expected_return_date')
        batch_op.drop_column('seal_status_check')
        batch_op.drop_column('condition_at_handover')
        batch_op.drop_column('purpose')
        batch_op.drop_column('to_location')
        batch_op.drop_column('to_person_name')
        batch_op.drop_column('to_person_id')
        batch_op.drop_column('from_location')
        batch_op.drop_column('from_person_name')
        batch_op.drop_column('from_person_id')

    with op.batch_alter_table('evidence', schema=None) as batch_op:
        batch_op.drop_column('evidence_kind')

