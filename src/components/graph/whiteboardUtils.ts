import type { InvestigationNode, InvestigationEdge, Entity, Evidence, TimelineEvent, Hypothesis } from '../../types';

export interface ColumnHeader {
  title: string;
  subtitle: string;
  icon: string;
  x: number;
  y: number;
  width: number;
  color: string;
}

export interface InvestigationStage {
  id: number;
  label: string;
  dateStr: string;
  title: string;
  description: string;
  nodeIds: string[];
}

export const CARD_WIDTH = 270;
export const CARD_HEIGHTS: Record<string, number> = {
  Person: 200,
  Organization: 160,
  Location: 160,
  Vehicle: 140,
  Event: 140,
  Other: 140,
  Evidence: 220,
  TimelineEvent: 240,
  Hypothesis: 220,
  Note: 180,
};

/**
 * Computes an organized, non-overlapping crime whiteboard layout with 
 * designated columns for Chronology, Suspects, Forensic Exhibits, and Hypotheses.
 */
export function computeStructuredWhiteboardLayout(
  nodes: InvestigationNode[],
  timelineEvents: TimelineEvent[] = [],
  entities: Entity[] = [],
  evidenceItems: Evidence[] = [],
  hypotheses: Hypothesis[] = [],
): {
  positions: Map<string, { x: number; y: number }>;
  columnHeaders: ColumnHeader[];
} {
  const positions = new Map<string, { x: number; y: number }>();
  const columnHeaders: ColumnHeader[] = [];

  // Categorize nodes
  const timelineNodes = nodes.filter(n => n.type === 'TimelineEvent');
  const personNodes = nodes.filter(n => n.type === 'Person' || n.type === 'Vehicle');
  const evidenceNodes = nodes.filter(n => n.type === 'Evidence');
  const hypothesisNodes = nodes.filter(n => n.type === 'Hypothesis');
  const otherNodes = nodes.filter(n => !['TimelineEvent', 'Person', 'Vehicle', 'Evidence', 'Hypothesis'].includes(n.type));

  // Sort timeline chronologically
  const timelineMap = new Map(timelineEvents.map(t => [t.id, new Date(t.timestamp).getTime()]));
  timelineNodes.sort((a, b) => (timelineMap.get(a.id) ?? 0) - (timelineMap.get(b.id) ?? 0));

  const startX = 380;
  const colWidth = 330;
  const cardGap = 40;
  const startY = 220;

  // Split evidence into 2 columns if more than 5 items
  const evidenceCol1 = evidenceNodes.slice(0, Math.ceil(evidenceNodes.length / 2));
  const evidenceCol2 = evidenceNodes.slice(Math.ceil(evidenceNodes.length / 2));

  // --- Column 1: Timeline of Incident (Chronology) ---
  const col1X = startX;
  let currY = startY;
  columnHeaders.push({
    title: '1. Incident Chronology',
    subtitle: 'Temporal sequence of events',
    icon: 'clock',
    x: col1X,
    y: 130,
    width: CARD_WIDTH,
    color: '#ca8a04',
  });
  timelineNodes.forEach(node => {
    positions.set(node.id, { x: col1X, y: currY });
    currY += (CARD_HEIGHTS[node.type] ?? 240) + cardGap;
  });

  // --- Column 2: Suspects & Persons of Interest ---
  const col2X = startX + colWidth;
  currY = startY;
  columnHeaders.push({
    title: '2. Persons of Interest',
    subtitle: 'Accused, accomplices & witnesses',
    icon: 'users',
    x: col2X,
    y: 130,
    width: CARD_WIDTH,
    color: '#3b82f6',
  });
  personNodes.forEach(node => {
    positions.set(node.id, { x: col2X, y: currY });
    currY += (CARD_HEIGHTS[node.type] ?? 200) + cardGap;
  });

  // --- Column 3: Physical & Digital Exhibits ---
  const col3X = startX + colWidth * 2;
  currY = startY;
  columnHeaders.push({
    title: '3. Physical & Digital Exhibits',
    subtitle: 'CCTV, CDR, vehicle & seized goods',
    icon: 'file-text',
    x: col3X,
    y: 130,
    width: CARD_WIDTH,
    color: '#64748b',
  });
  evidenceCol1.forEach(node => {
    positions.set(node.id, { x: col3X, y: currY });
    currY += (CARD_HEIGHTS[node.type] ?? 220) + cardGap;
  });

  // --- Column 4: Forensic & Lab Reports ---
  const col4X = startX + colWidth * 3;
  currY = startY;
  columnHeaders.push({
    title: '4. Forensic & Lab Reports',
    subtitle: 'FSL DNA, autopsy & turnstile logs',
    icon: 'activity',
    x: col4X,
    y: 130,
    width: CARD_WIDTH,
    color: '#0ea5e9',
  });
  evidenceCol2.forEach(node => {
    positions.set(node.id, { x: col4X, y: currY });
    currY += (CARD_HEIGHTS[node.type] ?? 220) + cardGap;
  });

  // --- Column 5: Competing Hypotheses & Legal Theories ---
  const col5X = startX + colWidth * 4;
  currY = startY;
  columnHeaders.push({
    title: '5. Competing Hypotheses',
    subtitle: 'Prosecution theories & defense claims',
    icon: 'lightbulb',
    x: col5X,
    y: 130,
    width: CARD_WIDTH,
    color: '#f97316',
  });
  hypothesisNodes.forEach(node => {
    positions.set(node.id, { x: col5X, y: currY });
    currY += (CARD_HEIGHTS[node.type] ?? 220) + cardGap;
  });

  // --- Column 6: Investigator Sticky Notes & Open Leads ---
  const col6X = startX + colWidth * 5;
  currY = startY;
  columnHeaders.push({
    title: '6. Investigator Leads & Notes',
    subtitle: 'Active memos, field leads & tips',
    icon: 'sticky-note',
    x: col6X,
    y: 130,
    width: CARD_WIDTH,
    color: '#eab308',
  });
  otherNodes.forEach(node => {
    positions.set(node.id, { x: col6X, y: currY });
    currY += (CARD_HEIGHTS[node.type] ?? 160) + cardGap;
  });

  return { positions, columnHeaders };
}

/**
 * Returns chronological investigation stages to model how police uncover 
 * clues "time to time" across the investigation.
 */
export function getInvestigationStages(
  caseId: string,
  nodes: InvestigationNode[],
): InvestigationStage[] {
  const isPujariCase = caseId.includes('534') || caseId.toLowerCase().includes('pujari');

  if (isPujariCase) {
    return [
      {
        id: 0,
        label: 'All Information',
        dateStr: 'Complete Case Docket',
        title: 'Full Solved Whiteboard',
        description: 'Complete synthesis of 26 items: Timeline, Suspects, Physical Exhibits, DNA Forensics, and Sessions Court Conviction.',
        nodeIds: nodes.map(n => n.id),
      },
      {
        id: 1,
        label: 'Stage 1',
        dateStr: '07 Oct 2009',
        title: 'Initial Abduction & Missing Report',
        description: 'Victim fails to return from Synechron Kharadi. Family lodges Missing Complaint at Yerwada PS. Eyewitness recalls white Qualis cab offering ride.',
        nodeIds: ['TL-NP-01', 'TL-NP-02', 'E-NP-001', 'ENT-NP-06'],
      },
      {
        id: 2,
        label: 'Stage 2',
        dateStr: '08 Oct 2009',
        title: 'ATM Cash Withdrawal & Bank Trail',
        description: 'Bank alerts ₹61,000 cash withdrawal across Vimannagar ATMs. ATM CCTV footage retrieved showing driver entering PIN.',
        nodeIds: ['TL-NP-01', 'TL-NP-02', 'E-NP-001', 'ENT-NP-06', 'TL-NP-03', 'E-NP-002', 'E-NP-003'],
      },
      {
        id: 3,
        label: 'Stage 3',
        dateStr: '09 Oct 2009',
        title: 'Crime Scene Discovery & Autopsy',
        description: 'Body recovered in Zarewadi forest ghat near Rajgurunagar. Aundh Civil Hospital postmortem confirms sexual assault and strangulation.',
        nodeIds: [
          'TL-NP-01', 'TL-NP-02', 'E-NP-001', 'ENT-NP-06', 'TL-NP-03', 'E-NP-002', 'E-NP-003',
          'TL-NP-04', 'E-NP-006'
        ],
      },
      {
        id: 4,
        label: 'Stage 4',
        dateStr: '16 Oct 2009',
        title: 'Suspects Apprehended & Physical Seizures',
        description: 'SIT arrests cab driver Yogesh Raut at Katraj. Sec 27 Panchnama leads to recovery of victim gold ring, ATM card, and impounded Qualis MH-12-AR-2445.',
        nodeIds: [
          'TL-NP-01', 'TL-NP-02', 'E-NP-001', 'ENT-NP-06', 'TL-NP-03', 'E-NP-002', 'E-NP-003',
          'TL-NP-04', 'E-NP-006', 'TL-NP-05', 'ENT-NP-01', 'ENT-NP-03', 'ENT-NP-04', 'E-NP-005', 'E-NP-010', 'HYP-NP-01'
        ],
      },
      {
        id: 5,
        label: 'Stage 5',
        dateStr: 'Nov 2009',
        title: 'Scientific DNA Match & Tower Triangulation',
        description: 'FSL Pune confirms 100% DNA match. CDR call logs place Yogesh Raut, Mahesh Thakur and Vishwas Kadam in the cab from Kharadi to Zarewadi.',
        nodeIds: [
          'TL-NP-01', 'TL-NP-02', 'E-NP-001', 'ENT-NP-06', 'TL-NP-03', 'E-NP-002', 'E-NP-003',
          'TL-NP-04', 'E-NP-006', 'TL-NP-05', 'ENT-NP-01', 'ENT-NP-03', 'ENT-NP-04', 'E-NP-005', 'E-NP-010', 'HYP-NP-01',
          'TL-NP-06', 'E-NP-004', 'E-NP-009', 'ENT-NP-02', 'E-NP-007', 'E-NP-008', 'HYP-NP-03'
        ],
      },
      {
        id: 6,
        label: 'Stage 6',
        dateStr: 'Sessions Verdict',
        title: 'Approver Confession & Capital Conviction',
        description: 'Security guard Rajesh Chaudhari turns approver under Sec 306 CrPC. Pune Special Court sentences prime accused Yogesh Raut, Mahesh Thakur and Vishwas Kadam to death.',
        nodeIds: nodes.map(n => n.id),
      },
    ];
  }

  // Dynamic automatic stages for any other cases
  const total = nodes.length;
  const s1 = Math.max(2, Math.floor(total * 0.25));
  const s2 = Math.max(s1 + 1, Math.floor(total * 0.5));
  const s3 = Math.max(s2 + 1, Math.floor(total * 0.75));

  return [
    {
      id: 0,
      label: 'All Information',
      dateStr: 'Complete Case',
      title: 'Full Solved Whiteboard',
      description: 'Viewing all accumulated evidence, suspects, and forensic milestones.',
      nodeIds: nodes.map(n => n.id),
    },
    {
      id: 1,
      label: 'Stage 1',
      dateStr: 'Initial Report',
      title: 'Incident Registration & First Clues',
      description: 'Initial reporting of the incident, first responders on scene, and opening case files.',
      nodeIds: nodes.slice(0, s1).map(n => n.id),
    },
    {
      id: 2,
      label: 'Stage 2',
      dateStr: 'Investigative Trail',
      title: 'Digital & Physical Exhibits Uncovered',
      description: 'Surveillance footage, forensic recoveries, and witness testimonies secured.',
      nodeIds: nodes.slice(0, s2).map(n => n.id),
    },
    {
      id: 3,
      label: 'Stage 3',
      dateStr: 'Breakthrough',
      title: 'Suspects Interrogated & Lab Matches',
      description: 'Forensic lab results return positive and prime suspects are apprehended.',
      nodeIds: nodes.slice(0, s3).map(n => n.id),
    },
    {
      id: 4,
      label: 'Stage 4',
      dateStr: 'Resolution',
      title: 'Complete Indictment & Charges Filed',
      description: 'All competing hypotheses evaluated and complete judicial charge-sheet submitted.',
      nodeIds: nodes.map(n => n.id),
    },
  ];
}
