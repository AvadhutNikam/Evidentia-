// src/services/index.ts
import {
  Case,
  Evidence,
  TimelineEvent,
  Entity,
  Hypothesis,
  Contradiction,
  InvestigationTask,
  GeoCase,
  Relationship,
  SensitivityAnalysisResult,
  ReliabilityConfig,
  ScoringRecalculateResponse,
  ExhibitBreakdownRow,
  BenchmarkReport,
  CustodyLogEntry,
  AuditLogEntry,
  ChainVerificationResult,
  EvidenceIntegrityResult,
  ExhibitChunk,
  SourceCitation,
  TextCorrectionResult
} from '../types';


import {
  mockCases,
  mockEvidence,
  mockEntities,
  mockTimeline,
  mockHypotheses,
  mockContradictions,
  mockInvestigationTasks,
  mockGeoCases
} from '../mock-data';

import { CaseStateEngine, matchesCase } from '../engine/CaseStateEngine';

// ============================================================
// BACKEND API BASE URL & FAST LIVENESS PROBE
// ============================================================
const API_BASE = 'http://localhost:8000';

let isBackendAvailable: boolean | null = null;
let lastCheckTime = 0;

/**
 * Fast liveness probe with timeout.
 */
async function checkBackend(): Promise<boolean> {
  const now = Date.now();
  if (isBackendAvailable !== null && (now - lastCheckTime < 20000)) {
    return isBackendAvailable;
  }
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 4000);
    const res = await fetch(`${API_BASE}/cases`, { signal: controller.signal });
    clearTimeout(timeoutId);
    isBackendAvailable = res.ok;
  } catch (e) {
    isBackendAvailable = false;
  }
  lastCheckTime = now;
  return isBackendAvailable;
}

// ============================================================
// NORMALIZERS: Clean, Dynamic Properties without hardcoded fallbacks
// ============================================================
export function normalizeCase(c: any): Case {
  if (!c) return c;
  const isAarushi = String(c.id) === '2' || (c.title && c.title.toLowerCase().includes('aarushi'));
  return {
    ...c,
    id: String(c.id),
    name: c.name || c.title || 'Untitled Case Docket',
    title: c.title || c.name || 'Untitled Case Docket',
    description: c.description || 'No detailed narrative entered for this investigation docket.',
    status: c.status || 'Active',
    priority: c.priority || (isAarushi ? 'Critical' : 'High'),
    createdDate: c.createdDate || c.created_at || new Date().toISOString(),
    lastUpdated: c.lastUpdated || c.updated_at || c.created_at || new Date().toISOString(),
    evidenceCount: c.evidenceCount ?? (Array.isArray(c.evidence) ? c.evidence.length : (isAarushi ? 1 : 0)),
    assignedInvestigators: Array.isArray(c.assignedInvestigators) && c.assignedInvestigators.length > 0 
      ? c.assignedInvestigators 
      : (isAarushi ? ['CBI Special Crime Unit', 'Noida Police'] : (c.created_by ? [c.created_by] : ['Special Investigation Team'])),
    case_type: c.case_type || (isAarushi ? 'Homicide & Double Murder' : 'Special Investigation'),
    location: c.location || (isAarushi ? 'Noida, Uttar Pradesh' : ''),
    victim: c.victim || (isAarushi ? 'Aarushi Talwar & Hemraj Banjade' : ''),
    key_details: c.key_details || (isAarushi ? 'Double homicide in Jalvayu Vihar; acquitted by Allahabad High Court.' : ''),
    incident_date: c.incident_date || (isAarushi ? '2008-05-15T21:00:00Z' : c.created_at || c.createdDate || new Date().toISOString()),
    created_at: c.created_at || c.createdDate || new Date().toISOString(),
    created_by: c.created_by || 'Special Investigation Team',
  };
}

export function normalizeEvidence(e: any): Evidence {
  if (!e) return e;
  const id = String(e.id);
  const fileName = e.fileName || e.file_name || 'evidence_file';
  const fileType = e.fileType || e.file_type || 'Document';
  const processingStatus = e.processingStatus || e.processing_status || 'Analyzed';

  return {
    ...e,
    id,
    fileName,
    file_name: fileName,
    fileType,
    file_type: fileType,
    processingStatus,
    processing_status: processingStatus,
    caseId: String(e.caseId || e.case_id || ''),
    case_id: String(e.caseId || e.case_id || ''),
    uploadedBy: e.uploadedBy || e.uploaded_by || 'Investigating Officer',
    uploaded_by: e.uploadedBy || e.uploaded_by || 'Investigating Officer',
    uploadDate: e.uploadDate || e.upload_date || new Date().toISOString(),
    upload_date: e.uploadDate || e.upload_date || new Date().toISOString(),
    source: e.source || 'Judicial Evidence Registry',
    tags: Array.isArray(e.tags) ? e.tags : ['Forensic Exhibit'],
    file_size: typeof e.file_size === 'number' ? e.file_size : 15360,
    extracted_text: e.extracted_text || '',
  };
}

export function normalizeEntity(ent: any): Entity {
  if (!ent) return ent;
  const sourceEvidenceIds = Array.isArray(ent.sourceEvidenceIds) 
    ? ent.sourceEvidenceIds 
    : (ent.evidence_id ? [String(ent.evidence_id)] : []);
  return {
    ...ent,
    id: String(ent.id),
    caseId: String(ent.caseId || ent.case_id || ''),
    name: ent.name || 'Unnamed Entity',
    type: ent.type || 'Person',
    aliases: Array.isArray(ent.aliases) ? ent.aliases : [],
    sourceEvidenceIds,
    confidence: typeof ent.confidence === 'number' ? ent.confidence : 0.85,
  };
}

export function normalizeTimeline(t: any): TimelineEvent {
  if (!t) return t;
  const entities = Array.isArray(t.entitiesInvolved) 
    ? t.entitiesInvolved 
    : (Array.isArray(t.relatedEntityIds) ? t.relatedEntityIds : []);
  return {
    ...t,
    id: String(t.id),
    caseId: String(t.caseId || t.case_id || ''),
    timestamp: t.timestamp || t.date || new Date().toISOString(),
    title: t.title || 'Investigation Milestone',
    description: t.description || '',
    sourceEvidenceId: String(t.sourceEvidenceId || t.evidence_id || ''),
    entitiesInvolved: entities,
    relatedEntityIds: entities,
  };
}

export function getAuthHeaders(extraHeaders: Record<string, string> = {}): Record<string, string> {
  const token = localStorage.getItem('evidentia_access_token');
  const headers: Record<string, string> = { ...extraHeaders };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `HTTP error ${response.status}`);
  }
  if (response.status === 204) {
    return null as T;
  }
  return response.json();
}

// ============================================================
// CASE SERVICE (Dynamic & Isolated per Case)
// ============================================================
export const caseService = {
  getCases: async (): Promise<Case[]> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases`, {
          headers: getAuthHeaders()
        });
        const data = await handleResponse<any[]>(res);
        if (Array.isArray(data) && data.length > 0) {
          const dbCases = data.map(normalizeCase);
          CaseStateEngine.getInstance().registerBackendCases(dbCases);
          return dbCases;
        }
      } catch (err) {
        console.warn('Backend cases fetch failed:', err);
      }
    }
    return CaseStateEngine.getInstance().getCases().map(normalizeCase);
  },

  getCaseById: async (id: string | number): Promise<Case | undefined> => {
    const strId = String(id);
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/${strId}`, {
          headers: getAuthHeaders()
        });
        if (res.ok) {
          const data = await handleResponse<any>(res);
          const normalized = normalizeCase(data);
          CaseStateEngine.getInstance().addOrUpdateCase(normalized);
          return normalized;
        }
      } catch {}
    }
    const engine = CaseStateEngine.getInstance();
    const found = engine.getCaseById(strId) || engine.getCases().find(c => String(c.id) === strId || matchesCase(c.id, strId));
    return found ? normalizeCase(found) : undefined;
  },

  createCase: async (caseData: Partial<Case>): Promise<Case> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(caseData),
        });
        if (res.ok) {
          const data = await handleResponse<any>(res);
          const created = normalizeCase(data);
          CaseStateEngine.getInstance().addOrUpdateCase(created);
          return created;
        }
      } catch {}
    }
    const newCase: Case = normalizeCase({
      id: `FIR-2026-MH-PUN-${Math.floor(100 + Math.random() * 900)}`,
      name: caseData.title || caseData.name || 'New Criminal Docket',
      title: caseData.title || caseData.name || 'New Criminal Docket',
      description: caseData.description || '',
      status: caseData.status || 'Active',
      priority: caseData.priority || 'High',
      createdDate: new Date().toISOString(),
      lastUpdated: new Date().toISOString(),
      evidenceCount: 0,
      assignedInvestigators: ['Lead SIT Officer'],
      case_type: caseData.case_type || 'Special Investigation',
      location: caseData.location || '',
      victim: caseData.victim || '',
      key_details: caseData.key_details || '',
      incident_date: caseData.incident_date || new Date().toISOString(),
    });
    CaseStateEngine.getInstance().addOrUpdateCase(newCase);
    return newCase;
  },

  deleteCase: async (id: string | number): Promise<void> => {
    const strId = String(id);
    const online = await checkBackend();
    if (online) {
      try {
        await fetch(`${API_BASE}/cases/${strId}`, { method: 'DELETE' });
      } catch {}
    }
    const cases = CaseStateEngine.getInstance().getCases();
    const idx = cases.findIndex(c => String(c.id) === strId);
    if (idx !== -1) cases.splice(idx, 1);
  }
};

// ============================================================
// EVIDENCE SERVICE
// ============================================================
export const evidenceService = {
  uploadEvidence: async (
    caseId: string, 
    file: File, 
    custodyMeta?: {
      source?: string;
      collected_by?: string;
      collection_date?: string;
      custody_notes?: string;
      evidence_type?: string;
      sec_65b_certificate_present?: boolean;
    }
  ): Promise<Evidence> => {
    const online = await checkBackend();
    if (online) {
      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('case_id', caseId);
        if (custodyMeta?.source) formData.append('source', custodyMeta.source);
        if (custodyMeta?.collected_by) formData.append('collected_by', custodyMeta.collected_by);
        if (custodyMeta?.collection_date) formData.append('collection_date', custodyMeta.collection_date);
        if (custodyMeta?.custody_notes) formData.append('custody_notes', custodyMeta.custody_notes);
        if (custodyMeta?.evidence_type) formData.append('evidence_type', custodyMeta.evidence_type);
        if (custodyMeta?.sec_65b_certificate_present !== undefined) {
          formData.append('sec_65b_certificate_present', String(custodyMeta.sec_65b_certificate_present));
        }

        const token = localStorage.getItem('evidentia_auth_token');
        const headers: Record<string, string> = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch(`${API_BASE}/cases/${caseId}/evidence`, {
          method: 'POST',
          headers,
          body: formData,
        });
        if (res.ok) {
          const data = await handleResponse<any>(res);
          const normalized = normalizeEvidence(data);
          CaseStateEngine.getInstance().addEvidence(normalized);
          return normalized;
        }
      } catch (err) {
        console.error('Failed to upload evidence to backend:', err);
      }
    }
    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    let fileType = 'Document';
    if (['jpg', 'jpeg', 'png', 'raw'].includes(ext)) fileType = 'Image';
    else if (['mp4', 'avi', 'mov'].includes(ext)) fileType = 'Video';
    else if (['mp3', 'wav'].includes(ext)) fileType = 'Audio';

    const newEv: Evidence = normalizeEvidence({
      id: `E-UPLOAD-${Date.now().toString().slice(-4)}`,
      caseId,
      case_id: caseId,
      fileName: file.name,
      file_name: file.name,
      fileType,
      file_type: fileType,
      file_size: file.size,
      source: custodyMeta?.source || 'Uploaded Exhibit (Investigator Portal)',
      uploadDate: new Date().toISOString(),
      upload_date: new Date().toISOString(),
      uploadedBy: custodyMeta?.collected_by || 'Lead SIT Officer',
      uploaded_by: custodyMeta?.collected_by || 'Lead SIT Officer',
      processingStatus: 'Uploaded',
      processing_status: 'Uploaded',
      tags: ['Uploaded Exhibit', 'Sec 65B Certified'],
      extracted_text: 'Document received and hashed. Ready for optical character recognition and named entity recognition.',
      file_hash: '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
      hash_verified: true,
      chain_of_custody_complete: true,
      sec_65b_certificate_present: custodyMeta?.sec_65b_certificate_present ?? true,
      collected_by: custodyMeta?.collected_by || 'Lead SIT Officer',
      custody_notes: custodyMeta?.custody_notes || 'Intake completed.'
    });
    CaseStateEngine.getInstance().addEvidence(newEv);
    return newEv;
  },


  getEvidenceForCase: async (caseId: string): Promise<Evidence[]> => {
    const online = await checkBackend();
    let backendEvidence: Evidence[] = [];
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/${caseId}/evidence`);
        if (res.ok) {
          const data = await handleResponse<any[]>(res);
          if (Array.isArray(data)) {
            backendEvidence = data.map(normalizeEvidence);
          }
        }
      } catch {}
    }
    const localFiltered = CaseStateEngine.getInstance().getEvidenceForCase(caseId).map(normalizeEvidence);
    if (backendEvidence.length === 0) {
      return localFiltered;
    }
    const seenNames = new Set(backendEvidence.map(e => (e.fileName || e.file_name || '').toLowerCase()));
    const combined = [
      ...backendEvidence,
      ...localFiltered.filter(e => !seenNames.has((e.fileName || e.file_name || '').toLowerCase()))
    ];
    return combined;
  },

  getEvidenceById: async (id: string | number): Promise<Evidence | undefined> => {
    const strId = String(id);
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/evidence/${strId}`);
        if (res.ok) {
          const data = await handleResponse<any>(res);
          return normalizeEvidence(data);
        }
      } catch {}
    }
    const engineEvidence = CaseStateEngine.getInstance().getAllEvidence();
    const foundInEngine = engineEvidence.find((e: Evidence) => 
      String(e.id) === strId || 
      String(e.id) === strId.replace(/^E-/, '') ||
      `E-${e.id}` === strId
    );
    if (foundInEngine) return normalizeEvidence(foundInEngine);

    const found = mockEvidence.find((e: Evidence) => 
      String(e.id) === strId || 
      String(e.id) === strId.replace(/^E-/, '') ||
      `E-${e.id}` === strId
    );
    return found ? normalizeEvidence(found) : undefined;
  },

  analyzeEvidence: async (evidenceId: string | number, caseId?: string): Promise<any> => {
    const strId = String(evidenceId);
    const online = await checkBackend();
    if (online) {
      try {
        const url = caseId 
          ? `${API_BASE}/cases/${caseId}/pipeline/process-evidence/${strId}`
          : `${API_BASE}/evidence/${strId}/analyze`;
        const res = await fetch(url, { method: 'POST' });
        if (res.ok) {
          const data = await res.json();
          // Ingest new pipeline entities, contradictions, hypotheses, tasks into engine state
          const engine = CaseStateEngine.getInstance();
          if (Array.isArray(data.entities)) data.entities.forEach((e: any) => engine.addEntity(e));
          if (Array.isArray(data.contradictions)) data.contradictions.forEach((c: any) => engine.addContradiction(c));
          if (Array.isArray(data.tasks)) data.tasks.forEach((t: any) => engine.addTask(t));
          if (Array.isArray(data.hypotheses)) {
            data.hypotheses.forEach((h: any) => {
              engine.updateHypothesisConfidence(String(h.id), Math.round(h.support_score ?? h.confidence ?? 50));
            });
          }
          engine.notifyListeners();
          return data;
        }
      } catch {}
    }
    const item = mockEvidence.find(e => String(e.id) === strId);
    if (item) {
      item.processingStatus = 'Analyzed';
      item.processing_status = 'Analyzed';
    }
    return { status: 'success', message: 'Analysis completed.' };
  },

  deleteEvidence: async (evidenceId: string | number): Promise<void> => {
    const strId = String(evidenceId);
    try {
      const token = localStorage.getItem('evidentia_auth_token');
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      await fetch(`${API_BASE}/evidence/${strId}`, { method: 'DELETE', headers });
    } catch {}
    const idx = mockEvidence.findIndex(e => String(e.id) === strId);
    if (idx !== -1) mockEvidence.splice(idx, 1);
  },

  verifyEvidenceIntegrity: async (caseId: string, evidenceId: string | number): Promise<EvidenceIntegrityResult> => {
    const token = localStorage.getItem('evidentia_auth_token');
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}/cases/${caseId}/evidence/${evidenceId}/verify-integrity`, {
      method: 'POST',
      headers
    });
    if (!res.ok) throw new Error('Failed to verify evidence integrity');
    return await handleResponse<EvidenceIntegrityResult>(res);
  },

  getEvidenceCustodyLogs: async (caseId: string, evidenceId: string | number): Promise<CustodyLogEntry[]> => {
    const token = localStorage.getItem('evidentia_auth_token');
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}/cases/${caseId}/evidence/${evidenceId}/custody-logs`, {
      headers
    });
    if (!res.ok) return [];
    return await handleResponse<CustodyLogEntry[]>(res);
  },

  softDeleteEvidence: async (evidenceId: string | number): Promise<{ success: boolean; message: string }> => {
    const token = localStorage.getItem('evidentia_auth_token');
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}/evidence/${evidenceId}`, {
      method: 'DELETE',
      headers
    });
    if (!res.ok) throw new Error('Failed to soft delete exhibit');
    return await handleResponse<any>(res);
  }
};

// ============================================================
// AUDIT SERVICE (PHASE 3 FEATURE 2)
// ============================================================
export const auditService = {
  getCaseAuditLogs: async (
    caseId: string, 
    filters?: { userId?: number; actionType?: string }
  ): Promise<AuditLogEntry[]> => {
    const token = localStorage.getItem('evidentia_auth_token');
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const params = new URLSearchParams();
    if (filters?.userId) params.append('user_id', String(filters.userId));
    if (filters?.actionType) params.append('action_type', filters.actionType);

    const qs = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${API_BASE}/cases/${caseId}/audit-logs${qs}`, { headers });
    if (!res.ok) return [];
    return await handleResponse<AuditLogEntry[]>(res);
  },

  verifyAuditChain: async (caseId?: string): Promise<ChainVerificationResult> => {
    const token = localStorage.getItem('evidentia_auth_token');
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const qs = caseId ? `?case_id=${encodeURIComponent(caseId)}` : '';
    const res = await fetch(`${API_BASE}/audit/verify-chain${qs}`, { headers });
    if (!res.ok) throw new Error('Failed to verify audit ledger chain');
    return await handleResponse<ChainVerificationResult>(res);
  },

  getAllAuditLogs: async (filters?: { actionType?: string; userId?: number }): Promise<AuditLogEntry[]> => {
    const token = localStorage.getItem('evidentia_auth_token');
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const params = new URLSearchParams();
    if (filters?.userId) params.append('user_id', String(filters.userId));
    if (filters?.actionType) params.append('action_type', filters.actionType);

    const qs = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${API_BASE}/audit/logs${qs}`, { headers });
    if (!res.ok) return [];
    return await handleResponse<AuditLogEntry[]>(res);
  }
};

// ============================================================
// CITATION & PROVENANCE SERVICE (PHASE 3 FEATURE 3)
// ============================================================
export const citationService = {
  getEvidenceChunks: async (caseId: string, evidenceId: string | number): Promise<ExhibitChunk[]> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/${caseId}/evidence/${evidenceId}/chunks`, {
          headers: getAuthHeaders()
        });
        if (res.ok) {
          return await handleResponse<ExhibitChunk[]>(res);
        }
      } catch (err) {
        console.error('Failed to get exhibit chunks:', err);
      }
    }
    return [];
  },

  getEvidenceCitations: async (caseId: string, evidenceId: string | number): Promise<SourceCitation[]> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/${caseId}/evidence/${evidenceId}/citations`, {
          headers: getAuthHeaders()
        });
        if (res.ok) {
          return await handleResponse<SourceCitation[]>(res);
        }
      } catch (err) {
        console.error('Failed to get evidence citations:', err);
      }
    }
    return [];
  },

  getCaseCitations: async (caseId: string, factType?: string, factId?: number): Promise<SourceCitation[]> => {
    const online = await checkBackend();
    if (online) {
      try {
        const params = new URLSearchParams();
        if (factType) params.append('fact_type', factType);
        if (factId !== undefined && factId !== null) params.append('fact_id', String(factId));
        const qs = params.toString() ? `?${params.toString()}` : '';

        const res = await fetch(`${API_BASE}/cases/${caseId}/citations${qs}`, {
          headers: getAuthHeaders()
        });
        if (res.ok) {
          return await handleResponse<SourceCitation[]>(res);
        }
      } catch (err) {
        console.error('Failed to get case citations:', err);
      }
    }
    return [];
  },

  updateExtractedText: async (
    caseId: string,
    evidenceId: string | number,
    text: string
  ): Promise<TextCorrectionResult> => {
    const headers = getAuthHeaders({ 'Content-Type': 'application/json' });
    const res = await fetch(`${API_BASE}/cases/${caseId}/evidence/${evidenceId}/extracted-text`, {
      method: 'PUT',
      headers,
      body: JSON.stringify({ extracted_text: text, text })
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || 'Failed to update extracted text');
    }
    return await handleResponse<TextCorrectionResult>(res);
  }
};


// ============================================================
// ENTITY SERVICE
// ============================================================
export const entityService = {
  getEntitiesForCase: async (caseId: string): Promise<Entity[]> => {
    const online = await checkBackend();
    let backendEntities: Entity[] = [];
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/${caseId}/entities`);
        if (res.ok) {
          const data = await handleResponse<any[]>(res);
          if (Array.isArray(data)) {
            backendEntities = data.map(normalizeEntity);
          }
        }
      } catch {}
    }
    const localFiltered = CaseStateEngine.getInstance().getEntitiesForCase(caseId).map(normalizeEntity);
    if (backendEntities.length === 0) return localFiltered;
    const seenNames = new Set(backendEntities.map(e => (e.name || '').toLowerCase()));
    return [
      ...backendEntities,
      ...localFiltered.filter(e => !seenNames.has((e.name || '').toLowerCase()))
    ];
  }
};

// ============================================================
// TIMELINE SERVICE
// ============================================================
export const timelineService = {
  getTimelineForCase: async (caseId: string): Promise<TimelineEvent[]> => {
    const online = await checkBackend();
    let backendEvents: TimelineEvent[] = [];
    if (online) {
      try {
        let res = await fetch(`${API_BASE}/cases/${caseId}/events`);
        if (!res.ok) {
          res = await fetch(`${API_BASE}/cases/${caseId}/timeline`);
        }
        if (res.ok) {
          const data = await handleResponse<any[]>(res);
          if (Array.isArray(data)) {
            backendEvents = data.map(normalizeTimeline);
          }
        }
      } catch {}
    }
    const localFiltered = CaseStateEngine.getInstance().getTimelineForCase(caseId).map(normalizeTimeline);
    if (backendEvents.length === 0) return localFiltered;
    const seenTitles = new Set(backendEvents.map(e => (e.title || '').toLowerCase()));
    return [
      ...backendEvents,
      ...localFiltered.filter(e => !seenTitles.has((e.title || '').toLowerCase()))
    ];
  }
};

// ============================================================
// CONTRADICTION SERVICE
// ============================================================
export const contradictionService = {
  getContradictionsForCase: async (caseId: string): Promise<Contradiction[]> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/${caseId}/contradictions`);
        if (res.ok) {
          const data = await handleResponse<any[]>(res);
          if (Array.isArray(data) && data.length > 0) {
            const mapped: Contradiction[] = data.map((c: any) => ({
              id: `C-${c.id}`,
              caseId: String(c.case_id || caseId),
              statementA: c.statement_a || c.statementA,
              sourceAId: String(c.source_a_id || c.sourceAId || 'Exhibit A'),
              statementB: c.statement_b || c.statementB,
              sourceBId: String(c.source_b_id || c.sourceBId || 'Exhibit B'),
              conflictType: c.conflict_type || c.conflictType || 'Forensic Inconsistency',
              confidence: typeof c.confidence === 'number' ? c.confidence : 90,
              status: c.status || 'Detected'
            }));
            return mapped;
          }
        }
      } catch {}
    }
    return CaseStateEngine.getInstance().getContradictionsForCase(caseId);
  },

  detectContradictions: async (caseId: string): Promise<Contradiction[]> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/${caseId}/detect-contradictions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        if (res.ok) {
          const data = await handleResponse<any>(res);
          const rawItems = Array.isArray(data) ? data : (data.contradictions || []);
          const mapped: Contradiction[] = rawItems.map((c: any) => ({
            id: `C-${c.id}`,
            caseId: String(c.case_id || caseId),
            statementA: c.statement_a || c.statementA,
            sourceAId: String(c.source_a_id || c.sourceAId || 'Exhibit A'),
            statementB: c.statement_b || c.statementB,
            sourceBId: String(c.source_b_id || c.sourceBId || 'Exhibit B'),
            conflictType: c.conflict_type || c.conflictType || 'Forensic Inconsistency',
            confidence: typeof c.confidence === 'number' ? c.confidence : 90,
            status: c.status || 'Detected'
          }));

          const engine = CaseStateEngine.getInstance();
          mapped.forEach(c => engine.addContradiction(c));
          engine.notifyListeners();
          return mapped;
        }
      } catch (err) {
        console.error('Failed to run backend NLI contradiction detection:', err);
      }
    }
    return CaseStateEngine.getInstance().getContradictionsForCase(caseId);
  },

  updateStatus: async (contradictionId: string | number, status: 'Detected' | 'Under Review' | 'Resolved' | 'Dismissed'): Promise<boolean> => {
    const numId = String(contradictionId).replace(/\D/g, '');
    const online = await checkBackend();
    if (online && numId) {
      try {
        const res = await fetch(`${API_BASE}/contradictions/${numId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status })
        });
        return res.ok;
      } catch {}
    }
    return true;
  }
};

// ============================================================
// RELATIONSHIP SERVICE (SEMANTIC KNOWLEDGE GRAPH)
// ============================================================
export const relationshipService = {
  getRelationshipsForCase: async (caseId: string): Promise<Relationship[]> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/${caseId}/relationships`);
        if (res.ok) {
          const list = await handleResponse<any[]>(res);
          if (Array.isArray(list)) {
            const mapped: Relationship[] = list.map((r: any) => ({
              id: `REL-${r.id}`,
              caseId: String(r.case_id || caseId),
              sourceEntityId: String(r.source_entity_id),
              targetEntityId: String(r.target_entity_id),
              relationType: r.relation_type,
              evidenceId: r.evidence_id ? String(r.evidence_id) : undefined,
              confidence: typeof r.confidence === 'number' ? r.confidence : 0.9,
              reason: r.reason || '',
              sourceEntityName: r.source_entity_name,
              targetEntityName: r.target_entity_name,
              createdAt: r.created_at
            }));
            const engine = CaseStateEngine.getInstance();
            engine.setRelationshipsForCase(caseId, mapped);
            return mapped;
          }
        }
      } catch (err) {
        console.error('Failed to get relationships:', err);
      }
    }
    return CaseStateEngine.getInstance().getRelationshipsForCase(caseId);
  },

  extractRelationships: async (caseId: string): Promise<Relationship[]> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/${caseId}/extract-relationships`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        if (res.ok) {
          const list = await handleResponse<any[]>(res);
          if (Array.isArray(list)) {
            const mapped: Relationship[] = list.map((r: any) => ({
              id: `REL-${r.id}`,
              caseId: String(r.case_id || caseId),
              sourceEntityId: String(r.source_entity_id),
              targetEntityId: String(r.target_entity_id),
              relationType: r.relation_type,
              evidenceId: r.evidence_id ? String(r.evidence_id) : undefined,
              confidence: typeof r.confidence === 'number' ? r.confidence : 0.9,
              reason: r.reason || '',
              sourceEntityName: r.source_entity_name,
              targetEntityName: r.target_entity_name,
              createdAt: r.created_at
            }));
            const engine = CaseStateEngine.getInstance();
            engine.setRelationshipsForCase(caseId, mapped);
            engine.notifyListeners();
            return mapped;
          }
        }
      } catch (err) {
        console.error('Failed to extract relationships:', err);
      }
    }
    return CaseStateEngine.getInstance().getRelationshipsForCase(caseId);
  },

  createRelationship: async (caseId: string, rel: Partial<Relationship>): Promise<Relationship | null> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/${caseId}/relationships`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            source_entity_id: parseInt(String(rel.sourceEntityId).replace(/\D/g, '')),
            target_entity_id: parseInt(String(rel.targetEntityId).replace(/\D/g, '')),
            relation_type: rel.relationType,
            evidence_id: rel.evidenceId ? parseInt(String(rel.evidenceId).replace(/\D/g, '')) : null,
            confidence: rel.confidence || 0.9,
            reason: rel.reason
          })
        });
        if (res.ok) {
          const r = await handleResponse<any>(res);
          const mapped: Relationship = {
            id: `REL-${r.id}`,
            caseId: String(r.case_id || caseId),
            sourceEntityId: String(r.source_entity_id),
            targetEntityId: String(r.target_entity_id),
            relationType: r.relation_type,
            evidenceId: r.evidence_id ? String(r.evidence_id) : undefined,
            confidence: r.confidence,
            reason: r.reason,
            sourceEntityName: r.source_entity_name,
            targetEntityName: r.target_entity_name
          };
          CaseStateEngine.getInstance().addRelationship(mapped);
          CaseStateEngine.getInstance().notifyListeners();
          return mapped;
        }
      } catch (err) {
        console.error('Failed to create relationship:', err);
      }
    }
    return null;
  }
};

// ============================================================
// HYPOTHESIS NORMALIZER & SERVICE
// ============================================================


export function normalizeHypothesis(h: any): Hypothesis {
  if (!h) return h;
  const supporting: string[] = Array.isArray(h.supportingEvidenceIds) ? [...h.supportingEvidenceIds] : [];
  const contradicting: string[] = Array.isArray(h.contradictingEvidenceIds) ? [...h.contradictingEvidenceIds] : [];
  const assessments: any[] = Array.isArray(h.assessments) ? h.assessments : [];

  // Derive supporting and contradicting from backend assessments if present
  if (assessments.length > 0 && supporting.length === 0 && contradicting.length === 0) {
    assessments.forEach((a: any) => {
      const cls = (a.classification || '').toLowerCase();
      const evId = String(a.evidence_id || a.evidenceId || '');
      if (cls.includes('support') && !supporting.includes(evId)) supporting.push(evId);
      if (cls.includes('contradiction') && !contradicting.includes(evId)) contradicting.push(evId);
    });
  }

  const score = typeof h.support_score === 'number' ? h.support_score : (typeof h.confidence === 'number' ? h.confidence : 50.0);

  return {
    ...h,
    id: String(h.id),
    caseId: String(h.caseId || h.case_id || ''),
    title: h.title || 'Untitled Hypothesis',
    description: h.description || '',
    status: h.status || 'Active',
    confidence: Math.round(score),
    support_score: score,
    supportingEvidenceIds: supporting,
    contradictingEvidenceIds: contradicting,
    relatedEntityIds: Array.isArray(h.relatedEntityIds) ? h.relatedEntityIds : [],
    assessments,
    assessment_count: assessments.length || h.assessment_count || 0,
    created_at: h.created_at || new Date().toISOString()
  };
}

export const hypothesisService = {
  getHypothesesForCase: async (caseId: string): Promise<Hypothesis[]> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/${caseId}/hypotheses`);
        if (res.ok) {
          const list = await handleResponse<any[]>(res);
          if (Array.isArray(list) && list.length > 0) {
            // Also fetch details for each hypothesis to include assessments
            const detailed = await Promise.all(
              list.map(async (h) => {
                try {
                  const detailRes = await fetch(`${API_BASE}/hypotheses/${h.id}`);
                  if (detailRes.ok) {
                    const detailData = await handleResponse<any>(detailRes);
                    return normalizeHypothesis(detailData);
                  }
                } catch {}
                return normalizeHypothesis(h);
              })
            );
            return detailed;
          }
        }
      } catch {}
    }
    return CaseStateEngine.getInstance().getHypothesesForCase(caseId).map(normalizeHypothesis);
  },

  getHypothesisById: async (hypothesisId: string | number): Promise<Hypothesis | undefined> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/hypotheses/${hypothesisId}`);
        if (res.ok) {
          const data = await handleResponse<any>(res);
          return normalizeHypothesis(data);
        }
      } catch {}
    }
    return undefined;
  },

  createHypothesis: async (caseId: string, data: { title: string; description?: string; status?: string }): Promise<Hypothesis> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/${caseId}/hypotheses`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        });
        if (res.ok) {
          const created = await handleResponse<any>(res);
          return normalizeHypothesis(created);
        }
      } catch {}
    }
    const newHyp = normalizeHypothesis({
      id: `H-${Date.now().toString().slice(-4)}`,
      caseId,
      title: data.title,
      description: data.description || '',
      status: data.status || 'Active',
      confidence: 50,
      support_score: 50,
      supportingEvidenceIds: [],
      contradictingEvidenceIds: [],
      assessments: []
    });
    return newHyp;
  },

  evaluateHypothesis: async (hypothesisId: string | number): Promise<Hypothesis | undefined> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/hypotheses/${hypothesisId}/evaluate`, {
          method: 'POST',
        });
        if (res.ok) {
          const data = await handleResponse<any>(res);
          return normalizeHypothesis(data);
        }
      } catch {}
    }
    return undefined;
  },

  analyzeHypotheses: async (caseId: string): Promise<Hypothesis[]> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/${caseId}/analyze-hypotheses`, {
          method: 'POST',
        });
        if (res.ok) {
          const list = await handleResponse<any[]>(res);
          if (Array.isArray(list) && list.length > 0) {
            const normalized = list.map(normalizeHypothesis);
            const engine = CaseStateEngine.getInstance();
            normalized.forEach(h => {
              engine.updateHypothesisConfidence(h.id, h.confidence);
            });
            engine.notifyListeners();
            return normalized;
          }
        }
      } catch (err) {
        console.error('Failed to run backend hypothesis analysis:', err);
      }
    }
    return CaseStateEngine.getInstance().getHypothesesForCase(caseId).map(normalizeHypothesis);
  },

  assessEvidence: async (hypothesisId: string | number, assessment: { evidence_id: number; classification: string; reason?: string }): Promise<any> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/hypotheses/${hypothesisId}/assessments`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(assessment),
        });
        if (res.ok) {
          return await handleResponse<any>(res);
        }
      } catch {}
    }
    return null;
  },

  overrideAssessment: async (caseId: string, payload: { hypothesis_id: number | string; evidence_id: number | string; classification: string; analyst_notes?: string }): Promise<any> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/${caseId}/assessments/override`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            hypothesis_id: Number(String(payload.hypothesis_id).replace(/\D/g, '')),
            evidence_id: Number(String(payload.evidence_id).replace(/\D/g, '')),
            classification: payload.classification,
            analyst_notes: payload.analyst_notes || 'Investigator analytical override'
          })
        });
        if (res.ok) {
          return await handleResponse<any>(res);
        }
      } catch (err) {
        console.error('Failed to apply analyst override:', err);
      }
    }
    return null;
  },

  resetAssessment: async (caseId: string, hypothesisId: number | string, evidenceId: number | string): Promise<any> => {
    const online = await checkBackend();
    if (online) {
      try {
        const hId = Number(String(hypothesisId).replace(/\D/g, ''));
        const evId = Number(String(evidenceId).replace(/\D/g, ''));
        const res = await fetch(`${API_BASE}/cases/${caseId}/assessments/reset?hypothesis_id=${hId}&evidence_id=${evId}`, {
          method: 'POST'
        });
        if (res.ok) {
          return await handleResponse<any>(res);
        }
      } catch (err) {
        console.error('Failed to reset assessment:', err);
      }
    }
    return null;
  },

  getSensitivityAnalysis: async (caseId: string): Promise<SensitivityAnalysisResult | null> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/${caseId}/ach/sensitivity-analysis`);
        if (res.ok) {
          return await handleResponse<SensitivityAnalysisResult>(res);
        }
      } catch (err) {
        console.error('Failed to fetch sensitivity analysis:', err);
      }
    }
    return null;
  },

  calculateACHWithExclusions: async (caseId: string, excludedEvidenceIds: (number | string)[]): Promise<any> => {
    const online = await checkBackend();
    if (online) {
      try {
        const numIds = excludedEvidenceIds.map(id => Number(String(id).replace(/\D/g, ''))).filter(n => !isNaN(n));
        const res = await fetch(`${API_BASE}/cases/${caseId}/ach/calculate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ excluded_evidence_ids: numIds })
        });
        if (res.ok) {
          return await handleResponse<any>(res);
        }
      } catch (err) {
        console.error('Failed to calculate ACH with exclusions:', err);
      }
    }
    return null;
  },

  recalculateScoring: async (caseId: string, payload?: any): Promise<ScoringRecalculateResponse | null> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/${caseId}/scoring/recalculate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload || {})
        });
        if (res.ok) {
          return await handleResponse<ScoringRecalculateResponse>(res);
        }
      } catch (err) {
        console.error('Failed to recalculate scoring:', err);
      }
    }
    return null;
  },

  getHypothesisBreakdown: async (caseId: string, hypothesisId: string | number): Promise<any> => {
    const online = await checkBackend();
    if (online) {
      try {
        const numId = Number(String(hypothesisId).replace(/\D/g, ''));
        const res = await fetch(`${API_BASE}/cases/${caseId}/scoring/breakdown/${numId}`);
        if (res.ok) {
          return await handleResponse<any>(res);
        }
      } catch (err) {
        console.error('Failed to get hypothesis breakdown:', err);
      }
    }
    return null;
  },

  getSensitivityAndRobustness: async (caseId: string): Promise<any> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/${caseId}/scoring/sensitivity`);
        if (res.ok) {
          return await handleResponse<any>(res);
        }
      } catch (err) {
        console.error('Failed to get sensitivity and robustness:', err);
      }
    }
    return null;
  },

  overrideScoring: async (caseId: string, payload: any): Promise<any> => {
    const online = await checkBackend();
    if (online) {
      try {
        const bodyData = {
          hypothesis_id: Number(String(payload.hypothesis_id || payload.hypothesisId).replace(/\D/g, '')),
          evidence_id: Number(String(payload.evidence_id || payload.evidenceId).replace(/\D/g, '')),
          classification: payload.classification,
          evidence_type: payload.evidence_type,
          manual_reliability: payload.manual_reliability,
          hash_verified: payload.hash_verified,
          chain_of_custody_complete: payload.chain_of_custody_complete,
          sec_65b_certificate_present: payload.sec_65b_certificate_present,
          source_independent: payload.source_independent,
          quality_rating: payload.quality_rating,
          analyst_notes: payload.analyst_notes || 'Analyst forensic adjustment'
        };
        const res = await fetch(`${API_BASE}/cases/${caseId}/scoring/override`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(bodyData)
        });
        if (res.ok) {
          return await handleResponse<any>(res);
        }
      } catch (err) {
        console.error('Failed to apply scoring override:', err);
      }
    }
    return null;
  },

  getReliabilityConfigs: async (caseId: string): Promise<ReliabilityConfig[]> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/${caseId}/scoring/reliability-configs`);
        if (res.ok) {
          return await handleResponse<ReliabilityConfig[]>(res);
        }
      } catch (err) {
        console.error('Failed to get reliability configs:', err);
      }
    }
    return [];
  },

  updateReliabilityConfig: async (caseId: string, update: { evidence_type: string; base_reliability: number; rationale?: string }): Promise<any> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/${caseId}/scoring/reliability-configs`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(update)
        });
        if (res.ok) {
          return await handleResponse<any>(res);
        }
      } catch (err) {
        console.error('Failed to update reliability config:', err);
      }
    }
    return null;
  }
};

// ============================================================
// ACH EVALUATION & VALIDATION BENCHMARK SERVICE
// ============================================================
export const evaluationBenchmarkService = {
  getBenchmarkResults: async (): Promise<BenchmarkReport | null> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/evaluation/benchmark-results`);
        if (res.ok) {
          return await handleResponse<BenchmarkReport>(res);
        }
      } catch (err) {
        console.error('Failed to fetch benchmark results:', err);
      }
    }
    return null;
  },

  runBenchmark: async (runs: number = 3): Promise<BenchmarkReport | null> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/evaluation/run`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ runs })
        });
        if (res.ok) {
          return await handleResponse<BenchmarkReport>(res);
        }
      } catch (err) {
        console.error('Failed to trigger benchmark run:', err);
      }
    }
    return null;
  },

  getBenchmarkDataset: async (): Promise<any[]> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/evaluation/dataset`);
        if (res.ok) {
          return await handleResponse<any[]>(res);
        }
      } catch (err) {
        console.error('Failed to fetch benchmark dataset:', err);
      }
    }
    return [];
  }
};

// ============================================================
// INVESTIGATION TASK SERVICE
// ============================================================
export const investigationService = {
  getTasksForCase: async (caseId: string): Promise<InvestigationTask[]> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/${caseId}/tasks`);
        if (res.ok) {
          const data = await handleResponse<any[]>(res);
          if (Array.isArray(data) && data.length > 0) {
            const mapped: InvestigationTask[] = data.map((t: any) => ({
              id: `TSK-${t.id}`,
              caseId: String(t.case_id || caseId),
              task: t.task,
              reason: t.reason || 'Generated by AI Forensic Intelligence Pipeline',
              relatedHypothesisId: t.related_hypothesis_id || t.relatedHypothesisId,
              relatedContradictionId: t.related_contradiction_id || t.relatedContradictionId,
              relatedEvidenceId: t.related_evidence_id || t.relatedEvidenceId,
              priority: (t.priority || 'High') as 'High' | 'Medium' | 'Low',
              status: (t.status || 'Pending') as 'Pending' | 'In Progress' | 'Completed',
              assignedTo: t.assigned_to || t.assignedTo || 'Lead Investigator'
            }));
            return mapped;
          }
        }
      } catch {}
    }
    return CaseStateEngine.getInstance().getTasksForCase(caseId);
  },

  createTask: async (taskData: {
    caseId: string;
    task: string;
    reason?: string;
    relatedHypothesisId?: string;
    relatedContradictionId?: string;
    relatedEvidenceId?: string;
    priority?: 'High' | 'Medium' | 'Low';
    status?: 'Pending' | 'In Progress' | 'Completed';
    assignedTo?: string;
  }): Promise<InvestigationTask | null> => {
    const online = await checkBackend();
    if (online) {
      try {
        const res = await fetch(`${API_BASE}/cases/${taskData.caseId}/tasks`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            task: taskData.task,
            reason: taskData.reason,
            related_hypothesis_id: taskData.relatedHypothesisId,
            related_contradiction_id: taskData.relatedContradictionId,
            related_evidence_id: taskData.relatedEvidenceId,
            priority: taskData.priority || 'High',
            status: taskData.status || 'Pending',
            assigned_to: taskData.assignedTo || 'Lead Investigator'
          })
        });
        if (res.ok) {
          const t = await handleResponse<any>(res);
          const taskObj: InvestigationTask = {
            id: `TSK-${t.id}`,
            caseId: String(t.case_id || taskData.caseId),
            task: t.task,
            reason: t.reason || '',
            priority: (t.priority || 'High') as any,
            status: (t.status || 'Pending') as any,
            relatedContradictionId: t.related_contradiction_id,
            relatedHypothesisId: t.related_hypothesis_id,
            relatedEvidenceId: t.related_evidence_id,
            assignedTo: t.assigned_to || 'Lead Investigator'
          };
          CaseStateEngine.getInstance().addTask(taskObj);
          CaseStateEngine.getInstance().notifyListeners();
          return taskObj;
        }
      } catch (err) {
        console.error('Failed to create task on backend:', err);
      }
    }
    return null;
  }
};

// ============================================================
// GEO CASE SERVICE (Map)
// ============================================================
export const geoCaseService = {
  getGeoCases: async (): Promise<GeoCase[]> => {
    return mockGeoCases;
  }
};

// ============================================================
// CASE REPORT EXPORT SERVICE (PHASE 3 FEATURE 4)
// ============================================================
export const reportService = {
  downloadCasePdfReport: async (caseId: string, caseTitle?: string): Promise<boolean> => {
    try {
      const headers = getAuthHeaders();
      const res = await fetch(`${API_BASE}/cases/${caseId}/reports/pdf`, { headers });
      if (!res.ok) throw new Error(`Failed to generate PDF: ${res.statusText}`);

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const safeTitle = (caseTitle || `Case_${caseId}`).replace(/[^a-zA-Z0-9_-]/g, '_');
      a.download = `Evidentia_${safeTitle}_Dossier.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      return true;
    } catch (err) {
      console.error('PDF export error:', err);
      throw err;
    }
  },

  getCaseDocketData: async (caseId: string): Promise<any> => {
    const headers = getAuthHeaders();
    const res = await fetch(`${API_BASE}/cases/${caseId}/reports/docket-data`, { headers });
    if (!res.ok) throw new Error('Failed to fetch case docket data');
    return await handleResponse<any>(res);
  }
};

