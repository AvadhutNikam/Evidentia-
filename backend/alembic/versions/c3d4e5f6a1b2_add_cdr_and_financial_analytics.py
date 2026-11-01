"""add_cdr_and_financial_analytics

Revision ID: c3d4e5f6a1b2
Revises: b2c3d4e5f6a1
Create Date: 2026-10-29 20:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a1b2'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create cdr_records table
    if 'cdr_records' not in tables:
        op.create_table(
            'cdr_records',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('evidence_id', sa.Integer(), sa.ForeignKey('evidence.id', ondelete='CASCADE'), nullable=True, index=True),
            sa.Column('source_file_name', sa.String(), nullable=False),
            sa.Column('row_number', sa.Integer(), nullable=False, index=True),
            sa.Column('calling_number', sa.String(64), nullable=False, index=True),
            sa.Column('called_number', sa.String(64), nullable=True, index=True),
            sa.Column('call_datetime', sa.DateTime(timezone=True), nullable=False, index=True),
            sa.Column('call_duration_sec', sa.Integer(), server_default='0', nullable=False),
            sa.Column('call_type', sa.String(32), server_default='voice', nullable=False),
            sa.Column('imei', sa.String(32), nullable=True, index=True),
            sa.Column('imsi', sa.String(32), nullable=True, index=True),
            sa.Column('cell_id', sa.String(64), nullable=False, index=True),
            sa.Column('azimuth', sa.Float(), nullable=True),
            sa.Column('site_name', sa.String(255), nullable=True),
            sa.Column('latitude', sa.Float(), nullable=True),
            sa.Column('longitude', sa.Float(), nullable=True),
            sa.Column('raw_data_json', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )
        op.create_index('ix_cdr_case_cell', 'cdr_records', ['case_id', 'cell_id'])
        op.create_index('ix_cdr_case_time', 'cdr_records', ['case_id', 'call_datetime'])

    # 2. Create bank_transactions table
    if 'bank_transactions' not in tables:
        op.create_table(
            'bank_transactions',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('evidence_id', sa.Integer(), sa.ForeignKey('evidence.id', ondelete='CASCADE'), nullable=True, index=True),
            sa.Column('source_file_name', sa.String(), nullable=False),
            sa.Column('row_number', sa.Integer(), nullable=False, index=True),
            sa.Column('transaction_date', sa.DateTime(timezone=True), nullable=False, index=True),
            sa.Column('value_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('reference_number', sa.String(128), nullable=True, index=True),
            sa.Column('debit_amount', sa.Float(), server_default='0.0', nullable=False),
            sa.Column('credit_amount', sa.Float(), server_default='0.0', nullable=False),
            sa.Column('balance', sa.Float(), nullable=True),
            sa.Column('account_number', sa.String(64), nullable=False, index=True),
            sa.Column('counterparty_account', sa.String(64), nullable=True, index=True),
            sa.Column('counterparty_name', sa.String(128), nullable=True, index=True),
            sa.Column('bank_name', sa.String(64), nullable=True),
            sa.Column('transaction_mode', sa.String(32), server_default='TRANSFER', nullable=False),
            sa.Column('raw_data_json', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )
        op.create_index('ix_bank_case_acc', 'bank_transactions', ['case_id', 'account_number'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'bank_transactions' in tables:
        op.drop_table('bank_transactions')
    if 'cdr_records' in tables:
        op.drop_table('cdr_records')

