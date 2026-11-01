import React, { useState, useEffect, useMemo } from 'react';
import { InvestigativeGap, NextBestStep } from '../../types';
import { scoringService } from '../../services';
import { 
  X, CheckSquare, Sparkles, AlertTriangle, ShieldAlert,
  Loader2, ArrowRight, CheckCircle2, User, ChevronDown, ChevronRight,
  TrendingUp, Zap, HelpCircle, FileCheck, Layers, RefreshCw, Eye
} from 'lucide-react';
import { cn } from '../../utils';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  onTaskCreated?: () => void;
}

const OFFICER_ROSTER = [
  'Lead Investigator',
  'Field Investigation Team',
  'Forensic Science Laboratory (FSL) DNA Division',
  'Digital Surveillance & CCTV Analytics Unit',
  'Cyber Crime Cell & Telecom Intelligence',
  'Fingerprint Bureau CID',
  'Evidence Custodian / Court Liaison',
  'Investigative Analyst'
];

export const GapsAndNextStepsModal: React.FC<Props> = ({
  isOpen,
  onClose,
  caseId,
  onTaskCreated
}) => {
  const [activeTab, setActiveTab] = useState<'gaps' | 'next_steps'>('gaps');
  
  // Gaps state
  const [gaps, setGaps] = useState<InvestigativeGap[]>([]);
  const [loadingGaps, setLoadingGaps] = useState(false);
  const [selectedRuleFilter, setSelectedRuleFilter] = useState<string>('all');
  const [assignedOfficers, setAssignedOfficers] = useState<Record<string, string>>({});
  const [processingGapId, setProcessingGapId] = useState<string | null>(null);

  // Next Best Steps state
  const [nextSteps, setNextSteps] = useState<NextBestStep[]>([]);
  const [loadingNextSteps, setLoadingNextSteps] = useState(false);
  const [expandedStepId, setExpandedStepId] = useState<string | null>(null);
  const [stepAssignedOfficers, setStepAssignedOfficers] = useState<Record<string, string>>({});
  const [processingStepId, setProcessingStepId] = useState<string | null>(null);
  const [acceptedStepIds, setAcceptedStepIds] = useState<Set<string>>(new Set());

  // Load data on open or caseId change
  const loadGaps = async () => {
    if (!caseId) return;
    setLoadingGaps(true);
    try {
      const data = await scoringService.getInvestigativeGaps(caseId);
      setGaps(data);
      // Init assigned officers
      const initialOfficers: Record<string, string> = {};
      data.forEach(g => {
        initialOfficers[g.gap_id] = g.default_assigned_to || 'Lead Investigator';
      });
      setAssignedOfficers(initialOfficers);
    } catch (err) {
      console.error('Failed to load investigative gaps:', err);
    } finally {
      setLoadingGaps(false);
    }
  };

  const loadNextSteps = async () => {
    if (!caseId) return;
    setLoadingNextSteps(true);
    try {
      const data = await scoringService.getNextBestSteps(caseId);
      setNextSteps(data);
      const initialStepOfficers: Record<string, string> = {};
      data.forEach(s => {
        initialStepOfficers[s.step_id] = s.suggested_assigned_to || 'Lead Investigator';
      });
      setStepAssignedOfficers(initialStepOfficers);
      if (data.length > 0 && !expandedStepId) {
        setExpandedStepId(data[0].step_id);
      }
    } catch (err) {
      console.error('Failed to load next best steps:', err);
    } finally {
      setLoadingNextSteps(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadGaps();
      loadNextSteps();
    }
  }, [isOpen, caseId]);

  // Handle Accept Gap as Task
  const handleAcceptGap = async (gap: InvestigativeGap) => {
    setProcessingGapId(gap.gap_id);
    try {
      const assigned = assignedOfficers[gap.gap_id] || gap.default_assigned_to || 'Lead Investigator';
      const created = await scoringService.createTaskFromGap(caseId, {
        task: gap.recommended_task,
        reason: gap.description,
        priority: gap.priority,
        category: 'gap_detection',
        impact_score: gap.severity === 'high' ? 85.0 : 65.0,
        assigned_to: assigned,
        gap_id: gap.gap_id,
        target_id: gap.target_id,
        target_type: gap.target_type
      });

      if (created) {
        setGaps(prev => prev.map(g => g.gap_id === gap.gap_id ? { ...g, is_accepted: true, existing_task_id: parseInt(created.id.replace('TSK-', '')) } : g));
        if (onTaskCreated) onTaskCreated();
      }
    } catch (err) {
      console.error('Failed to accept gap task:', err);
    } finally {
      setProcessingGapId(null);
    }
  };

  // Handle Dismiss Gap
  const handleDismissGap = (gapId: string) => {
    setGaps(prev => prev.map(g => g.gap_id === gapId ? { ...g, is_dismissed: true } : g));
  };

  // Handle Accept Next Best Step as Task
  const handleAcceptStep = async (step: NextBestStep) => {
    setProcessingStepId(step.step_id);
    try {
      const assigned = stepAssignedOfficers[step.step_id] || step.suggested_assigned_to || 'Lead Investigator';
      const created = await scoringService.createTaskFromGap(caseId, {
        task: step.action_title,
        reason: step.description,
        priority: step.recommended_priority,
        category: 'next_best_step',
        impact_score: step.expected_impact,
        assigned_to: assigned,
        gap_id: step.step_id,
        target_id: step.target_hypothesis_id,
        target_type: 'hypothesis'
      });

      if (created) {
        setAcceptedStepIds(prev => new Set(prev).add(step.step_id));
        if (onTaskCreated) onTaskCreated();
      }
    } catch (err) {
      console.error('Failed to accept step task:', err);
    } finally {
      setProcessingStepId(null);
    }
  };

  // Filtered Gaps
  const visibleGaps = useMemo(() => {
    return gaps.filter(g => {
      if (g.is_dismissed) return false;
      if (selectedRuleFilter !== 'all' && g.rule_code !== selectedRuleFilter) return false;
      return true;
    });
  }, [gaps, selectedRuleFilter]);

  const activeGapsCount = useMemo(() => gaps.filter(g => !g.is_dismissed && !g.is_accepted).length, [gaps]);
  const highSeverityCount = useMemo(() => gaps.filter(g => !g.is_dismissed && g.severity === 'high').length, [gaps]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-200">
      <div 
        className="bg-[#faf7f2] border border-[#d8d0c5] rounded-3xl w-full max-w-5xl shadow-2xl overflow-hidden my-auto max-h-[92vh] flex flex-col animate-in zoom-in-95 duration-200"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-[#eae4d9] bg-white flex flex-col md:flex-row md:items-center justify-between gap-4 shrink-0">
          <div>
            <div className="text-[11px] font-mono tracking-widest text-[#d93829] uppercase font-bold mb-1 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-[#d93829]" />
              <span>Investigative Intelligence & Trial Readiness</span>
            </div>
            <h2 className="text-xl md:text-2xl font-serif font-bold text-[#191410] flex items-center gap-3">
              <span>Missing Evidence Needed to Arrest & Next Steps</span>
              {activeGapsCount > 0 && (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-rose-100 text-rose-800 border border-rose-300">
                  {activeGapsCount} Gaps Active
                </span>
              )}
            </h2>
            <p className="text-xs text-[#6e665d] mt-1 max-w-2xl leading-relaxed">
              Procedural checks and evidence simulations that guide investigators on exactly what proof is needed to secure charges or clear suspects.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                if (activeTab === 'gaps') loadGaps();
                else loadNextSteps();
              }}
              className="p-2 rounded-full hover:bg-[#eae4d9] text-[#6e665d] hover:text-[#191410] transition-colors cursor-pointer"
              title="Refresh intelligence data"
            >
              <RefreshCw className={cn("w-4 h-4", (loadingGaps || loadingNextSteps) && "animate-spin text-[#d93829]")} />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-full hover:bg-[#eae4d9] text-[#6e665d] hover:text-[#191410] transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-[#eae4d9] bg-[#f5f0e8] px-6 gap-2 shrink-0">
          <button
            onClick={() => setActiveTab('gaps')}
            className={cn(
              "px-5 py-3 text-xs font-serif font-bold transition-all border-b-2 cursor-pointer flex items-center gap-2",
              activeTab === 'gaps'
                ? "border-[#d93829] text-[#d93829] bg-white rounded-t-xl shadow-2xs"
                : "border-transparent text-[#6e665d] hover:text-[#191410]"
            )}
          >
            <ShieldAlert className="w-4 h-4" />
            <span>Alibi & Forensic Gaps ({gaps.filter(g => !g.is_dismissed).length})</span>
            {highSeverityCount > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold bg-rose-500 text-white">
                {highSeverityCount} High
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('next_steps')}
            className={cn(
              "px-5 py-3 text-xs font-serif font-bold transition-all border-b-2 cursor-pointer flex items-center gap-2",
              activeTab === 'next_steps'
                ? "border-[#d93829] text-[#d93829] bg-white rounded-t-xl shadow-2xs"
                : "border-transparent text-[#6e665d] hover:text-[#191410]"
            )}
          >
            <Zap className="w-4 h-4" />
            <span>Evidence Simulations to Confirm Guilt ({nextSteps.length})</span>
            {nextSteps.some(s => s.can_flip_rank) && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold bg-amber-500 text-white">
                Can Flip #1
              </span>
            )}
          </button>
        </div>

        {/* Tab 1: Investigative Gaps */}
        {activeTab === 'gaps' && (
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Quick Rules Legend & Filter */}
            <div className="p-4 rounded-2xl bg-white border border-[#eae4d9] shadow-xs flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-serif font-bold text-[#191410]">Rule Filter:</span>
                {[
                  { key: 'all', label: 'All Rules' },
                  { key: 'GAP_NO_ALIBI_OR_FORENSIC', label: 'No Alibi/Forensic' },
                  { key: 'GAP_MISSING_CUSTODY_OR_SEC65B', label: 'Custody / Sec 65B' },
                  { key: 'GAP_UNCORROBORATED_STATEMENT', label: 'Uncorroborated Statement' },
                  { key: 'GAP_MISSING_TIMELINE_COVERAGE', label: 'Timeline Telemetry' },
                  { key: 'GAP_SINGLE_SUPPORTING_EXHIBIT', label: 'Single Supporting Exhibit' },
                ].map(rf => (
                  <button
                    key={rf.key}
                    onClick={() => setSelectedRuleFilter(rf.key)}
                    className={cn(
                      "px-3 py-1 rounded-full text-[11px] font-mono transition-all cursor-pointer border",
                      selectedRuleFilter === rf.key
                        ? "bg-[#191410] text-white border-[#191410] font-bold shadow-xs"
                        : "bg-[#faf7f2] hover:bg-[#eae4d9] text-[#6e665d] border-[#eae4d9]"
                    )}
                  >
                    {rf.label}
                  </button>
                ))}
              </div>

              <div className="text-[11px] font-mono text-[#8c8276]">
                Showing {visibleGaps.length} of {gaps.length} detected gaps
              </div>
            </div>

            {/* Loading Gaps */}
            {loadingGaps && (
              <div className="py-16 text-center">
                <Loader2 className="w-8 h-8 animate-spin text-[#d93829] mx-auto mb-2" />
                <p className="text-xs font-mono text-[#8c8276]">Running automated evidentiary gap rules...</p>
              </div>
            )}

            {/* Empty Gaps */}
            {!loadingGaps && visibleGaps.length === 0 && (
              <div className="py-16 text-center border border-dashed border-[#eae4d9] bg-white rounded-3xl">
                <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
                <h3 className="text-base font-serif font-bold text-[#191410]">No Investigative Gaps Detected</h3>
                <p className="text-xs text-[#6e665d] mt-1 max-w-md mx-auto">
                  All 5 rule checks passed: suspects have forensic comparisons, key exhibits have custody/65B certificates, and timeline telemetry is corroborated.
                </p>
              </div>
            )}

            {/* Gap Cards */}
            {!loadingGaps && visibleGaps.length > 0 && (
              <div className="space-y-4">
                {visibleGaps.map(gap => {
                  const isAccepted = gap.is_accepted;
                  const isHigh = gap.severity === 'high';
                  const isProcessing = processingGapId === gap.gap_id;

                  return (
                    <div 
                      key={gap.gap_id}
                      className={cn(
                        "p-5 rounded-2xl bg-white border transition-all shadow-xs",
                        isHigh ? "border-l-4 border-l-rose-500 border-[#eae4d9]" : "border-l-4 border-l-amber-500 border-[#eae4d9]",
                        isAccepted && "bg-emerald-50/40 border-emerald-300"
                      )}
                    >
                      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                        <div className="space-y-2 flex-1">
                          {/* Tags */}
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className={cn(
                              "px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider border",
                              isHigh ? "bg-rose-50 text-rose-800 border-rose-200" : "bg-amber-50 text-amber-800 border-amber-200"
                            )}>
                              {gap.severity.toUpperCase()} Priority
                            </span>
                            <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-[#faf7f2] text-[#6e665d] border border-[#eae4d9]">
                              {gap.rule_code}
                            </span>
                            {gap.target_title && (
                              <span className="px-2 py-0.5 rounded-md text-[10px] font-mono text-[#191410] bg-[#f5f0e8] border border-[#d8d0c5]">
                                Target: {gap.target_title}
                              </span>
                            )}
                          </div>

                          {/* Title & Description */}
                          <h4 className="text-base font-serif font-bold text-[#191410]">
                            {gap.rule_title}
                          </h4>
                          <p className="text-xs text-[#6e665d] leading-relaxed">
                            {gap.description}
                          </p>

                          {/* Recommended Task */}
                          <div className="p-3 rounded-xl bg-[#faf7f2] border border-[#eae4d9] flex items-start gap-2.5">
                            <CheckSquare className="w-4 h-4 text-[#d93829] shrink-0 mt-0.5" />
                            <div>
                              <div className="text-[10px] font-mono uppercase font-bold text-[#8c8276]">Recommended Remediation Task:</div>
                              <div className="text-xs font-semibold text-[#191410] mt-0.5">{gap.recommended_task}</div>
                            </div>
                          </div>
                        </div>

                        {/* Actions & Assignment */}
                        <div className="shrink-0 flex flex-col gap-2.5 md:w-64 pt-1">
                          {/* Assign to */}
                          <div>
                            <label className="block text-[10px] font-mono uppercase text-[#8c8276] mb-1 flex items-center gap-1">
                              <User className="w-3 h-3" />
                              <span>Assign Officer / Cell:</span>
                            </label>
                            <select
                              value={assignedOfficers[gap.gap_id] || gap.default_assigned_to}
                              onChange={e => setAssignedOfficers({ ...assignedOfficers, [gap.gap_id]: e.target.value })}
                              disabled={isAccepted || isProcessing}
                              className="w-full text-xs bg-[#faf7f2] border border-[#d8d0c5] rounded-xl px-2.5 py-1.5 text-[#191410] focus:ring-1 focus:ring-[#d93829] disabled:opacity-60 cursor-pointer"
                            >
                              {OFFICER_ROSTER.map(officer => (
                                <option key={officer} value={officer}>{officer}</option>
                              ))}
                            </select>
                          </div>

                          {/* Action Buttons */}
                          <div className="flex items-center gap-2">
                            {isAccepted ? (
                              <div className="flex-1 py-2 px-3 rounded-xl bg-emerald-100 text-emerald-800 border border-emerald-300 text-xs font-mono font-bold flex items-center justify-center gap-1.5">
                                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                                <span>Accepted as Task</span>
                              </div>
                            ) : (
                              <>
                                <button
                                  onClick={() => handleAcceptGap(gap)}
                                  disabled={isProcessing}
                                  className="flex-1 py-2 px-3 rounded-xl bg-[#191410] hover:bg-[#d93829] text-white text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-xs disabled:opacity-50"
                                >
                                  {isProcessing ? (
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                  ) : (
                                    <CheckSquare className="w-3.5 h-3.5" />
                                  )}
                                  <span>Accept as Task</span>
                                </button>
                                <button
                                  onClick={() => handleDismissGap(gap.gap_id)}
                                  disabled={isProcessing}
                                  className="py-2 px-3 rounded-xl bg-[#faf7f2] hover:bg-[#eae4d9] text-[#6e665d] border border-[#eae4d9] text-xs font-bold transition-all cursor-pointer"
                                  title="Dismiss this gap suggestion"
                                >
                                  Dismiss
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Next Best Step Simulations */}
        {activeTab === 'next_steps' && (
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Explanatory Banner */}
            <div className="p-4 rounded-2xl bg-amber-50/70 border border-amber-200 text-xs text-amber-950 flex items-start gap-3 shadow-xs">
              <Zap className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <span className="font-serif font-bold text-sm block">
                  Bayesian Candidate Step Simulation
                </span>
                <p className="text-amber-900 leading-relaxed">
                  For top competing suspects, candidate tests (DNA, CCTV Biometrics, CDR Triangulation, Latent Friction Ridge ACE-V, Alibi Verification) are simulated through the Bayesian scoring engine across positive match, exclusion, and inconclusive outcomes. Steps are ranked by expected impact and rank mobility.
                </p>
              </div>
            </div>

            {/* Loading Next Steps */}
            {loadingNextSteps && (
              <div className="py-16 text-center">
                <Loader2 className="w-8 h-8 animate-spin text-[#d93829] mx-auto mb-2" />
                <p className="text-xs font-mono text-[#8c8276]">Simulating candidate investigative exhibits...</p>
              </div>
            )}

            {/* Empty Next Steps */}
            {!loadingNextSteps && nextSteps.length === 0 && (
              <div className="py-16 text-center border border-dashed border-[#eae4d9] bg-white rounded-3xl">
                <Sparkles className="w-12 h-12 text-[#b0a89d] mx-auto mb-3" />
                <h3 className="text-base font-serif font-bold text-[#191410]">No Next Steps Required</h3>
                <p className="text-xs text-[#6e665d] mt-1 max-w-md mx-auto">
                  Either only one hypothesis exists or the existing evidence already provides decisive separation.
                </p>
              </div>
            )}

            {/* Steps List */}
            {!loadingNextSteps && nextSteps.length > 0 && (
              <div className="space-y-4">
                {nextSteps.map((step, idx) => {
                  const isExpanded = expandedStepId === step.step_id;
                  const isAccepted = acceptedStepIds.has(step.step_id);
                  const isProcessing = processingStepId === step.step_id;

                  return (
                    <div 
                      key={step.step_id}
                      className={cn(
                        "rounded-2xl bg-white border transition-all shadow-xs overflow-hidden",
                        step.can_flip_rank ? "border-amber-300 ring-1 ring-amber-400/20" : "border-[#eae4d9]",
                        isAccepted && "bg-emerald-50/40 border-emerald-300"
                      )}
                    >
                      {/* Step Header Card */}
                      <div className="p-5">
                        <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
                          <div className="space-y-2 flex-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-mono text-xs font-bold text-white bg-[#191410] px-2.5 py-0.5 rounded-full shrink-0">
                                Priority #{idx + 1}
                              </span>
                              {step.can_flip_rank && (
                                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-100 text-amber-900 border border-amber-300 flex items-center gap-1 shrink-0">
                                  <Zap className="w-3 h-3 text-amber-700" />
                                  <span>Can Flip Lead (#1)</span>
                                </span>
                              )}
                              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase bg-blue-50 text-blue-800 border border-blue-200">
                                {step.action_type.replace(/_/g, ' ')}
                              </span>
                              {step.target_hypothesis_title && (
                                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono text-[#191410] bg-[#faf7f2] border border-[#d8d0c5]">
                                  Target Suspect: {step.target_hypothesis_title}
                                </span>
                              )}
                            </div>

                            <h4 className="text-base font-serif font-bold text-[#191410]">
                              {step.action_title}
                            </h4>
                            <p className="text-xs text-[#6e665d] leading-relaxed">
                              {step.description}
                            </p>
                          </div>

                          {/* Impact Metric & Quick Actions */}
                          <div className="shrink-0 flex flex-col gap-2 lg:w-72 lg:items-end">
                            <div className="flex items-center gap-3">
                              <div className="text-right">
                                <div className="text-[10px] font-mono uppercase font-bold text-[#8c8276]">Expected Impact</div>
                                <div className="text-xl font-mono font-black text-[#191410]">{step.expected_impact}/100</div>
                              </div>
                              <div className="w-20 bg-[#f0ebe1] h-2.5 rounded-full overflow-hidden">
                                <div 
                                  className={cn(
                                    "h-full rounded-full",
                                    step.expected_impact >= 70 ? "bg-rose-500" : (step.expected_impact >= 40 ? "bg-amber-500" : "bg-blue-500")
                                  )}
                                  style={{ width: `${Math.min(100, step.expected_impact)}%` }}
                                />
                              </div>
                            </div>

                            <div className="w-full flex items-center gap-2 mt-1">
                              {isAccepted ? (
                                <div className="flex-1 py-1.5 px-3 rounded-xl bg-emerald-100 text-emerald-800 border border-emerald-300 text-xs font-mono font-bold flex items-center justify-center gap-1.5">
                                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                                  <span>Accepted Task</span>
                                </div>
                              ) : (
                                <button
                                  onClick={() => handleAcceptStep(step)}
                                  disabled={isProcessing}
                                  className="flex-1 py-2 px-3 rounded-xl bg-[#191410] hover:bg-[#d93829] text-white text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-xs disabled:opacity-50"
                                >
                                  {isProcessing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckSquare className="w-3.5 h-3.5" />}
                                  <span>Accept as Task</span>
                                </button>
                              )}

                              <button
                                onClick={() => setExpandedStepId(isExpanded ? null : step.step_id)}
                                className="px-3 py-2 rounded-xl bg-[#faf7f2] hover:bg-[#eae4d9] text-[#191410] border border-[#eae4d9] text-xs font-bold transition-all flex items-center gap-1 cursor-pointer"
                              >
                                <span>Simulations</span>
                                {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                              </button>
                            </div>
                          </div>
                        </div>

                        {/* Expandable Simulated Outcomes Accordion */}
                        {isExpanded && step.simulated_outcomes && (
                          <div className="mt-4 pt-4 border-t border-[#eae4d9] space-y-2 animate-in fade-in duration-150">
                            <div className="text-[11px] font-mono font-bold uppercase text-[#8c8276] mb-2 flex items-center gap-1.5">
                              <TrendingUp className="w-3.5 h-3.5 text-[#d93829]" />
                              <span>Simulated Bayesian Scoring Outcomes for this Test:</span>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                              {step.simulated_outcomes.map((out, oIdx) => (
                                <div 
                                  key={oIdx}
                                  className={cn(
                                    "p-3 rounded-xl border text-xs space-y-1.5",
                                    out.rank_flipped ? "bg-rose-50/70 border-rose-200" : "bg-[#faf7f2] border-[#eae4d9]"
                                  )}
                                >
                                  <div className="flex items-center justify-between gap-1">
                                    <span className="font-serif font-bold text-[#191410]">{out.outcome_label}</span>
                                    {out.rank_flipped && (
                                      <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-rose-200 text-rose-900">
                                        Flips #1
                                      </span>
                                    )}
                                  </div>
                                  <div className="font-mono text-sm font-bold text-[#191410]">
                                    Target Score: {out.target_score.toFixed(1)}% 
                                    <span className={cn("ml-1 text-xs", out.score_delta > 0 ? "text-emerald-700" : "text-stone-500")}>
                                      (Δ {out.score_delta.toFixed(1)}%)
                                    </span>
                                  </div>
                                  <div className="text-[11px] text-[#6e665d] leading-snug">
                                    #1 Suspect: <span className="font-bold text-[#191410]">{out.new_rank_1_title}</span>
                                  </div>
                                </div>
                              ))}
                            </div>

                            <div className="mt-2 text-[10px] font-mono text-[#8c8276] flex items-center justify-between">
                              <span>Assigned to: {step.suggested_assigned_to}</span>
                              <span>Max Score Delta: ±{step.max_score_delta.toFixed(1)}%</span>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Modal Footer */}
        <div className="p-4 border-t border-[#eae4d9] bg-white flex items-center justify-between gap-4 shrink-0 text-xs text-[#8c8276]">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>Interactive Task Integration Active • Accepted tasks automatically appear in the Case Investigation Plan.</span>
          </div>
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-full bg-[#191410] hover:bg-[#2e261f] text-white font-bold transition-all cursor-pointer shadow-xs"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
