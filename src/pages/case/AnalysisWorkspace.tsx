import { useParams, Link } from 'react-router-dom';
import { useEffect, useState, useMemo } from 'react';
import { evidenceService, entityService, hypothesisService, contradictionService } from '../../services';
import type { Evidence, Entity, Hypothesis, Contradiction } from '../../types';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { FileText, Users, Lightbulb, AlertTriangle, BrainCircuit, TrendingUp, ExternalLink } from 'lucide-react';
import { cn } from '../../utils';

export function AnalysisWorkspace() {
  const { caseId } = useParams();
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
  const [contradictions, setContradictions] = useState<Contradiction[]>([]);

  useEffect(() => {
    if (!caseId) return;
    Promise.all([
      evidenceService.getEvidenceForCase(caseId),
      entityService.getEntitiesForCase(caseId),
      hypothesisService.getHypothesesForCase(caseId),
      contradictionService.getContradictionsForCase(caseId),
    ]).then(([ev, ent, hyp, con]) => {
      setEvidence(ev);
      setEntities(ent);
      setHypotheses(hyp);
      setContradictions(con);
    });
  }, [caseId]);

  const summaryStats = useMemo(() => {
    const analyzed = evidence.filter(e => e.processingStatus === 'Analyzed').length;
    const processing = evidence.filter(e => e.processingStatus === 'Processing').length;
    const highConfidence = entities.filter(e => e.confidence >= 90).length;
    const activeHypotheses = hypotheses.filter(h => h.status === 'Active').length;
    const unresolvedContradictions = contradictions.filter(c => c.status !== 'Resolved' && c.status !== 'Dismissed').length;
    return { analyzed, processing, highConfidence, activeHypotheses, unresolvedContradictions };
  }, [evidence, entities, hypotheses, contradictions]);

  const evidenceByType = useMemo(() => {
    const map = new Map<string, Evidence[]>();
    for (const ev of evidence) {
      const list = map.get(ev.fileType) ?? [];
      list.push(ev);
      map.set(ev.fileType, list);
    }
    return map;
  }, [evidence]);

  const entityByType = useMemo(() => {
    const map = new Map<string, Entity[]>();
    for (const ent of entities) {
      const list = map.get(ent.type) ?? [];
      list.push(ent);
      map.set(ent.type, list);
    }
    return map;
  }, [entities]);

  return (
    <div className="space-y-6 pb-20">
      <div>
        <h1 className="text-2xl font-serif font-bold text-[#191410] mb-1">Analysis Workspace</h1>
        <p className="text-sm text-text-muted">Cross-reference evidence, entities, and hypotheses to identify patterns and gaps.</p>
      </div>

      {/* Summary KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {[
          { label: 'Evidence Analyzed', value: summaryStats.analyzed, of: evidence.length, icon: FileText, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20' },
          { label: 'Processing', value: summaryStats.processing, of: evidence.length, icon: BrainCircuit, color: 'text-purple-400', bg: 'bg-purple-500/10 border-purple-500/20' },
          { label: 'High-Confidence Entities', value: summaryStats.highConfidence, of: entities.length, icon: Users, color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/20' },
          { label: 'Active Hypotheses', value: summaryStats.activeHypotheses, of: hypotheses.length, icon: Lightbulb, color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/20' },
          { label: 'Unresolved Conflicts', value: summaryStats.unresolvedContradictions, of: contradictions.length, icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/20' },
        ].map(s => (
          <Card key={s.label} className="p-4 flex items-center gap-3">
            <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center border shrink-0', s.bg)}>
              <s.icon className={cn('w-5 h-5', s.color)} />
            </div>
            <div>
              <div className="text-xl font-serif font-bold text-[#191410]">{s.value}<span className="text-sm font-normal text-text-muted">/{s.of}</span></div>
              <div className="text-[10px] text-text-muted uppercase tracking-wider font-semibold leading-tight">{s.label}</div>
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Evidence by Type */}
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><FileText className="w-5 h-5 text-blue-400" /> Evidence by Type</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Array.from(evidenceByType.entries()).map(([type, items]) => {
                const analyzedCount = items.filter(e => e.processingStatus === 'Analyzed').length;
                const pct = items.length > 0 ? (analyzedCount / items.length) * 100 : 0;
                return (
                  <div key={type}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-text font-medium">{type}</span>
                      <span className="text-text-muted">{analyzedCount}/{items.length} analyzed</span>
                    </div>
                    <div className="h-1.5 w-full bg-surface-hover rounded-full overflow-hidden">
                      <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Entity Breakdown */}
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Users className="w-5 h-5 text-green-400" /> Entity Breakdown</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Array.from(entityByType.entries()).map(([type, items]) => {
                const avgConfidence = items.length > 0 ? Math.round(items.reduce((s, e) => s + e.confidence, 0) / items.length) : 0;
                return (
                  <div key={type} className="flex items-center justify-between p-3 rounded-lg bg-surface/50 border border-border/50">
                    <div>
                      <div className="text-sm font-medium text-[#191410]">{type}</div>
                      <div className="text-xs text-text-muted">{items.length} extracted</div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-bold text-[#191410]">{avgConfidence}%</div>
                      <div className="text-[10px] text-text-muted uppercase font-mono">Avg Conf</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Hypothesis Confidence Ranking */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="flex items-center gap-2"><TrendingUp className="w-5 h-5 text-amber-500" /> Hypothesis Confidence Ranking</CardTitle>
            <Link to={`/cases/${caseId}/hypotheses`} className="text-xs font-bold text-[#d93829] hover:underline flex items-center gap-1">
              Matrix View <ExternalLink className="w-3 h-3" />
            </Link>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[...hypotheses].sort((a, b) => b.confidence - a.confidence).map(h => (
                <Link 
                  key={h.id} 
                  to={`/cases/${caseId}/hypotheses`}
                  className="flex items-center gap-4 p-3 rounded-lg bg-[#faf7f2] hover:bg-[#f5efe6] border border-[#eae4d9] hover:border-[#d93829] transition-all group block cursor-pointer"
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-[#191410] truncate group-hover:text-[#d93829] transition-colors">{h.title}</div>
                    <div className="text-xs text-text-muted mt-0.5 font-mono">
                      {h.supportingEvidenceIds.length} supporting / {h.contradictingEvidenceIds.length} contradicting
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <div className="w-16 h-1.5 bg-[#eae4d9] rounded-full overflow-hidden">
                      <div
                        className={cn('h-full rounded-full', h.confidence >= 70 ? 'bg-emerald-500' : h.confidence >= 40 ? 'bg-amber-500' : 'bg-rose-500')}
                        style={{ width: `${h.confidence}%` }}
                      />
                    </div>
                    <span className="text-sm font-bold font-mono text-[#191410] w-10 text-right">{h.confidence}%</span>
                  </div>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Evidence Processing Status */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="flex items-center gap-2"><BrainCircuit className="w-5 h-5 text-purple-500" /> Evidence Processing Queue</CardTitle>
            <Link to={`/cases/${caseId}/evidence`} className="text-xs font-bold text-[#d93829] hover:underline flex items-center gap-1">
              All Evidence <ExternalLink className="w-3 h-3" />
            </Link>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {evidence.map(ev => (
                <Link 
                  key={ev.id} 
                  to={`/cases/${caseId}/evidence/${ev.id}`}
                  className="flex items-center gap-3 p-2.5 rounded-lg bg-[#faf7f2] hover:bg-[#f5efe6] border border-[#eae4d9] hover:border-purple-300 transition-all group cursor-pointer block"
                >
                  <div className={cn(
                    'w-2 h-2 rounded-full shrink-0',
                    ev.processingStatus === 'Analyzed' ? 'bg-emerald-500' :
                    ev.processingStatus === 'Processing' ? 'bg-blue-500 animate-pulse' :
                    ev.processingStatus === 'Queued' ? 'bg-amber-500' : 'bg-stone-300'
                  )} />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-bold text-[#191410] truncate group-hover:text-[#d93829] transition-colors">{ev.fileName}</div>
                    <div className="text-[10px] text-text-muted font-mono">{ev.id} • {ev.fileType}</div>
                  </div>
                  <span className={cn(
                    'text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border shrink-0',
                    ev.processingStatus === 'Analyzed' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                    ev.processingStatus === 'Processing' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                    ev.processingStatus === 'Queued' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                    'bg-stone-100 text-stone-600 border-stone-200'
                  )}>
                    {ev.processingStatus}
                  </span>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
