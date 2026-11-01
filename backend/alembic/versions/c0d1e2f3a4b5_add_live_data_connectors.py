"""add live data connectors and connector ingest records

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-10-30 17:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c0d1e2f3a4b5'
down_revision = 'b9c0d1e2f3a4'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create data_connectors table
    op.create_table(
        'data_connectors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('connector_type', sa.String(length=50), nullable=False),
        sa.Column('source_identifier', sa.String(length=255), nullable=False),
        sa.Column('config_json', sa.Text(), nullable=True),
        sa.Column('webhook_token', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='idle'),
        sa.Column('last_polled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_ingest_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('items_ingested_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_connectors_id'), 'data_connectors', ['id'], unique=False)
    op.create_index(op.f('ix_data_connectors_webhook_token'), 'data_connectors', ['webhook_token'], unique=True)

    # 2. Create connector_ingest_records table
    op.create_table(
        'connector_ingest_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('connector_id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('evidence_id', sa.Integer(), nullable=True),
        sa.Column('source_system', sa.String(length=255), nullable=False),
        sa.Column('source_filename', sa.String(length=255), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('receipt_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='success'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('details_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['connector_id'], ['data_connectors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_connector_ingest_records_id'), 'connector_ingest_records', ['id'], unique=False)

    # 3. Add connector attribution columns to evidence
    try:
        op.add_column('evidence', sa.Column('connector_id', sa.Integer(), nullable=True))
        op.add_column('evidence', sa.Column('connector_type', sa.String(length=50), nullable=True))
        op.add_column('evidence', sa.Column('connector_source_system', sa.String(length=255), nullable=True))
        op.add_column('evidence', sa.Column('connector_receipt_time', sa.DateTime(timezone=True), nullable=True))
    except Exception:
        pass


def downgrade():
    try:
        op.drop_column('evidence', 'connector_receipt_time')
        op.drop_column('evidence', 'connector_source_system')
        op.drop_column('evidence', 'connector_type')
        op.drop_column('evidence', 'connector_id')
    except Exception:
        pass
    op.drop_index(op.f('ix_connector_ingest_records_id'), table_name='connector_ingest_records')
    op.drop_table('connector_ingest_records')
    op.drop_index(op.f('ix_data_connectors_webhook_token'), table_name='data_connectors')
    op.drop_index(op.f('ix_data_connectors_id'), table_name='data_connectors')
    op.drop_table('data_connectors')

