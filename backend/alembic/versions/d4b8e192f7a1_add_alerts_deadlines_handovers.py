"""add_alerts_deadlines_handovers

Revision ID: d4b8e192f7a1
Revises: c7e12f845a90
Create Date: 2026-10-29 18:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4b8e192f7a1'
down_revision: Union[str, Sequence[str], None] = 'c7e12f845a90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Add statutory date and offence columns to cases table if not present
    if 'cases' in tables:
        case_cols = [c['name'] for c in inspector.get_columns('cases')]
        with op.batch_alter_table('cases') as batch_op:
            if 'fir_number' not in case_cols:
                batch_op.add_column(sa.Column('fir_number', sa.String(), nullable=True))
            if 'fir_date' not in case_cols:
                batch_op.add_column(sa.Column('fir_date', sa.DateTime(timezone=True), nullable=True))
            if 'incident_date' not in case_cols:
                batch_op.add_column(sa.Column('incident_date', sa.DateTime(timezone=True), nullable=True))
            if 'arrest_date' not in case_cols:
                batch_op.add_column(sa.Column('arrest_date', sa.DateTime(timezone=True), nullable=True))
            if 'remand_date' not in case_cols:
                batch_op.add_column(sa.Column('remand_date', sa.DateTime(timezone=True), nullable=True))
            if 'offence_section' not in case_cols:
                batch_op.add_column(sa.Column('offence_section', sa.String(), nullable=True))
            if 'statutory_time_limit_days' not in case_cols:
                batch_op.add_column(sa.Column('statutory_time_limit_days', sa.Integer(), server_default='90', nullable=True))

    # 2. alerts table
    if 'alerts' not in tables:
        op.create_table(
            'alerts',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('rule_type', sa.String(), nullable=False, index=True),
            sa.Column('severity', sa.String(), server_default='warning', nullable=False, index=True),
            sa.Column('title', sa.String(), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('linked_item_type', sa.String(), nullable=True),
            sa.Column('linked_item_id', sa.String(), nullable=True),
            sa.Column('status', sa.String(), server_default='unread', nullable=False, index=True),
            sa.Column('dedup_key', sa.String(), nullable=False, index=True),
            sa.Column('is_restricted', sa.Boolean(), server_default=sa.text('0'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
            sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('acknowledged_by', sa.String(), nullable=True),
            sa.Column('snoozed_until', sa.DateTime(timezone=True), nullable=True, index=True),
            sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('resolution_reason', sa.Text(), nullable=True)
        )

    # 3. alert_rule_configs table
    if 'alert_rule_configs' not in tables:
        op.create_table(
            'alert_rule_configs',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('rule_type', sa.String(), unique=True, nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('description', sa.String(), nullable=True),
            sa.Column('is_enabled', sa.Boolean(), server_default=sa.text('1'), nullable=False),
            sa.Column('severity_default', sa.String(), server_default='warning', nullable=False),
            sa.Column('threshold_val', sa.Float(), nullable=True),
            sa.Column('recipients_role', sa.String(), server_default='all', nullable=False),
            sa.Column('auto_resolve', sa.Boolean(), server_default=sa.text('1'), nullable=False)
        )

    # 4. notification_preferences table
    if 'notification_preferences' not in tables:
        op.create_table(
            'notification_preferences',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('rule_type', sa.String(), server_default='all', nullable=False),
            sa.Column('in_app_enabled', sa.Boolean(), server_default=sa.text('1'), nullable=False),
            sa.Column('email_enabled', sa.Boolean(), server_default=sa.text('0'), nullable=False),
            sa.Column('digest_mode', sa.String(), server_default='immediate', nullable=False),
            sa.Column('quiet_hours_start', sa.String(), nullable=True),
            sa.Column('quiet_hours_end', sa.String(), nullable=True)
        )

    # 5. statutory_deadline_rules table
    if 'statutory_deadline_rules' not in tables:
        op.create_table(
            'statutory_deadline_rules',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('statute_name', sa.String(), nullable=False),
            sa.Column('section_reference', sa.String(), nullable=False),
            sa.Column('offence_category', sa.String(), nullable=False),
            sa.Column('limit_days', sa.Integer(), nullable=False),
            sa.Column('trigger_event', sa.String(), nullable=False),
            sa.Column('description', sa.String(), nullable=False)
        )

    # 6. case_deadlines table
    if 'case_deadlines' not in tables:
        op.create_table(
            'case_deadlines',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('statute_rule_id', sa.Integer(), sa.ForeignKey('statutory_deadline_rules.id'), nullable=True),
            sa.Column('title', sa.String(), nullable=False),
            sa.Column('due_date', sa.DateTime(timezone=True), nullable=False, index=True),
            sa.Column('status', sa.String(), server_default='pending', nullable=False, index=True),
            sa.Column('satisfied_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('satisfied_by', sa.String(), nullable=True),
            sa.Column('extended_until', sa.DateTime(timezone=True), nullable=True),
            sa.Column('extension_reason', sa.Text(), nullable=True),
            sa.Column('last_alert_days', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )

    # 7. user_case_states table
    if 'user_case_states' not in tables:
        op.create_table(
            'user_case_states',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('last_handover_viewed_at', sa.DateTime(timezone=True), nullable=True)
        )

    # 8. handover_summaries table
    if 'handover_summaries' not in tables:
        op.create_table(
            'handover_summaries',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
            sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
            sa.Column('headline', sa.String(), nullable=False),
            sa.Column('structured_content', sa.Text(), nullable=False),
            sa.Column('rendered_text', sa.Text(), nullable=False),
            sa.Column('generated_by', sa.String(), server_default='System', nullable=False),
            sa.Column('generation_type', sa.String(), server_default='manual', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True)
        )

    # 9. email_logs table
    if 'email_logs' not in tables:
        op.create_table(
            'email_logs',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('recipient_email', sa.String(), nullable=False),
            sa.Column('alert_id', sa.Integer(), sa.ForeignKey('alerts.id', ondelete='SET NULL'), nullable=True),
            sa.Column('subject', sa.String(), nullable=False),
            sa.Column('status', sa.String(), server_default='pending', nullable=False, index=True),
            sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    for tbl in [
        'email_logs',
        'handover_summaries',
        'user_case_states',
        'case_deadlines',
        'statutory_deadline_rules',
        'notification_preferences',
        'alert_rule_configs',
        'alerts'
    ]:
        if tbl in tables:
            op.drop_table(tbl)

    if 'cases' in tables:
        case_cols = [c['name'] for c in inspector.get_columns('cases')]
        with op.batch_alter_table('cases') as batch_op:
            for col in [
                'statutory_time_limit_days',
                'offence_section',
                'remand_date',
                'arrest_date',
                'incident_date',
                'fir_date',
                'fir_number'
            ]:
                if col in case_cols:
                    batch_op.drop_column(col)

