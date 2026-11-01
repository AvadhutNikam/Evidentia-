import { apiRequest } from './apiClient';

export interface ProposedField {
  field_key: string;
  field_label: string;
  field_group: 'people' | 'dates' | 'amounts' | 'places' | 'vehicles' | 'sections';
  value: any;
  confidence: number;
  confidence_tier: 'high' | 'check' | 'low';
  source_quote?: string;
  source_bbox?: { x: number; y: number; width: number; height: number };
  source_timestamp_sec?: number;
  is_ambiguous?: boolean;
  alternative_readings?: string[];
  statutory_ref?: string;
}

export interface IntakeItemModel {
  id: number;
  case_id: number;
  channel: 'fir_copy' | 'handwritten_statement' | 'voice_note' | 'whatsapp_export';
  title: string;
  original_file_name?: string;
  storage_path?: string;
  file_hash: string;
  file_size_bytes?: number;
  mime_type?: string;
  raw_text?: string;
  parsed_metadata: Record<string, any>;
  proposed_fields: ProposedField[];
  status: 'ready_for_review' | 'confirmed' | 'rejected' | 'needs_reingest';
  confirmed_by?: string;
  confirmed_at?: string;
  applied_entities_count: number;
  created_at: string;
}

export interface FieldConfirmation {
  field_key: string;
  field_group: string;
  action: 'confirm' | 'edit' | 'reject';
  confirmed_value?: any;
  ai_value?: any;
  correction_notes?: string;
  candidate_signals?: Record<string, any>;
}

export interface IntakeTrustMetrics {
  total_reviewed_fields: number;
  accepted_unchanged_count: number;
  edited_count: number;
  rejected_count: number;
  acceptance_rate_pct: number;
  top_correction_fields: Array<{ field_key: string; count: number }>;
}

export interface LegalTermModel {
  id: number;
  term_key: string;
  statute: string;
  section: string;
  english_label: string;
  hindi_label: string;
  marathi_label: string;
  plain_explanation: string;
  court_admissibility_notes?: string;
  required_certificates?: string;
}

export async function fetchIntakeItems(caseId: number, status?: string): Promise<IntakeItemModel[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : '';
  return apiRequest<IntakeItemModel[]>(`/cases/${caseId}/intake${query}`, {
    method: 'GET'
  });
}

export async function fetchIntakeItemById(caseId: number, intakeId: number): Promise<IntakeItemModel> {
  return apiRequest<IntakeItemModel>(`/cases/${caseId}/intake/${intakeId}`, {
    method: 'GET'
  });
}

export async function submitIntakeText(
  caseId: number,
  channel: string,
  title: string,
  rawText: string,
  submitterName: string
): Promise<IntakeItemModel> {
  return apiRequest<IntakeItemModel>(`/cases/${caseId}/intake/submit-text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      case_id: caseId,
      channel,
      title,
      raw_text: rawText,
      submitter_name: submitterName
    })
  });
}

export async function uploadIntakeFile(
  caseId: number,
  channel: string,
  title: string,
  file: File,
  submitterName: string
): Promise<IntakeItemModel> {
  const formData = new FormData();
  formData.append('case_id', String(caseId));
  formData.append('channel', channel);
  formData.append('title', title);
  formData.append('submitter_name', submitterName);
  formData.append('file', file);

  return apiRequest<IntakeItemModel>(`/cases/${caseId}/intake/upload`, {
    method: 'POST',
    body: formData
  });
}

export async function confirmIntakeItem(
  caseId: number,
  intakeId: number,
  userId: number,
  userName: string,
  confirmations: FieldConfirmation[],
  applyToCaseDiary: boolean = true
): Promise<IntakeItemModel> {
  return apiRequest<IntakeItemModel>(`/cases/${caseId}/intake/${intakeId}/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      user_name: userName,
      confirmations,
      apply_to_case_diary: applyToCaseDiary
    })
  });
}

export async function rejectIntakeItem(
  caseId: number,
  intakeId: number,
  userName: string,
  reason: string
): Promise<IntakeItemModel> {
  return apiRequest<IntakeItemModel>(`/cases/${caseId}/intake/${intakeId}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      rejection_reason: reason,
      user_name: userName
    })
  });
}

export async function fetchIntakeMetrics(caseId: number): Promise<IntakeTrustMetrics> {
  return apiRequest<IntakeTrustMetrics>(`/cases/${caseId}/intake-metrics`, {
    method: 'GET'
  });
}

export async function fetchLegalGlossary(): Promise<LegalTermModel[]> {
  return apiRequest<LegalTermModel[]>('/legal-glossary', {
    method: 'GET'
  });
}
