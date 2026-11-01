import { 
  LayoutDashboard, Clock, FileText, Network, Users, AlertTriangle, 
  Target, UserCheck, CheckSquare, Mic, Map, ClipboardList, Scale, 
  Share2, Radio, BarChart2, Activity, FolderSync, Shield, Sliders,
  ShieldAlert, Sparkles, FolderArchive, Archive, LucideIcon
} from 'lucide-react';

/**
 * Terminology dictionary mapping academic / data-science terms
 * to police investigator terminology, with optional methodology wording.
 */
export const TERMINOLOGY_DICTIONARY = {
  overview: {
    investigator: 'Overview',
    methodology: 'Case Overview',
    description: 'Executive situation board, primary suspect strength, and operational summary'
  },
  priorities: {
    investigator: "Today's Priorities",
    methodology: 'Operational Priorities',
    description: 'Statutory countdowns (60/90 days), pending lab reports, open alerts, and urgent tasks'
  },
  case_file: {
    investigator: 'Case File',
    methodology: 'Docket & FIR Details',
    description: 'Official FIR parameters, statutory penal sections, IO metadata, and formal custody registry'
  },
  exhibits: {
    investigator: 'Exhibits',
    methodology: 'Evidence Register',
    description: 'Master exhibit register with chain of custody, OCR text, and forensic test results'
  },
  field_capture: {
    investigator: 'Field Capture',
    methodology: 'Mobile Field Ingest',
    description: 'Secure mobile field photo, audio, and seizure memo capture with tamper-proof hashing'
  },
  live_feeds: {
    investigator: 'Live Feeds',
    methodology: 'Data Connectors',
    description: 'Automated ingestion pipelines from forensic lab SFTPs, CCTV dumps, and network folders'
  },
  data_quality: {
    investigator: 'Data Quality',
    methodology: 'Cryptographic Audit',
    description: 'SHA-256 integrity audits, Section 65B BSA compliance, and low-confidence OCR verification'
  },
  malkhana: {
    investigator: 'Malkhana Register',
    methodology: 'Station Evidence Vault',
    description: 'Station-level Muddimalkhana inventory, tamper-evident seals, rack allocations, and two-person custody approvals'
  },
  suspects_theories: {
    investigator: 'Suspects and Theories',
    methodology: 'Hypotheses & Elimination (ACH)',
    description: 'Suspect case strength, alibi verification, and forensic proof elimination matrix'
  },
  witnesses: {
    investigator: 'Witnesses and Statements',
    methodology: 'Interviews & Confessions',
    description: 'Witness testimonies, suspect interrogations, audio recordings, and Section 161 statements'
  },
  link_analysis: {
    investigator: 'Link Analysis',
    methodology: 'Knowledge Graph & Entities',
    description: 'Unified visual graph, people & places registry, workspace, and cross-case intelligence'
  },
  phone_bank: {
    investigator: 'Phone and Bank Analysis',
    methodology: 'CDR & Financial Analytics',
    description: 'Call Detail Records (CDR), cell tower triangulation, and suspicious bank transaction trails'
  },
  map_timeline: {
    investigator: 'Map and Timeline',
    methodology: 'Spatio-Temporal Analysis',
    description: 'Minute-by-minute chronology and interactive crime scene / cell tower mapping'
  },
  missing_evidence: {
    investigator: 'Missing Evidence',
    methodology: 'Investigation Plan & Gaps',
    description: 'Critical proof required to secure conviction, procedural gap detection, and assigned field tasks'
  },
  defense_stress_test: {
    investigator: 'Defense Stress-Test',
    methodology: "Devil's Advocate Analysis",
    description: 'Stress-tests case against reasonable doubt: assembles the defense attorney’s counter-case before trial'
  },
  chargesheet: {
    investigator: 'Chargesheet',
    methodology: 'Statutory Chargesheet Generator',
    description: 'Court-ready chargesheet generator compliant with BNSS / CrPC statutory prosecution standards'
  },
  handover: {
    investigator: 'Handover',
    methodology: 'Officer Transfer Protocol',
    description: 'Four-eyes transfer briefing, unverified leads memo, and investigator custody handover'
  },
  activity_log: {
    investigator: 'Activity Log',
    methodology: 'Immutable Activity Log',
    description: 'Court-admissible tamper-evident activity log tracking every classification, edit, and export'
  },
  reports: {
    investigator: 'Reports',
    methodology: 'Intelligence Products',
    description: 'Generate briefing packs, forensic summaries, timeline exhibits, and supervisory status reports'
  }
} as const;

export interface NavTabConfig {
  id: string;
  label: string;
  methodologyLabel?: string;
  icon?: LucideIcon;
}

export interface CaseNavItem {
  id: string;
  label: string;
  methodologyLabel?: string;
  icon: LucideIcon;
  path: string; // Relative to /cases/:caseId/
  allowedRoles: string[]; // e.g. ['admin', 'lead_investigator', 'analyst', 'reviewer']
  featureFlag?: string; // Optional feature toggle
  badgeKey?: 'evidence_processing' | 'data_quality_issues' | 'unresolved_contradictions' | 'critical_gaps' | 'priorities_due' | 'handover_changed';
  badgeSource?: 'evidence_processing' | 'data_quality_issues' | 'unresolved_contradictions' | 'critical_gaps' | 'priorities_due' | 'handover_changed';
  searchKeywords: string[];
  replaces: string[]; // Old paths taken over for backward-compatible redirects
  oldPaths?: string[]; // Alias for replaces
  description?: string;
  tabs?: NavTabConfig[];
  defaultTab?: string;
}

export interface CaseNavGroup {
  id: string;
  label: string;
  icon: LucideIcon;
  openByDefault: boolean;
  defaultOpen?: boolean; // Alias for openByDefault
  items: CaseNavItem[];
}

export const CASE_NAV_GROUPS: CaseNavGroup[] = [
  {
    id: 'my_case',
    label: 'My case',
    icon: LayoutDashboard,
    openByDefault: true,
    items: [
      {
        id: 'overview',
        label: TERMINOLOGY_DICTIONARY.overview.investigator,
        methodologyLabel: TERMINOLOGY_DICTIONARY.overview.methodology,
        icon: LayoutDashboard,
        path: 'overview',
        allowedRoles: ['admin', 'lead_investigator', 'analyst', 'reviewer'],
        badgeKey: undefined,
        searchKeywords: ['overview', 'dashboard', 'situation board', 'kpi', 'status', 'summary', 'case wall'],
        replaces: ['dashboard', 'case-overview'],
        description: TERMINOLOGY_DICTIONARY.overview.description
      },
      {
        id: 'priorities',
        label: TERMINOLOGY_DICTIONARY.priorities.investigator,
        methodologyLabel: TERMINOLOGY_DICTIONARY.priorities.methodology,
        icon: Clock,
        path: 'priorities',
        allowedRoles: ['admin', 'lead_investigator', 'analyst', 'reviewer'],
        badgeKey: 'priorities_due',
        searchKeywords: ['priorities', 'today', 'deadlines', 'countdown', 'statutory deadline', 'chargesheet due', 'tasks', 'alerts', 'pending lab'],
        replaces: ['today', 'deadlines', 'tasks-due'],
        description: TERMINOLOGY_DICTIONARY.priorities.description
      },
      {
        id: 'case_file',
        label: TERMINOLOGY_DICTIONARY.case_file.investigator,
        methodologyLabel: TERMINOLOGY_DICTIONARY.case_file.methodology,
        icon: FolderArchive,
        path: 'case-file',
        allowedRoles: ['admin', 'lead_investigator', 'analyst', 'reviewer'],
        badgeKey: undefined,
        searchKeywords: ['case file', 'fir', 'offence', 'sections', 'ipc', 'bns', 'investigating officer', 'jurisdiction', 'docket'],
        replaces: ['details', 'docket-details', 'fir-details'],
        description: TERMINOLOGY_DICTIONARY.case_file.description
      }
    ]
  },
  {
    id: 'evidence',
    label: 'Evidence',
    icon: FileText,
    openByDefault: false,
    items: [
      {
        id: 'intake_inbox',
        label: 'Intake Inbox & Reading',
        methodologyLabel: 'Multimodal Ingestion Pipeline',
        icon: Sparkles,
        path: 'intake',
        allowedRoles: ['admin', 'lead_investigator', 'analyst', 'reviewer'],
        badgeKey: undefined,
        searchKeywords: ['intake', 'reading', 'ocr', 'fir', 'handwritten', 'voice', 'whatsapp', 'marathi', 'hindi', 'devanagari'],
        replaces: ['intake', 'intake-inbox', 'reading-card'],
        description: 'AI document reading and officer confirmation for FIRs, handwritten statements, audio logs, and WhatsApp'
      },
      {
        id: 'exhibits',
        label: TERMINOLOGY_DICTIONARY.exhibits.investigator,
        methodologyLabel: TERMINOLOGY_DICTIONARY.exhibits.methodology,
        icon: FileText,
        path: 'evidence',
        allowedRoles: ['admin', 'lead_investigator', 'analyst', 'reviewer'],
        badgeKey: 'evidence_processing',
        searchKeywords: ['evidence', 'exhibits', 'files', 'documents', 'cctv', 'dna', 'forensic', 'upload'],
        replaces: ['evidence/list', 'exhibits'],
        description: TERMINOLOGY_DICTIONARY.exhibits.description
      },
      {
        id: 'field_capture',
        label: TERMINOLOGY_DICTIONARY.field_capture.investigator,
        methodologyLabel: TERMINOLOGY_DICTIONARY.field_capture.methodology,
        icon: Sparkles,
        path: 'field-capture',
        allowedRoles: ['admin', 'lead_investigator', 'analyst'],
        badgeKey: undefined,
        searchKeywords: ['field capture', 'mobile', 'camera', 'photo', 'crime scene', 'audio note', 'upload photo'],
        replaces: ['capture', 'mobile', 'camera'],
        description: TERMINOLOGY_DICTIONARY.field_capture.description
      },
      {
        id: 'live_feeds',
        label: TERMINOLOGY_DICTIONARY.live_feeds.investigator,
        methodologyLabel: TERMINOLOGY_DICTIONARY.live_feeds.methodology,
        icon: FolderSync,
        path: 'connectors',
        allowedRoles: ['admin', 'lead_investigator'],
        featureFlag: 'enable_connectors',
        badgeKey: undefined,
        searchKeywords: ['live feeds', 'connectors', 'sftp', 'folder watch', 's3', 'cctv stream', 'ingest'],
        replaces: ['feeds', 'live-connectors'],
        description: TERMINOLOGY_DICTIONARY.live_feeds.description
      },
      {
        id: 'data_quality',
        label: TERMINOLOGY_DICTIONARY.data_quality.investigator,
        methodologyLabel: TERMINOLOGY_DICTIONARY.data_quality.methodology,
        icon: ShieldAlert,
        path: 'data-quality',
        allowedRoles: ['admin', 'lead_investigator', 'analyst'],
        badgeKey: 'data_quality_issues',
        searchKeywords: ['data quality', 'integrity', 'sha256', 'hash', 'ocr accuracy', 'section 65b', 'chain of custody'],
        replaces: ['evidence/quality', 'integrity', 'audit-hashes'],
        description: TERMINOLOGY_DICTIONARY.data_quality.description
      },
      {
        id: 'malkhana',
        label: TERMINOLOGY_DICTIONARY.malkhana.investigator,
        methodologyLabel: TERMINOLOGY_DICTIONARY.malkhana.methodology,
        icon: Archive,
        path: 'malkhana',
        allowedRoles: ['admin', 'lead_investigator', 'analyst', 'reviewer'],
        badgeKey: undefined,
        searchKeywords: ['malkhana', 'vault', 'store', 'muddimalkhana', 'rack', 'deposit', 'issue', 'qr label', 'seals'],
        replaces: ['malkhana-register', 'station-vault'],
        description: TERMINOLOGY_DICTIONARY.malkhana.description
      }
    ]
  },
  {
    id: 'people_links',
    label: 'People & links',
    icon: Users,
    openByDefault: false,
    items: [
      {
        id: 'suspects_theories',
        label: TERMINOLOGY_DICTIONARY.suspects_theories.investigator,
        methodologyLabel: TERMINOLOGY_DICTIONARY.suspects_theories.methodology,
        icon: Target,
        path: 'hypotheses',
        allowedRoles: ['admin', 'lead_investigator', 'analyst', 'reviewer'],
        badgeKey: 'unresolved_contradictions',
        searchKeywords: ['suspects', 'theories', 'hypotheses', 'ach', 'heuer', 'bayesian', 'case strength', 'prime suspect', 'alibi', 'contradictions', 'profiles'],
        replaces: ['suspects', 'ach', 'theories', 'contradictions', 'statement-conflicts'],
        description: TERMINOLOGY_DICTIONARY.suspects_theories.description,
        defaultTab: 'theories',
        tabs: [
          { id: 'theories', label: 'Case Theories', methodologyLabel: 'Hypotheses (ACH)' },
          { id: 'profiles', label: 'Suspect Profiles', methodologyLabel: 'Background & Priors' },
          { id: 'contradictions', label: 'Alibi & Conflicts', methodologyLabel: 'Contradiction Engine' }
        ]
      },
      {
        id: 'witnesses',
        label: TERMINOLOGY_DICTIONARY.witnesses.investigator,
        methodologyLabel: TERMINOLOGY_DICTIONARY.witnesses.methodology,
        icon: Mic,
        path: 'interviews',
        allowedRoles: ['admin', 'lead_investigator', 'analyst', 'reviewer'],
        badgeKey: undefined,
        searchKeywords: ['witnesses', 'statements', 'interviews', 'confessions', 'section 161', 'audio transcripts'],
        replaces: ['witnesses', 'statements'],
        description: TERMINOLOGY_DICTIONARY.witnesses.description
      },
      {
        id: 'link_analysis',
        label: TERMINOLOGY_DICTIONARY.link_analysis.investigator,
        methodologyLabel: TERMINOLOGY_DICTIONARY.link_analysis.methodology,
        icon: Network,
        path: 'link-analysis',
        allowedRoles: ['admin', 'lead_investigator', 'analyst', 'reviewer'],
        badgeKey: undefined,
        searchKeywords: ['link analysis', 'knowledge graph', 'entities', 'network', 'relationships', 'people and places', 'workspace', 'cross-case'],
        replaces: ['graph', 'entities', 'analysis', 'workspace', 'cross-case', 'cross-case-intelligence'],
        description: TERMINOLOGY_DICTIONARY.link_analysis.description,
        defaultTab: 'network',
        tabs: [
          { id: 'network', label: 'Network Graph', methodologyLabel: 'Knowledge Graph' },
          { id: 'entities', label: 'People & Places', methodologyLabel: 'Entity Registry' },
          { id: 'workspace', label: 'Analysis Workspace', methodologyLabel: 'Relationship Matrix' },
          { id: 'cross-case', label: 'Cross-Case Intel', methodologyLabel: 'Inter-Agency Matcher' }
        ]
      },
      {
        id: 'phone_bank',
        label: TERMINOLOGY_DICTIONARY.phone_bank.investigator,
        methodologyLabel: TERMINOLOGY_DICTIONARY.phone_bank.methodology,
        icon: Radio,
        path: 'telecom-financial',
        allowedRoles: ['admin', 'lead_investigator', 'analyst', 'reviewer'],
        badgeKey: undefined,
        searchKeywords: ['phone', 'bank', 'cdr', 'call details', 'imei', 'tower dump', 'financial transactions', 'bank statements'],
        replaces: ['cdr', 'financial', 'cdr-financial'],
        description: TERMINOLOGY_DICTIONARY.phone_bank.description
      },
      {
        id: 'map_timeline',
        label: TERMINOLOGY_DICTIONARY.map_timeline.investigator,
        methodologyLabel: TERMINOLOGY_DICTIONARY.map_timeline.methodology,
        icon: Map,
        path: 'timeline',
        allowedRoles: ['admin', 'lead_investigator', 'analyst', 'reviewer'],
        badgeKey: undefined,
        searchKeywords: ['map', 'timeline', 'locations', 'geo', 'coordinates', 'chronology', 'sequence of events'],
        replaces: ['map', 'case-map', 'timeline-map'],
        description: TERMINOLOGY_DICTIONARY.map_timeline.description,
        defaultTab: 'timeline',
        tabs: [
          { id: 'timeline', label: 'Timeline Chronology', methodologyLabel: 'Temporal Analysis' },
          { id: 'map', label: 'Crime Scene Map', methodologyLabel: 'Geospatial Analysis' }
        ]
      }
    ]
  },
  {
    id: 'closing_case',
    label: 'Closing the case',
    icon: Scale,
    openByDefault: false,
    items: [
      {
        id: 'missing_evidence',
        label: TERMINOLOGY_DICTIONARY.missing_evidence.investigator,
        methodologyLabel: TERMINOLOGY_DICTIONARY.missing_evidence.methodology,
        icon: CheckSquare,
        path: 'investigation-plan',
        allowedRoles: ['admin', 'lead_investigator', 'analyst', 'reviewer'],
        badgeKey: 'critical_gaps',
        searchKeywords: ['missing evidence', 'gaps', 'investigation plan', 'tasks', 'action items', 'proof needed', 'what is missing'],
        replaces: ['plan', 'missing-evidence', 'gaps'],
        description: TERMINOLOGY_DICTIONARY.missing_evidence.description
      },
      {
        id: 'defense_stress_test',
        label: TERMINOLOGY_DICTIONARY.defense_stress_test.investigator,
        methodologyLabel: TERMINOLOGY_DICTIONARY.defense_stress_test.methodology,
        icon: ShieldAlert,
        path: 'defense-stress-test',
        allowedRoles: ['admin', 'lead_investigator', 'analyst', 'reviewer'],
        badgeKey: undefined,
        searchKeywords: ['defense stress test', 'devils advocate', 'reasonable doubt', 'court test', 'cross examination', 'suppression'],
        replaces: ['devils-advocate', 'stress-test', 'court-test'],
        description: TERMINOLOGY_DICTIONARY.defense_stress_test.description
      },
      {
        id: 'chargesheet',
        label: TERMINOLOGY_DICTIONARY.chargesheet.investigator,
        methodologyLabel: TERMINOLOGY_DICTIONARY.chargesheet.methodology,
        icon: Scale,
        path: 'chargesheet',
        allowedRoles: ['admin', 'lead_investigator', 'reviewer'],
        badgeKey: undefined,
        searchKeywords: ['chargesheet', 'final report', 'court docket', 'section 173 crpc', 'section 193 bnss', 'filing'],
        replaces: ['docket', 'chargesheet-assistant', 'final-report'],
        description: TERMINOLOGY_DICTIONARY.chargesheet.description
      }
    ]
  },
  {
    id: 'team',
    label: 'Team',
    icon: ClipboardList,
    openByDefault: false,
    items: [
      {
        id: 'handover',
        label: TERMINOLOGY_DICTIONARY.handover.investigator,
        methodologyLabel: TERMINOLOGY_DICTIONARY.handover.methodology,
        icon: ClipboardList,
        path: 'handover',
        allowedRoles: ['admin', 'lead_investigator', 'analyst', 'reviewer'],
        badgeKey: 'handover_changed',
        searchKeywords: ['handover', 'shift handover', 'officer transfer', 'briefing', 'active locks', 'memo'],
        replaces: ['shift-handover', 'transfer'],
        description: TERMINOLOGY_DICTIONARY.handover.description
      },
      {
        id: 'activity_log',
        label: TERMINOLOGY_DICTIONARY.activity_log.investigator,
        methodologyLabel: TERMINOLOGY_DICTIONARY.activity_log.methodology,
        icon: Activity,
        path: 'activity',
        allowedRoles: ['admin', 'lead_investigator', 'analyst', 'reviewer'],
        badgeKey: undefined,
        searchKeywords: ['activity log', 'audit trail', 'who did what', 'timestamp', 'evidence logged', 'user actions'],
        replaces: ['activity-log', 'audit', 'case-activity'],
        description: TERMINOLOGY_DICTIONARY.activity_log.description
      },
      {
        id: 'reports',
        label: TERMINOLOGY_DICTIONARY.reports.investigator,
        methodologyLabel: TERMINOLOGY_DICTIONARY.reports.methodology,
        icon: BarChart2,
        path: 'reports',
        allowedRoles: ['admin', 'lead_investigator', 'analyst', 'reviewer'],
        badgeKey: undefined,
        searchKeywords: ['reports', 'case briefs', 'export', 'pdf', 'executive summary', 'prosecution pack'],
        replaces: ['case-reports', 'exports', 'briefing-pack'],
        description: TERMINOLOGY_DICTIONARY.reports.description
      }
    ]
  }
];

export const SETTINGS_TECHNICAL_ITEMS: CaseNavItem[] = [
  {
    id: 'config',
    label: 'Scoring Rules',
    methodologyLabel: 'Scoring Configuration',
    icon: Sliders,
    path: 'config',
    allowedRoles: ['admin', 'lead_investigator'],
    searchKeywords: ['scoring', 'weights', 'config', 'ach parameters', 'lr bounds'],
    replaces: ['scoring-config'],
    description: 'Customize forensic test likelihood ratio baselines and reliability coefficients'
  },
  {
    id: 'responsible_use',
    label: 'Responsible Use & Legal Limits',
    methodologyLabel: 'Section 54 IEA Safeguards',
    icon: Shield,
    path: 'responsible-use',
    allowedRoles: ['admin', 'lead_investigator', 'analyst', 'reviewer'],
    searchKeywords: ['responsible use', 'legal safeguards', 'section 54 iea', 'character evidence', 'ai limits'],
    replaces: ['limits', 'compliance'],
    description: 'Statutory character evidence partitions, non-verdict disclaimers, and human-in-the-loop controls'
  }
];

// Compatibility exports so navigationConfig and caseNav can be used interchangeably
export const CASE_NAVIGATION_GROUPS = CASE_NAV_GROUPS;
export const ADMIN_SETTINGS_ITEMS = SETTINGS_TECHNICAL_ITEMS;
export const ALL_NAV_ITEMS: CaseNavItem[] = [
  ...CASE_NAV_GROUPS.flatMap(g => g.items),
  ...SETTINGS_TECHNICAL_ITEMS
];

// Helper to look up item by current subpath
export function findNavItemByPath(subpath: string): CaseNavItem | undefined {
  const clean = subpath.replace(/^\//, '').split('?')[0];
  return ALL_NAV_ITEMS.find(item => item.path === clean || item.replaces?.includes(clean));
}

// Helper to look up parent group by subpath
export function findGroupForSubpath(subpath: string): CaseNavGroup | undefined {
  const clean = subpath.replace(/^\//, '').split('?')[0];
  return CASE_NAV_GROUPS.find(g => 
    g.items.some(item => item.path === clean || item.replaces?.includes(clean))
  );
}
