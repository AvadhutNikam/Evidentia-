"""add_private_model_and_security_upgrades

Revision ID: f7a1b2c3d4e5
Revises: e5f6a1b2c3d4
Create Date: 2026-10-29 23:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a1b2c3d4e5'
down_revision: Union[str, None] = 'e5f6a1b2c3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add airgap, retention, and legal hold columns to cases
    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_sensitive_airgapped', sa.Boolean(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('ai_provider_override', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('local_ai_endpoint', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('local_ai_model', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('retention_period_years', sa.Integer(), server_default='20', nullable=False))
        batch_op.add_column(sa.Column('retention_expiry_date', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('is_legal_hold', sa.Boolean(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('legal_hold_reason', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('legal_hold_placed_by', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('legal_hold_placed_at', sa.DateTime(timezone=True), nullable=True))

    # 2. Add 2FA and shorter session columns to users
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_2fa_enabled', sa.Boolean(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('totp_secret', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('backup_codes', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('session_duration_minutes', sa.Integer(), server_default='15', nullable=False))

    # 3. Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_token_hash', sa.String(length=64), nullable=False),
        sa.Column('device_info', sa.String(length=255), server_default='Unknown Device', nullable=True),
        sa.Column('ip_address', sa.String(length=64), server_default='127.0.0.1', nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_active_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), server_default='0', nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_sessions_id'), 'user_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_sessions_session_token_hash'), 'user_sessions', ['session_token_hash'], unique=False)

    # 4. Create system_security_configs table
    op.create_table(
        'system_security_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('default_ai_provider', sa.String(length=50), server_default='cloud_gemini', nullable=False),
        sa.Column('local_model_endpoint', sa.String(length=255), server_default='http://localhost:11434/v1', nullable=False),
        sa.Column('local_model_name', sa.String(length=100), server_default='llama3', nullable=False),
        sa.Column('allow_external_ai_global', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('default_session_duration_minutes', sa.Integer(), server_default='15', nullable=False),
        sa.Column('require_2fa_for_admins', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_by', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_security_configs_id'), 'system_security_configs', ['id'], unique=False)

    # 5. Create backup_records table
    op.create_table(
        'backup_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('backup_filename', sa.String(length=255), nullable=False),
        sa.Column('backup_type', sa.String(length=50), server_default='full', nullable=False),
        sa.Column('size_bytes', sa.Integer(), server_default='0', nullable=False),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_by', sa.String(length=100), server_default='system', nullable=False),
        sa.Column('restore_test_status', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('restore_test_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('restore_test_notes', sa.Text(), nullable=True),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_backup_records_id'), 'backup_records', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_backup_records_id'), table_name='backup_records')
    op.drop_table('backup_records')
    op.drop_index(op.f('ix_system_security_configs_id'), table_name='system_security_configs')
    op.drop_table('system_security_configs')
    op.drop_index(op.f('ix_user_sessions_session_token_hash'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_user_id'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_id'), table_name='user_sessions')
    op.drop_table('user_sessions')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('session_duration_minutes')
        batch_op.drop_column('backup_codes')
        batch_op.drop_column('totp_secret')
        batch_op.drop_column('is_2fa_enabled')

    with op.batch_alter_table('cases', schema=None) as batch_op:
        batch_op.drop_column('legal_hold_placed_at')
        batch_op.drop_column('legal_hold_placed_by')
        batch_op.drop_column('legal_hold_reason')
        batch_op.drop_column('is_legal_hold')
        batch_op.drop_column('retention_expiry_date')
        batch_op.drop_column('retention_period_years')
        batch_op.drop_column('local_ai_model')
        batch_op.drop_column('local_ai_endpoint')
        batch_op.drop_column('ai_provider_override')
        batch_op.drop_column('is_sensitive_airgapped')

