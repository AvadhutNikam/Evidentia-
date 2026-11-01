import { 
  PrioritiesResponse, 
  GlobalCasePriority, 
  ReportRequest, 
  PersonRegister, 
  StatementTracker 
} from '../types';
import { apiRequest } from './apiClient';
import { isDemoMode } from '../config/api';

export const prioritiesService = {
  getCasePriorities: async (caseId: string | number, skipCache = false): Promise<PrioritiesResponse> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    const url = `/cases/${cleanId}/priorities${skipCache ? '?skip_cache=true' : ''}`;
    try {
      return await apiRequest<PrioritiesResponse>(url);
    } catch (err) {
      if (isDemoMode()) {
        return getMockPriorities(Number(cleanId) || 1);
      }
      throw err;
    }
  },

  getGlobalPriorities: async (): Promise<GlobalCasePriority[]> => {
    try {
      return await apiRequest<GlobalCasePriority[]>('/priorities');
    } catch (err) {
      if (isDemoMode()) {
        return [
          {
            case_id: 1,
            case_title: 'State of Maharashtra vs. Yogesh Raut & Ors',
            fir_number: 'FIR-452/2009',
            has_dates: true,
            chargesheet_days_left: 4,
            chargesheet_band: 'urgent',
            remand_days_left: 2,
            remand_band: 'critical',
            overdue_reports_count: 1,
            unexamined_witnesses_count: 4,
            critical_review_items_count: 2,
            top_urgency: 'critical',
            next_action_title: 'Magisterial Remand Hearing in 2 days',
            next_action_due: new Date(Date.now() + 2 * 86400000).toISOString()
          }
        ];
      }
      throw err;
    }
  },

  createReportRequest: async (caseId: string | number, data: Partial<ReportRequest>): Promise<ReportRequest> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest<ReportRequest>(`/cases/${cleanId}/report-requests`, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  updateReportRequest: async (
    caseId: string | number, 
    requestId: number, 
    data: Partial<ReportRequest>
  ): Promise<ReportRequest> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest<ReportRequest>(`/cases/${cleanId}/report-requests/${requestId}`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
  },

  createPerson: async (caseId: string | number, data: Partial<PersonRegister>): Promise<PersonRegister> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest<PersonRegister>(`/cases/${cleanId}/people`, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  updateStatement: async (
    caseId: string | number, 
    statementId: number, 
    data: Partial<StatementTracker>
  ): Promise<StatementTracker> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest<StatementTracker>(`/cases/${cleanId}/statements/${statementId}`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
  },

  updateCaseProcedure: async (caseId: string | number, data: any): Promise<any> => {
    const cleanId = String(caseId).replace(/^C-/, '');
    return await apiRequest(`/cases/${cleanId}/procedure`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
  }
};

function getMockPriorities(caseId: number): PrioritiesResponse {
  return {
    case_id: caseId,
    case_title: 'State of Maharashtra vs. Yogesh Raut & Ors',
    fir_number: 'FIR-452/2009',
    cached: false,
    updated_at: new Date().toISOString(),
    since_you_were_away: {
      headline: '2 new forensic laboratory updates and 1 high-priority alibi conflict logged.',
      summary_sentence: 'Since your last shift, 1 DNA confirmation was uploaded and 2 statements were scheduled.',
      hours_away: 14.5,
      new_evidence_count: 2,
      changed_hypotheses_count: 1,
      unresolved_alerts_count: 2,
      open_tasks_count: 4,
      summary_points: [
        'FSL Kalina DNA match submitted for vaginal swab (Exhibit #03)',
        'Key witness Rajesh Chaudhari scheduled for Section 164 statement recording'
      ]
    },
    statutory_clock: {
      has_dates: true,
      chargesheet_limit_days: 90,
      arrest_date: '2009-10-16T10:00:00Z',
      remand_date: '2009-10-18T14:00:00Z',
      chargesheet_deadline: '2010-01-14T23:59:59Z',
      chargesheet_days_left: 4,
      chargesheet_hours_left: 96,
      chargesheet_band: 'urgent',
      chargesheet_legal_note: 'Section 167(2) CrPC / Section 187(3) BNSS: Charge-sheet filing deadline before accused becomes entitled to default bail.',
      remand_deadline: '2009-11-01T23:59:59Z',
      remand_days_left: 2,
      remand_hours_left: 48,
      remand_band: 'critical',
      remand_legal_note: '14-day statutory police custody remand expiry approaching. File for judicial extension.',
      statutory_provision: 'Section 187(3) BNSS / Section 167(2) CrPC',
      extensions: []
    },
    action_items: [
      {
        id: 'deadline-remand',
        type: 'deadline',
        title: 'Police Custody Remand Expiry in 2 Days',
        reason: 'Remand expires in 48 hours. Magisterial extension petition required.',
        severity: 'critical',
        days_left: 2,
        action_link: `/cases/${caseId}/case-file`,
        action_label: 'Review Custody Details',
        status: 'pending'
      },
      {
        id: 'report-fsl-kalina',
        type: 'report',
        title: 'DNA Profiling Report from FSL Kalina Awaited',
        reason: 'Waiting 12 days since dispatch. Expected delivery was 2 days ago.',
        severity: 'urgent',
        days_left: -2,
        action_link: `/cases/${caseId}/evidence`,
        action_label: 'Track Report & Send Reminder',
        status: 'pending'
      }
    ],
    pending_reports: {
      total_requested: 3,
      received_count: 1,
      overdue_count: 1,
      pending_count: 1,
      items: [
        {
          id: 1,
          case_id: caseId,
          report_type: 'DNA Profiling & Semen Serology',
          requested_from: 'FSL Kalina, Mumbai',
          requested_date: '2009-10-20T11:00:00Z',
          expected_date: '2009-10-30T17:00:00Z',
          status: 'overdue',
          urgency: 'critical',
          days_waiting: 12,
          is_overdue: true,
          notes: 'Crucial for corroborating Section 376(2)(g) charges'
        },
        {
          id: 2,
          case_id: caseId,
          report_type: 'CDR & Cellular Tower Dump Analysis',
          requested_from: 'Nodal Officer Idea Cellular & Vodafone',
          requested_date: '2009-10-22T09:30:00Z',
          expected_date: '2009-11-05T17:00:00Z',
          status: 'requested',
          urgency: 'high',
          days_waiting: 10,
          is_overdue: false,
          notes: 'Tower dump for Kharadi bypass sector'
        }
      ],
      unrequested_protocol_exhibits: [
        {
          item: 'Post-Mortem Final Opinion',
          description: 'Homicide / Cause of Death conclusive medical certificate',
          mandatory: true,
          reason: 'Required under IPC 302 / BNS 103 protocol'
        }
      ]
    },
    witnesses_and_statements: {
      total_people: 5,
      examined_count: 2,
      unexamined_count: 3,
      items: [
        {
          id: 1,
          case_id: caseId,
          name: 'Rajesh Chaudhari',
          role: 'Approver / Accomplice',
          contact_info: 'Under SIT Witness Protection',
          is_important: true,
          mention_count: 8,
          statement_status: 'scheduled',
          statement_type: 'Section 164 CrPC (Judicial Magistrate)',
          scheduled_date: '2009-11-03T11:00:00Z'
        },
        {
          id: 2,
          case_id: caseId,
          name: 'Shrikant Shinde',
          role: 'Eye Witness (ATM Guard)',
          contact_info: 'Yerwada Branch SBI',
          is_important: true,
          mention_count: 3,
          statement_status: 'summoned',
          statement_type: 'Section 161 CrPC (Police)',
          scheduled_date: '2009-11-02T15:00:00Z'
        }
      ],
      ai_suggested_persons: [
        {
          name: 'Security Supervisor (Synechron)',
          role: 'Campus Security',
          mention_count: 2,
          reason: 'Mentioned in logbook entry regarding cab departure'
        }
      ]
    },
    needs_your_review: {
      total_items: 2,
      items: [
        {
          id: 'contra-1',
          type: 'contradiction',
          title: 'Alibi Contradiction: Raut vehicle sighting vs CDR',
          reason: 'Suspect claimed he was at Hadapsar; cell tower dump places handset at Kharadi Bypass.',
          impact_score: 9.2,
          severity: 'critical',
          action_link: `/cases/${caseId}/hypotheses?tab=contradictions`,
          action_label: 'Open Contradiction Matrix'
        },
        {
          id: 'sec65b-1',
          type: 'data_quality',
          title: 'Missing Section 65B Indian Evidence Act Certificate',
          reason: 'ATM CCTV video Exhibit #01 requires electronic evidence certificate from bank branch manager.',
          impact_score: 8.5,
          severity: 'high',
          action_link: `/cases/${caseId}/evidence/data-quality`,
          action_label: 'View Data Quality Report'
        }
      ]
    },
    case_snapshot: {
      exhibits_count: 8,
      entities_count: 24,
      hypotheses_count: 3,
      timeline_events_count: 14,
      top_hypothesis: {
        id: 1,
        title: 'Premeditated Abduction, Robbery and Murder by Yogesh Raut and Accomplices',
        probability: 0.93,
        rank: 1
      }
    }
  };
}
