// src/pages/case/CaseOverview.tsx
import { useParams, Link } from 'react-router-dom';
import { useEffect, useState, useCallback } from 'react';
import { 
  caseService, 
  evidenceService, 
  timelineService, 
  contradictionService, 
  hypothesisService, 
  investigationService, 
  entityService,
  alertService,
  securityAdminService
} from '../../services';
import { 
  Case, Evidence, TimelineEvent, Contradiction, Hypothesis, 
  InvestigationTask, Entity, CaseDeadline, EvidenceChecklistResponse 
} from '../../types';
import { 
  FileText, Clock, Users, AlertTriangle, Lightbulb, CheckSquare, 
  ArrowRight, ShieldCheck, MapPin, Scale, User, Calendar, 
  BookOpen, Compass, ExternalLink, Download, AlertOctagon, 
  CheckCircle2, Edit3, X, Check, ShieldAlert, Sparkles, Lock, Server, Smartphone
} from 'lucide-react';
import { cn } from '../../utils';
import { useAuth } from '../../context/AuthContext';
import { PossiblyConnectedCasesBadge } from '../../components/case/PossiblyConnectedCasesBadge';

export function CaseOverview() {
  const { caseId } = useParams();
  const { role } = useAuth();
  const isLeadOrAdmin = role === 'lead_investigator' || role === 'admin';

  const [data, setData] = useState<{
    currentCase: Case;
    evidence: Evidence[];
    timeline: TimelineEvent[];
    entities: Entity[];
    contradictions: Contradiction[];
    hypotheses: Hypothesis[];
    tasks: InvestigationTask[];
  } | null>(null);

  const [deadlines, setDeadlines] = useState<CaseDeadline[]>([]);
  const [checklist, setChecklist] = useState<EvidenceChecklistResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // Procedural Dates Edit Modal State
  const [isEditProcedureOpen, setIsEditProcedureOpen] = useState(false);
  const [firNumber, setFirNumber] = useState('');
  const [firDate, setFirDate] = useState('');
  const [incidentDate, setIncidentDate] = useState('');
  const [arrestDate, setArrestDate] = useState('');
  const [remandDate, setRemandDate] = useState('');
  const [offenceSection, setOffenceSection] = useState('');
  const [statutoryLimitDays, setStatutoryLimitDays] = useState(90);
  const [savingProcedure, setSavingProcedure] = useState(false);

  // Legal Hold Modal State
  const [isLegalHoldModalOpen, setIsLegalHoldModalOpen] = useState(false);
  const [legalHoldReason, setLegalHoldReason] = useState('');
  const [submittingLegalHold, setSubmittingLegalHold] = useState(false);

  // Air Gap Modal State
  const [isAirGapModalOpen, setIsAirGapModalOpen] = useState(false);
  const [airgapModel, setAirgapModel] = useState('mistral');
  const [airgapEndpoint, setAirgapEndpoint] = useState('http://localhost:11434/v1');
  const [submittingAirgap, setSubmittingAirgap] = useState(false);

  const loadCaseData = useCallback(async () => {
    if (!caseId) return;
    try {
      setLoading(true);
      const [c, e, t, ent, con, h, tasks, dls, chk] = await Promise.allSettled([
        caseService.getCaseById(caseId),
        evidenceService.getEvidenceForCase(caseId),
        timelineService.getTimelineForCase(caseId),
        entityService.getEntitiesForCase(caseId),
        contradictionService.getContradictionsForCase(caseId),
        hypothesisService.getHypothesesForCase(caseId),
        investigationService.getTasksForCase(caseId),
        alertService.getDeadlines(caseId),
        caseService.getEvidenceChecklist(caseId),
      ]);

      if (c.status === 'fulfilled' && c.value) {
        setData({ 
          currentCase: c.value, 
          evidence: e.status === 'fulfilled' ? e.value || [] : [], 
          timeline: t.status === 'fulfilled' ? t.value || [] : [], 
          entities: ent.status === 'fulfilled' ? ent.value || [] : [],
          contradictions: con.status === 'fulfilled' ? con.value || [] : [], 
          hypotheses: h.status === 'fulfilled' ? h.value || [] : [], 
          tasks: tasks.status === 'fulfilled' ? tasks.value || [] : [] 
        });

        // Initialize edit form
        const curr = c.value;
        setFirNumber(curr.fir_number || '');
        setFirDate(curr.fir_date ? curr.fir_date.slice(0, 10) : '');
        setIncidentDate(curr.incident_date ? curr.incident_date.slice(0, 10) : '');
        setArrestDate(curr.arrest_date ? curr.arrest_date.slice(0, 10) : '');
        setRemandDate(curr.remand_date ? curr.remand_date.slice(0, 10) : '');
        setOffenceSection(curr.offence_section || '');
        setStatutoryLimitDays(curr.statutory_time_limit_days || 90);
      } else {
        setData(null);
      }

      if (dls.status === 'fulfilled') setDeadlines(dls.value || []);
      if (chk.status === 'fulfilled') setChecklist(chk.value);
    } catch (err) {
      console.error('Failed to load case overview:', err);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    loadCaseData();
  }, [loadCaseData]);

  const handleSaveProcedure = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId) return;
    try {
      setSavingProcedure(true);
      await caseService.updateCaseProcedure(caseId, {
        fir_number: firNumber.trim() || undefined,
        fir_date: firDate ? new Date(firDate).toISOString() : undefined,
        incident_date: incidentDate ? new Date(incidentDate).toISOString() : undefined,
        arrest_date: arrestDate ? new Date(arrestDate).toISOString() : undefined,
        remand_date: remandDate ? new Date(remandDate).toISOString() : undefined,
        offence_section: offenceSection.trim() || undefined,
        statutory_time_limit_days: statutoryLimitDays,
      });

      setIsEditProcedureOpen(false);
      await loadCaseData();
    } catch (err) {
      console.error('Failed to update procedural parameters:', err);
      alert('Could not update case procedure parameters.');
    } finally {
      setSavingProcedure(false);
    }
  };

  const handleToggleLegalHold = async (newHoldState: boolean) => {
    if (!caseId) return;
    try {
      setSubmittingLegalHold(true);
      await securityAdminService.setCaseLegalHold(caseId, {
        is_legal_hold: newHoldState,
        reason: legalHoldReason || (newHoldState ? 'Under judicial subpoena / litigation hold' : 'Legal hold released by supervisory authority')
      });
      setIsLegalHoldModalOpen(false);
      setLegalHoldReason('');
      await loadCaseData();
    } catch (e: any) {
      alert(`Legal hold update failed: ${e.message || e}`);
    } finally {
      setSubmittingLegalHold(false);
    }
  };

  const handleToggleAirgap = async (newAirgapState: boolean) => {
    if (!caseId) return;
    try {
      setSubmittingAirgap(true);
      await securityAdminService.toggleCaseAirgap(caseId, {
        is_sensitive_airgapped: newAirgapState,
        ai_provider_override: newAirgapState ? 'local_ollama' : undefined,
        local_ai_endpoint: airgapEndpoint || 'http://localhost:11434/v1',
        local_ai_model: airgapModel || 'mistral'
      });
      setIsAirGapModalOpen(false);
      await loadCaseData();
    } catch (e: any) {
      alert(`Air-gap update failed: ${e.message || e}`);
    } finally {
      setSubmittingAirgap(false);
    }
  };

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

  const primaryChargeDeadline = deadlines.find(d => d.title.includes('Charge Sheet'));
  const remandDeadline = deadlines.find(d => d.title.includes('Remand'));

  const isOverdue = primaryChargeDeadline ? primaryChargeDeadline.days_remaining <= 0 : false;
  const isImminent = primaryChargeDeadline ? primaryChargeDeadline.days_remaining <= 7 && !isOverdue : false;

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
              {currentCase.offence_section || (currentCase as any).case_type || 'Special Investigation'}
            </span>
            {currentCase.fir_number && (
              <span className="text-[11px] font-mono font-bold bg-[#faf7f2] border border-[#eae4d9] px-2 py-0.5 rounded-md text-[#191410]">
                FIR: {currentCase.fir_number}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Legal Hold Status & Toggle */}
            {currentCase.is_legal_hold ? (
              <button
                onClick={() => isLeadOrAdmin && setIsLegalHoldModalOpen(true)}
                className="px-3 py-1 rounded-full bg-amber-100 hover:bg-amber-200 border border-amber-300 text-amber-900 font-bold text-xs flex items-center gap-1.5 shadow-2xs transition-all cursor-pointer"
                title="Case is under legal hold. Case and exhibit deletion is blocked (HTTP 423 Locked)."
              >
                <Lock className="w-3.5 h-3.5 text-amber-700" />
                <span>Legal Hold Active</span>
              </button>
            ) : isLeadOrAdmin && (
              <button
                onClick={() => setIsLegalHoldModalOpen(true)}
                className="px-3 py-1 rounded-full bg-white hover:bg-amber-50 border border-[#eae4d9] text-[#70685e] hover:text-amber-800 font-semibold text-xs flex items-center gap-1.5 transition-all shadow-2xs cursor-pointer"
                title="Place case under legal hold to block deletion"
              >
                <Lock className="w-3.5 h-3.5 text-amber-600" />
                <span>Legal Hold</span>
              </button>
            )}

            {/* Air-Gap Sensitive Case Status & Toggle */}
            {currentCase.is_sensitive_airgapped ? (
              <button
                onClick={() => isLeadOrAdmin && setIsAirGapModalOpen(true)}
                className="px-3 py-1 rounded-full bg-purple-100 hover:bg-purple-200 border border-purple-300 text-purple-900 font-bold text-xs flex items-center gap-1.5 shadow-2xs transition-all cursor-pointer"
                title="Sensitive case air-gapped: Cloud AI calls are strictly blocked."
              >
                <ShieldAlert className="w-3.5 h-3.5 text-purple-700" />
                <span>Air-Gapped (Offline AI)</span>
              </button>
            ) : isLeadOrAdmin && (
              <button
                onClick={() => setIsAirGapModalOpen(true)}
                className="px-3 py-1 rounded-full bg-white hover:bg-purple-50 border border-[#eae4d9] text-[#70685e] hover:text-purple-800 font-semibold text-xs flex items-center gap-1.5 transition-all shadow-2xs cursor-pointer"
                title="Engage air-gap firewall to block external cloud calls"
              >
                <Server className="w-3.5 h-3.5 text-purple-600" />
                <span>Air-Gap</span>
              </button>
            )}

            {isLeadOrAdmin && (
              <button
                onClick={() => setIsEditProcedureOpen(true)}
                className="px-3 py-1 rounded-full bg-white hover:bg-[#faf7f2] border border-[#eae4d9] text-[#191410] font-semibold text-xs flex items-center gap-1.5 transition-all shadow-2xs cursor-pointer"
                title="Update FIR, arrest, remand, and offence sections"
              >
                <Edit3 className="w-3.5 h-3.5 text-[#1b64b8]" />
                <span>Legal Dates</span>
              </button>
            )}
            <a
              href={`/cases/${caseId}/wall`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3.5 py-1 rounded-full bg-[#faf7f2] hover:bg-[#eae4d9] border border-[#d8d0c5] text-[#191410] font-bold text-xs flex items-center gap-1.5 transition-all shadow-2xs"
              title="Open real-time Situation Board on second monitor or team room wall"
            >
              <ExternalLink className="w-3.5 h-3.5 text-[#d93829]" />
              <span>Live Case Wall</span>
            </a>
            <Link
              to={`/cases/${caseId}/priorities`}
              className="px-3.5 py-1 rounded-full bg-amber-50 hover:bg-amber-100 border border-amber-300 text-amber-900 font-bold text-xs flex items-center gap-1.5 transition-all shadow-2xs"
            >
              <Clock className="w-3.5 h-3.5 text-amber-700" />
              <span>Today's Priorities</span>
            </Link>
            <Link
              to={`/cases/${caseId}/case-file`}
              className="px-3.5 py-1 rounded-full bg-blue-50 hover:bg-blue-100 border border-blue-300 text-blue-900 font-bold text-xs flex items-center gap-1.5 transition-all shadow-2xs"
            >
              <FileText className="w-3.5 h-3.5 text-blue-700" />
              <span>Case File & FIR</span>
            </Link>
            <Link
              to={`/cases/${caseId}/handover`}
              className="px-3.5 py-1 rounded-full bg-[#fdeee9] hover:bg-[#fad8d1] border border-[#f5b8ad] text-[#d93829] font-bold text-xs flex items-center gap-1.5 transition-all shadow-2xs"
            >
              <Scale className="w-3.5 h-3.5" />
              <span>Shift Handover</span>
            </Link>
            <Link
              to={`/cases/${caseId}/reports`}
              className="px-3.5 py-1 rounded-full bg-cyan-50 hover:bg-cyan-100 border border-cyan-300 text-cyan-800 font-bold text-xs flex items-center gap-1.5 transition-all shadow-xs"
            >
              <Download className="w-3.5 h-3.5 text-cyan-600" />
              <span>Dossier (PDF)</span>
            </Link>
            {caseId && <PossiblyConnectedCasesBadge caseId={caseId} />}
            <span className="px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 font-bold text-xs">
              {currentCase.status || 'Active'}
            </span>
          </div>
        </div>

        <div>
          <h1 className="text-2xl lg:text-3xl font-serif font-bold text-[#191410] tracking-tight">
            {currentCase.title || currentCase.name}
          </h1>
          <p className="text-sm text-[#6e665d] leading-relaxed mt-2 max-w-4xl">
            {currentCase.description}
          </p>
        </div>

        {/* Procedural Meta Badges */}
        <div className="flex flex-wrap items-center gap-6 pt-2 text-xs text-[#70685e] border-t border-[#f0ebe1]">
          {currentCase.fir_date && (
            <span className="flex items-center gap-1.5 font-medium">
              <Calendar className="w-4 h-4 text-[#8c8276]" />
              <span>FIR Registered: {new Date(currentCase.fir_date).toLocaleDateString('en-GB')}</span>
            </span>
          )}
          {currentCase.arrest_date && (
            <span className="flex items-center gap-1.5 font-medium">
              <Clock className="w-4 h-4 text-[#d93829]" />
              <span>Arrest: {new Date(currentCase.arrest_date).toLocaleDateString('en-GB')}</span>
            </span>
          )}
          {currentCase.remand_date && (
            <span className="flex items-center gap-1.5 font-medium">
              <Scale className="w-4 h-4 text-[#1b64b8]" />
              <span>Remand: {new Date(currentCase.remand_date).toLocaleDateString('en-GB')}</span>
            </span>
          )}
          {currentCase.location && (
            <span className="flex items-center gap-1.5 font-medium">
              <MapPin className="w-4 h-4 text-[#d93829]" />
              <span>{currentCase.location}</span>
            </span>
          )}
        </div>
      </div>

      {/* 1. STATUTORY DEADLINE COUNTDOWN & PROCEDURAL WARNINGS WIDGET */}
      <div className={`p-6 rounded-3xl border transition-all ${
        isOverdue 
          ? 'bg-[#fffbf9] border-[#d93829] shadow-sm' 
          : isImminent 
          ? 'bg-[#fffdf5] border-[#f4c153] shadow-sm' 
          : 'bg-white border-[#eae4d9] shadow-xs'
      }`}>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#eae4d9]">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Scale className="w-4 h-4 text-[#1b64b8]" />
              <h2 className="text-sm font-bold text-[#191410] uppercase tracking-wider font-mono">
                Procedural Compliance & Legal Countdown Tracker
              </h2>
            </div>
            <p className="text-xs text-[#70685e]">
              Monitors statutory detention limits under BNSS Section 187(3) / CrPC Section 167(2).
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Link
              to={`/cases/${caseId}/handover`}
              className="text-xs font-semibold text-[#1b64b8] hover:underline flex items-center gap-1"
            >
              View Full Statutory Deadlines Table & Ext. Records →
            </Link>
          </div>
        </div>

        {/* Countdowns Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-4">
          {/* Charge Sheet Countdown Card */}
          <div className={`p-4 rounded-2xl border ${
            isOverdue 
              ? 'border-[#d93829] bg-white' 
              : isImminent 
              ? 'border-[#f4c153] bg-white' 
              : 'border-[#eae4d9] bg-[#faf7f2]'
          }`}>
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#70685e]">
                Statutory Charge Sheet
              </span>
              <span className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded-full uppercase ${
                isOverdue 
                  ? 'bg-[#fdeee9] text-[#d93829] animate-pulse' 
                  : isImminent 
                  ? 'bg-[#fff8ea] text-[#8a5b00]' 
                  : 'bg-[#ebf7ee] text-[#1b7a37]'
              }`}>
                {primaryChargeDeadline ? primaryChargeDeadline.status : 'Configured'}
              </span>
            </div>

            <div className="mt-2 flex items-baseline justify-between">
              <div className={`text-2xl font-serif font-bold font-mono ${
                isOverdue ? 'text-[#d93829]' : isImminent ? 'text-[#b87600]' : 'text-[#191410]'
              }`}>
                {primaryChargeDeadline ? `${primaryChargeDeadline.days_remaining} Days` : '90 Days Limit'}
              </div>
              <span className="text-[11px] text-[#70685e]">
                {primaryChargeDeadline ? `Due: ${new Date(primaryChargeDeadline.due_date).toLocaleDateString('en-GB')}` : 'Requires Arrest Date'}
              </span>
            </div>

            <p className="text-[11px] text-[#70685e] mt-2 leading-relaxed">
              {isOverdue 
                ? 'CRITICAL: Investigation period expired. Accused has an indefeasible right to statutory default bail.'
                : isImminent 
                ? 'URGENT: Deadline approaching. Finalize FSL reports, weapon recovery panchanamas, and prosecution sanction.'
                : 'Detention is legally compliant. File final police report before deadline to prevent default bail.'}
            </p>
          </div>

          {/* Judicial Remand Review Cycle */}
          <div className="p-4 rounded-2xl border border-[#eae4d9] bg-[#faf7f2]">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#70685e]">
                Judicial Remand Renewal
              </span>
              <span className="text-[9px] font-mono font-bold px-2 py-0.5 rounded-full uppercase bg-[#ebf4fd] text-[#1b64b8]">
                14-Day Review
              </span>
            </div>

            <div className="mt-2 flex items-baseline justify-between">
              <div className="text-2xl font-serif font-bold font-mono text-[#191410]">
                {remandDeadline ? `${remandDeadline.days_remaining} Days` : '14 Days'}
              </div>
              <span className="text-[11px] text-[#70685e]">
                {remandDeadline ? `Due: ${new Date(remandDeadline.due_date).toLocaleDateString('en-GB')}` : 'Requires Remand Date'}
              </span>
            </div>

            <p className="text-[11px] text-[#70685e] mt-2 leading-relaxed">
              Physical or video-link production before Jurisdictional Magistrate required under Section 187(2) BNSS.
            </p>
          </div>

          {/* Offence Legal Classification */}
          <div className="p-4 rounded-2xl border border-[#eae4d9] bg-[#faf7f2] space-y-2">
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#70685e]">
              Legal Offence Category
            </span>
            <div className="text-sm font-bold text-[#191410] line-clamp-2">
              {currentCase.offence_section || 'Unclassified Cognizable Offence'}
            </div>
            <div className="text-[11px] text-[#70685e] pt-1 border-t border-[#eae4d9]">
              <span>Time Limit: </span>
              <span className="font-bold text-[#191410]">{currentCase.statutory_time_limit_days || 90} calendar days</span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. EVIDENCE CHECKLIST PER OFFENCE TYPE (MISSING EXHIBITS ADVISORY) */}
      {checklist && (
        <div className="p-6 rounded-3xl bg-white border border-[#eae4d9] shadow-xs space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-4 border-b border-[#eae4d9]">
            <div>
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-[#d93829]" />
                <h3 className="font-serif font-bold text-base text-[#191410]">
                  Evidentiary Checklist: {checklist.offence_category.toUpperCase()} PROTOCOL
                </h3>
                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-[#fdeee9] text-[#d93829]">
                  {checklist.present_count} / {checklist.total_expected} Exhibits Gathered
                </span>
              </div>
              <p className="text-xs text-[#70685e] mt-0.5">
                Statutory proof requirements based on offence classification. Missing mandatory exhibits jeopardize prosecution at trial.
              </p>
            </div>

            {/* Compliance Progress Bar */}
            <div className="w-full md:w-56 space-y-1">
              <div className="flex justify-between text-[11px] font-mono">
                <span className="text-[#70685e]">Evidence Completeness</span>
                <span className="font-bold text-[#191410]">{checklist.compliance_percentage}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-[#f0ebe1] overflow-hidden">
                <div 
                  className={cn(
                    "h-full rounded-full transition-all duration-500",
                    checklist.compliance_percentage >= 80 ? "bg-[#22c55e]" :
                    checklist.compliance_percentage >= 50 ? "bg-[#e59b00]" : "bg-[#d93829]"
                  )}
                  style={{ width: `${checklist.compliance_percentage}%` }}
                />
              </div>
            </div>
          </div>

          {/* Checklist Items Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {checklist.items.map((item, idx) => {
              const isPresent = item.status === 'present';
              return (
                <div 
                  key={idx}
                  className={`p-3.5 rounded-2xl border text-xs space-y-1.5 transition-all ${
                    isPresent 
                      ? 'border-[#9fe0b2] bg-[#f8fdf9]' 
                      : item.mandatory 
                      ? 'border-[#f5b8ad] bg-[#fffbf9]' 
                      : 'border-[#eae4d9] bg-[#faf7f2]'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-1.5 font-bold text-[#191410]">
                      {isPresent ? (
                        <CheckCircle2 className="w-4 h-4 text-[#22c55e] shrink-0" />
                      ) : (
                        <AlertCircleIcon isMandatory={item.mandatory} />
                      )}
                      <span>{item.title}</span>
                    </div>

                    <span className={`text-[9px] font-mono uppercase px-1.5 py-0.2 rounded font-bold shrink-0 ${
                      isPresent 
                        ? 'bg-[#ebf7ee] text-[#1b7a37]' 
                        : item.mandatory 
                        ? 'bg-[#fdeee9] text-[#d93829]' 
                        : 'bg-[#eae4d9] text-[#70685e]'
                    }`}>
                      {item.status}
                    </span>
                  </div>

                  <p className="text-[11px] text-[#554e44] leading-relaxed">
                    {item.description}
                  </p>

                  <div className="pt-1.5 border-t border-[#eae4d9]/50 flex items-center justify-between text-[10px]">
                    <span className="font-mono text-[#1b64b8] font-medium">
                      {item.legal_provision}
                    </span>

                    {isPresent ? (
                      <span className="text-[#1b7a37] font-semibold truncate max-w-[180px]">
                        Attached: {item.matched_file_name}
                      </span>
                    ) : (
                      <Link 
                        to={`/cases/${caseId}/evidence`}
                        className="text-[#d93829] font-bold hover:underline flex items-center gap-0.5"
                      >
                        Upload exhibit →
                      </Link>
                    )}
                  </div>

                  {!isPresent && item.mandatory && (
                    <div className="text-[10px] text-[#b82a1d] font-medium pt-1">
                      ⚠️ {item.consequence_if_missing}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

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

      {/* EDIT PROCEDURAL DATES & SECTIONS MODAL */}
      {isEditProcedureOpen && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-white rounded-2xl border border-[#eae4d9] shadow-2xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-[#eae4d9] pb-3">
              <h3 className="text-sm font-bold text-[#191410] flex items-center gap-2">
                <Scale className="w-4 h-4 text-[#1b64b8]" />
                Update Legal Dates & Procedural Parameters
              </h3>
              <button 
                onClick={() => setIsEditProcedureOpen(false)}
                className="text-[#8c8276] hover:text-[#191410] cursor-pointer"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveProcedure} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-[#191410] mb-1">
                    FIR / Police Crime Number
                  </label>
                  <input
                    type="text"
                    value={firNumber}
                    onChange={(e) => setFirNumber(e.target.value)}
                    placeholder="e.g., FIR-432/2009"
                    className="w-full px-3 py-1.5 bg-[#faf7f2] border border-[#eae4d9] rounded-xl focus:outline-none focus:border-[#d93829]"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-[#191410] mb-1">
                    FIR Registration Date
                  </label>
                  <input
                    type="date"
                    value={firDate}
                    onChange={(e) => setFirDate(e.target.value)}
                    className="w-full px-3 py-1.5 bg-[#faf7f2] border border-[#eae4d9] rounded-xl focus:outline-none focus:border-[#d93829]"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-[#191410] mb-1">
                  Offence Section(s) & Penal Statutes
                </label>
                <input
                  type="text"
                  value={offenceSection}
                  onChange={(e) => setOffenceSection(e.target.value)}
                  placeholder="e.g., Section 302 IPC / Section 103 BNS (Murder)"
                  className="w-full px-3 py-1.5 bg-[#faf7f2] border border-[#eae4d9] rounded-xl focus:outline-none focus:border-[#d93829]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-[#191410] mb-1">
                    Arrest Date
                  </label>
                  <input
                    type="date"
                    value={arrestDate}
                    onChange={(e) => setArrestDate(e.target.value)}
                    className="w-full px-3 py-1.5 bg-[#faf7f2] border border-[#eae4d9] rounded-xl focus:outline-none focus:border-[#d93829]"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-[#191410] mb-1">
                    First Remand Date
                  </label>
                  <input
                    type="date"
                    value={remandDate}
                    onChange={(e) => setRemandDate(e.target.value)}
                    className="w-full px-3 py-1.5 bg-[#faf7f2] border border-[#eae4d9] rounded-xl focus:outline-none focus:border-[#d93829]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-[#191410] mb-1">
                    Incident / Crime Date
                  </label>
                  <input
                    type="date"
                    value={incidentDate}
                    onChange={(e) => setIncidentDate(e.target.value)}
                    className="w-full px-3 py-1.5 bg-[#faf7f2] border border-[#eae4d9] rounded-xl focus:outline-none focus:border-[#d93829]"
                  />
                </div>

                <div>
                  <label className="block font-semibold text-[#191410] mb-1">
                    Statutory Detention Limit
                  </label>
                  <select
                    value={statutoryLimitDays}
                    onChange={(e) => setStatutoryLimitDays(parseInt(e.target.value, 10))}
                    className="w-full px-3 py-1.5 bg-[#faf7f2] border border-[#eae4d9] rounded-xl focus:outline-none focus:border-[#d93829]"
                  >
                    <option value={90}>90 Days (Heinous / 10+ yrs / Life / Death)</option>
                    <option value={60}>60 Days (General Cognizable)</option>
                    <option value={180}>180 Days (NDPS / PMLA / Special Acts)</option>
                  </select>
                </div>
              </div>

              <div className="p-2.5 bg-[#ebf4fd] border border-[#bedcfc] rounded-xl text-[11px] text-[#1b64b8]">
                Updating legal dates automatically recalibrates statutory charge sheet deadlines, remand renewal schedules, and evidentiary checklists.
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#eae4d9]">
                <button
                  type="button"
                  onClick={() => setIsEditProcedureOpen(false)}
                  className="px-3 py-1.5 text-xs text-[#70685e] hover:text-[#191410] cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingProcedure}
                  className="px-4 py-2 text-xs font-bold text-white bg-[#1b64b8] hover:bg-[#155094] rounded-xl transition-all cursor-pointer shadow-xs disabled:opacity-50"
                >
                  {savingProcedure ? 'Saving...' : 'Save & Recalculate'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* LEGAL HOLD MODAL */}
      {isLegalHoldModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl border border-[#eae4d9] max-w-md w-full p-6 space-y-4 shadow-xl animate-in zoom-in-95">
            <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9]">
              <div className="flex items-center gap-2">
                <Lock className="w-5 h-5 text-amber-600" />
                <h3 className="font-bold text-base text-[#191410]">
                  {currentCase.is_legal_hold ? 'Release Legal Hold' : 'Place Case Under Legal Hold'}
                </h3>
              </div>
              <button onClick={() => setIsLegalHoldModalOpen(false)} className="text-[#999084] hover:text-[#191410] cursor-pointer">✕</button>
            </div>

            <div className="text-xs text-[#70685e] space-y-2">
              <p>
                {currentCase.is_legal_hold
                  ? 'Releasing legal hold will restore normal deletion and archiving rules for this case docket and its exhibits.'
                  : 'Placing this case under legal hold blocks deletion of the case and all attached exhibits with HTTP 423 Locked. All retention expiry schedules are suspended.'}
              </p>
              <div>
                <label className="font-bold text-[#191410] block mb-1">
                  Reason for {currentCase.is_legal_hold ? 'Release' : 'Legal Hold Placement'}:
                </label>
                <textarea
                  value={legalHoldReason}
                  onChange={(e) => setLegalHoldReason(e.target.value)}
                  placeholder="e.g. Subpoena received from High Court, judicial inquiry ongoing..."
                  rows={3}
                  className="w-full px-3 py-2 bg-[#faf7f2] border border-[#eae4d9] rounded-xl text-xs text-[#191410] focus:outline-none focus:border-amber-500"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-[#eae4d9]">
              <button
                type="button"
                onClick={() => setIsLegalHoldModalOpen(false)}
                className="px-3.5 py-1.5 text-xs text-[#70685e] hover:text-[#191410] cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={submittingLegalHold}
                onClick={() => handleToggleLegalHold(!currentCase.is_legal_hold)}
                className={cn(
                  "px-4 py-2 text-xs font-bold text-white rounded-xl shadow-xs transition-all cursor-pointer disabled:opacity-50",
                  currentCase.is_legal_hold ? "bg-amber-600 hover:bg-amber-700" : "bg-red-600 hover:bg-red-700"
                )}
              >
                {submittingLegalHold 
                  ? 'Updating...' 
                  : currentCase.is_legal_hold 
                  ? 'Confirm Release Hold' 
                  : 'Enforce Legal Hold'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* SENSITIVE CASE AIR-GAP MODAL */}
      {isAirGapModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl border border-[#eae4d9] max-w-md w-full p-6 space-y-4 shadow-xl animate-in zoom-in-95">
            <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9]">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-purple-600" />
                <h3 className="font-bold text-base text-[#191410]">
                  {currentCase.is_sensitive_airgapped ? 'Disable Air-Gap Mode' : 'Engage Air-Gap Firewall'}
                </h3>
              </div>
              <button onClick={() => setIsAirGapModalOpen(false)} className="text-[#999084] hover:text-[#191410] cursor-pointer">✕</button>
            </div>

            <div className="text-xs text-[#70685e] space-y-3">
              <p>
                {currentCase.is_sensitive_airgapped
                  ? 'Disabling air-gap mode allows this case to use standard cloud AI analysis models.'
                  : 'Engaging the air-gap firewall strictly blocks all external cloud AI requests for this case. The system will route all analysis to your locally hosted model.'}
              </p>

              {!currentCase.is_sensitive_airgapped && (
                <div className="space-y-2 pt-1 border-t border-[#f0ebe1]">
                  <div>
                    <label className="font-bold text-[#191410] block mb-1">Local Model Endpoint:</label>
                    <input
                      type="text"
                      value={airgapEndpoint}
                      onChange={(e) => setAirgapEndpoint(e.target.value)}
                      placeholder="http://localhost:11434/v1"
                      className="w-full px-3 py-1.5 bg-[#faf7f2] border border-[#eae4d9] rounded-xl text-xs font-mono text-[#191410] focus:outline-none focus:border-purple-500"
                    />
                  </div>
                  <div>
                    <label className="font-bold text-[#191410] block mb-1">Local Model Identifier:</label>
                    <input
                      type="text"
                      value={airgapModel}
                      onChange={(e) => setAirgapModel(e.target.value)}
                      placeholder="mistral"
                      className="w-full px-3 py-1.5 bg-[#faf7f2] border border-[#eae4d9] rounded-xl text-xs font-mono text-[#191410] focus:outline-none focus:border-purple-500"
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-[#eae4d9]">
              <button
                type="button"
                onClick={() => setIsAirGapModalOpen(false)}
                className="px-3.5 py-1.5 text-xs text-[#70685e] hover:text-[#191410] cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={submittingAirgap}
                onClick={() => handleToggleAirgap(!currentCase.is_sensitive_airgapped)}
                className={cn(
                  "px-4 py-2 text-xs font-bold text-white rounded-xl shadow-xs transition-all cursor-pointer disabled:opacity-50",
                  currentCase.is_sensitive_airgapped ? "bg-stone-700 hover:bg-stone-800" : "bg-purple-600 hover:bg-purple-700"
                )}
              >
                {submittingAirgap
                  ? 'Saving...'
                  : currentCase.is_sensitive_airgapped
                  ? 'Allow Cloud AI'
                  : 'Engage Total Air-Gap'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function AlertCircleIcon({ isMandatory }: { isMandatory: boolean }) {
  if (isMandatory) {
    return <AlertOctagon className="w-4 h-4 text-[#d93829] shrink-0" />;
  }
  return <AlertTriangle className="w-4 h-4 text-[#e59b00] shrink-0" />;
}

export default CaseOverview;
