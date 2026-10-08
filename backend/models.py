# backend/models.py
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

class EvidenceStatus(str, enum.Enum):
    UPLOADED = "Uploaded"
    QUEUED = "Queued"
    PROCESSING = "Processing"
    ANALYZED = "Analyzed"
    FAILED = "Failed"

class AssessmentClassification(str, enum.Enum):
    STRONG_SUPPORT = "strong_support"
    MODERATE_SUPPORT = "moderate_support"
    WEAK_SUPPORT = "weak_support"
    NEUTRAL = "neutral"
    WEAK_CONTRADICTION = "weak_contradiction"
    MODERATE_CONTRADICTION = "moderate_contradiction"
    STRONG_CONTRADICTION = "strong_contradiction"

class Case(Base):
    __tablename__ = "cases"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="Active")
    created_by = Column(String, default="current_user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    file_name = Column(String, nullable=False)
    file_type = Column(String)
    file_size = Column(Integer)
    storage_path = Column(String)
    uploaded_by = Column(String, default="current_user")
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    processing_status = Column(Enum(EvidenceStatus), default=EvidenceStatus.UPLOADED)
    extracted_text = Column(Text, nullable=True)
    source = Column(String, nullable=True)
    # Reliability & Forensics Integrity Attributes
    evidence_type = Column(String, default="document")  # DNA, fingerprint, CCTV, CDR, document, witness, confession
    file_hash = Column(String, nullable=True)  # SHA-256 integrity hash
    hash_verified = Column(Boolean, default=False)
    chain_of_custody_complete = Column(Boolean, default=False)
    sec_65b_certificate_present = Column(Boolean, default=False)  # Sec 65B Indian Evidence Act for electronic records
    source_independent = Column(Boolean, default=True)
    quality_rating = Column(Float, default=3.0)  # 1.0 to 5.0 scale
    # Phase 3 Feature 2: Custody & Soft-delete
    collected_by = Column(String, nullable=True)
    collection_date = Column(DateTime(timezone=True), nullable=True)
    custody_notes = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(String, nullable=True)

class Entity(Base):
    __tablename__ = "entities"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    evidence_id = Column(Integer, ForeignKey("evidence.id"))
    type = Column(String)
    name = Column(String, nullable=False)
    confidence = Column(Float, default=0.0)
    # Phase 3 Feature 3: Source-span citation
    source_quote = Column(Text, nullable=True)
    source_char_start = Column(Integer, nullable=True)
    source_char_end = Column(Integer, nullable=True)
    source_page_number = Column(Integer, nullable=True)

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    evidence_id = Column(Integer, ForeignKey("evidence.id"))
    timestamp = Column(DateTime(timezone=True), nullable=True)
    title = Column(String)
    description = Column(Text)
    location = Column(String, nullable=True)
    confidence = Column(Float, default=0.0)
    # Phase 3 Feature 3: Source-span citation
    source_quote = Column(Text, nullable=True)
    source_char_start = Column(Integer, nullable=True)
    source_char_end = Column(Integer, nullable=True)
    source_page_number = Column(Integer, nullable=True)


# ============================================================
# HYPOTHESIS & EVIDENCE ASSESSMENT MODELS
# ============================================================

class Hypothesis(Base):
    __tablename__ = "hypotheses"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="Active")  # Active, Proven, Discarded
    support_score = Column(Float, default=0.0)  # Normalized relative likelihood percentage (sums to 100.0)
    disconfirmation_penalty = Column(Float, default=0.0)  # ACH disconfirmation penalty
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    assessments = relationship("EvidenceAssessment", back_populates="hypothesis", cascade="all, delete-orphan")
    case = relationship("Case", backref="hypotheses")

class EvidenceAssessment(Base):
    __tablename__ = "evidence_assessments"
    id = Column(Integer, primary_key=True, index=True)
    hypothesis_id = Column(Integer, ForeignKey("hypotheses.id"), nullable=False)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False)
    classification = Column(String, nullable=False)  # strong_support, neutral, strong_contradiction, etc.
    original_classification = Column(String, nullable=True)  # AI's original classification before analyst override
    analyst_override = Column(Boolean, default=False)  # True if overridden by human investigator
    analyst_notes = Column(Text, nullable=True)  # Investigator's justification for override
    reason = Column(Text)
    llm_confidence = Column(Float, default=0.0)
    reliability = Column(Float, default=1.0)
    quoted_source_line = Column(Text, nullable=True)  # Exact quote from exhibit supporting classification
    computed_reliability = Column(Float, default=1.0)  # Final resolved reliability with modifiers
    computed_diagnosticity = Column(Float, default=1.0)  # Diagnosticity factor based on hypothesis variance
    final_contribution = Column(Float, default=0.0)  # Net signed contribution to hypothesis score

    # Relationships
    hypothesis = relationship("Hypothesis", back_populates="assessments")
    evidence = relationship("Evidence", backref="assessments")

# ============================================================
# RELIABILITY CONFIG & SCORING RUN MODELS
# ============================================================

class ReliabilityConfig(Base):
    __tablename__ = "reliability_configs"
    id = Column(Integer, primary_key=True, index=True)
    evidence_type = Column(String, unique=True, nullable=False, index=True)  # DNA, fingerprint, CCTV, CDR, document, witness, confession
    base_reliability = Column(Float, nullable=False, default=0.70)
    rationale = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ScoringRun(Base):
    __tablename__ = "scoring_runs"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    run_at = Column(DateTime(timezone=True), server_default=func.now())
    triggered_by = Column(String, default="analyst")  # analyst, override, automated, sensitivity
    settings_snapshot = Column(Text, nullable=True)  # JSON string of modifiers and configuration used
    results_snapshot = Column(Text, nullable=True)  # JSON string of scores, rankings, robustness ranges

    case = relationship("Case", backref="scoring_runs")


# ============================================================
# CONTRADICTION & INVESTIGATION TASK MODELS
# ============================================================

class Contradiction(Base):
    __tablename__ = "contradictions"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    statement_a = Column(Text, nullable=False)
    source_a_id = Column(String, nullable=True)
    statement_b = Column(Text, nullable=False)
    source_b_id = Column(String, nullable=True)
    conflict_type = Column(String, nullable=False)  # e.g., "Alibi Discrepancy", "Forensic Discrepancy", "Timeline Conflict", "Log Inconsistency"
    confidence = Column(Float, default=90.0)
    status = Column(String, default="Detected")  # Detected, Under Review, Resolved, Dismissed
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    case = relationship("Case", backref="contradictions")


class InvestigationTask(Base):
    __tablename__ = "investigation_tasks"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    task = Column(String, nullable=False)
    reason = Column(Text, nullable=True)
    related_hypothesis_id = Column(String, nullable=True)
    related_contradiction_id = Column(String, nullable=True)
    related_evidence_id = Column(String, nullable=True)
    priority = Column(String, default="High")  # High, Medium, Low
    status = Column(String, default="Pending")  # Pending, In Progress, Completed
    assigned_to = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    case = relationship("Case", backref="investigation_tasks")

class Relationship(Base):
    __tablename__ = "relationships"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    source_entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    target_entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    relation_type = Column(String, nullable=False)  # e.g. "called", "met", "visited", "drove", "accomplice_of", "threatened"
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=True)
    confidence = Column(Float, default=0.90)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    case = relationship("Case", backref="relationships")
    source_entity = relationship("Entity", foreign_keys=[source_entity_id], backref="outgoing_relationships")
    target_entity = relationship("Entity", foreign_keys=[target_entity_id], backref="incoming_relationships")
    evidence = relationship("Evidence", backref="relationships")


# ==============================================================================
# PHASE 3: AUTHENTICATION & CASE ISOLATION MEMBERSHIPS
# ==============================================================================

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="analyst")  # admin, lead_investigator, analyst, reviewer
    badge_number = Column(String, nullable=True)
    department = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CaseMember(Base):
    __tablename__ = "case_members"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    case_role = Column(String, nullable=True)  # lead_investigator, analyst, reviewer
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    added_by = Column(String, nullable=True)

    case = relationship("Case", backref="case_members")
    user = relationship("User", backref="case_assignments")


# ==============================================================================
# PHASE 3 FEATURE 2: CHAIN OF CUSTODY & MERKLE AUDIT LEDGER
# ==============================================================================

class CustodyLog(Base):
    __tablename__ = "custody_logs"
    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    action = Column(String, nullable=False)  # SEIZURE, INTAKE, ANALYSIS, ACCESS, TRANSFER, SEC_65B_VERIFY, INTEGRITY_VERIFY, SOFT_DELETE
    actor_name = Column(String, nullable=False)
    actor_role = Column(String, nullable=True)
    source_agency = Column(String, nullable=True)
    location = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    file_hash_snapshot = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    evidence = relationship("Evidence", backref="custody_entries")
    case = relationship("Case", backref="custody_entries")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_name = Column(String, nullable=False, default="System")
    user_role = Column(String, nullable=True)
    action_type = Column(String, nullable=False)  # LOGIN, EVIDENCE_UPLOAD, CLASSIFICATION_OVERRIDE, SCORING_RECALCULATE, INTEGRITY_VERIFY, EVIDENCE_SOFT_DELETE, CASE_CREATE, etc.
    target_type = Column(String, nullable=False)  # case, exhibit, hypothesis, user, system
    target_id = Column(String, nullable=True)
    description = Column(Text, nullable=False)
    before_value = Column(Text, nullable=True)
    after_value = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Cryptographic Merkle-chain hashes
    previous_hash = Column(String, nullable=False)
    current_hash = Column(String, nullable=False)

    case = relationship("Case", backref="audit_entries")
    user = relationship("User", backref="audit_entries")


# ==============================================================================
# PHASE 3 FEATURE 3: SOURCE-SPAN CITATIONS & NUMBERED EXHIBIT CHUNKS
# ==============================================================================

class ExhibitChunk(Base):
    __tablename__ = "exhibit_chunks"
    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)  # 0, 1, 2, ...
    text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)  # Page # for PDFs / multi-page docs
    char_start = Column(Integer, nullable=False)  # Starting character offset in full text
    char_end = Column(Integer, nullable=False)    # Ending character offset
    start_time_sec = Column(Float, nullable=True) # Timestamp for audio/video transcripts
    end_time_sec = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    evidence = relationship("Evidence", backref="chunks")
    case = relationship("Case", backref="exhibit_chunks")


class SourceCitation(Base):
    __tablename__ = "citations"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False)
    chunk_id = Column(Integer, ForeignKey("exhibit_chunks.id"), nullable=True)
    
    fact_type = Column(String, nullable=False)  # "entity", "event", "claim", "assessment"
    fact_id = Column(Integer, nullable=True)     # ID of the referenced Entity, Event, or Assessment
    
    quote = Column(Text, nullable=False)         # Exact quoted text span
    page_number = Column(Integer, nullable=True)
    char_start = Column(Integer, nullable=True)  # Absolute character offset in exhibit text
    char_end = Column(Integer, nullable=True)
    timestamp_sec = Column(Float, nullable=True)
    
    verified_match = Column(Boolean, default=True)      # True if quote actually exists in source bytes
    match_confidence = Column(Float, default=1.0)       # 1.0 = exact substring, 0.8+ = fuzzy match
    verification_method = Column(String, default="exact_substring") # exact_substring, fuzzy_token, unverified
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    evidence = relationship("Evidence", backref="citations")
    chunk = relationship("ExhibitChunk", backref="citations")
    case = relationship("Case", backref="citations")