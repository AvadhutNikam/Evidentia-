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
  disconfirmation_penalty?: number;
  disconfirmationPenalty?: number;
  relative_likelihood?: number;
  relativeLikelihood?: number;
  supportingEvidenceIds: string[];
  contradictingEvidenceIds: string[];
  relatedEntityIds?: string[];
  assessments?: EvidenceAssessment[];
  assessment_count?: number;
  created_at?: string;
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
  caseId: string;
  task: string;
  reason: string;
  relatedHypothesisId?: string;
  relatedContradictionId?: string;
  relatedEvidenceId?: string;
  priority: 'High' | 'Medium' | 'Low';
  status: 'Pending' | 'In Progress' | 'Completed';
  assignedTo?: string;
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

export interface BenchmarkReport {
  benchmark_timestamp: string;
  total_cases: number;
  scorable_cases: number;
  contested_cases: number;
  multi_run_iterations: number;
  metrics_summary: BenchmarkMethodMetric[];
  per_case_breakdowns: BenchmarkCaseBreakdown[];
  sensitivity_aggregate: BenchmarkSensitivityAggregate;
  sensitivity_case_summaries: any[];
  error_and_limitation_analysis: {
    unresolved_case_notes: string;
    synthetic_trap_performance: string;
    diagnosticity_ablation_finding: string;
    calibration_finding: string;
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
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in_minutes: number;
  user: UserOut;
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




