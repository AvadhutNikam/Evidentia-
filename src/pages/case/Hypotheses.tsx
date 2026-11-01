import { useParams, Link } from 'react-router-dom';
import { useEffect, useState, useMemo, useRef } from 'react';
import { hypothesisService, evidenceService, priorRecordService, scoringService, decisionQualityService } from '../../services';
import { 
  Hypothesis, 
  EvidenceAssessment, 
  Evidence, 
  SensitivityAnalysisResult, 
  SensitivityImpact, 
  ReliabilityConfig, 
  ExhibitBreakdownRow, 
  HypothesisRobustness,
  LikelihoodRatioReference,
  DependencyGroupsResponse,
  ExculpatoryConfigOut,
  MonteCarloScoringResponse,
  InvestigativeGap,
  DevilsAdvocateResponse,
  DecisionSignoff,
  PlainLanguageExplanation
} from '../../types';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { 
  Lightbulb, CheckCircle2, XCircle, ChevronDown, ChevronRight, 
  Plus, Sparkles, Loader2, ShieldCheck, AlertTriangle, 
  HelpCircle, Scale, FileText, Database, X, Cpu, ExternalLink,
  GitBranch, ArrowUpRight, Video, Mic, Compass, Sliders, RotateCcw,
  SlidersHorizontal, Check, AlertOctagon, Info, Table as TableIcon, 
  BarChart2, Settings, Quote, Eye, ShieldAlert, Award, Layers, UserCheck,
  BookOpen, Edit3, ArrowRight, Zap, Lock, Shield, UserX
} from 'lucide-react';
import { cn } from '../../utils';
import { useAuth } from '../../context/AuthContext';
import { SourceSpanViewerModal } from '../../components/common/SourceSpanViewerModal';
import { SuspectProfileCard } from '../../components/case/SuspectProfileCard';
import { CriminalHistoryModal } from '../../components/case/CriminalHistoryModal';
import { LikelihoodRatioReferenceModal } from '../../components/case/LikelihoodRatioReferenceModal';
import { DependencyGroupsModal } from '../../components/case/DependencyGroupsModal';
import { GapsAndNextStepsModal } from '../../components/case/GapsAndNextStepsModal';
import { DevilsAdvocateModal } from '../../components/case/DevilsAdvocateModal';
import { DecisionSignoffModal } from '../../components/case/DecisionSignoffModal';
import { useStreamingAnalysis } from '../../context/StreamingAnalysisContext';

export function Hypotheses() {
  const { caseId } = useParams<{ caseId: string }>();
  const { user, role } = useAuth();
  const { isItemHighlighted } = useStreamingAnalysis();
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
  const [caseEvidence, setCaseEvidence] = useState<Evidence[]>([]);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState<string | null>(null);
  const [expandedHypothesis, setExpandedHypothesis] = useState<string | null>(null);
  
  // View mode: 'ranked' (ranked cards with error bars) or 'matrix' (classic ACH heatmap grid)
  const [viewMode, setViewMode] = useState<'ranked' | 'matrix'>('ranked');

  // Change 1: Three-Layer Ranking Toggle: 'combined' (Bayesian posterior) | 'evidence' (relative support only) | 'background' (plausibility prior)
  const [rankingCriterion, setRankingCriterion] = useState<'combined' | 'evidence' | 'background'>('combined');

  // Change 4: Methodology Toggle: 'bayesian_lr' (Probabilistic Bayesian Updating) | 'classic_ach' (Heuer Matrix) | 'comparison' (Side-by-side)
  const [scoringMethod, setScoringMethod] = useState<'bayesian_lr' | 'classic_ach' | 'comparison'>('bayesian_lr');

  // Change 4: Forensic Likelihood Ratio Reference Table State
  const [isReferenceTableOpen, setIsReferenceTableOpen] = useState(false);
  const [referenceTableEntries, setReferenceTableEntries] = useState<LikelihoodRatioReference[]>([]);
  const [loadingRefTable, setLoadingRefTable] = useState(false);

  // Change 5: Evidentiary Dependence & Exculpatory Rules state
  const [isDependencyModalOpen, setIsDependencyModalOpen] = useState(false);
  const [dependencyGroupsData, setDependencyGroupsData] = useState<DependencyGroupsResponse | null>(null);
  const [exculpatoryConfig, setExculpatoryConfig] = useState<ExculpatoryConfigOut | null>(null);
  const [loadingDependencyData, setLoadingDependencyData] = useState(false);

  // Creation modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newStatus, setNewStatus] = useState('Active');
  const [creating, setCreating] = useState(false);

  // Breakdown Drawer / Modal state (Change 9: 3-layer breakdown)
  const [breakdownModalHyp, setBreakdownModalHyp] = useState<Hypothesis | null>(null);
  const [breakdownRows, setBreakdownRows] = useState<ExhibitBreakdownRow[]>([]);
  const [loadingBreakdown, setLoadingBreakdown] = useState(false);
  const [breakdownTab, setBreakdownTab] = useState<'evidence' | 'background' | 'history'>('evidence');
  const [breakdownPriorRecords, setBreakdownPriorRecords] = useState<any[]>([]);
  const [breakdownPriorRestricted, setBreakdownPriorRestricted] = useState(false);
  const [breakdownRestrictedMsg, setBreakdownRestrictedMsg] = useState('');

  // Change 9: With / Without History Toggle
  const [includeHistory, setIncludeHistory] = useState<boolean>(true);

  // "How This Score Was Calculated" Mathematical Trace Drawer state
  const [openCalcTraces, setOpenCalcTraces] = useState<Record<string, boolean>>({});
  const toggleCalcTrace = (hypId: string) => {
    setOpenCalcTraces(prev => ({ ...prev, [hypId]: !prev[hypId] }));
  };

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

  // Change 2: Suspect Profile Plausibility Modal state
  const [selectedProfileHyp, setSelectedProfileHyp] = useState<Hypothesis | null>(null);

  // Change 3: Criminal History & Safeguards Modal state
  const [isCriminalHistoryOpen, setIsCriminalHistoryOpen] = useState(false);
  const [criminalHistoryEnabled, setCriminalHistoryEnabled] = useState(true);
  const [criminalHistoryCap, setCriminalHistoryCap] = useState(0.10);
  const [selectedCriminalHistoryHypId, setSelectedCriminalHistoryHypId] = useState<string | number | null>(null);

  // Change 6 & 7: Monte Carlo Uncertainty Ranges & Investigative Gaps
  const [monteCarloData, setMonteCarloData] = useState<MonteCarloScoringResponse | null>(null);
  const [investigativeGaps, setInvestigativeGaps] = useState<InvestigativeGap[]>([]);
  const [isGapsModalOpen, setIsGapsModalOpen] = useState(false);

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

  // Decision Quality: Devil's Advocate, Sign-Offs & Bias Alerts
  const [isDevilsAdvocateOpen, setIsDevilsAdvocateOpen] = useState(false);
  const [devilsAdvocateTargetId, setDevilsAdvocateTargetId] = useState<number | undefined>(undefined);
  const [isSignoffModalOpen, setIsSignoffModalOpen] = useState(false);
  const [biasAlerts, setBiasAlerts] = useState<any[]>([]);
  const [expandedPlainLanguage, setExpandedPlainLanguage] = useState<Record<string, boolean>>({});

  const togglePlainLanguage = (hypId: string) => {
    setExpandedPlainLanguage(prev => ({ ...prev, [hypId]: !prev[hypId] }));
  };

  const loadData = async (silent: boolean = false) => {
    if (!caseId) return;
    try {
      if (!silent) {
        setLoading(true);
      }
      const [hyps, evs, sens, priorRes, depRes, exRes, mcRes, gapsRes] = await Promise.all([
        hypothesisService.getHypothesesForCase(caseId),
        evidenceService.getEvidenceForCase(caseId),
        hypothesisService.getSensitivityAndRobustness(caseId).catch(() => null),
        priorRecordService.getPriorRecords(caseId).catch(() => null),
        scoringService.getDependencyGroups(caseId).catch(() => null),
        scoringService.getExculpatoryConfig(caseId).catch(() => null),
        scoringService.getMonteCarloRanges(caseId).catch(() => null),
        scoringService.getInvestigativeGaps(caseId).catch(() => [])
      ]);
      setHypotheses(hyps);
      setCaseEvidence(evs);

      decisionQualityService.getBiasAlerts(caseId).then(res => {
        if (res && res.bias_alerts) setBiasAlerts(res.bias_alerts);
      }).catch(() => {});
      if (sens && sens.robustness_ranges) {
        setRobustnessRanges(sens.robustness_ranges);
      }
      if (priorRes) {
        const histOn = priorRes.include_criminal_history ?? true;
        setCriminalHistoryEnabled(histOn);
        setIncludeHistory(histOn);
        setCriminalHistoryCap(priorRes.criminal_history_max_cap ?? 0.10);
      }
      if (depRes) {
        setDependencyGroupsData(depRes);
      }
      if (exRes) {
        setExculpatoryConfig(exRes);
      }
      if (mcRes) {
        setMonteCarloData(mcRes);
      }
      if (Array.isArray(gapsRes)) {
        setInvestigativeGaps(gapsRes);
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
    loadData(false);
  }, [caseId]);

  // Live multi-user score and assessment synchronization (debounced & silent in background)
  const syncTimeoutRef = useRef<any>(null);

  useEffect(() => {
    const handleLiveSync = () => {
      if (syncTimeoutRef.current) clearTimeout(syncTimeoutRef.current);
      syncTimeoutRef.current = setTimeout(() => {
        loadData(true);
      }, 1500);
    };
    window.addEventListener('evidentia:scores-updated', handleLiveSync);
    window.addEventListener('evidentia:item-changed', handleLiveSync);
    return () => {
      if (syncTimeoutRef.current) clearTimeout(syncTimeoutRef.current);
      window.removeEventListener('evidentia:scores-updated', handleLiveSync);
      window.removeEventListener('evidentia:item-changed', handleLiveSync);
    };
  }, [caseId]);

  // Change 9: Toggle Criminal History Setting
  const handleToggleHistory = async (enabled: boolean) => {
    setIncludeHistory(enabled);
    setCriminalHistoryEnabled(enabled);
    if (!caseId) return;
    try {
      await priorRecordService.toggleCriminalHistory(caseId, enabled);
      setNotificationMsg({
        text: enabled 
          ? 'Criminal History enabled: Modus Operandi matching included with +10% max statutory cap.'
          : 'Criminal History partitioned: Section 54 IEA / Section 52 BSA character safeguard active (history excluded).',
        type: enabled ? 'info' : 'warning'
      });
      setTimeout(() => setNotificationMsg(null), 4000);
      await loadData();
    } catch (err) {
      console.error('Failed to toggle criminal history:', err);
    }
  };

  // Change 1, Change 4 & Change 9: Dynamic sorting based on rankingCriterion, scoringMethod, and includeHistory
  const sortedHypotheses = useMemo(() => {
    return [...hypotheses].sort((a, b) => {
      if (rankingCriterion === 'evidence') {
        const scoreA = scoringMethod === 'classic_ach'
          ? (a.classic_evidence_score ?? a.evidence_score ?? 50)
          : (a.bayesian_evidence_score ?? a.evidence_score ?? 50);
        const scoreB = scoringMethod === 'classic_ach'
          ? (b.classic_evidence_score ?? b.evidence_score ?? 50)
          : (b.bayesian_evidence_score ?? b.evidence_score ?? 50);
        return scoreB - scoreA;
      }
      if (rankingCriterion === 'background') {
        const baseA = a.background_score ?? a.backgroundScore ?? 50;
        const baseB = b.background_score ?? b.backgroundScore ?? 50;
        const scoreA = includeHistory
          ? baseA
          : (a.background_score_without_history ?? Math.max(0, baseA - (a.history_contribution ?? 0) * 100));
        const scoreB = includeHistory
          ? baseB
          : (b.background_score_without_history ?? Math.max(0, baseB - (b.history_contribution ?? 0) * 100));
        return scoreB - scoreA;
      }
      // 'combined' priority (default)
      const baseA = scoringMethod === 'classic_ach'
        ? (a.classic_ach_score ?? a.combined_score ?? a.support_score ?? 50)
        : (a.bayesian_lr_score ?? a.combined_score ?? a.support_score ?? 50);
      const baseB = scoringMethod === 'classic_ach'
        ? (b.classic_ach_score ?? b.combined_score ?? b.support_score ?? 50)
        : (b.bayesian_lr_score ?? b.combined_score ?? b.support_score ?? 50);
      const scoreA = includeHistory
        ? baseA
        : (a.combined_score_without_history ?? Math.max(0, baseA - (a.history_contribution ?? 0) * 100));
      const scoreB = includeHistory
        ? baseB
        : (b.combined_score_without_history ?? Math.max(0, baseB - (b.history_contribution ?? 0) * 100));
      return scoreB - scoreA;
    });
  }, [hypotheses, rankingCriterion, scoringMethod, includeHistory]);

  // Change 4: Forensic Reference Table Handlers
  const handleOpenReferenceTable = async () => {
    if (!caseId) return;
    try {
      setLoadingRefTable(true);
      setIsReferenceTableOpen(true);
      const table = await scoringService.getLikelihoodRatioReferenceTable(caseId);
      setReferenceTableEntries(table);
    } catch (err) {
      console.error('Failed to load likelihood ratio reference table:', err);
    } finally {
      setLoadingRefTable(false);
    }
  };

  const handleSaveReferenceEntry = async (entry: LikelihoodRatioReference, updates: { typical_lr: number; min_lr: number; max_lr: number }) => {
    if (!caseId) return;
    try {
      await scoringService.updateLikelihoodRatioEntry(caseId, entry.category_key, updates);
      const table = await scoringService.getLikelihoodRatioReferenceTable(caseId);
      setReferenceTableEntries(table);
      await loadData();
      setNotificationMsg({
        text: `Updated Likelihood Ratio for ${entry.finding_name}. Scores recalculated.`,
        type: 'success'
      });
      setTimeout(() => setNotificationMsg(null), 4000);
    } catch (err) {
      console.error('Failed to update reference entry:', err);
    }
  };

  const handleResetReferenceTable = async () => {
    if (!caseId) return;
    if (!confirm('Reset all 33 forensic categories to scientific baseline literature defaults?')) return;
    try {
      await scoringService.resetLikelihoodRatioTable(caseId);
      const table = await scoringService.getLikelihoodRatioReferenceTable(caseId);
      setReferenceTableEntries(table);
      await loadData();
      setNotificationMsg({
        text: 'Likelihood Ratio Reference Table reset to peer-reviewed forensic standards.',
        type: 'success'
      });
      setTimeout(() => setNotificationMsg(null), 4000);
    } catch (err) {
      console.error('Failed to reset reference table:', err);
    }
  };

  // Change 5: Evidentiary Dependence Handlers
  const handleOpenDependencyModal = async () => {
    if (!caseId) return;
    try {
      setLoadingDependencyData(true);
      setIsDependencyModalOpen(true);
      const [depRes, exRes] = await Promise.all([
        scoringService.getDependencyGroups(caseId),
        scoringService.getExculpatoryConfig(caseId)
      ]);
      if (depRes) setDependencyGroupsData(depRes);
      if (exRes) setExculpatoryConfig(exRes);
    } catch (err) {
      console.error('Failed to load dependency data:', err);
    } finally {
      setLoadingDependencyData(false);
    }
  };

  const handleUpdateExhibitGroup = async (evidenceId: string | number, newGroup: string | null) => {
    if (!caseId) return;
    try {
      await scoringService.updateEvidenceDependencyGroup(caseId, evidenceId, newGroup);
      await loadData();
      const depRes = await scoringService.getDependencyGroups(caseId);
      if (depRes) setDependencyGroupsData(depRes);
      if (breakdownModalHyp) handleOpenBreakdown(breakdownModalHyp);
      setNotificationMsg({
        text: newGroup 
          ? `Assigned exhibit to dependency group "${newGroup}". Geometric damping applied.`
          : `Cleared exhibit dependency group. Exhibit restored to independent weight.`,
        type: 'success'
      });
      setTimeout(() => setNotificationMsg(null), 4000);
    } catch (err) {
      console.error('Failed to update dependency group:', err);
    }
  };

  const handleAutoGroupDependencies = async () => {
    if (!caseId) return;
    try {
      const res = await scoringService.autoGroupDependencies(caseId);
      await loadData();
      const depRes = await scoringService.getDependencyGroups(caseId);
      if (depRes) setDependencyGroupsData(depRes);
      if (breakdownModalHyp) handleOpenBreakdown(breakdownModalHyp);
      const count = res?.detected_groups ? Object.keys(res.detected_groups).length : 0;
      setNotificationMsg({
        text: `Auto-detected ${count} shared-source exhibit groups. Geometric damping applied to correlated evidence.`,
        type: 'success'
      });
      setTimeout(() => setNotificationMsg(null), 4000);
    } catch (err) {
      console.error('Failed to auto-group dependencies:', err);
    }
  };

  const handleEvaluate = async (hypothesisId: string) => {
    setEvaluating(hypothesisId);
    try {
      const updated = await hypothesisService.evaluateHypothesis(hypothesisId);
      if (updated) {
        await loadData();
        setNotificationMsg({ text: 'AI evaluated exhibits with verified quotes. Suspect case strengths updated.', type: 'success' });
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
      setNotificationMsg({ text: 'All suspect theories evaluated with quote verification and alibi conflict analysis.', type: 'success' });
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
          text: 'Forensic evaluation complete: suspect theories ranked by alibi verification and case strength.', 
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
    setBreakdownTab('evidence');
    setLoadingBreakdown(true);
    try {
      const [res, priorRes] = await Promise.all([
        hypothesisService.getHypothesisBreakdown(caseId, h.id),
        priorRecordService.getPriorRecords(caseId, h.id).catch(() => null)
      ]);
      if (res && res.exhibits) {
        setBreakdownRows(res.exhibits);
      } else {
        setBreakdownRows([]);
      }
      if (priorRes) {
        setBreakdownPriorRestricted(Boolean(priorRes.is_role_restricted));
        setBreakdownRestrictedMsg(priorRes.restricted_message || '');
        setBreakdownPriorRecords(priorRes.records || []);
      } else {
        setBreakdownPriorRecords([]);
        setBreakdownPriorRestricted(false);
        setBreakdownRestrictedMsg('');
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
      {/* Decision Quality: Cognitive Bias & Fragility Alerts Banner */}
      {biasAlerts && biasAlerts.length > 0 && (
        <div className="rounded-2xl bg-amber-950 text-amber-100 border border-amber-600/70 p-4 shadow-lg space-y-3 animate-in fade-in duration-200">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-amber-800/80 pb-2.5">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 bg-amber-500/20 rounded-xl border border-amber-500/30 text-amber-400">
                <AlertOctagon className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-serif font-bold text-sm text-white">
                    Cognitive Bias & Fragility Warnings Detected ({biasAlerts.length})
                  </h3>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                    Decision Quality Active
                  </span>
                </div>
                <p className="text-[11px] text-amber-200/80 mt-0.5">
                  Automated heuristics detected evidentiary vulnerabilities that could compromise prosecution viability or indicate cognitive bias.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => {
                  setDevilsAdvocateTargetId(undefined);
                  setIsDevilsAdvocateOpen(true);
                }}
                className="px-3 py-1.5 rounded-full bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition-all shadow-xs flex items-center gap-1.5 cursor-pointer"
              >
                <Scale className="w-3.5 h-3.5" />
                <span>Run Devil's Advocate</span>
              </button>
              <button
                onClick={() => setIsGapsModalOpen(true)}
                className="px-3 py-1.5 rounded-full bg-amber-800/60 hover:bg-amber-800 text-amber-200 text-xs font-bold transition-all border border-amber-700/60 flex items-center gap-1.5 cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                <span>View Gaps</span>
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
            {biasAlerts.map((alert: any) => {
              const isHigh = alert.severity === 'high';
              const isSingleExhibit = alert.alert_type === 'bias_single_exhibit_dependency';
              const isUntested = alert.alert_type === 'bias_untested_alternative';
              const isMonoculture = alert.alert_type === 'bias_source_type_dominance';

              return (
                <div 
                  key={alert.id || alert.alert_type}
                  className={cn(
                    "p-3 rounded-xl border text-xs space-y-1.5",
                    isHigh ? "bg-rose-950/40 border-rose-600/50 text-rose-100" : "bg-amber-900/30 border-amber-700/50 text-amber-100"
                  )}
                >
                  <div className="flex items-center justify-between gap-1.5">
                    <span className={cn(
                      "px-2 py-0.5 rounded-full text-[9px] font-mono font-bold uppercase tracking-wider border",
                      isSingleExhibit && "bg-rose-900/60 text-rose-200 border-rose-500/40",
                      isUntested && "bg-amber-900/60 text-amber-200 border-amber-500/40",
                      isMonoculture && "bg-purple-900/60 text-purple-200 border-purple-500/40"
                    )}>
                      {isSingleExhibit ? 'Fragility' : isUntested ? 'Tunnel Vision' : 'Source Monoculture'}
                    </span>
                    <span className="text-[10px] font-mono text-stone-400">
                      {isHigh ? 'Severity: High' : 'Severity: Medium'}
                    </span>
                  </div>
                  <div className="font-semibold text-white text-[12px] leading-tight">
                    {alert.title}
                  </div>
                  <p className="text-[11px] text-stone-300 leading-snug line-clamp-3">
                    {alert.message}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Change 9: Persistent Statutory & Doctrine Notice Banner */}
      <div className="rounded-2xl bg-amber-50/90 border border-amber-200/90 p-3.5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-xs shadow-xs">
        <div className="flex items-center gap-2.5">
          <ShieldAlert className="w-4 h-4 text-amber-700 shrink-0" />
          <div>
            <span className="font-serif font-bold text-amber-950 mr-1.5">
              Decision support, not a verdict.
            </span>
            <span className="text-amber-900/90">
              Evidentia ACH generates structured investigative leads, not legal proof of guilt. All weights and scores remain subject to Section 54 IEA character safeguards.
            </span>
          </div>
        </div>
        <Link
          to={`/cases/${caseId}/responsible-use`}
          className="text-amber-900 hover:text-amber-950 font-mono font-bold flex items-center gap-1 shrink-0 underline hover:no-underline text-[11px]"
        >
          <span>Limits & Responsible Use</span>
          <ArrowRight className="w-3 h-3" />
        </Link>
      </div>

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-[#eae4d9]">
        <div>
          <div className="text-[11px] font-mono tracking-widest text-[#d93829] uppercase font-bold mb-1 flex items-center gap-1.5">
            <Scale className="w-3.5 h-3.5 text-[#d93829]" />
            <span>Forensic Proof Evaluation • Contradiction-First • High-Reliability Evidence Weighted</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-serif font-bold text-[#191410]">
            Suspect Theories & Case Strength Analysis
          </h1>
          <p className="text-xs text-[#6e665d] mt-1 max-w-3xl">
            Rigorous forensic methodology: suspect theories are evaluated primarily by uncovering alibi conflicts and contradictions, with evidence weighted by credibility and test decisiveness. Combined case strength strictly totals 100%.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Methodology Toggle */}
          <div className="flex items-center bg-[#f0ebe1] p-1 rounded-full border border-[#d8d0c5]">
            <span className="text-[10px] font-mono font-bold text-[#8c8276] px-2 uppercase tracking-wider flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-emerald-700" />
              <span>Analysis Model:</span>
            </span>
            <button
              onClick={() => setScoringMethod('bayesian_lr')}
              className={cn(
                "px-2.5 py-1 rounded-full text-xs font-bold transition-all cursor-pointer flex items-center gap-1",
                scoringMethod === 'bayesian_lr' ? "bg-white text-[#191410] shadow-xs" : "text-[#6e665d] hover:text-[#191410]"
              )}
              title="Probabilistic Weighting: Exact mathematical product of forensic test decisiveness normalized to 100%"
            >
              <CheckCircle2 className="w-3 h-3 text-emerald-700" />
              <span>Probabilistic Weighting</span>
            </button>
            <button
              onClick={() => setScoringMethod('classic_ach')}
              className={cn(
                "px-2.5 py-1 rounded-full text-xs font-bold transition-all cursor-pointer flex items-center gap-1",
                scoringMethod === 'classic_ach' ? "bg-white text-[#191410] shadow-xs" : "text-[#6e665d] hover:text-[#191410]"
              )}
              title="Elimination Model: Eliminates theories based on contradictions and inconsistencies"
            >
              <TableIcon className="w-3 h-3 text-[#d93829]" />
              <span>Elimination Model</span>
            </button>
            <button
              onClick={() => setScoringMethod('comparison')}
              className={cn(
                "px-2.5 py-1 rounded-full text-xs font-bold transition-all cursor-pointer flex items-center gap-1",
                scoringMethod === 'comparison' ? "bg-white text-[#191410] shadow-xs" : "text-[#6e665d] hover:text-[#191410]"
              )}
              title="Side-by-side comparison between Probabilistic Weighting and Elimination Model"
            >
              <SlidersHorizontal className="w-3 h-3 text-purple-700" />
              <span>Model Comparison</span>
            </button>
          </div>

          {/* Ranking criteria toggle */}
          <div className="flex items-center bg-[#f0ebe1] p-1 rounded-full border border-[#d8d0c5]">
            <span className="text-[10px] font-mono font-bold text-[#8c8276] px-2 uppercase tracking-wider flex items-center gap-1">
              <Layers className="w-3 h-3 text-[#d93829]" />
              <span>Rank By:</span>
            </span>
            <button
              onClick={() => setRankingCriterion('combined')}
              className={cn(
                "px-2.5 py-1 rounded-full text-xs font-bold transition-all cursor-pointer",
                rankingCriterion === 'combined' ? "bg-white text-[#191410] shadow-xs" : "text-[#6e665d] hover:text-[#191410]"
              )}
              title="Overall Case Priority: Merges verified forensic exhibits with suspect opportunity and motive"
            >
              Overall Case Priority
            </button>
            <button
              onClick={() => setRankingCriterion('evidence')}
              className={cn(
                "px-2.5 py-1 rounded-full text-xs font-bold transition-all cursor-pointer",
                rankingCriterion === 'evidence' ? "bg-white text-[#191410] shadow-xs" : "text-[#6e665d] hover:text-[#191410]"
              )}
              title="Exhibit Proof Only: Pure forensic exhibit strength without background priors"
            >
              Exhibit Proof Only
            </button>
            <button
              onClick={() => setRankingCriterion('background')}
              className={cn(
                "px-2.5 py-1 rounded-full text-xs font-bold transition-all cursor-pointer",
                rankingCriterion === 'background' ? "bg-white text-[#191410] shadow-xs" : "text-[#6e665d] hover:text-[#191410]"
              )}
              title="Means, Motive, Opportunity: Suspect access and background prior to exhibits"
            >
              Means, Motive, Opportunity
            </button>
          </div>

          {/* With / Without History Safeguard Toggle */}
          <div className="flex items-center bg-[#f0ebe1] p-1 rounded-full border border-[#d8d0c5]">
            <span className="text-[10px] font-mono font-bold text-[#8c8276] px-2 uppercase tracking-wider flex items-center gap-1">
              <Scale className="w-3 h-3 text-purple-700" />
              <span>Prior Record:</span>
            </span>
            <button
              onClick={() => handleToggleHistory(true)}
              className={cn(
                "px-2.5 py-1 rounded-full text-xs font-bold transition-all cursor-pointer flex items-center gap-1",
                includeHistory ? "bg-white text-[#191410] shadow-xs" : "text-[#6e665d] hover:text-[#191410]"
              )}
              title="With Prior MO: Includes MO matching & prior conviction factors (capped at +10.0%)"
            >
              <Check className={cn("w-3 h-3 text-emerald-700", !includeHistory && "opacity-0")} />
              <span>With Prior MO</span>
            </button>
            <button
              onClick={() => handleToggleHistory(false)}
              className={cn(
                "px-2.5 py-1 rounded-full text-xs font-bold transition-all cursor-pointer flex items-center gap-1",
                !includeHistory ? "bg-white text-[#191410] shadow-xs" : "text-[#6e665d] hover:text-[#191410]"
              )}
              title="Without Prior Record: Section 54 IEA / Section 52 BSA character partition active"
            >
              <Lock className={cn("w-3 h-3 text-rose-700", includeHistory && "opacity-0")} />
              <span>Without Prior Record</span>
            </button>
          </div>

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
              <span>Suspect Cards</span>
            </button>
            <button
              onClick={() => setViewMode('matrix')}
              className={cn(
                "px-3 py-1 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer",
                viewMode === 'matrix' ? "bg-white text-[#191410] shadow-xs" : "text-[#6e665d] hover:text-[#191410]"
              )}
            >
              <TableIcon className="w-3.5 h-3.5" />
              <span>Proof & Alibi Matrix</span>
            </button>
          </div>

          {/* Evidentiary Weight Reference Table Button */}
          <button
            onClick={handleOpenReferenceTable}
            className="flex items-center gap-1.5 px-3 py-2 bg-[#faf7f2] hover:bg-[#eae4d9] text-[#191410] rounded-full text-xs font-bold transition-all border border-[#d8d0c5] cursor-pointer shadow-xs"
            title="Peer-reviewed Forensic Evidentiary Weight Standards & Scientific Error Rates"
          >
            <Scale className="w-3.5 h-3.5 text-blue-700" />
            <span>Evidentiary Weight Guide</span>
            <span className="px-1.5 py-0.5 rounded-full text-[9px] font-mono font-bold bg-blue-50 text-blue-800 border border-blue-300">
              33 Standards
            </span>
          </button>

          {/* Shared Evidence Grouping Button */}
          <button
            onClick={handleOpenDependencyModal}
            className="flex items-center gap-1.5 px-3 py-2 bg-[#faf7f2] hover:bg-[#eae4d9] text-[#191410] rounded-full text-xs font-bold transition-all border border-[#d8d0c5] cursor-pointer shadow-xs"
            title="Mark exhibits that share a single underlying source and prevent double-counting"
          >
            <GitBranch className="w-3.5 h-3.5 text-purple-700" />
            <span>Shared Evidence Grouping</span>
            {caseEvidence.filter(e => Boolean(e.dependency_group)).length > 0 && (
              <span className="px-1.5 py-0.5 rounded-full text-[9px] font-mono font-bold bg-purple-50 text-purple-800 border border-purple-300">
                {caseEvidence.filter(e => Boolean(e.dependency_group)).length} Grouped
              </span>
            )}
          </button>

          <button
            onClick={handleOpenReliabilityConfigs}
            className="flex items-center gap-1.5 px-3 py-2 bg-[#faf7f2] hover:bg-[#eae4d9] text-[#191410] rounded-full text-xs font-bold transition-all border border-[#d8d0c5] cursor-pointer shadow-xs"
            title="Inspect and customize base reliabilities & legal rationales per evidence type"
          >
            <Settings className="w-3.5 h-3.5 text-[#6e665d]" />
            <span>Evidence Reliability Rules</span>
          </button>

          <button
            onClick={handleOpenSensitivity}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-[#faf7f2] hover:bg-[#191410] hover:text-white text-[#191410] rounded-full text-xs font-bold transition-all border border-[#d8d0c5] cursor-pointer shadow-xs"
            title="Evaluate how individual exhibits influence the overall conclusion"
          >
            <Sliders className="w-3.5 h-3.5 text-[#d93829]" />
            <span>Evidence Sensitivity Test</span>
          </button>

          <button
            onClick={() => {
              setSelectedCriminalHistoryHypId(null);
              setIsCriminalHistoryOpen(true);
            }}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-[#faf7f2] hover:bg-[#eae4d9] text-[#191410] rounded-full text-xs font-bold transition-all border border-[#d8d0c5] cursor-pointer shadow-xs"
            title="Inspect Prior Record Safeguards, Modus Operandi Matching, and Dual Ranking"
          >
            <Scale className="w-3.5 h-3.5 text-purple-700" />
            <span>Prior Records & MO</span>
            <span className={cn(
              "px-1.5 py-0.5 rounded-full text-[9px] font-mono font-bold border",
              criminalHistoryEnabled ? "bg-emerald-50 text-emerald-800 border-emerald-300" : "bg-stone-100 text-stone-600 border-stone-200"
            )}>
              {criminalHistoryEnabled ? `ON (+${(criminalHistoryCap * 100).toFixed(0)}% cap)` : 'OFF'}
            </span>
          </button>

          <button
            onClick={() => setIsGapsModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-[#faf7f2] hover:bg-[#eae4d9] text-[#191410] rounded-full text-xs font-bold transition-all border border-[#d8d0c5] cursor-pointer shadow-xs"
            title="Inspect Missing Evidence and Recommended Investigative Steps"
          >
            <Sparkles className="w-3.5 h-3.5 text-[#d93829]" />
            <span>Missing Evidence & Action Items</span>
            {investigativeGaps.length > 0 && (
              <span className="px-1.5 py-0.5 rounded-full text-[9px] font-mono font-bold bg-rose-500 text-white">
                {investigativeGaps.length}
              </span>
            )}
          </button>

          {/* Decision Quality: Trial Defense Stress-Test Button */}
          <button
            onClick={() => {
              setDevilsAdvocateTargetId(undefined);
              setIsDevilsAdvocateOpen(true);
            }}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-rose-50 hover:bg-rose-100 text-rose-900 rounded-full text-xs font-bold transition-all border border-rose-300 cursor-pointer shadow-xs"
            title="Trial Defense Stress-Test: Tests prosecution lead by assembling the strongest counter-case for runner-up"
          >
            <Scale className="w-3.5 h-3.5 text-rose-700" />
            <span>Trial Defense Stress-Test</span>
            <span className="px-1.5 py-0.5 rounded-full text-[9px] font-mono font-bold bg-rose-200 text-rose-900 border border-rose-300">
              Court Test
            </span>
          </button>

          {/* Decision Quality: Two-Analyst Sign-Offs Button */}
          <button
            onClick={() => setIsSignoffModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-cyan-50 hover:bg-cyan-100 text-cyan-900 rounded-full text-xs font-bold transition-all border border-cyan-300 cursor-pointer shadow-xs"
            title="Supervisory Sign-Offs: Maker-Checker Four-Eyes protocol for key classifications & reports"
          >
            <UserCheck className="w-3.5 h-3.5 text-cyan-700" />
            <span>Supervisory Sign-Offs</span>
          </button>
          
          <button
            onClick={handleRunACHAnalysis}
            disabled={evaluating !== null}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-[#191410] hover:bg-[#2e261f] text-white rounded-full text-xs font-bold transition-all disabled:opacity-50 cursor-pointer shadow-xs border border-[#3d332a]"
          >
            {evaluating === 'ACH' ? <Loader2 className="w-3.5 h-3.5 animate-spin text-[#d93829]" /> : <Cpu className="w-3.5 h-3.5 text-[#d93829]" />}
            <span>{evaluating === 'ACH' ? 'Evaluating Case...' : 'Run Case Analysis'}</span>
          </button>

          <button
            onClick={handleEvaluateAll}
            disabled={evaluating !== null}
            className="flex items-center gap-1.5 px-3 py-2 bg-[#fdeee9] hover:bg-[#d93829] text-[#d93829] hover:text-white rounded-full text-xs font-bold transition-all border border-[#f6d0c7] disabled:opacity-50 cursor-pointer shadow-xs"
          >
            {evaluating === 'ALL' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
            <span>{evaluating === 'ALL' ? 'Evaluating...' : 'AI Cross-Examine All'}</span>
          </button>

          <button 
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-[#d93829] hover:bg-[#bf2b1d] text-white rounded-full text-xs font-bold transition-all shadow-xs cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Suspect / Theory</span>
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

      {/* Change 9 Persistent Notice: Decision Support, Not a Verdict */}
      <div className="p-4 rounded-3xl bg-amber-50/90 text-amber-950 border border-amber-300 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-4 animate-in fade-in duration-150">
        <div className="flex items-start md:items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-[#d93829] text-white shrink-0 mt-0.5 md:mt-0 shadow-xs">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-serif font-bold text-sm text-[#191410] tracking-wide uppercase">
                Decision support, not a verdict.
              </span>
              <span className="px-2 py-0.5 rounded-full text-[9px] font-mono font-bold bg-amber-100 text-amber-900 border border-amber-300">
                Statutory Safeguard
              </span>
              <span className="text-[10px] font-mono text-amber-800">
                Sec 54 IEA • Sec 52 BSA • Sec 65B Electronic Certificate
              </span>
            </div>
            <p className="text-xs text-amber-900 mt-0.5 leading-relaxed">
              Analytical scores represent relative explanatory weight among evaluated hypotheses ($\sum = 100\%$) and do not establish guilt, replace trial evidence, or supersede judicial discretion.
            </p>
          </div>
        </div>
        <div className="shrink-0 flex items-center gap-2">
          <Link
            to={`/cases/${caseId}/responsible-use`}
            className="px-3.5 py-1.5 rounded-full text-xs font-mono font-bold text-amber-900 hover:text-[#d93829] bg-white hover:bg-amber-100/50 border border-amber-300 shadow-2xs transition-all flex items-center gap-1.5 whitespace-nowrap"
          >
            <span>Responsible Use Policy</span>
            <ArrowRight className="w-3 h-3 text-amber-700" />
          </Link>
        </div>
      </div>

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

      {/* Change 5: Unknown Hypothesis Dominant Warning Banner */}
      {!loading && sortedHypotheses.length > 0 && (sortedHypotheses[0].is_unknown || sortedHypotheses[0].lead_message || sortedHypotheses[0].title.toLowerCase().includes('unknown')) && (
        <div className="p-4 rounded-2xl bg-amber-500/10 border-2 border-amber-500/40 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs shadow-md animate-in fade-in slide-in-from-top-2">
          <div className="flex items-start gap-3">
            <div className="p-2.5 rounded-2xl bg-amber-100 text-amber-900 shrink-0">
              <ShieldAlert className="w-5 h-5 text-amber-800" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-serif font-bold text-sm text-amber-950">
                  Investigative Conclusion: The evidence does not clearly point to any listed suspect.
                </span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-200 text-amber-900 border border-amber-300">
                  Open-World Lead
                </span>
              </div>
              <p className="text-amber-900 mt-1 leading-relaxed">
                {sortedHypotheses[0].lead_message ||
                  "Forensic exhibits contradict or fail to substantiate the listed suspects. Open-world Bayesian updating indicates that an unknown perpetrator or alternate explanation holds the greatest relative explanatory support."}
              </p>
            </div>
          </div>
          <div className="shrink-0 flex md:flex-col items-end gap-1 font-mono text-right">
            <div className="text-xl font-black text-amber-950 font-serif">
              {(scoringMethod === 'classic_ach' ? sortedHypotheses[0].classic_ach_score : sortedHypotheses[0].bayesian_lr_score ?? sortedHypotheses[0].combined_score ?? 50.0)?.toFixed(1)}%
            </div>
            <div className="text-[10px] text-amber-800 uppercase tracking-wider font-sans font-semibold">
              Unknown Lead Share
            </div>
          </div>
        </div>
      )}

      {/* Change 6: Close Results Warning Banner ("cannot separate") */}
      {!loading && monteCarloData?.cannot_separate && (
        <div className="p-5 rounded-3xl bg-amber-500/10 border-2 border-amber-500/40 shadow-xs animate-in fade-in slide-in-from-top-2">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="p-2.5 rounded-2xl bg-amber-100 text-amber-900 shrink-0">
                <AlertOctagon className="w-5 h-5 text-amber-800" />
              </div>
              <div className="space-y-1.5 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-serif font-bold text-base text-amber-950">
                    Evidence cannot clearly separate these suspects
                  </span>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-200 text-amber-900 border border-amber-300">
                    Substantial Uncertainty Overlap
                  </span>
                </div>
                <p className="text-xs text-amber-900 leading-relaxed">
                  {monteCarloData.close_results_warning || "The top competing suspects have substantially overlapping credible uncertainty ranges under plausible likelihood ratio, reliability, and prior variations."}
                </p>

                {/* Discriminating Evidence Needed List */}
                {monteCarloData.discriminating_evidence_needed && monteCarloData.discriminating_evidence_needed.length > 0 && (
                  <div className="mt-3 p-3.5 rounded-2xl bg-white/90 border border-amber-200 text-xs space-y-2">
                    <div className="font-serif font-bold text-amber-950 flex items-center gap-1.5">
                      <Compass className="w-3.5 h-3.5 text-amber-800" />
                      <span>Evidence Required to Decisively Separate Suspects:</span>
                    </div>
                    <ul className="space-y-1.5 pl-1">
                      {monteCarloData.discriminating_evidence_needed.map((item, dIdx) => (
                        <li key={dIdx} className="flex items-start gap-2 text-amber-900 text-[11px] leading-relaxed">
                          <ArrowRight className="w-3.5 h-3.5 text-amber-700 shrink-0 mt-0.5" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>

            <div className="shrink-0 flex md:flex-col gap-2">
              <button
                onClick={() => setIsGapsModalOpen(true)}
                className="px-4 py-2 bg-[#191410] hover:bg-[#d93829] text-white rounded-full text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer shadow-xs whitespace-nowrap"
              >
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                <span>Simulate Next Best Steps</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Change 6: Fragility Warning Banner (Leave-One-Out) */}
      {!loading && monteCarloData?.is_fragile && (
        <div className="p-4 rounded-3xl bg-rose-50 border-2 border-rose-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4 animate-in fade-in slide-in-from-top-2">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-2xl bg-rose-100 text-rose-800 shrink-0">
              <AlertTriangle className="w-5 h-5 text-rose-700" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-serif font-bold text-sm text-rose-950">
                  Fragility Warning: Ranking Depends Heavily on a Single Exhibit
                </span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-rose-200 text-rose-900 border border-rose-300">
                  Leave-One-Out Sensitivity
                </span>
              </div>
              <p className="text-xs text-rose-900 mt-1 leading-relaxed">
                {monteCarloData.fragility_message || 
                  `Suspect ranking depends critically on Exhibit #${monteCarloData.fragile_exhibit_id} ('${monteCarloData.fragile_exhibit_title}'). If this exhibit is excluded or discredited, the leading ranking flips or drops sharply.`}
              </p>
            </div>
          </div>
          <div className="shrink-0">
            <button
              onClick={() => setIsSensitivityOpen(true)}
              className="px-3.5 py-1.5 rounded-full bg-rose-900 hover:bg-rose-800 text-white text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer shadow-xs whitespace-nowrap"
            >
              <Sliders className="w-3.5 h-3.5 text-rose-300" />
              <span>Inspect Sensitivity</span>
            </button>
          </div>
        </div>
      )}

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
          {sortedHypotheses.map((h, idx) => {
            const evScore = scoringMethod === 'classic_ach'
              ? (h.classic_evidence_score ?? h.evidence_score ?? 50.0)
              : (h.bayesian_evidence_score ?? h.evidence_score ?? 50.0);
            const baseBgScore = h.background_score ?? (h as any).backgroundScore ?? 50.0;
            const histCont = h.history_contribution ?? (h as any).historyContribution ?? 0.0;
            const bgWithoutHist = h.background_score_without_history ?? Math.max(0, baseBgScore - histCont * 100);
            const bgScore = includeHistory ? baseBgScore : bgWithoutHist;

            const baseCombScore = scoringMethod === 'classic_ach'
              ? (h.classic_ach_score ?? h.combined_score ?? h.support_score ?? 50.0)
              : (h.bayesian_lr_score ?? h.combined_score ?? h.support_score ?? 50.0);
            const combWithoutHist = h.combined_score_without_history ?? Math.max(0, baseCombScore - histCont * 100);
            const combScore = includeHistory ? baseCombScore : combWithoutHist;

            const score = rankingCriterion === 'evidence' ? evScore : (rankingCriterion === 'background' ? bgScore : combScore);
            const penalty = h.disconfirmation_penalty ?? (h as any).disconfirmationPenalty ?? 0.0;
            const isPrimary = idx === 0 && score >= 40.0 && penalty < 2.5;
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

            const supportingCount = enriched.filter(a => (a.classification || '').toLowerCase().includes('support')).length;
            const contradictingCount = enriched.filter(a => (a.classification || '').toLowerCase().includes('contradiction')).length;
            const isCalcTraceOpen = Boolean(openCalcTraces[h.id]);
            const isHighlighted = isItemHighlighted('hypothesis', h.id) || isItemHighlighted('hypothesis', idx + 1);

            return (
              <div 
                key={`${h.id}-${idx}`}
                className={cn(
                  "rounded-3xl bg-white border transition-all overflow-hidden shadow-xs",
                  isHighlighted && "ring-2 ring-amber-400 bg-amber-50/40 border-amber-300 shadow-md",
                  !isHighlighted && isPrimary && "border-emerald-300 ring-1 ring-emerald-400/20",
                  !isHighlighted && isDiscarded && "border-[#e0d9cf] opacity-85",
                  !isHighlighted && !isPrimary && !isDiscarded && "border-[#eae4d9]"
                )}
              >
                {/* Header Card */}
                <div className="p-6">
                  <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 mb-3">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <span className="font-mono text-xs font-bold text-white bg-[#191410] px-3 py-1 rounded-full shrink-0">
                        {idx === 0 ? 'Rank #1 • Prime Suspect' : `Rank #${idx + 1} • Theory ${idx + 1}`}
                      </span>
                      <h3 className="text-lg font-serif font-bold text-[#191410]">
                        {h.title}
                      </h3>
                      {isHighlighted && (
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-200 text-amber-950 border border-amber-300 flex items-center gap-1 shrink-0 animate-pulse">
                          <Zap className="w-3 h-3 text-amber-700" />
                          <span>NEW PROBABILITY SHIFT</span>
                        </span>
                      )}
                      {h.is_unknown && (
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-100 text-amber-900 border border-amber-300 flex items-center gap-1 shrink-0">
                          <HelpCircle className="w-3 h-3 text-amber-700" />
                          <span>Unidentified External Suspect</span>
                        </span>
                      )}

                      {/* Inconsistency Penalty Badge */}
                      <span className={cn(
                        "px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border flex items-center gap-1 shrink-0",
                        penalty > 0 ? "bg-rose-50 text-rose-800 border-rose-200" : "bg-emerald-50 text-emerald-800 border-emerald-200"
                      )} title="Alibi conflicts and physical contradictions accumulated from contradictory exhibits">
                        <AlertTriangle className={cn("w-3 h-3", penalty > 0 ? "text-rose-600" : "text-emerald-600")} />
                        <span>Alibi Conflicts: {penalty.toFixed(2)}</span>
                      </span>

                      {/* Exhibit Counts */}
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-[#f5f0e8] text-[#6e665d] border border-[#eae4d9] shrink-0" title="Evaluated evidentiary exhibits">
                        {supportingCount} Supporting • {contradictingCount} Contradicting ({enriched.length} Exhibits)
                      </span>

                      {/* Robustness Range */}
                      {robustness && (
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-stone-100 text-stone-700 border border-stone-200 shrink-0" title="Certainty range observed across exhibit removals & reliability checks">
                          Certainty Range: {robustness.min_score}%–{robustness.max_score}%
                        </span>
                      )}

                      {h.cumulative_lr !== undefined && h.cumulative_lr !== null && scoringMethod !== 'classic_ach' && (
                        <span className="font-mono text-[10px] font-bold text-blue-900 bg-blue-50 border border-blue-200 px-2.5 py-0.5 rounded-full shrink-0" title="Cumulative Evidentiary Decisiveness from multiplying exhibits">
                          Proof Weight: {h.cumulative_lr > 1e4 || h.cumulative_lr < 1e-4 ? h.cumulative_lr.toExponential(2) : h.cumulative_lr.toFixed(2)}×
                        </span>
                      )}
                      <span className={cn(
                        "px-3 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border shrink-0",
                        isPrimary && "bg-emerald-50 text-emerald-800 border-emerald-300",
                        isDiscarded && "bg-stone-100 text-stone-600 border-stone-200",
                        !isPrimary && !isDiscarded && "bg-blue-50 text-blue-700 border-blue-200"
                      )}>
                        {isPrimary ? 'Prime Suspect' : isDiscarded ? 'Disproven / Ruled Out' : (h.status || 'Active')}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-3">
                      {/* Three-layer output side by side with comparison */}
                      <div className="grid grid-cols-3 gap-2 p-1.5 bg-[#f5f0e8] rounded-2xl border border-[#eae4d9]">
                        {/* Layer 1: Exhibit Proof */}
                        <div 
                          className={cn(
                            "px-2.5 py-1.5 rounded-xl text-center transition-all min-w-[115px]",
                            rankingCriterion === 'evidence' ? "bg-white shadow-xs border border-blue-400 ring-1 ring-blue-300" : "bg-white/60 border border-transparent"
                          )}
                          title="Exhibit Proof: direct exhibit strength without suspect background priors"
                        >
                          <div className="text-[9px] font-mono font-bold uppercase tracking-tight text-[#6e665d] leading-tight">
                            Exhibit Proof
                          </div>
                          {scoringMethod === 'comparison' ? (
                            <div className="mt-1 space-y-0.5">
                              <div className="text-xs font-mono font-bold text-emerald-800 flex items-center justify-between gap-1">
                                <span className="text-[8px] text-[#6e665d]">Prob.:</span>
                                <span>{(h.bayesian_evidence_score ?? evScore).toFixed(1)}%</span>
                              </div>
                              <div className="text-xs font-mono font-bold text-stone-600 flex items-center justify-between gap-1">
                                <span className="text-[8px] text-[#6e665d]">Elim.:</span>
                                <span>{(h.classic_evidence_score ?? evScore).toFixed(1)}%</span>
                              </div>
                            </div>
                          ) : (
                            <>
                              <div className="text-base font-mono font-bold text-blue-900 mt-0.5">
                                {evScore.toFixed(1)}%
                              </div>
                              <div className="text-[8px] font-mono text-[#8c8276]">
                                {scoringMethod === 'bayesian_lr' ? 'Evidence Weight' : 'Exhibit Support'}
                              </div>
                            </>
                          )}
                        </div>

                        {/* Layer 2: Means, Motive & Opportunity */}
                        <div 
                          onClick={() => setSelectedProfileHyp(h)}
                          className={cn(
                            "px-2.5 py-1.5 rounded-xl text-center transition-all min-w-[115px] cursor-pointer hover:ring-2 hover:ring-amber-300",
                            rankingCriterion === 'background' ? "bg-white shadow-xs border border-amber-400 ring-1 ring-amber-300" : "bg-white/60 border border-transparent"
                          )}
                          title="Means, Motive & Opportunity: click to inspect or adjust Access, Opportunity, Means, Motive, Alibi factors"
                        >
                          <div className="text-[9px] font-mono font-bold uppercase tracking-tight text-[#6e665d] leading-tight">
                            Means, Motive & Opp.
                          </div>
                          <div className="text-base font-mono font-bold text-amber-900 mt-0.5">
                            {bgScore.toFixed(1)}%
                          </div>
                          <div className="text-[8px] font-mono text-[#8c8276]">
                            MMO Prior ✎
                          </div>
                          {histCont > 0 && (
                            <div 
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedCriminalHistoryHypId(h.id);
                                setIsCriminalHistoryOpen(true);
                              }}
                              className={cn(
                                "mt-1 inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[8px] font-mono font-bold border transition-colors cursor-pointer shadow-2xs",
                                includeHistory 
                                  ? "bg-amber-100 text-amber-900 border-amber-300 hover:bg-amber-200" 
                                  : "bg-stone-100 text-stone-500 border-stone-200 line-through"
                              )}
                              title={includeHistory ? `+${(histCont * 100).toFixed(1)}% prior included` : 'History excluded under Section 54 IEA'}
                            >
                              <Scale className="w-2.5 h-2.5 text-amber-800" />
                              <span>{includeHistory ? `+${(histCont * 100).toFixed(1)}% prior` : 'hist excluded'}</span>
                            </div>
                          )}
                        </div>

                        {/* Layer 3: Overall Case Strength */}
                        <div 
                          className={cn(
                            "px-2.5 py-1.5 rounded-xl text-center transition-all min-w-[115px]",
                            rankingCriterion === 'combined' ? "bg-white shadow-xs border border-emerald-500 ring-1 ring-emerald-400" : "bg-white/60 border border-transparent"
                          )}
                          title="Overall Case Strength: Combined strength of exhibits, opportunity, and motive"
                        >
                          <div className="text-[9px] font-mono font-bold uppercase tracking-tight text-[#6e665d] leading-tight">
                            Case Strength
                          </div>
                          {scoringMethod === 'comparison' ? (
                            <div className="mt-1 space-y-0.5">
                              <div className="text-xs font-mono font-bold text-emerald-800 flex items-center justify-between gap-1">
                                <span className="text-[8px] text-[#6e665d]">Prob.:</span>
                                <span>{(h.bayesian_lr_score ?? combScore).toFixed(1)}%</span>
                              </div>
                              <div className="text-xs font-mono font-bold text-stone-600 flex items-center justify-between gap-1">
                                <span className="text-[8px] text-[#6e665d]">Elim.:</span>
                                <span>{(h.classic_ach_score ?? combScore).toFixed(1)}%</span>
                              </div>
                              {(() => {
                                const bScore = h.bayesian_lr_score ?? combScore;
                                const cScore = h.classic_ach_score ?? combScore;
                                const delta = bScore - cScore;
                                return (
                                  <div className="text-[8px] font-mono font-bold text-purple-700 bg-purple-50 px-1 py-0.5 rounded border border-purple-200 text-center">
                                    Δ {delta >= 0 ? `+${delta.toFixed(1)}` : delta.toFixed(1)}%
                                  </div>
                                );
                              })()}
                            </div>
                          ) : (
                            <>
                              <div className="text-base font-mono font-bold text-emerald-900 mt-0.5">
                                {combScore.toFixed(1)}%
                              </div>
                              <div className="text-[8px] font-mono text-[#8c8276]">
                                {scoringMethod === 'bayesian_lr' ? 'Case Strength' : 'Elimination Score'}
                              </div>
                              {histCont > 0 && !includeHistory && (
                                <div className="mt-0.5 text-[8px] font-mono font-bold text-rose-700">
                                  Δ -{(histCont * 100).toFixed(1)}% w/o history
                                </div>
                              )}
                            </>
                          )}
                        </div>
                      </div>

                      {/* Change 6: Monte Carlo Credible Range & Error Bar Whisker Track */}
                      {(() => {
                        const mcRange = monteCarloData?.ranges?.find(r => String(r.hypothesis_id) === String(h.id));
                        return (
                          <div className="min-w-[210px] max-w-xs px-3 py-2 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] flex flex-col justify-center">
                            <div className="flex items-center justify-between text-[10px] font-mono mb-1">
                              <span className="font-bold text-[#191410] truncate max-w-[125px]" title={mcRange?.plain_label || 'Plausible Score Range'}>
                                {mcRange ? mcRange.plain_label : 'Range Error Bar'}
                              </span>
                              <span className="font-bold text-[#d93829]">
                                {mcRange ? `${mcRange.p5_score.toFixed(0)}%–${mcRange.p95_score.toFixed(0)}%` : `${score.toFixed(1)}%`}
                              </span>
                            </div>

                            {/* Horizontal Error Bar Track */}
                            <div className="w-full h-3 bg-[#e8e2d5] rounded-full relative overflow-visible flex items-center my-0.5">
                              {mcRange ? (
                                <>
                                  {/* Shaded Credible Interval [p5, p95] */}
                                  <div 
                                    className="absolute h-2 bg-gradient-to-r from-emerald-400 to-teal-500 rounded-full opacity-80"
                                    style={{ 
                                      left: `${Math.max(0, Math.min(95, mcRange.p5_score))}%`, 
                                      width: `${Math.max(3, Math.min(100 - mcRange.p5_score, mcRange.p95_score - mcRange.p5_score))}%` 
                                    }}
                                    title={`90% Credible Range: ${mcRange.p5_score}% to ${mcRange.p95_score}%`}
                                  />
                                  {/* Left Whisker Cap (p5) */}
                                  <div 
                                    className="absolute w-0.5 h-3 bg-[#191410] rounded"
                                    style={{ left: `${Math.max(0, Math.min(99, mcRange.p5_score))}%` }}
                                    title={`5th Percentile: ${mcRange.p5_score}%`}
                                  />
                                  {/* Right Whisker Cap (p95) */}
                                  <div 
                                    className="absolute w-0.5 h-3 bg-[#191410] rounded"
                                    style={{ left: `${Math.max(1, Math.min(99, mcRange.p95_score))}%` }}
                                    title={`95th Percentile: ${mcRange.p95_score}%`}
                                  />
                                  {/* Median Dot Marker (p50) */}
                                  <div 
                                    className="absolute w-2.5 h-2.5 rounded-full bg-[#191410] ring-2 ring-white shadow-xs -ml-1.25"
                                    style={{ left: `${Math.max(1, Math.min(98, mcRange.median_score))}%` }}
                                    title={`Median Sampled Score: ${mcRange.median_score}%`}
                                  />
                                </>
                              ) : (
                                <div 
                                  className={cn(
                                    "h-full rounded-full transition-all duration-500",
                                    score >= 40 && "bg-emerald-500",
                                    score < 40 && score > 10 && "bg-amber-500",
                                    score <= 10 && "bg-rose-500"
                                  )}
                                  style={{ width: `${Math.max(4, score)}%` }}
                                />
                              )}
                            </div>

                            <div className="flex items-center justify-between text-[8px] font-mono text-[#8c8276] mt-0.5">
                              <span>0%</span>
                              <span>
                                {mcRange ? `Median: ${mcRange.median_score.toFixed(1)}% (±${(mcRange.range_spread / 2).toFixed(1)}%)` : `Score: ${score.toFixed(1)}%`}
                              </span>
                              <span>100%</span>
                            </div>
                          </div>
                        );
                      })()}

                      <button
                        onClick={() => toggleCalcTrace(h.id)}
                        className={cn(
                          "px-3.5 py-1.5 rounded-full border text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer shadow-xs",
                          isCalcTraceOpen
                            ? "bg-amber-600 hover:bg-amber-700 text-white border-amber-600 ring-2 ring-amber-300" 
                            : "bg-[#faf7f2] hover:bg-[#eae4d9] text-[#191410] border-[#d8d0c5]"
                        )}
                        title="View step-by-step mathematical trace explaining how this score was calculated"
                      >
                        <Sliders className={cn("w-3.5 h-3.5", isCalcTraceOpen ? "text-white" : "text-amber-600")} />
                        <span>{isCalcTraceOpen ? "Hide Calculation Trace" : "How Score Was Calculated"}</span>
                      </button>

                      <button
                        onClick={() => handleOpenBreakdown(h)}
                        className="px-3.5 py-1.5 rounded-full bg-[#191410] hover:bg-[#d93829] text-white text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer shadow-xs"
                        title="View mathematical breakdown of exhibit contributions, reliabilities, and verified quotes"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Breakdown</span>
                      </button>

                      <button
                        onClick={() => setSelectedProfileHyp(h)}
                        className="px-3 py-1.5 rounded-full bg-[#faf7f2] hover:bg-[#eae4d9] text-[#191410] border border-[#d8d0c5] text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer shadow-xs"
                        title="View & Edit Suspect Profile: Access, Opportunity, Means, Motive, Alibi, Feasibility"
                      >
                        <UserCheck className="w-3.5 h-3.5 text-amber-700" />
                        <span>Suspect Profile</span>
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

                  {/* Decision Quality: Plain-Language Explanation for Non-Technical Officers */}
                  <div className="mt-3 p-3.5 rounded-2xl bg-[#faf7f2] border border-[#e5ded3] space-y-2.5 shadow-2xs">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-[#191410] text-white flex items-center gap-1">
                          <BookOpen className="w-3 h-3 text-amber-400" />
                          <span>IO Plain-Language Brief</span>
                        </span>
                        {h.plain_language_verdict && (
                          <span className={cn(
                            "px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border",
                            h.plain_language_verdict.toLowerCase().includes('decisive') && "bg-emerald-100 text-emerald-900 border-emerald-300",
                            h.plain_language_verdict.toLowerCase().includes('strong') && "bg-teal-100 text-teal-900 border-teal-300",
                            h.plain_language_verdict.toLowerCase().includes('plausible') && "bg-amber-100 text-amber-900 border-amber-300",
                            h.plain_language_verdict.toLowerCase().includes('disfavored') && "bg-rose-100 text-rose-900 border-rose-300"
                          )}>
                            {h.plain_language_verdict}
                          </span>
                        )}
                        <span className="text-[11px] font-sans font-medium text-stone-700">
                          {h.plain_language_summary || (
                            combScore >= 40 
                              ? `Primary working hypothesis with ${(combScore).toFixed(1)}% likelihood. Supported by key exhibits without critical contradictions.`
                              : combScore >= 15
                                ? `Active secondary hypothesis (${(combScore).toFixed(1)}% likelihood). Requires further corroboration or exclusion testing.`
                                : `Low probability alternative (${(combScore).toFixed(1)}% likelihood). Disfavored by inconsistencies or lack of positive evidence.`
                          )}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        {idx === 1 && (
                          <button
                            onClick={() => {
                              setDevilsAdvocateTargetId(Number(h.id));
                              setIsDevilsAdvocateOpen(true);
                            }}
                            className="px-2.5 py-1 rounded-full text-[11px] font-mono font-bold bg-rose-100 hover:bg-rose-200 text-rose-900 border border-rose-300 transition-colors flex items-center gap-1 cursor-pointer"
                            title="Stress-test this hypothesis as the primary alternative against the lead"
                          >
                            <Scale className="w-3 h-3 text-rose-700" />
                            <span>Devil's Advocate Focus</span>
                          </button>
                        )}
                        <button
                          onClick={() => togglePlainLanguage(String(h.id))}
                          className="px-2.5 py-1 rounded-full text-[11px] font-mono font-bold bg-white hover:bg-stone-100 text-stone-700 border border-stone-300 transition-colors flex items-center gap-1 cursor-pointer"
                        >
                          <span>{expandedPlainLanguage[String(h.id)] ? 'Hide Details' : 'Key Drivers & Doubts'}</span>
                          {expandedPlainLanguage[String(h.id)] ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                        </button>
                      </div>
                    </div>

                    {/* Expandable Key Drivers & Evidentiary Doubts */}
                    {expandedPlainLanguage[String(h.id)] && (
                      <div className="pt-2 border-t border-stone-200/80 grid grid-cols-1 md:grid-cols-2 gap-3 animate-in fade-in duration-150">
                        <div className="p-2.5 rounded-xl bg-white border border-emerald-200 text-xs space-y-1">
                          <div className="font-mono font-bold text-[10px] uppercase text-emerald-800 flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            <span>Primary Evidentiary Drivers (Why score is high)</span>
                          </div>
                          {h.plain_language_drivers && Array.isArray(h.plain_language_drivers) && h.plain_language_drivers.length > 0 ? (
                            <ul className="list-disc pl-4 space-y-0.5 text-stone-700 text-[11px]">
                              {h.plain_language_drivers.map((d: string, dIdx: number) => (
                                <li key={dIdx}>{d}</li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-[11px] text-stone-500 italic">
                              Supported by {supportingCount} exhibits in the ACH matrix with consistent physical or circumstantial evidence.
                            </p>
                          )}
                        </div>

                        <div className="p-2.5 rounded-xl bg-white border border-rose-200 text-xs space-y-1">
                          <div className="font-mono font-bold text-[10px] uppercase text-rose-800 flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3 text-rose-600" />
                            <span>Vulnerabilities & Evidentiary Doubts (Defense challenges)</span>
                          </div>
                          {h.plain_language_doubts && Array.isArray(h.plain_language_doubts) && h.plain_language_doubts.length > 0 ? (
                            <ul className="list-disc pl-4 space-y-0.5 text-stone-700 text-[11px]">
                              {h.plain_language_doubts.map((d: string, dIdx: number) => (
                                <li key={dIdx}>{d}</li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-[11px] text-stone-500 italic">
                              {contradictingCount > 0 
                                ? `${contradictingCount} contradictory exhibit(s) present unaddressed timeline or physical discrepancies.`
                                : 'No critical physical contradictions currently registered.'}
                            </p>
                          )}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Step-by-Step Mathematical Calculation Trace (Change requested by user) */}
                  {isCalcTraceOpen && (
                    <div className="mt-4 pt-4 border-t border-[#eae4d9] space-y-4 animate-in fade-in duration-200">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-[#eae4d9]/80">
                        <div className="flex items-center gap-2">
                          <div className="p-1.5 bg-amber-100 rounded-lg text-amber-800">
                            <Sliders className="w-4 h-4 text-amber-700" />
                          </div>
                          <div>
                            <h4 className="font-serif font-bold text-sm text-[#191410]">
                              How Case Strength Was Calculated • Complete Investigative Trace
                            </h4>
                            <p className="text-[10px] text-[#6e665d] font-mono">
                              Transparent forensic formulation: Alibi Conflicts & Inconsistencies + Suspect Opportunity & Motive + Evidentiary Weight + Statutory Safeguards
                            </p>
                          </div>
                        </div>
                        <span className="text-[10px] font-mono font-bold text-amber-900 bg-amber-50 px-2.5 py-1 rounded-full border border-amber-200 self-start sm:self-auto">
                          Formula: Exhibit Proof ⊗ Opportunity/Motive → Case Strength
                        </span>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        {/* Layer 1: Exhibit Proof */}
                        <div className="p-4 rounded-2xl bg-[#faf7f2] border border-blue-200 shadow-xs space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-blue-900 flex items-center gap-1">
                              <FileText className="w-3.5 h-3.5 text-blue-600" />
                              <span>Layer 1: Exhibit Proof</span>
                            </span>
                            <span className="text-lg font-mono font-bold text-blue-950">
                              {evScore.toFixed(1)}%
                            </span>
                          </div>
                          <p className="text-[11px] text-[#6e665d]">
                            Evaluated against <strong>{enriched.length} exhibits</strong> ({supportingCount} supporting, {contradictingCount} contradicting).
                          </p>
                          <div className="p-2.5 rounded-xl bg-white border border-blue-100 font-mono text-[10px] text-blue-950 space-y-1">
                            <div><span className="text-[#6e665d]">Alibi Conflict Penalty:</span> <strong className="text-rose-700">{penalty.toFixed(2)}</strong></div>
                            <div><span className="text-[#6e665d]">Elimination Base:</span> e^(-0.75 × {penalty.toFixed(2)}) = <strong>{Math.exp(-0.75 * penalty).toFixed(4)}</strong></div>
                            <div><span className="text-[#6e665d]">Normalized Exhibit Proof:</span> <strong className="text-blue-900">{evScore.toFixed(1)}%</strong> (among evaluated theories, $\sum = 100\%$)</div>
                            {h.cumulative_lr !== undefined && h.cumulative_lr !== null && (
                              <div className="pt-1 mt-1 border-t border-blue-100 text-blue-800">
                                <span className="text-[#6e665d]">Evidentiary Weight:</span> <strong>{h.cumulative_lr >= 1e4 || h.cumulative_lr < 1e-4 ? h.cumulative_lr.toExponential(2) : h.cumulative_lr.toFixed(2)}×</strong>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Layer 2: Suspect Means, Motive & Opportunity */}
                        <div className="p-4 rounded-2xl bg-[#faf7f2] border border-amber-200 shadow-xs space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-amber-900 flex items-center gap-1">
                              <UserCheck className="w-3.5 h-3.5 text-amber-600" />
                              <span>Layer 2: Means, Motive & Opp.</span>
                            </span>
                            <span className="text-lg font-mono font-bold text-amber-950">
                              {bgScore.toFixed(1)}%
                            </span>
                          </div>
                          <p className="text-[11px] text-[#6e665d]">
                            Suspect prior formulated from opportunity, access, means, motive, alibi, and transit feasibility before exhibits.
                          </p>
                          <div className="p-2.5 rounded-xl bg-white border border-amber-100 font-mono text-[10px] text-amber-950 space-y-1">
                            <div><span className="text-[#6e665d]">Baseline Prior:</span> <strong>{bgScore.toFixed(1)}%</strong></div>
                            {histCont > 0 ? (
                              <div className="text-purple-800">
                                <span className="text-[#6e665d]">Modus Operandi Boost:</span> <strong>+{(histCont * 100).toFixed(1)}%</strong> (statutory cap applied)
                              </div>
                            ) : (
                              <div className="text-stone-500">
                                <span className="text-[#6e665d]">Prior Record:</span> <strong>0.0% (No MO match or partitioned)</strong>
                              </div>
                            )}
                            <div className="pt-1 mt-1 border-t border-amber-100 text-amber-900 text-[9px]">
                              Alibi discounts applied for verified exculpatory timelines.
                            </div>
                          </div>
                        </div>

                        {/* Layer 3: Overall Case Strength */}
                        <div className="p-4 rounded-2xl bg-[#faf7f2] border border-emerald-200 shadow-xs space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-emerald-900 flex items-center gap-1">
                              <Scale className="w-3.5 h-3.5 text-emerald-600" />
                              <span>Layer 3: Overall Case Strength</span>
                            </span>
                            <span className="text-lg font-mono font-bold text-emerald-950">
                              {combScore.toFixed(1)}%
                            </span>
                          </div>
                          <p className="text-[11px] text-[#6e665d]">
                            Combined case certainty: posterior probability combining Layer 1 exhibit proof with Layer 2 suspect background prior.
                          </p>
                          <div className="p-2.5 rounded-xl bg-white border border-emerald-100 font-mono text-[10px] text-emerald-950 space-y-1">
                            <div><span className="text-[#6e665d]">Evidence-Backed Strength:</span> <strong className="text-emerald-900">{combScore.toFixed(1)}%</strong></div>
                            <div><span className="text-[#6e665d]">Suspect Priority:</span> #{idx + 1} • {isPrimary ? 'Prime Suspect' : isDiscarded ? 'Disproven / Ruled Out' : 'Active Suspect'}</div>
                            {robustness && (
                              <div className="text-stone-700">
                                <span className="text-[#6e665d]">Certainty Range:</span> <strong>{robustness.min_score}%–{robustness.max_score}%</strong>
                              </div>
                            )}
                            {histCont > 0 && !includeHistory && (
                              <div className="pt-1 mt-1 border-t border-rose-100 text-rose-700 font-bold">
                                Section 54 IEA Safeguard: -{(histCont * 100).toFixed(1)}% history excluded
                              </div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Safeguard & Methodological Disclaimer */}
                      <div className="p-3 rounded-xl bg-amber-50/60 border border-amber-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-[10px] font-mono text-amber-950">
                        <div className="flex items-center gap-2">
                          <ShieldCheck className="w-4 h-4 text-emerald-700 shrink-0" />
                          <span>
                            <strong>Legal Safeguard Notice:</strong> Prior history is partitioned under Indian Evidence Act § 54 / BSA § 52 with max +10% cap. Decision support only — not a verdict.
                          </span>
                        </div>
                        <button
                          onClick={() => handleOpenBreakdown(h)}
                          className="text-[#d93829] hover:underline font-bold shrink-0 flex items-center gap-1 cursor-pointer"
                        >
                          <span>Inspect Exhibit-by-Exhibit Breakdown Table →</span>
                        </button>
                      </div>
                    </div>
                  )}
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
                              <div className="flex items-center gap-2">
                                <span className={cn("px-2.5 py-1 rounded-md text-[11px] font-mono font-bold border", clsMeta.color)}>
                                  {clsMeta.label}
                                </span>
                                <div className="flex items-center gap-1 font-mono text-[11px]">
                                  <span className="text-[#6e665d]">Signed Contribution:</span>
                                  <span className={cn(
                                    "font-bold",
                                    contrib > 0 ? "text-emerald-700" : contrib < 0 ? "text-rose-700" : "text-stone-500"
                                  )}>
                                    {contrib > 0 ? `+${contrib.toFixed(2)}` : contrib.toFixed(2)}
                                  </span>
                                  {(a as any).share_of_support_pct !== undefined && (a as any).share_of_support_pct > 0 && (
                                    <span className="text-[10px] text-emerald-800 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200">
                                      {(a as any).share_of_support_pct}% share
                                    </span>
                                  )}
                                </div>
                              </div>

                              {a.likelihood_ratio !== undefined && a.likelihood_ratio !== null ? (
                                <div className="flex flex-wrap items-center gap-2 font-mono text-[11px]">
                                  <span className="text-[#6e665d]">Forensic LR:</span>
                                  <span className="font-bold text-blue-800" title={`Reference Range: [${a.lr_min ?? '—'}, ${a.lr_max ?? '—'}]`}>
                                    {a.likelihood_ratio > 1e4 ? a.likelihood_ratio.toExponential(1) : a.likelihood_ratio}×
                                  </span>
                                  <span className="text-stone-300">•</span>
                                  <span className="text-[#6e665d]">Shrunk:</span>
                                  <span className="font-bold text-emerald-700" title="Shrunk by Reliability × Confidence">
                                    {a.effective_lr ? a.effective_lr.toFixed(2) : '1.00'}×
                                  </span>
                                  {a.weight_of_evidence_bans !== undefined && a.weight_of_evidence_bans !== null && (
                                    <>
                                      <span className="text-stone-300">•</span>
                                      <span className="text-[#6e665d]">WoE:</span>
                                      <span className={cn(
                                        "font-bold",
                                        a.weight_of_evidence_bans > 0 ? "text-emerald-700" : a.weight_of_evidence_bans < 0 ? "text-rose-700" : "text-stone-500"
                                      )}>
                                        {a.weight_of_evidence_bans > 0 ? `+${a.weight_of_evidence_bans.toFixed(1)}` : a.weight_of_evidence_bans.toFixed(1)} dB
                                      </span>
                                    </>
                                  )}
                                </div>
                              ) : (
                                <div className="text-[10px] font-mono text-[#8c8276]">
                                  Reliability: {(a.computed_reliability ?? a.reliability ?? 1.0)} • Diag: {diagWeight}x
                                </div>
                              )}
                            </div>

                            {/* Forensic Finding category and citation if present */}
                            {a.finding_name && (
                              <div className="text-[10px] font-mono text-[#6e665d] flex items-center gap-1.5 flex-wrap">
                                <span className="font-bold text-stone-700">Forensic Category:</span>
                                <span className="text-blue-900 font-semibold">{a.finding_name}</span>
                                {a.lr_source_citation && (
                                  <span className="text-[9px] text-[#8c8276] italic">({a.lr_source_citation})</span>
                                )}
                              </div>
                            )}

                            {/* Change 5: Clearing Factor Badge */}
                            {(a.is_exculpatory || a.clearing_factor_note) && (
                              <div className="flex items-start gap-1.5 p-2 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-950 text-[11px]">
                                <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                                <div>
                                  <span className="font-serif font-bold block uppercase tracking-wider text-[9px] text-emerald-800">
                                    Clearing Factor (Exculpatory Evidence)
                                  </span>
                                  <span className="leading-snug block font-medium">
                                    {a.clearing_factor_note || 'Physical or scientific exclusion clearing suspect.'}
                                  </span>
                                </div>
                              </div>
                            )}

                            {/* Change 5: Shared Source Dependency Group Badge */}
                            {a.dependency_group && (
                              <div className="flex items-center gap-1.5 flex-wrap">
                                <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-purple-50 text-purple-900 border border-purple-200 flex items-center gap-1">
                                  <GitBranch className="w-3 h-3 text-purple-700" />
                                  <span>Shared Source: {a.dependency_group}</span>
                                </span>
                                {a.dependency_weight_multiplier !== undefined && a.dependency_weight_multiplier < 1.0 && (
                                  <span className="text-[9px] font-mono text-purple-800 bg-purple-100 px-1.5 py-0.2 rounded border border-purple-300">
                                    -{( (1 - a.dependency_weight_multiplier) * 100 ).toFixed(0)}% Damping Discount
                                  </span>
                                )}
                              </div>
                            )}

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

                              <div className="flex items-center gap-2">
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

                                {(isOverridden || a.second_signoff_status) && (
                                  <button
                                    onClick={() => setIsSignoffModalOpen(true)}
                                    className={cn(
                                      "text-[10px] font-mono font-bold px-2 py-0.5 rounded-md border flex items-center gap-1 cursor-pointer transition-all",
                                      a.second_signoff_status === 'approved' 
                                        ? "bg-emerald-50 text-emerald-800 border-emerald-300"
                                        : a.second_signoff_status === 'pending'
                                          ? "bg-amber-50 text-amber-800 border-amber-300"
                                          : "bg-cyan-50 text-cyan-800 border-cyan-300 hover:bg-cyan-100"
                                    )}
                                    title="Four-Eyes Protocol: Two-analyst signoff required for overrides and key classifications"
                                  >
                                    <UserCheck className="w-2.5 h-2.5" />
                                    <span>
                                      {a.second_signoff_status === 'approved'
                                        ? `2nd Sign-Off: Approved (${a.second_signoff_by_name || 'Checker'})`
                                        : a.second_signoff_status === 'pending'
                                          ? '2nd Sign-Off: Pending'
                                          : 'Request 2nd Sign-Off'}
                                    </span>
                                  </button>
                                )}
                              </div>
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
                <span>Proof & Alibi Evaluation Matrix</span>
              </CardTitle>
              <p className="text-xs text-[#6e665d] mt-0.5">
                Full forensic cross-evaluation grid: rows represent evidentiary exhibits with decisiveness weights; columns represent suspect theories.
              </p>
            </div>
            <div className="text-xs font-mono font-bold text-[#d93829]">
              Forensic Proof vs. Suspects Grid
            </div>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="bg-[#f5f0e8] border-b border-[#eae4d9]">
                  <th className="p-3.5 font-mono font-bold text-[#191410] min-w-[220px]">
                    Exhibits & Decisiveness
                  </th>
                  {sortedHypotheses.map((h, hIdx) => {
                    const bayesScore = h.bayesian_lr_score ?? (h as any).bayesianLrScore ?? h.combined_score ?? 50.0;
                    const classicScore = h.classic_ach_score ?? (h as any).classicAchScore ?? h.combined_score ?? 50.0;
                    const bayesEv = h.bayesian_evidence_score ?? (h as any).bayesianEvidenceScore ?? h.evidence_score ?? 50.0;
                    const classicEv = h.classic_evidence_score ?? (h as any).classicEvidenceScore ?? h.evidence_score ?? 50.0;
                    const evScore = scoringMethod === 'classic_ach' ? classicEv : bayesEv;
                    const bgScore = h.background_score ?? (h as any).backgroundScore ?? 50.0;
                    const combScore = scoringMethod === 'classic_ach' ? classicScore : bayesScore;
                    const cumLR = h.cumulative_lr ?? (h as any).cumulativeLr ?? 1.0;
                    const robustness = robustnessRanges[String(h.id)] || robustnessRanges[h.id];
                    return (
                      <th key={`matrix-head-${h.id}`} className="p-3.5 border-l border-[#eae4d9] min-w-[220px]">
                        <div className="flex items-center justify-between gap-1 mb-1">
                          <span className="font-mono text-[10px] font-bold px-2 py-0.5 bg-[#191410] text-white rounded-full">
                            {hIdx === 0 ? 'Prime Suspect' : `Suspect ${hIdx + 1}`}
                          </span>
                          <span className="font-mono text-xs font-bold text-emerald-800" title="Methodology score">
                            {combScore.toFixed(1)}% Strength
                          </span>
                        </div>
                        <div className="font-serif font-bold text-[#191410] truncate text-xs" title={h.title}>
                          {h.title}
                        </div>
                        <div className="flex items-center gap-2 mt-1.5 pt-1.5 border-t border-[#eae4d9] text-[9px] font-mono">
                          <span className="text-blue-800" title="Direct exhibit proof">Proof: {evScore.toFixed(1)}%</span>
                          <span className="text-[#8c8276]">•</span>
                          <button
                            onClick={() => setSelectedProfileHyp(h)}
                            className="text-amber-800 hover:underline cursor-pointer flex items-center gap-0.5"
                            title="Inspect / Edit Suspect Profile"
                          >
                            <span>MMO: {bgScore.toFixed(1)}% ✎</span>
                          </button>
                        </div>
                        {/* Cumulative LR badge */}
                        <div className="flex items-center justify-between text-[9px] font-mono text-[#6e665d] mt-1 pt-1 border-t border-[#eae4d9]/60">
                          <span>Proof Wt:</span>
                          <span className="font-bold text-[#191410]">
                            {cumLR >= 10000 ? `${cumLR.toExponential(1)}×` : `${cumLR.toFixed(cumLR < 1 ? 3 : 1)}×`}
                          </span>
                        </div>
                        {robustness && (
                          <div className="text-[9px] font-mono text-[#6e665d] mt-0.5">
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

                      {sortedHypotheses.map((h) => {
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

                              {/* Change 4: Likelihood Ratio & Effective Shrunk Ratio Display */}
                              {assessment && (assessment.effective_lr !== undefined || assessment.likelihood_ratio !== undefined) && (
                                <div className="pt-1.5 border-t border-black/10 text-[9px] font-mono space-y-0.5 bg-black/3 p-1.5 rounded-lg">
                                  <div className="flex items-center justify-between">
                                    <span className="text-[#6e665d]">Table LR:</span>
                                    <span className="font-bold text-[#191410]">
                                      {(assessment.likelihood_ratio ?? 1.0) >= 10000 
                                        ? `${(assessment.likelihood_ratio ?? 1.0).toExponential(1)}×` 
                                        : `${(assessment.likelihood_ratio ?? 1.0).toFixed((assessment.likelihood_ratio ?? 1.0) < 1 ? 3 : 1)}×`}
                                    </span>
                                  </div>
                                  <div className="flex items-center justify-between">
                                    <span className="text-[#6e665d]" title="Ratio shrunk toward 1.0 by reliability and confidence">
                                      Shrunk LR:
                                    </span>
                                    <span className={cn(
                                      "font-bold",
                                      (assessment.effective_lr ?? 1.0) > 1.0 ? "text-emerald-800" :
                                      (assessment.effective_lr ?? 1.0) < 1.0 ? "text-rose-800" : "text-stone-600"
                                    )}>
                                      {(assessment.effective_lr ?? 1.0) >= 10000 
                                        ? `${(assessment.effective_lr ?? 1.0).toExponential(1)}×` 
                                        : `${(assessment.effective_lr ?? 1.0).toFixed((assessment.effective_lr ?? 1.0) < 1 ? 3 : 1)}×`}
                                    </span>
                                  </div>
                                  {assessment.weight_of_evidence_bans !== undefined && assessment.weight_of_evidence_bans !== null && (
                                    <div className="flex items-center justify-between text-[8px] text-[#8c8276]">
                                      <span>WoE:</span>
                                      <span className="font-bold">{assessment.weight_of_evidence_bans > 0 ? `+${assessment.weight_of_evidence_bans.toFixed(1)}` : assessment.weight_of_evidence_bans.toFixed(1)} dB</span>
                                    </div>
                                  )}
                                  {assessment.finding_name && (
                                    <div className="text-[8px] text-[#6e665d] italic truncate font-serif" title={`${assessment.finding_name} (${assessment.lr_source_citation || ''})`}>
                                      {assessment.finding_name}
                                    </div>
                                  )}
                                </div>
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

      {/* DETAILED MATHEMATICAL BREAKDOWN MODAL / DRAWER (Change 9: 3-Layer Breakdown) */}
      {breakdownModalHyp && (() => {
        const hypEvScore = (breakdownModalHyp as any).evidence_score ?? breakdownModalHyp.support_score ?? 0;
        const hypBaseBg = (breakdownModalHyp as any).background_score ?? 50.0;
        const hypHistCont = (breakdownModalHyp as any).history_contribution ?? 0;
        const hypBgWithout = (breakdownModalHyp as any).background_score_without_history ?? Math.max(0, hypBaseBg - hypHistCont * 100);
        const hypBaseComb = (breakdownModalHyp as any).combined_score ?? breakdownModalHyp.support_score ?? 0;
        const hypCombWithout = (breakdownModalHyp as any).combined_score_without_history ?? Math.max(0, hypBaseComb - hypHistCont * 100);

        return (
          <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-200">
            <div className="bg-white rounded-3xl max-w-5xl w-full p-6 space-y-5 border border-[#eae4d9] shadow-2xl max-h-[90vh] flex flex-col">
              <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9]">
                <div>
                  <div className="text-[11px] font-mono font-bold uppercase tracking-wider text-[#d93829] flex items-center gap-1.5">
                    <Scale className="w-3.5 h-3.5" />
                    <span>Investigative Breakdown • Suspect #{breakdownModalHyp.id}</span>
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

              {/* Three Tab Selectors */}
              <div className="flex items-center gap-2 border-b border-[#eae4d9] pb-2 overflow-x-auto">
                <button
                  onClick={() => setBreakdownTab('evidence')}
                  className={cn(
                    "px-4 py-2 rounded-xl text-xs font-mono font-bold transition-all flex items-center gap-2 cursor-pointer whitespace-nowrap",
                    breakdownTab === 'evidence'
                      ? "bg-blue-600 text-white shadow-xs"
                      : "text-[#6e665d] hover:bg-[#faf7f2] hover:text-[#191410]"
                  )}
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>1. Exhibit Proof</span>
                  <span className={cn(
                    "px-1.5 py-0.5 rounded-full text-[10px] font-mono font-bold",
                    breakdownTab === 'evidence' ? "bg-white/20 text-white" : "bg-blue-100 text-blue-800"
                  )}>
                    {hypEvScore.toFixed(1)}%
                  </span>
                </button>

                <button
                  onClick={() => setBreakdownTab('background')}
                  className={cn(
                    "px-4 py-2 rounded-xl text-xs font-mono font-bold transition-all flex items-center gap-2 cursor-pointer whitespace-nowrap",
                    breakdownTab === 'background'
                      ? "bg-amber-600 text-white shadow-xs"
                      : "text-[#6e665d] hover:bg-[#faf7f2] hover:text-[#191410]"
                  )}
                >
                  <UserCheck className="w-3.5 h-3.5" />
                  <span>2. Means, Motive & Opp.</span>
                  <span className={cn(
                    "px-1.5 py-0.5 rounded-full text-[10px] font-mono font-bold",
                    breakdownTab === 'background' ? "bg-white/20 text-white" : "bg-amber-100 text-amber-800"
                  )}>
                    {hypBaseBg.toFixed(1)}%
                  </span>
                </button>

                <button
                  onClick={() => setBreakdownTab('history')}
                  className={cn(
                    "px-4 py-2 rounded-xl text-xs font-mono font-bold transition-all flex items-center gap-2 cursor-pointer whitespace-nowrap",
                    breakdownTab === 'history'
                      ? "bg-purple-700 text-white shadow-xs"
                      : "text-[#6e665d] hover:bg-[#faf7f2] hover:text-[#191410]"
                  )}
                >
                  <Scale className="w-3.5 h-3.5" />
                  <span>3. Prior Record & MO</span>
                  {breakdownPriorRestricted ? (
                    <span className="px-1.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-rose-100 text-rose-800 flex items-center gap-1">
                      <Lock className="w-2.5 h-2.5" />
                      <span>Restricted</span>
                    </span>
                  ) : (
                    <span className={cn(
                      "px-1.5 py-0.5 rounded-full text-[10px] font-mono font-bold",
                      breakdownTab === 'history' ? "bg-white/20 text-white" : "bg-purple-100 text-purple-800"
                    )}>
                      +{(Math.min(0.10, hypHistCont) * 100).toFixed(1)}%
                    </span>
                  )}
                </button>
              </div>

              {loadingBreakdown ? (
                <div className="py-20 text-center">
                  <Loader2 className="w-8 h-8 animate-spin text-[#d93829] mx-auto mb-2" />
                  <p className="text-xs font-mono text-[#8c8276]">Resolving reliability audits & exact quoted source lines...</p>
                </div>
              ) : (
                <div className="overflow-y-auto flex-1 space-y-4 pr-1">
                  {/* TAB 1: EVIDENCE CONTRIBUTIONS */}
                  {breakdownTab === 'evidence' && (
                    <div className="space-y-4">
                      {/* Summary Banner */}
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        <div className="p-3.5 rounded-2xl bg-blue-50/60 border border-blue-200">
                          <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-blue-900">
                            Exhibit Proof Strength
                          </div>
                          <div className="text-2xl font-mono font-bold text-blue-950 mt-1">
                            {hypEvScore.toFixed(1)}%
                          </div>
                          <div className="text-[10px] font-mono text-blue-800 mt-0.5">
                            Explanatory support strictly from exhibits ($\sum = 100\%$)
                          </div>
                        </div>

                        <div className="p-3.5 rounded-2xl bg-[#faf7f2] border border-[#eae4d9]">
                          <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#6e665d]">
                            Alibi Conflicts / Contradictions
                          </div>
                          <div className="text-2xl font-mono font-bold text-rose-900 mt-1">
                            {(breakdownModalHyp.disconfirmation_penalty ?? 0).toFixed(2)}
                          </div>
                          <div className="text-[10px] font-mono text-[#8c8276] mt-0.5">
                            Cumulative alibi conflict penalty
                          </div>
                        </div>

                        <div className="p-3.5 rounded-2xl bg-[#faf7f2] border border-[#eae4d9]">
                          <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#6e665d]">
                            Exhibits & Evidentiary Decisiveness
                          </div>
                          <div className="text-2xl font-mono font-bold text-[#191410] mt-1">
                            {breakdownRows.length} Exhibits
                          </div>
                          <div className="text-[10px] font-mono text-[#8c8276] mt-0.5">
                            Proof Decisiveness: {(breakdownModalHyp.cumulative_lr ?? 1.0) >= 1e4 ? (breakdownModalHyp.cumulative_lr ?? 1.0).toExponential(1) : (breakdownModalHyp.cumulative_lr ?? 1.0).toFixed(2)}×
                          </div>
                        </div>
                      </div>

                      <div className="border border-[#eae4d9] rounded-2xl overflow-hidden">
                  <table className="w-full text-xs text-left border-collapse">
                    <thead className="bg-[#f5f0e8] border-b border-[#eae4d9] font-mono text-[11px]">
                      <tr>
                        <th className="p-3 font-bold text-[#191410]">Exhibit</th>
                        <th className="p-3 font-bold text-[#191410]">Classification / Finding</th>
                        <th className="p-3 font-bold text-[#191410]">Reliability & Shrinkage</th>
                        <th className="p-3 font-bold text-[#191410]">Diagnosticity</th>
                        <th className="p-3 font-bold text-[#191410]">Signed Contribution</th>
                        <th className="p-3 font-bold text-[#191410]">Share of Support</th>
                        <th className="p-3 font-bold text-[#191410]">Forensic LR & WoE</th>
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
                              <div className="mt-1 flex items-center gap-1.5 flex-wrap">
                                {getEvidenceTypeBadge(row.evidence_type)}
                                {row.finding_name && (
                                  <span className="text-[10px] font-mono text-blue-900 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                                    {row.finding_name}
                                  </span>
                                )}
                                {row.dependency_group && (
                                  <span className="text-[10px] font-mono font-bold text-purple-900 bg-purple-50 px-2 py-0.5 rounded border border-purple-200 flex items-center gap-1">
                                    <GitBranch className="w-3 h-3 text-purple-700" />
                                    <span>Group: {row.dependency_group}</span>
                                  </span>
                                )}
                              </div>

                              {/* Change 5: Clearing Factor in Breakdown */}
                              {(row.is_exculpatory || row.clearing_factor_note) && (
                                <div className="mt-1.5 flex items-start gap-1 p-1.5 rounded-md bg-emerald-50 border border-emerald-300 text-emerald-900 text-[10px]">
                                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                                  <div>
                                    <span className="font-bold block uppercase tracking-wider text-[9px] text-emerald-800">
                                      Clearing Factor
                                    </span>
                                    <span>{row.clearing_factor_note || 'Exculpatory exclusion clearing suspect'}</span>
                                  </div>
                                </div>
                              )}
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
                              {row.lr_source_citation && (
                                <div className="mt-1 text-[9px] font-mono text-[#8c8276] italic">
                                  Ref: {row.lr_source_citation} {row.lr_error_rate ? `• Error: ${row.lr_error_rate}` : ''}
                                </div>
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
                              {row.shrinkage_factor_alpha !== undefined && (
                                <div className="text-[10px] text-emerald-700">
                                  α = {row.shrinkage_factor_alpha.toFixed(2)}
                                </div>
                              )}
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

                            {/* Diagnosticity */}
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

                            {/* Signed Contribution */}
                            <td className="p-3 align-top font-mono font-bold text-sm">
                              <span className={row.contribution > 0 ? "text-emerald-700" : row.contribution < 0 ? "text-rose-700" : "text-stone-500"}>
                                {row.contribution > 0 ? `+${row.contribution.toFixed(2)}` : row.contribution.toFixed(2)}
                              </span>
                            </td>

                            {/* Share of Support */}
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

                            {/* Forensic LR & WoE */}
                            <td className="p-3 align-top font-mono">
                              {row.likelihood_ratio || row.base_lr ? (
                                <div className="space-y-0.5">
                                  <div className="font-bold text-blue-900 text-xs">
                                    {(row.likelihood_ratio ?? row.base_lr ?? 1.0) > 1e4 ? (row.likelihood_ratio ?? row.base_lr ?? 1.0).toExponential(1) : (row.likelihood_ratio ?? row.base_lr ?? 1.0)}×
                                    <span className="text-[10px] font-normal text-emerald-700 ml-1">
                                      (Eff: {(row.effective_lr ?? 1.0).toFixed(2)}×)
                                    </span>
                                  </div>
                                  <div className={cn(
                                    "text-[10px] font-bold",
                                    (row.weight_of_evidence_bans ?? 0) > 0 ? "text-emerald-700" : (row.weight_of_evidence_bans ?? 0) < 0 ? "text-rose-700" : "text-stone-500"
                                  )}>
                                    {(row.weight_of_evidence_bans ?? 0) > 0 ? `+${(row.weight_of_evidence_bans ?? 0).toFixed(1)}` : (row.weight_of_evidence_bans ?? 0).toFixed(1)} dB
                                  </div>
                                </div>
                              ) : (
                                <span className="text-stone-400 text-[10px]">Heuer Standard</span>
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

            {/* TAB 2: BACKGROUND CONTRIBUTIONS */}
            {breakdownTab === 'background' && (
              <div className="space-y-4">
                <div className="p-4 rounded-2xl bg-amber-50/70 border border-amber-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-amber-900">
                      background plausibility (Layer 2)
                    </div>
                    <div className="text-2xl font-mono font-bold text-amber-950 mt-1">
                      {hypBaseBg.toFixed(1)}%
                    </div>
                    <p className="text-xs text-amber-900 mt-1">
                      Baseline candidate prior formulated from opportunity, access, means, motive, alibi verification, and transit feasibility before case exhibits.
                    </p>
                  </div>
                  <Link
                    to={`/cases/${caseId}/suspects`}
                    className="px-4 py-2 rounded-full bg-[#191410] hover:bg-[#d93829] text-white text-xs font-bold transition-all shrink-0 flex items-center gap-1.5 self-start sm:self-auto"
                  >
                    <UserCheck className="w-3.5 h-3.5" />
                    <span>Full Suspect Profile Page →</span>
                  </Link>
                </div>

                {/* Factor Grid */}
                <div className="border border-[#eae4d9] rounded-2xl p-4 bg-[#faf7f2] space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-serif font-bold text-sm text-[#191410]">
                      Candidate Background Factor Weighting
                    </h4>
                    <span className="text-[10px] font-mono text-[#8c8276]">
                      Calibrated in Scoring Config
                    </span>
                  </div>

                  {(breakdownModalHyp as any).background_factors ? (
                    <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 font-mono text-xs">
                      {Object.entries((breakdownModalHyp as any).background_factors).map(([factor, val]: any) => (
                        <div key={factor} className="p-3 bg-white rounded-xl border border-[#eae4d9] text-center shadow-xs">
                          <div className="text-[10px] uppercase font-bold text-[#8c8276] truncate">
                            {factor.replace(/_/g, ' ')}
                          </div>
                          <div className="text-base font-bold text-[#191410] mt-1">
                            {typeof val === 'number' ? `${(val * 100).toFixed(0)}%` : String(val)}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-[#6e665d] italic">
                      No discrete factor ratings logged. Baseline neutral prior (50.0%) assumed.
                    </p>
                  )}
                </div>

                {/* Exculpatory Background & Alibi Exhibits */}
                <div className="p-4 rounded-2xl bg-white border border-[#eae4d9] space-y-2">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-600" />
                    <h4 className="font-serif font-bold text-sm text-[#191410]">
                      Alibi & Exculpatory Fact Anchors
                    </h4>
                  </div>
                  <p className="text-xs text-[#6e665d] leading-relaxed">
                    Verified alibi evidence discounts background plausibility by up to -90%, preventing unfounded suspicion. Contradicted alibis introduce a +30% multiplier.
                  </p>
                  <div className="pt-2 flex items-center gap-2">
                    <Link
                      to={`/cases/${caseId}/config`}
                      className="text-xs font-mono font-bold text-[#d93829] hover:underline flex items-center gap-1"
                    >
                      <Sliders className="w-3.5 h-3.5" />
                      <span>Adjust Factor Weights & Alibi Discounts in Scoring Configuration →</span>
                    </Link>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 3: HISTORY CONTRIBUTIONS */}
            {breakdownTab === 'history' && (
              <div className="space-y-4">
                {/* Statutory Cap and Safeguard Banner */}
                <div className="p-4 rounded-2xl bg-purple-50 border border-purple-200 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-purple-950 font-serif font-bold text-sm">
                      <Scale className="w-4 h-4 text-purple-700" />
                      <span>Section 54 IEA / Section 52 BSA Character Partition & Statutory Cap</span>
                    </div>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-purple-200 text-purple-900 border border-purple-300">
                      Max Cap: +10.0%
                    </span>
                  </div>
                  <p className="text-xs text-purple-900 leading-relaxed">
                    Prior criminal records are strictly partitioned to prevent character prejudice. 
                    Under statutory rules, history contributions can never exceed +10.0% and cannot overcome contradictory physical exhibits or DNA exclusions.
                  </p>
                </div>

                {/* ON / OFF HISTORY COMPARISON TABLE */}
                <div className="border border-[#eae4d9] rounded-2xl overflow-hidden shadow-xs">
                  <div className="bg-[#f5f0e8] p-3 border-b border-[#eae4d9] flex items-center justify-between">
                    <h4 className="font-serif font-bold text-xs text-[#191410]">
                      On / Off Criminal History Impact Comparison
                    </h4>
                    <span className="text-[10px] font-mono text-[#8c8276]">
                      Real-time toggle stability analysis
                    </span>
                  </div>
                  <table className="w-full text-xs text-left border-collapse">
                    <thead className="bg-[#faf7f2] border-b border-[#eae4d9] font-mono text-[10px] text-[#6e665d] uppercase">
                      <tr>
                        <th className="p-3">Analytical Layer</th>
                        <th className="p-3">With History (ON)</th>
                        <th className="p-3">Without History (OFF)</th>
                        <th className="p-3">Delta Impact (Δ)</th>
                        <th className="p-3">Safeguard Assessment</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#eae4d9] font-mono">
                      <tr className="hover:bg-[#faf7f2]/60">
                        <td className="p-3 font-serif font-bold text-[#191410]">
                          Layer 1: relative support
                        </td>
                        <td className="p-3 font-bold text-blue-900">{hypEvScore.toFixed(1)}%</td>
                        <td className="p-3 font-bold text-blue-900">{hypEvScore.toFixed(1)}%</td>
                        <td className="p-3 text-stone-500">0.0%</td>
                        <td className="p-3 font-sans text-[11px] text-emerald-800 font-semibold">
                          ✓ Fully partitioned (Evidence untouched)
                        </td>
                      </tr>
                      <tr className="hover:bg-[#faf7f2]/60">
                        <td className="p-3 font-serif font-bold text-[#191410]">
                          Layer 2: background plausibility
                        </td>
                        <td className="p-3 font-bold text-amber-900">{hypBaseBg.toFixed(1)}%</td>
                        <td className="p-3 font-bold text-amber-900">{hypBgWithout.toFixed(1)}%</td>
                        <td className="p-3 text-rose-700 font-bold">
                          {hypHistCont > 0 ? `+${(hypHistCont * 100).toFixed(1)}%` : '0.0%'}
                        </td>
                        <td className="p-3 font-sans text-[11px] text-stone-700">
                          {hypHistCont > 0 ? `Capped at +${(Math.min(0.10, hypHistCont) * 100).toFixed(1)}% max` : 'No history boost'}
                        </td>
                      </tr>
                      <tr className="hover:bg-[#faf7f2]/60 bg-emerald-50/30">
                        <td className="p-3 font-serif font-bold text-[#191410]">
                          Layer 3: investigative priority
                        </td>
                        <td className="p-3 font-bold text-emerald-950">{hypBaseComb.toFixed(1)}%</td>
                        <td className="p-3 font-bold text-emerald-950">{hypCombWithout.toFixed(1)}%</td>
                        <td className="p-3 text-rose-700 font-bold">
                          {hypHistCont > 0 ? `+${(hypHistCont * 100).toFixed(1)}%` : '0.0%'}
                        </td>
                        <td className="p-3 font-sans text-[11px] font-semibold text-emerald-900">
                          Rank stability preserved; evidence dominates
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                {/* Role-Restricted Prior Records Section */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-serif font-bold text-sm text-[#191410] flex items-center gap-1.5">
                      <Lock className="w-3.5 h-3.5 text-purple-700" />
                      <span>Role-Restricted Criminal Records for Suspect</span>
                    </h4>
                    <span className="text-[10px] font-mono text-[#8c8276]">
                      Restricted to Lead Investigators & Court Officers
                    </span>
                  </div>

                  {breakdownPriorRestricted ? (
                    <div className="p-5 rounded-2xl bg-stone-100 border border-stone-300 text-stone-800 space-y-2 text-center">
                      <Lock className="w-6 h-6 text-stone-500 mx-auto" />
                      <div className="font-serif font-bold text-sm text-stone-900">
                        Access Restricted Under Section 54 IEA
                      </div>
                      <p className="text-xs text-stone-600 max-w-lg mx-auto">
                        {breakdownRestrictedMsg || 'Prior criminal records are partitioned from analysts and reviewers to prevent confirmation bias and character prejudice. Log in as Lead Investigator or Admin to inspect record details.'}
                      </p>
                    </div>
                  ) : (
                    <div className="border border-[#eae4d9] rounded-2xl overflow-hidden">
                      {breakdownPriorRecords.length > 0 ? (
                        <div className="divide-y divide-[#eae4d9]">
                          {breakdownPriorRecords.map((rec: any, pIdx: number) => (
                            <div key={pIdx} className="p-3.5 bg-white hover:bg-[#faf7f2] transition-colors space-y-1">
                              <div className="flex items-center justify-between">
                                <div className="font-serif font-bold text-xs text-[#191410]">
                                  {rec.offense_title || rec.offense_category || 'Prior Offense'}
                                </div>
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-purple-50 text-purple-800 border border-purple-200">
                                  MO Similarity: {((rec.mo_similarity_score ?? 0.8) * 100).toFixed(0)}%
                                </span>
                              </div>
                              <div className="text-[10px] font-mono text-[#6e665d] flex items-center gap-3">
                                <span>Date: {rec.conviction_date || 'Past Record'}</span>
                                <span>Jurisdiction: {rec.court_jurisdiction || 'State District Court'}</span>
                                <span>Case Ref: {rec.case_reference || 'N/A'}</span>
                              </div>
                              {rec.relevance_reasoning && (
                                <p className="text-[11px] text-[#6e665d] italic mt-1 bg-[#faf7f2] p-2 rounded-lg border border-[#eae4d9]">
                                  Legal Nexus: {rec.relevance_reasoning}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="p-6 text-center text-xs text-[#8c8276] italic bg-white">
                          No prior criminal records recorded for this candidate hypothesis.
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
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
      );
    })()}

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
                  <div className="p-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] text-[#191410] space-y-3 shadow-xs">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Scale className="w-4 h-4 text-[#d93829]" />
                        <span className="font-serif font-bold text-sm text-[#191410]">
                          Simulated Matrix Output ({excludedExhibitIds.length} Exhibits Excluded)
                        </span>
                      </div>
                      {simulating && <Loader2 className="w-4 h-4 animate-spin text-[#d93829]" />}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {simulatedScores && Object.entries(simulatedScores).map(([hId, sData]: any) => {
                        const hInfo = hypotheses.find(h => String(h.id) === String(hId));
                        return (
                          <div key={`sim-${hId}`} className="p-3 rounded-xl bg-white border border-[#eae4d9] text-xs shadow-xs">
                            <div className="font-serif font-bold text-[#191410] truncate">
                              {hInfo?.title || `Hypothesis #${hId}`}
                            </div>
                            <div className="flex items-center justify-between mt-2 font-mono">
                              <span className="text-[#6e665d]">Simulated Likelihood:</span>
                              <span className="text-emerald-700 font-bold text-sm">{sData.support_score}%</span>
                            </div>
                            <div className="flex items-center justify-between text-[11px] font-mono text-[#6e665d]">
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

      {/* Change 2: Suspect Profile Modal */}
      {selectedProfileHyp && caseId && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-200">
          <div className="relative w-full max-w-4xl max-h-[92vh] overflow-y-auto bg-white rounded-3xl shadow-2xl border border-[#eae4d9]">
            <SuspectProfileCard
              caseId={caseId}
              hypothesisId={selectedProfileHyp.id}
              hypothesisTitle={selectedProfileHyp.title}
              backgroundScore={selectedProfileHyp.background_score ?? (selectedProfileHyp as any).backgroundScore ?? 50.0}
              onClose={() => setSelectedProfileHyp(null)}
              onProfileUpdated={loadData}
              onOpenCriminalHistory={() => {
                setSelectedCriminalHistoryHypId(selectedProfileHyp.id);
                setIsCriminalHistoryOpen(true);
              }}
            />
          </div>
        </div>
      )}

      {/* Change 3: Criminal History Module & Safeguards Modal */}
      {isCriminalHistoryOpen && caseId && (
        <CriminalHistoryModal
          caseId={caseId}
          isOpen={isCriminalHistoryOpen}
          selectedHypothesisId={selectedCriminalHistoryHypId}
          onClose={() => {
            setIsCriminalHistoryOpen(false);
            setSelectedCriminalHistoryHypId(null);
          }}
          onHistoryUpdated={() => {
            loadData();
          }}
        />
      )}

      {/* Change 4: Forensic Likelihood Ratio Reference Table Modal */}
      <LikelihoodRatioReferenceModal
        isOpen={isReferenceTableOpen}
        onClose={() => setIsReferenceTableOpen(false)}
        entries={referenceTableEntries}
        onSaveEntry={handleSaveReferenceEntry}
        onResetDefaults={handleResetReferenceTable}
        loading={loadingRefTable}
      />

      {/* Change 5: Evidentiary Dependence & Clearing Factors Modal */}
      <DependencyGroupsModal
        isOpen={isDependencyModalOpen}
        onClose={() => setIsDependencyModalOpen(false)}
        caseId={caseId || ''}
        evidenceList={caseEvidence}
        dependencyData={dependencyGroupsData}
        exculpatoryConfig={exculpatoryConfig}
        onUpdateGroup={handleUpdateExhibitGroup}
        onAutoGroup={handleAutoGroupDependencies}
        loading={loadingDependencyData}
      />

      {/* Change 7: Gaps & Next-Step Suggestions Modal */}
      <GapsAndNextStepsModal
        isOpen={isGapsModalOpen}
        onClose={() => setIsGapsModalOpen(false)}
        caseId={caseId || ''}
        onTaskCreated={() => {
          loadData();
          setNotificationMsg({
            text: 'Investigative task created and synchronized with the Case Investigation Plan.',
            type: 'success'
          });
          setTimeout(() => setNotificationMsg(null), 4000);
        }}
      />

      {/* Decision Quality: Devil's Advocate Counter-Case Modal */}
      {caseId && (
        <DevilsAdvocateModal
          isOpen={isDevilsAdvocateOpen}
          onClose={() => setIsDevilsAdvocateOpen(false)}
          caseId={caseId}
          allHypotheses={hypotheses}
          initialTargetId={devilsAdvocateTargetId}
        />
      )}

      {/* Decision Quality: Two-Analyst Sign-Offs (Four-Eyes Protocol) Modal */}
      {caseId && (
        <DecisionSignoffModal
          isOpen={isSignoffModalOpen}
          onClose={() => setIsSignoffModalOpen(false)}
          caseId={caseId}
          onSignoffUpdated={() => loadData()}
        />
      )}
    </div>
  );
}