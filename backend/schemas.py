# backend/schemas.py
from pydantic import BaseModel
from typing import Optional, List, Union, Any, Dict
from datetime import datetime

# ---------- CASE SCHEMAS ----------
class CaseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "Active"
    created_by: Optional[str] = "current_user"

class CaseOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: str
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# ---------- EVIDENCE SCHEMAS ----------
class EvidenceCreate(BaseModel):
    case_id: int
    file_name: str
    file_type: str
    file_size: int
    storage_path: str
    uploaded_by: str = "current_user"

class EvidenceOut(BaseModel):
    id: int
    case_id: int
    file_name: str
    file_type: str
    file_size: int
    upload_date: datetime
    processing_status: str
    extracted_text: Optional[str] = None
    source: Optional[str] = None
    evidence_type: Optional[str] = "document"
    file_hash: Optional[str] = None
    hash_verified: Optional[bool] = False
    chain_of_custody_complete: Optional[bool] = False
    sec_65b_certificate_present: Optional[bool] = False
    source_independent: Optional[bool] = True
    quality_rating: Optional[float] = 3.0
    collected_by: Optional[str] = None
    collection_date: Optional[datetime] = None
    custody_notes: Optional[str] = None
    is_deleted: Optional[bool] = False

    class Config:
        from_attributes = True

# ---------- ENTITY SCHEMAS ----------
class EntityOut(BaseModel):
    id: int
    type: str
    name: str
    confidence: float
    evidence_id: int
    source_quote: Optional[str] = None
    source_char_start: Optional[int] = None
    source_char_end: Optional[int] = None
    source_page_number: Optional[int] = None

    class Config:
        from_attributes = True

# ---------- EVENT SCHEMAS ----------
class EventOut(BaseModel):
    id: int
    timestamp: Optional[datetime]
    title: str
    description: str
    location: Optional[str]
    confidence: float
    evidence_id: int
    source_quote: Optional[str] = None
    source_char_start: Optional[int] = None
    source_char_end: Optional[int] = None
    source_page_number: Optional[int] = None

    class Config:
        from_attributes = True


# ---------- EVIDENCE ASSESSMENT SCHEMAS ----------
class EvidenceAssessmentCreate(BaseModel):
    evidence_id: int
    classification: str  # strong_support, moderate_support, weak_support, neutral, weak_contradiction, moderate_contradiction, strong_contradiction
    reason: Optional[str] = None
    llm_confidence: Optional[float] = 0.0
    reliability: Optional[float] = 1.0
    original_classification: Optional[str] = None
    analyst_override: Optional[bool] = False
    analyst_notes: Optional[str] = None
    quoted_source_line: Optional[str] = None

class EvidenceAssessmentOut(BaseModel):
    id: int
    hypothesis_id: int
    evidence_id: int
    classification: str
    original_classification: Optional[str] = None
    analyst_override: bool = False
    analyst_notes: Optional[str] = None
    reason: Optional[str] = None
    llm_confidence: float = 0.0
    reliability: float = 1.0
    diagnosticity_weight: Optional[float] = 1.0
    diagnosticity_category: Optional[str] = "Medium"
    quoted_source_line: Optional[str] = None
    computed_reliability: Optional[float] = 1.0
    computed_diagnosticity: Optional[float] = 1.0
    final_contribution: Optional[float] = 0.0
    evidence_file_name: Optional[str] = None
    evidence_file_type: Optional[str] = None
    evidence_type: Optional[str] = "document"

    class Config:
        from_attributes = True

class AssessmentOverrideRequest(BaseModel):
    assessment_id: Optional[int] = None
    hypothesis_id: int
    evidence_id: int
    classification: Optional[str] = None
    evidence_type: Optional[str] = None
    manual_reliability: Optional[float] = None
    hash_verified: Optional[bool] = None
    chain_of_custody_complete: Optional[bool] = None
    sec_65b_certificate_present: Optional[bool] = None
    source_independent: Optional[bool] = None
    quality_rating: Optional[float] = None
    analyst_notes: Optional[str] = "Investigator analytical adjustment"

# ---------- RELIABILITY CONFIG SCHEMAS ----------
class ReliabilityConfigOut(BaseModel):
    id: int
    evidence_type: str
    base_reliability: float
    rationale: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ReliabilityConfigUpdate(BaseModel):
    evidence_type: str
    base_reliability: float
    rationale: Optional[str] = None

# ---------- HYPOTHESIS SCHEMAS ----------
class HypothesisCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "Active"
    support_score: Optional[float] = 0.0

class HypothesisOut(BaseModel):
    id: int
    case_id: int
    title: str
    description: Optional[str]
    status: str
    support_score: float
    disconfirmation_penalty: Optional[float] = 0.0
    relative_likelihood: Optional[float] = 0.0
    created_at: Optional[datetime]
    assessment_count: Optional[int] = 0

    class Config:
        from_attributes = True

class HypothesisDetailOut(BaseModel):
    id: int
    case_id: int
    title: str
    description: Optional[str]
    status: str
    support_score: float
    disconfirmation_penalty: Optional[float] = 0.0
    relative_likelihood: Optional[float] = 0.0
    created_at: Optional[datetime]
    assessments: List[EvidenceAssessmentOut] = []

    class Config:
        from_attributes = True

class SensitivityImpactOut(BaseModel):
    evidence_id: int
    file_name: str
    file_type: str
    diagnosticity_score: float
    diagnosticity_category: str  # High, Medium, Low
    is_critical_pivot: bool  # True if excluding this flips top-ranked hypothesis
    top_hypothesis_with: str
    top_hypothesis_without: str
    impact_level: str  # CRITICAL_PIVOT, HIGH_IMPACT, MODERATE_IMPACT, ROBUST_INSENSITIVE
    score_shifts: Dict[str, float] = {}

class SensitivityAnalysisResponse(BaseModel):
    case_id: int
    baseline_ranking: List[HypothesisOut]
    exhibit_impacts: List[SensitivityImpactOut]
    most_critical_evidence_id: Optional[int] = None
    most_critical_evidence_name: Optional[str] = None

class HypothesisRobustnessOut(BaseModel):
    hypothesis_id: int
    baseline_score: float
    min_score: float
    max_score: float
    range_spread: float
    range_label: str

class ScoringRecalculateResponse(BaseModel):
    success: bool
    total_relative_sum: float = 100.0
    all_zero_diagnosticity: bool = False
    message: Optional[str] = None
    hypotheses: List[Dict[str, Any]] = []
    matrix: Dict[str, Any] = {}
    hypothesis_breakdowns: Dict[str, Any] = {}
    robustness_ranges: Dict[str, Any] = {}
    critical_exhibits: List[Dict[str, Any]] = []

# ---------- CONTRADICTION SCHEMAS ----------
class ContradictionCreate(BaseModel):
    statement_a: str
    source_a_id: Optional[Union[str, int]] = None
    statement_b: str
    source_b_id: Optional[Union[str, int]] = None
    conflict_type: str
    confidence: Optional[float] = 90.0
    status: Optional[str] = "Detected"

class ContradictionOut(BaseModel):
    id: int
    case_id: int
    statement_a: str
    source_a_id: Optional[Union[str, int]] = None
    statement_b: str
    source_b_id: Optional[Union[str, int]] = None
    conflict_type: str
    confidence: float
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ---------- INVESTIGATION TASK SCHEMAS ----------
class InvestigationTaskCreate(BaseModel):
    task: str
    reason: Optional[str] = None
    related_hypothesis_id: Optional[Union[str, int]] = None
    related_contradiction_id: Optional[Union[str, int]] = None
    related_evidence_id: Optional[Union[str, int]] = None
    priority: Optional[str] = "High"
    status: Optional[str] = "Pending"
    assigned_to: Optional[str] = None

class InvestigationTaskOut(BaseModel):
    id: int
    case_id: int
    task: str
    reason: Optional[str] = None
    related_hypothesis_id: Optional[Union[str, int]] = None
    related_contradiction_id: Optional[Union[str, int]] = None
    related_evidence_id: Optional[Union[str, int]] = None
    priority: str
    status: str
    assigned_to: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------- RELATIONSHIP (SEMANTIC GRAPH) SCHEMAS ----------
class RelationshipCreate(BaseModel):
    source_entity_id: int
    target_entity_id: int
    relation_type: str
    evidence_id: Optional[int] = None
    confidence: Optional[float] = 0.90
    reason: Optional[str] = None

class RelationshipOut(BaseModel):
    id: int
    case_id: int
    source_entity_id: int
    target_entity_id: int
    relation_type: str
    evidence_id: Optional[int] = None
    confidence: float
    reason: Optional[str] = None
    created_at: Optional[datetime] = None

    source_entity_name: Optional[str] = None
    target_entity_name: Optional[str] = None

    class Config:
        from_attributes = True


# ---------- AUTH & USER SCHEMAS ----------
class UserRegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: Optional[str] = "analyst"
    badge_number: Optional[str] = None
    department: Optional[str] = None

class UserLoginRequest(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    badge_number: Optional[str] = None
    department: Optional[str] = None
    is_active: bool
    accessible_cases: Optional[List[int]] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: UserOut

class CaseMemberOut(BaseModel):
    id: int
    case_id: int
    user_id: int
    case_role: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    added_at: Optional[datetime] = None
    added_by: Optional[str] = None

    class Config:
        from_attributes = True

class CaseMemberAddRequest(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
    case_role: Optional[str] = None


# ---------- CUSTODY & AUDIT SCHEMAS (PHASE 3 FEATURE 2) ----------

class CustodyLogOut(BaseModel):
    id: int
    evidence_id: int
    case_id: int
    action: str
    actor_name: str
    actor_role: Optional[str] = None
    source_agency: Optional[str] = None
    location: Optional[str] = None
    timestamp: datetime
    file_hash_snapshot: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class AuditLogOut(BaseModel):
    id: int
    case_id: Optional[int] = None
    user_id: Optional[int] = None
    user_name: str
    user_role: Optional[str] = None
    action_type: str
    target_type: str
    target_id: Optional[str] = None
    description: str
    before_value: Optional[str] = None
    after_value: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime
    previous_hash: str
    current_hash: str

    class Config:
        from_attributes = True


class AuditChainVerificationResponse(BaseModel):
    chain_intact: bool
    total_entries: int
    verified_count: int
    genesis_hash: str
    latest_hash: str
    last_timestamp: Optional[str] = None
    status: str
    message: str
    tampered_at_index: Optional[int] = None
    tampered_entry_id: Optional[int] = None
    error: Optional[str] = None


class EvidenceIntegrityResponse(BaseModel):
    success: bool
    evidence_id: int
    file_name: str
    stored_hash: Optional[str] = None
    recomputed_hash: Optional[str] = None
    integrity_verified: bool
    status: str
    message: str


# ---------- SOURCE-SPAN CITATION SCHEMAS (PHASE 3 FEATURE 3) ----------

class ExhibitChunkOut(BaseModel):
    id: int
    evidence_id: int
    case_id: int
    chunk_index: int
    text: str
    page_number: Optional[int] = None
    char_start: int
    char_end: int
    start_time_sec: Optional[float] = None
    end_time_sec: Optional[float] = None

    class Config:
        from_attributes = True


class SourceCitationOut(BaseModel):
    id: int
    case_id: int
    evidence_id: int
    chunk_id: Optional[int] = None
    fact_type: str
    fact_id: Optional[int] = None
    quote: str
    page_number: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    timestamp_sec: Optional[float] = None
    verified_match: bool
    match_confidence: float
    verification_method: str

    class Config:
        from_attributes = True


class TextCorrectionRequest(BaseModel):
    extracted_text: Optional[str] = None
    text: Optional[str] = None


class TextCorrectionResponse(BaseModel):
    success: bool
    evidence_id: int
    total_chunks: int
    total_citations: int
    verified_citations: int
    unverified_citations: int
    message: str