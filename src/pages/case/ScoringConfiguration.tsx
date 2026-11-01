import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { suspectProfileService, scoringService } from '../../services';
import { BackgroundWeightConfig, ScoringConfigVersion, LikelihoodRatioReference } from '../../types';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { 
  Sliders, SlidersHorizontal, Scale, ShieldCheck, ShieldAlert, History, 
  Save, RotateCcw, AlertTriangle, CheckCircle2, Lock, ArrowLeft, Loader2, Info, FileText
} from 'lucide-react';
import { cn } from '../../utils';
import { useAuth } from '../../context/AuthContext';

export function ScoringConfiguration() {
  const { caseId: paramCaseId } = useParams<{ caseId: string }>();
  const caseId = paramCaseId || '1';
  const { user, role } = useAuth();

  const [config, setConfig] = useState<BackgroundWeightConfig | null>(null);
  const [versions, setVersions] = useState<ScoringConfigVersion[]>([]);
  const [lrEntries, setLrEntries] = useState<LikelihoodRatioReference[]>([]);
  const [loading, setLoading] = useState(true);

  // Editable Form State
  const [accessWeight, setAccessWeight] = useState(0.25);
  const [opportunityWeight, setOpportunityWeight] = useState(0.25);
  const [meansWeight, setMeansWeight] = useState(0.15);
  const [motiveWeight, setMotiveWeight] = useState(0.20);
  const [feasibilityWeight, setFeasibilityWeight] = useState(0.15);

  const [alibiStrongDiscount, setAlibiStrongDiscount] = useState(0.10);
  const [alibiPartialDiscount, setAlibiPartialDiscount] = useState(0.50);
  const [alibiContradictMultiplier, setAlibiContradictMultiplier] = useState(1.30);
  const [criminalCap, setCriminalCap] = useState(0.10);
  const [includeHistory, setIncludeHistory] = useState(true);
  const [excludeJuvenile, setExcludeJuvenile] = useState(true);

  // Version Stamping Modal
  const [isVersionModalOpen, setIsVersionModalOpen] = useState(false);
  const [versionTag, setVersionTag] = useState('');
  const [changeRationale, setChangeRationale] = useState('');
  const [saving, setSaving] = useState(false);

  // Active tab inside config
  const [activeTab, setActiveTab] = useState<'weights' | 'caps' | 'lr_table' | 'version_history'>('weights');

  // Notification Toast
  const [toastMsg, setToastMsg] = useState<{ text: string; type: 'success' | 'info' | 'warning' } | null>(null);

  const isPrivileged = role === 'admin' || role === 'lead_investigator';

  const loadConfigData = async () => {
    if (!caseId) return;
    try {
      setLoading(true);
      const [cfg, vers, lr] = await Promise.all([
        suspectProfileService.getBackgroundConfig(caseId),
        scoringService.getScoringConfigVersions(caseId),
        scoringService.getLikelihoodRatioReferenceTable(caseId).catch(() => [])
      ]);

      if (cfg) {
        setConfig(cfg);
        setAccessWeight(cfg.access_weight ?? 0.25);
        setOpportunityWeight(cfg.opportunity_weight ?? 0.25);
        setMeansWeight(cfg.means_weight ?? 0.15);
        setMotiveWeight(cfg.motive_weight ?? 0.20);
        setFeasibilityWeight(cfg.travel_feasibility_weight ?? 0.15);

        setAlibiStrongDiscount(cfg.alibi_strongly_verified_discount ?? 0.10);
        setAlibiPartialDiscount(cfg.alibi_partially_verified_discount ?? 0.50);
        setAlibiContradictMultiplier(cfg.alibi_contradicted_multiplier ?? 1.30);
        setCriminalCap(cfg.criminal_history_max_cap ?? 0.10);
        setIncludeHistory(cfg.include_criminal_history ?? true);
        setExcludeJuvenile(cfg.exclude_juvenile_records ?? true);
      }
      setVersions(vers || []);
      setLrEntries(lr || []);
    } catch (err) {
      console.error('Failed to load scoring configuration:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConfigData();
  }, [caseId]);

  const handleOpenSaveModal = () => {
    const nextVer = config?.config_version 
      ? `v${(parseFloat(config.config_version.replace('v', '')) + 0.1).toFixed(1)}`
      : 'v1.1';
    setVersionTag(nextVer);
    setChangeRationale('Calibration of background plausibility weights and legal safeguard caps.');
    setIsVersionModalOpen(true);
  };

  const handleSaveAndVersionStamp = async () => {
    if (!caseId) return;
    setSaving(true);
    try {
      await suspectProfileService.updateBackgroundConfig(caseId, {
        access_weight: accessWeight,
        opportunity_weight: opportunityWeight,
        means_weight: meansWeight,
        motive_weight: motiveWeight,
        travel_feasibility_weight: feasibilityWeight,
        alibi_strongly_verified_discount: alibiStrongDiscount,
        alibi_partially_verified_discount: alibiPartialDiscount,
        alibi_contradicted_multiplier: alibiContradictMultiplier,
        criminal_history_max_cap: criminalCap,
        include_criminal_history: includeHistory,
        exclude_juvenile_records: excludeJuvenile,
        config_version: versionTag.trim() || 'v1.1.0',
        change_rationale: changeRationale.trim() || 'Investigation parameter update'
      });

      setIsVersionModalOpen(false);
      setToastMsg({
        text: `Configuration saved and stamped as ${versionTag}. Version permanently recorded for case dossiers.`,
        type: 'success'
      });
      setTimeout(() => setToastMsg(null), 4000);
      await loadConfigData();
    } catch (err: any) {
      console.error('Failed to save config:', err);
      alert(err.message || 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const totalWeight = accessWeight + opportunityWeight + meansWeight + motiveWeight + feasibilityWeight;

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
            <SlidersHorizontal className="w-3.5 h-3.5 text-[#d93829]" />
            <span>Audit-Controlled Parameter Calibration</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-serif font-bold text-[#191410]">
            Scoring Configuration & Versioning
          </h1>
          <p className="text-xs text-[#6e665d] mt-1 max-w-2xl">
            Configure background plausibility factor weights, statutory caps, and likelihood tables. 
            All modifications are version-stamped and recorded in generated case reports.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {caseId && (
            <Link
              to={`/cases/${caseId}/hypotheses`}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-full text-xs font-bold bg-[#faf7f2] hover:bg-[#eae4d9] text-[#191410] border border-[#d8d0c5] transition-all cursor-pointer shadow-xs"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Hypotheses</span>
            </Link>
          )}

          <button
            onClick={handleOpenSaveModal}
            className="flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-bold bg-[#191410] hover:bg-[#d93829] text-white transition-all cursor-pointer shadow-xs"
          >
            <Save className="w-3.5 h-3.5 text-emerald-400" />
            <span>Save & Version Stamp</span>
          </button>
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
            • Parameter configuration calibrates analytical sensitivity. Every report records which version stamp was active.
          </span>
        </div>
        <Link 
          to={`/cases/${caseId}/responsible-use`} 
          className="text-[11px] font-mono font-bold text-amber-900 underline hover:text-[#d93829] whitespace-nowrap shrink-0"
        >
          Limits & Safeguards Policy →
        </Link>
      </div>

      {/* Active Version Status Bar */}
      <div className="p-4 rounded-3xl bg-white border border-[#eae4d9] shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-stone-100 text-[#191410] shrink-0 font-mono font-bold text-sm">
            {config?.config_version || 'v1.0.0'}
          </div>
          <div>
            <div className="text-[10px] font-mono font-bold uppercase text-[#8c8276] tracking-wider">
              Active Configuration Stamp
            </div>
            <div className="text-xs font-bold text-[#191410]">
              Calibrated by: {config?.updated_by || 'Lead Investigator'}
            </div>
            <div className="text-[11px] text-[#6e665d] italic">
              "{config?.change_rationale || 'Standard Forensic Intelligence baseline parameters.'}"
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-emerald-50 text-emerald-800 border border-emerald-300">
            Merkle Audited
          </span>
          <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-stone-100 text-stone-800 border border-stone-300">
            {versions.length} Historical Stamped Versions
          </span>
        </div>
      </div>

      {/* Configuration Tabs */}
      <div className="flex items-center gap-2 border-b border-[#eae4d9] pb-2">
        <button
          onClick={() => setActiveTab('weights')}
          className={cn(
            "px-4 py-2 rounded-2xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5",
            activeTab === 'weights' ? "bg-[#191410] text-white shadow-xs" : "text-[#6e665d] hover:bg-[#faf7f2]"
          )}
        >
          <Sliders className="w-3.5 h-3.5" />
          <span>Background Weights</span>
        </button>
        <button
          onClick={() => setActiveTab('caps')}
          className={cn(
            "px-4 py-2 rounded-2xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5",
            activeTab === 'caps' ? "bg-[#191410] text-white shadow-xs" : "text-[#6e665d] hover:bg-[#faf7f2]"
          )}
        >
          <Scale className="w-3.5 h-3.5" />
          <span>Statutory Caps & Alibis</span>
        </button>
        <button
          onClick={() => setActiveTab('lr_table')}
          className={cn(
            "px-4 py-2 rounded-2xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5",
            activeTab === 'lr_table' ? "bg-[#191410] text-white shadow-xs" : "text-[#6e665d] hover:bg-[#faf7f2]"
          )}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Likelihood Ratio Reference Table</span>
        </button>
        <button
          onClick={() => setActiveTab('version_history')}
          className={cn(
            "px-4 py-2 rounded-2xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5",
            activeTab === 'version_history' ? "bg-[#191410] text-white shadow-xs" : "text-[#6e665d] hover:bg-[#faf7f2]"
          )}
        >
          <History className="w-3.5 h-3.5" />
          <span>Version Audit History</span>
        </button>
      </div>

      {/* TAB 1: BACKGROUND WEIGHTS */}
      {activeTab === 'weights' && (
        <Card className="rounded-3xl border-[#eae4d9] bg-white shadow-xs">
          <CardHeader className="border-b border-[#eae4d9] pb-3 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-base font-serif font-bold text-[#191410]">
                Layer 2 Plausibility Dimension Weights
              </CardTitle>
              <p className="text-xs text-[#6e665d] mt-0.5">
                Balances the contribution of physical access, opportunity, means, and motive before evidentiary updating.
              </p>
            </div>
            <div className="text-right">
              <span className="text-[10px] font-mono uppercase text-[#8c8276] block">Total Weight</span>
              <span className={cn("text-xs font-mono font-bold", totalWeight === 1.0 ? "text-emerald-700" : "text-amber-700")}>
                {totalWeight.toFixed(2)} / 1.00
              </span>
            </div>
          </CardHeader>
          <CardContent className="pt-6 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Access */}
              <div className="p-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-[#191410]">Access Weight</span>
                  <span className="font-mono font-bold text-amber-900">{accessWeight.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.05"
                  max="0.50"
                  step="0.05"
                  value={accessWeight}
                  onChange={(e) => setAccessWeight(parseFloat(e.target.value))}
                  className="w-full cursor-pointer accent-[#d93829]"
                />
                <p className="text-[11px] text-[#8c8276]">Physical proximity to the crime scene jurisdiction.</p>
              </div>

              {/* Opportunity */}
              <div className="p-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-[#191410]">Opportunity Weight</span>
                  <span className="font-mono font-bold text-amber-900">{opportunityWeight.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.05"
                  max="0.50"
                  step="0.05"
                  value={opportunityWeight}
                  onChange={(e) => setOpportunityWeight(parseFloat(e.target.value))}
                  className="w-full cursor-pointer accent-[#d93829]"
                />
                <p className="text-[11px] text-[#8c8276]">Temporal opportunity within the estimated incident window.</p>
              </div>

              {/* Means */}
              <div className="p-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-[#191410]">Means & Capability Weight</span>
                  <span className="font-mono font-bold text-amber-900">{meansWeight.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.05"
                  max="0.40"
                  step="0.05"
                  value={meansWeight}
                  onChange={(e) => setMeansWeight(parseFloat(e.target.value))}
                  className="w-full cursor-pointer accent-[#d93829]"
                />
                <p className="text-[11px] text-[#8c8276]">Access to specific weapons, tools, or specialised knowledge.</p>
              </div>

              {/* Motive */}
              <div className="p-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-[#191410]">Motive Driver Weight</span>
                  <span className="font-mono font-bold text-amber-900">{motiveWeight.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.05"
                  max="0.40"
                  step="0.05"
                  value={motiveWeight}
                  onChange={(e) => setMotiveWeight(parseFloat(e.target.value))}
                  className="w-full cursor-pointer accent-[#d93829]"
                />
                <p className="text-[11px] text-[#8c8276]">Financial, animosity, or retaliatory incentive driver.</p>
              </div>

              {/* Feasibility */}
              <div className="p-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] space-y-2 md:col-span-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-[#191410]">Travel Feasibility Weight</span>
                  <span className="font-mono font-bold text-amber-900">{feasibilityWeight.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.05"
                  max="0.30"
                  step="0.05"
                  value={feasibilityWeight}
                  onChange={(e) => setFeasibilityWeight(parseFloat(e.target.value))}
                  className="w-full cursor-pointer accent-[#d93829]"
                />
                <p className="text-[11px] text-[#8c8276]">Physical distance divided by transit time feasibility check.</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* TAB 2: CAPS & ALIBIS */}
      {activeTab === 'caps' && (
        <Card className="rounded-3xl border-[#eae4d9] bg-white shadow-xs">
          <CardHeader className="border-b border-[#eae4d9] pb-3">
            <CardTitle className="text-base font-serif font-bold text-[#191410]">
              Statutory Maximum Caps & Alibi Multipliers
            </CardTitle>
            <p className="text-xs text-[#6e665d] mt-0.5">
              Enforces legal boundaries under Section 54 Indian Evidence Act and calibrate alibi clearing rates.
            </p>
          </CardHeader>
          <CardContent className="pt-6 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Criminal History Cap */}
              <div className="p-4 rounded-2xl bg-rose-50/70 border border-rose-200 space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-rose-950">Criminal History Maximum Cap</span>
                  <span className="font-mono font-bold text-rose-900">+{(criminalCap * 100).toFixed(1)}% max</span>
                </div>
                <input
                  type="range"
                  min="0.02"
                  max="0.10"
                  step="0.01"
                  value={criminalCap}
                  onChange={(e) => setCriminalCap(parseFloat(e.target.value))}
                  className="w-full cursor-pointer accent-rose-700"
                />
                <p className="text-[11px] text-rose-800">
                  <b>Statutory Limit:</b> Hard statutory boundary capped at max 10.0% to ensure prior records can never overcome contradictory physical exhibits.
                </p>
              </div>

              {/* Alibi Strongly Verified Discount */}
              <div className="p-4 rounded-2xl bg-blue-50/70 border border-blue-200 space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-blue-950">Strongly Verified Alibi Discount</span>
                  <span className="font-mono font-bold text-blue-900">{alibiStrongDiscount.toFixed(2)}x ({(1 - alibiStrongDiscount) * 100}% reduction)</span>
                </div>
                <input
                  type="range"
                  min="0.05"
                  max="0.30"
                  step="0.05"
                  value={alibiStrongDiscount}
                  onChange={(e) => setAlibiStrongDiscount(parseFloat(e.target.value))}
                  className="w-full cursor-pointer accent-blue-700"
                />
                <p className="text-[11px] text-blue-800">
                  Multiplier applied to candidate plausibility when supported by independent electronic timestamp (e.g. CCTV, CDR).
                </p>
              </div>

              {/* Juvenile Records Exclusion */}
              <div className="p-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-[#191410]">Exclude Juvenile Justice Records</div>
                  <div className="text-[11px] text-[#8c8276]">Adheres to Juvenile Justice Act confidentiality mandates.</div>
                </div>
                <input
                  type="checkbox"
                  checked={excludeJuvenile}
                  onChange={(e) => setExcludeJuvenile(e.target.checked)}
                  className="w-4 h-4 accent-[#d93829] cursor-pointer"
                />
              </div>

              {/* Include Criminal History Toggle */}
              <div className="p-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-[#191410]">Active History Consideration</div>
                  <div className="text-[11px] text-[#8c8276]">Include or disable prior conviction pattern matching case-wide.</div>
                </div>
                <input
                  type="checkbox"
                  checked={includeHistory}
                  onChange={(e) => setIncludeHistory(e.target.checked)}
                  className="w-4 h-4 accent-[#d93829] cursor-pointer"
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* TAB 3: LIKELIHOOD RATIO REFERENCE TABLE */}
      {activeTab === 'lr_table' && (
        <Card className="rounded-3xl border-[#eae4d9] bg-white shadow-xs">
          <CardHeader className="border-b border-[#eae4d9] pb-3 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-base font-serif font-bold text-[#191410]">
                Forensic Likelihood Ratio Reference Standards
              </CardTitle>
              <p className="text-xs text-[#6e665d] mt-0.5">
                Peer-reviewed ranges based on scientific literature citations (ENFSI, SWGDE, Forensic Science International).
              </p>
            </div>
            <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-blue-50 text-blue-800 border border-blue-300">
              {lrEntries.length} Scientific Categories
            </span>
          </CardHeader>
          <CardContent className="p-0">
            <div className="max-h-[500px] overflow-y-auto">
              <table className="w-full text-xs text-left border-collapse">
                <thead className="bg-[#f5f0e8] border-b border-[#eae4d9] font-mono text-[11px] sticky top-0 z-10">
                  <tr>
                    <th className="p-3 font-bold text-[#191410]">Finding Category</th>
                    <th className="p-3 font-bold text-[#191410]">Evidence Type</th>
                    <th className="p-3 font-bold text-[#191410]">Typical LR</th>
                    <th className="p-3 font-bold text-[#191410]">Range [Min – Max]</th>
                    <th className="p-3 font-bold text-[#191410]">Literature Citation</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#eae4d9]">
                  {lrEntries.slice(0, 15).map(e => (
                    <tr key={e.category_key} className="hover:bg-[#faf7f2] transition-colors">
                      <td className="p-3 font-bold text-[#191410]">{e.finding_name}</td>
                      <td className="p-3 font-mono text-[11px] text-[#6e665d] uppercase">{e.evidence_type}</td>
                      <td className="p-3 font-mono font-bold text-emerald-800">{e.typical_lr >= 1 ? `${e.typical_lr}x` : `1/${(1/e.typical_lr).toFixed(0)}`}</td>
                      <td className="p-3 font-mono text-[11px] text-[#8c8276]">{e.min_lr} – {e.max_lr}</td>
                      <td className="p-3 text-[11px] text-[#6e665d] italic">{e.source_citation || 'Forensic Literature Standard'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* TAB 4: VERSION AUDIT HISTORY */}
      {activeTab === 'version_history' && (
        <Card className="rounded-3xl border-[#eae4d9] bg-white shadow-xs">
          <CardHeader className="border-b border-[#eae4d9] pb-3">
            <CardTitle className="text-base font-serif font-bold text-[#191410]">
              Version Stamping & Calibration Audit Trail
            </CardTitle>
            <p className="text-xs text-[#6e665d] mt-0.5">
              Permanent chronological record of parameter adjustments. Every case report records which settings version was used.
            </p>
          </CardHeader>
          <CardContent className="p-0">
            {versions.length === 0 ? (
              <div className="py-12 text-center text-xs text-[#8c8276] font-mono">
                No previous configuration versions recorded yet. Current settings represent the baseline v1.0.0.
              </div>
            ) : (
              <div className="divide-y divide-[#eae4d9]">
                {versions.map(v => (
                  <div key={v.id} className="p-4 hover:bg-[#faf7f2] transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-sm text-[#191410] bg-stone-100 px-2 py-0.5 rounded border border-stone-200">
                          {v.version_tag}
                        </span>
                        <span className="font-bold text-[#191410]">by {v.created_by}</span>
                        <span className="text-[#8c8276] font-mono text-[11px]">
                          {v.created_at ? new Date(v.created_at).toLocaleString() : 'Recent'}
                        </span>
                      </div>
                      <p className="text-[#6e665d] mt-1 italic">
                        "{v.rationale || 'Parameter update'}"
                      </p>
                    </div>

                    <div className="shrink-0 font-mono text-[11px] text-[#8c8276] bg-white p-2 rounded-xl border border-[#eae4d9]">
                      Recorded in Case Dossier
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* VERSION STAMPING MODAL */}
      {isVersionModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 space-y-4 border border-[#eae4d9] shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9]">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-[#d93829]" />
                <h3 className="font-serif font-bold text-base text-[#191410]">
                  Version Stamp Settings
                </h3>
              </div>
              <button 
                onClick={() => setIsVersionModalOpen(false)}
                className="p-1 rounded-full hover:bg-stone-100 text-stone-500 cursor-pointer"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-[#6e665d] leading-relaxed">
              Every change must be stamped with a version tag and audit justification so subsequent case dossiers 
              permanently document which calibration settings were applied.
            </p>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-mono font-bold uppercase text-[#8c8276] text-[10px] block mb-1">
                  Version Identifier Tag:
                </label>
                <input
                  type="text"
                  value={versionTag}
                  onChange={(e) => setVersionTag(e.target.value)}
                  placeholder="e.g. v1.1.0"
                  className="w-full p-2.5 rounded-xl border border-[#d8d0c5] font-mono text-xs font-bold text-[#191410]"
                />
              </div>

              <div>
                <label className="font-mono font-bold uppercase text-[#8c8276] text-[10px] block mb-1">
                  Investigator Rationale:
                </label>
                <textarea
                  value={changeRationale}
                  onChange={(e) => setChangeRationale(e.target.value)}
                  placeholder="Explain why weights or caps were recalibrated (e.g. Alibi verification sensitivity update)..."
                  rows={3}
                  className="w-full p-2.5 rounded-xl border border-[#d8d0c5] text-xs resize-none"
                />
              </div>

              <div className="p-3 rounded-2xl bg-amber-50 border border-amber-200 text-[11px] text-amber-900">
                <b>Audit Requirement:</b> This stamp will be appended to the Merkle audit ledger under your credentials: <b>{user?.full_name || 'Investigator'} ({role})</b>.
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-[#eae4d9]">
              <button
                onClick={() => setIsVersionModalOpen(false)}
                className="px-4 py-2 rounded-full border border-[#d8d0c5] text-xs font-bold text-[#6e665d] hover:bg-[#faf7f2] cursor-pointer"
              >
                Cancel
              </button>
              <button
                disabled={saving}
                onClick={handleSaveAndVersionStamp}
                className="px-4 py-2 rounded-full bg-[#191410] hover:bg-[#d93829] text-white text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer shadow-xs"
              >
                {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5 text-emerald-400" />}
                <span>Save & Record Version</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
