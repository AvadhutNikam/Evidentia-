import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, Shield, ShieldCheck, Scale, AlertTriangle, CheckCircle2, 
  ToggleLeft, ToggleRight, Plus, Trash2, Edit3, X, FileText, 
  ExternalLink, ChevronRight, ArrowUpDown, Info, Loader2, Sparkles, UserCheck
} from 'lucide-react';
import { 
  PriorRecord, 
  CriminalHistoryComparison, 
  CriminalHistoryComparisonHypothesis 
} from '../../types';
import { priorRecordService } from '../../services';
import { cn } from '../../utils';

interface CriminalHistoryModalProps {
  caseId: string;
  isOpen: boolean;
  onClose: () => void;
  onHistoryUpdated?: () => void;
  selectedHypothesisId?: string | number | null;
}

export function CriminalHistoryModal({
  caseId,
  isOpen,
  onClose,
  onHistoryUpdated,
  selectedHypothesisId
}: CriminalHistoryModalProps) {
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [priorRecords, setPriorRecords] = useState<PriorRecord[]>([]);
  const [comparison, setComparison] = useState<CriminalHistoryComparison | null>(null);
  const [activeTab, setActiveTab] = useState<'records' | 'comparison' | 'add'>('records');
  const [selectedHypoFilter, setSelectedHypoFilter] = useState<string>(
    selectedHypothesisId ? String(selectedHypothesisId) : 'all'
  );
  const [editingRecord, setEditingRecord] = useState<PriorRecord | null>(null);
  const [notification, setNotification] = useState<{ msg: string; type: 'success' | 'info' | 'error' } | null>(null);

  // Form State
  const [formSuspectName, setFormSuspectName] = useState('Yogesh Raut');
  const [formHypothesisId, setFormHypothesisId] = useState<number | undefined>(
    selectedHypothesisId ? Number(selectedHypothesisId) : undefined
  );
  const [formOffenseType, setFormOffenseType] = useState('Armed Transit Robbery & Abduction');
  const [formLegalSection, setFormLegalSection] = useState('Section 392, 397 IPC');
  const [formOffenseDate, setFormOffenseDate] = useState('2007-04-18');
  const [formLocation, setFormLocation] = useState('Wagholi-Kharadi Bypass, Pune');
  const [formOutcome, setFormOutcome] = useState('convicted');
  const [formWeapon, setFormWeapon] = useState('Iron rod / jack handle');
  const [formEntry, setFormEntry] = useState('Fake transport / cab route intercept');
  const [formVictimType, setFormVictimType] = useState('Lone female commuter post-evening shift');
  const [formLocationType, setFormLocationType] = useState('Desolate transit bypass / isolated corridor');
  const [formTimePattern, setFormTimePattern] = useState('Late night 21:00-01:00');
  const [formMoDescription, setFormMoDescription] = useState(
    'Suspect and accomplices operated shared vehicle along transit route pretending to offer ride. Subdued victim with iron lever before transporting to isolated bypass.'
  );
  const [formSourceAgency, setFormSourceAgency] = useState('State Criminal Records Bureau (SCRB) Maharashtra');
  const [formSourceDocument, setFormSourceDocument] = useState('Certified Court Judgment #CR-104/2007');
  const [formVerificationStatus, setFormVerificationStatus] = useState('verified');
  const [formIdConfidence, setFormIdConfidence] = useState(0.98);
  const [formVerifiedId, setFormVerifiedId] = useState(true);
  const [formIsJuvenile, setFormIsJuvenile] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [recordsRes, compRes] = await Promise.all([
        priorRecordService.getPriorRecords(caseId),
        priorRecordService.getCriminalHistoryComparison(caseId)
      ]);
      setPriorRecords(recordsRes.records || []);
      setComparison(compRes);
    } catch (err) {
      console.error('Failed to load criminal history data:', err);
      showToast('Error loading criminal history data', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen, caseId]);

  const showToast = (msg: string, type: 'success' | 'info' | 'error' = 'success') => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const handleToggleHistory = async () => {
    try {
      setActionLoading('toggle');
      const newState = !comparison?.include_criminal_history;
      await priorRecordService.toggleCriminalHistory(caseId, newState);
      showToast(`Criminal history signal is now ${newState ? 'ENABLED' : 'DISABLED'}.`);
      await loadData();
      if (onHistoryUpdated) onHistoryUpdated();
    } catch (err: any) {
      console.error('Toggle history error:', err);
      showToast(err.message || 'Failed to toggle criminal history', 'error');
    } finally {
      setActionLoading(null);
    }
  };

  const handleSaveRecord = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setActionLoading('save');
      const payload: Partial<PriorRecord> = {
        suspect_name: formSuspectName,
        hypothesis_id: formHypothesisId || undefined,
        offense_type: formOffenseType,
        legal_section: formLegalSection,
        offense_date: formOffenseDate ? new Date(formOffenseDate).toISOString() : undefined,
        location: formLocation,
        outcome: formOutcome,
        weapon_used: formWeapon,
        entry_method: formEntry,
        victim_type: formVictimType,
        location_type: formLocationType,
        time_pattern: formTimePattern,
        mo_description: formMoDescription,
        source_agency: formSourceAgency,
        source_document: formSourceDocument,
        verification_status: formVerificationStatus,
        identity_match_confidence: formIdConfidence,
        verified_identity: formVerifiedId,
        is_juvenile: formIsJuvenile
      };

      if (editingRecord) {
        await priorRecordService.updatePriorRecord(caseId, editingRecord.id, payload);
        showToast(`Updated prior record #${editingRecord.id}. Scores recomputed.`);
      } else {
        await priorRecordService.createPriorRecord(caseId, payload);
        showToast(`Imported prior record for ${formSuspectName}. Scores recomputed.`);
      }

      setEditingRecord(null);
      setActiveTab('records');
      await loadData();
      if (onHistoryUpdated) onHistoryUpdated();
    } catch (err: any) {
      console.error('Save record error:', err);
      showToast(err.message || 'Failed to save prior record', 'error');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeleteRecord = async (recordId: number) => {
    if (!window.confirm(`Delete prior record #${recordId}? This will immediately update plausibility scores and log to the audit ledger.`)) {
      return;
    }
    try {
      setActionLoading(`delete_${recordId}`);
      await priorRecordService.deletePriorRecord(caseId, recordId);
      showToast(`Record #${recordId} deleted.`);
      await loadData();
      if (onHistoryUpdated) onHistoryUpdated();
    } catch (err: any) {
      console.error('Delete error:', err);
      showToast(err.message || 'Failed to delete record', 'error');
    } finally {
      setActionLoading(null);
    }
  };

  const startEdit = (rec: PriorRecord) => {
    setEditingRecord(rec);
    setFormSuspectName(rec.suspect_name);
    setFormHypothesisId(rec.hypothesis_id || undefined);
    setFormOffenseType(rec.offense_type);
    setFormLegalSection(rec.legal_section || '');
    setFormOffenseDate(rec.offense_date ? rec.offense_date.split('T')[0] : '');
    setFormLocation(rec.location || '');
    setFormOutcome(rec.outcome);
    setFormWeapon(rec.weapon_used || '');
    setFormEntry(rec.entry_method || '');
    setFormVictimType(rec.victim_type || '');
    setFormLocationType(rec.location_type || '');
    setFormTimePattern(rec.time_pattern || '');
    setFormMoDescription(rec.mo_description || '');
    setFormSourceAgency(rec.source_agency);
    setFormSourceDocument(rec.source_document || '');
    setFormVerificationStatus(rec.verification_status);
    setFormIdConfidence(rec.identity_match_confidence ?? 1.0);
    setFormVerifiedId(rec.verified_identity ?? true);
    setFormIsJuvenile(rec.is_juvenile ?? false);
    setActiveTab('add');
  };

  if (!isOpen) return null;

  const filteredRecords = selectedHypoFilter === 'all'
    ? priorRecords
    : priorRecords.filter(r => String(r.hypothesis_id) === selectedHypoFilter);

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-200">
      <div className="relative w-full max-w-5xl max-h-[92vh] overflow-y-auto bg-white rounded-3xl shadow-2xl border border-[#eae4d9] flex flex-col">
        
        {/* Header with Safeguard Notice */}
        <div className="p-6 border-b border-[#eae4d9] bg-[#faf7f2] rounded-t-3xl">
          <div className="flex items-center justify-between gap-4 mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center shrink-0">
                <Scale className="w-5 h-5 text-amber-700" />
              </div>
              <div>
                <h2 className="text-xl font-serif font-bold text-[#191410] flex items-center gap-2">
                  <span>Criminal History Module & Legal Safeguards</span>
                  <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-900 border border-amber-300">
                    Change 3
                  </span>
                </h2>
                <p className="text-xs font-mono text-[#6e665d]">
                  Limited, reviewable signal based on Modus Operandi similarity. Never evidence of guilt.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* On/Off Switch */}
              <button
                onClick={handleToggleHistory}
                disabled={actionLoading === 'toggle'}
                className={cn(
                  "flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-mono font-bold transition-all border cursor-pointer",
                  comparison?.include_criminal_history 
                    ? "bg-emerald-50 text-emerald-900 border-emerald-300 hover:bg-emerald-100" 
                    : "bg-stone-100 text-stone-600 border-stone-300 hover:bg-stone-200"
                )}
                title="Toggle criminal history contribution to background plausibility"
              >
                {actionLoading === 'toggle' ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : comparison?.include_criminal_history ? (
                  <ToggleRight className="w-5 h-5 text-emerald-600" />
                ) : (
                  <ToggleLeft className="w-5 h-5 text-stone-400" />
                )}
                <span>Signal: {comparison?.include_criminal_history ? 'ACTIVE (+10% Cap)' : 'DISABLED (0%)'}</span>
              </button>

              <button
                onClick={onClose}
                className="w-8 h-8 rounded-full bg-white hover:bg-stone-100 border border-stone-200 flex items-center justify-center text-stone-500 hover:text-stone-800 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* PERMANENT MANDATORY LEGAL SAFEGUARD NOTICE BANNER */}
          <div className="p-3.5 rounded-2xl bg-amber-50 border-2 border-amber-300 text-amber-950 text-xs flex items-start gap-3 shadow-xs">
            <ShieldAlert className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <div className="font-serif font-bold text-amber-950 flex items-center gap-2">
                <span>STATUTORY & EVIDENTIARY SAFEGUARD (Section 54 IEA / Section 52 BSA 2023)</span>
                <span className="text-[10px] font-mono px-2 py-0.2 bg-amber-200 text-amber-900 rounded font-bold">
                  MANDATORY NOTICE
                </span>
              </div>
              <p className="text-[11px] leading-relaxed text-amber-900 font-sans">
                <strong>“Prior history is an investigative lead, not evidence of guilt.”</strong> Under statutory evidentiary rules, past character, mere accusation, and prior convictions are inadmissible as substantive proof of the charged offense. Modus operandi similarity is utilized solely to prioritize lines of inquiry. Dissimilar offenses score zero, and total background contribution is strictly capped at +10.0%.
              </p>
            </div>
          </div>
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

        {/* Navigation Tabs */}
        <div className="px-6 pt-4 border-b border-[#eae4d9] flex items-center justify-between">
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('records')}
              className={cn(
                "px-4 py-2 text-xs font-mono font-bold border-b-2 transition-all cursor-pointer",
                activeTab === 'records'
                  ? "border-[#d93829] text-[#191410]"
                  : "border-transparent text-[#8c8276] hover:text-[#191410]"
              )}
            >
              Prior Offense Records ({priorRecords.length})
            </button>

            <button
              onClick={() => setActiveTab('comparison')}
              className={cn(
                "px-4 py-2 text-xs font-mono font-bold border-b-2 transition-all cursor-pointer flex items-center gap-1.5",
                activeTab === 'comparison'
                  ? "border-[#d93829] text-[#191410]"
                  : "border-transparent text-[#8c8276] hover:text-[#191410]"
              )}
            >
              <ArrowUpDown className="w-3.5 h-3.5 text-blue-600" />
              <span>Ranking Comparison (With vs Without History)</span>
            </button>

            <button
              onClick={() => {
                setEditingRecord(null);
                setActiveTab('add');
              }}
              className={cn(
                "px-4 py-2 text-xs font-mono font-bold border-b-2 transition-all cursor-pointer flex items-center gap-1.5",
                activeTab === 'add'
                  ? "border-[#d93829] text-[#191410]"
                  : "border-transparent text-[#8c8276] hover:text-[#191410]"
              )}
            >
              <Plus className="w-3.5 h-3.5 text-[#d93829]" />
              <span>{editingRecord ? 'Edit Record' : 'Manual Record Import'}</span>
            </button>
          </div>

          {activeTab === 'records' && (
            <div className="flex items-center gap-2 pb-2">
              <label className="text-[11px] font-mono text-[#6e665d]">Filter by Suspect:</label>
              <select
                value={selectedHypoFilter}
                onChange={(e) => setSelectedHypoFilter(e.target.value)}
                className="px-2.5 py-1 text-xs font-mono bg-[#f5f0e8] border border-[#d8d0c5] rounded-xl"
              >
                <option value="all">All Suspects</option>
                {comparison?.hypotheses_comparison.map((h) => (
                  <option key={h.hypothesis_id} value={String(h.hypothesis_id)}>
                    {h.title}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* TAB 1: PRIOR RECORDS LIST */}
        {activeTab === 'records' && (
          <div className="p-6 space-y-4">
            {loading ? (
              <div className="py-16 text-center">
                <Loader2 className="w-7 h-7 animate-spin text-[#d93829] mx-auto mb-2" />
                <p className="text-xs font-mono text-[#8c8276]">Evaluating Modus Operandi & Safeguards...</p>
              </div>
            ) : filteredRecords.length === 0 ? (
              <div className="py-12 text-center border border-dashed border-[#eae4d9] rounded-2xl bg-[#faf7f2]">
                <Shield className="w-10 h-10 text-[#b0a89d] mx-auto mb-2" />
                <p className="text-xs font-mono font-bold text-[#191410]">No prior criminal records imported for this suspect.</p>
                <p className="text-[11px] text-[#6e665d] mt-1 max-w-md mx-auto">
                  Click "Manual Record Import" to enter verified prior offense records from SCRB or certified court judgments.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredRecords.map((rec) => {
                  const isConvicted = rec.outcome.toLowerCase() === 'convicted';
                  const isExcludedOutcome = ['acquitted', 'discharged'].includes(rec.outcome.toLowerCase());
                  const isUnverifiedId = !rec.verified_identity || (rec.identity_match_confidence || 1.0) < 0.70;
                  const isJuvenileExcluded = Boolean(rec.is_juvenile);
                  const isExcluded = isExcludedOutcome || isUnverifiedId || isJuvenileExcluded || rec.computed_mo_similarity < 0.25;

                  let breakdownObj: any = {};
                  try {
                    if (rec.similarity_breakdown) breakdownObj = JSON.parse(rec.similarity_breakdown);
                  } catch {}

                  return (
                    <div 
                      key={rec.id}
                      className={cn(
                        "p-5 rounded-2xl border transition-all relative flex flex-col gap-3",
                        isExcluded 
                          ? "bg-stone-50/80 border-stone-200 opacity-80" 
                          : "bg-white border-[#eae4d9] shadow-xs hover:border-[#d8d0c5]"
                      )}
                    >
                      {/* Top row: Offense title, Section, Outcome badge, MO Similarity Badge */}
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="flex items-center gap-2.5">
                          <span className="font-mono text-xs font-bold px-2.5 py-0.5 rounded-md bg-[#191410] text-white">
                            Record #{rec.id}
                          </span>
                          <h4 className="font-serif font-bold text-base text-[#191410]">
                            {rec.offense_type}
                          </h4>
                          {rec.legal_section && (
                            <span className="text-xs font-mono font-bold text-[#6e665d] bg-[#f5f0e8] px-2 py-0.5 rounded border border-[#eae4d9]">
                              {rec.legal_section}
                            </span>
                          )}
                          <span className="text-xs font-serif italic text-stone-500">
                            • Suspect: <strong>{rec.suspect_name}</strong>
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          {/* Outcome Badge */}
                          <span className={cn(
                            "px-2.5 py-0.5 rounded-full text-xs font-mono font-bold border",
                            rec.outcome === 'convicted' && "bg-emerald-50 text-emerald-900 border-emerald-300",
                            rec.outcome === 'pending' && "bg-amber-50 text-amber-900 border-amber-300",
                            rec.outcome === 'merely_accused' && "bg-blue-50 text-blue-900 border-blue-300",
                            isExcludedOutcome && "bg-stone-100 text-stone-600 border-stone-300 line-through"
                          )}>
                            Outcome: {rec.outcome.toUpperCase()} {isConvicted ? '(1.0x)' : isExcludedOutcome ? '(0.0x Excluded)' : '(0.3x)'}
                          </span>

                          {/* MO Similarity Gauge */}
                          <span className={cn(
                            "px-3 py-0.5 rounded-full text-xs font-mono font-bold border flex items-center gap-1",
                            rec.computed_mo_similarity >= 0.60 ? "bg-purple-50 text-purple-900 border-purple-300" :
                            rec.computed_mo_similarity >= 0.25 ? "bg-amber-50 text-amber-900 border-amber-300" :
                            "bg-stone-100 text-stone-600 border-stone-300"
                          )}>
                            <Sparkles className="w-3 h-3 text-purple-600" />
                            <span>MO Match: {Math.round((rec.computed_mo_similarity || 0) * 100)}%</span>
                          </span>

                          {/* Action Buttons */}
                          <button
                            onClick={() => startEdit(rec)}
                            className="p-1 text-stone-400 hover:text-stone-700 transition-colors"
                            title="Edit Record"
                          >
                            <Edit3 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteRecord(rec.id)}
                            className="p-1 text-stone-400 hover:text-rose-600 transition-colors"
                            title="Delete Record"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>

                      {/* Safeguard Exclusion Alert if Applicable */}
                      {isExcluded && (
                        <div className="p-2.5 rounded-xl bg-stone-100 text-stone-800 text-xs font-mono flex items-center gap-2 border border-stone-200">
                          <AlertTriangle className="w-4 h-4 text-stone-500 shrink-0" />
                          <span>
                            <strong>SAFEGUARD EXCLUSION APPLIED: </strong>
                            {isExcludedOutcome ? "Judicial outcome is acquittal/discharge. Admissibility rule strictly excludes from background prior." :
                             isUnverifiedId ? "Identity match unverified or confidence below threshold. Excluded to prevent misattribution." :
                             isJuvenileExcluded ? "Juvenile protection rule: Offense committed during minority excluded by default." :
                             "Dissimilar modus operandi (<25% similarity threshold). Scores zero."}
                          </span>
                        </div>
                      )}

                      {/* Quoted Tradecraft Comparison */}
                      {rec.quoted_comparison && (
                        <div className="p-3.5 rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-xs space-y-2">
                          <div className="font-mono font-bold text-[11px] text-[#6e665d] uppercase tracking-wider flex items-center gap-1">
                            <FileText className="w-3.5 h-3.5 text-[#d93829]" />
                            <span>Quoted Modus Operandi & Tradecraft Comparison:</span>
                          </div>
                          <div className="text-stone-800 whitespace-pre-line leading-relaxed font-sans text-xs">
                            {rec.quoted_comparison}
                          </div>
                        </div>
                      )}

                      {/* Method Dimensions Badges */}
                      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-[11px] font-mono">
                        <div className="p-2 rounded-lg bg-[#f5f0e8] border border-[#eae4d9]">
                          <span className="text-[#8c8276] block text-[9px] uppercase">Weapon / Force</span>
                          <span className="font-bold text-[#191410] truncate block">{rec.weapon_used || 'Unspecified'}</span>
                        </div>
                        <div className="p-2 rounded-lg bg-[#f5f0e8] border border-[#eae4d9]">
                          <span className="text-[#8c8276] block text-[9px] uppercase">Entry / Ambush</span>
                          <span className="font-bold text-[#191410] truncate block">{rec.entry_method || 'Unspecified'}</span>
                        </div>
                        <div className="p-2 rounded-lg bg-[#f5f0e8] border border-[#eae4d9]">
                          <span className="text-[#8c8276] block text-[9px] uppercase">Victim Demographics</span>
                          <span className="font-bold text-[#191410] truncate block">{rec.victim_type || 'Unspecified'}</span>
                        </div>
                        <div className="p-2 rounded-lg bg-[#f5f0e8] border border-[#eae4d9]">
                          <span className="text-[#8c8276] block text-[9px] uppercase">Corridor / Topology</span>
                          <span className="font-bold text-[#191410] truncate block">{rec.location_type || 'Unspecified'}</span>
                        </div>
                        <div className="p-2 rounded-lg bg-[#f5f0e8] border border-[#eae4d9]">
                          <span className="text-[#8c8276] block text-[9px] uppercase">Temporal Pattern</span>
                          <span className="font-bold text-[#191410] truncate block">{rec.time_pattern || 'Unspecified'}</span>
                        </div>
                      </div>

                      {/* Footer: Provenance, Verification, Identity Confidence */}
                      <div className="pt-2 border-t border-[#eae4d9] flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono text-[#6e665d]">
                        <div className="flex items-center gap-3">
                          <span>
                            <strong>Source:</strong> {rec.source_agency} {rec.source_document ? `(${rec.source_document})` : ''}
                          </span>
                          <span className={cn(
                            "px-2 py-0.2 rounded font-bold text-[10px]",
                            rec.verification_status === 'verified' ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"
                          )}>
                            Status: {rec.verification_status.toUpperCase()}
                          </span>
                          <span>
                            <strong>Identity Match:</strong> {Math.round((rec.identity_match_confidence || 1.0) * 100)}%
                          </span>
                        </div>

                        <div className="font-bold text-amber-900 bg-amber-50 px-2.5 py-0.5 rounded border border-amber-200">
                          Net Plausibility Contribution: +{(rec.history_contribution * 100).toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: RANKING COMPARISON TABLE (WITH VS WITHOUT HISTORY) */}
        {activeTab === 'comparison' && (
          <div className="p-6 space-y-4">
            <div className="p-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] flex items-center justify-between">
              <div>
                <h4 className="font-serif font-bold text-sm text-[#191410]">Dual Ranking Comparison Ledger</h4>
                <p className="text-xs text-[#6e665d] font-mono">
                  Inspect how prior criminal records shift candidate plausibility and overall combined priority.
                </p>
              </div>
              <div className="text-xs font-mono bg-white px-3 py-1.5 rounded-xl border border-[#d8d0c5]">
                History Cap: <strong>+10.0% Max Prior Shift</strong>
              </div>
            </div>

            <div className="overflow-x-auto rounded-2xl border border-[#eae4d9]">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-[#f5f0e8] text-[#6e665d] border-b border-[#eae4d9] uppercase text-[10px]">
                  <tr>
                    <th className="p-3">Suspect / Competing Theory</th>
                    <th className="p-3 text-center">Rank (Without)</th>
                    <th className="p-3 text-center">Rank (With)</th>
                    <th className="p-3 text-center">Evidence Score</th>
                    <th className="p-3 text-center">Background (Without)</th>
                    <th className="p-3 text-center">Background (With)</th>
                    <th className="p-3 text-center">Net Hist Boost</th>
                    <th className="p-3 text-center">Combined (Without)</th>
                    <th className="p-3 text-center">Combined (With)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#eae4d9]">
                  {comparison?.hypotheses_comparison.map((h) => {
                    const rankChanged = h.rank_with_history !== h.rank_without_history;
                    return (
                      <tr 
                        key={h.hypothesis_id}
                        className={cn(
                          "hover:bg-[#faf7f2] transition-colors",
                          rankChanged && "bg-amber-50/50"
                        )}
                      >
                        <td className="p-3 font-serif font-bold text-stone-900">
                          {h.title}
                          {rankChanged && (
                            <span className="ml-2 px-1.5 py-0.5 rounded bg-amber-200 text-amber-900 text-[9px] font-mono font-bold">
                              Shifted #{h.rank_without_history} → #{h.rank_with_history}
                            </span>
                          )}
                        </td>
                        <td className="p-3 text-center text-stone-600 font-bold">#{h.rank_without_history}</td>
                        <td className="p-3 text-center font-bold text-[#191410]">
                          <span className={cn(
                            "px-2 py-0.5 rounded-full",
                            h.rank_with_history === 1 ? "bg-emerald-100 text-emerald-800" : "bg-stone-100"
                          )}>
                            #{h.rank_with_history}
                          </span>
                        </td>
                        <td className="p-3 text-center text-blue-900 font-bold">{h.evidence_score.toFixed(1)}%</td>
                        <td className="p-3 text-center text-stone-600">{h.background_without_history.toFixed(1)}%</td>
                        <td className="p-3 text-center text-amber-900 font-bold">{h.background_with_history.toFixed(1)}%</td>
                        <td className="p-3 text-center font-bold">
                          {h.history_contribution_pct > 0 ? (
                            <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                              +{h.history_contribution_pct.toFixed(1)}%
                            </span>
                          ) : (
                            <span className="text-stone-400">0.0%</span>
                          )}
                        </td>
                        <td className="p-3 text-center text-stone-600">{h.combined_without_history.toFixed(1)}%</td>
                        <td className="p-3 text-center text-emerald-900 font-bold">{h.combined_with_history.toFixed(1)}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 3: MANUAL RECORD IMPORT / ENTRY FORM */}
        {activeTab === 'add' && (
          <form onSubmit={handleSaveRecord} className="p-6 space-y-4">
            <div className="p-4 rounded-2xl bg-amber-50/70 border border-amber-200 text-xs text-amber-950 flex items-start gap-2.5">
              <Info className="w-4 h-4 text-amber-800 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">Official Records Source Requirement: </span>
                <span>
                  Only import records from official sources to which the officer is entitled (State Criminal Records Bureau SCRB, CCTNS certified records, or certified court judgments). Live external integration with external live databases is not possessed.
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
              <div>
                <label className="block font-bold text-[#6e665d] mb-1">Suspect Name:</label>
                <input
                  type="text"
                  required
                  value={formSuspectName}
                  onChange={(e) => setFormSuspectName(e.target.value)}
                  className="w-full p-2.5 bg-white rounded-xl border border-[#d8d0c5] font-mono text-xs"
                  placeholder="e.g. Yogesh Raut"
                />
              </div>

              <div>
                <label className="block font-bold text-[#6e665d] mb-1">Target Hypothesis / Competing Candidate:</label>
                <select
                  value={formHypothesisId || ''}
                  onChange={(e) => setFormHypothesisId(e.target.value ? Number(e.target.value) : undefined)}
                  className="w-full p-2.5 bg-white rounded-xl border border-[#d8d0c5] font-mono text-xs"
                >
                  <option value="">Auto-link by Suspect Name</option>
                  {comparison?.hypotheses_comparison.map((h) => (
                    <option key={h.hypothesis_id} value={h.hypothesis_id}>
                      {h.title}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-bold text-[#6e665d] mb-1">Offense Type & Description:</label>
                <input
                  type="text"
                  required
                  value={formOffenseType}
                  onChange={(e) => setFormOffenseType(e.target.value)}
                  className="w-full p-2.5 bg-white rounded-xl border border-[#d8d0c5] font-mono text-xs"
                  placeholder="e.g. Armed Highway Robbery"
                />
              </div>

              <div>
                <label className="block font-bold text-[#6e665d] mb-1">Statutory Section:</label>
                <input
                  type="text"
                  value={formLegalSection}
                  onChange={(e) => setFormLegalSection(e.target.value)}
                  className="w-full p-2.5 bg-white rounded-xl border border-[#d8d0c5] font-mono text-xs"
                  placeholder="e.g. Section 392, 397 IPC"
                />
              </div>

              <div>
                <label className="block font-bold text-[#6e665d] mb-1">Offense Date:</label>
                <input
                  type="date"
                  value={formOffenseDate}
                  onChange={(e) => setFormOffenseDate(e.target.value)}
                  className="w-full p-2.5 bg-white rounded-xl border border-[#d8d0c5] font-mono text-xs"
                />
              </div>

              <div>
                <label className="block font-bold text-[#6e665d] mb-1">Judicial Outcome (Outcome Rule):</label>
                <select
                  value={formOutcome}
                  onChange={(e) => setFormOutcome(e.target.value)}
                  className="w-full p-2.5 bg-white rounded-xl border border-[#d8d0c5] font-mono text-xs font-bold"
                >
                  <option value="convicted">Convicted (Counts most: 1.0x factor)</option>
                  <option value="pending">Pending Trial (Counts little: 0.30x factor)</option>
                  <option value="merely_accused">Merely Accused (Counts little: 0.15x factor)</option>
                  <option value="acquitted">Acquitted (Excluded from prior: 0.0x)</option>
                  <option value="discharged">Discharged (Excluded from prior: 0.0x)</option>
                </select>
              </div>

              <div>
                <label className="block font-bold text-[#6e665d] mb-1">Weapon Used (Method):</label>
                <input
                  type="text"
                  value={formWeapon}
                  onChange={(e) => setFormWeapon(e.target.value)}
                  className="w-full p-2.5 bg-white rounded-xl border border-[#d8d0c5] font-mono text-xs"
                  placeholder="e.g. Iron rod / jack handle"
                />
              </div>

              <div>
                <label className="block font-bold text-[#6e665d] mb-1">Entry / Ambush Method:</label>
                <input
                  type="text"
                  value={formEntry}
                  onChange={(e) => setFormEntry(e.target.value)}
                  className="w-full p-2.5 bg-white rounded-xl border border-[#d8d0c5] font-mono text-xs"
                  placeholder="e.g. Fake transport / cab route intercept"
                />
              </div>

              <div>
                <label className="block font-bold text-[#6e665d] mb-1">Victim Type:</label>
                <input
                  type="text"
                  value={formVictimType}
                  onChange={(e) => setFormVictimType(e.target.value)}
                  className="w-full p-2.5 bg-white rounded-xl border border-[#d8d0c5] font-mono text-xs"
                  placeholder="e.g. Lone female commuter post-evening shift"
                />
              </div>

              <div>
                <label className="block font-bold text-[#6e665d] mb-1">Location Type & Topology:</label>
                <input
                  type="text"
                  value={formLocationType}
                  onChange={(e) => setFormLocationType(e.target.value)}
                  className="w-full p-2.5 bg-white rounded-xl border border-[#d8d0c5] font-mono text-xs"
                  placeholder="e.g. Desolate transit bypass / isolated corridor"
                />
              </div>

              <div>
                <label className="block font-bold text-[#6e665d] mb-1">Time Pattern:</label>
                <input
                  type="text"
                  value={formTimePattern}
                  onChange={(e) => setFormTimePattern(e.target.value)}
                  className="w-full p-2.5 bg-white rounded-xl border border-[#d8d0c5] font-mono text-xs"
                  placeholder="e.g. Late night 21:00-01:00"
                />
              </div>

              <div>
                <label className="block font-bold text-[#6e665d] mb-1">Source Agency & Certified Record:</label>
                <input
                  type="text"
                  required
                  value={formSourceAgency}
                  onChange={(e) => setFormSourceAgency(e.target.value)}
                  className="w-full p-2.5 bg-white rounded-xl border border-[#d8d0c5] font-mono text-xs"
                  placeholder="e.g. State Criminal Records Bureau (SCRB)"
                />
              </div>
            </div>

            <div className="text-xs font-mono">
              <label className="block font-bold text-[#6e665d] mb-1">Modus Operandi Narrative (For Text Comparison):</label>
              <textarea
                rows={3}
                value={formMoDescription}
                onChange={(e) => setFormMoDescription(e.target.value)}
                className="w-full p-2.5 bg-white rounded-xl border border-[#d8d0c5] font-mono text-xs"
                placeholder="Narrative description of the tradecraft and method executed in this prior offense..."
              />
            </div>

            {/* Identity & Safeguard Toggles */}
            <div className="p-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
              <div>
                <label className="block font-bold text-[#6e665d] mb-1">
                  Identity Confidence ({Math.round(formIdConfidence * 100)}%):
                </label>
                <input
                  type="range"
                  min="0.4"
                  max="1.0"
                  step="0.05"
                  value={formIdConfidence}
                  onChange={(e) => setFormIdConfidence(parseFloat(e.target.value))}
                  className="w-full accent-[#d93829]"
                />
              </div>

              <div className="flex items-center gap-2 pt-4">
                <input
                  type="checkbox"
                  id="verifiedIdCheck"
                  checked={formVerifiedId}
                  onChange={(e) => setFormVerifiedId(e.target.checked)}
                  className="w-4 h-4 accent-emerald-600 rounded cursor-pointer"
                />
                <label htmlFor="verifiedIdCheck" className="font-bold text-[#191410] cursor-pointer">
                  Verified Identity Match
                </label>
              </div>

              <div className="flex items-center gap-2 pt-4">
                <input
                  type="checkbox"
                  id="juvenileCheck"
                  checked={formIsJuvenile}
                  onChange={(e) => setFormIsJuvenile(e.target.checked)}
                  className="w-4 h-4 accent-amber-600 rounded cursor-pointer"
                />
                <label htmlFor="juvenileCheck" className="font-bold text-stone-700 cursor-pointer">
                  Juvenile Record (Excluded by Default)
                </label>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3">
              <button
                type="button"
                onClick={() => {
                  setEditingRecord(null);
                  setActiveTab('records');
                }}
                className="px-4 py-2 rounded-full text-xs font-mono font-bold text-[#6e665d] hover:bg-stone-100"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={actionLoading !== null}
                className="px-5 py-2 rounded-full text-xs font-mono font-bold bg-[#d93829] hover:bg-[#bf2b1d] text-white shadow-xs cursor-pointer flex items-center gap-2"
              >
                {actionLoading === 'save' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                <span>{editingRecord ? 'Update Record & Recompute' : 'Import Record & Recompute'}</span>
              </button>
            </div>
          </form>
        )}

      </div>
    </div>
  );
}
