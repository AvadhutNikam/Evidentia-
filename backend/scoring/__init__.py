"""
backend/scoring/__init__.py
Modular Scientific Forensic Scoring Engine for Evidentia AI.
Submodules:
- evidence_scoring: ACH matrix calculation, diagnosticity, exculpatory clearing
- background: M.O. similarity, suspect prior records, demographic insulation
- bayesian: Bayesian LR multiplication, 3-layer synthesis, hypothesis normalization
- sensitivity: Leave-One-Out (LOO) robustness and Monte Carlo perturbations
- gaps: Investigative blind spot detection and next-best-evidence simulations
- history: Historical score versioning, deltas, and audit snapshotting
"""

from config import (
    DEFAULT_BASE_RELIABILITY,
    CLASSIFICATION_CONFIG,
    LIKELIHOOD_RATIO_REFERENCE_TABLE,
    EXCULPATORY_EVIDENCE_TYPES_CONFIG,
    UNKNOWN_HYPOTHESIS_TITLE,
    DEFAULT_UNKNOWN_PRIOR,
    DEFAULT_DEPENDENCY_DAMPING_FACTORS,
    DEFAULT_SCORING_TOLERANCE,
    CHANGE2_FACTOR_NUMERICS,
    AVOID_DOUBLE_COUNTING_RULE,
    CRIMINAL_HISTORY_SAFEGUARD_NOTICE,
    METHOD_DIMENSION_WEIGHTS
)

from scoring.evidence_scoring import (
    evaluate_assessment_clearing_status,
    resolve_exhibit_dependency_multipliers,
    cluster_breakdown_rows_by_dependency,
    map_legacy_classification_to_finding,
    shrink_likelihood_ratio,
    resolve_assessment_likelihood_ratio,
    resolve_exhibit_reliability,
    compute_exhibit_diagnosticity,
    compute_evidence_scores
)

from scoring.background import (
    check_travel_feasibility,
    _compute_dimension_match,
    _get_val,
    compute_mo_similarity,
    calculate_record_effective_weight,
    compute_background_scores,
    generate_ai_suspect_profile_suggestions
)

from scoring.bayesian import (
    combine_scores_bayesian,
    compute_bayesian_lr_scoring,
    calculate_three_layer_ach_scoring,
    calculate_ach_scoring
)

from scoring.sensitivity import (
    calculate_sensitivity_and_robustness,
    compute_monte_carlo_scoring_ranges
)

from scoring.gaps import (
    detect_investigative_gaps,
    simulate_next_best_steps
)

from scoring.history import (
    capture_scoring_snapshot,
    compute_score_deltas
)

__all__ = [
    "DEFAULT_BASE_RELIABILITY",
    "CLASSIFICATION_CONFIG",
    "LIKELIHOOD_RATIO_REFERENCE_TABLE",
    "EXCULPATORY_EVIDENCE_TYPES_CONFIG",
    "UNKNOWN_HYPOTHESIS_TITLE",
    "DEFAULT_UNKNOWN_PRIOR",
    "DEFAULT_DEPENDENCY_DAMPING_FACTORS",
    "DEFAULT_SCORING_TOLERANCE",
    "CHANGE2_FACTOR_NUMERICS",
    "AVOID_DOUBLE_COUNTING_RULE",
    "CRIMINAL_HISTORY_SAFEGUARD_NOTICE",
    "METHOD_DIMENSION_WEIGHTS",
    "evaluate_assessment_clearing_status",
    "resolve_exhibit_dependency_multipliers",
    "cluster_breakdown_rows_by_dependency",
    "map_legacy_classification_to_finding",
    "shrink_likelihood_ratio",
    "resolve_assessment_likelihood_ratio",
    "resolve_exhibit_reliability",
    "compute_exhibit_diagnosticity",
    "compute_evidence_scores",
    "check_travel_feasibility",
    "_compute_dimension_match",
    "_get_val",
    "compute_mo_similarity",
    "calculate_record_effective_weight",
    "compute_background_scores",
    "generate_ai_suspect_profile_suggestions",
    "combine_scores_bayesian",
    "compute_bayesian_lr_scoring",
    "calculate_three_layer_ach_scoring",
    "calculate_ach_scoring",
    "calculate_sensitivity_and_robustness",
    "compute_monte_carlo_scoring_ranges",
    "detect_investigative_gaps",
    "simulate_next_best_steps",
    "capture_scoring_snapshot",
    "compute_score_deltas"
]
