/**
 * src/services/physicalEvidenceService.ts
 * =======================================
 * Client service for Physical Evidence Tracking, Extended Chained Custody,
 * Tamper-Evident Seals, Station Malkhana Register, and FSL Dispatches.
 */

import { apiRequest } from './apiClient';

export interface PhysicalItem {
  id: number;
  evidence_id: number;
  case_id: number;
  category: 'weapon' | 'clothing' | 'biological_sample' | 'vehicle' | 'device' | 'narcotics' | 'cash_valuables' | 'document_original' | 'other';
  description: string;
  identifying_marks?: string;
  quantity_or_weight?: string;
  condition: string;
  packaging: string;
  seized_from?: string;
  seized_at?: string;
  seized_by_id?: number;
  seized_by_name?: string;
  seizure_memo_id?: number;
  panch_witness_1_id?: number;
  panch_witness_2_id?: number;
  current_location: string;
  current_custodian?: string;
  malkhana_entry_number?: string;
  rack_or_shelf?: string;
  status: 'seized' | 'deposited_malkhana' | 'issued_investigation' | 'dispatched_fsl' | 'returned_from_fsl' | 'produced_court' | 'returned_to_owner' | 'disposed';
  is_perishable: boolean;
  is_biological: boolean;
  is_firearm: boolean;
  is_narcotics: boolean;
  dispatch_time_limit_days?: number;
  created_at: string;
}

export interface CustodyLogExtended {
  id: number;
  evidence_id: number;
  case_id: number;
  action: string;
  actor_name: string;
  actor_role?: string;
  source_agency?: string;
  location?: string;
  timestamp: string;
  notes?: string;
  from_person_id?: number;
  from_person_name?: string;
  from_location?: string;
  to_person_id?: number;
  to_person_name?: string;
  to_location?: string;
  purpose?: string;
  condition_at_handover?: string;
  seal_status_check?: string;
  expected_return_date?: string;
  authority_order_ref?: string;
  acknowledgement_type?: string;
  attached_photos?: string;
  previous_log_hash?: string;
  current_log_hash?: string;
}

export interface ContinuityIssue {
  type: string;
  severity: 'critical' | 'warning' | 'info';
  step_index?: number;
  message: string;
}

export interface ContinuityCheck {
  evidence_id: number;
  evidence_kind: string;
  status: 'complete' | 'gap' | 'seal_issue';
  chain_of_custody_complete: boolean;
  hash_chain_valid: boolean;
  reliability_penalty: number;
  total_custody_entries: number;
  issues: ContinuityIssue[];
  last_action?: string;
  last_timestamp?: string;
  current_custodian?: string;
  current_location?: string;
}

export interface Seal {
  id: number;
  case_id: number;
  evidence_id: number;
  seal_number: string;
  owner_mark: string;
  package_description?: string;
  applied_by_name: string;
  applied_at: string;
  status: 'intact' | 'broken_authorized' | 'broken_unauthorized' | 'resealed';
  replaced_seal_id?: number;
  created_at: string;
}

export interface MalkhanaRegisterItem {
  id: number;
  evidence_id: number;
  case_id: number;
  crime_number: string;
  case_title: string;
  category: string;
  description: string;
  identifying_marks?: string;
  quantity_or_weight?: string;
  condition: string;
  packaging: string;
  current_location: string;
  current_custodian?: string;
  malkhana_entry_number?: string;
  rack_or_shelf?: string;
  status: string;
  seal_number?: string;
  seal_status: string;
  is_biological: boolean;
  is_perishable: boolean;
  is_firearm: boolean;
  is_narcotics: boolean;
  created_at?: string;
}

export interface FSLDispatchItem {
  id: number;
  dispatch_id: number;
  evidence_id: number;
  seal_number_at_dispatch: string;
  seal_status_at_dispatch: string;
  return_seal_number?: string;
  return_seal_status?: string;
  condition_on_return?: string;
}

export interface FSLDispatch {
  id: number;
  case_id: number;
  forwarding_letter_number: string;
  forwarding_letter_date: string;
  fsl_name: string;
  examination_requested: string;
  sent_date: string;
  carried_by_name: string;
  carried_by_role?: string;
  carried_by_id_card?: string;
  mode_of_transit: string;
  expected_report_date?: string;
  status: 'prepared' | 'dispatched' | 'received_by_lab' | 'under_examination' | 'report_issued' | 'items_returned' | 'closed';
  lab_acknowledgement_receipt_path?: string;
  lab_acknowledgement_date?: string;
  report_evidence_id?: number;
  return_date?: string;
  return_carried_by?: string;
  items: FSLDispatchItem[];
}

export interface CourtCertificate {
  certificate_title: string;
  legal_provision: string;
  crime_number: string;
  police_station: string;
  court_name: string;
  evidence_id: number;
  exhibit_kind: string;
  category: string;
  description: string;
  identifying_marks: string;
  malkhana_entry_number: string;
  continuity_status: string;
  hash_chain_verified: boolean;
  total_transfers: number;
  certifying_officer: string;
  generation_timestamp: string;
  ledger: Array<{
    step: number;
    action: string;
    timestamp: string;
    actor: string;
    from_location: string;
    to_location: string;
    to_person: string;
    seal_status: string;
    hash: string;
  }>;
}

export const physicalEvidenceService = {
  getPhysicalEvidence: async (caseId: string | number): Promise<PhysicalItem[]> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest<PhysicalItem[]>(`/cases/${cleanId}/physical-evidence`);
  },

  getPhysicalEvidenceDetails: async (evidenceId: number): Promise<PhysicalItem> => {
    return await apiRequest<PhysicalItem>(`/physical-evidence/${evidenceId}`);
  },

  registerPhysicalEvidence: async (
    caseId: string | number,
    payload: {
      category: string;
      description: string;
      identifying_marks?: string;
      quantity_or_weight?: string;
      condition?: string;
      packaging?: string;
      seized_from?: string;
      seized_at?: string;
      seized_by_name?: string;
      current_location?: string;
      current_custodian?: string;
      malkhana_entry_number?: string;
      rack_or_shelf?: string;
      is_perishable?: boolean;
      is_biological?: boolean;
      is_firearm?: boolean;
      is_narcotics?: boolean;
      dispatch_time_limit_days?: number;
    }
  ): Promise<PhysicalItem> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest<PhysicalItem>(`/cases/${cleanId}/physical-evidence`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  recordCustodyTransfer: async (
    evidenceId: number,
    payload: {
      action: string;
      to_person_name: string;
      to_location: string;
      from_location?: string;
      purpose?: string;
      condition_at_handover?: string;
      seal_status_check?: string;
      expected_return_date?: string;
      authority_order_ref?: string;
      notes?: string;
    }
  ): Promise<CustodyLogExtended> => {
    return await apiRequest<CustodyLogExtended>(`/physical-evidence/${evidenceId}/custody-handover`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  checkContinuity: async (evidenceId: number): Promise<ContinuityCheck> => {
    return await apiRequest<ContinuityCheck>(`/physical-evidence/${evidenceId}/continuity`);
  },

  getCustodyLedger: async (evidenceId: number): Promise<CustodyLogExtended[]> => {
    return await apiRequest<CustodyLogExtended[]>(`/evidence/${evidenceId}/custody-ledger`);
  },

  getSeals: async (evidenceId: number): Promise<Seal[]> => {
    return await apiRequest<Seal[]>(`/physical-evidence/${evidenceId}/seals`);
  },

  createSeal: async (
    evidenceId: number,
    payload: {
      seal_number: string;
      owner_mark: string;
      package_description?: string;
      applied_in_presence_of?: string[];
      photos?: any[];
    }
  ): Promise<Seal> => {
    return await apiRequest<Seal>(`/physical-evidence/${evidenceId}/seals`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  recordSealEvent: async (
    sealId: number,
    payload: {
      event_type: 'inspect' | 'break' | 'reseal';
      reason: string;
      witnesses?: string[];
      photos?: any[];
      new_seal_data?: { seal_number: string; owner_mark?: string };
    }
  ): Promise<any> => {
    return await apiRequest<any>(`/seals/${sealId}/events`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  compareOCRSeal: async (claimedSeal: string, ocrDetectedText: string): Promise<any> => {
    return await apiRequest<any>('/physical-evidence/ocr-compare', {
      method: 'POST',
      body: JSON.stringify({ claimed_seal: claimedSeal, ocr_detected_text: ocrDetectedText }),
    });
  },

  getMalkhanaRegister: async (
    station: string = 'Yerawada Police Station',
    caseId?: number,
    status?: string
  ): Promise<MalkhanaRegisterItem[]> => {
    const params = new URLSearchParams({ police_station: station });
    if (caseId) params.append('case_id', String(caseId));
    if (status) params.append('status', status);
    return await apiRequest<MalkhanaRegisterItem[]>(`/malkhana/register?${params.toString()}`);
  },

  depositMalkhana: async (
    evidenceId: number,
    payload: {
      malkhana_entry_number: string;
      rack_or_shelf: string;
      depositor_name: string;
      condition?: string;
      seal_status?: string;
      photos?: any[];
    }
  ): Promise<any> => {
    return await apiRequest<any>(`/malkhana/deposit?evidence_id=${evidenceId}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  issueMalkhana: async (
    evidenceId: number,
    payload: {
      purpose: string;
      destination_location: string;
      taken_by_name: string;
      approver_id: number;
      expected_return_date?: string;
      authority_order_ref?: string;
      seal_check?: string;
      notes?: string;
    }
  ): Promise<any> => {
    return await apiRequest<any>(`/malkhana/issue?evidence_id=${evidenceId}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  getBarcodeLabel: async (evidenceId: number): Promise<{ evidence_id: number; crime_number: string; malkhana_entry_number: string; seal_number: string; svg: string }> => {
    return await apiRequest<any>(`/physical-evidence/${evidenceId}/barcode-label`);
  },

  getFSLDispatches: async (caseId: string | number): Promise<FSLDispatch[]> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest<FSLDispatch[]>(`/cases/${cleanId}/fsl-dispatches`);
  },

  createFSLDispatch: async (
    caseId: string | number,
    payload: {
      forwarding_letter_number: string;
      forwarding_letter_date: string;
      fsl_name: string;
      examination_requested: string;
      carried_by_name: string;
      carried_by_role?: string;
      carried_by_id_card?: string;
      mode_of_transit: string;
      expected_report_date?: string;
      item_evidence_ids: number[];
    }
  ): Promise<FSLDispatch> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest<FSLDispatch>(`/cases/${cleanId}/fsl-dispatches`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  getCourtCustodyCertificate: async (evidenceId: number): Promise<CourtCertificate> => {
    return await apiRequest<CourtCertificate>(`/physical-evidence/${evidenceId}/court-certificate`);
  },
};

