import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { hypothesisService, evidenceService, suspectProfileService, priorRecordService, scoringService } from '../../services';
import { Hypothesis, Evidence, PriorRecord, SuspectProfileFactor, ExculpatoryConfigOut } from '../../types';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { 
  Users, UserCheck, ShieldCheck, ShieldAlert, AlertTriangle, Scale, Lock, 
  FileText, CheckCircle2, XCircle, Plus, Edit3, ArrowRight, Loader2, Sparkles, 
  RotateCcw, Eye, Shield, Award, Info, ExternalLink
} from 'lucide-react';
import { cn } from '../../utils';
import { useAuth } from '../../context/AuthContext';

export function SuspectProfile() {
  const { caseId } = useParams<{ caseId: string }>();
  const { user, role, loginAsDemoRole } = useAuth();

  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
  const [selectedHypId, setSelectedHypId] = useState<string>('');
  const [loading, setLoading] = useState(true);

  // Profile factors state
  const [factors, setFactors] = useState<SuspectProfileFactor[]>([]);
  const [backgroundScore, setBackgroundScore] = useState<number>(50.0);
  const [feasibility, setFeasibility] = useState<any>(null);
  const [loadingProfile, setLoadingProfile] = useState(false);

  // Prior records state (role-restricted)
  const [priorRecords, setPriorRecords] = useState<PriorRecord[]>([]);
  const [isRoleRestricted, setIsRoleRestricted] = useState(false);
  const [restrictedMsg, setRestrictedMsg] = useState('');
  const [loadingPriors, setLoadingPriors] = useState(false);
  const [criminalCap, setCriminalCap] = useState<number>(0.10);

  // Case exhibits for exculpatory evidence check
  const [caseEvidence, setCaseEvidence] = useState<Evidence[]>([]);
  const [exculpatoryConfig, setExculpatoryConfig] = useState<ExculpatoryConfigOut | null>(null);

  // Edit Factor Modal state
  const [editingFactor, setEditingFactor] = useState<{
    factor_type: string;
    factor_value: string;
    note?: string;
    numeric_adjustment?: number;
  } | null>(null);
  const [savingFactor, setSavingFactor] = useState(false);

  // Toast notification
  const [toastMsg, setToastMsg] = useState<{ text: string; type: 'success' | 'info' | 'warning' } | null>(null);

  const isPrivileged = role === 'admin' || role === 'lead_investigator';

  // Load Initial Hypotheses & Evidence
  useEffect(() => {
    if (!caseId) return;
    setLoading(true);
    Promise.all([
      hypothesisService.getHypothesesForCase(caseId),
      evidenceService.getEvidenceForCase(caseId),
      scoringService.getExculpatoryConfig(caseId).catch(() => null)
    ])
      .then(([hyps, evs, exConf]) => {
        setHypotheses(hyps);
        setCaseEvidence(evs);
        if (exConf) setExculpatoryConfig(exConf);
        if (hyps.length > 0) {
          setSelectedHypId(String(hyps[0].id));
        }
      })
      .catch((err) => console.error('Failed to load suspects:', err))
      .finally(() => setLoading(false));
  }, [caseId]);

  // Load Suspect Profile factors & Prior records whenever selected hypothesis or role changes
  useEffect(() => {
    if (!caseId || !selectedHypId) return;
    loadSuspectData(selectedHypId);
  }, [caseId, selectedHypId, role]);

  // Live collaboration synchronization for suspect factors and criminal history
  useEffect(() => {
    const handleLiveSync = () => {
      if (selectedHypId) {
        loadSuspectData(selectedHypId);
      }
    };
    window.addEventListener('evidentia:item-changed', handleLiveSync);
    window.addEventListener('evidentia:scores-updated', handleLiveSync);
    return () => {
      window.removeEventListener('evidentia:item-changed', handleLiveSync);
      window.removeEventListener('evidentia:scores-updated', handleLiveSync);
    };
  }, [caseId, selectedHypId]);

  const loadSuspectData = async (hypId: string) => {
    if (!caseId) return;
    setLoadingProfile(true);
    setLoadingPriors(true);

    try {
      // 1. Suspect Profile factors (Access, Opportunity, Means, Motive, Alibi, Feasibility)
      const prof = await suspectProfileService.getSuspectProfile(caseId, hypId);
      if (prof) {
        setFactors(prof.factors || []);
        setBackgroundScore(prof.background_score || 50.0);
        setFeasibility(prof.feasibility_check || null);
      } else {
        setFactors([]);
        setBackgroundScore(50.0);
      }
    } catch (err) {
      console.error('Error fetching suspect profile:', err);
    } finally {
      setLoadingProfile(false);
    }

    try {
      // 2. Prior Criminal Records (Role-restricted by backend)
      const priorRes = await priorRecordService.getPriorRecords(caseId, hypId);
      if (priorRes.is_role_restricted) {
        setIsRoleRestricted(true);
        setRestrictedMsg(priorRes.restricted_message || 'Access Restricted: Criminal prior records are partitioned under Section 54 IEA.');
        setPriorRecords([]);
      } else {
        setIsRoleRestricted(false);
        setRestrictedMsg('');
        setPriorRecords(priorRes.records || []);
        setCriminalCap(priorRes.criminal_history_max_cap ?? 0.10);
      }
    } catch (err: any) {
      if (err.message && err.message.includes('Restricted')) {
        setIsRoleRestricted(true);
        setRestrictedMsg(err.message);
      }
      setPriorRecords([]);
    } finally {
      setLoadingPriors(false);
    }
  };

  const handleSaveFactor = async () => {
    if (!caseId || !selectedHypId || !editingFactor) return;
    setSavingFactor(true);
    try {
      await suspectProfileService.createOrUpdateFactor(caseId, selectedHypId, editingFactor);
      setToastMsg({ text: `Background factor '${editingFactor.factor_type}' recorded and verified.`, type: 'success' });
      setTimeout(() => setToastMsg(null), 4000);
      setEditingFactor(null);
      await loadSuspectData(selectedHypId);
    } catch (err: any) {
      console.error('Failed to save factor:', err);
      alert(err.message || 'Failed to save factor');
    } finally {
      setSavingFactor(false);
    }
  };

  const selectedHyp = hypotheses.find(h => String(h.id) === String(selectedHypId));

  // Determine exculpatory evidence related to this suspect
  const exculpatoryFindings = caseEvidence.filter(ev => {
    const isExculpatoryFlag = ev.is_exculpatory || (ev as any).isExculpatory;
    const notes = ((ev as any).clearing_factor_note || ev.description || '').toLowerCase();
    const suspectNameLower = (selectedHyp?.title || '').toLowerCase();
    return isExculpatoryFlag || (notes.includes(suspectNameLower) && notes.includes('clearing'));
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-24 text-[#191410]">
      {/* Toast */}
      {toastMsg && (
        <div className="fixed top-5 right-5 z-50 bg-[#191410] text-white px-4 py-2.5 rounded-2xl shadow-xl text-xs font-mono font-bold flex items-center gap-2 border border-stone-700 animate-in fade-in slide-in-from-top-3">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{toastMsg.text}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-[#eae4d9]">
        <div>
          <div className="text-[11px] font-mono tracking-widest text-[#d93829] uppercase font-bold mb-1 flex items-center gap-1.5">
            <UserCheck className="w-3.5 h-3.5 text-[#d93829]" />
            <span>Layer 2 Plausibility & Partitioned Modus Operandi Profiling</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-serif font-bold text-[#191410]">
            Suspect Profile Dossier
          </h1>
          <p className="text-xs text-[#6e665d] mt-1 max-w-3xl">
            Candidate opportunity factors, verified alibis, role-restricted prior conviction patterns, and exculpatory clearing exhibits.
          </p>
        </div>

        {/* Suspect Selector Pill Row */}
        <div className="flex items-center gap-2 bg-[#f0ebe1] p-1.5 rounded-2xl border border-[#d8d0c5] overflow-x-auto">
          <span className="text-[10px] font-mono font-bold text-[#8c8276] px-2 uppercase tracking-wider whitespace-nowrap">
            Candidate:
          </span>
          {hypotheses.map(h => (
            <button
              key={h.id}
              onClick={() => setSelectedHypId(String(h.id))}
              className={cn(
                "px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap flex items-center gap-1.5",
                String(h.id) === String(selectedHypId)
                  ? "bg-white text-[#191410] shadow-xs border border-[#eae4d9]"
                  : "text-[#6e665d] hover:text-[#191410]"
              )}
            >
              <span>{h.title}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Persistent Legal Notice Banner */}
      <div className="px-4 py-3 rounded-2xl bg-amber-50/90 border border-amber-300 shadow-2xs flex items-center justify-between gap-3 text-xs text-amber-950">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-700 shrink-0" />
          <span className="font-bold uppercase tracking-wider font-mono text-[11px] text-amber-900">
            Decision support, not a verdict.
          </span>
          <span className="hidden sm:inline text-amber-800 text-[11px]">
            • Suspect profiling evaluates candidate plausibility and behavioral patterns. Character evidence is partitioned from physical exhibit evaluation.
          </span>
        </div>
        <Link 
          to={`/cases/${caseId}/responsible-use`} 
          className="text-[11px] font-mono font-bold text-amber-900 underline hover:text-[#d93829] whitespace-nowrap shrink-0"
        >
          Limits & Responsible Use →
        </Link>
      </div>

      {/* Active Suspect Metric Overview */}
      {selectedHyp && (
        <div className="p-4 rounded-3xl bg-white border border-[#eae4d9] shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#8c8276]">
              Subject Candidate Profile
            </div>
            <h2 className="text-xl font-serif font-bold text-[#191410] mt-0.5">
              {selectedHyp.title}
            </h2>
            <p className="text-xs text-[#6e665d] mt-1 max-w-2xl">
              {selectedHyp.description || 'Investigative scenario under competing hypothesis evaluation.'}
            </p>
          </div>

          <div className="grid grid-cols-3 gap-2 shrink-0">
            <div className="px-3 py-2 rounded-2xl bg-blue-50/70 border border-blue-200 text-center min-w-[110px]">
              <div className="text-[9px] font-mono font-bold uppercase text-blue-900">
                relative support
              </div>
              <div className="text-base font-mono font-bold text-blue-950 mt-0.5">
                {((selectedHyp.evidence_score ?? selectedHyp.support_score ?? 50.0)).toFixed(1)}%
              </div>
              <div className="text-[8px] font-mono text-blue-700">Layer 1 Exhibits</div>
            </div>

            <div className="px-3 py-2 rounded-2xl bg-amber-50/70 border border-amber-200 text-center min-w-[110px]">
              <div className="text-[9px] font-mono font-bold uppercase text-amber-900">
                background plausibility
              </div>
              <div className="text-base font-mono font-bold text-amber-950 mt-0.5">
                {backgroundScore.toFixed(1)}%
              </div>
              <div className="text-[8px] font-mono text-amber-700">Layer 2 Factors</div>
            </div>

            <div className="px-3 py-2 rounded-2xl bg-emerald-50/70 border border-emerald-200 text-center min-w-[110px]">
              <div className="text-[9px] font-mono font-bold uppercase text-emerald-900">
                investigative priority
              </div>
              <div className="text-base font-mono font-bold text-emerald-950 mt-0.5">
                {((selectedHyp.combined_score ?? selectedHyp.support_score ?? 50.0)).toFixed(1)}%
              </div>
              <div className="text-[8px] font-mono text-emerald-700">Combined Posterior</div>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 1: CANDIDATE BACKGROUND FACTORS */}
      <Card className="rounded-3xl border-[#eae4d9] bg-white shadow-xs">
        <CardHeader className="border-b border-[#eae4d9] flex flex-row items-center justify-between pb-3">
          <div>
            <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#d93829]">
              Layer 2 • Plausibility Dimension
            </div>
            <CardTitle className="text-base font-serif font-bold text-[#191410] mt-0.5">
              Candidate Background Factors & Feasibility Check
            </CardTitle>
          </div>

          <button
            onClick={() => setEditingFactor({
              factor_type: 'access',
              factor_value: 'unrestricted',
              note: '',
              numeric_adjustment: 0.80
            })}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold bg-[#191410] hover:bg-[#d93829] text-white transition-all cursor-pointer shadow-xs"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Factor</span>
          </button>
        </CardHeader>
        <CardContent className="pt-4 space-y-4">
          {loadingProfile ? (
            <div className="py-12 text-center">
              <Loader2 className="w-6 h-6 animate-spin text-[#d93829] mx-auto mb-2" />
              <p className="text-xs font-mono text-[#8c8276]">Loading suspect factors and verifying alibis...</p>
            </div>
          ) : factors.length === 0 ? (
            <div className="text-center py-8 border border-dashed border-[#eae4d9] rounded-2xl bg-[#faf7f2]">
              <UserCheck className="w-8 h-8 text-[#b0a89d] mx-auto mb-2" />
              <div className="text-xs font-serif font-bold text-[#191410]">No Background Factors Recorded</div>
              <p className="text-[11px] text-[#8c8276] mt-0.5">Click "Add Factor" above to evaluate access, opportunity, means, or alibi.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {factors.map(f => (
                <div key={f.id} className="p-3.5 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] flex flex-col justify-between space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono font-bold uppercase text-[#8c8276] tracking-wider">
                      {f.factor_type.replace(/_/g, ' ')}
                    </span>
                    <span className={cn(
                      "px-2 py-0.5 rounded-full text-[9px] font-mono font-bold uppercase border",
                      f.effect_on_prior === 'raises_prior' ? "bg-amber-100 text-amber-900 border-amber-300" :
                      f.effect_on_prior === 'lowers_prior' || f.effect_on_prior === 'lowers_prior_sharply' ? "bg-blue-100 text-blue-900 border-blue-300" :
                      f.effect_on_prior === 'blocks_impossible' ? "bg-rose-100 text-rose-900 border-rose-300" :
                      "bg-stone-100 text-stone-700 border-stone-300"
                    )}>
                      {f.effect_on_prior?.replace(/_/g, ' ') || 'Neutral'}
                    </span>
                  </div>

                  <div>
                    <div className="text-sm font-bold text-[#191410] capitalize">
                      {f.factor_value.replace(/_/g, ' ')}
                    </div>
                    {f.note && (
                      <p className="text-[11px] text-[#6e665d] mt-1 line-clamp-2 italic">
                        "{f.note}"
                      </p>
                    )}
                  </div>

                  <div className="pt-2 border-t border-[#eae4d9] flex items-center justify-between text-[10px] text-[#8c8276] font-mono">
                    <span className="flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                      <span>{f.is_confirmed ? 'Verified by ' + (f.confirmed_by || 'Human') : 'AI Suggestion'}</span>
                    </span>
                    <button
                      onClick={() => setEditingFactor({
                        factor_type: f.factor_type,
                        factor_value: f.factor_value,
                        note: f.note,
                        numeric_adjustment: f.numeric_adjustment
                      })}
                      className="text-amber-900 hover:text-[#d93829] font-bold underline cursor-pointer"
                    >
                      Edit
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Travel Feasibility Check Summary */}
          {feasibility && (
            <div className="p-3.5 rounded-2xl bg-stone-50 border border-stone-200 text-xs flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
                <span className="font-mono text-[11px] text-stone-800">
                  <b>Timeline Feasibility:</b> {feasibility.message || 'Suspect known distance is physically achievable within estimated incident timeline window.'}
                </span>
              </div>
              <span className="px-2 py-0.5 rounded-full text-[9px] font-mono font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 whitespace-nowrap">
                Feasible (25 km / 60 min)
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* SECTION 2: PRIOR CRIMINAL RECORDS (ROLE-RESTRICTED) */}
      <Card className="rounded-3xl border-[#eae4d9] bg-white shadow-xs">
        <CardHeader className="border-b border-[#eae4d9] flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <div className="p-1 rounded bg-rose-100 text-rose-800">
                <Lock className="w-3.5 h-3.5" />
              </div>
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-rose-800">
                Layer 3 • Restricted Intelligence (Section 54 IEA / Section 52 BSA)
              </span>
            </div>
            <CardTitle className="text-base font-serif font-bold text-[#191410] mt-0.5">
              Prior Criminal History & Modus Operandi Matching
            </CardTitle>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-amber-50 text-amber-900 border border-amber-300">
              Statutory Cap: Max +{(criminalCap * 100).toFixed(0)}%
            </span>

            {/* Quick Demo Role Switcher for Test Validation */}
            <div className="flex items-center bg-[#f0ebe1] p-1 rounded-full border border-[#d8d0c5]">
              <span className="text-[9px] font-mono text-[#8c8276] px-1.5 uppercase font-bold">Role:</span>
              <button
                onClick={() => loginAsDemoRole('lead_investigator')}
                className={cn(
                  "px-2 py-0.5 rounded-full text-[10px] font-mono font-bold transition-all cursor-pointer",
                  isPrivileged ? "bg-white text-emerald-900 shadow-2xs" : "text-[#6e665d]"
                )}
                title="Switch to Lead Investigator (Authorized to view criminal history)"
              >
                Lead Investigator
              </button>
              <button
                onClick={() => loginAsDemoRole('analyst')}
                className={cn(
                  "px-2 py-0.5 rounded-full text-[10px] font-mono font-bold transition-all cursor-pointer",
                  !isPrivileged ? "bg-white text-rose-900 shadow-2xs" : "text-[#6e665d]"
                )}
                title="Switch to Analyst (Role restricted under Section 54 IEA)"
              >
                Analyst
              </button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-4">
          {/* If Role Restricted: Display Statutory Lock Screen */}
          {(!isPrivileged || isRoleRestricted) ? (
            <div className="p-6 rounded-2xl bg-rose-50/70 border-2 border-rose-200 text-center space-y-3">
              <div className="w-10 h-10 rounded-full bg-rose-100 text-rose-700 flex items-center justify-center mx-auto">
                <Lock className="w-5 h-5" />
              </div>
              <div className="max-w-xl mx-auto space-y-1">
                <h3 className="text-sm font-serif font-bold text-rose-950">
                  Access Restricted: Character Evidence Partition
                </h3>
                <p className="text-xs text-rose-900 leading-relaxed">
                  {restrictedMsg || 
                    "Under Section 54 of the Indian Evidence Act and Section 52 of Bharatiya Sakshya Adhiniyam, 2023, prior criminal convictions are strictly partitioned to eliminate confirmation bias and prevent prejudicial character inference. Only Lead Investigators and Administrators may access prior records."}
                </p>
                <div className="text-[11px] font-mono text-rose-800 pt-2">
                  Your current active role is: <span className="font-bold underline uppercase">{role}</span>. Switch to Lead Investigator above to inspect prior records.
                </div>
              </div>
            </div>
          ) : loadingPriors ? (
            <div className="py-12 text-center">
              <Loader2 className="w-6 h-6 animate-spin text-[#d93829] mx-auto mb-2" />
              <p className="text-xs font-mono text-[#8c8276]">Accessing partitioned prior records ledger...</p>
            </div>
          ) : priorRecords.length === 0 ? (
            <div className="text-center py-8 border border-dashed border-[#eae4d9] rounded-2xl bg-[#faf7f2]">
              <ShieldCheck className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
              <div className="text-xs font-serif font-bold text-[#191410]">No Prior Convictions on Record</div>
              <p className="text-[11px] text-[#8c8276] mt-0.5">Subject candidate has no prior criminal records registered in this case docket.</p>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="p-3 rounded-2xl bg-amber-50/60 border border-amber-200 text-xs text-amber-950">
                <b>Relevance Reasoning:</b> Prior record admitted strictly under Section 14/15 Indian Evidence Act to evaluate signature Modus Operandi patterns. Under the statutory safeguard, total history contribution cannot exceed <b>+10.0%</b> to ensure physical exhibits prevail.
              </div>

              <div className="border border-[#eae4d9] rounded-2xl overflow-hidden">
                <table className="w-full text-xs text-left border-collapse">
                  <thead className="bg-[#f5f0e8] border-b border-[#eae4d9] font-mono text-[11px]">
                    <tr>
                      <th className="p-3 font-bold text-[#191410]">Offense & Section</th>
                      <th className="p-3 font-bold text-[#191410]">Jurisdiction / Date</th>
                      <th className="p-3 font-bold text-[#191410]">Outcome</th>
                      <th className="p-3 font-bold text-[#191410]">MO Similarity</th>
                      <th className="p-3 font-bold text-[#191410]">Effective Weight</th>
                      <th className="p-3 font-bold text-[#191410]">History Contribution</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#eae4d9]">
                    {priorRecords.map(pr => (
                      <tr key={pr.id} className="hover:bg-[#faf7f2] transition-colors">
                        <td className="p-3">
                          <div className="font-bold text-[#191410]">{pr.offense_type}</div>
                          <div className="font-mono text-[10px] text-[#8c8276]">{pr.legal_section || 'IPC Section'}</div>
                        </td>
                        <td className="p-3">
                          <div>{pr.location || 'Unknown District'}</div>
                          <div className="font-mono text-[10px] text-[#8c8276]">{pr.offense_date || 'Past Record'}</div>
                        </td>
                        <td className="p-3">
                          <span className={cn(
                            "px-2 py-0.5 rounded-full text-[9px] font-mono font-bold uppercase",
                            pr.outcome === 'convicted' ? "bg-rose-100 text-rose-800 border border-rose-300" :
                            "bg-stone-100 text-stone-700 border border-stone-300"
                          )}>
                            {pr.outcome}
                          </span>
                        </td>
                        <td className="p-3 font-mono font-bold text-amber-900">
                          {((pr.computed_mo_similarity || 0.8) * 100).toFixed(0)}% Match
                        </td>
                        <td className="p-3 font-mono text-[#6e665d]">
                          {(pr.effective_weight || 0.08).toFixed(3)}
                        </td>
                        <td className="p-3 font-mono font-bold text-amber-900">
                          +{((pr.history_contribution || 0.08) * 100).toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* SECTION 3: EXCULPATORY EVIDENCE & CLEARING FACTORS */}
      <Card className="rounded-3xl border-[#eae4d9] bg-white shadow-xs">
        <CardHeader className="border-b border-[#eae4d9] flex flex-row items-center justify-between pb-3">
          <div>
            <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-emerald-800">
              Statutory Duty • Brady / Fair Disclosure Doctrine
            </div>
            <CardTitle className="text-base font-serif font-bold text-[#191410] mt-0.5">
              Exculpatory Evidence & Clearing Exhibits
            </CardTitle>
          </div>

          <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-emerald-50 text-emerald-800 border border-emerald-300">
            {exculpatoryFindings.length} Clearing Exhibit(s)
          </span>
        </CardHeader>
        <CardContent className="pt-4 space-y-3">
          <p className="text-xs text-[#6e665d] leading-relaxed">
            Exculpatory exhibits provide affirmative evidence inconsistent with suspect culpability (e.g. definitive DNA exclusion, 
            verified electronic alibi, blood type mismatch). The system automatically highlights these exhibits to prevent wrongful convictions.
          </p>

          {exculpatoryFindings.length === 0 ? (
            <div className="p-4 rounded-2xl bg-stone-50 border border-stone-200 text-xs text-stone-700 flex items-center justify-between">
              <span>No definitive exculpatory clearing exhibits identified for this suspect candidate yet.</span>
              <span className="font-mono text-[10px] text-stone-500">Inconclusive / Pending Lab Results</span>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {exculpatoryFindings.map(ev => (
                <div key={ev.id} className="p-3.5 rounded-2xl bg-emerald-50/70 border border-emerald-300 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-[10px] text-emerald-900 uppercase tracking-wider">
                      Definitive Clearing Exhibit
                    </span>
                    <span className="px-2 py-0.5 rounded-full text-[9px] font-mono font-bold bg-emerald-200 text-emerald-900">
                      Exculpatory
                    </span>
                  </div>
                  <div className="font-bold text-sm text-[#191410]">{ev.fileName || (ev as any).file_name}</div>
                  <p className="text-xs text-emerald-950 italic">
                    {(ev as any).clearing_factor_note || ev.description || 'Forensic analysis definitively clears subject from direct physical presence.'}
                  </p>
                  <div className="text-[10px] font-mono text-emerald-800 pt-1 border-t border-emerald-200">
                    Statutory Rule: Physical clearing exhibit strictly eliminates suspect priority despite any background plausibility.
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* EDIT FACTOR MODAL */}
      {editingFactor && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 space-y-4 border border-[#eae4d9] shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9]">
              <h3 className="font-serif font-bold text-base text-[#191410]">
                Record Suspect Background Factor
              </h3>
              <button 
                onClick={() => setEditingFactor(null)}
                className="p-1 rounded-full hover:bg-stone-100 text-stone-500 cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-mono font-bold uppercase text-[#8c8276] text-[10px] block mb-1">
                  Factor Type:
                </label>
                <select
                  value={editingFactor.factor_type}
                  onChange={(e) => setEditingFactor({ ...editingFactor, factor_type: e.target.value })}
                  className="w-full p-2 rounded-xl border border-[#d8d0c5] bg-white font-mono text-xs cursor-pointer"
                >
                  <option value="access">Access (Physical access to site)</option>
                  <option value="opportunity">Opportunity (Presence in timeframe)</option>
                  <option value="means">Means (Technical skills / Tools)</option>
                  <option value="motive">Motive (Financial / Personal)</option>
                  <option value="alibi_status">Alibi Status (Verified / Contradicted)</option>
                  <option value="travel_feasibility">Travel Feasibility (Speed / Route)</option>
                </select>
              </div>

              <div>
                <label className="font-mono font-bold uppercase text-[#8c8276] text-[10px] block mb-1">
                  Factor Value:
                </label>
                <input
                  type="text"
                  value={editingFactor.factor_value}
                  onChange={(e) => setEditingFactor({ ...editingFactor, factor_value: e.target.value })}
                  placeholder="e.g., unrestricted, strong, strongly_verified"
                  className="w-full p-2 rounded-xl border border-[#d8d0c5] font-mono text-xs"
                />
              </div>

              <div>
                <label className="font-mono font-bold uppercase text-[#8c8276] text-[10px] block mb-1">
                  Investigator Note & Exhibit Reference:
                </label>
                <textarea
                  value={editingFactor.note || ''}
                  onChange={(e) => setEditingFactor({ ...editingFactor, note: e.target.value })}
                  placeholder="Provide forensic justification or cite witness/CCTV record..."
                  rows={3}
                  className="w-full p-2 rounded-xl border border-[#d8d0c5] text-xs resize-none"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-[#eae4d9]">
              <button
                onClick={() => setEditingFactor(null)}
                className="px-4 py-2 rounded-full border border-[#d8d0c5] text-xs font-bold text-[#6e665d] hover:bg-[#faf7f2] cursor-pointer"
              >
                Cancel
              </button>
              <button
                disabled={savingFactor}
                onClick={handleSaveFactor}
                className="px-4 py-2 rounded-full bg-[#191410] hover:bg-[#d93829] text-white text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer shadow-xs"
              >
                {savingFactor ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                <span>Save & Confirm Factor</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
