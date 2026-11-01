"""add offline sync and notifications

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f7
Create Date: 2026-11-01 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5a6'
down_revision = 'a1b2c3d4e5f7'
branch_labels = None
depends_on = None


def upgrade():
    # 1. sync_idempotency_records
    op.create_table(
        'sync_idempotency_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('idempotency_key', sa.String(length=100), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('endpoint', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('device_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('server_receipt_timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('result_summary', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sync_idempotency_records_idempotency_key'), 'sync_idempotency_records', ['idempotency_key'], unique=True)
    op.create_index(op.f('ix_sync_idempotency_records_case_id'), 'sync_idempotency_records', ['case_id'], unique=False)

    # 2. notification_logs
    op.create_table(
        'notification_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=True),
        sa.Column('channel', sa.String(length=32), nullable=False),
        sa.Column('recipient_address', sa.String(length=150), nullable=False),
        sa.Column('message_template_id', sa.String(length=64), nullable=False),
        sa.Column('message_content', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('provider_ref', sa.String(length=100), nullable=True),
        sa.Column('attempts', sa.Integer(), server_default='1', nullable=False),
        sa.Column('escalated_to_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['alert_id'], ['alerts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notification_logs_user_id'), 'notification_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_notification_logs_case_id'), 'notification_logs', ['case_id'], unique=False)
    op.create_index(op.f('ix_notification_logs_channel'), 'notification_logs', ['channel'], unique=False)
    op.create_index(op.f('ix_notification_logs_status'), 'notification_logs', ['status'], unique=False)


def downgrade():
    op.drop_table('notification_logs')
    op.drop_table('sync_idempotency_records')

