export interface Case {
  id: string;
  name: string;
  title?: string;
  description: string;
  status: 'New' | 'Active' | 'Under Investigation' | 'Pending Review' | 'Closed' | 'Archived' | string;
  priority: 'High' | 'Medium' | 'Low' | string;
  createdDate: string;
  lastUpdated: string;
  evidenceCount: number;
  assignedInvestigators: string[];
  case_type?: string;
  location?: string;
  victim?: string;
  key_details?: string;
  incident_date?: string;
  created_at?: string;
  created_by?: string;
  is_demo?: boolean;
  fir_number?: string;
  fir_date?: string;
  arrest_date?: string;
  remand_date?: string;
  offence_section?: string;
  statutory_time_limit_days?: number;
  is_sensitive_airgapped?: boolean;
  ai_provider_override?: string | null;
  local_ai_endpoint?: string | null;
  local_ai_model?: string | null;
  retention_period_years?: number;
  retention_expiry_date?: string | null;
  is_legal_hold?: boolean;
  legal_hold_reason?: string | null;
  legal_hold_placed_by?: string | null;
  legal_hold_placed_at?: string | null;
}

export interface Evidence {
  id: string;
  fileName: string;
  fileType: string;
  caseId: string;
  uploadedBy: string;
  uploadDate: string;
  processingStatus: 'Uploaded' | 'Queued' | 'Processing' | 'Analyzed' | 'Failed' | string;
  source: string;
  tags: string[];
  file_name?: string;
  file_type?: string;
  file_size?: number;
  case_id?: string | number;
  uploaded_by?: string;
  upload_date?: string;
  processing_status?: 'Uploaded' | 'Queued' | 'Processing' | 'Analyzed' | 'Failed' | string;
  extracted_text?: string;
  evidence_kind?: 'digital' | 'physical';
  evidence_type?: string;
  file_hash?: string;
  hash_verified?: boolean;
  chain_of_custody_complete?: boolean;
  sec_65b_certificate_present?: boolean;
  source_independent?: boolean;
  quality_rating?: number;
  collected_by?: string;
  collection_date?: string;
  custody_notes?: string;
  is_deleted?: boolean;
  dependency_group?: string;
  description?: string;
  is_exculpatory?: boolean;
  clearing_factor_note?: string;
  extraction_mode?: 'live' | 'demo_fixture' | string;
  is_demo_fixture?: boolean;
  job_id?: number | string;
  jobId?: number | string;
  current_stage?: string;
  progress_pct?: number;
  version?: number;
  primary_language?: string;
  is_mixed?: boolean;
  script?: string;
  content_type?: string;
  language_source?: string;
  text_quality_status?: string;
  is_poor_audio?: boolean;
  current_version_id?: number;
  ocr_reading_method?: string;
  ocr_confidence?: number;
  is_field_captured?: boolean;
  capture_source?: 'web_upload' | 'field_mobile' | 'api_import' | string;
  field_latitude?: number | null;
  field_longitude?: number | null;
  field_accuracy_meters?: number | null;
  field_captured_at?: string | null;
  field_device_info?: string | null;
  field_location_name?: string | null;
  field_tamper_seal_number?: string | null;
  field_officer_confirmed?: boolean;
  field_officer_declaration?: string | null;
  client_computed_hash?: string | null;
  hash_match_verified?: boolean;
}

export interface Entity {
  id: string;
  caseId: string;
  type: 'Person' | 'Organization' | 'Location' | 'Vehicle' | 'Event' | 'Other';
  name: string;
  aliases: string[];
  sourceEvidenceIds: string[];
  confidence: number;
  source_quote?: string;
  source_char_start?: number;
  source_char_end?: number;
  source_page_number?: number;
}

export interface TimelineEvent {
  id: string;
  caseId: string;
  timestamp: string;
  title: string;
  description: string;
  sourceEvidenceId?: string;
  relatedEntityIds?: string[];
  entitiesInvolved?: string[];
  location?: string;
  confidence?: number;
  source_quote?: string;
  source_char_start?: number;
  source_char_end?: number;
  source_page_number?: number;
}


export interface Contradiction {
  id: string;
  caseId: string;
  statementA: string;
  sourceAId: string;
  statementB: string;
  sourceBId: string;
  conflictType: string;
  confidence: number;
  status: 'Detected' | 'Under Review' | 'Resolved' | 'Dismissed';
}

export type AssessmentClassificationType =
  | 'strong_support'
  | 'moderate_support'
  | 'weak_support'
  | 'neutral'
  | 'weak_contradiction'
  | 'moderate_contradiction'
  | 'strong_contradiction';

export interface EvidenceAssessment {
  id: string | number;
  hypothesis_id?: number;
  hypothesisId?: string | number;
  evidence_id: number;
  evidenceId?: string | number;
  classification: AssessmentClassificationType | string;
  original_classification?: string;
  originalClassification?: string;
  analyst_override?: boolean;
  analystOverride?: boolean;
  analyst_notes?: string;
  analystNotes?: string;
  second_signoff_status?: 'not_required' | 'pending_signoff' | 'approved' | 'rejected' | string;
  second_signoff_by_id?: number;
  second_signoff_by_name?: string;
  second_signoff_at?: string;
  second_signoff_notes?: string;
  is_key_classification?: boolean;
  diagnosticity_weight?: number;
  diagnosticityWeight?: number;
  diagnosticity_category?: 'High' | 'Medium' | 'Low' | string;
  diagnosticityCategory?: 'High' | 'Medium' | 'Low' | string;
  reason?: string;
  llm_confidence?: number;
  llmConfidence?: number;
  reliability?: number;
  quoted_source_line?: string;
  quotedSourceLine?: string;
  computed_reliability?: number;
  computedReliability?: number;
  computed_diagnosticity?: number;
  computedDiagnosticity?: number;
  final_contribution?: number;
  finalContribution?: number;
  evidence_file_name?: string;
  evidenceFileName?: string;
  evidence_file_type?: string;
  evidenceFileType?: string;
  evidence_type?: string;
  evidenceType?: string;
  finding_category?: string;
  findingCategory?: string;
  finding_name?: string;
  findingName?: string;
  likelihood_ratio?: number;
  likelihoodRatio?: number;
  effective_lr?: number;
  effectiveLr?: number;
  lr_min?: number;
  lrMin?: number;
  lr_max?: number;
  lrMax?: number;
  lr_source_citation?: string;
  lrSourceCitation?: string;
  lr_error_rate?: string;
  lrErrorRate?: string;
  weight_of_evidence_bans?: number;
  weightOfEvidenceBans?: number;
  dependency_group?: string;
  is_exculpatory?: boolean;
  clearing_factor_note?: string;
  dependency_weight_multiplier?: number;
  damped_likelihood_ratio?: number;
  version?: number;
}

export interface Hypothesis {
  id: string;
  caseId: string;
  case_id?: number;
  title: string;
  description: string;
  status: 'Active' | 'Discarded' | 'Proven' | string;
  confidence: number;
  support_score?: number;
  evidence_score?: number;
  evidenceScore?: number;
  background_score?: number;
  backgroundScore?: number;
  combined_score?: number;
  combinedScore?: number;
  bayesian_lr_score?: number;
  bayesianLrScore?: number;
  bayesian_evidence_score?: number;
  bayesianEvidenceScore?: number;
  classic_ach_score?: number;
  classicAchScore?: number;
  classic_evidence_score?: number;
  classicEvidenceScore?: number;
  cumulative_lr?: number;
  cumulativeLr?: number;
  background_factors?: any;
  scoring_inputs?: any;
  disconfirmation_penalty?: number;
  disconfirmationPenalty?: number;
  relative_likelihood?: number;
  relativeLikelihood?: number;
  background_score_without_history?: number;
  backgroundScoreWithoutHistory?: number;
  combined_score_without_history?: number;
  combinedScoreWithoutHistory?: number;
  history_contribution?: number;
  historyContribution?: number;
  supportingEvidenceIds: string[];
  contradictingEvidenceIds: string[];
  relatedEntityIds?: string[];
  assessments?: EvidenceAssessment[];
  assessment_count?: number;
  created_at?: string;
  is_unknown?: boolean;
  lead_message?: string;
  version?: number;
  plain_language_summary?: string;
  plain_language_verdict?: string;
  plain_language_drivers?: string;
  plain_language_doubts?: string;
  plain_language_explanation?: PlainLanguageExplanation;
}

export interface LikelihoodRatioReference {
  id?: number;
  category_key: string;
  evidence_type: string;
  finding_name: string;
  support_direction: string;
  min_lr: number;
  max_lr: number;
  typical_lr: number;
  source_citation: string;
  forensic_error_rate?: string;
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

export interface SensitivityImpact {
  evidence_id: number | string;
  file_name: string;
  file_type: string;
  diagnosticity_score: number;
  diagnosticity_category: 'High' | 'Medium' | 'Low' | string;
  is_critical_pivot: boolean;
  top_hypothesis_with: string;
  top_hypothesis_without: string;
  impact_level: 'CRITICAL_PIVOT' | 'HIGH_IMPACT' | 'MODERATE_IMPACT' | 'ROBUST_INSENSITIVE' | string;
  score_shifts: Record<string, number>;
}

export interface SensitivityAnalysisResult {
  case_id: number | string;
  baseline_ranking: Hypothesis[];
  exhibit_impacts: SensitivityImpact[];
  most_critical_evidence_id?: number | string | null;
  most_critical_evidence_name?: string | null;
}

export interface SuspectProfileFactor {
  id: number | string;
  case_id: number | string;
  hypothesis_id: number | string;
  suspect_name?: string;
  factor_type: 'access' | 'opportunity' | 'means' | 'motive' | 'alibi_status' | 'travel_feasibility' | string;
  factor_value: string;
  numeric_adjustment: number;
  note?: string;
  source_evidence_id?: number | string | null;
  source_exhibit_name?: string | null;
  confidence: number;
  entered_by: string;
  is_ai_suggested: boolean;
  is_confirmed: boolean;
  confirmed_by?: string | null;
  confirmed_at?: string | null;
  effect_on_prior?: 'raises_prior' | 'lowers_prior' | 'lowers_prior_sharply' | 'blocks_impossible' | 'tight_margin' | 'feasible' | 'neutral' | string;
  created_at?: string;
  version?: number;
}

export interface TravelFeasibilityCheck {
  status: 'physically_feasible' | 'borderline' | 'physically_impossible' | string;
  feasibility_multiplier: number;
  explanation: string;
  is_blocked: boolean;
}

export interface SuspectProfileResponse {
  status: string;
  case_id: number | string;
  hypothesis_id: number | string;
  hypothesis_title: string;
  background_score: number;
  factors: SuspectProfileFactor[];
  summary: {
    total_factors: number;
    confirmed_count: number;
    pending_ai_count: number;
    has_human_signoff: boolean;
  };
  feasibility_check: TravelFeasibilityCheck;
  avoid_double_counting_rule: string;
}

export interface BackgroundWeightConfig {
  id?: number;
  case_id?: number | null;
  access_weight: number;
  opportunity_weight: number;
  means_weight: number;
  motive_weight: number;
  travel_feasibility_weight: number;
  alibi_strongly_verified_discount: number;
  alibi_partially_verified_discount: number;
  alibi_contradicted_multiplier: number;
  impossible_travel_penalty: number;
  avoid_double_counting_rule?: string;
  config_version?: string;
  updated_by?: string;
  change_rationale?: string;
  include_criminal_history?: boolean;
  criminal_history_max_cap?: number;
  exclude_juvenile_records?: boolean;
  exclude_unverified_identity?: boolean;
  min_identity_confidence?: number;
}

export interface ScoringConfigVersion {
  id: number;
  case_id: number;
  version_tag: string;
  weights_json?: string | null;
  caps_json?: string | null;
  lr_table_json?: string | null;
  rationale?: string | null;
  created_by: string;
  created_at?: string;
}

export interface ReliabilityConfig {
  id: number;
  evidence_type: string;
  base_reliability: number;
  rationale: string;
  created_at?: string;
  updated_at?: string;
}

export interface HypothesisRobustness {
  hypothesis_id: number | string;
  baseline_score: number;
  min_score: number;
  max_score: number;
  range_spread: number;
  range_label: string;
}

export interface ExhibitBreakdownRow {
  evidence_id: number | string;
  evidence_title: string;
  evidence_type: string;
  classification: string;
  classification_label: string;
  confidence: number;
  computed_reliability: number;
  reliability_audit?: any;
  computed_diagnosticity: number;
  diagnosticity_audit?: any;
  contribution: number;
  share_of_support_pct: number;
  quoted_source_line?: string;
  reason?: string;
  analyst_override?: boolean;
  finding_category?: string;
  finding_name?: string;
  likelihood_ratio?: number;
  effective_lr?: number;
  lr_min?: number;
  min_lr?: number;
  lr_max?: number;
  max_lr?: number;
  base_lr?: number;
  lr_source_citation?: string;
  lr_error_rate?: string;
  weight_of_evidence_bans?: number;
  shrinkage_factor_alpha?: number;
  dependency_group?: string;
  is_exculpatory?: boolean;
  clearing_factor_note?: string;
  dependency_weight_multiplier?: number;
  damped_likelihood_ratio?: number;
  version?: number;
}

export interface ScoringRecalculateResponse {
  success: boolean;
  total_relative_sum: number;
  all_zero_diagnosticity: boolean;
  message?: string;
  hypotheses: any[];
  matrix: Record<string, Record<string, any>>;
  hypothesis_breakdowns: Record<string, ExhibitBreakdownRow[]>;
  reliability_audits?: Record<string, any>;
  diagnosticity_audits?: Record<string, any>;
  robustness_ranges: Record<string, HypothesisRobustness>;
  critical_exhibits: any[];
  exhibit_impacts: any[];
}

// --- Change 5: Unknown Hypothesis, Exculpatory Evidence & Dependence ---

export interface DependencyGroupUpdateRequest {
  dependency_group?: string | null;
}

export interface ExculpatoryCategoryDetail {
  name: string;
  clearing_level: string;
  default_lr: number;
  decibans: number;
  statutory_ref: string;
  scientific_citation: string;
  description: string;
}

export interface ExculpatoryConfigOut {
  status?: string;
  categories: Record<string, ExculpatoryCategoryDetail>;
  unknown_hypothesis_title: string;
  default_unknown_prior: number;
  dependency_damping_beta: number;
}

export interface DependencyGroupCluster {
  group_name: string;
  evidence_ids: (number | string)[];
  count: number;
  exhibits: {
    id: number | string;
    file_name: string;
    evidence_type: string;
    rank_in_group: number;
    multiplier: number;
  }[];
}

export interface DependencyGroupsResponse {
  status: string;
  damping_beta: number;
  total_grouped_exhibits: number;
  groups: Record<string, DependencyGroupCluster>;
}

// --- Geographic Case Map ---

export type CrimeType =
  'Murder' |
  'Theft' |
  'Robbery' |
  'Cybercrime' |
  'Missing Person' |
  'Fraud' |
  'Other';

export type GeoCaseStatus =
  'Active' |
  'Investigating' |
  'Solved' |
  'Closed';

export type Severity =
  'Low' |
  'Medium' |
  'High' |
  'Critical';

export interface GeoCase {
  id: string;
  title: string;
  crimeType: CrimeType;
  location: string;
  latitude: number;
  longitude: number;
  status: GeoCaseStatus;
  severity: Severity;
  evidenceCount: number;
  suspectCount: number;
  witnessCount: number;
}

export type GeoEntityType =
  | 'Case'
  | 'Crime Scene'
  | 'Evidence Location'
  | 'Witness Location'
  | 'Suspect Last Seen'
  | 'CCTV Location'
  | 'Vehicle Location';
  
export interface InvestigationTask {
  id: string;
  caseId?: string;
  case_id?: number | string;
  task: string;
  reason: string;
  relatedHypothesisId?: string;
  related_hypothesis_id?: string;
  relatedContradictionId?: string;
  related_contradiction_id?: string;
  relatedEvidenceId?: string;
  related_evidence_id?: string;
  priority: 'High' | 'Medium' | 'Low' | string;
  status: 'Pending' | 'In Progress' | 'Completed' | 'Dismissed' | string;
  assignedTo?: string;
  assigned_to?: string;
  category?: 'investigation' | 'gap_detection' | 'next_best_step' | string;
  impact_score?: number;
  suggested_by_ai?: boolean;
  dismissed?: boolean;
  created_at?: string;
}

// --- Change 6: Ranges and "cannot separate" results ---
export interface MonteCarloHypothesisRange {
  hypothesis_id: number | string;
  title: string;
  is_unknown?: boolean;
  baseline_score: number;
  median_score: number;
  p5_score: number;
  p95_score: number;
  min_score: number;
  max_score: number;
  range_spread: number;
  std_dev: number;
  plain_label: string;
}

export interface MonteCarloScoringResponse {
  success: boolean;
  num_simulations: number;
  ranges: MonteCarloHypothesisRange[];
  cannot_separate: boolean;
  close_results_warning?: string | null;
  discriminating_evidence_needed: string[];
  is_fragile: boolean;
  fragile_exhibit_id?: number | string | null;
  fragile_exhibit_title?: string | null;
  fragility_message?: string | null;
}

// --- Change 7: Next-step suggestions and gap detection ---
export interface InvestigativeGap {
  gap_id: string;
  rule_code: string;
  rule_title: string;
  target_type: string;
  target_id?: number | string | null;
  target_title?: string | null;
  severity: 'high' | 'medium' | 'low' | string;
  description: string;
  recommended_task: string;
  action_category: string;
  default_assigned_to: string;
  priority: 'High' | 'Medium' | 'Low' | string;
  existing_task_id?: number | null;
  is_accepted?: boolean;
  is_dismissed?: boolean;
}

export interface NextBestStepOutcome {
  outcome_label: string;
  target_score: number;
  score_delta: number;
  new_rank_1_title: string;
  rank_flipped: boolean;
  summary: string;
}

export interface NextBestStep {
  step_id: string;
  action_title: string;
  action_type: string;
  target_hypothesis_id?: number | string | null;
  target_hypothesis_title?: string | null;
  expected_impact: number;
  can_flip_rank: boolean;
  max_score_delta: number;
  description: string;
  simulated_outcomes: NextBestStepOutcome[];
  recommended_priority: 'High' | 'Medium' | 'Low' | string;
  suggested_assigned_to: string;
}


// --- Investigation Board / Knowledge Graph ---

export type GraphNodeType =
  | 'Person'
  | 'Organization'
  | 'Location'
  | 'Vehicle'
  | 'Event'
  | 'Other'
  | 'Evidence'
  | 'TimelineEvent'
  | 'Hypothesis';

export interface InvestigationNode {
  id: string;
  label: string;
  type: GraphNodeType;
}

export type EdgeType =
  | 'sourced_from'
  | 'co_mentioned'
  | 'involves'
  | 'references'
  | 'supports'
  | 'contradicts'
  | 'semantic_relation'
  | 'called'
  | 'met'
  | 'visited'
  | 'drove'
  | 'accomplice_of'
  | 'threatened'
  | 'withdrew_funds_at'
  | 'passenger_in'
  | string;

export interface InvestigationEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  type: EdgeType;
  confidence?: number;
  reason?: string;
}

export interface Relationship {
  id: string;
  caseId: string;
  sourceEntityId: string;
  targetEntityId: string;
  relationType: string;
  evidenceId?: string;
  confidence: number;
  reason?: string;
  sourceEntityName?: string;
  targetEntityName?: string;
  createdAt?: string;
}

// --- ACH Validation Benchmark Types ---

export interface CalibrationBinData {
  sample_count: number;
  avg_predicted_confidence: number;
  empirical_accuracy: number;
  calibration_gap: number;
}

export interface BenchmarkMethodMetric {
  method_id: string;
  method_name: string;
  top1_accuracy: string;
  top1_count: number;
  top1_pct: number;
  top2_accuracy: string;
  top2_count: number;
  top2_pct: number;
  mrr: number;
  margin: string;
  margin_val: number;
  stability: string;
  stability_pct: number;
  expected_calibration_error: number;
  calibration_bins: Record<string, CalibrationBinData>;
  latency_ms: string;
  raw_latency: number;
}

export interface CaseMethodRank {
  top_hypothesis: string;
  top_score: number;
  rank_of_gt: number | string;
  margin: number;
  is_correct: boolean;
}

export interface BenchmarkCaseBreakdown {
  case_id: string;
  title: string;
  split: string;
  category: string;
  is_contested: boolean;
  ground_truth_hypothesis: string;
  citation: string;
  rankings_by_method: Record<string, CaseMethodRank>;
}

export interface BenchmarkSensitivityAggregate {
  avg_rank_flips_on_removal: number;
  critical_evidence_precision: number;
  critical_evidence_recall: number;
  critical_evidence_f1: number;
  ach_adversarial_resistance_rate: string;
  llm_adversarial_resistance_rate: string;
}

export interface SystemVariantMetric {
  variant_id: string;
  variant_name: string;
  top1_accuracy: string;
  top1_count: number;
  top1_pct: number;
  tuning_accuracy: string;
  tuning_pct: number;
  test_accuracy: string;
  test_pct: number;
  top2_accuracy: string;
  top2_count: number;
  top2_pct: number;
  mrr: number;
  margin: string;
  margin_val: number;
  stability: string;
  stability_pct: number;
  expected_calibration_error: number;
  calibration_bins: Record<string, CalibrationBinData>;
  evidence_removal_effect: {
    total_exhibits_tested: number;
    total_rank_flips_on_removal: number;
    avg_flips_per_case: number;
    avg_score_shift_decisive_exhibit: number;
    avg_score_shift_non_decisive_exhibit: number;
    critical_evidence_precision: number;
    critical_evidence_recall: number;
    critical_evidence_f1: number;
  };
  ground_truth_ranks: (number | string)[];
  latency_ms: string;
  raw_latency: number;
}

export interface DemographicAxisResult {
  axis_name: string;
  pairs_tested: number;
  flips_detected: number;
  max_disparity: number;
  mean_disparity: number;
  passed: boolean;
}

export interface DemographicBiasReport {
  suite_name: string;
  total_pairs_tested: number;
  total_flips_detected: number;
  max_score_disparity: number;
  mean_score_disparity: number;
  overall_passed: boolean;
  disparity_flagged_count: number;
  axis_breakdown: Record<string, DemographicAxisResult>;
  flagged_disparities: any[];
  statutory_fairness_finding: string;
}

export interface InnocentPriorCaseEvaluation {
  case_id: string;
  case_title: string;
  true_culprit_hypothesis: string;
  innocent_suspect_hypothesis: string;
  true_culprit_rank_no_history: number;
  true_culprit_rank_with_history: number;
  true_culprit_score_with_history: number;
  innocent_suspect_rank_no_history: number;
  innocent_suspect_rank_with_history: number;
  innocent_suspect_score_no_history: number;
  innocent_suspect_score_with_history: number;
  innocent_posterior_score_delta: number;
  evidence_prevailed: boolean;
  false_positive: boolean;
}

export interface InnocentPriorDisadvantageReport {
  suite_name: string;
  cases_tested: number;
  false_positive_count: number;
  false_positive_rate: number;
  rank_displacements_count: number;
  exculpatory_dominance_confirmed: boolean;
  mean_innocent_posterior_delta: number;
  case_evaluations: InnocentPriorCaseEvaluation[];
  conclusion: string;
}

export interface PriorContributionAnalysis {
  evidence_only_acc: number;
  evidence_plus_bg_no_hist_acc: number;
  evidence_plus_bg_with_hist_acc: number;
  delta_accuracy_from_background: number;
  delta_margin_from_background: number;
  delta_accuracy_from_history: number;
  delta_margin_from_history: number;
  background_benefit: string;
  history_honest_verdict: string;
  prior_improves_results: boolean;
  prior_safety_guarantee: string;
}

export interface BenchmarkReport {
  benchmark_timestamp: string;
  total_cases: number;
  scorable_cases: number;
  tuning_cases_count?: number;
  test_cases_count?: number;
  contested_cases_count?: number;
  contested_cases?: number;
  multi_run_iterations: number;
  variants_summary?: SystemVariantMetric[];
  all_methods_summary?: BenchmarkMethodMetric[];
  metrics_summary: BenchmarkMethodMetric[];
  per_case_breakdowns: BenchmarkCaseBreakdown[];
  sensitivity_aggregate?: BenchmarkSensitivityAggregate;
  sensitivity_case_summaries?: any[];
  demographic_bias_analysis?: DemographicBiasReport;
  innocent_prior_disadvantage_analysis?: InnocentPriorDisadvantageReport;
  prior_contribution_analysis?: PriorContributionAnalysis;
  error_and_limitation_analysis?: {
    unresolved_case_notes: string;
    synthetic_trap_performance: string;
    diagnosticity_ablation_finding?: string;
    calibration_finding?: string;
    innocent_prior_guarantee?: string;
    prior_contribution_finding?: string;
  };
}

// --- Authentication & User Types ---

export interface UserOut {
  id: number;
  email: string;
  full_name: string;
  role: 'admin' | 'lead_investigator' | 'analyst' | 'reviewer' | string;
  badge_number?: string;
  department?: string;
  is_active: boolean;
  accessible_cases?: number[] | null;
  created_at?: string;
  is_2fa_enabled?: boolean;
  session_duration_minutes?: number;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in_minutes: number;
  user?: UserOut | null;
  requires_2fa?: boolean;
  temp_token?: string | null;
}

// --- Chain of Custody & Cryptographic Merkle Audit Log Types (Feature 2) ---

export interface CustodyLogEntry {
  id: number;
  evidence_id: number;
  case_id: number;
  action: string;
  actor_name: string;
  actor_role?: string;
  source_agency?: string;
  location?: string;
  timestamp: string;
  file_hash_snapshot?: string;
  notes?: string;
}

export interface AuditLogEntry {
  id: number;
  case_id?: number | null;
  user_id?: number | null;
  user_name: string;
  user_role?: string;
  action_type: string;
  target_type: string;
  target_id?: string | null;
  description: string;
  before_value?: string | null;
  after_value?: string | null;
  ip_address?: string | null;
  timestamp: string;
  previous_hash: string;
  current_hash: string;
}

export interface ChainVerificationResult {
  chain_intact: boolean;
  total_entries: number;
  verified_count: number;
  genesis_hash: string;
  latest_hash: string;
  last_timestamp?: string | null;
  status: string;
  message: string;
  tampered_at_index?: number | null;
  tampered_entry_id?: number | null;
  error?: string | null;
}

export interface EvidenceIntegrityResult {
  success: boolean;
  evidence_id: number;
  file_name: string;
  stored_hash?: string;
  recomputed_hash?: string;
  integrity_verified: boolean;
  status: string;
  message: string;
}

// --- Source-Span Citations & Exhibit Chunks (Feature 3) ---

export interface ExhibitChunk {
  id: number;
  evidence_id: number;
  case_id: number;
  chunk_index: number;
  text: string;
  page_number?: number | null;
  char_start: number;
  char_end: number;
  start_time_sec?: number | null;
  end_time_sec?: number | null;
}

export interface SourceCitation {
  id: number;
  case_id: number;
  evidence_id: number;
  chunk_id?: number | null;
  fact_type: 'entity' | 'event' | 'claim' | 'assessment' | string;
  fact_id?: number | null;
  quote: string;
  page_number?: number | null;
  char_start?: number | null;
  char_end?: number | null;
  timestamp_sec?: number | null;
  verified_match: boolean;
  match_confidence: number;
  verification_method: 'exact_substring' | 'fuzzy_token' | 'normalized_substring' | 'unverified' | string;
}

export interface TextCorrectionResult {
  success: boolean;
  evidence_id: number;
  total_chunks: number;
  total_citations: number;
  verified_citations: number;
  unverified_citations: number;
  message: string;
}

// ==============================================================================
// CHANGE 3: PRIOR CRIMINAL HISTORY & SAFEGUARDS TYPES
// ==============================================================================

export type PriorOutcome = 'convicted' | 'acquitted' | 'discharged' | 'pending' | 'merely_accused' | string;
export type VerificationStatus = 'verified' | 'unverified' | 'disputed' | string;

export interface PriorRecord {
  id: number;
  case_id: number;
  hypothesis_id?: number | null;
  person_entity_id?: number | null;
  suspect_name: string;
  offense_type: string;
  legal_section?: string | null;
  offense_date?: string | null;
  location?: string | null;
  outcome: PriorOutcome;
  weapon_used?: string | null;
  entry_method?: string | null;
  victim_type?: string | null;
  location_type?: string | null;
  time_pattern?: string | null;
  mo_description?: string | null;
  source_agency: string;
  source_document?: string | null;
  verification_status: VerificationStatus;
  identity_match_confidence: number;
  verified_identity: boolean;
  is_juvenile: boolean;
  computed_mo_similarity: number;
  similarity_breakdown?: string | null;
  quoted_comparison?: string | null;
  effective_weight: number;
  history_contribution: number;
  entered_by: string;
  created_at?: string | null;
  updated_at?: string | null;
  version?: number;
}

export interface CriminalHistoryComparisonHypothesis {
  hypothesis_id: number;
  title: string;
  rank_with_history: number;
  rank_without_history: number;
  background_with_history: number;
  background_without_history: number;
  combined_with_history: number;
  combined_without_history: number;
  evidence_score: number;
  history_contribution_pct: number;
  rank_changed: boolean;
}

export interface CriminalHistoryComparison {
  case_id: number;
  include_criminal_history: boolean;
  criminal_history_max_cap: number;
  legal_safeguard_notice: string;
  total_prior_records: number;
  hypotheses_comparison: CriminalHistoryComparisonHypothesis[];
}

export interface PriorRecordsResponse {
  case_id: number;
  legal_safeguard_notice: string;
  include_criminal_history: boolean;
  criminal_history_max_cap: number;
  total_records: number;
  is_role_restricted?: boolean;
  restricted_message?: string;
  records: PriorRecord[];
}

export interface BackgroundJob {
  id: number;
  case_id: number;
  exhibit_id?: number | null;
  user_id?: number | null;
  created_by?: string;
  job_type: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled';
  current_stage?: string;
  progress_pct: number;
  attempt_count: number;
  max_attempts: number;
  error_message?: string | null;
  error_detail?: string | null;
  stage_results?: Record<string, any>;
  next_run_at?: string | null;
  priority: number;
  created_at?: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export type Job = BackgroundJob;

// ==============================================================================
// MULTI-USER LIVE COLLABORATION, PRESENCE & CONCURRENCY TYPES
// ==============================================================================

export interface PresenceUser {
  user_id: number;
  user_name: string;
  user_role: string;
  current_location: string;
  item_id?: string | null;
  last_seen_at?: string | null;
}

export interface EditLock {
  id?: number;
  case_id: number;
  item_type: string;
  item_id: string;
  user_id: number;
  user_name: string;
  user_role: string;
  acquired_at?: string | null;
  expires_at: string;
  is_active: boolean;
  client_token?: string | null;
}

export interface CollaborationEvent {
  id: number;
  case_id: number;
  event_type: 'item.changed' | 'lock.acquired' | 'lock.released' | 'presence.joined' | 'presence.left' | 'presence.moved' | 'scores.updated' | 'job.progress' | string;
  item_type?: string | null;
  item_id?: string | null;
  version?: number | null;
  user_id?: number | null;
  user_name?: string | null;
  summary: string;
  payload?: any;
  is_restricted?: boolean;
  created_at?: string;
  timestamp?: string;
}

export interface ConflictDetail {
  error: 'conflict';
  message: string;
  item_type: string;
  item_id: string;
  current_version: number;
  submitted_version?: number | null;
  current_data: any;
}

export interface Alert {
  id: number;
  case_id: number;
  rule_type: string;
  severity: 'critical' | 'warning' | 'info';
  title: string;
  message: string;
  linked_item_type?: string | null;
  linked_item_id?: string | null;
  status: 'unread' | 'read' | 'acknowledged' | 'resolved';
  dedup_key: string;
  is_restricted: boolean;
  created_at: string;
  acknowledged_at?: string | null;
  acknowledged_by?: string | null;
  snoozed_until?: string | null;
  resolved_at?: string | null;
  resolution_reason?: string | null;
}

export interface NotificationPreference {
  id: number;
  user_id: number;
  rule_type: string;
  in_app_enabled: boolean;
  email_enabled: boolean;
  digest_mode: string;
  quiet_hours_start?: string | null;
  quiet_hours_end?: string | null;
}

export interface StatutoryDeadlineRule {
  id: number;
  statute_name: string;
  section_reference: string;
  offence_category: string;
  limit_days: number;
  trigger_event: string;
  description: string;
  procedure_name?: string;
  is_reviewed_by_expert?: boolean;
  expert_reviewer?: string;
  legal_notes?: string;
}

export interface CaseProcedureUpdate {
  fir_number?: string;
  fir_date?: string;
  incident_date?: string;
  arrest_date?: string;
  remand_date?: string;
  offence_section?: string;
  statutory_time_limit_days?: number;
}

export interface EvidenceChecklistItem {
  exhibit_code: string;
  title: string;
  description: string;
  mandatory: boolean;
  legal_provision: string;
  consequence_if_missing: string;
  status: 'present' | 'missing';
  matched_evidence_id?: number | null;
  matched_file_name?: string | null;
  matched_at?: string | null;
}

export interface EvidenceChecklistResponse {
  case_id: number;
  offence_section?: string | null;
  offence_category: string;
  total_expected: number;
  mandatory_expected: number;
  present_count: number;
  missing_count: number;
  mandatory_missing_count: number;
  compliance_percentage: number;
  items: EvidenceChecklistItem[];
  warnings: string[];
}

export interface CaseDeadline {
  id: number;
  case_id: number;
  statute_rule_id?: number | null;
  title: string;
  due_date: string;
  status: 'pending' | 'satisfied' | 'extended' | 'overdue';
  days_remaining: number;
  satisfied_at?: string | null;
  satisfied_by?: string | null;
  extended_until?: string | null;
  extension_reason?: string | null;
  created_at: string;
}

export interface HandoverSummary {
  id: number;
  case_id: number;
  period_start: string;
  period_end: string;
  headline: string;
  structured_content?: any;
  rendered_text: string;
  generated_by: string;
  generation_type: string;
  created_at: string;
}

export interface SinceYouWereAwaySummary {
  case_id: number;
  last_seen_at: string;
  headline: string;
  hours_away: number;
  new_evidence_count: number;
  changed_hypotheses_count: number;
  overrides_count: number;
  open_tasks_count: number;
  unresolved_alerts_count: number;
  recent_active_users: string[];
  summary_points: string[];
}


// --- Chargesheet & Docket Assistant Models ---

export interface ChargesheetExhibitItem {
  exhibit_code: string;
  evidence_id: number;
  title: string;
  evidence_type: string;
  file_hash: string;
  sec_65b_certificate_present: boolean;
  chain_of_custody_complete: boolean;
  statutory_compliance: string;
  source_location: string;
  probative_relevance: string;
  source_span?: {
    file_name: string;
    chunk_id: number;
    char_start: number;
    char_end: number;
    quote: string;
  };
}

export interface ChargesheetWitnessItem {
  witness_code: string;
  name: string;
  designation_or_role: string;
  statutory_provision: string;
  statement_gist: string;
  quoted_span_text: string;
  source_span?: {
    file_name: string;
    chunk_id: number;
    char_start: number;
    char_end: number;
    quote: string;
  };
}

export interface ChargesheetForensicItem {
  finding_code: string;
  report_name: string;
  expert_category: string;
  finding_summary: string;
  evidentiary_impact: string;
  source_span?: {
    file_name: string;
    chunk_id: number;
    char_start: number;
    char_end: number;
    quote: string;
  };
}

export interface ChargesheetDraft {
  id: number;
  case_id: number;
  title: string;
  court_name: string;
  police_station: string;
  fir_number?: string | null;
  offence_section?: string | null;
  investigating_officer?: string | null;
  status: 'draft' | 'under_review' | 'approved' | 'finalized';
  legal_review_status: 'pending_legal_review' | 'scrutiny_cleared' | 'revisions_requested';
  is_draft: boolean;
  version: number;
  facts_narrative: string;
  evidence_inventory: ChargesheetExhibitItem[];
  witness_statements: ChargesheetWitnessItem[];
  forensic_findings: ChargesheetForensicItem[];
  analysis_and_charges: string;
  source_citations?: any[];
  legal_disclaimer: string;
  created_by: string;
  last_edited_by?: string | null;
  last_edit_summary?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChargesheetEditLog {
  id: number;
  chargesheet_id: number;
  case_id: number;
  version: number;
  section_edited: string;
  edit_summary: string;
  edited_by_user_id?: number | null;
  edited_by_name: string;
  created_at: string;
}

export interface ChargesheetUpdateRequest {
  section_edited?: string;
  edit_summary?: string;
  title?: string;
  court_name?: string;
  police_station?: string;
  fir_number?: string;
  offence_section?: string;
  investigating_officer?: string;
  status?: string;
  legal_review_status?: string;
  facts_narrative?: string;
  evidence_inventory?: ChargesheetExhibitItem[];
  witness_statements?: ChargesheetWitnessItem[];
  forensic_findings?: ChargesheetForensicItem[];
  analysis_and_charges?: string;
}

// ==============================================================================
// INTERVIEWS & DEPOSITION ANALYSIS
// ==============================================================================

export interface InterviewContradiction {
  id: number;
  interview_id: number;
  statement_id: number;
  case_id: number;
  quote_new: string;
  source_new: string;
  quote_prior: string;
  source_prior: string;
  prior_statement_id?: number | null;
  prior_evidence_id?: number | null;
  conflict_type: string;
  reasoning: string;
  confidence: number;
  severity: 'critical' | 'major' | 'minor' | string;
  created_at: string;
}

export interface InterviewStatement {
  id: number;
  interview_id: number;
  case_id: number;
  sequence_order: number;
  speaker: string;
  role: 'investigator' | 'interviewee' | 'counsel' | string;
  timestamp_marker: string;
  seconds: number;
  question?: string | null;
  question_source_type?: string | null;
  question_source_id?: string | null;
  text: string;
  tag?: string | null;
  is_contradiction_flag: boolean;
  created_at: string;
  contradictions?: InterviewContradiction[];
}

export interface InterviewSession {
  id: number;
  case_id: number;
  session_code: string;
  interviewee_name: string;
  interviewee_role: 'suspect' | 'witness' | 'approver' | 'victim' | 'expert' | string;
  interviewer_name: string;
  interview_date?: string | null;
  duration: string;
  status: 'Transcribed' | 'Active' | 'Pending Analysis' | string;
  audio_url?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
  statement_count?: number;
  contradiction_count?: number;
  statements?: InterviewStatement[];
  contradictions?: InterviewContradiction[];
}

export interface SuggestedQuestion {
  id: string;
  category: 'contradiction' | 'gap' | 'alibi' | string;
  category_label: string;
  title: string;
  question: string;
  rationale: string;
  quote_a?: string | null;
  quote_b?: string | null;
  source_a?: string | null;
  source_b?: string | null;
  severity: 'critical' | 'major' | 'minor' | string;
  is_subject_specific: boolean;
  source_id?: string | null;
}

export interface StatementAnalysisResponse {
  statement: InterviewStatement;
  has_contradiction: boolean;
  new_contradictions: InterviewContradiction[];
}

// ==============================================================================
// CROSS-CASE INTELLIGENCE & ENTITY RESOLUTION TYPES
// ==============================================================================

export interface CrossCaseEntityDetail {
  id?: number | null;
  name: string;
  type: string;
}

export interface CrossCaseEntityLink {
  id: number;
  case_id: number;
  linked_case_id: number;
  linked_case_title: string;
  entity_type: 'person' | 'phone' | 'vehicle' | 'address' | 'digital' | string;
  match_type: 'exact_identifier' | 'exact_name' | 'fuzzy_name' | 'fuzzy_address' | string;
  match_value: string;
  similarity_score: number;
  status: 'pending_review' | 'confirmed' | 'rejected' | string;
  confidence_reason: string;
  source_entity: CrossCaseEntityDetail;
  linked_entity: CrossCaseEntityDetail;
  reviewed_by_user_id?: number | null;
  reviewed_by_name?: string | null;
  reviewed_at?: string | null;
  reviewer_notes?: string | null;
  created_at?: string | null;
}

export interface CrossCaseMOSimilarCase {
  case_id: number;
  title: string;
  fir_number: string;
  status: string;
  offence_section: string;
  similarity_score: number;
  similarity_percentage: number;
  matched_features: string[];
  field_scores: Record<string, number>;
  description_snippet: string;
}

export interface CrossCaseIntelligenceSummary {
  case_id: number;
  total_links: number;
  pending_links: number;
  confirmed_links: number;
  rejected_links: number;
  links: CrossCaseEntityLink[];
  similar_cases: CrossCaseMOSimilarCase[];
}

export interface MatchingFeatureDetail {
  link_id: number;
  entity_type: string;
  match_type: string;
  match_value: string;
  similarity_score: number;
  confidence_reason: string;
  status: string;
}

export interface ConnectedCaseGroup {
  linked_case_id: number;
  linked_case_title: string;
  status: 'pending_review' | 'confirmed' | 'rejected' | string;
  has_pending_review: boolean;
  highest_similarity_score: number;
  feature_types: string[];
  matching_features: MatchingFeatureDetail[];
}

export interface ConnectedCasesSummary {
  case_id: number;
  total_connected_cases: number;
  pending_candidates_count: number;
  confirmed_connections_count: number;
  connected_cases: ConnectedCaseGroup[];
}

// ==============================================================================
// CDR & FORENSIC FINANCIAL ANALYTICS TYPES
// ==============================================================================

export interface CDRRecord {
  id: number;
  case_id: number;
  evidence_id?: number | null;
  source_file_name: string;
  row_number: number;
  calling_number: string;
  called_number?: string | null;
  call_datetime: string;
  call_duration_sec: number;
  call_type: string;
  imei?: string | null;
  imsi?: string | null;
  cell_id: string;
  azimuth?: number | null;
  site_name?: string | null;
  latitude?: number | null;
  longitude?: number | null;
}

export interface BankTransaction {
  id: number;
  case_id: number;
  evidence_id?: number | null;
  source_file_name: string;
  row_number: number;
  transaction_date: string;
  value_date?: string | null;
  description: string;
  reference_number?: string | null;
  debit_amount: number;
  credit_amount: number;
  balance?: number | null;
  account_number: string;
  counterparty_account?: string | null;
  counterparty_name?: string | null;
  bank_name?: string | null;
  transaction_mode: string;
}

export interface CoLocationPhoneEndpoint {
  number: string;
  timestamp: string;
  evidence_id?: number | null;
  source_file: string;
  row_number: number;
  duration_sec: number;
  call_type: string;
}

export interface CoLocationEvent {
  event_id: string;
  cell_id: string;
  site_name?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  time_delta_seconds: number;
  time_delta_minutes: number;
  confidence: number;
  phone_a: CoLocationPhoneEndpoint;
  phone_b: CoLocationPhoneEndpoint;
  reasoning: string;
}

export interface CommonContactRowCitation {
  source_file: string;
  row_number: number;
  timestamp: string;
  duration_sec: number;
  cell_id: string;
  site_name?: string | null;
}

export interface CommonContactBreakdown {
  suspect_number: string;
  call_count: number;
  total_duration_sec: number;
  row_citations: CommonContactRowCitation[];
}

export interface CommonContact {
  contact_number: string;
  suspects_connected_count: number;
  suspects_connected: string[];
  total_calls: number;
  total_duration_sec: number;
  first_contact: string;
  last_contact: string;
  breakdown: CommonContactBreakdown[];
  all_linked_rows: CommonContactRowCitation[];
  risk_rating: string;
}

export interface ShortLivedNumberRowCitation {
  source_file: string;
  row_number: number;
  timestamp: string;
  called_number?: string | null;
  cell_id: string;
  site_name?: string | null;
  duration_sec: number;
}

export interface ShortLivedNumber {
  phone_number: string;
  total_events: number;
  first_seen: string;
  last_seen: string;
  active_duration_hours: number;
  unique_towers_count: number;
  towers: string[];
  imeis: string[];
  linked_rows: ShortLivedNumberRowCitation[];
  indicator: string;
  reasoning: string;
}

export interface ImpossibleTravelEndpoint {
  source_file: string;
  row_number: number;
  timestamp: string;
  cell_id: string;
  site_name?: string | null;
  latitude?: number | null;
  longitude?: number | null;
}

export interface ImpossibleTravelEvent {
  phone_number: string;
  calculated_speed_kmh: number;
  distance_km: number;
  time_delta_minutes: number;
  event_a: ImpossibleTravelEndpoint;
  event_b: ImpossibleTravelEndpoint;
  reasoning: string;
}

export interface CDRAnalyticsOverview {
  case_id: number;
  total_records: number;
  unique_callers: number;
  unique_towers: number;
  co_location_events: CoLocationEvent[];
  common_contacts: CommonContact[];
  short_lived_numbers: ShortLivedNumber[];
  impossible_travel: ImpossibleTravelEvent[];
  records_sample: CDRRecord[];
}

export interface MoneyFlowLinkedRow {
  source_file: string;
  row_number: number;
  date: string;
  amount: number;
  type: string;
  reference?: string | null;
  mode: string;
  description: string;
}

export interface MoneyFlowNode {
  id: string;
  label: string;
  type: string;
  total_in: number;
  total_out: number;
  net_flow: number;
  transaction_count: number;
}

export interface MoneyFlowEdge {
  source: string;
  target: string;
  total_amount: number;
  transaction_count: number;
  modes: string[];
  linked_rows: MoneyFlowLinkedRow[];
}

export interface MoneyFlowStructuringAlert {
  alert_type: string;
  title: string;
  severity: string;
  matched_transactions_count: number;
  total_structured_amount: number;
  reasoning: string;
  linked_rows: Array<{
    source_file: string;
    row_number: number;
    date: string;
    amount: number;
    reference?: string | null;
    description: string;
  }>;
}

export interface MoneyFlowLayeringAlert {
  alert_type: string;
  title: string;
  severity: string;
  inflow_amount: number;
  dispersed_amount: number;
  timeframe_hours: number;
  reasoning: string;
  inflow_row: {
    source_file: string;
    row_number: number;
    date: string;
    amount: number;
    description: string;
  };
  outflow_rows: Array<{
    source_file: string;
    row_number: number;
    date: string;
    amount: number;
    description: string;
  }>;
}

export interface MoneyFlowAnalysis {
  nodes: MoneyFlowNode[];
  edges: MoneyFlowEdge[];
  total_transactions: number;
  total_volume: number;
  structuring_alerts: MoneyFlowStructuringAlert[];
  layering_alerts: MoneyFlowLayeringAlert[];
}

// ==============================================================================
// MULTILINGUAL EVIDENCE, OCR PROFILING & SIDE-BY-SIDE TYPES
// ==============================================================================

export interface LanguageProfileConfig {
  id: number;
  language: string;
  script: string;
  content_type: string;
  reading_method: string;
  fallback_method?: string | null;
  stt_model_hint?: string | null;
  preprocessing_steps: string;
  confidence_threshold: number;
  translate_by_default: boolean;
  default_target_language: string;
  created_at: string;
}

export interface ExhibitSegment {
  id: number;
  evidence_id: number;
  version_id: number;
  case_id: number;
  segment_index: number;
  page_number?: number | null;
  bbox_json?: string | null;
  start_time_sec?: number | null;
  end_time_sec?: number | null;
  speaker_label?: string | null;
  raw_text: string;
  normalized_text: string;
  confidence: number;
  is_low_confidence: boolean;
  status: 'machine_read' | 'reviewed' | 'corrected' | 'disputed' | string;
  reading_method?: string | null;
  created_at: string;
}

export interface ExhibitTextVersion {
  id: number;
  evidence_id: number;
  case_id: number;
  version_number: number;
  raw_text: string;
  normalized_text: string;
  extracted_text?: string;
  reading_method: string;
  overall_confidence: number;
  status: 'machine_read' | 'reviewed' | 'corrected' | 'disputed' | string;
  is_current: boolean;
  created_by: string;
  created_at: string;
  edit_reason?: string | null;
  diff_summary?: string | null;
  requires_second_signoff: boolean;
  second_signoff_by?: string | null;
  second_signoff_at?: string | null;
  is_reverted: boolean;
  reverted_from_version?: number | null;
  segments?: ExhibitSegment[];
}

export interface TranslationSegment {
  id: number;
  translation_id: number;
  source_segment_id?: number | null;
  source_text_snippet: string;
  translated_text: string;
  alignment_confidence: number;
  proper_names_json?: string | null;
  created_at: string;
}

export interface ExhibitTranslation {
  id: number;
  evidence_id: number;
  version_id: number;
  source_language: string;
  target_language: string;
  author_type: 'machine' | 'certified_human' | 'analyst' | string;
  author_name: string;
  model_used?: string | null;
  review_status: 'unreviewed' | 'reviewed' | string;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  full_translated_text: string;
  created_at: string;
  aligned_segments?: TranslationSegment[];
}

export interface DualCitation {
  citation_id: number;
  evidence_id: number;
  file_name: string;
  primary_language: string;
  original_quote: string;
  location_tag: string;
  page_number?: number | null;
  timestamp_sec?: number | null;
  char_start?: number | null;
  char_end?: number | null;
  translated_quote?: string | null;
  translation_label?: string | null;
  is_verified: boolean;
  is_stale: boolean;
  viewer_link: string;
}

export interface MultilingualProfileResponse {
  evidence_id: number;
  file_name: string;
  file_type: string;
  primary_language: string;
  is_mixed: boolean;
  script: string;
  content_type: string;
  language_source: string;
  text_quality_status: string;
  is_poor_audio: boolean;
  ocr_reading_method?: string | null;
  ocr_confidence: number;
  current_version?: ExhibitTextVersion | null;
  versions_count: number;
  versions: ExhibitTextVersion[];
  translations: ExhibitTranslation[];
  dual_citations: DualCitation[];
  reliability_assessment: Record<string, any>;
}

// ============================================================
// DECISION QUALITY & DEVIL'S ADVOCATE TYPES
// ============================================================

export interface PlainLanguageExplanation {
  hypothesis_id: number;
  rank: number;
  score_pct: number;
  verdict: string;
  summary: string;
  primary_drivers: string[];
  vulnerabilities_and_doubts: string[];
  recommended_action: string;
}

export interface DevilsAdvocatePoint {
  evidence_id: number;
  evidence_title: string;
  evidence_type: string;
  counter_classification: string;
  lead_classification: string;
  role_in_counter_case: string;
  probative_weight: number;
  quoted_source_span?: string | null;
  counter_rationale?: string | null;
  sec_65b_present: boolean;
  hash_verified: boolean;
}

export interface DevilsAdvocateVulnerability {
  evidence_id: number;
  evidence_title: string;
  evidence_type?: string;
  contribution_to_lead: number;
  vulnerabilities: string[];
  defense_challenge_vector: string;
}

export interface DevilsAdvocateSuppression {
  suppressed_exhibit_id: number;
  suppressed_exhibit_title: string;
  suppression_legal_ground: string;
  original_lead_score: number;
  new_lead_score: number;
  original_counter_score: number;
  new_counter_score: number;
  score_drop_pct: number;
  new_prob_gap: number;
  rank_flipped: boolean;
  impact_summary: string;
}

export interface DevilsAdvocateBrief {
  executive_challenge: string;
  counter_case_narrative: string;
  defense_cross_examination_angles: string[];
  stress_test_recommendations: string[];
}

export interface DevilsAdvocateResponse {
  success: boolean;
  case_id?: number;
  message?: string;
  leading_hypothesis?: {
    id: number;
    title: string;
    score_pct: number;
  } | null;
  counter_hypothesis?: {
    id: number;
    title: string;
    score_pct: number;
  } | null;
  prob_gap?: number;
  required_shift_to_overtake?: number;
  counter_corroborating_points: DevilsAdvocatePoint[];
  lead_vulnerabilities: DevilsAdvocateVulnerability[];
  suppression_simulation?: DevilsAdvocateSuppression | null;
  legal_challenge_brief?: DevilsAdvocateBrief | null;
}

export interface DecisionSignoff {
  id: number;
  case_id: number;
  item_type: 'evidence_assessment' | 'chargesheet_draft' | 'hypothesis_ranking' | 'final_report' | string;
  item_id: number;
  item_summary: string;
  maker_user_id?: number | null;
  maker_name: string;
  checker_user_id?: number | null;
  checker_name?: string | null;
  checker_role?: string | null;
  status: 'pending' | 'approved' | 'rejected' | 'waived' | string;
  review_notes?: string | null;
  requested_at: string;
  reviewed_at?: string | null;
}

// ============================================================
// SECURITY, 2FA, PRIVATE MODEL & BACKUP TYPES
// ============================================================

export interface UserSession {
  id: number;
  device_info: string;
  ip_address?: string | null;
  user_agent?: string | null;
  created_at: string;
  last_active_at: string;
  expires_at: string;
  is_revoked: boolean;
}

export interface SystemSecurityConfig {
  id: number;
  default_ai_provider: 'cloud_gemini' | 'local_ollama' | 'local_vllm' | 'custom_local';
  local_ai_endpoint: string;
  local_ai_model: string;
  block_external_ai_globally: boolean;
  default_session_duration_minutes: number;
  enforce_two_factor_globally: boolean;
  updated_at?: string | null;
}

export interface BackupRecord {
  id: number;
  file_name: string;
  file_size_bytes: number;
  sha256_hash: string;
  backup_type: string;
  created_at: string;
  restore_test_status: 'untested' | 'in_progress' | 'passed' | 'failed';
  restore_test_results?: Record<string, any> | null;
  restore_tested_at?: string | null;
  is_deleted: boolean;
}

export interface TwoFactorSetupResponse {
  secret: string;
  otpauth_uri: string;
  backup_codes: string[];
}

// --- Validation 2.0: Blind Benchmark, Domain Reviewers & Regression Catcher Types ---

export interface IndependentAuthor {
  id: string;
  name: string;
  title: string;
  institution: string;
  specialization: string;
  case_contributed: string;
}

export interface DomainReviewer {
  id: string;
  name: string;
  role_category: string;
  credential: string;
  focus: string;
}

export interface FrozenSuiteMetadata {
  suite_version: string;
  name: string;
  description: string;
  is_frozen: boolean;
  checksum_sha256: string;
  total_cases: number;
  authors: IndependentAuthor[];
  domain_reviewers: DomainReviewer[];
}

export interface CalibrationBin {
  bin: string;
  count: number;
  avg_confidence: number;
  empirical_accuracy: number;
  calibration_gap: number;
}

export interface ValidationCalibration {
  expected_calibration_error: number;
  expected_calibration_error_pct: number;
  brier_score: number;
  calibration_bins: CalibrationBin[];
}

export interface ValidationStability {
  stability_score: number;
  rank_flips_detected: number;
  is_deterministic: boolean;
  max_score_drift_pct: number;
  avg_score_drift_pct: number;
  iterations_per_case: number;
}

export interface ReviewerEvaluationDetail {
  reviewer_name: string;
  top_ranked: string;
  confidence: number;
  spearman_rho: number;
  plausibility: number;
  legal_defensibility: number;
  rebuttal_resistance: number;
  notes: string;
}

export interface ReviewerSummary {
  reviewer_name: string;
  role: string;
  avg_spearman_rho: number;
  top1_agreement_pct: number;
  agreements_count: string;
}

export interface MultiReviewerComparison {
  overall_human_system_consensus_rho: number;
  reviewer_summaries: Record<string, ReviewerSummary>;
  per_case_evaluations: Array<{
    case_id: string;
    case_title: string;
    system_top_hypothesis: string;
    reviewers: Record<string, ReviewerEvaluationDetail>;
  }>;
}

export interface FailureNote {
  case_id: string;
  case_title: string;
  culprit: string;
  culprit_rank: number;
  decisiveness_margin: number;
  rationale: string;
  failure_note: string;
}

export interface RegressionAlert {
  type: string;
  severity: 'CRITICAL' | 'WARNING';
  message: string;
}

export interface RegressionStatus {
  status: 'PASSED' | 'REGRESSION_DETECTED';
  is_regression: boolean;
  regressions_count: number;
  alerts: RegressionAlert[];
  summary: string;
}

export interface ValidationV2Report {
  suite_version: string;
  suite_name: string;
  checksum_sha256: string;
  run_timestamp: string;
  run_by: string;
  total_blind_cases: number;
  accuracy: {
    top1_pct: number;
    top1_count: string;
    top3_pct: number;
    top3_count: string;
  };
  ranking_position: {
    mrr: number;
    avg_culprit_rank: number;
    median_culprit_rank: number;
    rank_distribution: {
      rank_1: number;
      rank_2: number;
      rank_3_plus: number;
    };
  };
  calibration: ValidationCalibration;
  stability: ValidationStability;
  multi_reviewer_comparison: MultiReviewerComparison;
  failure_notes: FailureNote[];
  regression_status: RegressionStatus;
  cases: Array<{
    case_id: string;
    case_title: string;
    ranked_hypotheses: Array<{
      id: string;
      title: string;
      relative_likelihood: number;
    }>;
    predicted_top_id: string;
    predicted_top_label: string;
    predicted_top_score: number;
    runner_up_id: string;
    runner_up_score: number;
    decisiveness_margin: number;
    is_correct: boolean;
    culprit_rank: number;
    true_hypothesis_id: string;
    true_culprit_name: string;
    decisive_exhibits: string[];
    forensic_rationale: string;
    failure_note: string;
    sealed_hash: string;
  }>;
  frozen_baseline_comparison: {
    baseline: Record<string, any>;
    delta_top1_pct: number;
    delta_mrr: number;
    delta_ece: number;
  };
}

// --- Live Data Connectors (Automated Evidence Ingestion Pipeline) ---

export type ConnectorType = 'folder_watch' | 'email_inbox' | 'api_pull' | 'webhook';
export type ConnectorStatus = 'idle' | 'polling' | 'active' | 'paused' | 'error';

export interface DataConnector {
  id: number;
  case_id: number;
  name: string;
  connector_type: ConnectorType | string;
  source_identifier: string;
  config_json?: string;
  webhook_token?: string | null;
  webhook_url?: string | null;
  is_active: boolean;
  status: ConnectorStatus | string;
  last_polled_at?: string | null;
  last_ingest_at?: string | null;
  items_ingested_count: number;
  error_message?: string | null;
  created_by?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface ConnectorIngestRecord {
  id: number;
  connector_id: number;
  case_id: number;
  evidence_id?: number | null;
  source_system: string;
  source_filename: string;
  file_hash: string;
  file_size: number;
  receipt_time: string;
  status: 'success' | 'duplicate_skipped' | 'failed' | string;
  error_message?: string | null;
  details_json?: string | null;
  created_at?: string;
}

export interface ConnectorPollResponse {
  success: boolean;
  connector_id: number;
  connector_name: string;
  items_fetched: number;
  items_ingested: number;
  duplicates_skipped: number;
  errors_count: number;
  message: string;
  ingested_evidence_ids: number[];
}

export interface ConnectorSimulateDropRequest {
  sample_type?: 'cdr_export' | 'lab_toxicology' | 'bank_statement' | 'cctv_metadata' | 'whistleblower_email' | string;
  custom_filename?: string;
  custom_content?: string;
}

// ==============================================================================
// VOICE NOTES & CITATION TYPES
// ==============================================================================

export interface VoiceNoteCitation {
  citation_id: number;
  citation_code: string;
  chunk_id: number;
  char_start: number;
  char_end: number;
  quote: string;
}

export interface VoiceNote {
  id: number;
  case_id: number;
  evidence_id: number;
  citation_code: string;
  note_text: string;
  category: string;
  officer_name: string;
  officer_role: string;
  latitude?: number | null;
  longitude?: number | null;
  location_name?: string | null;
  recorded_at: string;
  audio_path?: string | null;
  file_hash: string;
  citations: VoiceNoteCitation[];
  created_at: string;
}

// ==============================================================================
// OFFLINE FIELD CAPTURE TYPES
// ==============================================================================

export interface OfflineFieldExhibit {
  id: string;
  caseId: string | number;
  title: string;
  evidenceType: 'photograph' | 'video' | 'audio' | 'document' | string;
  fileName: string;
  blobDataUrl?: string;
  fileSize: number;
  clientHash: string;
  capturedAt: string;
  latitude?: number | null;
  longitude?: number | null;
  accuracy?: number | null;
  locationName?: string;
  tamperSealNumber?: string;
  custodyNotes?: string;
  officerDeclaration: string;
  syncStatus: 'pending' | 'syncing' | 'synced' | 'failed';
  syncError?: string;
  syncedEvidenceId?: string | number;
}

// ==============================================================================
// SYSTEM HEALTH & EXHIBIT DATA QUALITY TYPES
// ==============================================================================

export interface AIServiceStatus {
  service_name: string;
  provider: string;
  status: 'available' | 'degraded' | 'offline' | 'unconfigured' | 'disabled';
  latency_ms?: number | null;
  endpoint_or_model: string;
  notes: string;
}

export interface BackupHealth {
  last_backup_id?: number | null;
  last_backup_at?: string | null;
  seconds_since_last_backup?: number | null;
  time_since_backup_human: string;
  backup_status: 'up_to_date' | 'due' | 'overdue' | 'no_backup';
  last_backup_filename?: string | null;
  last_backup_hash?: string | null;
  last_backup_type?: string | null;
  restore_test_status: 'passed' | 'failed' | 'pending' | 'untested';
  restore_test_notes: string;
}

export interface QueueHealth {
  pending_jobs_count: number;
  running_jobs_count: number;
  total_active_queue: number;
  oldest_queued_job_seconds?: number | null;
  queue_status: 'idle' | 'healthy' | 'busy' | 'congested';
}

export interface RecentJobItem {
  id: number;
  case_id: number;
  job_type: string;
  status: string;
  current_stage?: string | null;
  progress_pct: number;
  error_message?: string | null;
  duration_seconds?: number | null;
  created_at?: string | null;
}

export interface JobSuccessHealth {
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  running_jobs: number;
  success_rate_pct: number;
  failed_last_24h_count: number;
  recent_jobs: RecentJobItem[];
}

export interface SystemHealth {
  system_status: 'operational' | 'degraded' | 'critical';
  timestamp: string;
  uptime_seconds: number;
  db_size_mb: number;
  queue: QueueHealth;
  job_success: JobSuccessHealth;
  ai_services: AIServiceStatus[];
  backup: BackupHealth;
}

export interface ExhibitQualityPillars {
  text_confidence_score: number;
  text_confidence_pct: number;
  text_status: 'high' | 'medium' | 'low' | 'unextracted' | 'poor_audio' | string;
  text_notes: string;
  hash_score: number;
  hash_status: 'verified' | 'unverified' | 'mismatch' | string;
  hash_value?: string | null;
  certificate_score: number;
  certificate_status: 'certified' | 'missing' | 'pending' | string;
  certificate_notes: string;
  language_review_score: number;
  language_status: 'verified' | 'pending_review' | 'untranslated' | 'native_english' | string;
  primary_language: string;
  language_notes: string;
}

export interface ExhibitDataQualityItem {
  evidence_id: number;
  case_id: number;
  title: string;
  file_name: string;
  file_type: string;
  evidence_type: string;
  uploaded_by: string;
  upload_date?: string | null;
  overall_quality_score: number;
  quality_tier: string;
  is_weak_item: boolean;
  pillars: ExhibitQualityPillars;
  warning_flags: string[];
  recommended_action: string;
}

export interface CaseDataQualityReport {
  case_id: number;
  case_title: string;
  total_exhibits: number;
  average_quality_score: number;
  weak_exhibits_count: number;
  missing_certificates_count: number;
  unverified_hashes_count: number;
  low_confidence_text_count: number;
  pending_language_reviews_count: number;
  sorted_exhibits: ExhibitDataQualityItem[];
}

// ==============================================================================
// COMMAND PALETTE & GLOBAL OMNI-SEARCH TYPES
// ==============================================================================

export interface OmniSearchResultItem {
  id: string;
  category: 'exhibit' | 'entity' | 'claim' | 'quote' | 'suspect' | 'task' | 'alert' | 'command' | string;
  title: string;
  match_source: string;
  matched_snippet: string;
  highlight_term: string;
  char_start?: number | null;
  char_end?: number | null;
  page_number?: number | null;
  target_url: string;
  metadata?: Record<string, any>;
}

export interface OmniSearchResponse {
  query: string;
  case_id?: number | null;
  total_matches: number;
  matches: OmniSearchResultItem[];
}

export interface PaletteCommand {
  id: string;
  title: string;
  description: string;
  category: 'navigation' | 'investigation' | 'system' | 'forensics';
  action: () => void | Promise<void>;
  shortcut?: string;
  keywords?: string[];
  iconName: string;
}

// ==============================================================================
// TODAY'S PRIORITIES & OPERATIONAL DASHBOARD TYPES
// ==============================================================================

export interface ReportRequest {
  id: number;
  case_id: number;
  report_type: string;
  requested_from: string;
  requested_date: string;
  expected_date: string;
  received_date?: string | null;
  status: 'requested' | 'received' | 'overdue' | 'not_needed';
  linked_evidence_id?: number | null;
  reminder_date?: string | null;
  urgency: 'low' | 'medium' | 'high' | 'critical';
  days_waiting: number;
  is_overdue: boolean;
  notes?: string | null;
  created_at?: string | null;
}

export interface PersonRegister {
  id: number;
  case_id: number;
  name: string;
  role: string;
  contact_info?: string | null;
  linked_entity_id?: number | null;
  is_important: boolean;
  mention_count: number;
  notes?: string | null;
  statement_status: 'not_contacted' | 'summoned' | 'recorded' | 'untraceable' | 'refused' | 'scheduled';
  statement_type?: string | null;
  statement_id?: number | null;
  scheduled_date?: string | null;
  created_at?: string | null;
}

export interface StatementTracker {
  id: number;
  case_id: number;
  person_id: number;
  person_name?: string | null;
  person_role?: string | null;
  statement_type: string;
  status: string;
  scheduled_date?: string | null;
  recorded_date?: string | null;
  linked_evidence_id?: number | null;
  linked_interview_id?: number | null;
  summary?: string | null;
  key_claims?: string | null;
  notes?: string | null;
  created_at?: string | null;
}

export interface PriorityActionItem {
  id: string;
  type: 'deadline' | 'report' | 'witness' | 'review' | 'alert';
  title: string;
  reason: string;
  due_time?: string | null;
  severity: 'overdue' | 'critical' | 'urgent' | 'watch' | 'calm';
  days_left?: number | null;
  owner?: string | null;
  action_link: string;
  action_label: string;
  status: string;
  snoozed_until?: string | null;
}

export interface StatutoryClock {
  has_dates: boolean;
  chargesheet_limit_days: number;
  arrest_date?: string | null;
  remand_date?: string | null;
  chargesheet_deadline?: string | null;
  chargesheet_days_left?: number | null;
  chargesheet_hours_left?: number | null;
  chargesheet_band: 'overdue' | 'critical' | 'urgent' | 'watch' | 'calm' | 'missing_dates';
  chargesheet_legal_note: string;
  remand_deadline?: string | null;
  remand_days_left?: number | null;
  remand_hours_left?: number | null;
  remand_band: 'overdue' | 'critical' | 'urgent' | 'watch' | 'calm' | 'missing_dates';
  remand_legal_note: string;
  statutory_provision: string;
  extensions?: Array<{ date: string; granted_by: string; days: number; notes: string }>;
}

export interface PrioritiesSinceYouWereAway {
  headline: string;
  summary_sentence: string;
  hours_away: number;
  new_evidence_count: number;
  changed_hypotheses_count: number;
  unresolved_alerts_count: number;
  open_tasks_count: number;
  summary_points: string[];
}

export interface PendingReportsSection {
  total_requested: number;
  received_count: number;
  overdue_count: number;
  pending_count: number;
  items: ReportRequest[];
  unrequested_protocol_exhibits: Array<{
    item: string;
    description: string;
    mandatory: boolean;
    reason: string;
  }>;
}

export interface WitnessesSection {
  total_people: number;
  examined_count: number;
  unexamined_count: number;
  items: PersonRegister[];
  ai_suggested_persons: Array<{
    name: string;
    role: string;
    mention_count: number;
    reason: string;
    linked_entity_id?: number | null;
  }>;
}

export interface NeedsYourReviewItem {
  id: string;
  type: 'contradiction' | 'data_quality' | 'low_confidence_ocr' | 'unverified_citation' | 'signoff' | 'alert';
  title: string;
  reason: string;
  impact_score: number;
  severity: 'critical' | 'high' | 'medium' | 'low';
  action_link: string;
  action_label: string;
}

export interface NeedsYourReviewSection {
  total_items: number;
  items: NeedsYourReviewItem[];
}

export interface PrioritiesCaseSnapshot {
  exhibits_count: number;
  entities_count: number;
  hypotheses_count: number;
  timeline_events_count: number;
  top_hypothesis?: {
    id: number;
    title: string;
    probability: number;
    rank: number;
  } | null;
}

export interface PrioritiesResponse {
  case_id: number;
  case_title: string;
  fir_number: string;
  cached: boolean;
  updated_at: string;
  since_you_were_away: PrioritiesSinceYouWereAway;
  statutory_clock: StatutoryClock;
  action_items: PriorityActionItem[];
  pending_reports: PendingReportsSection;
  witnesses_and_statements: WitnessesSection;
  needs_your_review: NeedsYourReviewSection;
  case_snapshot: PrioritiesCaseSnapshot;
}

export interface GlobalCasePriority {
  case_id: number;
  case_title: string;
  fir_number: string;
  has_dates: boolean;
  chargesheet_days_left?: number | null;
  chargesheet_band: string;
  remand_days_left?: number | null;
  remand_band: string;
  overdue_reports_count: number;
  unexamined_witnesses_count: number;
  critical_review_items_count: number;
  top_urgency: 'overdue' | 'critical' | 'urgent' | 'watch' | 'calm' | 'missing_dates';
  next_action_title?: string | null;
  next_action_due?: string | null;
}

















