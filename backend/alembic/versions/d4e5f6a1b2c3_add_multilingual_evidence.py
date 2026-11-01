"""add_multilingual_evidence

Revision ID: d4e5f6a1b2c3
Revises: c3d4e5f6a1b2
Create Date: 2026-10-29 20:56:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a1b2c3'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create language_settings table
    if 'language_settings' not in tables:
        op.create_table(
            'language_settings',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('language', sa.String(length=20), nullable=False, index=True),
            sa.Column('script', sa.String(length=30), nullable=False),
            sa.Column('content_type', sa.String(length=30), nullable=False),
            sa.Column('reading_method', sa.String(length=64), nullable=False),
            sa.Column('fallback_method', sa.String(length=64), nullable=True),
            sa.Column('stt_model_hint', sa.String(length=64), nullable=True),
            sa.Column('preprocessing_steps', sa.Text(), server_default='[]', nullable=False),
            sa.Column('confidence_threshold', sa.Float(), server_default='0.75', nullable=False),
            sa.Column('translate_by_default', sa.Boolean(), server_default='1', nullable=False),
            sa.Column('default_target_language', sa.String(length=20), server_default='en', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )

    # 2. Create exhibit_text_versions table
    if 'exhibit_text_versions' not in tables:
        op.create_table(
            'exhibit_text_versions',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('evidence_id', sa.Integer(), sa.ForeignKey('evidence.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('version_number', sa.Integer(), nullable=False, index=True),
            sa.Column('raw_text', sa.Text(), nullable=False),
            sa.Column('normalized_text', sa.Text(), nullable=False),
            sa.Column('reading_method', sa.String(length=64), nullable=False),
            sa.Column('overall_confidence', sa.Float(), server_default='1.0', nullable=False),
            sa.Column('status', sa.String(length=32), server_default='machine_read', nullable=False),
            sa.Column('is_current', sa.Boolean(), server_default='0', nullable=False, index=True),
            sa.Column('created_by', sa.String(length=128), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('edit_reason', sa.Text(), nullable=True),
            sa.Column('diff_summary', sa.Text(), nullable=True),
            sa.Column('requires_second_signoff', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('second_signoff_by', sa.String(length=128), nullable=True),
            sa.Column('second_signoff_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('is_reverted', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('reverted_from_version', sa.Integer(), nullable=True)
        )

    # 3. Create exhibit_segments table
    if 'exhibit_segments' not in tables:
        op.create_table(
            'exhibit_segments',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('evidence_id', sa.Integer(), sa.ForeignKey('evidence.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('version_id', sa.Integer(), sa.ForeignKey('exhibit_text_versions.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('case_id', sa.Integer(), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('segment_index', sa.Integer(), nullable=False),
            sa.Column('page_number', sa.Integer(), nullable=True),
            sa.Column('bbox_json', sa.Text(), nullable=True),
            sa.Column('start_time_sec', sa.Float(), nullable=True),
            sa.Column('end_time_sec', sa.Float(), nullable=True),
            sa.Column('speaker_label', sa.String(length=64), nullable=True),
            sa.Column('raw_text', sa.Text(), nullable=False),
            sa.Column('normalized_text', sa.Text(), nullable=False),
            sa.Column('confidence', sa.Float(), server_default='1.0', nullable=False),
            sa.Column('is_low_confidence', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('status', sa.String(length=32), server_default='machine_read', nullable=False),
            sa.Column('reading_method', sa.String(length=64), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )

    # 4. Create exhibit_translations table
    if 'exhibit_translations' not in tables:
        op.create_table(
            'exhibit_translations',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('evidence_id', sa.Integer(), sa.ForeignKey('evidence.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('version_id', sa.Integer(), sa.ForeignKey('exhibit_text_versions.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('source_language', sa.String(length=20), nullable=False),
            sa.Column('target_language', sa.String(length=20), server_default='en', nullable=False),
            sa.Column('author_type', sa.String(length=32), server_default='machine', nullable=False),
            sa.Column('author_name', sa.String(length=128), nullable=False),
            sa.Column('model_used', sa.String(length=64), nullable=True),
            sa.Column('review_status', sa.String(length=32), server_default='unreviewed', nullable=False),
            sa.Column('reviewed_by', sa.String(length=128), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('full_translated_text', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )

    # 5. Create translation_segments table
    if 'translation_segments' not in tables:
        op.create_table(
            'translation_segments',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('translation_id', sa.Integer(), sa.ForeignKey('exhibit_translations.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('source_segment_id', sa.Integer(), sa.ForeignKey('exhibit_segments.id', ondelete='CASCADE'), nullable=True, index=True),
            sa.Column('source_text_snippet', sa.Text(), nullable=False),
            sa.Column('translated_text', sa.Text(), nullable=False),
            sa.Column('alignment_confidence', sa.Float(), server_default='1.0', nullable=False),
            sa.Column('proper_names_json', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )

    # 6. Add columns to evidence table if not present
    evidence_cols = [c['name'] for c in inspector.get_columns('evidence')]
    with op.batch_alter_table('evidence') as batch_op:
        if 'primary_language' not in evidence_cols:
            batch_op.add_column(sa.Column('primary_language', sa.String(length=20), server_default='en', nullable=False))
        if 'is_mixed' not in evidence_cols:
            batch_op.add_column(sa.Column('is_mixed', sa.Boolean(), server_default='0', nullable=False))
        if 'script' not in evidence_cols:
            batch_op.add_column(sa.Column('script', sa.String(length=30), server_default='latin', nullable=False))
        if 'content_type' not in evidence_cols:
            batch_op.add_column(sa.Column('content_type', sa.String(length=30), server_default='printed', nullable=False))
        if 'language_source' not in evidence_cols:
            batch_op.add_column(sa.Column('language_source', sa.String(length=30), server_default='auto_detected', nullable=False))
        if 'text_quality_status' not in evidence_cols:
            batch_op.add_column(sa.Column('text_quality_status', sa.String(length=30), server_default='unreviewed', nullable=False))
        if 'is_poor_audio' not in evidence_cols:
            batch_op.add_column(sa.Column('is_poor_audio', sa.Boolean(), server_default='0', nullable=False))
        if 'current_version_id' not in evidence_cols:
            batch_op.add_column(sa.Column('current_version_id', sa.Integer(), nullable=True))
        if 'ocr_reading_method' not in evidence_cols:
            batch_op.add_column(sa.Column('ocr_reading_method', sa.String(length=50), nullable=True))
        if 'ocr_confidence' not in evidence_cols:
            batch_op.add_column(sa.Column('ocr_confidence', sa.Float(), server_default='1.0', nullable=True))

    # 7. Add stale columns to entities table
    entities_cols = [c['name'] for c in inspector.get_columns('entities')]
    with op.batch_alter_table('entities') as batch_op:
        if 'is_stale' not in entities_cols:
            batch_op.add_column(sa.Column('is_stale', sa.Boolean(), server_default='0', nullable=False))
        if 'stale_reason' not in entities_cols:
            batch_op.add_column(sa.Column('stale_reason', sa.String(), nullable=True))
        if 'source_version_id' not in entities_cols:
            batch_op.add_column(sa.Column('source_version_id', sa.Integer(), nullable=True))

    # 8. Add stale columns to events table
    events_cols = [c['name'] for c in inspector.get_columns('events')]
    with op.batch_alter_table('events') as batch_op:
        if 'is_stale' not in events_cols:
            batch_op.add_column(sa.Column('is_stale', sa.Boolean(), server_default='0', nullable=False))
        if 'stale_reason' not in events_cols:
            batch_op.add_column(sa.Column('stale_reason', sa.String(), nullable=True))
        if 'source_version_id' not in events_cols:
            batch_op.add_column(sa.Column('source_version_id', sa.Integer(), nullable=True))

    # 9. Add columns to citations table
    citations_cols = [c['name'] for c in inspector.get_columns('citations')]
    with op.batch_alter_table('citations') as batch_op:
        if 'version_id' not in citations_cols:
            batch_op.add_column(sa.Column('version_id', sa.Integer(), nullable=True))
        if 'segment_id' not in citations_cols:
            batch_op.add_column(sa.Column('segment_id', sa.Integer(), nullable=True))
        if 'is_stale' not in citations_cols:
            batch_op.add_column(sa.Column('is_stale', sa.Boolean(), server_default='0', nullable=False))
        if 'translated_quote' not in citations_cols:
            batch_op.add_column(sa.Column('translated_quote', sa.Text(), nullable=True))
        if 'translation_label' not in citations_cols:
            batch_op.add_column(sa.Column('translation_label', sa.String(length=128), nullable=True))

    # 10. Ensure reliability_configs has version column
    rel_cols = [c['name'] for c in inspector.get_columns('reliability_configs')]
    if 'version' not in rel_cols:
        with op.batch_alter_table('reliability_configs') as batch_op:
            batch_op.add_column(sa.Column('version', sa.Integer(), server_default='1', nullable=False))


def downgrade() -> None:
    pass

