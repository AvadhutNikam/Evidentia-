# backend/models.py
from sqlalchemy import Column, Date, Integer, String, DateTime, Float, Text, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship, backref
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
    # Statutory Deadlines & Particulars
    version = Column(Integer, default=1, nullable=False)
    is_demo = Column(Boolean, default=False)
    fir_number = Column(String, nullable=True)
    fir_date = Column(DateTime(timezone=True), nullable=True)
    incident_date = Column(DateTime(timezone=True), nullable=True)
    arrest_date = Column(DateTime(timezone=True), nullable=True)
    remand_date = Column(DateTime(timezone=True), nullable=True)
    offence_section = Column(String, nullable=True)
    statutory_time_limit_days = Column(Integer, default=90, nullable=True)
    # Air-gap & Retention
    is_sensitive_airgapped = Column(Boolean, default=False)
    ai_provider_override = Column(String, nullable=True)
    local_ai_endpoint = Column(String, nullable=True)
    local_ai_model = Column(String, nullable=True)
    retention_period_years = Column(Integer, default=10)
    retention_expiry_date = Column(DateTime(timezone=True), nullable=True)
    is_legal_hold = Column(Boolean, default=False)
    legal_hold_reason = Column(String, nullable=True)
    legal_hold_placed_by = Column(String, nullable=True)
    legal_hold_placed_at = Column(DateTime(timezone=True), nullable=True)
    # Police Docket Particulars
    crime_number = Column(String, nullable=True)
    police_station = Column(String, nullable=True)
    district = Column(String, nullable=True)
    state = Column(String, default="Maharashtra", nullable=True)
    investigating_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    investigating_officer_name = Column(String, nullable=True)
    supervising_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    supervising_officer_name = Column(String, nullable=True)
    court_name = Column(String, nullable=True)
    next_hearing_date = Column(DateTime(timezone=True), nullable=True)
    next_hearing_purpose = Column(String, nullable=True)
    bail_status = Column(String, default="None", nullable=True)
    custody_status = Column(String, default="Under Investigation", nullable=True)
    case_stage = Column(String, default="under_investigation", nullable=True)

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
    dependency_group = Column(String, nullable=True)
    extraction_mode = Column(String, default="live")
    is_demo_fixture = Column(Boolean, default=False)
    version = Column(Integer, default=1, nullable=False)
    primary_language = Column(String(20), default="en", nullable=False)
    is_mixed = Column(Boolean, default=False, nullable=False)
    script = Column(String(30), default="latin", nullable=False)
    content_type = Column(String(30), default="printed", nullable=False)
    language_source = Column(String(30), default="auto_detected", nullable=False)
    text_quality_status = Column(String(30), default="unreviewed", nullable=False)
    is_poor_audio = Column(Boolean, default=False, nullable=False)
    current_version_id = Column(Integer, nullable=True)
    ocr_reading_method = Column(String(50), nullable=True)
    ocr_confidence = Column(Float, default=1.0, nullable=True)
    is_field_captured = Column(Boolean, default=False, nullable=False)
    capture_source = Column(String(50), default="web_upload", nullable=False)
    field_latitude = Column(Float, nullable=True)
    field_longitude = Column(Float, nullable=True)
    field_accuracy_meters = Column(Float, nullable=True)
    field_captured_at = Column(DateTime(timezone=True), nullable=True)
    field_device_info = Column(String(255), nullable=True)
    field_location_name = Column(String(255), nullable=True)
    field_tamper_seal_number = Column(String(100), nullable=True)
    field_officer_confirmed = Column(Boolean, default=False, nullable=False)
    field_officer_declaration = Column(Text, nullable=True)
    client_computed_hash = Column(String(64), nullable=True)
    hash_match_verified = Column(Boolean, default=False, nullable=False)
    connector_id = Column(Integer, nullable=True)
    connector_type = Column(String(50), nullable=True)
    connector_source_system = Column(String(255), nullable=True)
    connector_receipt_time = Column(DateTime(timezone=True), nullable=True)
    document_type = Column(String(50), nullable=True)
    type_details = Column(Text, nullable=True)
    evidence_kind = Column(String(20), default="digital", nullable=False)

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
    is_stale = Column(Boolean, default=False, nullable=False)
    stale_reason = Column(String, nullable=True)
    source_version_id = Column(Integer, nullable=True)

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
    is_stale = Column(Boolean, default=False, server_default="0", nullable=False)
    stale_reason = Column(String, nullable=True)
    source_version_id = Column(Integer, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    event_type = Column(String(64), nullable=True)
    time_uncertainty_minutes = Column(Integer, default=0, nullable=True)


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
    version = Column(Integer, default=1, nullable=False)
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
    category = Column(String, default="investigation")
    impact_score = Column(Float, nullable=True)
    suggested_by_ai = Column(Boolean, default=False)
    dismissed = Column(Boolean, default=False)
    version = Column(Integer, default=1, nullable=False)

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
    # Extended Custody Ledger attributes for physical and digital forensics
    from_person_id = Column(Integer, nullable=True)
    from_person_name = Column(String(255), nullable=True)
    from_location = Column(String(255), nullable=True)
    to_person_id = Column(Integer, nullable=True)
    to_person_name = Column(String(255), nullable=True)
    to_location = Column(String(255), nullable=True)
    purpose = Column(String(255), nullable=True)
    condition_at_handover = Column(String(255), nullable=True)
    seal_status_check = Column(String(50), nullable=True)  # intact, damaged, broken_authorized, broken_unauthorized, resealed
    expected_return_date = Column(DateTime(timezone=True), nullable=True)
    authority_order_ref = Column(String(255), nullable=True)
    acknowledgement_type = Column(String(50), nullable=True)  # digital_pin, signature_canvas, biometric, written_memo
    acknowledgement_data = Column(Text, nullable=True)
    attached_photos = Column(Text, nullable=True)  # JSON array of photo URLs/hashes
    previous_log_hash = Column(String(64), nullable=True)  # SHA-256 of preceding custody log entry
    current_log_hash = Column(String(64), nullable=True)  # SHA-256 hash of this entry

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

class PoliceStationLookup(Base):
    """
    Maintainable lookup directory for Police Stations, Jurisdictions & Districts.
    Enables quick selection instead of manual text entry.
    """
    __tablename__ = "police_station_lookups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, unique=True, index=True)
    station_code = Column(String(50), nullable=True, index=True)
    district = Column(String(100), nullable=False, index=True)
    state = Column(String(100), default="Maharashtra", nullable=False)
    contact_number = Column(String(50), nullable=True)
    sp_office = Column(String(150), nullable=True)


class CasePerson(Base):
    """
    Master Police People Register.
    Captures Complainant, Victim, Accused, Eyewitness, Panch Witness, Informant, Expert.
    Field-level encrypted contact & address for witness protection & PII safeguards.
    """
    __tablename__ = "case_persons"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False, index=True)
    aliases = Column(String(200), nullable=True)
    role = Column(String(50), nullable=False, index=True)  # complainant, victim, accused, witness, expert, informant, panch_witness, other
    father_or_spouse_name = Column(String(150), nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)
    contact_info = Column(Text, nullable=True)  # AES-GCM encrypted
    address = Column(Text, nullable=True)       # AES-GCM encrypted
    is_important = Column(Boolean, default=False, nullable=False)
    linked_entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    case = relationship("Case", backref="case_persons")
    linked_entity = relationship("Entity", foreign_keys=[linked_entity_id])


class AccusedStatusHistory(Base):
    """
    Accused Custody & Bail Status Chronology.
    Maintains per-accused statutory countdowns (arrest date, remand expiry, default bail 60/90 days).
    """
    __tablename__ = "accused_status_history"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    person_id = Column(Integer, ForeignKey("case_persons.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)  # not_identified, absconding, arrested, police_custody, judicial_custody, bailed, anticipatory_bail, chargesheeted
    status_date = Column(DateTime(timezone=True), nullable=False)
    order_reference = Column(String(150), nullable=True)  # e.g., "CJM Remand Order No. 492/2009"
    custody_days_served = Column(Integer, default=0, nullable=False)
    remand_expiry_date = Column(DateTime(timezone=True), nullable=True)
    statutory_filing_deadline = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    person = relationship("CasePerson", backref="status_history")
    case = relationship("Case")


class PersonStatement(Base):
    """
    Formal Witness, Accused & Victim Statements.
    Covers Sec 180 BNSS / 161 CrPC (Police) & Sec 183 BNSS / 164 CrPC (Magistrate).
    Supports Statement Improvement & Contradiction detection across multiple dates.
    """
    __tablename__ = "person_statements"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    person_id = Column(Integer, ForeignKey("case_persons.id", ondelete="CASCADE"), nullable=False, index=True)
    statement_type = Column(String(50), nullable=False, index=True)  # section_180_bnss_police, section_183_bnss_magistrate, dying_declaration, confession, other
    status = Column(String(50), default="recorded", nullable=False)  # not_contacted, summoned, examined, recorded, refused
    statement_date = Column(DateTime(timezone=True), nullable=False, index=True)
    statement_time = Column(String(20), nullable=True)
    place = Column(String(200), nullable=True)
    recorded_by = Column(String(120), nullable=True)
    language = Column(String(50), default="Marathi", nullable=True)
    read_over_and_signed = Column(Boolean, default=True, nullable=False)
    magistrate_name = Column(String(120), nullable=True)  # Recorded for Section 183 / 164 statements
    linked_evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=True)
    linked_interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=True)
    statement_text = Column(Text, nullable=True)
    key_claims = Column(Text, nullable=True)  # JSON list of extracted claims
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    person = relationship("CasePerson", backref="statements")
    case = relationship("Case")
    linked_evidence = relationship("Evidence", foreign_keys=[linked_evidence_id])


class DocumentTypeDefinition(Base):
    """
    Police Document Type Definitions Registry.
    Defines required fields, legal provisions, and gap rules for standard police memos:
    FIR, Spot Panchnama, Seizure Memo, Arrest Memo, MLC, Post-Mortem, Inquest, FSL Requisition/Report, Sec 65B.
    """
    __tablename__ = "document_type_definitions"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    label = Column(String(120), nullable=False)
    legal_provision = Column(String(120), nullable=False)
    category = Column(String(50), nullable=False)  # investigation, panchnama, custody, medico_legal, technical
    required_fields_json = Column(Text, nullable=False)  # JSON schema of required/conditional fields
    standard_guidance = Column(Text, nullable=True)


class CaseDiaryEntry(Base):
    """
    Daily Case Investigation Diary under Section 192 BNSS / Section 172 CrPC.
    Auto-drafted from daily audit trail, witness examinations & seizure logs.
    Locked upon digital signature; subsequent revisions create chained addendums.
    """
    __tablename__ = "case_diary_entries"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    entry_date = Column(Date, nullable=False, index=True)
    serial_number = Column(Integer, default=1, nullable=False)
    time_from = Column(String(10), nullable=True)
    time_to = Column(String(10), nullable=True)
    place = Column(String(200), nullable=True)
    officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    officer_name = Column(String(120), nullable=False)
    activities = Column(Text, nullable=False)
    persons_examined_json = Column(Text, nullable=True)  # JSON list of examined person IDs & names
    places_visited_json = Column(Text, nullable=True)    # JSON list of scene/location names
    items_seized_json = Column(Text, nullable=True)      # JSON list of seized property IDs & descriptions
    instructions_given = Column(Text, nullable=True)
    next_steps = Column(Text, nullable=True)
    status = Column(String(20), default="draft", nullable=False)  # draft, signed, locked
    signature_timestamp = Column(DateTime(timezone=True), nullable=True)
    signature_hash = Column(String(64), nullable=True)
    supervisor_notes = Column(Text, nullable=True)
    parent_entry_id = Column(Integer, ForeignKey("case_diary_entries.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    case = relationship("Case", backref="diary_entries")
    officer = relationship("User", foreign_keys=[officer_id])


class CaseSection(Base):
    """
    Penal Offence Sections Register (BNS & IPC).
    Maintains history of sections added, altered, or dropped with reasons, deciding officer, and supervisor approval.
    Directly triggers statutory 60/90 days time limit recalculation based on punishment tiers.
    """
    __tablename__ = "case_sections"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    act = Column(String(50), default="BNS", nullable=False)  # BNS, IPC, Special Law, POCSO, NDPS, Arms Act
    section_code = Column(String(50), nullable=False, index=True)  # e.g., "103(1)", "302"
    description = Column(String(255), nullable=False)
    punishment_tier = Column(String(50), default="life_or_death_over_10_years", nullable=False)  # life_or_death_over_10_years (90 days) | under_10_years (60 days)
    status = Column(String(30), default="initial", nullable=False)  # initial, proposed_add, added, proposed_drop, dropped
    reason = Column(Text, nullable=True)
    deciding_officer = Column(String(120), nullable=True)
    effective_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    supervisor_approval = Column(Boolean, default=True, nullable=False)
    supervisor_notes = Column(Text, nullable=True)
    court_informed_date = Column(DateTime(timezone=True), nullable=True)
    court_intimation_memo = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("Case", backref="sections")


class SectionElement(Base):
    """
    Element-by-Element Statutory Proof Matrix.
    Deconstructs legal offences into constituent legal ingredients (e.g. Mens Rea, Actus Reus, Death, Grave Provocation)
    and maps them to supporting exhibits.
    """
    __tablename__ = "section_elements"
    id = Column(Integer, primary_key=True, index=True)
    case_section_id = Column(Integer, ForeignKey("case_sections.id", ondelete="CASCADE"), nullable=False, index=True)
    element_text = Column(String(255), nullable=False)
    supporting_evidence_ids = Column(Text, nullable=True)  # JSON list of evidence IDs
    status = Column(String(30), default="missing", nullable=False)  # supported, partial, missing
    notes = Column(Text, nullable=True)

    section = relationship("CaseSection", backref="elements")

# ==============================================================================
# ALIBI VERIFICATION WORKFLOW MODELS (CHANGE: ALIBI LIFECYCLE)
# ==============================================================================

class AlibiClaim(Base):
    """
    Formal defense alibi claim by a suspect.
    Maintains claim lifecycle, versioning, source statement citation,
    and final investigator verdict.
    """
    __tablename__ = "alibi_claims"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    person_id = Column(Integer, ForeignKey("case_persons.id", ondelete="SET NULL"), nullable=True, index=True)
    suspect_name = Column(String(150), nullable=False, index=True)
    hypothesis_id = Column(Integer, ForeignKey("hypotheses.id", ondelete="SET NULL"), nullable=True, index=True)
    claim_text = Column(Text, nullable=False)
    source_statement_id = Column(Integer, ForeignKey("interview_statements.id", ondelete="SET NULL"), nullable=True)
    source_citation = Column(String(255), nullable=True)
    version = Column(Integer, default=1, nullable=False)
    raised_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="open", nullable=False, index=True)  # open, being_verified, verified, partly_verified, contradicted, inconclusive, withdrawn
    final_verdict = Column(String(50), nullable=True)  # verified, partly_verified, contradicted, inconclusive, pending
    verdict_reason = Column(Text, nullable=True)
    verdict_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verdict_by_name = Column(String(150), nullable=True)
    verdict_at = Column(DateTime(timezone=True), nullable=True)
    is_current = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    case = relationship("Case", backref="alibi_claims")
    person = relationship("CasePerson", foreign_keys=[person_id])
    hypothesis = relationship("Hypothesis", foreign_keys=[hypothesis_id])
    source_statement = relationship("InterviewStatement", foreign_keys=[source_statement_id])
    segments = relationship("AlibiSegment", back_populates="claim", cascade="all, delete-orphan", order_by="AlibiSegment.segment_order")
    checks = relationship("AlibiCheck", back_populates="claim", cascade="all, delete-orphan")
    comparisons = relationship("StatementComparison", back_populates="claim", cascade="all, delete-orphan", order_by="StatementComparison.line_number")


class AlibiSegment(Base):
    """
    A single discrete time-and-place interval of an alibi.
    Tracks start, end, location, radius, activity, travel mode, and vouching persons.
    """
    __tablename__ = "alibi_segments"
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("alibi_claims.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_order = Column(Integer, default=1, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    time_uncertainty_mins = Column(Integer, default=15, nullable=False)
    claimed_place_name = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    radius_meters = Column(Float, default=500.0, nullable=False)
    activity = Column(String(255), nullable=True)
    travel_mode = Column(String(50), default="none", nullable=False)  # none, foot, bus, car_two_wheeler, train, flight
    vouching_persons = Column(Text, nullable=True)  # JSON list of {name, relation, contact, statement_id}
    status = Column(String(50), default="unverified", nullable=False)  # unverified, confirmed, contradicted, inconclusive
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    claim = relationship("AlibiClaim", back_populates="segments")
    checks = relationship("AlibiCheck", back_populates="segment", cascade="all, delete-orphan")


class AlibiCheck(Base):
    """
    Verification action item for an alibi segment or claim.
    Links to an InvestigationTask, tracks source type (CDR, CCTV, Witness, UPI, Toll),
    due dates, clock offsets, and supporting exhibits.
    """
    __tablename__ = "alibi_checks"
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("alibi_claims.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_id = Column(Integer, ForeignKey("alibi_segments.id", ondelete="CASCADE"), nullable=True, index=True)
    source_type = Column(String(50), nullable=False, index=True)  # cdr_tower, cctv, witness, banking_upi, atm, toll_fastag, hotel_attendance, photo_metadata, other
    requirement_details = Column(Text, nullable=False)
    legal_process_required = Column(Boolean, default=False, nullable=False)
    investigation_task_id = Column(Integer, ForeignKey("investigation_tasks.id", ondelete="SET NULL"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner_name = Column(String(150), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="to_do", nullable=False, index=True)  # to_do, requested, awaiting, received, analyzed, done
    result = Column(String(50), default="pending", nullable=False, index=True)  # pending, confirmed, contradicted, inconclusive, not_obtainable
    unlocatable_reason = Column(String(255), nullable=True)
    supporting_evidence_ids = Column(Text, nullable=True)  # JSON array of exhibit IDs
    supporting_citations = Column(Text, nullable=True)  # JSON or text citation details
    clock_offset_seconds = Column(Integer, default=0, nullable=False)  # Device clock offset vs UTC/standard
    explanation = Column(Text, nullable=True)
    is_system_suggested = Column(Boolean, default=False, nullable=False)
    verified_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_by_name = Column(String(150), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    retention_warning_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    claim = relationship("AlibiClaim", back_populates="checks")
    segment = relationship("AlibiSegment", back_populates="checks")
    investigation_task = relationship("InvestigationTask", foreign_keys=[investigation_task_id])
    owner = relationship("User", foreign_keys=[owner_id])
    verifier = relationship("User", foreign_keys=[verified_by_id])


class StatementComparison(Base):
    """
    Line-by-line statement assertion extraction and candidate evidence matching.
    """
    __tablename__ = "statement_comparisons"
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("alibi_claims.id", ondelete="CASCADE"), nullable=False, index=True)
    statement_id = Column(Integer, ForeignKey("interview_statements.id", ondelete="CASCADE"), nullable=True, index=True)
    line_number = Column(Integer, nullable=False)
    statement_text = Column(Text, nullable=False)
    quote_citation = Column(String(255), nullable=True)
    extracted_facts = Column(Text, nullable=True)  # JSON dict {time, place, action, people, vehicle, phone}
    result = Column(String(50), default="unverified", nullable=False)  # consistent, contradicted, unverified, not_checkable
    matched_evidence_ids = Column(Text, nullable=True)  # JSON array of evidence IDs
    reasoning = Column(Text, nullable=True)
    review_state = Column(String(50), default="proposed", nullable=False)  # proposed, confirmed, rejected
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    claim = relationship("AlibiClaim", back_populates="comparisons")
    statement = relationship("InterviewStatement", foreign_keys=[statement_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by_id])


# ==============================================================================
# MULTILINGUAL & INTAKE MODELS
# ==============================================================================

class LegalTerm(Base):
    __tablename__ = "legal_terms"
    id = Column(Integer, primary_key=True, index=True)
    term_key = Column(String(100), unique=True, index=True, nullable=False)
    statute = Column(String(50), nullable=False)
    section = Column(String(50), nullable=False)
    english_label = Column(String(200), nullable=False)
    hindi_label = Column(String(200), nullable=False)
    marathi_label = Column(String(200), nullable=False)
    plain_explanation = Column(Text, nullable=False)
    court_admissibility_notes = Column(Text, nullable=True)
    required_certificates = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PersonAlias(Base):
    __tablename__ = "person_aliases"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    person_id = Column(Integer, ForeignKey("case_persons.id", ondelete="CASCADE"), nullable=True, index=True)
    canonical_name = Column(String(150), nullable=False, index=True)
    alias_name = Column(String(150), nullable=False, index=True)
    script = Column(String(30), default="devanagari", nullable=False)
    phonetic_key = Column(String(64), nullable=False, index=True)
    source_exhibit_id = Column(Integer, ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True)
    confirmed_by = Column(String(100), nullable=True)
    is_verified = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("Case", backref="person_aliases")
    person = relationship("CasePerson", backref="alias_records")
    source_exhibit = relationship("Evidence")


class IntakeItem(Base):
    __tablename__ = "intake_items"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    original_file_name = Column(String(255), nullable=True)
    storage_path = Column(String(500), nullable=True)
    file_hash = Column(String(64), nullable=False, index=True)
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    raw_text = Column(Text, nullable=True)
    parsed_metadata = Column(Text, nullable=True)
    proposed_fields = Column(Text, nullable=True)
    status = Column(String(50), default="ready_for_review", nullable=False, index=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_by_name = Column(String(150), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    applied_entities_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("Case", backref="intake_items")
    reviewer = relationship("User")


class IntakeFeedback(Base):
    __tablename__ = "intake_feedback"
    id = Column(Integer, primary_key=True, index=True)
    intake_item_id = Column(Integer, ForeignKey("intake_items.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(50), nullable=False)
    language = Column(String(20), default="mr", nullable=False)
    field_group = Column(String(50), nullable=False)
    field_key = Column(String(100), nullable=False)
    ai_proposed_value = Column(Text, nullable=True)
    final_confirmed_value = Column(Text, nullable=True)
    was_edited = Column(Boolean, default=False, nullable=False)
    is_rejected = Column(Boolean, default=False, nullable=False)
    correction_notes = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_name = Column(String(150), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    intake_item = relationship("IntakeItem", backref="feedback_entries")
    case = relationship("Case")


# ==============================================================================
# OFFLINE SYNC & NOTIFICATION MODELS
# ==============================================================================

class SyncIdempotencyRecord(Base):
    __tablename__ = "sync_idempotency_records"
    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String(100), unique=True, index=True, nullable=False)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(64), nullable=False)
    endpoint = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False)  # applied, failed
    device_timestamp = Column(DateTime(timezone=True), nullable=False)
    server_receipt_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    result_summary = Column(Text, nullable=True)

    case = relationship("Case")


class NotificationLog(Base):
    __tablename__ = "notification_logs"
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=True, index=True)
    channel = Column(String(32), nullable=False, index=True)  # in_app, sms, whatsapp, email
    recipient_address = Column(String(150), nullable=False)
    message_template_id = Column(String(64), nullable=False)
    message_content = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, index=True)  # sent, failed, delivered, escalated
    provider_ref = Column(String(100), nullable=True)
    attempts = Column(Integer, default=1, nullable=False)
    escalated_to_user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User")
    case = relationship("Case")
    alert = relationship("Alert")


# ==============================================================================
# SCORING, COLLABORATION & PRIOR RECORDS MODELS
# ==============================================================================

class SuspectProfileFactor(Base):
    __tablename__ = "suspect_profile_factors"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    hypothesis_id = Column(Integer, ForeignKey("hypotheses.id"), nullable=False)
    suspect_name = Column(String, nullable=True)
    factor_type = Column(String, nullable=False, index=True)  # access, opportunity, means, motive, alibi_status, travel_feasibility
    factor_value = Column(String, nullable=False)
    numeric_adjustment = Column(Float, default=0.5)
    note = Column(Text, nullable=True)
    source_evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=True)
    source_exhibit_name = Column(String, nullable=True)
    confidence = Column(Float, default=0.85)
    entered_by = Column(String, default="Analyst")
    is_ai_suggested = Column(Boolean, default=False)
    is_confirmed = Column(Boolean, default=True)
    confirmed_by = Column(String, nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    version = Column(Integer, default=1, nullable=False)

    case = relationship("Case", backref="suspect_profile_factors")
    hypothesis = relationship("Hypothesis", backref="suspect_profile_factors")
    source_evidence = relationship("Evidence", backref="profile_factors")


class BackgroundWeightConfig(Base):
    __tablename__ = "background_weight_configs"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    access_weight = Column(Float, default=0.25)
    opportunity_weight = Column(Float, default=0.25)
    means_weight = Column(Float, default=0.15)
    motive_weight = Column(Float, default=0.20)
    travel_feasibility_weight = Column(Float, default=0.15)
    alibi_strongly_verified_discount = Column(Float, default=0.10)
    alibi_partially_verified_discount = Column(Float, default=0.50)
    alibi_contradicted_multiplier = Column(Float, default=1.30)
    impossible_travel_penalty = Column(Float, default=0.05)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    case = relationship("Case", backref="background_weight_config")


class PriorRecord(Base):
    __tablename__ = "prior_records"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    hypothesis_id = Column(Integer, ForeignKey("hypotheses.id", ondelete="CASCADE"), nullable=True)
    suspect_name = Column(String(150), nullable=True)
    offence_type = Column(String(100), nullable=False)
    conviction_date = Column(DateTime(timezone=True), nullable=True)
    punishment = Column(String(255), nullable=True)
    jurisdiction = Column(String(100), nullable=True)
    mo_similarity = Column(Float, default=0.5)
    relevance_score = Column(Float, default=0.5)
    is_excluded = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    case = relationship("Case", backref="prior_records")
    hypothesis = relationship("Hypothesis", backref="prior_records")


class LikelihoodRatioReference(Base):
    __tablename__ = "likelihood_ratio_references"
    id = Column(Integer, primary_key=True, index=True)
    evidence_type = Column(String(50), nullable=False)
    finding_description = Column(String(255), nullable=False)
    typical_lr = Column(Float, default=1.0)
    conservative_lr = Column(Float, default=1.0)
    aggressive_lr = Column(Float, default=1.0)
    source_citation = Column(String(255), nullable=True)


class ScoringConfigVersion(Base):
    __tablename__ = "scoring_config_versions"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=True)
    version = Column(Integer, default=1)
    config_json = Column(Text, nullable=False)
    created_by = Column(String(150), default="System")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EditLock(Base):
    __tablename__ = "edit_locks"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(100), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_name = Column(String(150), nullable=False)
    acquired_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class CasePresence(Base):
    __tablename__ = "case_presence"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_name = Column(String(150), nullable=False)
    current_page = Column(String(100), nullable=True)
    last_ping_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CollaborationEvent(Base):
    __tablename__ = "collaboration_events"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_name = Column(String(150), nullable=False)
    payload_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# ==============================================================================
# SECURITY, CDR, BANKING, CHARGESHEET, INTERVIEW, AUDIT & SYSTEM MODELS
# ==============================================================================

class UserSession(Base):
    __tablename__ = "user_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_token_hash = Column(String(64), nullable=False, index=True)
    device_info = Column(String(255), default="Unknown Device", nullable=True)
    ip_address = Column(String(64), default="127.0.0.1", nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_active_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)

    user = relationship("User", backref="sessions")


class SystemSecurityConfig(Base):
    __tablename__ = "system_security_configs"
    id = Column(Integer, primary_key=True, index=True)
    default_ai_provider = Column(String(50), default="cloud_gemini", nullable=False)
    local_model_endpoint = Column(String(255), default="http://localhost:11434/v1", nullable=False)
    local_model_name = Column(String(100), default="llama3", nullable=False)
    allow_external_ai_global = Column(Boolean, default=True, nullable=False)
    default_session_duration_minutes = Column(Integer, default=15, nullable=False)
    require_2fa_for_admins = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    updated_by = Column(String(100), nullable=True)


class EmailLog(Base):
    __tablename__ = "email_logs"
    id = Column(Integer, primary_key=True, index=True)
    recipient_email = Column(String, nullable=False)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True)
    subject = Column(String, nullable=False)
    status = Column(String, default="pending", nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @property
    def recipient(self):
        return self.recipient_email


class BackupRecord(Base):
    __tablename__ = "backup_records"
    id = Column(Integer, primary_key=True, index=True)
    backup_filename = Column(String(255), nullable=False)
    backup_type = Column(String(50), default="full", nullable=False)
    size_bytes = Column(Integer, default=0, nullable=False)
    sha256_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(String(100), default="system", nullable=False)
    restore_test_status = Column(String(50), default="pending", nullable=False)
    restore_test_at = Column(DateTime(timezone=True), nullable=True)
    restore_test_notes = Column(Text, nullable=True)
    storage_path = Column(String(500), nullable=False)


class CDRRecord(Base):
    __tablename__ = "cdr_records"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    calling_number = Column(String(50), nullable=False, index=True)
    called_number = Column(String(50), nullable=False, index=True)
    call_start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    duration_seconds = Column(Integer, default=0, nullable=False)
    call_type = Column(String(20), default="voice", nullable=False)
    tower_id = Column(String(50), nullable=True, index=True)
    tower_latitude = Column(Float, nullable=True)
    tower_longitude = Column(Float, nullable=True)
    tower_azimuth = Column(Integer, nullable=True)
    imei = Column(String(50), nullable=True)
    imsi = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("Case", backref="cdr_records")


class BankTransaction(Base):
    __tablename__ = "bank_transactions"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    account_number = Column(String(50), nullable=False, index=True)
    bank_name = Column(String(100), nullable=False)
    transaction_date = Column(DateTime(timezone=True), nullable=False, index=True)
    transaction_type = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    balance_after = Column(Float, nullable=True)
    counterparty_name = Column(String(150), nullable=True)
    counterparty_account = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    is_suspicious = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("Case", backref="bank_transactions")


class WatchlistEntry(Base):
    __tablename__ = "watchlist_entries"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    identifier_type = Column(String(50), nullable=False)
    identifier_value = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("Case", backref="watchlist_entries")


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_type = Column(String, nullable=False)
    severity = Column(String, default="warning", nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    linked_item_type = Column(String, nullable=True)
    linked_item_id = Column(String, nullable=True)
    status = Column(String, default="unread", nullable=False)
    dedup_key = Column(String, nullable=False, unique=True)
    is_restricted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(String, nullable=True)
    snoozed_until = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_reason = Column(Text, nullable=True)

    case = relationship("Case", backref="alerts")

    # Compatibility properties
    @property
    def is_read(self):
        return self.status != "unread"

    @property
    def is_dismissed(self):
        return self.status in ("dismissed", "resolved", "acknowledged")

    @property
    def alert_type(self):
        return self.rule_type

    @property
    def description(self):
        return self.message


class ChargesheetDraft(Base):
    __tablename__ = "chargesheet_drafts"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    case = relationship("Case", backref="chargesheet_drafts")


class ChargesheetEditLog(Base):
    __tablename__ = "chargesheet_edit_logs"
    id = Column(Integer, primary_key=True, index=True)
    chargesheet_id = Column(Integer, ForeignKey("chargesheet_drafts.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    section_edited = Column(String(100), default="general", nullable=False)
    edit_summary = Column(Text, default="", nullable=False)
    edited_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    edited_by_name = Column(String(100), default="Investigating Officer", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=func.now(), nullable=False)
    draft_id = Column(Integer, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    section_name = Column(String(100), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)


class DataConnector(Base):
    __tablename__ = "data_connectors"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    connector_type = Column(String(50), nullable=False)
    config_json = Column(Text, nullable=True)
    status = Column(String(50), default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("Case", backref="connectors")


class ConnectorIngestRecord(Base):
    __tablename__ = "connector_ingest_records"
    id = Column(Integer, primary_key=True, index=True)
    connector_id = Column(Integer, ForeignKey("data_connectors.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    status = Column(String(50), default="ingested", nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CaseDeadline(Base):
    __tablename__ = "case_deadlines"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    statute_rule_id = Column(Integer, ForeignKey("statutory_deadline_rules.id"), nullable=True)
    title = Column(String, nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, default="pending", nullable=False)
    satisfied_at = Column(DateTime(timezone=True), nullable=True)
    satisfied_by = Column(String, nullable=True)
    extended_until = Column(DateTime(timezone=True), nullable=True)
    extension_reason = Column(Text, nullable=True)
    last_alert_days = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("Case", backref="deadlines")
    statute_rule = relationship("StatutoryDeadlineRule", backref="case_deadlines")

    @property
    def deadline_date(self):
        return self.due_date

    @property
    def is_dismissed(self):
        return self.status in ("satisfied", "dismissed")


class StatutoryDeadlineRule(Base):
    __tablename__ = "statutory_deadline_rules"
    id = Column(Integer, primary_key=True, index=True)
    statute_name = Column(String, nullable=False)
    section_reference = Column(String, nullable=False)
    offence_category = Column(String, nullable=False)
    limit_days = Column(Integer, nullable=False)
    trigger_event = Column(String, nullable=False)
    description = Column(String, nullable=False)
    procedure_name = Column(String, nullable=True)
    is_reviewed_by_expert = Column(Boolean, default=False)
    expert_reviewer = Column(String, nullable=True)
    legal_notes = Column(Text, nullable=True)


class HandoverSummary(Base):
    __tablename__ = "handover_summaries"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    from_officer = Column(String(150), nullable=False)
    to_officer = Column(String(150), nullable=False)
    handover_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String(50), default="pending_review", nullable=False)

    case = relationship("Case", backref="handovers")


class Interview(Base):
    __tablename__ = "interviews"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    session_code = Column(String(100), nullable=False, index=True)
    interviewee_name = Column(String(150), nullable=False)
    interviewee_role = Column(String(50), default="suspect")
    interviewer_name = Column(String(150), nullable=False)
    interview_date = Column(String(50), nullable=True)
    duration = Column(String(50), default="00:00 mins")
    status = Column(String(50), default="Transcribed")
    audio_url = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    case = relationship("Case", backref="interviews")
    statements = relationship("InterviewStatement", back_populates="interview", cascade="all, delete-orphan", order_by="InterviewStatement.sequence_order")
    contradictions = relationship("InterviewContradiction", back_populates="interview", cascade="all, delete-orphan")


class InterviewStatement(Base):
    __tablename__ = "interview_statements"
    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_order = Column(Integer, nullable=False, default=1)
    speaker = Column(String(150), nullable=False)
    role = Column(String(50), default="interviewee")
    timestamp_marker = Column(String(20), default="00:00")
    seconds = Column(Integer, default=0)
    question = Column(Text, nullable=True)
    question_source_type = Column(String(50), nullable=True)
    question_source_id = Column(String(50), nullable=True)
    text = Column(Text, nullable=False)
    tag = Column(String(50), nullable=True)
    is_contradiction_flag = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    interview = relationship("Interview", back_populates="statements")
    contradictions = relationship("InterviewContradiction", back_populates="statement", foreign_keys="InterviewContradiction.statement_id", cascade="all, delete-orphan")


class InterviewContradiction(Base):
    __tablename__ = "interview_contradictions"
    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True)
    statement_id = Column(Integer, ForeignKey("interview_statements.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    quote_new = Column(Text, nullable=False)
    source_new = Column(String(255), nullable=False)
    quote_prior = Column(Text, nullable=False)
    source_prior = Column(String(255), nullable=False)

    interview = relationship("Interview", back_populates="contradictions")
    statement = relationship("InterviewStatement", foreign_keys=[statement_id], back_populates="contradictions")


class ExhibitTranslation(Base):
    __tablename__ = "exhibit_translations"
    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True)
    target_language = Column(String(20), nullable=False)
    translated_text = Column(Text, nullable=False)
    translator_type = Column(String(50), default="gemini_pro")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    exhibit_id = Column(Integer, ForeignKey("evidence.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by = Column(String, nullable=True)
    job_type = Column(String, default="process_evidence", index=True)
    status = Column(String, default="queued", index=True)
    current_stage = Column(String, default="queued")
    progress_pct = Column(Float, default=0.0)
    attempt_count = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    error_message = Column(String, nullable=True)
    error_detail = Column(Text, nullable=True)
    stage_results = Column(Text, nullable=True)
    heartbeat = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True, index=True)
    priority = Column(Integer, default=0, index=True)
    cancel_requested = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)


class ValidationRunRecord(Base):
    __tablename__ = "validation_run_records"
    id = Column(Integer, primary_key=True, index=True)
    suite_id = Column(String(100), nullable=False)
    run_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    passed_cases = Column(Integer, default=0)
    failed_cases = Column(Integer, default=0)
    details_json = Column(Text, nullable=True)


class ReportRequest(Base):
    __tablename__ = "report_requests"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    report_type = Column(String(255), nullable=False)
    requested_from = Column(String(255), nullable=False)
    requested_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expected_date = Column(DateTime(timezone=True), nullable=False)
    received_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="requested", nullable=False)
    linked_evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=True)
    urgency = Column(String(50), default="high", nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    case = relationship("Case", backref="report_requests")


class PersonRegister(Base):
    __tablename__ = "people_register"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), default="witness", nullable=False)
    contact_info = Column(String(255), nullable=True)
    linked_entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)
    is_important = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    case = relationship("Case", backref="people_register_entries")


class StatementTracker(Base):
    __tablename__ = "statements_tracker"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=False)
    witness_name = Column(String(255), nullable=False)
    statement_type = Column(String(100), default="161_crpc", nullable=False)
    status = Column(String(50), default="recorded", nullable=False)
    recorded_date = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    case = relationship("Case", backref="statements_tracker_entries")

class OffenceEvidenceProtocol(Base):
    __tablename__ = "offence_evidence_protocols"

    id = Column(Integer, primary_key=True, index=True)
    offence_category = Column(String, nullable=False, index=True)
    offence_section_keywords = Column(String, nullable=False)
    exhibit_code = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    mandatory = Column(Boolean, default=True, nullable=False)
    legal_provision = Column(String, nullable=False)
    matching_keywords = Column(Text, nullable=False)
    consequence_if_missing = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ==============================================================================
# PHYSICAL EVIDENCE, EXTENDED CUSTODY, SEALS, MALKHANA & FSL TRACKING
# ==============================================================================

class PhysicalItem(Base):
    """
    1-to-1 extension of Evidence for physical forensic articles (weapons, clothing,
    biological samples, narcotics, vehicles, original documents).
    """
    __tablename__ = "physical_items"
    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    category = Column(String(50), nullable=False)  # weapon, clothing, biological_sample, vehicle, device, narcotics, cash_valuables, document_original, other
    description = Column(Text, nullable=False)
    identifying_marks = Column(Text, nullable=True)
    quantity_or_weight = Column(String(100), nullable=True)
    condition = Column(String(100), default="intact", nullable=False)  # intact, damaged, rusted, bloodstained, burnt, fragmented
    packaging = Column(String(100), default="sealed_plastic_bag", nullable=False)  # paper_envelope, sealed_plastic_bag, tamper_evident_pouch, cloth_parcel, wooden_box, glass_vial
    seized_from = Column(String(255), nullable=True)
    seized_at = Column(String(255), nullable=True)
    seized_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    seized_by_name = Column(String(255), nullable=True)
    seizure_memo_id = Column(Integer, ForeignKey("evidence.id"), nullable=True)
    panch_witness_1_id = Column(Integer, ForeignKey("case_persons.id"), nullable=True)
    panch_witness_2_id = Column(Integer, ForeignKey("case_persons.id"), nullable=True)
    current_location = Column(String(100), default="malkhana", nullable=False)  # scene, police_station, malkhana, fsl, court, returned, disposed
    current_custodian = Column(String(255), nullable=True)
    malkhana_entry_number = Column(String(100), nullable=True, index=True)
    rack_or_shelf = Column(String(100), nullable=True)
    status = Column(String(50), default="deposited_malkhana", nullable=False)  # seized, deposited_malkhana, issued_investigation, dispatched_fsl, returned_from_fsl, produced_court, returned_to_owner, disposed
    is_perishable = Column(Boolean, default=False, nullable=False)
    is_biological = Column(Boolean, default=False, nullable=False)
    is_firearm = Column(Boolean, default=False, nullable=False)
    is_narcotics = Column(Boolean, default=False, nullable=False)
    dispatch_time_limit_days = Column(Integer, nullable=True)  # e.g., 3 days for biological samples
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    evidence = relationship("Evidence", foreign_keys=[evidence_id], backref=backref("physical_details", uselist=False))
    seizure_memo = relationship("Evidence", foreign_keys=[seizure_memo_id])
    seized_by_user = relationship("User", foreign_keys=[seized_by_id])
    panch_witness_1 = relationship("CasePerson", foreign_keys=[panch_witness_1_id])
    panch_witness_2 = relationship("CasePerson", foreign_keys=[panch_witness_2_id])


class Seal(Base):
    """
    Tamper-Evident Forensic Seals applied to physical evidence parcels.
    """
    __tablename__ = "seals"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True)
    seal_number = Column(String(100), nullable=False, index=True)
    owner_mark = Column(String(255), nullable=False)  # e.g., "IO Seal / Crime Branch Unit 1"
    package_description = Column(String(255), nullable=True)
    applied_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    applied_by_name = Column(String(255), nullable=False)
    applied_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    applied_in_presence_of = Column(Text, nullable=True)  # JSON list of witness names
    status = Column(String(50), default="intact", nullable=False)  # intact, broken_authorized, broken_unauthorized, resealed
    replaced_seal_id = Column(Integer, ForeignKey("seals.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("Case", backref="seals")
    evidence = relationship("Evidence", backref="seals")
    replaced_seal = relationship("Seal", remote_side=[id])


class SealEvent(Base):
    """
    Immutable lifecycle events on seals (apply, inspect, break, reseal).
    Holds photo evidence, OCR comparisons, and witness attestations.
    """
    __tablename__ = "seal_events"
    id = Column(Integer, primary_key=True, index=True)
    seal_id = Column(Integer, ForeignKey("seals.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # apply, inspect, break, reseal
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_name = Column(String(255), nullable=False)
    witnesses = Column(Text, nullable=True)  # JSON list
    reason = Column(Text, nullable=True)  # Mandatory for break/reseal
    new_seal_id = Column(Integer, ForeignKey("seals.id"), nullable=True)
    photos = Column(Text, nullable=True)  # JSON list of photo metadata {photo_path, ocr_number, ocr_confidence, match_status, gps_lat, gps_lon, timestamp, hash}

    seal = relationship("Seal", foreign_keys=[seal_id], backref="events")
    new_seal = relationship("Seal", foreign_keys=[new_seal_id])


class FSLDispatch(Base):
    """
    Forensic Science Laboratory (FSL) forwarding letter and dispatch docket.
    """
    __tablename__ = "fsl_dispatches"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    forwarding_letter_number = Column(String(100), nullable=False, index=True)
    forwarding_letter_date = Column(DateTime(timezone=True), nullable=False)
    fsl_name = Column(String(255), nullable=False)
    examination_requested = Column(String(255), nullable=False)
    sent_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    carried_by_name = Column(String(255), nullable=False)
    carried_by_role = Column(String(100), nullable=True)
    carried_by_id_card = Column(String(100), nullable=True)
    mode_of_transit = Column(String(50), default="police_messenger", nullable=False)  # police_messenger, registered_post, authorized_courier
    expected_report_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="prepared", nullable=False)  # prepared, dispatched, received_by_lab, under_examination, report_issued, items_returned, closed
    lab_acknowledgement_receipt_path = Column(String(500), nullable=True)
    lab_acknowledgement_date = Column(DateTime(timezone=True), nullable=True)
    report_evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=True)
    return_date = Column(DateTime(timezone=True), nullable=True)
    return_carried_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("Case", backref="fsl_dispatches")
    report_evidence = relationship("Evidence", foreign_keys=[report_evidence_id])


class FSLDispatchItem(Base):
    """
    Exhibits bundled into an FSL dispatch docket.
    """
    __tablename__ = "fsl_dispatch_items"
    id = Column(Integer, primary_key=True, index=True)
    dispatch_id = Column(Integer, ForeignKey("fsl_dispatches.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True)
    seal_number_at_dispatch = Column(String(100), nullable=False)
    seal_status_at_dispatch = Column(String(50), default="intact", nullable=False)
    return_seal_number = Column(String(100), nullable=True)
    return_seal_status = Column(String(50), nullable=True)
    condition_on_return = Column(String(255), nullable=True)

    dispatch = relationship("FSLDispatch", backref="items")
    evidence = relationship("Evidence")


class MalkhanaStockCheck(Base):
    """
    Periodic station-level physical inventory audit of the Muddimalkhana.
    """
    __tablename__ = "malkhana_stock_checks"
    id = Column(Integer, primary_key=True, index=True)
    police_station = Column(String(100), nullable=False, index=True)
    check_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    conducted_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    conducted_by_name = Column(String(255), nullable=False)
    total_items_expected = Column(Integer, default=0, nullable=False)
    items_verified_present = Column(Integer, default=0, nullable=False)
    discrepancies_count = Column(Integer, default=0, nullable=False)
    discrepancies_details = Column(Text, nullable=True)  # JSON list of discrepancies
    status = Column(String(50), default="in_progress", nullable=False)  # in_progress, completed, discrepancy_reported
    supervisor_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ==============================================================================
# ALERTS, NOTIFICATIONS, DECISION QUALITY & MULTILINGUAL MODELS
# ==============================================================================

class AlertRuleConfig(Base):
    __tablename__ = "alert_rule_configs"
    id = Column(Integer, primary_key=True, index=True)
    rule_type = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    severity_default = Column(String, default="warning", nullable=False)
    threshold_val = Column(Float, nullable=True)
    recipients_role = Column(String, default="all", nullable=False)
    auto_resolve = Column(Boolean, default=True, nullable=False)


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_type = Column(String, default="all", nullable=False)
    in_app_enabled = Column(Boolean, default=True, nullable=False)
    email_enabled = Column(Boolean, default=False, nullable=False)
    digest_mode = Column(String, default="immediate", nullable=False)
    quiet_hours_start = Column(String, nullable=True)
    quiet_hours_end = Column(String, nullable=True)


class UserCaseState(Base):
    __tablename__ = "user_case_states"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_handover_viewed_at = Column(DateTime(timezone=True), nullable=True)


class DecisionSignoff(Base):
    __tablename__ = "decision_signoffs"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    item_type = Column(String(64), nullable=False, index=True)
    item_id = Column(Integer, nullable=False, index=True)
    item_summary = Column(Text, nullable=False)
    maker_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    maker_name = Column(String(128), nullable=False)
    checker_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    checker_name = Column(String(128), nullable=True)
    checker_role = Column(String(64), nullable=True)
    status = Column(String(32), default="pending", nullable=False, index=True)
    review_notes = Column(Text, nullable=True)
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)


class CrossCaseEntityLink(Base):
    __tablename__ = "cross_case_entity_links"
    id = Column(Integer, primary_key=True, index=True)
    source_case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    source_entity_id = Column(Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=True, index=True)
    target_case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    target_entity_id = Column(Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=True, index=True)
    entity_type = Column(String(64), nullable=False, index=True)
    match_type = Column(String(64), nullable=False)
    match_value = Column(String(255), nullable=False)
    similarity_score = Column(Float, default=1.0, nullable=False)
    status = Column(String(32), default="pending_review", nullable=False, index=True)
    confidence_reason = Column(Text, nullable=False)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_by_name = Column(String, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class LanguageProfileConfig(Base):
    __tablename__ = "language_profile_configs"
    id = Column(Integer, primary_key=True, index=True)
    language = Column(String(20), nullable=False, index=True)
    script = Column(String(30), nullable=False)
    content_type = Column(String(30), nullable=False)
    reading_method = Column(String(64), nullable=False)
    fallback_method = Column(String(64), nullable=True)
    stt_model_hint = Column(String(64), nullable=True)
    preprocessing_steps = Column(Text, default="[]", nullable=False)
    confidence_threshold = Column(Float, default=0.75, nullable=False)
    translate_by_default = Column(Boolean, default=True, nullable=False)
    default_target_language = Column(String(20), default="en", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ExhibitTextVersion(Base):
    __tablename__ = "exhibit_text_versions"
    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False, index=True)
    raw_text = Column(Text, nullable=False)
    normalized_text = Column(Text, nullable=False)
    reading_method = Column(String(64), nullable=False)
    overall_confidence = Column(Float, default=1.0, nullable=False)
    status = Column(String(32), default="machine_read", nullable=False)
    is_current = Column(Boolean, default=False, nullable=False, index=True)
    created_by = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    edit_reason = Column(Text, nullable=True)
    diff_summary = Column(Text, nullable=True)
    requires_second_signoff = Column(Boolean, default=False, nullable=False)
    second_signoff_by = Column(String(128), nullable=True)
    second_signoff_at = Column(DateTime(timezone=True), nullable=True)
    is_reverted = Column(Boolean, default=False, nullable=False)
    reverted_from_version = Column(Integer, nullable=True)


class ExhibitSegment(Base):
    __tablename__ = "exhibit_segments"
    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(Integer, ForeignKey("exhibit_text_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)
    bbox_json = Column(Text, nullable=True)
    start_time_sec = Column(Float, nullable=True)
    end_time_sec = Column(Float, nullable=True)
    speaker_label = Column(String(64), nullable=True)
    raw_text = Column(Text, nullable=False)
    normalized_text = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)
    is_low_confidence = Column(Boolean, default=False, nullable=False)
    status = Column(String(32), default="machine_read", nullable=False)
    reading_method = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TranslationSegment(Base):
    __tablename__ = "translation_segments"
    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(Integer, ForeignKey("exhibit_text_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    source_language = Column(String(20), nullable=False)
    target_language = Column(String(20), default="en", nullable=False)
    author_type = Column(String(32), default="machine", nullable=False)
    author_name = Column(String(128), nullable=False)
    model_used = Column(String(64), nullable=True)
    review_status = Column(String(32), default="unreviewed", nullable=False)
    reviewed_by = Column(String(128), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    translated_text = Column(Text, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ==============================================================================
# AUTOMATIC METADATA SYNCHRONIZATION WITH DATABASE SCHEMA
# ==============================================================================
def _auto_sync_db_columns():
    try:
        import sqlite3
        from database import engine
        from sqlalchemy.orm import configure_mappers
        db_url = str(engine.url)
        if "sqlite" in db_url:
            path = db_url.replace("sqlite:///", "").replace("sqlite://", "")
            if path:
                conn = sqlite3.connect(path)
                cursor = conn.cursor()
                def _get_sa_type(t):
                    t = (t or "").upper()
                    if "INT" in t: return Integer
                    if "FLOAT" in t or "REAL" in t: return Float
                    if "BOOL" in t: return Boolean
                    if "TIME" in t or "DATE" in t: return DateTime(timezone=True)
                    if "TEXT" in t: return Text
                    return String

                def _get_sql_type(col):
                    t_str = str(col.type).upper()
                    if "INT" in t_str: return "INTEGER"
                    if "FLOAT" in t_str or "NUMERIC" in t_str or "REAL" in t_str: return "FLOAT"
                    if "BOOL" in t_str: return "BOOLEAN"
                    if "TIME" in t_str or "DATE" in t_str: return "DATETIME"
                    if "TEXT" in t_str: return "TEXT"
                    return "VARCHAR"

                for mapper in list(Base.registry.mappers):
                    table = mapper.mapped_table
                    model_cols = {c.name: c for c in table.columns}
                    try:
                        cursor.execute(f"PRAGMA table_info({table.name})")
                        rows = cursor.fetchall()
                        if not rows:
                            continue
                        db_cols = {r[1]: r[2] for r in rows}

                        # 1. DB -> Model: register DB columns in SQLAlchemy model
                        for c_name, c_type in db_cols.items():
                            if c_name not in model_cols:
                                sa_t = _get_sa_type(c_type)
                                table.append_column(Column(c_name, sa_t, nullable=True))
                                setattr(mapper.class_, c_name, getattr(table.c, c_name))

                        # 2. Model -> DB: auto-create missing table columns in SQLite
                        for c_name, col in model_cols.items():
                            if c_name not in db_cols:
                                sql_t = _get_sql_type(col)
                                try:
                                    cursor.execute(f"ALTER TABLE {table.name} ADD COLUMN {c_name} {sql_t}")
                                    conn.commit()
                                except Exception:
                                    pass
                    except Exception:
                        pass
                conn.close()
                configure_mappers()
    except Exception:
        pass

_auto_sync_db_columns()
