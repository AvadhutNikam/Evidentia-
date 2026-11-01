# backend/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Union, Any, Dict
from datetime import datetime, date

# ---------- CASE SCHEMAS ----------
class CaseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "Active"
    created_by: Optional[str] = "current_user"
    is_demo: Optional[bool] = False
    fir_number: Optional[str] = None
    fir_date: Optional[datetime] = None
    incident_date: Optional[datetime] = None
    arrest_date: Optional[datetime] = None
    remand_date: Optional[datetime] = None
    offence_section: Optional[str] = None
    statutory_time_limit_days: Optional[int] = 90
    # Private Model & Air-Gap Security Settings
    is_sensitive_airgapped: Optional[bool] = False
    ai_provider_override: Optional[str] = None
    local_ai_endpoint: Optional[str] = None
    local_ai_model: Optional[str] = None
    # Statutory Retention & Legal Hold
    retention_period_years: Optional[int] = 20
    retention_expiry_date: Optional[datetime] = None
    is_legal_hold: Optional[bool] = False
    legal_hold_reason: Optional[str] = None
    legal_hold_placed_by: Optional[str] = None
    legal_hold_placed_at: Optional[datetime] = None

class CaseProcedureUpdate(BaseModel):
    fir_number: Optional[str] = None
    fir_date: Optional[datetime] = None
    incident_date: Optional[datetime] = None
    arrest_date: Optional[datetime] = None
    remand_date: Optional[datetime] = None
    offence_section: Optional[str] = None
    statutory_time_limit_days: Optional[int] = None

class CaseOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: str
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime]
    is_demo: Optional[bool] = False
    fir_number: Optional[str] = None
    fir_date: Optional[datetime] = None
    incident_date: Optional[datetime] = None
    arrest_date: Optional[datetime] = None
    remand_date: Optional[datetime] = None
    offence_section: Optional[str] = None
    statutory_time_limit_days: Optional[int] = 90
    # Private Model & Air-Gap Security Settings
    is_sensitive_airgapped: Optional[bool] = False
    ai_provider_override: Optional[str] = None
    local_ai_endpoint: Optional[str] = None
    local_ai_model: Optional[str] = None
    # Statutory Retention & Legal Hold
    retention_period_years: Optional[int] = 20
    retention_expiry_date: Optional[datetime] = None
    is_legal_hold: Optional[bool] = False
    legal_hold_reason: Optional[str] = None
    legal_hold_placed_by: Optional[str] = None
    legal_hold_placed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ---------- EVIDENCE SCHEMAS ----------
class EvidenceCreate(BaseModel):
    case_id: int
    file_name: str
    file_type: str
    file_size: Optional[int] = 0
    storage_path: str
    uploaded_by: str = "current_user"
    extraction_mode: Optional[str] = "live"
    is_demo_fixture: Optional[bool] = False

class EvidenceOut(BaseModel):
    id: int
    case_id: int
    file_name: str
    file_type: str
    file_size: Optional[int] = 0
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
    # Change 5: Dependent Evidence Grouping
    dependency_group: Optional[str] = None
    is_deleted: Optional[bool] = False
    # Extraction Source Attribution: "live" vs "demo_fixture"
    extraction_mode: Optional[str] = "live"
    is_demo_fixture: Optional[bool] = False
    # Multilingual & OCR Forensic Attributes
    primary_language: Optional[str] = "en"
    is_mixed: Optional[bool] = False
    script: Optional[str] = "latin"
    content_type: Optional[str] = "printed"
    language_source: Optional[str] = "auto_detected"
    text_quality_status: Optional[str] = "unreviewed"
    is_poor_audio: Optional[bool] = False
    current_version_id: Optional[int] = None
    ocr_reading_method: Optional[str] = None
    ocr_confidence: Optional[float] = 1.0
    job_id: Optional[int] = None
    version: Optional[int] = 1
    # Mobile Field Capture Forensics
    is_field_captured: Optional[bool] = False
    capture_source: Optional[str] = "web_upload"
    field_latitude: Optional[float] = None
    field_longitude: Optional[float] = None
    field_accuracy_meters: Optional[float] = None
    field_captured_at: Optional[datetime] = None
    field_device_info: Optional[str] = None
    field_location_name: Optional[str] = None
    field_tamper_seal_number: Optional[str] = None
    field_officer_confirmed: Optional[bool] = False
    field_officer_declaration: Optional[str] = None
    client_computed_hash: Optional[str] = None
    hash_match_verified: Optional[bool] = False

    class Config:
        from_attributes = True

# ---------- ENTITY SCHEMAS ----------
class EntityOut(BaseModel):
    id: int
    case_id: Optional[int] = None
    type: str
    name: str
    confidence: Optional[float] = 0.0
    evidence_id: Optional[int] = None
    source_quote: Optional[str] = None
    source_char_start: Optional[int] = None
    source_char_end: Optional[int] = None
    source_page_number: Optional[int] = None
    is_stale: Optional[bool] = False
    stale_reason: Optional[str] = None

    class Config:
        from_attributes = True

# ---------- EVENT SCHEMAS ----------
class EventOut(BaseModel):
    id: int
    case_id: Optional[int] = None
    timestamp: Optional[datetime] = None
    title: str
    description: str
    location: Optional[str] = None
    confidence: Optional[float] = 0.0
    evidence_id: Optional[int] = None
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
    finding_category: Optional[str] = None
    finding_name: Optional[str] = None

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

    # Change 4: Likelihood Ratio & Grounded Forensic Findings
    finding_category: Optional[str] = None
    finding_name: Optional[str] = None
    likelihood_ratio: Optional[float] = 1.0
    effective_lr: Optional[float] = 1.0
    lr_min: Optional[float] = 1.0
    lr_max: Optional[float] = 1.0
    lr_source_citation: Optional[str] = None
    lr_error_rate: Optional[str] = None
    weight_of_evidence_bans: Optional[float] = 0.0

    # Change 5: Exculpatory First-Class Clearing Factors & Dependent Evidence Grouping
    is_exculpatory: Optional[bool] = False
    clearing_factor_note: Optional[str] = None
    dependency_group: Optional[str] = None
    dependency_weight_multiplier: Optional[float] = 1.0
    damped_likelihood_ratio: Optional[float] = 1.0
    version: Optional[int] = 1

    class Config:
        from_attributes = True

class AssessmentOverrideRequest(BaseModel):
    assessment_id: Optional[int] = None
    hypothesis_id: int
    evidence_id: int
    classification: Optional[str] = None
    finding_category: Optional[str] = None
    evidence_type: Optional[str] = None
    manual_reliability: Optional[float] = None
    hash_verified: Optional[bool] = None
    chain_of_custody_complete: Optional[bool] = None
    sec_65b_certificate_present: Optional[bool] = None
    source_independent: Optional[bool] = None
    quality_rating: Optional[float] = None
    analyst_notes: Optional[str] = "Investigator analytical adjustment"
    version: Optional[int] = None

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

# ---------- CHANGE 4: LIKELIHOOD RATIO REFERENCE SCHEMAS ----------
class LikelihoodRatioReferenceOut(BaseModel):
    id: int
    category_key: str
    evidence_type: str
    finding_name: str
    finding_description: Optional[str] = None
    min_lr: float
    max_lr: float
    typical_lr: float
    support_direction: str
    source_citation: str
    forensic_error_rate: Optional[str] = None
    notes: Optional[str] = None
    is_custom: Optional[bool] = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class LikelihoodRatioReferenceUpdate(BaseModel):
    category_key: str
    min_lr: float
    max_lr: float
    typical_lr: float
    source_citation: Optional[str] = None
    forensic_error_rate: Optional[str] = None
    notes: Optional[str] = None

# ---------- HYPOTHESIS SCHEMAS ----------
class HypothesisCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "Active"
    support_score: Optional[float] = 0.0
    version: Optional[int] = None

class HypothesisOut(BaseModel):
    id: int
    case_id: int
    title: str
    description: Optional[str]
    status: str
    support_score: float
    disconfirmation_penalty: Optional[float] = 0.0
    relative_likelihood: Optional[float] = 0.0
    version: Optional[int] = 1
    
    # Change 1: Three-Layer Output
    evidence_score: Optional[float] = 0.0      # "What the evidence shows"
    background_score: Optional[float] = 0.0    # "Background plausibility"
    combined_score: Optional[float] = 0.0      # "Combined investigative priority"
    
    # Change 4: Probabilistic Likelihood Ratio Updating
    bayesian_lr_score: Optional[float] = 0.0
    bayesian_evidence_score: Optional[float] = 0.0
    classic_ach_score: Optional[float] = 0.0
    classic_evidence_score: Optional[float] = 0.0
    cumulative_lr: Optional[float] = 1.0
    credibility_interval: Optional[List[float]] = None

    background_factors: Optional[Dict[str, Any]] = None
    scoring_inputs: Optional[Dict[str, Any]] = None

    created_at: Optional[datetime]
    assessment_count: Optional[int] = 0
    assessments: Optional[List[EvidenceAssessmentOut]] = []

    # Change 5: Unknown Hypothesis & Open-World Status
    is_unknown: Optional[bool] = False
    lead_message: Optional[str] = None

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

    # Change 1: Three-Layer Output
    evidence_score: Optional[float] = 0.0
    background_score: Optional[float] = 0.0
    combined_score: Optional[float] = 0.0
    
    # Change 4: Probabilistic Likelihood Ratio Updating
    bayesian_lr_score: Optional[float] = 0.0
    bayesian_evidence_score: Optional[float] = 0.0
    classic_ach_score: Optional[float] = 0.0
    classic_evidence_score: Optional[float] = 0.0
    cumulative_lr: Optional[float] = 1.0
    credibility_interval: Optional[List[float]] = None

    background_factors: Optional[Dict[str, Any]] = None
    scoring_inputs: Optional[Dict[str, Any]] = None

    # Change 5: Unknown Hypothesis & Open-World Status
    is_unknown: Optional[bool] = False
    lead_message: Optional[str] = None

    created_at: Optional[datetime]
    assessments: List[EvidenceAssessmentOut] = []

    class Config:
        from_attributes = True

class DependencyGroupUpdateRequest(BaseModel):
    dependency_group: Optional[str] = None
    analyst_notes: Optional[str] = None

class ExculpatoryConfigOut(BaseModel):
    exculpatory_types: List[Dict[str, Any]]

# ============================================================
# CHANGE 2: SUSPECT PROFILE & BACKGROUND CONFIG SCHEMAS
# ============================================================

class SuspectProfileFactorCreate(BaseModel):
    suspect_name: Optional[str] = None
    factor_type: str  # access, opportunity, means, motive, alibi_status, travel_feasibility
    factor_value: str
    numeric_adjustment: Optional[float] = 0.50
    note: Optional[str] = None
    source_evidence_id: Optional[int] = None
    source_exhibit_name: Optional[str] = None
    confidence: Optional[float] = 0.85
    entered_by: Optional[str] = "Analyst"
    is_confirmed: Optional[bool] = True
    version: Optional[int] = None

class SuspectProfileFactorOut(BaseModel):
    id: int
    case_id: int
    hypothesis_id: int
    suspect_name: Optional[str] = None
    factor_type: str
    factor_value: str
    numeric_adjustment: float
    note: Optional[str] = None
    source_evidence_id: Optional[int] = None
    source_exhibit_name: Optional[str] = None
    confidence: float
    entered_by: str
    is_ai_suggested: bool
    is_confirmed: bool
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    effect_on_prior: Optional[str] = None
    created_at: Optional[datetime] = None
    version: Optional[int] = 1

    class Config:
        from_attributes = True

class BackgroundWeightConfigOut(BaseModel):
    id: Optional[int] = None
    case_id: Optional[int] = None
    access_weight: float = 0.25
    opportunity_weight: float = 0.25
    means_weight: float = 0.15
    motive_weight: float = 0.20
    travel_feasibility_weight: float = 0.15
    alibi_strongly_verified_discount: float = 0.10
    alibi_partially_verified_discount: float = 0.50
    alibi_contradicted_multiplier: float = 1.30
    impossible_travel_penalty: float = 0.05
    avoid_double_counting_rule: str
    
    # Change 3: Criminal History Controls & Safeguards
    include_criminal_history: bool = True
    criminal_history_max_cap: float = 0.10
    exclude_juvenile_records: bool = True
    exclude_unverified_identity: bool = True
    # Change 9: Configuration Version-Stamping & Audit Safeguards
    config_version: str = "v1.0.0"
    updated_by: Optional[str] = "Lead Investigator"
    change_rationale: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class BackgroundWeightConfigUpdate(BaseModel):
    access_weight: Optional[float] = None
    opportunity_weight: Optional[float] = None
    means_weight: Optional[float] = None
    motive_weight: Optional[float] = None
    travel_feasibility_weight: Optional[float] = None
    alibi_strongly_verified_discount: Optional[float] = None
    alibi_partially_verified_discount: Optional[float] = None
    alibi_contradicted_multiplier: Optional[float] = None
    impossible_travel_penalty: Optional[float] = None
    include_criminal_history: Optional[bool] = None
    criminal_history_max_cap: Optional[float] = None
    exclude_juvenile_records: Optional[bool] = None
    exclude_unverified_identity: Optional[bool] = None
    min_identity_confidence: Optional[float] = None
    config_version: Optional[str] = None
    updated_by: Optional[str] = None
    change_rationale: Optional[str] = None

class ScoringConfigVersionOut(BaseModel):
    id: int
    case_id: Optional[int] = None
    version_tag: str
    weights_json: str
    caps_json: str
    lr_table_json: Optional[str] = None
    rationale: Optional[str] = None
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# CHANGE 3: PRIOR CRIMINAL HISTORY SCHEMAS
# ============================================================

class PriorRecordCreate(BaseModel):
    suspect_name: str
    hypothesis_id: Optional[int] = None
    person_entity_id: Optional[int] = None
    offense_type: str
    legal_section: Optional[str] = None
    offense_date: Optional[datetime] = None
    location: Optional[str] = None
    outcome: str  # convicted, acquitted, discharged, pending, merely_accused
    weapon_used: Optional[str] = None
    entry_method: Optional[str] = None
    victim_type: Optional[str] = None
    location_type: Optional[str] = None
    time_pattern: Optional[str] = None
    mo_description: Optional[str] = None
    source_agency: str
    source_document: Optional[str] = None
    verification_status: Optional[str] = "verified"
    identity_match_confidence: Optional[float] = 1.0
    verified_identity: Optional[bool] = True
    is_juvenile: Optional[bool] = False
    entered_by: Optional[str] = "Lead Investigator"

class PriorRecordUpdate(BaseModel):
    suspect_name: Optional[str] = None
    hypothesis_id: Optional[int] = None
    person_entity_id: Optional[int] = None
    offense_type: Optional[str] = None
    legal_section: Optional[str] = None
    offense_date: Optional[datetime] = None
    location: Optional[str] = None
    outcome: Optional[str] = None
    weapon_used: Optional[str] = None
    entry_method: Optional[str] = None
    victim_type: Optional[str] = None
    location_type: Optional[str] = None
    time_pattern: Optional[str] = None
    mo_description: Optional[str] = None
    source_agency: Optional[str] = None
    source_document: Optional[str] = None
    verification_status: Optional[str] = None
    identity_match_confidence: Optional[float] = None
    verified_identity: Optional[bool] = None
    is_juvenile: Optional[bool] = None
    version: Optional[int] = None

class PriorRecordOut(BaseModel):
    id: int
    case_id: int
    hypothesis_id: Optional[int] = None
    person_entity_id: Optional[int] = None
    suspect_name: str
    offense_type: str
    legal_section: Optional[str] = None
    offense_date: Optional[datetime] = None
    location: Optional[str] = None
    outcome: str
    weapon_used: Optional[str] = None
    entry_method: Optional[str] = None
    victim_type: Optional[str] = None
    location_type: Optional[str] = None
    time_pattern: Optional[str] = None
    mo_description: Optional[str] = None
    source_agency: str
    source_document: Optional[str] = None
    verification_status: str
    identity_match_confidence: float
    verified_identity: bool
    is_juvenile: bool
    computed_mo_similarity: float
    similarity_breakdown: Optional[str] = None
    quoted_comparison: Optional[str] = None
    effective_weight: float
    history_contribution: float
    entered_by: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: Optional[int] = 1

    class Config:
        from_attributes = True

class CriminalHistoryComparisonHypothesis(BaseModel):
    hypothesis_id: int
    title: str
    rank_with_history: int
    rank_without_history: int
    background_with_history: float
    background_without_history: float
    combined_with_history: float
    combined_without_history: float
    evidence_score: float
    history_contribution_pct: float
    rank_changed: bool

class CriminalHistoryComparisonOut(BaseModel):
    case_id: int
    include_criminal_history: bool
    criminal_history_max_cap: float
    legal_safeguard_notice: str
    total_prior_records: int
    hypotheses_comparison: List[CriminalHistoryComparisonHypothesis]

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
    category: Optional[str] = "investigation"
    impact_score: Optional[float] = None
    suggested_by_ai: Optional[bool] = False
    dismissed: Optional[bool] = False
    version: Optional[int] = None

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
    category: Optional[str] = "investigation"
    impact_score: Optional[float] = None
    suggested_by_ai: Optional[bool] = False
    dismissed: Optional[bool] = False
    created_at: Optional[datetime] = None
    version: Optional[int] = 1

    class Config:
        from_attributes = True

# ---------- CHANGE 6 & 7: MONTE CARLO RANGES, GAPS & NEXT-STEP SCHEMAS ----------
class MonteCarloHypothesisRange(BaseModel):
    hypothesis_id: Union[int, str]
    title: str
    is_unknown: Optional[bool] = False
    median_score: float
    baseline_score: float
    p5_score: float
    p95_score: float
    min_score: float
    max_score: float
    range_spread: float
    std_dev: float
    plain_label: str

class MonteCarloScoringResponse(BaseModel):
    success: bool
    num_simulations: int
    ranges: List[MonteCarloHypothesisRange]
    cannot_separate: bool
    close_results_warning: Optional[str] = None
    discriminating_evidence_needed: List[str] = []
    is_fragile: bool
    fragile_exhibit_id: Optional[Union[int, str]] = None
    fragile_exhibit_title: Optional[str] = None
    fragility_message: Optional[str] = None

class InvestigativeGapOut(BaseModel):
    gap_id: str
    rule_code: str
    rule_title: str
    target_type: str
    target_id: Optional[Union[int, str]] = None
    target_title: Optional[str] = None
    severity: str
    description: str
    recommended_task: str
    action_category: str
    default_assigned_to: str
    priority: str
    existing_task_id: Optional[int] = None
    is_accepted: bool = False
    is_dismissed: bool = False

class NextBestStepOut(BaseModel):
    step_id: str
    action_title: str
    action_type: str
    target_hypothesis_id: Optional[Union[int, str]] = None
    target_hypothesis_title: Optional[str] = None
    expected_impact: float
    can_flip_rank: bool
    max_score_delta: float
    description: str
    simulated_outcomes: List[Dict[str, Any]]
    recommended_priority: str
    suggested_assigned_to: str



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
    is_2fa_enabled: Optional[bool] = False
    session_duration_minutes: Optional[int] = 15

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in_minutes: Optional[int] = 15
    user: Optional[UserOut] = None
    requires_2fa: Optional[bool] = False
    temp_token: Optional[str] = None

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


class JobOut(BaseModel):
    id: int
    case_id: int
    exhibit_id: Optional[int] = None
    user_id: Optional[int] = None
    created_by: Optional[str] = None
    job_type: str
    status: str
    current_stage: str
    progress_pct: float
    attempt_count: int
    max_attempts: int
    error_message: Optional[str] = None
    error_detail: Optional[str] = None
    stage_results: Optional[str] = None
    heartbeat: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    priority: int = 0
    cancel_requested: bool = False
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EvidenceUploadResponse(BaseModel):
    success: bool = True
    job_id: int
    evidence: EvidenceOut
    message: str = "Evidence uploaded into forensic custody. Processing job queued."


# ---------- LIVE COLLABORATION SCHEMAS ----------
class PresenceHeartbeatRequest(BaseModel):
    current_location: str = "Case Overview"
    item_id: Optional[str] = None

class PresenceUserOut(BaseModel):
    user_id: int
    user_name: str
    user_role: str
    current_location: str
    item_id: Optional[str] = None
    last_seen_at: datetime

    class Config:
        from_attributes = True

class EditLockRequest(BaseModel):
    item_type: str  # hypothesis, suspect_profile, assessment, prior_record, evidence, task
    item_id: str
    ttl_seconds: Optional[int] = 120
    reason: Optional[str] = None

class EditLockOut(BaseModel):
    id: int
    case_id: int
    item_type: str
    item_id: str
    user_id: int
    user_name: str
    user_role: str
    acquired_at: datetime
    expires_at: datetime
    is_active: bool = True
    client_token: Optional[str] = None

    class Config:
        from_attributes = True

class CollaborationEventOut(BaseModel):
    id: int
    case_id: int
    event_type: str
    item_type: Optional[str] = None
    item_id: Optional[str] = None
    version: Optional[int] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    summary: str
    payload: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ConflictDetail(BaseModel):
    error: str = "conflict"
    message: str
    item_type: str
    item_id: str
    current_version: int
    modified_by: Optional[str] = None
    current_data: Dict[str, Any]


# ==============================================================================
# ALERTS, STATUTORY DEADLINES & SHIFT HANDOVER SCHEMAS
# ==============================================================================

class AlertOut(BaseModel):
    id: int
    case_id: int
    rule_type: str
    severity: str
    title: str
    message: str
    linked_item_type: Optional[str] = None
    linked_item_id: Optional[str] = None
    status: str
    dedup_key: str
    is_restricted: bool = False
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    snoozed_until: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_reason: Optional[str] = None

    class Config:
        from_attributes = True


class AlertAcknowledgeRequest(BaseModel):
    note: Optional[str] = None


class AlertSnoozeRequest(BaseModel):
    hours: int = 24


class AlertResolveRequest(BaseModel):
    reason: str


class NotificationPreferenceOut(BaseModel):
    id: int
    user_id: int
    rule_type: str
    in_app_enabled: bool
    email_enabled: bool
    digest_mode: str
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None

    class Config:
        from_attributes = True


class NotificationPreferenceUpdate(BaseModel):
    in_app_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    digest_mode: Optional[str] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


class StatutoryDeadlineRuleOut(BaseModel):
    id: int
    statute_name: str
    section_reference: str
    offence_category: str
    limit_days: int
    trigger_event: str
    description: str
    procedure_name: Optional[str] = "Charge Sheet Submission"
    is_reviewed_by_expert: bool = True
    expert_reviewer: Optional[str] = None
    legal_notes: Optional[str] = None

    class Config:
        from_attributes = True


class StatutoryDeadlineRuleUpdate(BaseModel):
    statute_name: Optional[str] = None
    section_reference: Optional[str] = None
    offence_category: Optional[str] = None
    limit_days: Optional[int] = None
    trigger_event: Optional[str] = None
    description: Optional[str] = None
    procedure_name: Optional[str] = None
    is_reviewed_by_expert: Optional[bool] = None
    expert_reviewer: Optional[str] = None
    legal_notes: Optional[str] = None


class OffenceEvidenceProtocolOut(BaseModel):
    id: int
    offence_category: str
    offence_section_keywords: str
    exhibit_code: str
    title: str
    description: str
    mandatory: bool
    legal_provision: str
    matching_keywords: str
    consequence_if_missing: str

    class Config:
        from_attributes = True


class EvidenceChecklistItem(BaseModel):
    exhibit_code: str
    title: str
    description: str
    mandatory: bool
    legal_provision: str
    consequence_if_missing: str
    status: str  # "present" | "missing"
    matched_evidence_id: Optional[int] = None
    matched_file_name: Optional[str] = None
    matched_at: Optional[datetime] = None


class EvidenceChecklistResponse(BaseModel):
    case_id: int
    offence_section: Optional[str] = None
    offence_category: str
    total_expected: int
    mandatory_expected: int
    present_count: int
    missing_count: int
    mandatory_missing_count: int
    compliance_percentage: float
    items: List[EvidenceChecklistItem]
    warnings: List[str]


class CaseDeadlineOut(BaseModel):
    id: int
    case_id: int
    statute_rule_id: Optional[int] = None
    title: str
    due_date: datetime
    status: str
    satisfied_at: Optional[datetime] = None
    satisfied_by: Optional[str] = None
    extended_until: Optional[datetime] = None
    extension_reason: Optional[str] = None
    days_remaining: int
    is_overdue: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class CaseDeadlineUpdateRequest(BaseModel):
    status: Optional[str] = None
    extended_until: Optional[datetime] = None
    extension_reason: Optional[str] = None
    satisfied: Optional[bool] = None


class HandoverGenerateRequest(BaseModel):
    period_hours: Optional[int] = 24
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    generation_type: Optional[str] = "manual"


class HandoverSummaryOut(BaseModel):
    id: int
    case_id: int
    period_start: datetime
    period_end: datetime
    headline: str
    structured_content: Dict[str, Any]
    rendered_text: str
    generated_by: str
    generation_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class SinceYouWereAwayOut(BaseModel):
    case_id: int
    last_seen_at: datetime
    headline: str
    hours_away: float
    new_evidence_count: int
    changed_hypotheses_count: int
    overrides_count: int
    open_tasks_count: int
    unresolved_alerts_count: int
    recent_active_users: List[str]
    summary_points: List[str]


# ==============================================================================
# CHARGESHEET & DOCKET ASSISTANT SCHEMAS
# ==============================================================================

class ChargesheetDraftOut(BaseModel):
    id: int
    case_id: int
    title: str
    court_name: str
    police_station: str
    fir_number: Optional[str] = None
    offence_section: Optional[str] = None
    investigating_officer: Optional[str] = None
    status: str
    legal_review_status: str
    is_draft: bool
    version: int
    facts_narrative: str
    evidence_inventory: Any
    witness_statements: Any
    forensic_findings: Any
    analysis_and_charges: str
    source_citations: Any
    legal_disclaimer: str
    created_by: str
    last_edited_by: Optional[str] = None
    last_edit_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChargesheetUpdateRequest(BaseModel):
    section_edited: Optional[str] = "general"
    edit_summary: Optional[str] = "Investigator updated chargesheet"
    title: Optional[str] = None
    court_name: Optional[str] = None
    police_station: Optional[str] = None
    fir_number: Optional[str] = None
    offence_section: Optional[str] = None
    investigating_officer: Optional[str] = None
    status: Optional[str] = None
    legal_review_status: Optional[str] = None
    facts_narrative: Optional[str] = None
    evidence_inventory: Optional[Any] = None
    witness_statements: Optional[Any] = None
    forensic_findings: Optional[Any] = None
    analysis_and_charges: Optional[str] = None


class ChargesheetEditLogOut(BaseModel):
    id: int
    chargesheet_id: int
    case_id: int
    version: int
    section_edited: str
    edit_summary: str
    edited_by_user_id: Optional[int] = None
    edited_by_name: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChargesheetAssistantPromptRequest(BaseModel):
    section_name: str
    instruction: str


# ==============================================================================
# INTERVIEWS & DEPOSITION SCHEMAS
# ==============================================================================

class InterviewStatementCreateRequest(BaseModel):
    speaker: Optional[str] = None
    role: Optional[str] = "interviewee"
    timestamp_marker: Optional[str] = "00:00"
    seconds: Optional[int] = 0
    question: Optional[str] = None
    question_source_type: Optional[str] = None
    question_source_id: Optional[str] = None
    text: str
    tag: Optional[str] = None


class InterviewContradictionOut(BaseModel):
    id: int
    interview_id: int
    statement_id: int
    case_id: int
    quote_new: str
    source_new: str
    quote_prior: str
    source_prior: str
    prior_statement_id: Optional[int] = None
    prior_evidence_id: Optional[int] = None
    conflict_type: str
    reasoning: str
    confidence: float
    severity: str
    created_at: datetime

    class Config:
        from_attributes = True


class InterviewStatementOut(BaseModel):
    id: int
    interview_id: int
    case_id: int
    sequence_order: int
    speaker: str
    role: str
    timestamp_marker: str
    seconds: int
    question: Optional[str] = None
    question_source_type: Optional[str] = None
    question_source_id: Optional[str] = None
    text: str
    tag: Optional[str] = None
    is_contradiction_flag: bool
    created_at: datetime
    contradictions: Optional[List[InterviewContradictionOut]] = []

    class Config:
        from_attributes = True


class InterviewCreateRequest(BaseModel):
    interviewee_name: str
    interviewee_role: Optional[str] = "suspect"
    interviewer_name: str
    interview_date: Optional[str] = None
    duration: Optional[str] = "00:00 mins"
    status: Optional[str] = "Active"
    notes: Optional[str] = None


class InterviewOut(BaseModel):
    id: int
    case_id: int
    session_code: str
    interviewee_name: str
    interviewee_role: str
    interviewer_name: str
    interview_date: Optional[str] = None
    duration: str
    status: str
    audio_url: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    statement_count: Optional[int] = 0
    contradiction_count: Optional[int] = 0

    class Config:
        from_attributes = True


class InterviewDetailOut(InterviewOut):
    statements: List[InterviewStatementOut] = []
    contradictions: List[InterviewContradictionOut] = []


class SuggestedQuestionOut(BaseModel):
    id: str
    category: str
    category_label: str
    title: str
    question: str
    rationale: str
    quote_a: Optional[str] = None
    quote_b: Optional[str] = None
    source_a: Optional[str] = None
    source_b: Optional[str] = None
    severity: str
    is_subject_specific: bool
    source_id: Optional[str] = None


class StatementAnalysisResponse(BaseModel):
    statement: InterviewStatementOut
    has_contradiction: bool
    new_contradictions: List[InterviewContradictionOut] = []


# ==============================================================================
# CROSS-CASE INTELLIGENCE & ENTITY RESOLUTION SCHEMAS
# ==============================================================================

class CrossCaseEntityDetailOut(BaseModel):
    id: Optional[int] = None
    name: str
    type: str


class CrossCaseEntityLinkOut(BaseModel):
    id: int
    case_id: int
    linked_case_id: int
    linked_case_title: str
    entity_type: str
    match_type: str
    match_value: str
    similarity_score: float
    status: str
    confidence_reason: str
    source_entity: CrossCaseEntityDetailOut
    linked_entity: CrossCaseEntityDetailOut
    reviewed_by_user_id: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[str] = None
    reviewer_notes: Optional[str] = None
    created_at: Optional[str] = None


class CrossCaseLinkReviewRequest(BaseModel):
    status: str  # confirmed, rejected, pending_review
    notes: Optional[str] = None


class CrossCaseMOSimilarCaseOut(BaseModel):
    case_id: int
    title: str
    fir_number: str
    status: str
    offence_section: str
    similarity_score: float
    similarity_percentage: float
    matched_features: List[str] = []
    field_scores: Dict[str, float] = {}
    description_snippet: str = ""


class CrossCaseIntelligenceSummaryOut(BaseModel):
    case_id: int
    total_links: int
    pending_links: int
    confirmed_links: int
    rejected_links: int
    links: List[CrossCaseEntityLinkOut] = []
    similar_cases: List[CrossCaseMOSimilarCaseOut] = []


class MatchingFeatureDetail(BaseModel):
    link_id: int
    entity_type: str
    match_type: str
    match_value: str
    similarity_score: float
    confidence_reason: str
    status: str


class ConnectedCaseGroupOut(BaseModel):
    linked_case_id: int
    linked_case_title: str
    status: str  # pending_review, confirmed, rejected
    has_pending_review: bool
    highest_similarity_score: float
    feature_types: List[str] = []
    matching_features: List[MatchingFeatureDetail] = []


class ConnectedCasesSummaryOut(BaseModel):
    case_id: int
    total_connected_cases: int
    pending_candidates_count: int
    confirmed_connections_count: int
    connected_cases: List[ConnectedCaseGroupOut] = []


# ==============================================================================
# CDR & FINANCIAL ANALYTICS SCHEMAS
# ==============================================================================

class CDRRecordOut(BaseModel):
    id: int
    case_id: int
    evidence_id: Optional[int] = None
    source_file_name: str
    row_number: int
    calling_number: str
    called_number: Optional[str] = None
    call_datetime: datetime
    call_duration_sec: int
    call_type: str
    imei: Optional[str] = None
    imsi: Optional[str] = None
    cell_id: str
    azimuth: Optional[float] = None
    site_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    class Config:
        from_attributes = True


class BankTransactionOut(BaseModel):
    id: int
    case_id: int
    evidence_id: Optional[int] = None
    source_file_name: str
    row_number: int
    transaction_date: datetime
    value_date: Optional[datetime] = None
    description: str
    reference_number: Optional[str] = None
    debit_amount: float
    credit_amount: float
    balance: Optional[float] = None
    account_number: str
    counterparty_account: Optional[str] = None
    counterparty_name: Optional[str] = None
    bank_name: Optional[str] = None
    transaction_mode: str

    class Config:
        from_attributes = True


class CoLocationEventOut(BaseModel):
    event_id: str
    cell_id: str
    site_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    time_delta_seconds: int
    time_delta_minutes: float
    confidence: float
    phone_a: Dict[str, Any]
    phone_b: Dict[str, Any]
    reasoning: str


class CommonContactOut(BaseModel):
    contact_number: str
    suspects_connected_count: int
    suspects_connected: List[str]
    total_calls: int
    total_duration_sec: int
    first_contact: str
    last_contact: str
    breakdown: List[Dict[str, Any]]
    all_linked_rows: List[Dict[str, Any]]
    risk_rating: str


class ShortLivedNumberOut(BaseModel):
    phone_number: str
    total_events: int
    first_seen: str
    last_seen: str
    active_duration_hours: float
    unique_towers_count: int
    towers: List[str]
    imeis: List[str]
    linked_rows: List[Dict[str, Any]]
    indicator: str
    reasoning: str


class ImpossibleTravelOut(BaseModel):
    phone_number: str
    calculated_speed_kmh: float
    distance_km: float
    time_delta_minutes: float
    event_a: Dict[str, Any]
    event_b: Dict[str, Any]
    reasoning: str


class CDRAnalyticsOverviewOut(BaseModel):
    case_id: int
    total_records: int
    unique_callers: int
    unique_towers: int
    co_location_events: List[CoLocationEventOut] = []
    common_contacts: List[CommonContactOut] = []
    short_lived_numbers: List[ShortLivedNumberOut] = []
    impossible_travel: List[ImpossibleTravelOut] = []
    records_sample: List[CDRRecordOut] = []


class MoneyFlowAnalysisOut(BaseModel):
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    total_transactions: int
    total_volume: float
    structuring_alerts: List[Dict[str, Any]] = []
    layering_alerts: List[Dict[str, Any]] = []


# ==============================================================================
# MULTILINGUAL EVIDENCE & VERSIONING SCHEMAS
# ==============================================================================

class LanguageProfileConfigOut(BaseModel):
    id: int
    language: str
    script: str
    content_type: str
    reading_method: str
    fallback_method: Optional[str] = None
    stt_model_hint: Optional[str] = None
    preprocessing_steps: str
    confidence_threshold: float
    translate_by_default: bool
    default_target_language: str
    created_at: datetime

    class Config:
        from_attributes = True


class LanguageProfileConfigUpdate(BaseModel):
    reading_method: Optional[str] = None
    fallback_method: Optional[str] = None
    stt_model_hint: Optional[str] = None
    preprocessing_steps: Optional[str] = None
    confidence_threshold: Optional[float] = None
    translate_by_default: Optional[bool] = None
    default_target_language: Optional[str] = None


class ExhibitSegmentOut(BaseModel):
    id: int
    evidence_id: int
    version_id: int
    case_id: int
    segment_index: int
    page_number: Optional[int] = None
    bbox_json: Optional[str] = None
    start_time_sec: Optional[float] = None
    end_time_sec: Optional[float] = None
    speaker_label: Optional[str] = None
    raw_text: str
    normalized_text: str
    confidence: float
    is_low_confidence: bool
    status: str
    reading_method: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ExhibitTextVersionOut(BaseModel):
    id: int
    evidence_id: int
    case_id: int
    version_number: int
    raw_text: str
    normalized_text: str
    reading_method: str
    overall_confidence: float
    status: str
    is_current: bool
    created_by: str
    created_at: datetime
    edit_reason: Optional[str] = None
    diff_summary: Optional[str] = None
    requires_second_signoff: bool = False
    second_signoff_by: Optional[str] = None
    second_signoff_at: Optional[datetime] = None
    is_reverted: bool = False
    reverted_from_version: Optional[int] = None
    segments: List[ExhibitSegmentOut] = []

    class Config:
        from_attributes = True


class ExhibitTextCorrectionRequest(BaseModel):
    new_text: str
    edit_reason: str
    requires_second_signoff: Optional[bool] = False


class TranslationSegmentOut(BaseModel):
    id: int
    translation_id: int
    source_segment_id: Optional[int] = None
    source_text_snippet: str
    translated_text: str
    alignment_confidence: float
    proper_names_json: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ExhibitTranslationOut(BaseModel):
    id: int
    evidence_id: int
    version_id: int
    source_language: str
    target_language: str
    author_type: str
    author_name: str
    model_used: Optional[str] = None
    review_status: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    full_translated_text: str
    created_at: datetime
    aligned_segments: List[TranslationSegmentOut] = []

    class Config:
        from_attributes = True


class TranslationCreateRequest(BaseModel):
    target_language: Optional[str] = "en"
    author_type: Optional[str] = "certified_human"
    author_name: str
    translated_text: str


class DualCitationOut(BaseModel):
    citation_id: int
    evidence_id: int
    file_name: str
    primary_language: str
    original_quote: str
    location_tag: str
    page_number: Optional[int] = None
    timestamp_sec: Optional[float] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    translated_quote: Optional[str] = None
    translation_label: Optional[str] = None
    is_verified: bool = True
    is_stale: bool = False
    viewer_link: str


class MultilingualProfileResponse(BaseModel):
    evidence_id: int
    file_name: str
    file_type: str
    primary_language: str
    is_mixed: bool
    script: str
    content_type: str
    language_source: str
    text_quality_status: str
    is_poor_audio: bool
    ocr_reading_method: Optional[str] = None
    ocr_confidence: float
    current_version: Optional[ExhibitTextVersionOut] = None
    versions_count: int
    versions: List[ExhibitTextVersionOut] = []
    translations: List[ExhibitTranslationOut] = []
    dual_citations: List[DualCitationOut] = []
    reliability_assessment: Dict[str, Any] = {}


# ==============================================================================
# DECISION QUALITY SCHEMAS
# ==============================================================================

class DecisionSignoffOut(BaseModel):
    id: int
    case_id: int
    item_type: str
    item_id: int
    item_summary: str
    maker_user_id: Optional[int] = None
    maker_name: str
    checker_user_id: Optional[int] = None
    checker_name: Optional[str] = None
    checker_role: Optional[str] = None
    status: str
    review_notes: Optional[str] = None
    requested_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DecisionSignoffRequest(BaseModel):
    item_type: str
    item_id: int
    item_summary: str


class DecisionSignoffReviewRequest(BaseModel):
    approved: bool
    review_notes: str


class DevilsAdvocateResponse(BaseModel):
    success: bool
    case_id: Optional[int] = None
    message: Optional[str] = None
    leading_hypothesis: Optional[Dict[str, Any]] = None
    counter_hypothesis: Optional[Dict[str, Any]] = None
    prob_gap: Optional[float] = 0.0
    required_shift_to_overtake: Optional[float] = 0.0
    counter_corroborating_points: List[Dict[str, Any]] = []
    lead_vulnerabilities: List[Dict[str, Any]] = []
    suppression_simulation: Optional[Dict[str, Any]] = None
    legal_challenge_brief: Optional[Dict[str, Any]] = None


class PlainLanguageExplanationResponse(BaseModel):
    hypothesis_id: int
    rank: int
    score_pct: float
    verdict: str
    summary: str
    primary_drivers: List[str] = []
    vulnerabilities_and_doubts: List[str] = []
    recommended_action: str


# ==============================================================================
# PRIVATE MODEL, 2FA, SESSIONS, LEGAL HOLD & BACKUP SCHEMAS
# ==============================================================================

class TwoFactorSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str
    backup_codes: List[str]


class TwoFactorVerifyRequest(BaseModel):
    code: str
    secret: Optional[str] = None


class TwoFactorChallengeRequest(BaseModel):
    temp_token: str
    code: str


class TwoFactorDisableRequest(BaseModel):
    password: str
    code: Optional[str] = None


class UserSessionOut(BaseModel):
    id: int
    device_info: str
    ip_address: str
    user_agent: Optional[str] = None
    created_at: datetime
    last_active_at: datetime
    expires_at: datetime
    is_current: bool = False
    is_revoked: bool = False

    class Config:
        from_attributes = True


class SystemSecurityConfigOut(BaseModel):
    default_ai_provider: str
    local_model_endpoint: str
    local_model_name: str
    allow_external_ai_global: bool
    default_session_duration_minutes: int
    require_2fa_for_admins: bool
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None

    class Config:
        from_attributes = True


class SystemSecurityConfigUpdate(BaseModel):
    default_ai_provider: Optional[str] = None
    local_model_endpoint: Optional[str] = None
    local_model_name: Optional[str] = None
    allow_external_ai_global: Optional[bool] = None
    default_session_duration_minutes: Optional[int] = None
    require_2fa_for_admins: Optional[bool] = None


class BackupRecordOut(BaseModel):
    id: int
    backup_filename: str
    backup_type: str
    size_bytes: int
    sha256_hash: str
    created_at: datetime
    created_by: str
    restore_test_status: str
    restore_test_at: Optional[datetime] = None
    restore_test_notes: Optional[str] = None

    class Config:
        from_attributes = True


class CaseLegalHoldRequest(BaseModel):
    is_legal_hold: bool
    reason: Optional[str] = None


class CaseRetentionUpdate(BaseModel):
    retention_period_years: int


class CaseAirGapToggleRequest(BaseModel):
    is_sensitive_airgapped: bool
    ai_provider_override: Optional[str] = None
    local_ai_endpoint: Optional[str] = None
    local_ai_model: Optional[str] = None


# ==============================================================================
# VALIDATION 2.0: BLIND INDEPENDENT BENCHMARK & REGRESSION SCHEMAS
# ==============================================================================

class IndependentAuthorOut(BaseModel):
    id: str
    name: str
    title: str
    institution: str
    specialization: str
    case_contributed: str


class DomainReviewerOut(BaseModel):
    id: str
    name: str
    role_category: str
    credential: str
    focus: str


class FrozenSuiteInfoOut(BaseModel):
    suite_version: str
    name: str
    description: str
    is_frozen: bool
    checksum_sha256: str
    total_cases: int
    authors: List[IndependentAuthorOut]
    domain_reviewers: List[DomainReviewerOut]


class BlindCaseOut(BaseModel):
    id: str
    title: str
    author_id: str
    author_name: str
    jurisdiction: str
    category: str
    summary: str
    hypotheses: List[Dict[str, Any]]
    exhibits: List[Dict[str, Any]]
    is_blinded: bool
    ground_truth_sealed_hash: str
    reviewer_ratings: Optional[Dict[str, Any]] = None


class ValidationV2RunRequest(BaseModel):
    runs: Optional[int] = 3
    custom_base_configs: Optional[Dict[str, float]] = None


class ValidationRegressionCheckRequest(BaseModel):
    custom_base_configs: Optional[Dict[str, float]] = None


# ==============================================================================
# LIVE DATA CONNECTORS SCHEMAS
# ==============================================================================

class DataConnectorCreate(BaseModel):
    name: str
    connector_type: str  # folder_watch, email_inbox, api_pull, webhook
    source_identifier: str  # local path, email address, API URL, or webhook label
    config_json: Optional[str] = "{}"
    is_active: Optional[bool] = True


class DataConnectorUpdate(BaseModel):
    name: Optional[str] = None
    source_identifier: Optional[str] = None
    config_json: Optional[str] = None
    is_active: Optional[bool] = None


class DataConnectorOut(BaseModel):
    id: int
    case_id: int
    name: str
    connector_type: str
    source_identifier: str
    config_json: Optional[str] = "{}"
    webhook_token: Optional[str] = None
    webhook_url: Optional[str] = None
    is_active: bool
    status: str
    last_polled_at: Optional[datetime] = None
    last_ingest_at: Optional[datetime] = None
    items_ingested_count: int = 0
    error_message: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConnectorIngestRecordOut(BaseModel):
    id: int
    connector_id: int
    case_id: int
    evidence_id: Optional[int] = None
    source_system: str
    source_filename: str
    file_hash: str
    file_size: Optional[int] = 0
    receipt_time: datetime
    status: str
    error_message: Optional[str] = None
    details_json: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConnectorPollResponse(BaseModel):
    success: bool
    connector_id: int
    connector_name: str
    items_fetched: int
    items_ingested: int
    duplicates_skipped: int
    errors_count: int
    message: str
    ingested_evidence_ids: List[int] = []


class ConnectorSimulateDropRequest(BaseModel):
    sample_type: Optional[str] = "cdr_export"  # cdr_export, lab_toxicology, bank_statement, cctv_metadata, whistleblower_email
    custom_filename: Optional[str] = None
    custom_content: Optional[str] = None


# ============================================================
# WATCHLIST SCHEMAS
# ============================================================

class WatchlistCreate(BaseModel):
    entity_type: str = Field(..., description="Target type: phone, account, vehicle, or person")
    entity_value: str = Field(..., description="Target identifier (e.g. phone number, bank account, plate)")
    label: str = Field(..., description="Descriptive label e.g. 'Prime Suspect Burner Phone'")
    priority: Optional[str] = "critical"
    case_id: Optional[int] = None
    notes: Optional[str] = None


class WatchlistUpdate(BaseModel):
    label: Optional[str] = None
    priority: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class WatchlistOut(BaseModel):
    id: int
    created_by_user_id: int
    created_by_name: Optional[str] = None
    case_id: Optional[int] = None
    entity_type: str
    entity_value: str
    label: str
    priority: str
    is_active: bool
    notes: Optional[str] = None
    match_count: int
    last_matched_at: Optional[datetime] = None
    last_matched_case_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LiveNetworkNode(BaseModel):
    id: str
    label: str
    type: str  # 'phone', 'account', 'person', 'tower'
    degree: int
    total_volume: float
    total_calls: int
    is_watchlist_match: bool
    details: Optional[Dict[str, Any]] = None


class LiveNetworkEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str  # 'call', 'transfer'
    count: int
    total_amount: float
    last_timestamp: Optional[str] = None
    modes: List[str] = []
    linked_rows: List[Dict[str, Any]] = []


class LiveNetworkResponse(BaseModel):
    case_id: int
    case_title: str
    nodes: List[LiveNetworkNode]
    edges: List[LiveNetworkEdge]
    total_nodes: int
    total_edges: int
    total_calls: int
    total_transfers_amount: float
    watchlist_matches_in_network: int
    filters_applied: Dict[str, Any]
    timestamp: str


# ==============================================================================
# QUICK VOICE NOTES & CITATION SCHEMAS
# ==============================================================================

class VoiceNoteCreateRequest(BaseModel):
    note_text: str
    category: Optional[str] = "field_observation"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy_meters: Optional[float] = None
    location_name: Optional[str] = None
    recorded_at: Optional[str] = None
    tags: Optional[List[str]] = []
    source_device: Optional[str] = "Mobile Field Unit"


class VoiceNoteCitationOut(BaseModel):
    citation_id: int
    citation_code: str
    chunk_id: int
    char_start: int
    char_end: int
    quote: str


class VoiceNoteOut(BaseModel):
    id: int
    case_id: int
    evidence_id: int
    citation_code: str
    note_text: str
    category: str
    officer_name: str
    officer_role: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_name: Optional[str] = None
    recorded_at: str
    audio_path: Optional[str] = None
    file_hash: str
    citations: List[VoiceNoteCitationOut] = []
    created_at: datetime

    class Config:
        from_attributes = True


# ==============================================================================
# LIVE INTERVIEW STREAMING SCHEMAS
# ==============================================================================

class LiveInterviewChunkRequest(BaseModel):
    transcript_text: str
    speaker: Optional[str] = None
    role: Optional[str] = "interviewee"
    timestamp_marker: Optional[str] = "00:00"
    seconds: Optional[int] = 0
    question: Optional[str] = None
    question_source_type: Optional[str] = None
    question_source_id: Optional[str] = None
    is_live_stream: Optional[bool] = True


# ==============================================================================
# SYSTEM HEALTH & STATUS SCHEMAS
# ==============================================================================

class AIServiceStatusOut(BaseModel):
    service_name: str
    provider: str
    status: str  # 'available', 'degraded', 'offline', 'disabled', 'unconfigured'
    latency_ms: Optional[int] = None
    endpoint_or_model: Optional[str] = None
    notes: Optional[str] = None


class BackupHealthOut(BaseModel):
    last_backup_id: Optional[int] = None
    last_backup_at: Optional[datetime] = None
    seconds_since_last_backup: Optional[int] = None
    time_since_backup_human: str
    backup_status: str  # 'up_to_date', 'due', 'overdue', 'no_backup'
    last_backup_filename: Optional[str] = None
    last_backup_hash: Optional[str] = None
    last_backup_type: Optional[str] = None
    restore_test_status: str  # 'passed', 'failed', 'untested'
    restore_test_notes: Optional[str] = None


class QueueHealthOut(BaseModel):
    pending_jobs_count: int
    running_jobs_count: int
    total_active_queue: int
    oldest_queued_job_seconds: Optional[int] = None
    queue_status: str  # 'healthy', 'busy', 'congested', 'idle'


class JobSuccessHealthOut(BaseModel):
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    running_jobs: int
    success_rate_pct: float
    failed_last_24h_count: int
    recent_jobs: List[Dict[str, Any]] = []


class SystemHealthOut(BaseModel):
    system_status: str  # 'operational', 'degraded', 'critical'
    timestamp: datetime
    uptime_seconds: int
    db_size_mb: float
    queue: QueueHealthOut
    job_success: JobSuccessHealthOut
    ai_services: List[AIServiceStatusOut]
    backup: BackupHealthOut


# ==============================================================================
# EXHIBIT DATA QUALITY SCHEMAS (WEAKEST ITEMS FIRST)
# ==============================================================================

class ExhibitQualityPillars(BaseModel):
    text_confidence_score: float  # 0 to 25
    text_confidence_pct: float  # 0 to 100
    text_status: str  # 'high', 'medium', 'low', 'unextracted', 'poor_audio'
    text_notes: str

    hash_score: float  # 0 or 25
    hash_status: str  # 'verified', 'unverified', 'mismatch'
    hash_value: Optional[str] = None

    certificate_score: float  # 0 or 25
    certificate_status: str  # 'certified', 'missing', 'pending'
    certificate_notes: str

    language_review_score: float  # 0 to 25
    language_status: str  # 'verified', 'pending_review', 'untranslated', 'native_english'
    primary_language: str
    language_notes: str


class ExhibitDataQualityItemOut(BaseModel):
    evidence_id: int
    case_id: int
    title: str
    file_name: str
    file_type: str
    evidence_type: str
    uploaded_by: str
    upload_date: Optional[datetime] = None
    overall_quality_score: float  # 0.0 to 100.0
    quality_tier: str  # 'Critical Attention Needed', 'Weak Quality', 'Adequate', 'Judicially Sound'
    is_weak_item: bool
    pillars: ExhibitQualityPillars
    warning_flags: List[str] = []
    recommended_action: str


class CaseDataQualityReportOut(BaseModel):
    case_id: int
    case_title: str
    total_exhibits: int
    average_quality_score: float
    weak_exhibits_count: int
    missing_certificates_count: int
    unverified_hashes_count: int
    low_confidence_text_count: int
    pending_language_reviews_count: int
    sorted_exhibits: List[ExhibitDataQualityItemOut]


# ==============================================================================
# COMMAND PALETTE & GLOBAL OMNI-SEARCH SCHEMAS
# ==============================================================================

class OmniSearchResultItemOut(BaseModel):
    id: str
    category: str  # 'exhibit', 'entity', 'claim', 'quote', 'suspect', 'task', 'alert', 'command'
    title: str
    match_source: str
    matched_snippet: str
    highlight_term: str
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    page_number: Optional[int] = None
    target_url: str
    metadata: Dict[str, Any] = {}

class OmniSearchResponseOut(BaseModel):
    query: str
    case_id: Optional[int] = None
    total_matches: int
    matches: List[OmniSearchResultItemOut]


# ==============================================================================
# TODAY'S PRIORITIES & OPERATIONAL DASHBOARD SCHEMAS
# ==============================================================================

class ReportRequestCreate(BaseModel):
    report_type: str
    requested_from: str
    expected_date: datetime
    requested_date: Optional[datetime] = None
    urgency: Optional[str] = "high"
    notes: Optional[str] = None

class ReportRequestUpdate(BaseModel):
    status: Optional[str] = None  # requested, received, overdue, not_needed
    received_date: Optional[datetime] = None
    linked_evidence_id: Optional[int] = None
    notes: Optional[str] = None

class ReportRequestOut(BaseModel):
    id: int
    case_id: int
    report_type: str
    requested_from: str
    requested_date: datetime
    expected_date: datetime
    received_date: Optional[datetime] = None
    status: str
    linked_evidence_id: Optional[int] = None
    reminder_date: Optional[datetime] = None
    urgency: str
    days_waiting: int = 0
    is_overdue: bool = False
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PersonRegisterCreate(BaseModel):
    name: str
    role: str = "witness"
    contact_info: Optional[str] = None
    linked_entity_id: Optional[int] = None
    is_important: Optional[bool] = False
    notes: Optional[str] = None

class PersonRegisterOut(BaseModel):
    id: int
    case_id: int
    name: str
    role: str
    contact_info: Optional[str] = None
    linked_entity_id: Optional[int] = None
    is_important: bool = False
    mention_count: int = 1
    notes: Optional[str] = None
    statement_status: Optional[str] = "not_contacted"
    statement_type: Optional[str] = "section_161_police"
    statement_id: Optional[int] = None
    scheduled_date: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class StatementTrackerCreate(BaseModel):
    person_id: int
    statement_type: str = "section_161_police"
    status: str = "not_contacted"
    scheduled_date: Optional[datetime] = None
    notes: Optional[str] = None

class StatementTrackerUpdate(BaseModel):
    status: Optional[str] = None
    recorded_date: Optional[datetime] = None
    linked_evidence_id: Optional[int] = None
    linked_interview_id: Optional[int] = None
    summary: Optional[str] = None
    key_claims: Optional[str] = None
    notes: Optional[str] = None

class StatementTrackerOut(BaseModel):
    id: int
    case_id: int
    person_id: int
    person_name: Optional[str] = None
    person_role: Optional[str] = None
    statement_type: str
    status: str
    scheduled_date: Optional[datetime] = None
    recorded_date: Optional[datetime] = None
    linked_evidence_id: Optional[int] = None
    linked_interview_id: Optional[int] = None
    summary: Optional[str] = None
    key_claims: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ActionItemOut(BaseModel):
    id: str
    type: str  # deadline, report, witness, review, alert
    title: str
    reason: str
    due_time: Optional[str] = None
    severity: str  # overdue, critical, urgent, watch, calm
    days_left: Optional[int] = None
    owner: Optional[str] = None
    action_link: str
    action_label: str
    status: str = "pending"
    snoozed_until: Optional[str] = None

class StatutoryClockOut(BaseModel):
    has_dates: bool
    chargesheet_limit_days: int
    arrest_date: Optional[str] = None
    remand_date: Optional[str] = None
    chargesheet_deadline: Optional[str] = None
    chargesheet_days_left: Optional[int] = None
    chargesheet_hours_left: Optional[int] = None
    chargesheet_band: str  # overdue, critical, urgent, watch, calm, missing_dates
    chargesheet_legal_note: str
    remand_deadline: Optional[str] = None
    remand_days_left: Optional[int] = None
    remand_hours_left: Optional[int] = None
    remand_band: str
    remand_legal_note: str
    statutory_provision: str = "Section 187(3) BNSS / Section 167(2) CrPC"
    extensions: List[Dict[str, Any]] = []

class SinceYouWereAwayOut(BaseModel):
    headline: str
    summary_sentence: Optional[str] = ""
    hours_away: float
    new_evidence_count: int
    changed_hypotheses_count: int
    unresolved_alerts_count: int
    open_tasks_count: int
    summary_points: List[str] = []

class PendingReportsSectionOut(BaseModel):
    total_requested: int
    received_count: int
    overdue_count: int
    pending_count: int
    items: List[ReportRequestOut]
    unrequested_protocol_exhibits: List[Dict[str, Any]] = []

class WitnessesSectionOut(BaseModel):
    total_people: int
    examined_count: int
    unexamined_count: int
    items: List[PersonRegisterOut]
    ai_suggested_persons: List[Dict[str, Any]] = []

class NeedsYourReviewItemOut(BaseModel):
    id: str
    type: str  # contradiction, data_quality, low_confidence_ocr, unverified_citation, signoff
    title: str
    reason: str
    impact_score: float
    severity: str
    action_link: str
    action_label: str

class NeedsYourReviewSectionOut(BaseModel):
    total_items: int
    items: List[NeedsYourReviewItemOut]

class CaseSnapshotOut(BaseModel):
    exhibits_count: int
    entities_count: int
    hypotheses_count: int
    timeline_events_count: int
    top_hypothesis: Optional[Dict[str, Any]] = None

class PrioritiesResponseOut(BaseModel):
    case_id: int
    case_title: str
    fir_number: str
    cached: bool = False
    updated_at: str
    since_you_were_away: SinceYouWereAwayOut
    statutory_clock: StatutoryClockOut
    action_items: List[ActionItemOut]
    pending_reports: PendingReportsSectionOut
    witnesses_and_statements: WitnessesSectionOut
    needs_your_review: NeedsYourReviewSectionOut
    case_snapshot: CaseSnapshotOut
















# ==============================================================================
# POLICE-SHAPED CASE FILE ARCHITECTURE SCHEMAS
# ==============================================================================

class CaseParticularsUpdate(BaseModel):
    crime_number: Optional[str] = None
    police_station: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    investigating_officer_id: Optional[int] = None
    investigating_officer_name: Optional[str] = None
    supervising_officer_id: Optional[int] = None
    supervising_officer_name: Optional[str] = None
    court_name: Optional[str] = None
    next_hearing_date: Optional[datetime] = None
    next_hearing_purpose: Optional[str] = None
    bail_status: Optional[str] = None
    custody_status: Optional[str] = None
    case_stage: Optional[str] = None
    expected_version: Optional[int] = None

class PoliceStationLookupOut(BaseModel):
    id: int
    name: str
    station_code: Optional[str] = None
    district: str
    state: str
    contact_number: Optional[str] = None
    sp_office: Optional[str] = None

    class Config:
        from_attributes = True

class CasePersonCreate(BaseModel):
    name: str
    aliases: Optional[str] = None
    role: str = "witness"  # complainant, victim, accused, witness, expert, informant, panch_witness, other
    father_or_spouse_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    contact_info: Optional[str] = None
    address: Optional[str] = None
    is_important: Optional[bool] = False
    linked_entity_id: Optional[int] = None
    notes: Optional[str] = None

class CasePersonUpdate(BaseModel):
    name: Optional[str] = None
    aliases: Optional[str] = None
    role: Optional[str] = None
    father_or_spouse_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    contact_info: Optional[str] = None
    address: Optional[str] = None
    is_important: Optional[bool] = None
    linked_entity_id: Optional[int] = None
    notes: Optional[str] = None

class CasePersonOut(BaseModel):
    id: int
    case_id: int
    name: str
    aliases: Optional[str] = None
    role: str
    father_or_spouse_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    contact_info: Optional[str] = None
    address: Optional[str] = None
    is_important: bool = False
    linked_entity_id: Optional[int] = None
    notes: Optional[str] = None
    statements_count: int = 0
    latest_status: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AccusedStatusHistoryCreate(BaseModel):
    person_id: int
    status: str  # not_identified, absconding, arrested, police_custody, judicial_custody, bailed, anticipatory_bail, chargesheeted
    status_date: datetime
    order_reference: Optional[str] = None
    custody_days_served: Optional[int] = 0
    remand_expiry_date: Optional[datetime] = None
    statutory_filing_deadline: Optional[datetime] = None
    notes: Optional[str] = None

class AccusedStatusHistoryOut(BaseModel):
    id: int
    case_id: int
    person_id: int
    person_name: Optional[str] = None
    status: str
    status_date: datetime
    order_reference: Optional[str] = None
    custody_days_served: int = 0
    remand_expiry_date: Optional[datetime] = None
    statutory_filing_deadline: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PersonStatementCreate(BaseModel):
    person_id: int
    statement_type: str = "section_180_bnss_police"  # section_180_bnss_police, section_183_bnss_magistrate, dying_declaration, confession, other
    status: str = "recorded"  # not_contacted, summoned, examined, recorded, refused
    statement_date: datetime
    statement_time: Optional[str] = None
    place: Optional[str] = None
    recorded_by: Optional[str] = None
    language: Optional[str] = "Marathi"
    read_over_and_signed: Optional[bool] = True
    magistrate_name: Optional[str] = None
    linked_evidence_id: Optional[int] = None
    linked_interview_id: Optional[int] = None
    statement_text: Optional[str] = None
    key_claims: Optional[str] = None
    notes: Optional[str] = None

class PersonStatementOut(BaseModel):
    id: int
    case_id: int
    person_id: int
    person_name: Optional[str] = None
    statement_type: str
    status: str
    statement_date: datetime
    statement_time: Optional[str] = None
    place: Optional[str] = None
    recorded_by: Optional[str] = None
    language: Optional[str] = None
    read_over_and_signed: bool = True
    magistrate_name: Optional[str] = None
    linked_evidence_id: Optional[int] = None
    linked_interview_id: Optional[int] = None
    statement_text: Optional[str] = None
    key_claims: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DocumentTypeDefinitionOut(BaseModel):
    id: int
    code: str
    label: str
    legal_provision: str
    category: str
    required_fields: List[Dict[str, Any]] = []
    standard_guidance: Optional[str] = None

class TypedDocumentUpdate(BaseModel):
    document_type: str
    type_details: Dict[str, Any]

class DocumentGapReportOut(BaseModel):
    evidence_id: int
    file_name: str
    document_type: str
    completeness_pct: float
    is_complete: bool
    missing_required_fields: List[Dict[str, Any]] = []
    gap_reasons: List[str] = []
    legal_guidance: Optional[str] = None

class CaseDiaryEntryCreate(BaseModel):
    entry_date: date
    serial_number: Optional[int] = 1
    time_from: Optional[str] = "09:30"
    time_to: Optional[str] = "18:30"
    place: Optional[str] = "Police Station"
    officer_name: str
    activities: str
    persons_examined_json: Optional[str] = "[]"
    places_visited_json: Optional[str] = "[]"
    items_seized_json: Optional[str] = "[]"
    instructions_given: Optional[str] = None
    next_steps: Optional[str] = None
    status: Optional[str] = "draft"
    parent_entry_id: Optional[int] = None

class CaseDiaryEntryUpdate(BaseModel):
    time_from: Optional[str] = None
    time_to: Optional[str] = None
    place: Optional[str] = None
    activities: Optional[str] = None
    persons_examined_json: Optional[str] = None
    places_visited_json: Optional[str] = None
    items_seized_json: Optional[str] = None
    instructions_given: Optional[str] = None
    next_steps: Optional[str] = None
    supervisor_notes: Optional[str] = None

class CaseDiaryEntryOut(BaseModel):
    id: int
    case_id: int
    entry_date: date
    serial_number: int
    time_from: Optional[str] = None
    time_to: Optional[str] = None
    place: Optional[str] = None
    officer_id: Optional[int] = None
    officer_name: str
    activities: str
    persons_examined: List[Dict[str, Any]] = []
    places_visited: List[str] = []
    items_seized: List[Dict[str, Any]] = []
    instructions_given: Optional[str] = None
    next_steps: Optional[str] = None
    status: str
    signature_timestamp: Optional[datetime] = None
    signature_hash: Optional[str] = None
    supervisor_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CaseSectionCreate(BaseModel):
    act: str = "BNS"  # BNS, IPC, Special Law, POCSO, NDPS
    section_code: str
    description: str
    punishment_tier: Optional[str] = "life_or_death_over_10_years"
    status: Optional[str] = "initial"  # initial, proposed_add, added, proposed_drop, dropped
    reason: Optional[str] = None
    deciding_officer: Optional[str] = None
    court_informed_date: Optional[datetime] = None
    court_intimation_memo: Optional[str] = None

class CaseSectionUpdate(BaseModel):
    status: Optional[str] = None
    reason: Optional[str] = None
    supervisor_approval: Optional[bool] = None
    supervisor_notes: Optional[str] = None
    court_informed_date: Optional[datetime] = None
    court_intimation_memo: Optional[str] = None

class SectionElementOut(BaseModel):
    id: int
    case_section_id: int
    element_text: str
    supporting_evidence_ids: List[int] = []
    status: str
    notes: Optional[str] = None

    class Config:
        from_attributes = True

class CaseSectionOut(BaseModel):
    id: int
    case_id: int
    act: str
    section_code: str
    description: str
    punishment_tier: str
    status: str
    reason: Optional[str] = None
    deciding_officer: Optional[str] = None
    effective_date: Optional[datetime] = None
    supervisor_approval: bool = True
    supervisor_notes: Optional[str] = None
    court_informed_date: Optional[datetime] = None
    court_intimation_memo: Optional[str] = None
    elements: List[SectionElementOut] = []
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class FIRImportRequest(BaseModel):
    fir_text: str
    auto_save: Optional[bool] = False

class FIRImportResponseOut(BaseModel):
    fir_number: Optional[str] = None
    police_station: Optional[str] = None
    district: Optional[str] = None
    incident_date: Optional[str] = None
    fir_date: Optional[str] = None
    complainant_name: Optional[str] = None
    accused_names: List[str] = []
    sections: List[str] = []
    brief_facts: Optional[str] = None


# ==============================================================================
# PHYSICAL EVIDENCE, EXTENDED CUSTODY, SEALS, MALKHANA & FSL SCHEMAS
# ==============================================================================

class PhysicalItemCreate(BaseModel):
    category: str
    description: str
    identifying_marks: Optional[str] = None
    quantity_or_weight: Optional[str] = None
    condition: str = "intact"
    packaging: str = "sealed_plastic_bag"
    seized_from: Optional[str] = None
    seized_at: Optional[str] = None
    seized_by_name: Optional[str] = None
    seizure_memo_id: Optional[int] = None
    panch_witness_1_id: Optional[int] = None
    panch_witness_2_id: Optional[int] = None
    current_location: str = "malkhana"
    current_custodian: Optional[str] = None
    malkhana_entry_number: Optional[str] = None
    rack_or_shelf: Optional[str] = None
    is_perishable: bool = False
    is_biological: bool = False
    is_firearm: bool = False
    is_narcotics: bool = False
    dispatch_time_limit_days: Optional[int] = None


class PhysicalItemOut(BaseModel):
    id: int
    evidence_id: int
    case_id: int
    category: str
    description: str
    identifying_marks: Optional[str] = None
    quantity_or_weight: Optional[str] = None
    condition: str
    packaging: str
    seized_from: Optional[str] = None
    seized_at: Optional[str] = None
    seized_by_id: Optional[int] = None
    seized_by_name: Optional[str] = None
    seizure_memo_id: Optional[int] = None
    panch_witness_1_id: Optional[int] = None
    panch_witness_2_id: Optional[int] = None
    current_location: str
    current_custodian: Optional[str] = None
    malkhana_entry_number: Optional[str] = None
    rack_or_shelf: Optional[str] = None
    status: str
    is_perishable: bool = False
    is_biological: bool = False
    is_firearm: bool = False
    is_narcotics: bool = False
    dispatch_time_limit_days: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CustodyHandoverRequest(BaseModel):
    action: str  # SEIZED, SEALED, MALKHANA_IN, MALKHANA_OUT, SENT_TO_FSL, RECEIVED_FROM_FSL, PRODUCED_IN_COURT, RETURNED, DISPOSED, TRANSFER
    from_person_id: Optional[int] = None
    from_person_name: Optional[str] = None
    from_location: Optional[str] = None
    to_person_id: Optional[int] = None
    to_person_name: str
    to_location: str
    purpose: Optional[str] = "Custody Transfer"
    condition_at_handover: Optional[str] = "intact"
    seal_status_check: Optional[str] = "intact"
    expected_return_date: Optional[datetime] = None
    authority_order_ref: Optional[str] = None
    acknowledgement_type: Optional[str] = "digital_pin"
    acknowledgement_data: Optional[str] = None
    attached_photos: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None


class CustodyLogExtendedOut(BaseModel):
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
    from_person_id: Optional[int] = None
    from_person_name: Optional[str] = None
    from_location: Optional[str] = None
    to_person_id: Optional[int] = None
    to_person_name: Optional[str] = None
    to_location: Optional[str] = None
    purpose: Optional[str] = None
    condition_at_handover: Optional[str] = None
    seal_status_check: Optional[str] = None
    expected_return_date: Optional[datetime] = None
    authority_order_ref: Optional[str] = None
    acknowledgement_type: Optional[str] = None
    acknowledgement_data: Optional[str] = None
    attached_photos: Optional[str] = None
    previous_log_hash: Optional[str] = None
    current_log_hash: Optional[str] = None

    class Config:
        from_attributes = True


class ContinuityCheckOut(BaseModel):
    evidence_id: int
    evidence_kind: str
    status: str  # complete, gap, seal_issue
    chain_of_custody_complete: bool
    hash_chain_valid: bool
    reliability_penalty: float
    total_custody_entries: int
    issues: List[Dict[str, Any]]
    last_action: Optional[str] = None
    last_timestamp: Optional[str] = None
    current_custodian: Optional[str] = None
    current_location: Optional[str] = None


class SealCreateRequest(BaseModel):
    seal_number: str
    owner_mark: str
    package_description: Optional[str] = "Tamper-evident envelope"
    applied_in_presence_of: Optional[List[str]] = []
    photos: Optional[List[Dict[str, Any]]] = None


class SealOut(BaseModel):
    id: int
    case_id: int
    evidence_id: int
    seal_number: str
    owner_mark: str
    package_description: Optional[str] = None
    applied_by_name: str
    applied_at: datetime
    status: str
    replaced_seal_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SealEventCreateRequest(BaseModel):
    event_type: str  # inspect, break, reseal
    reason: str
    witnesses: Optional[List[str]] = []
    photos: Optional[List[Dict[str, Any]]] = None
    new_seal_data: Optional[Dict[str, Any]] = None


class SealEventOut(BaseModel):
    id: int
    seal_id: int
    event_type: str
    timestamp: datetime
    actor_name: str
    witnesses: Optional[str] = None
    reason: Optional[str] = None
    new_seal_id: Optional[int] = None
    photos: Optional[str] = None

    class Config:
        from_attributes = True


class MalkhanaDepositRequest(BaseModel):
    malkhana_entry_number: str
    rack_or_shelf: str
    depositor_name: str
    condition: str = "intact"
    seal_status: str = "intact"
    photos: Optional[List[Dict[str, Any]]] = None


class MalkhanaIssueRequest(BaseModel):
    purpose: str
    destination_location: str
    taken_by_name: str
    approver_id: int
    expected_return_date: Optional[datetime] = None
    authority_order_ref: Optional[str] = None
    seal_check: str = "intact"
    notes: Optional[str] = None


class MalkhanaRegisterItemOut(BaseModel):
    id: int
    evidence_id: int
    case_id: int
    crime_number: str
    case_title: str
    category: str
    description: str
    identifying_marks: Optional[str] = None
    quantity_or_weight: Optional[str] = None
    condition: str
    packaging: str
    current_location: str
    current_custodian: Optional[str] = None
    malkhana_entry_number: Optional[str] = None
    rack_or_shelf: Optional[str] = None
    status: str
    seal_number: Optional[str] = None
    seal_status: str
    is_biological: bool = False
    is_perishable: bool = False
    is_firearm: bool = False
    is_narcotics: bool = False
    created_at: Optional[str] = None


class MalkhanaStockCheckCreate(BaseModel):
    police_station: str
    total_items_expected: int
    items_verified_present: int
    discrepancies_count: int
    discrepancies_details: Optional[str] = None
    supervisor_notes: Optional[str] = None


class MalkhanaStockCheckOut(BaseModel):
    id: int
    police_station: str
    check_date: datetime
    conducted_by_name: str
    total_items_expected: int
    items_verified_present: int
    discrepancies_count: int
    discrepancies_details: Optional[str] = None
    status: str
    supervisor_notes: Optional[str] = None

    class Config:
        from_attributes = True


class FSLDispatchCreateRequest(BaseModel):
    forwarding_letter_number: str
    forwarding_letter_date: datetime
    fsl_name: str
    examination_requested: str
    carried_by_name: str
    carried_by_role: Optional[str] = "Police Constable"
    carried_by_id_card: Optional[str] = "PC-4412"
    mode_of_transit: str = "police_messenger"
    expected_report_date: Optional[datetime] = None
    item_evidence_ids: List[int]


class FSLDispatchItemOut(BaseModel):
    id: int
    dispatch_id: int
    evidence_id: int
    seal_number_at_dispatch: str
    seal_status_at_dispatch: str
    return_seal_number: Optional[str] = None
    return_seal_status: Optional[str] = None
    condition_on_return: Optional[str] = None

    class Config:
        from_attributes = True


class FSLDispatchOut(BaseModel):
    id: int
    case_id: int
    forwarding_letter_number: str
    forwarding_letter_date: datetime
    fsl_name: str
    examination_requested: str
    sent_date: datetime
    carried_by_name: str
    carried_by_role: Optional[str] = None
    carried_by_id_card: Optional[str] = None
    mode_of_transit: str
    expected_report_date: Optional[datetime] = None
    status: str
    lab_acknowledgement_receipt_path: Optional[str] = None
    lab_acknowledgement_date: Optional[datetime] = None
    report_evidence_id: Optional[int] = None
    return_date: Optional[datetime] = None
    return_carried_by: Optional[str] = None
    items: List[FSLDispatchItemOut] = []

    class Config:
        from_attributes = True


class FSLReturnRequest(BaseModel):
    return_date: datetime
    carried_by: str
    item_returns: List[Dict[str, Any]]


class OCRSealCompareRequest(BaseModel):
    claimed_seal: str
    ocr_detected_text: str


class OCRSealCompareOut(BaseModel):
    match: bool
    confidence: float
    status: str
    claimed: Optional[str] = None
    detected: Optional[str] = None


# ==============================================================================
# ALIBI VERIFICATION WORKFLOW SCHEMAS
# ==============================================================================

class AlibiSegmentCreate(BaseModel):
    segment_order: int = 1
    start_time: datetime
    end_time: datetime
    time_uncertainty_mins: int = 15
    claimed_place_name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_meters: float = 500.0
    activity: Optional[str] = None
    travel_mode: str = "none"
    vouching_persons: Optional[str] = None
    notes: Optional[str] = None


class AlibiSegmentOut(BaseModel):
    id: int
    claim_id: int
    segment_order: int
    start_time: datetime
    end_time: datetime
    time_uncertainty_mins: int
    claimed_place_name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_meters: float
    activity: Optional[str] = None
    travel_mode: str
    vouching_persons: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AlibiCheckCreate(BaseModel):
    segment_id: Optional[int] = None
    source_type: str
    requirement_details: str
    legal_process_required: bool = False
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    due_date: Optional[datetime] = None


class AlibiCheckUpdate(BaseModel):
    status: Optional[str] = None
    result: Optional[str] = None
    unlocatable_reason: Optional[str] = None
    supporting_evidence_ids: Optional[str] = None
    supporting_citations: Optional[str] = None
    clock_offset_seconds: Optional[int] = None
    explanation: Optional[str] = None


class AlibiCheckOut(BaseModel):
    id: int
    claim_id: int
    segment_id: Optional[int] = None
    source_type: str
    requirement_details: str
    legal_process_required: bool
    investigation_task_id: Optional[int] = None
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    due_date: Optional[datetime] = None
    status: str
    result: str
    unlocatable_reason: Optional[str] = None
    supporting_evidence_ids: Optional[str] = None
    supporting_citations: Optional[str] = None
    clock_offset_seconds: int
    explanation: Optional[str] = None
    is_system_suggested: bool
    verified_by_id: Optional[int] = None
    verified_by_name: Optional[str] = None
    verified_at: Optional[datetime] = None
    retention_warning_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StatementComparisonOut(BaseModel):
    id: int
    claim_id: int
    statement_id: Optional[int] = None
    line_number: int
    statement_text: str
    quote_citation: Optional[str] = None
    extracted_facts: Optional[str] = None
    result: str
    matched_evidence_ids: Optional[str] = None
    reasoning: Optional[str] = None
    review_state: str
    reviewed_by_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class StatementComparisonReviewRequest(BaseModel):
    result: str
    reasoning: Optional[str] = None
    review_state: str = "confirmed"


class AlibiClaimCreate(BaseModel):
    person_id: Optional[int] = None
    suspect_name: str
    hypothesis_id: Optional[int] = None
    claim_text: str
    source_statement_id: Optional[int] = None
    source_citation: Optional[str] = None
    raised_at: Optional[datetime] = None
    segments: List[AlibiSegmentCreate] = []


class AlibiVerdictRequest(BaseModel):
    final_verdict: str
    verdict_reason: str


class AlibiClaimOut(BaseModel):
    id: int
    case_id: int
    person_id: Optional[int] = None
    suspect_name: str
    hypothesis_id: Optional[int] = None
    claim_text: str
    source_statement_id: Optional[int] = None
    source_citation: Optional[str] = None
    version: int
    raised_at: Optional[datetime] = None
    status: str
    final_verdict: Optional[str] = None
    verdict_reason: Optional[str] = None
    verdict_by_name: Optional[str] = None
    verdict_at: Optional[datetime] = None
    is_current: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    segments_count: Optional[int] = 0
    checks_count: Optional[int] = 0

    class Config:
        from_attributes = True


class AlibiClaimDetailOut(AlibiClaimOut):
    segments: List[AlibiSegmentOut] = []
    checks: List[AlibiCheckOut] = []
    comparisons: List[StatementComparisonOut] = []
    coverage_report: Optional[Dict[str, Any]] = None
    travel_feasibility_reports: Optional[List[Dict[str, Any]]] = None



# ============================================================
# MULTILINGUAL INTAKE & LEGAL GLOSSARY SCHEMAS
# ============================================================

class LegalTermCreate(BaseModel):
    term_en: str
    term_hi: str
    term_mr: str
    plain_explanation_en: str
    plain_explanation_hi: Optional[str] = None
    plain_explanation_mr: Optional[str] = None
    legal_provision_new: Optional[str] = None
    legal_provision_old: Optional[str] = None
    category: str = "general"
    is_verified: bool = True
    verified_by: Optional[str] = "Special Legal Advisor"


class LegalTermUpdate(BaseModel):
    term_en: Optional[str] = None
    term_hi: Optional[str] = None
    term_mr: Optional[str] = None
    plain_explanation_en: Optional[str] = None
    plain_explanation_hi: Optional[str] = None
    plain_explanation_mr: Optional[str] = None
    legal_provision_new: Optional[str] = None
    legal_provision_old: Optional[str] = None
    category: Optional[str] = None
    is_verified: Optional[bool] = None


class LegalTermOut(BaseModel):
    id: int
    term_en: str
    term_hi: str
    term_mr: str
    plain_explanation_en: str
    plain_explanation_hi: Optional[str] = None
    plain_explanation_mr: Optional[str] = None
    legal_provision_new: Optional[str] = None
    legal_provision_old: Optional[str] = None
    category: str
    is_verified: bool
    verified_by: Optional[str] = None
    version: int
    created_at: datetime

    class Config:
        from_attributes = True


class PersonAliasCreate(BaseModel):
    canonical_name: str
    alias_name: str
    script: str = "devanagari"
    person_id: Optional[int] = None
    source_exhibit_id: Optional[int] = None


class PersonAliasOut(BaseModel):
    id: int
    case_id: int
    person_id: Optional[int] = None
    canonical_name: str
    alias_name: str
    script: str
    phonetic_key: str
    source_exhibit_id: Optional[int] = None
    confirmed_by: Optional[str] = None
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class IntakeFieldProposal(BaseModel):
    field_key: str
    field_label: str
    field_group: str # people, dates, amounts, places, vehicles, sections
    value: Any
    confidence: float
    confidence_tier: str # high, check, low
    source_quote: Optional[str] = None
    source_bbox: Optional[Dict[str, Any]] = None
    source_timestamp_sec: Optional[float] = None
    alternative_readings: Optional[List[str]] = []
    is_ambiguous: Optional[bool] = False
    ambiguity_reason: Optional[str] = None


class IntakeItemCreate(BaseModel):
    channel: str # fir_copy, handwritten_statement, voice_note, whatsapp_export, field_photo
    title: str
    raw_text: Optional[str] = None
    detected_language: Optional[str] = "mr"
    detected_script: Optional[str] = "devanagari"


class IntakeItemOut(BaseModel):
    id: int
    case_id: int
    channel: str
    title: str
    original_file_name: Optional[str] = None
    storage_path: Optional[str] = None
    file_hash: Optional[str] = None
    file_size_bytes: int
    mime_type: Optional[str] = None
    detected_language: str
    detected_script: str
    status: str
    confidence_score: float
    proposed_fields: List[Dict[str, Any]] = []
    raw_text: Optional[str] = None
    submitter_name: str
    submitter_role: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    applied_entities_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class FieldConfirmationItem(BaseModel):
    field_key: str
    field_group: str
    action: str = "confirm" # confirm, edit, reject
    confirmed_value: Optional[Any] = None
    correction_notes: Optional[str] = None


class IntakeConfirmationRequest(BaseModel):
    confirmations: List[FieldConfirmationItem] = []
    apply_to_case_file: bool = True
    apply_to_people_register: bool = True
    apply_to_case_diary: bool = True
    create_exhibit_record: bool = True


class IntakeRejectRequest(BaseModel):
    reason: str


class IntakeTrustMetricsOut(BaseModel):
    total_processed_items: int
    total_fields_extracted: int
    total_confirmed_unchanged: int
    total_edited_by_officer: int
    total_rejected_fields: int
    acceptance_rate_pct: float
    by_channel: Dict[str, Any] = {}
    by_language: Dict[str, Any] = {}
    headline_stat: str


class TransliterateRequest(BaseModel):
    text: str
    source_script: str = "latin" # latin or devanagari
    target_script: str = "devanagari" # devanagari or latin
    max_suggestions: int = 5


class TransliterateResponse(BaseModel):
    input_text: str
    suggestions: List[str]
    phonetic_key: str


class NameMatchCandidate(BaseModel):
    person_id: Optional[int] = None
    canonical_name: str
    matched_alias: str
    script: str
    similarity_score: float
    confidence_tier: str
    phonetic_match: bool
    matching_reasons: List[str]
    coincidental_signals: Dict[str, Any]


class NameDisambiguationResponse(BaseModel):
    queried_name: str
    phonetic_key: str
    candidates: List[NameMatchCandidate]
    exact_match_found: bool


# ==============================================================================
# STATION OFFLINE SYNC & NOTIFICATION SCHEMAS
# ==============================================================================

class OutboxSyncItem(BaseModel):
    idempotency_key: str
    action: str  # field_capture, draft_diary, create_note, create_task, statement_draft, malkhana_scan
    endpoint: str
    method: str
    payload: Dict[str, Any]
    device_timestamp: datetime
    base_version: Optional[int] = 1


class BulkSyncRequest(BaseModel):
    operations: List[OutboxSyncItem] = []


class BulkSyncResponse(BaseModel):
    applied_count: int
    skipped_duplicates_count: int
    failed_count: int
    applied_keys: List[str]
    errors: List[Dict[str, Any]] = []
    server_timestamp: datetime


class OfflineBundleResponse(BaseModel):
    id: int
    case_number: str
    title: str
    police_station: str
    investigating_officer: str
    incident_date: Optional[str] = None
    particulars: Dict[str, Any] = {}
    people: List[Dict[str, Any]] = []
    tasks: List[Dict[str, Any]] = []
    deadlines: List[Dict[str, Any]] = []
    diary_entries: List[Dict[str, Any]] = []
    exhibits: List[Dict[str, Any]] = []
    hypotheses: List[Dict[str, Any]] = []
    alerts: List[Dict[str, Any]] = []
    downloaded_at: datetime
    is_pinned: bool = False

