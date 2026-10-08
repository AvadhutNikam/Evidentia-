import { useParams, Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { 
  caseService, 
  evidenceService, 
  timelineService, 
  contradictionService, 
  hypothesisService, 
  investigationService, 
  entityService 
} from '../../services';
import { Case, Evidence, TimelineEvent, Contradiction, Hypothesis, InvestigationTask, Entity } from '../../types';
import { 
  FileText, Clock, Users, AlertTriangle, Lightbulb, CheckSquare, 
  ArrowRight, ShieldCheck, MapPin, Scale, User, Calendar, 
  BookOpen, Compass, ExternalLink, Download 
} from 'lucide-react';
import { cn } from '../../utils';

export function CaseOverview() {
  const { caseId } = useParams();
  const [data, setData] = useState<{
    currentCase: Case;
    evidence: Evidence[];
    timeline: TimelineEvent[];
    entities: Entity[];
    contradictions: Contradiction[];
    hypotheses: Hypothesis[];
    tasks: InvestigationTask[];
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!caseId) return;
    setLoading(true);
    Promise.all([
      caseService.getCaseById(caseId),
      evidenceService.getEvidenceForCase(caseId),
      timelineService.getTimelineForCase(caseId),
      entityService.getEntitiesForCase(caseId),
      contradictionService.getContradictionsForCase(caseId),
      hypothesisService.getHypothesesForCase(caseId),
      investigationService.getTasksForCase(caseId)
    ]).then(([c, e, t, ent, con, h, tasks]) => {
      if (c) {
        setData({ 
          currentCase: c, 
          evidence: e || [], 
          timeline: t || [], 
          entities: ent || [],
          contradictions: con || [], 
          hypotheses: h || [], 
          tasks: tasks || [] 
        });
      } else {
        setData(null);
      }
      setLoading(false);
    }).catch(err => {
      console.error('Failed to load case overview:', err);
      setLoading(false);
    });
  }, [caseId]);

  if (loading) {
    return (
      <div className="animate-pulse space-y-4 max-w-6xl mx-auto py-12">
        <div className="h-8 bg-[#eae4d9] rounded-lg w-1/3" />
        <div className="h-28 bg-white rounded-3xl border border-[#eae4d9]" />
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3.5">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-24 bg-white rounded-2xl border border-[#eae4d9]" />
          ))}
        </div>
      </div>
    );
  }

  if (!data || !data.currentCase) {
    return (
      <div className="max-w-4xl mx-auto py-20 text-center rounded-3xl border border-dashed border-[#eae4d9] bg-white p-8">
        <h2 className="text-xl font-serif font-bold text-[#191410] mb-2">Case Docket Not Found</h2>
        <p className="text-xs text-[#6e665d] mb-6">The requested case #{caseId} could not be retrieved from the repository.</p>
        <Link to="/cases" className="px-5 py-2.5 rounded-full bg-[#d93829] text-white text-xs font-semibold shadow-sm hover:bg-[#bf2b1d] transition-colors">
          Return to Cases Catalog
        </Link>
      </div>
    );
  }

  const { currentCase, evidence, timeline, entities, contradictions, hypotheses, tasks } = data;

  const stats = [
    { label: 'Exhibits', value: evidence.length, icon: FileText, color: 'text-[#d93829]', bg: 'bg-[#fdeee9]' },
    { label: 'Timeline Milestones', value: timeline.length, icon: Clock, color: 'text-purple-700', bg: 'bg-purple-50' },
    { label: 'Entities Tracked', value: entities.length, icon: Users, color: 'text-blue-700', bg: 'bg-blue-50' },
    { label: 'Contradictions', value: contradictions.length, icon: AlertTriangle, color: 'text-amber-700', bg: 'bg-amber-50' },
    { label: 'Hypotheses', value: hypotheses.length, icon: Lightbulb, color: 'text-emerald-700', bg: 'bg-emerald-50' },
    { label: 'Pending Tasks', value: tasks.filter((t: any) => t.status !== 'Completed').length, icon: CheckSquare, color: 'text-rose-700', bg: 'bg-rose-50' }
  ];

  const incidentDateDisplay = (currentCase as any).incident_date 
    ? new Date((currentCase as any).incident_date).toLocaleDateString()
    : ((currentCase as any).createdDate || (currentCase as any).created_at 
        ? new Date((currentCase as any).createdDate || (currentCase as any).created_at).toLocaleDateString() 
        : 'Registered');

  return (
    <div className="space-y-8 pb-24 max-w-6xl mx-auto text-[#191410]">
      {/* Case Header Card */}
      <div className="p-8 rounded-3xl bg-white border border-[#eae4d9] shadow-xs space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-[#f0ebe1]">
          <div className="flex items-center gap-2.5">
            <span className="px-3 py-1 rounded-full bg-[#fdeee9] font-mono text-xs text-[#d93829] font-bold">
              {currentCase.id}
            </span>
            <span className="text-xs font-semibold text-[#70685e]">
              {(currentCase as any).case_type || 'Special Investigation'}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Link
              to={`/cases/${caseId}/reports`}
              className="px-3.5 py-1 rounded-full bg-cyan-50 hover:bg-cyan-100 border border-cyan-300 text-cyan-800 font-bold text-xs flex items-center gap-1.5 transition-all shadow-xs"
            >
              <Download className="w-3.5 h-3.5 text-cyan-600" />
              <span>Export Dossier (PDF)</span>
            </Link>
            <span className="px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 font-bold text-xs">
              {currentCase.status || 'Active'}
            </span>
            <span className="px-3 py-1 rounded-full bg-red-50 border border-red-200 text-red-700 font-bold text-xs">
              Priority: {currentCase.priority || 'High'}
            </span>
          </div>
        </div>

        <div>
          <h1 className="text-2xl lg:text-3xl font-serif font-bold text-[#191410] tracking-tight">
            {(currentCase as any).title || currentCase.name}
          </h1>
          <p className="text-sm text-[#6e665d] leading-relaxed mt-2 max-w-4xl">
            {currentCase.description}
          </p>
        </div>

        {/* Dynamic Statutory Key Details */}
        {(currentCase as any).key_details && (
          <div className="p-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] text-xs space-y-1">
            <div className="font-bold text-[#191410] uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5 text-[#d93829]" />
              Statutory Framework & Investigation Scope
            </div>
            <p className="text-[#6e665d] leading-relaxed">
              {(currentCase as any).key_details}
            </p>
          </div>
        )}

        {/* Jurisdictional and Meta Badges */}
        <div className="flex flex-wrap items-center gap-6 pt-2 text-xs text-[#70685e] border-t border-[#f0ebe1]">
          {currentCase.location && (
            <span className="flex items-center gap-1.5 font-medium">
              <MapPin className="w-4 h-4 text-[#d93829]" />
              <span>{currentCase.location}</span>
            </span>
          )}
          {currentCase.victim && (
            <span className="flex items-center gap-1.5 font-medium">
              <User className="w-4 h-4 text-blue-600" />
              <span>Victim: {currentCase.victim}</span>
            </span>
          )}
          <span className="flex items-center gap-1.5 font-medium">
            <Calendar className="w-4 h-4 text-[#8c8276]" />
            <span>Incident / Seized: {incidentDateDisplay}</span>
          </span>
          <span className="flex items-center gap-1.5 font-medium">
            <Scale className="w-4 h-4 text-emerald-600" />
            <span>Statutory Admissibility: Certified</span>
          </span>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
        {stats.map(s => (
          <div key={s.label} className="p-4 rounded-2xl bg-white border border-[#eae4d9] shadow-xs text-center hover:-translate-y-0.5 transition-all">
            <div className={cn("w-9 h-9 rounded-xl flex items-center justify-center mx-auto mb-2", s.bg)}>
              <s.icon className={cn("w-4 h-4", s.color)} />
            </div>
            <div className="text-2xl font-serif font-bold text-[#191410]">{s.value}</div>
            <div className="text-[10px] text-[#70685e] uppercase tracking-wider font-bold mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Hypotheses and Contradictions Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Leading Hypotheses */}
        <div className="p-6 rounded-3xl bg-white border border-[#eae4d9] shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#f0ebe1]">
            <h3 className="font-serif font-bold text-lg text-[#191410] flex items-center gap-2">
              <Lightbulb className="w-5 h-5 text-amber-600" /> Leading Hypotheses
            </h3>
            <span className="text-xs font-mono text-[#8c8276]">ACH Analysis</span>
          </div>

          <div className="space-y-3">
            {hypotheses.length === 0 ? (
              <div className="py-8 px-4 text-center rounded-2xl bg-[#faf7f2] border border-dashed border-[#eae4d9]">
                <p className="text-xs text-[#8c8276]">No leading hypotheses formed yet for this docket.</p>
                <Link to={`/cases/${caseId}/hypotheses`} className="inline-flex items-center gap-1 mt-2 text-xs font-semibold text-[#d93829] hover:underline">
                  Evaluate hypotheses in ACH Workspace &rarr;
                </Link>
              </div>
            ) : (
              hypotheses.map((h: Hypothesis) => (
                <div key={h.id} className="p-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] hover:border-[#d93829]/40 transition-colors">
                  <div className="flex justify-between items-start mb-1.5">
                    <h4 className="font-serif font-bold text-sm text-[#191410]">{h.title}</h4>
                    <span className={cn(
                      "text-xs font-bold font-mono px-2.5 py-0.5 rounded-full",
                      h.confidence >= 70 ? "bg-emerald-100 text-emerald-800" :
                      h.confidence <= 20 ? "bg-gray-200 text-gray-700" : "bg-amber-100 text-amber-800"
                    )}>
                      {h.confidence}% Probability
                    </span>
                  </div>
                  <p className="text-xs text-[#6e665d] leading-relaxed">{h.description}</p>
                  <div className="mt-2.5 flex items-center gap-3 text-[11px] font-medium">
                    <span className="text-emerald-700 font-bold">{h.supportingEvidenceIds.length} Supporting Exhibits</span>
                    <span className="text-red-700 font-bold">{h.contradictingEvidenceIds.length} Contradicting</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Contradictions Preview */}
        <div className="p-6 rounded-3xl bg-white border border-[#eae4d9] shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#f0ebe1]">
            <h3 className="font-serif font-bold text-lg text-[#191410] flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-[#d93829]" /> Contradictions Detected
            </h3>
            <span className="text-xs font-mono text-[#8c8276]">Discrepancy Matrix</span>
          </div>

          <div className="space-y-3">
            {contradictions.length === 0 ? (
              <div className="py-8 px-4 text-center rounded-2xl bg-[#faf7f2] border border-dashed border-[#eae4d9]">
                <p className="text-xs text-[#8c8276]">No contradictions detected across testimonies and seized exhibits.</p>
                <Link to={`/cases/${caseId}/contradictions`} className="inline-flex items-center gap-1 mt-2 text-xs font-semibold text-[#d93829] hover:underline">
                  Review contradiction matrix &rarr;
                </Link>
              </div>
            ) : (
              contradictions.map((c: Contradiction) => (
                <div key={c.id} className="p-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-xs text-[#d93829] uppercase">{c.conflictType}</span>
                    <span className="text-[10px] font-mono text-[#8c8276]">{c.id}</span>
                  </div>
                  <div className="text-xs text-[#191410] space-y-1">
                    <p><strong className="text-[#70685e]">Statement A:</strong> {c.statementA}</p>
                    <p><strong className="text-[#70685e]">Statement B:</strong> {c.statementB}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
