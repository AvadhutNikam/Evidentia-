import { useParams } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';
import { CaseStateEngine } from '../../engine/CaseStateEngine';
import { relationshipService } from '../../services';
import type { Entity, Evidence, TimelineEvent, Hypothesis, Relationship, InvestigationNode, InvestigationEdge } from '../../types';
import { InvestigationBoard } from '../../components/graph/InvestigationBoard';
import { Sparkles, RefreshCw, Network, ShieldCheck } from 'lucide-react';
import { cn } from '../../utils';

/**
 * Derives graph nodes and edges from raw case data and explicit semantic relationships.
 * Transforms generic co-occurrence ("co-mentioned") into directed semantic forensic predicates:
 * Person A ── called ────► Person B
 * Person A ── met ───────► Person C
 * Person A ── visited ───► Location X
 * Person A ── drove ─────► Vehicle Y
 */
function deriveGraphData(
  entities: Entity[],
  evidence: Evidence[],
  timeline: TimelineEvent[],
  hypotheses: Hypothesis[],
  relationships: Relationship[] = [],
): { nodes: InvestigationNode[]; edges: InvestigationEdge[] } {
  const nodes: InvestigationNode[] = [];
  const edges: InvestigationEdge[] = [];
  const edgeSet = new Set<string>();

  const addEdge = (
    src: string,
    tgt: string,
    label: string,
    type: InvestigationEdge['type'],
    confidence?: number,
    reason?: string
  ) => {
    if (!src || !tgt) return;
    const key = `${src}::${tgt}::${type}`;
    const revKey = `${tgt}::${src}::${type}`;
    if (edgeSet.has(key) || edgeSet.has(revKey)) return;
    edgeSet.add(key);
    edges.push({
      id: `e-${edges.length}`,
      source: src,
      target: tgt,
      label,
      type,
      confidence,
      reason
    });
  };

  // 1. Entity nodes
  for (const entity of (entities || [])) {
    if (!entity) continue;
    nodes.push({ id: String(entity.id), label: entity.name || 'Entity', type: entity.type || 'Person' });
  }

  // 2. Evidence nodes
  for (const ev of (evidence || [])) {
    if (!ev) continue;
    nodes.push({ id: String(ev.id), label: ev.fileName || (ev as any).file_name || 'Evidence', type: 'Evidence' });
  }

  // 3. Timeline event nodes
  for (const event of (timeline || [])) {
    if (!event) continue;
    nodes.push({ id: String(event.id), label: event.title || 'Event', type: 'TimelineEvent' });
  }

  // 4. Hypothesis nodes
  for (const h of (hypotheses || [])) {
    if (!h) continue;
    nodes.push({ id: String(h.id), label: h.title || 'Hypothesis', type: 'Hypothesis' });
  }

  // 5. Explicit Semantic Relationships (HIGHEST PRIORITY)
  // Person A ── called ── Person B / Person A ── visited ── Location X / etc.
  const semanticallyConnectedPairs = new Set<string>();
  for (const rel of (relationships || [])) {
    if (!rel || !rel.sourceEntityId || !rel.targetEntityId) continue;
    const src = String(rel.sourceEntityId).replace(/^ENT-/, '');
    const tgt = String(rel.targetEntityId).replace(/^ENT-/, '');
    const cleanLabel = (rel.relationType || 'related to').replace(/_/g, ' ');
    
    // Track pair so we don't emit fallback co-mentioned for the same entities
    semanticallyConnectedPairs.add(`${src}::${tgt}`);
    semanticallyConnectedPairs.add(`${tgt}::${src}`);

    addEdge(
      src,
      tgt,
      cleanLabel,
      rel.relationType || 'semantic_relation',
      rel.confidence,
      rel.reason
    );
  }

  // 6. Edges: Entity -> Evidence (entity references evidence)
  for (const entity of (entities || [])) {
    if (!entity) continue;
    const srcEvs = Array.isArray(entity.sourceEvidenceIds)
      ? entity.sourceEvidenceIds
      : ((entity as any).evidence_id ? [String((entity as any).evidence_id)] : []);
    for (const evidenceId of srcEvs) {
      if (evidenceId) addEdge(String(entity.id), String(evidenceId), 'sourced from', 'sourced_from');
    }
  }

  // 7. Edges: Entity <-> Entity (Fallback co-mentioned via shared evidence ONLY if no explicit relationship exists)
  for (const ev of (evidence || [])) {
    if (!ev) continue;
    const evId = String(ev.id);
    const connected = (entities || []).filter(e => {
      if (!e) return false;
      const ids = Array.isArray(e.sourceEvidenceIds) ? e.sourceEvidenceIds.map(String) : [];
      if ((e as any).evidence_id) ids.push(String((e as any).evidence_id));
      return ids.includes(evId);
    });
    for (let i = 0; i < connected.length; i++) {
      for (let j = i + 1; j < connected.length; j++) {
        const idA = String(connected[i].id).replace(/^ENT-/, '');
        const idB = String(connected[j].id).replace(/^ENT-/, '');
        // Only emit if no direct semantic relationship already connects them
        if (!semanticallyConnectedPairs.has(`${idA}::${idB}`)) {
          addEdge(idA, idB, `shared: ${ev.fileName || evId}`, 'co_mentioned');
        }
      }
    }
  }

  // 8. Edges: TimelineEvent -> Entity (event involves entities)
  for (const event of (timeline || [])) {
    if (!event) continue;
    const entIds = Array.isArray(event.relatedEntityIds)
      ? event.relatedEntityIds
      : (Array.isArray((event as any).entitiesInvolved) ? (event as any).entitiesInvolved : []);
    for (const entityId of entIds) {
      if (entityId) addEdge(String(event.id), String(entityId), 'involves', 'involves');
    }
    // Also connect to source evidence
    const srcEv = event.sourceEvidenceId || (event as any).evidence_id;
    if (srcEv) {
      addEdge(String(event.id), String(srcEv), 'sourced from', 'sourced_from');
    }
  }

  // 9. Edges: Hypothesis -> Entity & Evidence
  for (const h of (hypotheses || [])) {
    if (!h) continue;
    const entIds = Array.isArray(h.relatedEntityIds) ? h.relatedEntityIds : [];
    for (const entityId of entIds) {
      if (entityId) addEdge(String(h.id), String(entityId), 'references', 'references');
    }
    const supIds = Array.isArray(h.supportingEvidenceIds) ? h.supportingEvidenceIds : [];
    for (const eid of supIds) {
      if (eid) addEdge(String(h.id), String(eid), 'supports', 'supports');
    }
    const conIds = Array.isArray(h.contradictingEvidenceIds) ? h.contradictingEvidenceIds : [];
    for (const eid of conIds) {
      if (eid) addEdge(String(h.id), String(eid), 'contradicts', 'contradicts');
    }
  }

  return { nodes, edges };
}

export function KnowledgeGraph() {
  const { caseId } = useParams();
  const engine = CaseStateEngine.getInstance();
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractMsg, setExtractMsg] = useState<string | null>(null);

  const [snapshot, setSnapshot] = useState(() => ({
    entities: caseId ? engine.getEntitiesForCase(caseId) : [],
    evidence: caseId ? engine.getEvidenceForCase(caseId) : [],
    timeline: caseId ? engine.getTimelineForCase(caseId) : [],
    hypotheses: caseId ? engine.getHypothesesForCase(caseId) : [],
    relationships: caseId ? engine.getRelationshipsForCase(caseId) : [],
    caseData: caseId ? engine.getCaseById(caseId) : null,
  }));

  const loadData = () => {
    if (!caseId) return;
    setSnapshot({
      entities: engine.getEntitiesForCase(caseId),
      evidence: engine.getEvidenceForCase(caseId),
      timeline: engine.getTimelineForCase(caseId),
      hypotheses: engine.getHypothesesForCase(caseId),
      relationships: engine.getRelationshipsForCase(caseId),
      caseData: engine.getCaseById(caseId) || null,
    });
  };

  useEffect(() => {
    if (!caseId) return;
    loadData();

    // Fetch live semantic relationships from backend
    relationshipService.getRelationshipsForCase(caseId).then(rels => {
      if (rels && rels.length > 0) {
        setSnapshot(prev => ({ ...prev, relationships: rels }));
      }
    });

    // Subscribe to engine changes
    return engine.subscribe(loadData);
  }, [caseId, engine]);

  const handleExtractRelationships = async () => {
    if (!caseId || isExtracting) return;
    setIsExtracting(true);
    setExtractMsg('Extracting explicit semantic relationships via Gemini...');
    try {
      const rels = await relationshipService.extractRelationships(caseId);
      setSnapshot(prev => ({ ...prev, relationships: rels }));
      setExtractMsg(`Discovered ${rels.length} explicit forensic semantic relationships!`);
      setTimeout(() => setExtractMsg(null), 5000);
    } catch (err) {
      console.error('Extraction failed:', err);
      setExtractMsg('Relationship extraction error. Check backend connection.');
      setTimeout(() => setExtractMsg(null), 5000);
    } finally {
      setIsExtracting(false);
    }
  };

  const { entities, evidence, timeline, hypotheses, relationships, caseData } = snapshot;

  const { nodes, edges } = useMemo(
    () => deriveGraphData(entities, evidence, timeline, hypotheses, relationships),
    [entities, evidence, timeline, hypotheses, relationships],
  );

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col gap-4">
      {/* Header with Title and Action Button */}
      <div className="shrink-0 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/40 pb-3">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-serif font-bold text-[#191410] mb-0.5">Investigation Board</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-700 border border-blue-500/20 flex items-center gap-1">
              <Network className="w-3 h-3" />
              Forensic Intelligence Graph
            </span>
            {relationships.length > 0 && (
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-700 border border-emerald-500/20 flex items-center gap-1">
                <ShieldCheck className="w-3 h-3" />
                {relationships.length} Semantic Links
              </span>
            )}
          </div>
          <p className="text-sm text-[#6e665d]">
            Semantic entity-to-entity relationship graph. Explicit forensic links (<span className="font-mono text-xs font-semibold text-blue-600">called</span>, <span className="font-mono text-xs font-semibold text-purple-600">met</span>, <span className="font-mono text-xs font-semibold text-emerald-600">visited</span>, <span className="font-mono text-xs font-semibold text-amber-600">drove</span>) replace weak co-occurrence links.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {extractMsg && (
            <span className="text-xs text-amber-700 font-medium animate-fade-in truncate max-w-[260px]" title={extractMsg}>
              {extractMsg}
            </span>
          )}
          <button
            onClick={handleExtractRelationships}
            disabled={isExtracting}
            className={cn(
              "flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all shadow-sm",
              isExtracting
                ? "bg-amber-500/20 text-amber-700 border border-amber-500/30 cursor-wait"
                : "bg-primary hover:bg-primary-hover text-white shadow-primary/20 active:scale-98"
            )}
          >
            {isExtracting ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Extracting Relations...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                <span>Extract Semantic Relationships</span>
              </>
            )}
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0">
        <InvestigationBoard
          nodes={nodes}
          edges={edges}
          entities={entities}
          evidenceItems={evidence}
          timelineEvents={timeline}
          hypotheses={hypotheses}
          caseId={caseId ?? ''}
          caseName={caseData?.title || caseData?.name || ''}
        />
      </div>
    </div>
  );
}
