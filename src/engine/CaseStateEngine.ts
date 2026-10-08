import { Case, Evidence, Entity, TimelineEvent, Hypothesis, Contradiction, InvestigationTask, Relationship } from '../types';
import { mockCases, mockEvidence, mockEntities, mockTimeline, mockHypotheses, mockContradictions, mockInvestigationTasks } from '../mock-data';

export const CASE_ALIASES: Record<string, string[]> = {
  '1': ['1', 'fir-2009-mh-pun-534', 'pujari', 'raut'],
  'fir-2009-mh-pun-534': ['1', 'fir-2009-mh-pun-534', 'pujari', 'raut'],

  '2': ['2', 'cr-2024-mh-pun-0042', 'cyber', 'heist'],
  'cr-2024-mh-pun-0042': ['2', 'cr-2024-mh-pun-0042', 'cyber', 'heist'],

  '3': ['3', 'fir-2023-ka-blr-0891', 'indiranagar', 'homicide'],
  'fir-2023-ka-blr-0891': ['3', 'fir-2023-ka-blr-0891', 'indiranagar', 'homicide'],

  '4': ['4', 'op-blackout-2024-w', 'blackout', 'grid'],
  'op-blackout-2024-w': ['4', 'op-blackout-2024-w', 'blackout', 'grid'],

  '5': ['5', 'cbi-2008-up-noi-001', 'aarushi', 'talwar'],
  'cbi-2008-up-noi-001': ['5', 'cbi-2008-up-noi-001', 'aarushi', 'talwar'],

  '6': ['6', 'bpd-2013-ma-bos-0415', 'boston', 'marathon'],
  'bpd-2013-ma-bos-0415': ['6', 'bpd-2013-ma-bos-0415', 'boston', 'marathon'],
};

export function matchesCase(itemCaseId: string | number | undefined, queryCaseId: string | number | undefined): boolean {
  if (!itemCaseId || !queryCaseId) return false;
  const sItem = String(itemCaseId).trim().toLowerCase();
  const sQuery = String(queryCaseId).trim().toLowerCase();
  if (sItem === sQuery) return true;

  const queryAliases = CASE_ALIASES[sQuery];
  if (queryAliases && queryAliases.includes(sItem)) return true;

  const itemAliases = CASE_ALIASES[sItem];
  if (itemAliases && itemAliases.includes(sQuery)) return true;

  return false;
}

export class CaseStateEngine {
  private static instance: CaseStateEngine;

  private cases: Case[] = [...mockCases];
  private evidence: Evidence[] = [...mockEvidence];
  private entities: Entity[] = [...mockEntities];
  private timeline: TimelineEvent[] = [...mockTimeline];
  private hypotheses: Hypothesis[] = [...mockHypotheses];
  private contradictions: Contradiction[] = [...mockContradictions];
  private tasks: InvestigationTask[] = [...mockInvestigationTasks];
  private relationships: Relationship[] = [];

  // Pub/Sub for React reactivity
  private listeners: Array<() => void> = [];

  private constructor() { }

  public static getInstance(): CaseStateEngine {
    if (!CaseStateEngine.instance) {
      CaseStateEngine.instance = new CaseStateEngine();
    }
    return CaseStateEngine.instance;
  }

  public subscribe(listener: () => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  public notifyListeners() {
    this.listeners.forEach(listener => listener());
  }

  // --- Getters with intelligent case matching ---
  public getCases(): Case[] { return this.cases; }

  public getCaseById(id: string): Case | undefined {
    return this.cases.find(c => String(c.id) === String(id) || matchesCase(c.id, id));
  }

  public getAllEvidence(): Evidence[] {
    return this.evidence;
  }

  public getEvidenceForCase(caseId: string): Evidence[] {
    return this.evidence.filter(e => matchesCase(e.caseId || (e as any).case_id, caseId));
  }

  public getEntitiesForCase(caseId: string): Entity[] {
    return this.entities.filter(e => matchesCase(e.caseId || (e as any).case_id, caseId));
  }

  public getTimelineForCase(caseId: string): TimelineEvent[] {
    return this.timeline.filter(e => matchesCase(e.caseId || (e as any).case_id, caseId));
  }

  public getHypothesesForCase(caseId: string): Hypothesis[] {
    return this.hypotheses.filter(h => matchesCase(h.caseId || (h as any).case_id, caseId));
  }

  public getContradictionsForCase(caseId: string): Contradiction[] {
    return this.contradictions.filter(c => matchesCase(c.caseId || (c as any).case_id, caseId));
  }

  public getTasksForCase(caseId: string): InvestigationTask[] {
    return this.tasks.filter(t => matchesCase(t.caseId || (t as any).case_id, caseId));
  }

  // --- Mutators ---
  public addOrUpdateCase(newCase: Case) {
    const idx = this.cases.findIndex(c => String(c.id) === String(newCase.id) || matchesCase(c.id, newCase.id));
    if (idx >= 0) {
      this.cases[idx] = { ...this.cases[idx], ...newCase };
    } else {
      this.cases.unshift(newCase);
    }
    this.notifyListeners();
  }

  public registerBackendCases(backendCases: Case[]) {
    backendCases.forEach(bc => {
      const idx = this.cases.findIndex(c => String(c.id) === String(bc.id) || matchesCase(c.id, bc.id));
      if (idx >= 0) {
        this.cases[idx] = { ...this.cases[idx], ...bc };
      } else {
        this.cases.unshift(bc);
      }
    });
    this.notifyListeners();
  }

  public addEvidence(newEvidence: Evidence) {
    this.evidence.push(newEvidence);
    this.notifyListeners();
  }

  public updateEvidenceStatus(evidenceId: string, status: Evidence['processingStatus']) {
    const ev = this.evidence.find(e => String(e.id) === String(evidenceId));
    if (ev) {
      ev.processingStatus = status;
      this.notifyListeners();
    }
  }

  public addEntity(newEntity: Entity) {
    this.entities.push(newEntity);
    this.notifyListeners();
  }

  public addTimelineEvent(newEvent: TimelineEvent) {
    this.timeline.push(newEvent);
    this.notifyListeners();
  }

  public addContradiction(newContradiction: Contradiction) {
    this.contradictions.push(newContradiction);
    this.notifyListeners();
  }

  public updateHypothesisConfidence(hypothesisId: string, newConfidence: number) {
    const hyp = this.hypotheses.find(h => String(h.id) === String(hypothesisId));
    if (hyp) {
      hyp.confidence = newConfidence;
      this.notifyListeners();
    }
  }

  public addTask(newTask: InvestigationTask) {
    this.tasks.push(newTask);
    this.notifyListeners();
  }

  public getRelationshipsForCase(caseId: string): Relationship[] {
    return this.relationships.filter(r => matchesCase(r.caseId, caseId));
  }

  public setRelationshipsForCase(caseId: string, rels: Relationship[]) {
    this.relationships = this.relationships.filter(r => !matchesCase(r.caseId, caseId)).concat(rels);
    this.notifyListeners();
  }

  public addRelationship(rel: Relationship) {
    this.relationships.push(rel);
    this.notifyListeners();
  }
}

