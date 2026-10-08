import { useParams, Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { hypothesisService, evidenceService } from '../../services';
import { 
  Hypothesis, 
  EvidenceAssessment, 
  Evidence, 
  SensitivityAnalysisResult, 
  SensitivityImpact, 
  ReliabilityConfig, 
  ExhibitBreakdownRow, 
  HypothesisRobustness 
} from '../../types';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { 
  Lightbulb, CheckCircle2, XCircle, ChevronDown, ChevronRight, 
  Plus, Sparkles, Loader2, ShieldCheck, AlertTriangle, 
  HelpCircle, Scale, FileText, Database, X, Cpu, ExternalLink,
  GitBranch, ArrowUpRight, Video, Mic, Compass, Sliders, RotateCcw,
  SlidersHorizontal, Check, AlertOctagon, Info, Table as TableIcon, 
  BarChart2, Settings, Quote, Eye, ShieldAlert, Award
} from 'lucide-react';
import { cn } from '../../utils';
import { useCaseState } from '../../engine/useCaseState';
import { SourceSpanViewerModal } from '../../components/common/SourceSpanViewerModal';

export function Hypotheses() {
  const { caseId } = useParams<{ caseId: string }>();
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
  const [caseEvidence, setCaseEvidence] = useState<Evidence[]>([]);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState<string | null>(null);
  const [expandedHypothesis, setExpandedHypothesis] = useState<string | null>(null);
  
  // View mode: 'ranked' (ranked cards with error bars) or 'matrix' (classic ACH heatmap grid)
  const [viewMode, setViewMode] = useState<'ranked' | 'matrix'>('ranked');

  // Creation modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newStatus, setNewStatus] = useState('Active');
  const [creating, setCreating] = useState(false);

  // Breakdown Drawer / Modal state
  const [breakdownModalHyp, setBreakdownModalHyp] = useState<Hypothesis | null>(null);
  const [breakdownRows, setBreakdownRows] = useState<ExhibitBreakdownRow[]>([]);
  const [loadingBreakdown, setLoadingBreakdown] = useState(false);

  // Sensitivity Analysis (Heuer Step 6) state
  const [isSensitivityOpen, setIsSensitivityOpen] = useState(false);
  const [sensitivityData, setSensitivityData] = useState<SensitivityAnalysisResult | null>(null);
  const [robustnessRanges, setRobustnessRanges] = useState<Record<string, HypothesisRobustness>>({});
  const [loadingSensitivity, setLoadingSensitivity] = useState(false);
  const [excludedExhibitIds, setExcludedExhibitIds] = useState<number[]>([]);
  const [simulatedScores, setSimulatedScores] = useState<Record<string, any> | null>(null);
  const [simulating, setSimulating] = useState(false);

  // Reliability Configuration Manager Modal state
  const [isReliabilityModalOpen, setIsReliabilityModalOpen] = useState(false);
  const [reliabilityConfigs, setReliabilityConfigs] = useState<ReliabilityConfig[]>([]);
  const [editingConfig, setEditingConfig] = useState<ReliabilityConfig | null>(null);
  const [savingConfig, setSavingConfig] = useState(false);

  // Notification Toast state
  const [notificationMsg, setNotificationMsg] = useState<{ text: string; type: 'success' | 'info' | 'warning' } | null>(null);

  // Feature 3: Source-Span Citations Modal State
  const [citationModalOpen, setCitationModalOpen] = useState(false);
  const [citationEvidenceId, setCitationEvidenceId] = useState<string | number | null>(null);
  const [citationEvidenceTitle, setCitationEvidenceTitle] = useState<string | undefined>(undefined);
  const [citationTargetQuote, setCitationTargetQuote] = useState<string | undefined>(undefined);

  const handleOpenSourceSpan = (evId: string | number, evTitle?: string, quote?: string) => {
    setCitationEvidenceId(evId);
    setCitationEvidenceTitle(evTitle);
    setCitationTargetQuote(quote);
    setCitationModalOpen(true);
  };

  const stateTick = useCaseState();

  const loadData = async () => {
    if (!caseId) return;
    try {
      setLoading(true);
      const [hyps, evs, sens] = await Promise.all([
        hypothesisService.getHypothesesForCase(caseId),
        evidenceService.getEvidenceForCase(caseId),
        hypothesisService.getSensitivityAndRobustness(caseId).catch(() => null)
      ]);
      setHypotheses(hyps);
      setCaseEvidence(evs);
      if (sens && sens.robustness_ranges) {
        setRobustnessRanges(sens.robustness_ranges);
      }
      if (hyps.length > 0 && !expandedHypothesis) {
        setExpandedHypothesis(hyps[0].id);
      }
    } catch (err) {
      console.error('Failed to load hypotheses:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [caseId, stateTick]);

  const handleEvaluate = async (hypothesisId: string) => {
    setEvaluating(hypothesisId);
    try {
      const updated = await hypothesisService.evaluateHypothesis(hypothesisId);
      if (updated) {
        await loadData();
        setNotificationMsg({ text: 'AI evaluated hypothesis exhibits with verified quotes. ACH scores recalculated.', type: 'success' });
        setTimeout(() => setNotificationMsg(null), 4000);
      }
    } catch (err) {
      console.error('Evaluation failed:', err);
    } finally {
      setEvaluating(null);
    }
  };

  const handleEvaluateAll = async () => {
    setEvaluating('ALL');
    try {
      for (const h of hypotheses) {
        await hypothesisService.evaluateHypothesis(h.id);
      }
      await loadData();
      setNotificationMsg({ text: 'All hypotheses evaluated with quote verification and disconfirmation scoring.', type: 'success' });
      setTimeout(() => setNotificationMsg(null), 4000);
    } catch (err) {
      console.error('Batch evaluation failed:', err);
    } finally {
      setEvaluating(null);
    }
  };

  const handleRunACHAnalysis = async () => {
    if (!caseId) return;
    setEvaluating('ACH');
    try {
      const results = await hypothesisService.analyzeHypotheses(caseId);
      if (results && results.length > 0) {
        setHypotheses(results);
        if (!expandedHypothesis) setExpandedHypothesis(results[0].id);
        setNotificationMsg({ 
          text: 'True ACH Matrix generated: disconfirmation-first ranking and normalized 100% relative likelihoods computed.', 
          type: 'success' 
        });
        setTimeout(() => setNotificationMsg(null), 5000);
      } else {
        await loadData();
      }
    } catch (err) {
      console.error('ACH Analysis failed:', err);
    } finally {
      setEvaluating(null);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId || !newTitle.trim()) return;
    setCreating(true);
    try {
      const created = await hypothesisService.createHypothesis(caseId, {
        title: newTitle.trim(),
        description: newDesc.trim(),
        status: newStatus
      });
      setIsModalOpen(false);
      setNewTitle('');
      setNewDesc('');
      await loadData();
      handleEvaluate(created.id);
    } catch (err) {
      console.error('Failed to create hypothesis:', err);
    } finally {
      setCreating(false);
    }
  };

  // Open Detailed Breakdown Panel for a Hypothesis
  const handleOpenBreakdown = async (h: Hypothesis) => {
    if (!caseId) return;
    setBreakdownModalHyp(h);
    setLoadingBreakdown(true);
    try {
      const res = await hypothesisService.getHypothesisBreakdown(caseId, h.id);
      if (res && res.exhibits) {
        setBreakdownRows(res.exhibits);
      } else {
        setBreakdownRows([]);
      }
    } catch (err) {
      console.error('Failed to load breakdown:', err);
      setBreakdownRows([]);
    } finally {
      setLoadingBreakdown(false);
    }
  };

  // Analyst Override handler
  const handleOverrideClassification = async (
    hypothesisId: string | number, 
    evidenceId: string | number, 
    newClassification: string
  ) => {
    if (!caseId) return;
    try {
      await hypothesisService.overrideScoring(caseId, {
        hypothesis_id: hypothesisId,
        evidence_id: evidenceId,
        classification: newClassification,
        analyst_notes: `Analyst analytical adjustment to ${newClassification.replace('_', ' ')}`
      });
      setNotificationMsg({ 
        text: `Analyst override applied to Exhibit #${evidenceId}. Normalized relative likelihoods recomputed live.`, 
        type: 'success' 
      });
      setTimeout(() => setNotificationMsg(null), 4000);
      await loadData();
      if (breakdownModalHyp && String(breakdownModalHyp.id) === String(hypothesisId)) {
        handleOpenBreakdown(breakdownModalHyp);
      }
    } catch (err) {
      console.error('Override error:', err);
    }
  };

  // Override Evidence Type
  const handleOverrideEvidenceType = async (evidenceId: string | number, newType: string) => {
    if (!caseId || !hypotheses.length) return;
    try {
      await hypothesisService.overrideScoring(caseId, {
        hypothesis_id: hypotheses[0].id,
        evidence_id: evidenceId,
        evidence_type: newType,
        analyst_notes: `Analyst updated evidence type to ${newType}`
      });
      setNotificationMsg({ 
        text: `Exhibit #${evidenceId} categorized as ${newType}. Reliability re-resolved and scores updated.`, 
        type: 'success' 
      });
      setTimeout(() => setNotificationMsg(null), 4000);
      await loadData();
      if (breakdownModalHyp) handleOpenBreakdown(breakdownModalHyp);
    } catch (err) {
      console.error('Evidence type override error:', err);
    }
  };

  // Analyst Reset handler
  const handleResetClassification = async (hypothesisId: string | number, evidenceId: string | number) => {
    if (!caseId) return;
    try {
      await hypothesisService.resetAssessment(caseId, hypothesisId, evidenceId);
      setNotificationMsg({ 
        text: `Exhibit #${evidenceId} restored to AI baseline classification.`, 
        type: 'info' 
      });
      setTimeout(() => setNotificationMsg(null), 4000);
      await loadData();
      if (breakdownModalHyp && String(breakdownModalHyp.id) === String(hypothesisId)) {
        handleOpenBreakdown(breakdownModalHyp);
      }
    } catch (err) {
      console.error('Reset override error:', err);
    }
  };

  // Sensitivity Analysis Open
  const handleOpenSensitivity = async () => {
    if (!caseId) return;
    setIsSensitivityOpen(true);
    setLoadingSensitivity(true);
    try {
      const [sensRes, robustRes] = await Promise.all([
        hypothesisService.getSensitivityAnalysis(caseId),
        hypothesisService.getSensitivityAndRobustness(caseId)
      ]);
      setSensitivityData(sensRes);
      if (robustRes && robustRes.robustness_ranges) {
        setRobustnessRanges(robustRes.robustness_ranges);
      }
      setExcludedExhibitIds([]);
      setSimulatedScores(null);
    } catch (err) {
      console.error('Sensitivity analysis error:', err);
    } finally {
      setLoadingSensitivity(false);
    }
  };

  // Sensitivity Interactive Toggle
  const handleToggleExcludeExhibit = async (evId: number | string) => {
    if (!caseId) return;
    const numId = Number(String(evId).replace(/\D/g, ''));
    const nextExcluded = excludedExhibitIds.includes(numId)
      ? excludedExhibitIds.filter(id => id !== numId)
      : [...excludedExhibitIds, numId];
    
    setExcludedExhibitIds(nextExcluded);
    setSimulating(true);
    try {
      const res = await hypothesisService.calculateACHWithExclusions(caseId, nextExcluded);
      if (res && res.hypotheses) {
        setSimulatedScores(res.hypotheses);
      }
    } catch (err) {
      console.error('Interactive exclusion calculation error:', err);
    } finally {
      setSimulating(false);
    }
  };

  // Open Reliability Configs
  const handleOpenReliabilityConfigs = async () => {
    if (!caseId) return;
    setIsReliabilityModalOpen(true);
    try {
      const list = await hypothesisService.getReliabilityConfigs(caseId);
      setReliabilityConfigs(list);
    } catch (err) {
      console.error('Failed to load reliability configs:', err);
    }
  };

  // Save Reliability Config
  const handleSaveReliabilityConfig = async () => {
    if (!caseId || !editingConfig) return;
    setSavingConfig(true);
    try {
      await hypothesisService.updateReliabilityConfig(caseId, {
        evidence_type: editingConfig.evidence_type,
        base_reliability: editingConfig.base_reliability,
        rationale: editingConfig.rationale
      });
      setNotificationMsg({
        text: `Base reliability for ${editingConfig.evidence_type} updated. ACH scores recalculated.`,
        type: 'success'
      });
      setTimeout(() => setNotificationMsg(null), 4000);
      setEditingConfig(null);
      await loadData();
      const updated = await hypothesisService.getReliabilityConfigs(caseId);
      setReliabilityConfigs(updated);
    } catch (err) {
      console.error('Failed to save reliability config:', err);
    } finally {
      setSavingConfig(false);
    }
  };

  const getEvidenceTypeBadge = (evType?: string) => {
    const t = (evType || 'document').toLowerCase();
    if (t.includes('dna')) {
      return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-purple-50 text-purple-700 border border-purple-200">DNA (0.95)</span>;
    }
    if (t.includes('fingerprint')) {
      return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">Fingerprint (0.90)</span>;
    }
    if (t.includes('cctv')) {
      return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-blue-50 text-blue-700 border border-blue-200">CCTV (0.85)</span>;
    }
    if (t.includes('cdr')) {
      return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-cyan-50 text-cyan-700 border border-cyan-200">CDR (0.80)</span>;
    }
    if (t.includes('confession')) {
      return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-rose-50 text-rose-700 border border-rose-200">Sec 164 Confession (0.40)</span>;
    }
    if (t.includes('witness')) {
      return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-amber-50 text-amber-700 border border-amber-200">Witness (0.55)</span>;
    }
    return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-stone-100 text-stone-700 border border-stone-200">Document (0.70)</span>;
  };

  const getEvidenceIcon = (fileType: string) => {
    const ft = (fileType || '').toLowerCase();
    if (ft.includes('video') || ft.includes('cctv') || ft.includes('mp4')) {
      return <Video className="w-3.5 h-3.5 text-blue-600 shrink-0" />;
    }
    if (ft.includes('audio') || ft.includes('call') || ft.includes('voice')) {
      return <Mic className="w-3.5 h-3.5 text-purple-600 shrink-0" />;
    }
    return <FileText className="w-3.5 h-3.5 text-amber-600 shrink-0" />;
  };

  const formatClassificationLabel = (cls: string) => {
    const c = (cls || 'neutral').toLowerCase();
    if (c === 'strong_support') return { label: 'Strong Support (++)', color: 'bg-emerald-50 text-emerald-800 border-emerald-300' };
    if (c === 'moderate_support') return { label: 'Moderate Support (+)', color: 'bg-emerald-50/70 text-emerald-700 border-emerald-200' };
    if (c === 'weak_support') return { label: 'Weak Support', color: 'bg-teal-50 text-teal-700 border-teal-200' };
    if (c === 'strong_contradiction') return { label: 'Strong Contradiction (--)', color: 'bg-rose-50 text-rose-800 border-rose-300' };
    if (c === 'moderate_contradiction') return { label: 'Moderate Contradiction (-)', color: 'bg-rose-50/70 text-rose-700 border-rose-200' };
    if (c === 'weak_contradiction') return { label: 'Weak Contradiction', color: 'bg-amber-50 text-amber-800 border-amber-200' };
    return { label: 'Neutral / Inconclusive (0)', color: 'bg-stone-50 text-stone-600 border-stone-200' };
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-24 text-[#191410]">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-[#eae4d9]">
        <div>
          <div className="text-[11px] font-mono tracking-widest text-[#d93829] uppercase font-bold mb-1 flex items-center gap-1.5">
            <Scale className="w-3.5 h-3.5 text-[#d93829]" />
            <span>True Heuer ACH Engine • Disconfirmation-First • Diagnosticity Weighted</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-serif font-bold text-[#191410]">
            Analysis of Competing Hypotheses (ACH)
          </h1>
          <p className="text-xs text-[#6e665d] mt-1 max-w-3xl">
            Richards J. Heuer's methodology: hypotheses are evaluated primarily by eliminating inconsistencies (disconfirmation), with evidence weighted by diagnosticity. Relative support scores strictly sum to 100.0%.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* View Mode Toggle */}
          <div className="flex items-center bg-[#f0ebe1] p-1 rounded-full border border-[#d8d0c5]">
            <button
              onClick={() => setViewMode('ranked')}
              className={cn(
                "px-3 py-1 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer",
                viewMode === 'ranked' ? "bg-white text-[#191410] shadow-xs" : "text-[#6e665d] hover:text-[#191410]"
              )}
            >
              <BarChart2 className="w-3.5 h-3.5" />
              <span>Ranked Cards</span>
            </button>
            <button
              onClick={() => setViewMode('matrix')}
              className={cn(
                "px-3 py-1 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer",
                viewMode === 'matrix' ? "bg-white text-[#191410] shadow-xs" : "text-[#6e665d] hover:text-[#191410]"
              )}
            >
              <TableIcon className="w-3.5 h-3.5" />
              <span>ACH Heatmap Grid</span>
            </button>
          </div>

          <button
            onClick={handleOpenReliabilityConfigs}
            className="flex items-center gap-1.5 px-3 py-2 bg-[#faf7f2] hover:bg-[#eae4d9] text-[#191410] rounded-full text-xs font-bold transition-all border border-[#d8d0c5] cursor-pointer shadow-xs"
            title="Inspect and customize base reliabilities & legal rationales per evidence type"
          >
            <Settings className="w-3.5 h-3.5 text-[#6e665d]" />
            <span>Reliability Config</span>
          </button>

          <button
            onClick={handleOpenSensitivity}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-[#faf7f2] hover:bg-[#191410] hover:text-white text-[#191410] rounded-full text-xs font-bold transition-all border border-[#d8d0c5] cursor-pointer shadow-xs"
            title="Evaluate how single exhibits influence the overall conclusion (Heuer Step 6)"
          >
            <Sliders className="w-3.5 h-3.5 text-[#d93829]" />
            <span>Sensitivity Analysis</span>
          </button>
          
          <button
            onClick={handleRunACHAnalysis}
            disabled={evaluating !== null}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-[#191410] hover:bg-[#2e261f] text-white rounded-full text-xs font-bold transition-all disabled:opacity-50 cursor-pointer shadow-xs border border-[#3d332a]"
          >
            {evaluating === 'ACH' ? <Loader2 className="w-3.5 h-3.5 animate-spin text-[#d93829]" /> : <Cpu className="w-3.5 h-3.5 text-[#d93829]" />}
            <span>{evaluating === 'ACH' ? 'Computing ACH...' : 'Run Dataset Analysis'}</span>
          </button>

          <button
            onClick={handleEvaluateAll}
            disabled={evaluating !== null}
            className="flex items-center gap-1.5 px-3 py-2 bg-[#fdeee9] hover:bg-[#d93829] text-[#d93829] hover:text-white rounded-full text-xs font-bold transition-all border border-[#f6d0c7] disabled:opacity-50 cursor-pointer shadow-xs"
          >
            {evaluating === 'ALL' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
            <span>{evaluating === 'ALL' ? 'Evaluating...' : 'AI Re-Evaluate All'}</span>
          </button>

          <button 
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-[#d93829] hover:bg-[#bf2b1d] text-white rounded-full text-xs font-bold transition-all shadow-xs cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Hypothesis</span>
          </button>
        </div>
      </div>

      {/* Notification Toast Banner */}
      {notificationMsg && (
        <div className={cn(
          "p-3.5 rounded-2xl text-xs font-mono font-medium flex items-center justify-between animate-in fade-in slide-in-from-top-2 border shadow-xs",
          notificationMsg.type === 'success' ? "bg-emerald-50 text-emerald-900 border-emerald-300" : 
          notificationMsg.type === 'warning' ? "bg-amber-50 text-amber-900 border-amber-300" :
          "bg-blue-50 text-blue-900 border-blue-300"
        )}>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{notificationMsg.text}</span>
          </div>
          <button onClick={() => setNotificationMsg(null)} className="text-stone-400 hover:text-stone-700">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Honest Methodology & Legal Disclaimer Banner */}
      <div className="p-3.5 rounded-2xl bg-amber-50/60 border border-amber-200/80 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs shadow-xs">
        <div className="flex items-start gap-2.5">
          <Info className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold text-amber-950 font-serif">Methodological Note on Relative Support: </span>
            <span className="text-amber-900">
              Scores represent relative explanatory strength among the evaluated hypotheses ($\sum = 100\%$). They do not constitute an absolute legal probability of guilt or replace judicial evaluation. Disconfirmation penalties heavily suppress contradicted theories.
            </span>
          </div>
        </div>
        <div className="shrink-0 flex items-center gap-2 font-mono font-bold text-amber-900 text-[11px] bg-white/80 px-3 py-1 rounded-full border border-amber-200">
          <span>Heuer Inconsistency Dominant: $\sum = 100.0\%$</span>
        </div>
      </div>

      {/* Loading Indicator */}
      {loading && (
        <div className="py-20 text-center">
          <div className="w-8 h-8 border-2 border-[#d93829] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-xs text-[#8c8276] font-mono">Resolving Exhibit Reliabilities & Computing ACH Contributions...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && hypotheses.length === 0 && (
        <div className="text-center py-16 border border-dashed border-[#eae4d9] bg-white rounded-3xl">
          <Lightbulb className="w-12 h-12 text-[#b0a89d] mx-auto mb-3" />
          <h3 className="text-base font-serif font-bold text-[#191410]">No Hypotheses Defined Yet</h3>
          <p className="text-xs text-[#6e665d] mt-1">Add a new investigative hypothesis or click "Run Dataset Analysis" above to generate competing theories with Gemini.</p>
        </div>
      )}

      {/* VIEW MODE 1: RANKED CARDS & ERROR BARS */}
      {!loading && hypotheses.length > 0 && viewMode === 'ranked' && (
        <div className="space-y-6">
          {hypotheses.map((h, idx) => {
            const score = h.support_score ?? h.confidence ?? 50;
            const penalty = h.disconfirmation_penalty ?? (h as any).disconfirmationPenalty ?? 0.0;
            const isPrimary = idx === 0 && score >= 45.0 && penalty < 2.0;
            const isDiscarded = h.status === 'Discarded' || penalty >= 4.0 || score < 2.0;
            const isExpanded = expandedHypothesis === h.id;
            const robustness = robustnessRanges[String(h.id)] || robustnessRanges[h.id];

            // Enrich assessments with caseEvidence metadata & diagnosticity
            const rawAssessments: EvidenceAssessment[] = (h.assessments && h.assessments.length > 0)
              ? h.assessments
              : [
                  ...h.supportingEvidenceIds.map((eid, i) => ({
                    id: `sup-${eid}-${i}`,
                    hypothesis_id: h.id,
                    evidence_id: eid,
                    classification: 'strong_support',
                    reason: 'Forensic exhibit provides direct affirmative corroboration for this hypothesis.',
                    llm_confidence: 0.94
                  } as unknown as EvidenceAssessment)),
                  ...h.contradictingEvidenceIds.map((eid, i) => ({
                    id: `con-${eid}-${i}`,
                    hypothesis_id: h.id,
                    evidence_id: eid,
                    classification: 'strong_contradiction',
                    reason: 'Forensic exhibit presents contradictory alibi or forensic physical discrepancy.',
                    llm_confidence: 0.89
                  } as unknown as EvidenceAssessment))
                ];

            const enriched = rawAssessments.map(a => {
              const strId = String(a.evidence_id || '').replace(/^E-/, '').trim();
              const found = caseEvidence.find(e => 
                String(e.id) === strId || 
                String(e.id) === String(a.evidence_id) ||
                (a.evidence_file_name && (e.fileName === a.evidence_file_name || (e as any).file_name === a.evidence_file_name))
              );
              return {
                ...a,
                evidenceId: found ? String(found.id) : String(a.evidence_id),
                fileName: a.evidence_file_name || found?.fileName || (found as any)?.file_name || `Exhibit #${a.evidence_id}`,
                fileType: found?.fileType || (found as any)?.file_type || 'Document',
                evidenceType: a.evidence_type || found?.evidence_type || 'document'
              };
            });

            return (
              <div 
                key={`${h.id}-${idx}`}
                className={cn(
                  "rounded-3xl bg-white border transition-all overflow-hidden shadow-xs",
                  isPrimary && "border-emerald-300 ring-1 ring-emerald-400/20",
                  isDiscarded && "border-[#e0d9cf] opacity-85",
                  !isPrimary && !isDiscarded && "border-[#eae4d9]"
                )}
              >
                {/* Header Card */}
                <div className="p-6">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-3">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs font-bold text-white bg-[#191410] px-3 py-1 rounded-full shrink-0">
                        Rank #{idx + 1} • H{idx + 1}
                      </span>
                      <h3 className="text-lg font-serif font-bold text-[#191410]">
                        {h.title}
                      </h3>
                      <span className={cn(
                        "px-3 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border shrink-0",
                        isPrimary && "bg-emerald-50 text-emerald-800 border-emerald-300",
                        isDiscarded && "bg-stone-100 text-stone-600 border-stone-200",
                        !isPrimary && !isDiscarded && "bg-blue-50 text-blue-700 border-blue-200"
                      )}>
                        {isPrimary ? 'Primary Candidate' : isDiscarded ? 'Disproven / Discarded' : (h.status || 'Active')}
                      </span>
                    </div>

                    <div className="flex items-center gap-4">
                      {/* Normalized Relative Support with Robustness Error Bar */}
                      <div className="text-right">
                        <div className="flex items-center justify-end gap-1 text-[10px] font-mono text-[#8c8276] uppercase tracking-wider font-semibold">
                          <span>Relative Support</span>
                        </div>
                        <div className={cn(
                          "text-xl font-mono font-bold",
                          score >= 40 && "text-emerald-700",
                          score < 40 && score > 10 && "text-amber-700",
                          score <= 10 && "text-rose-700"
                        )}>
                          {score.toFixed(1)}%
                        </div>
                        {robustness && (
                          <div className="text-[10px] font-mono font-medium text-[#6e665d]" title="Sensitivity range observed across exhibit removals & ±20% reliability perturbation">
                            Range: {robustness.min_score}% – {robustness.max_score}%
                          </div>
                        )}
                        <div className="text-[10px] font-mono font-semibold text-rose-700">
                          Inconsistency Penalty: {penalty.toFixed(2)}
                        </div>
                      </div>

                      {/* Visual Bar with Robustness Range Indicator */}
                      <div className="w-28 relative">
                        <div className="w-full bg-[#f0ebe1] h-3 rounded-full overflow-hidden relative">
                          <div 
                            className={cn(
                              "h-full rounded-full transition-all duration-500",
                              score >= 40 && "bg-emerald-500",
                              score < 40 && score > 10 && "bg-amber-500",
                              score <= 10 && "bg-rose-500"
                            )}
                            style={{ width: `${Math.max(4, score)}%` }}
                          />
                        </div>
                        {/* Error Bar overlay */}
                        {robustness && robustness.range_spread > 0 && (
                          <div 
                            className="absolute top-1/2 -translate-y-1/2 h-1 bg-black/40 rounded-full pointer-events-none"
                            style={{
                              left: `${robustness.min_score}%`,
                              width: `${Math.max(3, robustness.max_score - robustness.min_score)}%`
                            }}
                            title={`Robustness range spread: ${robustness.range_spread}%`}
                          />
                        )}
                      </div>

                      <button
                        onClick={() => handleOpenBreakdown(h)}
                        className="px-3.5 py-1.5 rounded-full bg-[#191410] hover:bg-[#d93829] text-white text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer shadow-xs"
                        title="View mathematical breakdown of exhibit contributions, reliabilities, and verified quotes"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Breakdown</span>
                      </button>

                      <button
                        onClick={() => handleEvaluate(h.id)}
                        disabled={evaluating === h.id}
                        className="p-1.5 rounded-full bg-[#faf7f2] hover:bg-[#d93829] text-[#191410] hover:text-white border border-[#eae4d9] transition-all cursor-pointer disabled:opacity-50"
                        title="Run AI Neural Evaluation for this hypothesis"
                      >
                        {evaluating === h.id ? (
                          <Loader2 className="w-4 h-4 animate-spin text-[#d93829]" />
                        ) : (
                          <Sparkles className="w-4 h-4" />
                        )}
                      </button>

                      <button
                        onClick={() => setExpandedHypothesis(isExpanded ? null : h.id)}
                        className="p-1.5 text-[#8c8276] hover:text-[#191410] rounded-full hover:bg-[#faf7f2] transition-colors cursor-pointer"
                        title={isExpanded ? "Collapse Card" : "Expand Card"}
                      >
                        {isExpanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                      </button>
                    </div>
                  </div>

                  <p className="text-xs text-[#6e665d] leading-relaxed max-w-4xl">
                    {h.description || 'No detailed hypothesis theory provided.'}
                  </p>
                </div>

                {/* Expanded Card Details */}
                {isExpanded && (
                  <div className="border-t border-[#eae4d9] bg-[#faf7f2]/50 p-6 space-y-4">
                    <div className="flex items-center justify-between pb-2">
                      <div className="text-xs font-mono font-bold uppercase tracking-wider text-[#6e665d] flex items-center gap-1.5">
                        <Scale className="w-3.5 h-3.5 text-[#d93829]" />
                        <span>Evidence Assessments & Matrix Contributions ({enriched.length} Exhibits)</span>
                      </div>
                      <button
                        onClick={() => handleOpenBreakdown(h)}
                        className="text-xs text-[#d93829] hover:underline font-mono font-bold flex items-center gap-1 cursor-pointer"
                      >
                        <span>Open Full Table with Reliability Audit & Quotes</span>
                        <ArrowUpRight className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {enriched.map((a, aIdx) => {
                        const isOverridden = a.analyst_override || (a as any).analystOverride;
                        const diagWeight = a.diagnosticity_weight ?? 1.0;
                        const diagCategory = a.diagnosticity_category ?? 'Medium';
                        const clsMeta = formatClassificationLabel(a.classification);
                        const contrib = a.final_contribution ?? 0.0;

                        return (
                          <div 
                            key={`assess-${a.evidence_id}-${aIdx}`}
                            className={cn(
                              "p-3.5 rounded-2xl bg-white border text-xs space-y-2.5 shadow-xs transition-all",
                              isOverridden ? "border-amber-300 ring-1 ring-amber-300/40" : "border-[#eae4d9]"
                            )}
                          >
                            <div className="flex items-center justify-between gap-2">
                              <div className="flex items-center gap-2 font-medium text-[#191410] truncate">
                                {getEvidenceIcon(a.fileType || '')}
                                <Link 
                                  to={`/cases/${caseId}/evidence/${a.evidenceId}`}
                                  className="truncate font-semibold hover:text-[#d93829] hover:underline flex items-center gap-1"
                                >
                                  <span>{a.fileName}</span>
                                  <ArrowUpRight className="w-3 h-3 text-stone-400" />
                                </Link>
                              </div>
                              <div className="flex items-center gap-1.5 shrink-0">
                                {getEvidenceTypeBadge(a.evidenceType)}
                                <span className={cn(
                                  "px-2 py-0.5 rounded-md text-[10px] font-mono font-bold border",
                                  diagCategory === 'High' ? "bg-amber-50 text-amber-900 border-amber-300" :
                                  diagCategory === 'Low' ? "bg-stone-50 text-stone-600 border-stone-200" :
                                  "bg-blue-50 text-blue-900 border-blue-200"
                                )}>
                                  Diag: {diagWeight}x
                                </span>
                              </div>
                            </div>

                            <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-[#f0ebe1]">
                              <span className={cn("px-2.5 py-1 rounded-md text-[11px] font-mono font-bold border", clsMeta.color)}>
                                {clsMeta.label}
                              </span>

                              <div className="flex items-center gap-2 font-mono text-[11px]">
                                <span className="text-[#6e665d]">Signed Contribution:</span>
                                <span className={cn(
                                  "font-bold",
                                  contrib > 0 ? "text-emerald-700" : contrib < 0 ? "text-rose-700" : "text-stone-500"
                                )}>
                                  {contrib > 0 ? `+${contrib.toFixed(2)}` : contrib.toFixed(2)}
                                </span>
                              </div>
                            </div>

                            {/* Quoted Source Line if available */}
                            {a.quoted_source_line && (
                              <div className="p-2 rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-[11px] font-mono text-[#383129] flex items-start gap-1.5">
                                <Quote className="w-3 h-3 text-[#d93829] shrink-0 mt-0.5" />
                                <span className="italic">"{a.quoted_source_line}"</span>
                              </div>
                            )}

                            {/* Analyst Inline Override Dropdown */}
                            <div className="flex items-center justify-between gap-2 pt-2 border-t border-[#f5f0e8] text-[11px]">
                              <div className="flex items-center gap-1.5">
                                <SlidersHorizontal className="w-3 h-3 text-[#6e665d]" />
                                <span className="text-[#6e665d] font-mono">Override:</span>
                                <select
                                  value={a.classification}
                                  onChange={(e) => handleOverrideClassification(h.id, a.evidence_id || (a as any).evidenceId, e.target.value)}
                                  className="px-2 py-0.5 rounded-lg bg-[#faf7f2] border border-[#d8d0c5] text-[11px] font-mono font-medium focus:outline-hidden focus:border-[#d93829]"
                                >
                                  <option value="strong_support">Strong Support (++)</option>
                                  <option value="moderate_support">Moderate Support (+)</option>
                                  <option value="weak_support">Weak Support</option>
                                  <option value="neutral">Neutral / Inconclusive (0)</option>
                                  <option value="weak_contradiction">Weak Contradiction</option>
                                  <option value="moderate_contradiction">Moderate Contradiction (-)</option>
                                  <option value="strong_contradiction">Strong Contradiction (--)</option>
                                </select>
                              </div>

                              {isOverridden && (
                                <button
                                  onClick={() => handleResetClassification(h.id, a.evidence_id || (a as any).evidenceId)}
                                  className="text-[10px] font-mono font-bold text-amber-700 hover:text-amber-900 flex items-center gap-1 cursor-pointer"
                                  title="Reset to AI baseline classification"
                                >
                                  <RotateCcw className="w-2.5 h-2.5" />
                                  <span>Reset AI</span>
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* VIEW MODE 2: CLASSIC ACH HEATMAP MATRIX */}
      {!loading && hypotheses.length > 0 && viewMode === 'matrix' && (
        <Card className="rounded-3xl border border-[#eae4d9] overflow-hidden shadow-xs bg-white">
          <CardHeader className="bg-[#faf7f2] border-b border-[#eae4d9] p-4 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-base font-serif font-bold text-[#191410] flex items-center gap-2">
                <TableIcon className="w-4 h-4 text-[#d93829]" />
                <span>Analysis of Competing Hypotheses (ACH) Heatmap Matrix</span>
              </CardTitle>
              <p className="text-xs text-[#6e665d] mt-0.5">
                Full cross-evaluation grid: rows represent evidentiary exhibits with diagnosticity weights; columns represent candidate hypotheses.
              </p>
            </div>
            <div className="text-xs font-mono font-bold text-[#d93829]">
              Heuer Step 3 & 4 Matrix View
            </div>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="bg-[#f5f0e8] border-b border-[#eae4d9]">
                  <th className="p-3.5 font-mono font-bold text-[#191410] min-w-[220px]">
                    Evidence Exhibits & Diagnosticity
                  </th>
                  {hypotheses.map((h, hIdx) => {
                    const score = h.support_score ?? h.confidence ?? 50;
                    const robustness = robustnessRanges[String(h.id)] || robustnessRanges[h.id];
                    return (
                      <th key={`matrix-head-${h.id}`} className="p-3.5 border-l border-[#eae4d9] min-w-[190px]">
                        <div className="flex items-center justify-between gap-1 mb-1">
                          <span className="font-mono text-[10px] font-bold px-2 py-0.5 bg-[#191410] text-white rounded-full">
                            H{hIdx + 1}
                          </span>
                          <span className="font-mono text-xs font-bold text-emerald-800">
                            {score.toFixed(1)}%
                          </span>
                        </div>
                        <div className="font-serif font-bold text-[#191410] truncate text-xs" title={h.title}>
                          {h.title}
                        </div>
                        {robustness && (
                          <div className="text-[10px] font-mono text-[#6e665d] mt-0.5">
                            Range: {robustness.min_score}%–{robustness.max_score}%
                          </div>
                        )}
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#eae4d9]">
                {caseEvidence.map((ev) => {
                  return (
                    <tr key={`matrix-row-${ev.id}`} className="hover:bg-[#faf7f2]/60 transition-colors">
                      <td className="p-3.5 bg-white font-medium">
                        <div className="flex items-center gap-2 mb-1">
                          {getEvidenceIcon(ev.fileType || '')}
                          <Link 
                            to={`/cases/${caseId}/evidence/${ev.id}`} 
                            className="font-serif font-bold text-[#191410] hover:text-[#d93829] hover:underline truncate"
                          >
                            {ev.fileName || (ev as any).file_name || `Exhibit #${ev.id}`}
                          </Link>
                        </div>
                        <div className="flex items-center gap-1.5">
                          {getEvidenceTypeBadge(ev.evidence_type)}
                          <select
                            value={ev.evidence_type || 'document'}
                            onChange={(e) => handleOverrideEvidenceType(ev.id, e.target.value)}
                            className="text-[10px] font-mono bg-[#faf7f2] border border-[#d8d0c5] rounded-md px-1.5 py-0.5 text-[#6e665d]"
                            title="Change evidence category to re-resolve base reliability"
                          >
                            <option value="DNA">DNA</option>
                            <option value="fingerprint">Fingerprint</option>
                            <option value="CCTV">CCTV</option>
                            <option value="CDR">CDR</option>
                            <option value="document">Document</option>
                            <option value="witness">Witness</option>
                            <option value="confession">Confession</option>
                          </select>
                        </div>
                      </td>

                      {hypotheses.map((h) => {
                        const assessment = (h.assessments || []).find(
                          a => String(a.evidence_id) === String(ev.id) || String((a as any).evidenceId) === String(ev.id)
                        );
                        const cls = assessment ? assessment.classification : 'neutral';
                        const meta = formatClassificationLabel(cls);
                        const isOverridden = assessment?.analyst_override || (assessment as any)?.analystOverride;

                        return (
                          <td key={`cell-${h.id}-${ev.id}`} className="p-3 border-l border-[#eae4d9] align-top bg-white">
                            <div className={cn(
                              "p-2 rounded-xl border text-xs space-y-1.5 transition-all",
                              meta.color,
                              isOverridden && "ring-1 ring-amber-400"
                            )}>
                              <div className="flex items-center justify-between gap-1 font-mono font-bold text-[10px]">
                                <span>{meta.label}</span>
                                {isOverridden && (
                                  <span className="text-amber-800" title="Analyst Override Active">★ Override</span>
                                )}
                              </div>

                              {assessment?.quoted_source_line && (
                                <button
                                  type="button"
                                  onClick={() => handleOpenSourceSpan(ev.id, ev.fileName || (ev as any).file_name, assessment.quoted_source_line)}
                                  className="w-full text-left text-[10px] font-mono italic truncate text-black/80 hover:text-[#d93829] hover:bg-black/5 p-1 rounded flex items-center gap-1 transition-all cursor-pointer group"
                                  title={`Inspect source quote: "${assessment.quoted_source_line}"`}
                                >
                                  <Quote className="w-2.5 h-2.5 shrink-0 text-[#d93829]" />
                                  <span className="truncate underline decoration-dotted">{assessment.quoted_source_line}</span>
                                </button>
                              )}

                              <div className="pt-1 border-t border-black/10 flex items-center justify-between">
                                <select
                                  value={cls}
                                  onChange={(e) => handleOverrideClassification(h.id, ev.id, e.target.value)}
                                  className="text-[10px] font-mono bg-white/90 border border-black/20 rounded-md px-1.5 py-0.5 text-black"
                                >
                                  <option value="strong_support">++ Strong Support</option>
                                  <option value="moderate_support">+ Moderate Support</option>
                                  <option value="weak_support">Weak Support</option>
                                  <option value="neutral">0 Neutral</option>
                                  <option value="weak_contradiction">Weak Contradiction</option>
                                  <option value="moderate_contradiction">- Moderate Contradiction</option>
                                  <option value="strong_contradiction">-- Strong Contradiction</option>
                                </select>

                                {isOverridden && (
                                  <button
                                    onClick={() => handleResetClassification(h.id, ev.id)}
                                    className="text-[9px] font-mono text-stone-600 hover:text-black cursor-pointer"
                                    title="Reset to AI baseline"
                                  >
                                    <RotateCcw className="w-2.5 h-2.5" />
                                  </button>
                                )}
                              </div>
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* DETAILED MATHEMATICAL BREAKDOWN MODAL / DRAWER */}
      {breakdownModalHyp && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-200">
          <div className="bg-white rounded-3xl max-w-5xl w-full p-6 space-y-5 border border-[#eae4d9] shadow-2xl max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9]">
              <div>
                <div className="text-[11px] font-mono font-bold uppercase tracking-wider text-[#d93829] flex items-center gap-1.5">
                  <Scale className="w-3.5 h-3.5" />
                  <span>Heuer ACH Mathematical Breakdown • Hypothesis #{breakdownModalHyp.id}</span>
                </div>
                <h2 className="text-xl font-serif font-bold text-[#191410] mt-0.5">
                  {breakdownModalHyp.title}
                </h2>
              </div>
              <button 
                onClick={() => setBreakdownModalHyp(null)}
                className="p-2 rounded-full hover:bg-stone-100 text-stone-500 hover:text-stone-800 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {loadingBreakdown ? (
              <div className="py-20 text-center">
                <Loader2 className="w-8 h-8 animate-spin text-[#d93829] mx-auto mb-2" />
                <p className="text-xs font-mono text-[#8c8276]">Resolving reliability audits & exact quoted source lines...</p>
              </div>
            ) : (
              <div className="overflow-y-auto flex-1 space-y-4 pr-1">
                <div className="p-3.5 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] flex flex-wrap items-center justify-between text-xs font-mono gap-3">
                  <div>
                    <span className="font-bold text-[#191410]">Normalized Relative Support: </span>
                    <span className="text-emerald-800 font-bold text-sm">
                      {(breakdownModalHyp.support_score ?? 0).toFixed(1)}%
                    </span>
                  </div>
                  <div>
                    <span className="font-bold text-[#191410]">Disconfirmation Inconsistency: </span>
                    <span className="text-rose-800 font-bold text-sm">
                      {(breakdownModalHyp.disconfirmation_penalty ?? 0).toFixed(2)}
                    </span>
                  </div>
                  <div>
                    <span className="font-bold text-[#191410]">Total Evaluated Exhibits: </span>
                    <span>{breakdownRows.length}</span>
                  </div>
                </div>

                <div className="border border-[#eae4d9] rounded-2xl overflow-hidden">
                  <table className="w-full text-xs text-left border-collapse">
                    <thead className="bg-[#f5f0e8] border-b border-[#eae4d9] font-mono text-[11px]">
                      <tr>
                        <th className="p-3 font-bold text-[#191410]">Exhibit</th>
                        <th className="p-3 font-bold text-[#191410]">Classification</th>
                        <th className="p-3 font-bold text-[#191410]">Resolved Reliability</th>
                        <th className="p-3 font-bold text-[#191410]">Diagnosticity</th>
                        <th className="p-3 font-bold text-[#191410]">Contribution</th>
                        <th className="p-3 font-bold text-[#191410]">Share of Support</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#eae4d9]">
                      {breakdownRows.map((row, rIdx) => {
                        const meta = formatClassificationLabel(row.classification);
                        return (
                          <tr key={`breakdown-row-${row.evidence_id}-${rIdx}`} className="hover:bg-[#faf7f2]/60">
                            <td className="p-3">
                              <div className="font-serif font-bold text-[#191410] flex items-center gap-1.5">
                                <Link 
                                  to={`/cases/${caseId}/evidence/${row.evidence_id}`}
                                  className="hover:text-[#d93829] hover:underline"
                                >
                                  {row.evidence_title}
                                </Link>
                              </div>
                              <div className="mt-1">
                                {getEvidenceTypeBadge(row.evidence_type)}
                              </div>
                              {row.quoted_source_line && (
                                <button
                                  type="button"
                                  onClick={() => handleOpenSourceSpan(row.evidence_id, row.evidence_title, row.quoted_source_line)}
                                  className="mt-2 w-full text-left p-2 rounded-lg bg-[#faf7f2] hover:bg-[#f2ece1] border border-[#eae4d9] text-[11px] font-mono text-[#383129] flex items-start gap-1.5 transition-all cursor-pointer group"
                                  title="Open exhibit viewer and highlight exact source quote"
                                >
                                  <Quote className="w-3.5 h-3.5 text-[#d93829] shrink-0 mt-0.5" />
                                  <div className="flex-1 min-w-0">
                                    <span className="italic block truncate">"{row.quoted_source_line}"</span>
                                    <span className="block text-[10px] text-[#d93829] font-bold mt-1 group-hover:underline">
                                      Inspect Source Span →
                                    </span>
                                  </div>
                                </button>
                              )}
                              {row.reason && (
                                <p className="mt-1 text-[11px] text-[#6e665d]">
                                  {row.reason}
                                </p>
                              )}
                            </td>

                            <td className="p-3 align-top">
                              <span className={cn("px-2.5 py-1 rounded-md text-[10px] font-mono font-bold border block text-center", meta.color)}>
                                {meta.label}
                              </span>
                              {row.analyst_override && (
                                <span className="text-[10px] font-mono text-amber-800 font-bold block text-center mt-1">
                                  ★ Overridden
                                </span>
                              )}
                            </td>

                            <td className="p-3 align-top font-mono">
                              <div className="font-bold text-[#191410] text-sm">
                                {row.computed_reliability}
                              </div>
                              {row.reliability_audit && (
                                <div className="text-[10px] text-[#6e665d] space-y-0.5 mt-1">
                                  <div>Base: {row.reliability_audit.base_value}</div>
                                  {Object.entries(row.reliability_audit.modifiers_applied || {}).map(([mod, val]: any) => (
                                    <div key={mod} className={val > 0 ? "text-emerald-700" : "text-rose-700"}>
                                      {mod.replace(/_/g, ' ')}: {val > 0 ? `+${val}` : val}
                                    </div>
                                  ))}
                                </div>
                              )}
                            </td>

                            <td className="p-3 align-top font-mono">
                              <span className={cn(
                                "px-2 py-0.5 rounded-md text-[10px] font-mono font-bold border",
                                row.computed_diagnosticity >= 1.5 ? "bg-amber-50 text-amber-900 border-amber-300" :
                                row.computed_diagnosticity < 0.6 ? "bg-stone-50 text-stone-600 border-stone-200" :
                                "bg-blue-50 text-blue-900 border-blue-200"
                              )}>
                                {row.computed_diagnosticity}x
                              </span>
                            </td>

                            <td className="p-3 align-top font-mono font-bold text-sm">
                              <span className={row.contribution > 0 ? "text-emerald-700" : row.contribution < 0 ? "text-rose-700" : "text-stone-500"}>
                                {row.contribution > 0 ? `+${row.contribution.toFixed(2)}` : row.contribution.toFixed(2)}
                              </span>
                            </td>

                            <td className="p-3 align-top font-mono">
                              {row.share_of_support_pct > 0 ? (
                                <div className="flex items-center gap-1.5">
                                  <div className="w-12 bg-[#f0ebe1] h-2 rounded-full overflow-hidden">
                                    <div className="bg-emerald-500 h-full" style={{ width: `${row.share_of_support_pct}%` }} />
                                  </div>
                                  <span className="font-bold text-[#191410]">{row.share_of_support_pct}%</span>
                                </div>
                              ) : (
                                <span className="text-stone-400">0.0%</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <div className="pt-3 border-t border-[#eae4d9] flex justify-end">
              <button
                onClick={() => setBreakdownModalHyp(null)}
                className="px-5 py-2 rounded-full bg-[#191410] text-white text-xs font-bold hover:bg-[#2e261f] cursor-pointer"
              >
                Close Breakdown
              </button>
            </div>
          </div>
        </div>
      )}

      {/* SENSITIVITY ANALYSIS MODAL (HEUER STEP 6) */}
      {isSensitivityOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-200">
          <div className="bg-white rounded-3xl max-w-4xl w-full p-6 space-y-6 border border-[#eae4d9] shadow-2xl max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9]">
              <div>
                <div className="text-[11px] font-mono font-bold uppercase tracking-wider text-[#d93829] flex items-center gap-1.5">
                  <Sliders className="w-3.5 h-3.5" />
                  <span>Heuer Step 6 • Sensitivity & Robustness Analysis</span>
                </div>
                <h2 className="text-xl font-serif font-bold text-[#191410] mt-0.5">
                  Single-Exhibit Dependency & Pivot Analysis
                </h2>
              </div>
              <button 
                onClick={() => setIsSensitivityOpen(false)}
                className="p-2 rounded-full hover:bg-stone-100 text-stone-500 hover:text-stone-800 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {loadingSensitivity ? (
              <div className="py-20 text-center">
                <Loader2 className="w-8 h-8 animate-spin text-[#d93829] mx-auto mb-2" />
                <p className="text-xs font-mono text-[#8c8276]">Simulating leave-one-out runs & ±20% reliability perturbations...</p>
              </div>
            ) : (
              <div className="overflow-y-auto flex-1 space-y-6 pr-1">
                {/* Critical Pivot Alert */}
                {sensitivityData?.most_critical_evidence_name && (
                  <div className="p-4 rounded-2xl bg-amber-50 border border-amber-300 text-xs space-y-2">
                    <div className="flex items-center gap-2 text-amber-900 font-bold font-serif text-sm">
                      <ShieldAlert className="w-4 h-4 text-amber-700" />
                      <span>Critical Pivot Evidence Detected: {sensitivityData.most_critical_evidence_name}</span>
                    </div>
                    <p className="text-amber-800 leading-relaxed">
                      Richards Heuer Warning: Excluding this single exhibit alters which hypothesis ranks #1 or produces a massive shift in probability. The investigative finding critically depends upon the chain of custody and credibility of this exhibit.
                    </p>
                  </div>
                )}

                {/* Exhibit Impact Table with Interactive Exclude Toggle */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-serif font-bold text-[#191410]">
                      Leave-One-Out (LOO) Exhibit Impact
                    </h4>
                    <span className="text-[11px] font-mono text-[#6e665d]">
                      Toggle checkboxes to simulate hypothetical exclusion in real time
                    </span>
                  </div>

                  <div className="border border-[#eae4d9] rounded-2xl overflow-hidden">
                    <table className="w-full text-xs text-left border-collapse">
                      <thead className="bg-[#f5f0e8] border-b border-[#eae4d9] font-mono text-[11px]">
                        <tr>
                          <th className="p-3 font-bold text-[#191410] text-center w-12">Exclude</th>
                          <th className="p-3 font-bold text-[#191410]">Exhibit</th>
                          <th className="p-3 font-bold text-[#191410]">Diagnosticity</th>
                          <th className="p-3 font-bold text-[#191410]">Impact Classification</th>
                          <th className="p-3 font-bold text-[#191410]">Top Hypothesis Without Exhibit</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#eae4d9]">
                        {sensitivityData?.exhibit_impacts.map((imp) => {
                          const isExcluded = excludedExhibitIds.includes(Number(imp.evidence_id));
                          const isCritical = imp.is_critical_pivot || imp.impact_level === 'CRITICAL_PIVOT';

                          return (
                            <tr key={`sens-${imp.evidence_id}`} className={cn("hover:bg-[#faf7f2]/60", isExcluded && "bg-rose-50/50")}>
                              <td className="p-3 text-center">
                                <input 
                                  type="checkbox"
                                  checked={isExcluded}
                                  onChange={() => handleToggleExcludeExhibit(imp.evidence_id)}
                                  className="w-4 h-4 rounded-sm text-[#d93829] cursor-pointer"
                                />
                              </td>
                              <td className="p-3">
                                <div className="font-serif font-bold text-[#191410]">
                                  {imp.file_name}
                                </div>
                                <div className="text-[10px] font-mono text-[#8c8276]">
                                  Type: {imp.file_type}
                                </div>
                              </td>
                              <td className="p-3 font-mono">
                                <span className={cn(
                                  "px-2 py-0.5 rounded-md text-[10px] font-bold border",
                                  imp.diagnosticity_category === 'High' ? "bg-amber-50 text-amber-900 border-amber-300" : "bg-stone-50 text-stone-600 border-stone-200"
                                )}>
                                  {imp.diagnosticity_category} ({imp.diagnosticity_score})
                                </span>
                              </td>
                              <td className="p-3 font-mono">
                                <span className={cn(
                                  "px-2.5 py-1 rounded-full text-[10px] font-bold border",
                                  isCritical ? "bg-rose-100 text-rose-800 border-rose-300" :
                                  imp.impact_level === 'HIGH_IMPACT' ? "bg-amber-100 text-amber-800 border-amber-300" :
                                  "bg-stone-100 text-stone-700 border-stone-200"
                                )}>
                                  {imp.impact_level}
                                </span>
                              </td>
                              <td className="p-3 text-xs">
                                <div className="font-medium text-[#191410] truncate max-w-xs">
                                  {imp.top_hypothesis_without}
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Simulated Results when Exhibits Excluded */}
                {excludedExhibitIds.length > 0 && (
                  <div className="p-4 rounded-2xl bg-stone-900 text-white space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Scale className="w-4 h-4 text-[#d93829]" />
                        <span className="font-serif font-bold text-sm">
                          Simulated Matrix Output ({excludedExhibitIds.length} Exhibits Excluded)
                        </span>
                      </div>
                      {simulating && <Loader2 className="w-4 h-4 animate-spin text-[#d93829]" />}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {simulatedScores && Object.entries(simulatedScores).map(([hId, sData]: any) => {
                        const hInfo = hypotheses.find(h => String(h.id) === String(hId));
                        return (
                          <div key={`sim-${hId}`} className="p-3 rounded-xl bg-white/10 border border-white/10 text-xs">
                            <div className="font-serif font-bold text-white truncate">
                              {hInfo?.title || `Hypothesis #${hId}`}
                            </div>
                            <div className="flex items-center justify-between mt-2 font-mono">
                              <span className="text-stone-300">Simulated Likelihood:</span>
                              <span className="text-emerald-400 font-bold text-sm">{sData.support_score}%</span>
                            </div>
                            <div className="flex items-center justify-between text-[11px] font-mono text-stone-400">
                              <span>Inconsistency:</span>
                              <span>{sData.disconfirmation_penalty}</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="pt-3 border-t border-[#eae4d9] flex justify-end">
              <button
                onClick={() => setIsSensitivityOpen(false)}
                className="px-5 py-2 rounded-full bg-[#191410] text-white text-xs font-bold hover:bg-[#2e261f] cursor-pointer"
              >
                Close Analysis
              </button>
            </div>
          </div>
        </div>
      )}

      {/* RELIABILITY CONFIGURATION MODAL */}
      {isReliabilityModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-200">
          <div className="bg-white rounded-3xl max-w-3xl w-full p-6 space-y-5 border border-[#eae4d9] shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9]">
              <div>
                <div className="text-[11px] font-mono font-bold uppercase tracking-wider text-[#d93829] flex items-center gap-1.5">
                  <Settings className="w-3.5 h-3.5" />
                  <span>Forensic Science & Statutory Evidence Configuration</span>
                </div>
                <h2 className="text-xl font-serif font-bold text-[#191410] mt-0.5">
                  Base Reliability Settings & Legal Rationales
                </h2>
              </div>
              <button 
                onClick={() => setIsReliabilityModalOpen(false)}
                className="p-2 rounded-full hover:bg-stone-100 text-stone-500 hover:text-stone-800 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-1">
              <p className="text-xs text-[#6e665d]">
                Base reliabilities represent statutory and scientific baselines before exhibit integrity modifiers (hash verified, chain of custody, Section 65B electronic certificate, source independence, and quality rating) are computed.
              </p>

              <div className="divide-y divide-[#eae4d9] border border-[#eae4d9] rounded-2xl overflow-hidden">
                {reliabilityConfigs.map((cfg) => {
                  const isEditing = editingConfig?.id === cfg.id;

                  return (
                    <div key={`cfg-${cfg.id}`} className="p-4 bg-white hover:bg-[#faf7f2]/50 transition-colors text-xs space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {getEvidenceTypeBadge(cfg.evidence_type)}
                          <span className="font-serif font-bold text-[#191410] text-sm">{cfg.evidence_type}</span>
                        </div>
                        <div className="flex items-center gap-3 font-mono">
                          <span className="text-[#6e665d]">Base Value:</span>
                          {isEditing ? (
                            <input 
                              type="number"
                              step="0.05"
                              min="0.10"
                              max="1.0"
                              value={editingConfig.base_reliability}
                              onChange={(e) => setEditingConfig({ ...editingConfig, base_reliability: parseFloat(e.target.value) || 0.5 })}
                              className="w-16 px-2 py-0.5 rounded-md border border-[#d8d0c5] bg-white font-mono text-xs font-bold"
                            />
                          ) : (
                            <span className="font-bold text-sm text-[#191410] bg-[#faf7f2] px-2 py-0.5 rounded-md border border-[#eae4d9]">
                              {cfg.base_reliability}
                            </span>
                          )}

                          {isEditing ? (
                            <div className="flex items-center gap-1">
                              <button
                                onClick={handleSaveReliabilityConfig}
                                disabled={savingConfig}
                                className="px-2.5 py-1 bg-emerald-600 text-white rounded-md font-bold text-[10px] hover:bg-emerald-700 cursor-pointer"
                              >
                                {savingConfig ? 'Saving...' : 'Save'}
                              </button>
                              <button
                                onClick={() => setEditingConfig(null)}
                                className="px-2 py-1 bg-stone-200 text-stone-700 rounded-md font-bold text-[10px] hover:bg-stone-300 cursor-pointer"
                              >
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => setEditingConfig({ ...cfg })}
                              className="text-[11px] text-[#d93829] font-bold hover:underline cursor-pointer"
                            >
                              Edit
                            </button>
                          )}
                        </div>
                      </div>

                      {isEditing ? (
                        <textarea
                          rows={2}
                          value={editingConfig.rationale}
                          onChange={(e) => setEditingConfig({ ...editingConfig, rationale: e.target.value })}
                          className="w-full p-2 rounded-xl border border-[#d8d0c5] text-xs font-serif leading-relaxed"
                        />
                      ) : (
                        <p className="text-xs text-[#6e665d] leading-relaxed">
                          {cfg.rationale}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="pt-3 border-t border-[#eae4d9] flex justify-end">
              <button
                onClick={() => setIsReliabilityModalOpen(false)}
                className="px-5 py-2 rounded-full bg-[#191410] text-white text-xs font-bold hover:bg-[#2e261f] cursor-pointer"
              >
                Close Settings
              </button>
            </div>
          </div>
        </div>
      )}

      {/* CREATE HYPOTHESIS MODAL */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-200">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 space-y-4 border border-[#eae4d9] shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9]">
              <div className="flex items-center gap-2">
                <Lightbulb className="w-5 h-5 text-[#d93829]" />
                <h3 className="text-lg font-serif font-bold text-[#191410]">New Investigative Hypothesis</h3>
              </div>
              <button 
                onClick={() => setIsModalOpen(false)}
                className="p-1.5 rounded-full hover:bg-stone-100 text-stone-500 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-xs font-mono font-bold text-[#191410] mb-1">
                  Hypothesis Title *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. H4: Opportunistic Robbery by Unaffiliated Third Party"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl border border-[#d8d0c5] focus:outline-hidden focus:border-[#d93829] text-xs font-medium"
                />
              </div>

              <div>
                <label className="block text-xs font-mono font-bold text-[#191410] mb-1">
                  Theory Description & Mechanics
                </label>
                <textarea
                  rows={3}
                  placeholder="Detail the investigative proposition, timeline mechanics, and how physical traces fit..."
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl border border-[#d8d0c5] focus:outline-hidden focus:border-[#d93829] text-xs font-medium"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-[#eae4d9]">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-full border border-[#d8d0c5] text-xs font-bold text-[#6e665d] hover:bg-stone-50 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating || !newTitle.trim()}
                  className="px-5 py-2 rounded-full bg-[#d93829] hover:bg-[#bf2b1d] text-white text-xs font-bold transition-all shadow-xs disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
                >
                  {creating && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>Create Hypothesis</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Feature 3: Interactive Source-Span Provenance Modal */}
      {citationEvidenceId && caseId && (
        <SourceSpanViewerModal
          isOpen={citationModalOpen}
          onClose={() => setCitationModalOpen(false)}
          caseId={caseId}
          evidenceId={citationEvidenceId}
          evidenceTitle={citationEvidenceTitle}
          targetQuote={citationTargetQuote}
          onTextUpdated={() => {
            loadData();
          }}
        />
      )}
    </div>
  );
}