"""add_mobile_field_evidence_capture

Revision ID: a8b9c0d1e2f3
Revises: f7a1b2c3d4e5
Create Date: 2026-10-30 00:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8b9c0d1e2f3'
down_revision: Union[str, None] = 'f7a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('evidence', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_field_captured', sa.Boolean(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('capture_source', sa.String(length=50), server_default='web_upload', nullable=False))
        batch_op.add_column(sa.Column('field_latitude', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('field_longitude', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('field_accuracy_meters', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('field_captured_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('field_device_info', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('field_location_name', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('field_tamper_seal_number', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('field_officer_confirmed', sa.Boolean(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('field_officer_declaration', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('client_computed_hash', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('hash_match_verified', sa.Boolean(), server_default='0', nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('evidence', schema=None) as batch_op:
        batch_op.drop_column('hash_match_verified')
        batch_op.drop_column('client_computed_hash')
        batch_op.drop_column('field_officer_declaration')
        batch_op.drop_column('field_officer_confirmed')
        batch_op.drop_column('field_tamper_seal_number')
        batch_op.drop_column('field_location_name')
        batch_op.drop_column('field_device_info')
        batch_op.drop_column('field_captured_at')
        batch_op.drop_column('field_accuracy_meters')
        batch_op.drop_column('field_longitude')
        batch_op.drop_column('field_latitude')
        batch_op.drop_column('capture_source')
        batch_op.drop_column('is_field_captured')

