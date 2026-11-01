import { apiRequest } from './apiClient';
import { isDemoMode } from '../config/api';

export interface PoliceStationLookup {
  id: number;
  name: string;
  district: string;
  state: string;
  station_code: string;
}

export interface CaseParticularsData {
  case_id: number;
  title: string;
  fir_number?: string;
  crime_number?: string;
  police_station?: string;
  district?: string;
  state?: string;
  investigating_officer_id?: number | null;
  investigating_officer_name?: string;
  supervising_officer_id?: number | null;
  supervising_officer_name?: string;
  court_name?: string;
  next_hearing_date?: string | null;
  next_hearing_purpose?: string;
  bail_status?: string;
  custody_status?: string;
  case_stage?: string;
  fir_date?: string | null;
  incident_date?: string | null;
  arrest_date?: string | null;
  remand_date?: string | null;
  offence_section?: string;
  statutory_time_limit_days: number;
  version: number;
  consistency_warnings: string[];
  per_accused_clocks: AccusedClockItem[];
}

export interface AccusedClockItem {
  person_id: number;
  name: string;
  aliases?: string;
  current_status: string;
  order_reference?: string;
  arrest_date?: string;
  chargesheet_deadline?: string;
  chargesheet_days_left?: number;
  chargesheet_band: 'calm' | 'watch' | 'urgent' | 'critical' | 'overdue' | 'missing_dates';
  remand_deadline?: string;
  remand_days_left?: number;
  is_custody_active: boolean;
}

export interface CasePersonItem {
  id: number;
  case_id: number;
  name: string;
  aliases?: string;
  role: 'complainant' | 'victim' | 'accused' | 'witness' | 'expert' | 'informant' | 'other';
  father_or_spouse_name?: string;
  age?: number;
  gender?: string;
  contact_info?: string;
  address?: string;
  is_important: boolean;
  linked_entity_id?: number;
  notes?: string;
  statements_count: number;
  latest_status?: string;
  created_at?: string;
}

export interface PersonStatementItem {
  id: number;
  case_id: number;
  person_id: number;
  person_name?: string;
  statement_type: string;
  status: string;
  statement_date: string;
  statement_time?: string;
  place?: string;
  recorded_by?: string;
  language?: string;
  read_over_and_signed: boolean;
  magistrate_name?: string;
  linked_evidence_id?: number;
  linked_interview_id?: number;
  statement_text?: string;
  key_claims?: string;
  notes?: string;
}

export interface DocumentTypeItem {
  id: number;
  code: string;
  label: string;
  legal_provision: string;
  category: string;
  required_fields: Array<{ key: string; label: string; type: string; required: boolean }>;
  standard_guidance?: string;
}

export interface TypedDocumentItem {
  evidence_id: number;
  file_name: string;
  evidence_type: string;
  document_type: string;
  type_details: Record<string, any>;
  completeness_pct: number;
  is_complete: boolean;
  missing_required_fields: Array<{ key: string; label: string }>;
  gap_reasons: string[];
  legal_guidance?: string;
  upload_date?: string;
}

export interface CaseDiaryItem {
  id: number;
  case_id: number;
  entry_date: string;
  serial_number: number;
  time_from?: string;
  time_to?: string;
  place?: string;
  officer_name: string;
  activities: string;
  persons_examined: Array<{ name: string; role?: string; type?: string }>;
  places_visited: string[];
  items_seized: Array<{ title: string; type?: string }>;
  instructions_given?: string;
  next_steps?: string;
  status: 'draft' | 'signed' | 'locked';
  signature_timestamp?: string;
  signature_hash?: string;
  supervisor_notes?: string;
}

export interface CaseSectionItem {
  id: number;
  case_id: number;
  act: string;
  section_code: string;
  description: string;
  punishment_tier: string;
  status: string;
  reason?: string;
  deciding_officer?: string;
  effective_date?: string;
  supervisor_approval: boolean;
  supervisor_notes?: string;
  court_informed_date?: string;
  court_intimation_memo?: string;
  elements: Array<{
    id: number;
    case_section_id: number;
    element_text: string;
    supporting_evidence_ids: number[];
    status: 'supported' | 'partial' | 'missing';
    notes?: string;
  }>;
}

export const caseFileService = {
  getParticulars: async (caseId: string | number): Promise<CaseParticularsData> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    try {
      return await apiRequest<CaseParticularsData>(`/cases/${cleanId}/particulars`);
    } catch (err) {
      if (isDemoMode()) {
        return getMockParticulars(Number(cleanId) || 1);
      }
      throw err;
    }
  },

  updateParticulars: async (caseId: string | number, data: Partial<CaseParticularsData>): Promise<any> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest(`/cases/${cleanId}/particulars`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
  },

  getPoliceStations: async (): Promise<PoliceStationLookup[]> => {
    try {
      return await apiRequest<PoliceStationLookup[]>('/police-stations');
    } catch (err) {
      return [
        { id: 1, name: 'Yerwada Police Station', district: 'Pune City', state: 'Maharashtra', station_code: 'PUN-YER-01' },
        { id: 2, name: 'Khadki Police Station', district: 'Pune City', state: 'Maharashtra', station_code: 'PUN-KHD-02' },
        { id: 3, name: 'Bund Garden Police Station', district: 'Pune City', state: 'Maharashtra', station_code: 'PUN-BGD-03' },
        { id: 4, name: 'Hinjewadi Police Station', district: 'Pimpri-Chinchwad', state: 'Maharashtra', station_code: 'PCMC-HNJ-01' },
        { id: 5, name: 'Sector 20 Police Station', district: 'Gautam Buddha Nagar', state: 'Uttar Pradesh', station_code: 'UP-NOI-01' }
      ];
    }
  },

  getPersons: async (caseId: string | number): Promise<CasePersonItem[]> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    try {
      return await apiRequest<CasePersonItem[]>(`/cases/${cleanId}/persons`);
    } catch (err) {
      if (isDemoMode()) return [];
      throw err;
    }
  },

  createPerson: async (caseId: string | number, data: Partial<CasePersonItem>): Promise<CasePersonItem> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest<CasePersonItem>(`/cases/${cleanId}/persons`, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  getAccusedClocks: async (caseId: string | number): Promise<AccusedClockItem[]> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest<AccusedClockItem[]>(`/cases/${cleanId}/accused-clocks`);
  },

  recordAccusedStatus: async (caseId: string | number, data: any): Promise<any> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest(`/cases/${cleanId}/accused-status`, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  getStatements: async (caseId: string | number, personId?: number): Promise<PersonStatementItem[]> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    const pParam = personId ? `?person_id=${personId}` : '';
    return await apiRequest<PersonStatementItem[]>(`/cases/${cleanId}/person-statements${pParam}`);
  },

  recordStatement: async (caseId: string | number, data: any): Promise<PersonStatementItem> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest<PersonStatementItem>(`/cases/${cleanId}/person-statements`, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  getStatementImprovements: async (caseId: string | number, personId: number): Promise<any> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest(`/cases/${cleanId}/persons/${personId}/statement-improvements`);
  },

  getDocumentTypes: async (): Promise<DocumentTypeItem[]> => {
    return await apiRequest<DocumentTypeItem[]>('/document-types');
  },

  getTypedDocuments: async (caseId: string | number): Promise<TypedDocumentItem[]> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest<TypedDocumentItem[]>(`/cases/${cleanId}/typed-documents`);
  },

  updateTypedDocument: async (caseId: string | number, evidenceId: number, data: any): Promise<any> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest(`/cases/${cleanId}/evidence/${evidenceId}/typed-document`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
  },

  getDiaryEntries: async (caseId: string | number): Promise<CaseDiaryItem[]> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest<CaseDiaryItem[]>(`/cases/${cleanId}/diary`);
  },

  getDiaryAutoDraft: async (caseId: string | number, entryDate?: string): Promise<any> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    const dParam = entryDate ? `?entry_date=${entryDate}` : '';
    return await apiRequest(`/cases/${cleanId}/diary/auto-draft${dParam}`);
  },

  saveDiaryEntry: async (caseId: string | number, data: any): Promise<CaseDiaryItem> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest<CaseDiaryItem>(`/cases/${cleanId}/diary`, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  signDiaryEntry: async (caseId: string | number, entryId: number): Promise<CaseDiaryItem> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest<CaseDiaryItem>(`/cases/${cleanId}/diary/${entryId}/sign`, {
      method: 'POST'
    });
  },

  getSections: async (caseId: string | number): Promise<CaseSectionItem[]> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest<CaseSectionItem[]>(`/cases/${cleanId}/sections`);
  },

  addSection: async (caseId: string | number, data: any): Promise<CaseSectionItem> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest<CaseSectionItem>(`/cases/${cleanId}/sections`, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  updateSection: async (caseId: string | number, sectionId: number, data: any): Promise<any> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest(`/cases/${cleanId}/sections/${sectionId}`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
  },

  importFIR: async (caseId: string | number, firText: string, autoSave = false): Promise<any> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest(`/cases/${cleanId}/fir-import`, {
      method: 'POST',
      body: JSON.stringify({ fir_text: firText, auto_save: autoSave })
    });
  }
};

function getMockParticulars(caseId: number): CaseParticularsData {
  return {
    case_id: caseId,
    title: 'State of Maharashtra vs. Yogesh Raut & Ors',
    fir_number: 'FIR-452/2009',
    crime_number: 'CR No. 142/2009',
    police_station: 'Yerwada Police Station',
    district: 'Pune City',
    state: 'Maharashtra',
    investigating_officer_name: 'Inspector Kishor Mhaswade',
    supervising_officer_name: 'ACP Sanjeev Bhor',
    court_name: 'Chief Judicial Magistrate Special Sessions Court, Pune',
    next_hearing_date: '2010-01-15T11:00:00Z',
    next_hearing_purpose: 'Judicial Custody Remand Review',
    bail_status: 'Rejected',
    custody_status: 'Judicial Custody',
    case_stage: 'under_investigation',
    fir_date: '2009-10-08T14:30:00Z',
    incident_date: '2009-10-07T21:15:00Z',
    arrest_date: '2009-10-16T10:00:00Z',
    remand_date: '2009-10-18T14:00:00Z',
    offence_section: '103(1) BNS / 302 IPC, 64 BNS / 376(2)(g) IPC, 309 BNS / 392 IPC, 3(5) BNS / 34 IPC',
    statutory_time_limit_days: 90,
    version: 1,
    consistency_warnings: [],
    per_accused_clocks: []
  };
}

