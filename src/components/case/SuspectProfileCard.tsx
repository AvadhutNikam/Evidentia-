import React, { useState, useEffect } from 'react';
import { 
  UserCheck, Shield, Sparkles, AlertTriangle, CheckCircle2, 
  MapPin, Clock, Key, Wrench, HeartHandshake, FileText, 
  Plus, Trash2, ArrowUpRight, ArrowDownRight, Minus, 
  Loader2, ExternalLink, X, Info, Check, ShieldCheck,
  Scale, ShieldAlert
} from 'lucide-react';
import { SuspectProfileFactor, SuspectProfileResponse, PriorRecordsResponse } from '../../types';
import { suspectProfileService, priorRecordService } from '../../services';
import { CriminalHistoryModal } from './CriminalHistoryModal';
import { cn } from '../../utils';

interface SuspectProfileCardProps {
  caseId: string;
  hypothesisId: string | number;
  hypothesisTitle: string;
  backgroundScore: number;
  onProfileUpdated?: () => void;
  onClose?: () => void;
  onOpenCriminalHistory?: () => void;
}

export function SuspectProfileCard({
  caseId,
  hypothesisId,
  hypothesisTitle,
  backgroundScore,
  onProfileUpdated,
  onClose,
  onOpenCriminalHistory
}: SuspectProfileCardProps) {
  const [profileData, setProfileData] = useState<SuspectProfileResponse | null>(null);
  const [priorRecordsData, setPriorRecordsData] = useState<PriorRecordsResponse | null>(null);
  const [isCriminalHistoryOpen, setIsCriminalHistoryOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [isAddingFactor, setIsAddingFactor] = useState(false);
  const [notification, setNotification] = useState<{ msg: string; type: 'success' | 'info' | 'error' } | null>(null);

  // New factor form state
  const [newFactorType, setNewFactorType] = useState('access');
  const [newFactorValue, setNewFactorValue] = useState('direct_physical_access');
  const [newFactorNote, setNewFactorNote] = useState('');
  const [newFactorExhibit, setNewFactorExhibit] = useState('');

  const loadProfile = async () => {
    try {
      setLoading(true);
      const [res, priorRes] = await Promise.all([
        suspectProfileService.getSuspectProfile(caseId, hypothesisId),
        priorRecordService.getPriorRecords(caseId, hypothesisId).catch(() => null)
      ]);
      setProfileData(res);
      if (priorRes) {
        setPriorRecordsData(priorRes);
      }
    } catch (err) {
      console.error('Failed to load suspect profile:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, [caseId, hypothesisId]);

  const showToast = (msg: string, type: 'success' | 'info' | 'error' = 'success') => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const handleTriggerAISuggestions = async () => {
    try {
      setActionLoading('ai_suggest');
      const res = await suspectProfileService.triggerAISuggestions(caseId, hypothesisId);
      if (res) {
        showToast('AI analyzed case exhibits and generated profile suggestions. Please review and confirm.', 'info');
        await loadProfile();
        if (onProfileUpdated) onProfileUpdated();
      }
    } catch (err) {
      console.error('AI suggest error:', err);
      showToast('Failed to generate AI suggestions', 'error');
    } finally {
      setActionLoading(null);
    }
  };

  const handleConfirmFactor = async (factorId: string | number) => {
    try {
      setActionLoading(`confirm_${factorId}`);
      await suspectProfileService.confirmFactor(caseId, hypothesisId, factorId);
      showToast('Factor verified and signed off by investigator.');
      await loadProfile();
      if (onProfileUpdated) onProfileUpdated();
    } catch (err) {
      console.error('Confirm factor error:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleConfirmAll = async () => {
    if (!profileData?.factors) return;
    try {
      setActionLoading('confirm_all');
      for (const f of profileData.factors) {
        if (!f.is_confirmed) {
          await suspectProfileService.confirmFactor(caseId, hypothesisId, f.id);
        }
      }
      showToast('All suspect factors confirmed with human investigator sign-off.');
      await loadProfile();
      if (onProfileUpdated) onProfileUpdated();
    } catch (err) {
      console.error('Confirm all error:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeleteFactor = async (factorId: string | number) => {
    try {
      setActionLoading(`delete_${factorId}`);
      await suspectProfileService.deleteFactor(caseId, hypothesisId, factorId);
      showToast('Profile factor deleted.');
      await loadProfile();
      if (onProfileUpdated) onProfileUpdated();
    } catch (err) {
      console.error('Delete factor error:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleSaveNewFactor = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setActionLoading('save_factor');
      await suspectProfileService.createOrUpdateFactor(caseId, hypothesisId, {
        factor_type: newFactorType,
        factor_value: newFactorValue,
        note: newFactorNote,
        source_exhibit_name: newFactorExhibit || undefined,
        entered_by: 'Lead Investigator'
      });
      showToast(`Factor '${newFactorType}' saved with investigator sign-off.`);
      setIsAddingFactor(false);
      setNewFactorNote('');
      setNewFactorExhibit('');
      await loadProfile();
      if (onProfileUpdated) onProfileUpdated();
    } catch (err) {
      console.error('Save factor error:', err);
      showToast('Failed to save factor', 'error');
    } finally {
      setActionLoading(null);
    }
  };

  const getFactorIcon = (type: string) => {
    switch (type) {
      case 'access': return <Key className="w-4 h-4 text-amber-700" />;
      case 'opportunity': return <Clock className="w-4 h-4 text-blue-700" />;
      case 'means': return <Wrench className="w-4 h-4 text-purple-700" />;
      case 'motive': return <HeartHandshake className="w-4 h-4 text-rose-700" />;
      case 'alibi_status': return <Shield className="w-4 h-4 text-emerald-700" />;
      case 'travel_feasibility': return <MapPin className="w-4 h-4 text-teal-700" />;
      default: return <FileText className="w-4 h-4 text-stone-600" />;
    }
  };

  const getEffectBadge = (effect?: string) => {
    switch (effect) {
      case 'raises_prior':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-50 text-amber-900 border border-amber-300">
            <ArrowUpRight className="w-3 h-3 text-amber-700" />
            <span>Raises Prior (↑)</span>
          </span>
        );
      case 'lowers_prior':
      case 'lowers_prior_sharply':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-50 text-emerald-900 border border-emerald-300">
            <ArrowDownRight className="w-3 h-3 text-emerald-700" />
            <span>Lowers Prior (↓)</span>
          </span>
        );
      case 'blocks_impossible':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-rose-50 text-rose-900 border border-rose-300">
            <AlertTriangle className="w-3 h-3 text-rose-700" />
            <span>Blocks / Impossible</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-stone-50 text-stone-700 border border-stone-200">
            <Minus className="w-3 h-3 text-stone-500" />
            <span>Neutral (→)</span>
          </span>
        );
    }
  };

  const relevantRecords = priorRecordsData?.records.filter(
    r => r.effective_weight > 0 && r.computed_mo_similarity >= 0.25 && r.outcome !== 'acquitted' && r.outcome !== 'discharged'
  ) || [];
  const totalHistoryContribution = priorRecordsData?.records.reduce(
    (sum, r) => sum + (r.history_contribution || 0), 0
  ) || 0;
  const historyContributionPct = (totalHistoryContribution * 100).toFixed(1);

  return (
    <div className="bg-white rounded-3xl border border-[#eae4d9] shadow-xl overflow-hidden max-w-4xl w-full mx-auto animate-in fade-in duration-200">
      {/* Header */}
      <div className="p-6 bg-[#faf7f2] border-b border-[#eae4d9]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="text-[11px] font-mono font-bold uppercase tracking-wider text-[#d93829] flex items-center gap-1.5">
              <UserCheck className="w-4 h-4 text-[#d93829]" />
              <span>Suspect Profile & Background Plausibility Prior (Change 2)</span>
            </div>
            <h2 className="text-xl font-serif font-bold text-[#191410] mt-1">
              {hypothesisTitle}
            </h2>
            <p className="text-xs text-[#6e665d] mt-0.5">
              Structured assessment of access, opportunity, means, motive, alibi verification, and travel feasibility converted into baseline prior.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <div className="text-right">
              <div className="text-[10px] font-mono uppercase font-bold text-[#8c8276]">
                Background Plausibility
              </div>
              <div className="text-2xl font-mono font-bold text-amber-900">
                {backgroundScore.toFixed(1)}%
              </div>
            </div>
            {onClose && (
              <button 
                onClick={onClose}
                className="p-2 rounded-full hover:bg-stone-200 text-stone-600 transition-colors cursor-pointer"
                title="Close Profile"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>

        {/* Status & Sign-off Pill */}
        {profileData && (
          <div className="mt-4 flex flex-wrap items-center gap-2.5">
            {profileData.summary.has_human_signoff ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-emerald-100 text-emerald-900 border border-emerald-300">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-700" />
                <span>Human Verified: Investigator Signed Off ({profileData.summary.confirmed_count}/{profileData.summary.total_factors})</span>
              </span>
            ) : profileData.summary.pending_ai_count > 0 ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-amber-100 text-amber-900 border border-amber-300">
                <Sparkles className="w-3.5 h-3.5 text-amber-700" />
                <span>{profileData.summary.pending_ai_count} AI Suggestions Pending Investigator Sign-off</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-stone-100 text-stone-700 border border-stone-200">
                <Info className="w-3.5 h-3.5 text-stone-600" />
                <span>Baseline Profile Active</span>
              </span>
            )}

            <button
              onClick={handleTriggerAISuggestions}
              disabled={actionLoading !== null}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-[#191410] hover:bg-[#2e261f] text-white transition-all cursor-pointer disabled:opacity-50"
              title="Automatically extract suspect factors from case exhibits (CDR, CCTV, statements)"
            >
              {actionLoading === 'ai_suggest' ? <Loader2 className="w-3 h-3 animate-spin text-amber-400" /> : <Sparkles className="w-3 h-3 text-amber-400" />}
              <span>AI Suggest from Exhibits</span>
            </button>

            {profileData.summary.pending_ai_count > 0 && (
              <button
                onClick={handleConfirmAll}
                disabled={actionLoading !== null}
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-emerald-600 hover:bg-emerald-700 text-white transition-all cursor-pointer shadow-xs disabled:opacity-50"
                title="Sign off on all AI suggestions"
              >
                {actionLoading === 'confirm_all' ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
                <span>Confirm All & Sign-Off</span>
              </button>
            )}

            <button
              onClick={() => setIsAddingFactor(!isAddingFactor)}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-white hover:bg-stone-100 text-[#191410] border border-[#d8d0c5] transition-all cursor-pointer"
            >
              <Plus className="w-3 h-3 text-[#d93829]" />
              <span>{isAddingFactor ? 'Cancel Entry' : 'Manual Entry'}</span>
            </button>

            <button
              onClick={() => {
                if (onOpenCriminalHistory) {
                  onOpenCriminalHistory();
                } else {
                  setIsCriminalHistoryOpen(true);
                }
              }}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-[#faf7f2] hover:bg-[#eae4d9] text-[#191410] border border-[#d8d0c5] transition-all cursor-pointer shadow-xs"
              title="Inspect Prior Records, Modus Operandi Similarity, and Safeguards"
            >
              <Scale className="w-3.5 h-3.5 text-purple-700" />
              <span>Prior Records ({priorRecordsData?.records.length || 0})</span>
              {relevantRecords.length > 0 && (
                <span className="px-1.5 py-0.2 rounded-full text-[9px] bg-amber-100 text-amber-900 border border-amber-300 font-bold">
                  +{historyContributionPct}%
                </span>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Notification Toast */}
      {notification && (
        <div className={cn(
          "mx-6 mt-4 p-3 rounded-xl text-xs font-mono font-bold flex items-center justify-between border",
          notification.type === 'success' && "bg-emerald-50 text-emerald-900 border-emerald-300",
          notification.type === 'info' && "bg-blue-50 text-blue-900 border-blue-300",
          notification.type === 'error' && "bg-rose-50 text-rose-900 border-rose-300"
        )}>
          <span>{notification.msg}</span>
          <button onClick={() => setNotification(null)} className="text-stone-400 hover:text-stone-700">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Avoid Double Counting Investigative Notice */}
      <div className="mx-6 mt-4 p-3.5 rounded-2xl bg-amber-50/70 border border-amber-200 text-xs text-amber-950 flex items-start gap-2.5">
        <Info className="w-4 h-4 text-amber-800 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold">Investigative Rule on Avoiding Double Counting: </span>
          <span>
            Post-incident flight, destruction of physical evidence, and false statements during interrogation are subsequent case exhibits, not baseline plausibility. They are scored exclusively in the Evidence Score (Layer 1). This module assesses only pre-existing candidate profile factors.
          </span>
        </div>
      </div>

      {/* Feasibility Check Status Banner */}
      {profileData?.feasibility_check && (
        <div className="mx-6 mt-3 p-3 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-teal-700 shrink-0" />
            <div>
              <span className="font-bold text-[#191410]">Spatiotemporal Feasibility: </span>
              <span className={cn(
                "font-bold",
                profileData.feasibility_check.status === 'physically_feasible' ? "text-emerald-700" :
                profileData.feasibility_check.status === 'borderline' ? "text-amber-700" : "text-rose-700"
              )}>
                {profileData.feasibility_check.status.toUpperCase()}
              </span>
              <span className="text-[#6e665d] ml-1.5">({profileData.feasibility_check.explanation})</span>
            </div>
          </div>
          {profileData.feasibility_check.is_blocked && (
            <span className="px-2 py-0.5 rounded-md bg-rose-100 text-rose-900 text-[10px] font-bold border border-rose-300">
              BLOCKED
            </span>
          )}
        </div>
      )}

      {/* Manual Data Entry Form */}
      {isAddingFactor && (
        <form onSubmit={handleSaveNewFactor} className="mx-6 mt-4 p-4 rounded-2xl bg-[#f5f0e8] border border-[#eae4d9] space-y-3">
          <div className="font-serif font-bold text-sm text-[#191410] flex items-center justify-between">
            <span>Add / Edit Factor with Human Sign-off</span>
            <span className="text-[10px] font-mono text-[#8c8276]">Analyst verification mode</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div>
              <label className="block font-mono font-bold text-[#6e665d] mb-1">Factor Type:</label>
              <select
                value={newFactorType}
                onChange={(e) => {
                  setNewFactorType(e.target.value);
                  if (e.target.value === 'access') setNewFactorValue('direct_physical_access');
                  if (e.target.value === 'opportunity') setNewFactorValue('confirmed_vicinity');
                  if (e.target.value === 'means') setNewFactorValue('standard_physical_capacity');
                  if (e.target.value === 'motive') setNewFactorValue('direct_financial_gain');
                  if (e.target.value === 'alibi_status') setNewFactorValue('none');
                  if (e.target.value === 'travel_feasibility') setNewFactorValue('physically_feasible');
                }}
                className="w-full p-2 bg-white rounded-xl border border-[#d8d0c5] font-mono"
              >
                <option value="access">Access (Victim, premises, vehicle, weapon)</option>
                <option value="opportunity">Opportunity (Presence in time window)</option>
                <option value="means">Means (Skills, tools, physical capacity)</option>
                <option value="motive">Motive & Relationship (Financial, personal)</option>
                <option value="alibi_status">Alibi Status (Verified vs Contradicted)</option>
                <option value="travel_feasibility">Distance & Travel Feasibility</option>
              </select>
            </div>

            <div>
              <label className="block font-mono font-bold text-[#6e665d] mb-1">Categorical Rating:</label>
              <select
                value={newFactorValue}
                onChange={(e) => setNewFactorValue(e.target.value)}
                className="w-full p-2 bg-white rounded-xl border border-[#d8d0c5] font-mono"
              >
                {newFactorType === 'access' && (
                  <>
                    <option value="direct_physical_access">Direct Physical Access (1.00)</option>
                    <option value="key_premises_access">Key / Premises Access (0.85)</option>
                    <option value="vehicle_weapon_access">Vehicle / Weapon Access (0.80)</option>
                    <option value="remote_or_indirect">Remote or Indirect Access (0.45)</option>
                    <option value="none_or_restricted">None / Restricted Access (0.10)</option>
                  </>
                )}
                {newFactorType === 'opportunity' && (
                  <>
                    <option value="confirmed_at_scene">Confirmed Presence at Scene (1.00)</option>
                    <option value="confirmed_vicinity">Confirmed Vicinity by CDR/CCTV (0.80)</option>
                    <option value="unconfirmed_unknown">Unconfirmed / Unknown Baseline (0.50)</option>
                    <option value="confirmed_elsewhere">Confirmed Elsewhere (0.10)</option>
                  </>
                )}
                {newFactorType === 'means' && (
                  <>
                    <option value="specialized_expert">Specialized / Expert Means (1.00)</option>
                    <option value="standard_physical_capacity">Standard Physical Capacity (0.75)</option>
                    <option value="limited_capacity">Limited Capacity / Tools (0.40)</option>
                    <option value="physically_incapable">Physically Incapable (0.05)</option>
                  </>
                )}
                {newFactorType === 'motive' && (
                  <>
                    <option value="direct_financial_gain">Direct Financial Gain (0.95)</option>
                    <option value="personal_enmity_grudge">Personal Enmity / Grudge (0.90)</option>
                    <option value="sexual_predation">Sexual Predation (0.90)</option>
                    <option value="professional_conflict">Professional Dispute (0.70)</option>
                    <option value="secondary_opportunistic">Secondary / Opportunistic (0.50)</option>
                    <option value="none_apparent">None Apparent (0.20)</option>
                  </>
                )}
                {newFactorType === 'alibi_status' && (
                  <>
                    <option value="strongly_verified">Strongly Verified Alibi (0.10x Prior -90%)</option>
                    <option value="partially_verified">Partially Verified Alibi (0.50x Prior -50%)</option>
                    <option value="claimed">Claimed but Unverified (1.00x Neutral)</option>
                    <option value="none">No Alibi Offered (1.00x Neutral)</option>
                    <option value="contradicted">Contradicted Alibi (+30% Suspicion 1.30x)</option>
                  </>
                )}
                {newFactorType === 'travel_feasibility' && (
                  <>
                    <option value="physically_feasible">Physically Feasible (1.00x)</option>
                    <option value="borderline">Borderline / Tight Margin (0.75x)</option>
                    <option value="physically_impossible">Physically Impossible (0.05x Blocked)</option>
                  </>
                )}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div>
              <label className="block font-mono font-bold text-[#6e665d] mb-1">Source Exhibit Name (Citation):</label>
              <input
                type="text"
                placeholder="e.g. CDR Cell Tower Records (Kharadi Sector)"
                value={newFactorExhibit}
                onChange={(e) => setNewFactorExhibit(e.target.value)}
                className="w-full p-2 bg-white rounded-xl border border-[#d8d0c5] font-mono text-xs"
              />
            </div>
            <div>
              <label className="block font-mono font-bold text-[#6e665d] mb-1">Investigative Note / Rationale:</label>
              <input
                type="text"
                placeholder="Rationale explaining candidate assessment..."
                value={newFactorNote}
                onChange={(e) => setNewFactorNote(e.target.value)}
                className="w-full p-2 bg-white rounded-xl border border-[#d8d0c5] font-mono text-xs"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setIsAddingFactor(false)}
              className="px-3 py-1.5 rounded-full text-xs font-mono font-bold text-[#6e665d] hover:bg-stone-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={actionLoading !== null}
              className="px-4 py-1.5 rounded-full text-xs font-mono font-bold bg-[#d93829] hover:bg-[#bf2b1d] text-white shadow-xs cursor-pointer"
            >
              {actionLoading === 'save_factor' ? 'Saving...' : 'Save & Sign Off Factor'}
            </button>
          </div>
        </form>
      )}

      {/* Factor Cards List */}
      <div className="p-6 space-y-3">
        {loading ? (
          <div className="py-12 text-center">
            <Loader2 className="w-6 h-6 animate-spin text-[#d93829] mx-auto mb-2" />
            <p className="text-xs font-mono text-[#8c8276]">Loading suspect profiling factors...</p>
          </div>
        ) : (profileData?.factors.length === 0 && (!priorRecordsData?.records || priorRecordsData.records.length === 0)) ? (
          <div className="py-8 text-center border border-dashed border-[#eae4d9] rounded-2xl bg-[#faf7f2]">
            <UserCheck className="w-8 h-8 text-[#b0a89d] mx-auto mb-2" />
            <p className="text-xs font-mono font-bold text-[#191410]">No structured factors or prior records recorded yet.</p>
            <p className="text-[11px] text-[#6e665d] mt-1">
              Click "AI Suggest from Exhibits" above to extract candidate factors automatically from CDR, CCTV, and statements.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Change 3: Criminal History Module with Safeguards Factor Card */}
            <div 
              className={cn(
                "p-4 rounded-2xl border transition-all relative flex flex-col justify-between",
                relevantRecords.length > 0 
                  ? "bg-amber-50/50 border-amber-300 ring-1 ring-amber-300" 
                  : "bg-white border-[#eae4d9] hover:border-[#d8d0c5]"
              )}
            >
              <div>
                {/* Header line */}
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-1.5 font-mono font-bold text-xs text-[#191410]">
                    <Scale className="w-4 h-4 text-purple-700" />
                    <span>Criminal History Factor (Safeguarded)</span>
                  </div>
                  <div>
                    {relevantRecords.length > 0 ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-100 text-amber-900 border border-amber-300">
                        <ArrowUpRight className="w-3 h-3 text-amber-700" />
                        <span>+{historyContributionPct}% to Prior</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-stone-100 text-stone-600 border border-stone-200">
                        <Minus className="w-3 h-3 text-stone-500" />
                        <span>0.0% (Excluded)</span>
                      </span>
                    )}
                  </div>
                </div>

                {/* Labeled Factor Value Badge */}
                <div className="mb-2">
                  <span className="font-mono text-xs font-bold text-[#191410] px-2 py-1 bg-[#f5f0e8] rounded-md border border-[#eae4d9] block">
                    Similar prior offense: contributes +{historyContributionPct}% to background plausibility
                  </span>
                </div>

                {/* Note & Quoted Tradecraft Description */}
                <div className="text-xs text-[#383129] leading-relaxed mb-2 space-y-1">
                  {relevantRecords.length > 0 ? (
                    <>
                      <p>
                        Matched <span className="font-bold">{relevantRecords.length} verified past offense(s)</span> with modus operandi tradecraft similarity (capped at +10.0% maximum).
                      </p>
                      {relevantRecords[0]?.legal_section && (
                        <div className="text-[11px] font-mono text-[#8c8276]">
                          Section: <span className="font-bold text-[#191410]">{relevantRecords[0].legal_section}</span> • Similarity: <span className="font-bold text-amber-800">{Math.round((relevantRecords[0].computed_mo_similarity || 0) * 100)}%</span>
                        </div>
                      )}
                      {relevantRecords[0]?.quoted_comparison && (
                        <div className="text-[11px] font-serif italic text-[#554d42] bg-[#faf7f2] p-2 rounded-lg border border-[#eae4d9] mt-1">
                          "{relevantRecords[0].quoted_comparison}"
                        </div>
                      )}
                    </>
                  ) : (
                    <p className="text-[#6e665d]">
                      {priorRecordsData?.records && priorRecordsData.records.length > 0
                        ? `${priorRecordsData.records.length} past record(s) on file, but excluded due to lack of method similarity (<25%), acquittal/discharge, or unverified identity.`
                        : 'No prior criminal records imported for this suspect.'}
                    </p>
                  )}
                </div>

                {/* Safeguard Legal Citation */}
                <div className="text-[10px] font-mono text-[#8c8276] flex items-center gap-1.5 mb-2 bg-stone-50 px-2 py-1 rounded-md border border-stone-200">
                  <ShieldAlert className="w-3.5 h-3.5 text-amber-700 shrink-0" />
                  <span className="truncate">Section 54 IEA / Sec 52 BSA: Investigative lead only, never proof of guilt.</span>
                </div>
              </div>

              {/* Footer with action button */}
              <div className="pt-2 border-t border-[#eae4d9] flex items-center justify-between text-[10px] font-mono">
                <span className="text-[#8c8276]">
                  {priorRecordsData?.records.length || 0} record(s) logged
                </span>

                <button
                  onClick={() => {
                    if (onOpenCriminalHistory) {
                      onOpenCriminalHistory();
                    } else {
                      setIsCriminalHistoryOpen(true);
                    }
                  }}
                  className="px-2.5 py-1 rounded-full bg-[#191410] hover:bg-[#2e261f] text-white font-bold flex items-center gap-1 transition-all cursor-pointer shadow-xs"
                  title="Inspect all prior records, judicial outcomes, and tradecraft comparisons"
                >
                  <Scale className="w-3 h-3 text-amber-400" />
                  <span>Inspect Prior Records & MO Analysis</span>
                </button>
              </div>
            </div>

            {profileData?.factors.map((factor) => {
              return (
                <div 
                  key={factor.id} 
                  className={cn(
                    "p-4 rounded-2xl border transition-all relative flex flex-col justify-between",
                    !factor.is_confirmed ? "bg-amber-50/50 border-amber-300 ring-1 ring-amber-300" : "bg-white border-[#eae4d9] hover:border-[#d8d0c5]"
                  )}
                >
                  <div>
                    {/* Header line */}
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-1.5 font-mono font-bold text-xs capitalize text-[#191410]">
                        {getFactorIcon(factor.factor_type)}
                        <span>{factor.factor_type.replace(/_/g, ' ')}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        {getEffectBadge(factor.effect_on_prior)}
                        <button
                          onClick={() => handleDeleteFactor(factor.id)}
                          className="text-stone-300 hover:text-rose-600 p-0.5 transition-colors cursor-pointer"
                          title="Delete factor"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Value Badge */}
                    <div className="mb-2">
                      <span className="font-mono text-xs font-bold text-[#191410] px-2 py-0.5 bg-[#f5f0e8] rounded-md border border-[#eae4d9]">
                        {factor.factor_value.replace(/_/g, ' ')}
                      </span>
                    </div>

                    {/* Note */}
                    {factor.note && (
                      <p className="text-xs text-[#383129] leading-relaxed mb-2">
                        {factor.note}
                      </p>
                    )}

                    {/* Source Exhibit Citation */}
                    {factor.source_exhibit_name && (
                      <div className="text-[11px] font-mono text-[#8c8276] flex items-center gap-1 mb-2">
                        <FileText className="w-3 h-3 text-[#d93829] shrink-0" />
                        <span className="font-medium text-[#191410] truncate">
                          Source: {factor.source_exhibit_name}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Footer: Sign-off & Human Confirmation */}
                  <div className="pt-2 border-t border-[#eae4d9] flex items-center justify-between text-[10px] font-mono">
                    <span className="text-[#8c8276]">
                      Entered by: {factor.entered_by}
                    </span>

                    {!factor.is_confirmed ? (
                      <button
                        onClick={() => handleConfirmFactor(factor.id)}
                        disabled={actionLoading === `confirm_${factor.id}`}
                        className="px-2.5 py-1 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold flex items-center gap-1 transition-all cursor-pointer shadow-xs disabled:opacity-50"
                        title="Investigator confirms AI suggestion"
                      >
                        <Check className="w-3 h-3" />
                        <span>Confirm Sign-off</span>
                      </button>
                    ) : (
                      <span className="text-emerald-800 font-bold flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        <span>Verified</span>
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Criminal History Modal */}
      {isCriminalHistoryOpen && (
        <CriminalHistoryModal
          caseId={caseId}
          isOpen={isCriminalHistoryOpen}
          onClose={() => setIsCriminalHistoryOpen(false)}
          selectedHypothesisId={hypothesisId}
          onHistoryUpdated={async () => {
            await loadProfile();
            if (onProfileUpdated) onProfileUpdated();
          }}
        />
      )}
    </div>
  );
}
