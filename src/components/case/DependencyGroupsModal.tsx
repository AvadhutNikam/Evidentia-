import React, { useState, useMemo } from 'react';
import { Evidence, DependencyGroupsResponse, ExculpatoryConfigOut } from '../../types';
import { 
  X, GitBranch, Sparkles, ShieldCheck, HelpCircle, 
  Check, Loader2, Info, ArrowRight, Layers, Database, AlertCircle, FileText
} from 'lucide-react';
import { cn } from '../../utils';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  evidenceList: Evidence[];
  dependencyData: DependencyGroupsResponse | null;
  exculpatoryConfig: ExculpatoryConfigOut | null;
  onUpdateGroup: (evidenceId: string | number, newGroup: string | null) => Promise<void>;
  onAutoGroup: () => Promise<void>;
  loading?: boolean;
}

export const DependencyGroupsModal: React.FC<Props> = ({
  isOpen,
  onClose,
  caseId,
  evidenceList,
  dependencyData,
  exculpatoryConfig,
  onUpdateGroup,
  onAutoGroup,
  loading = false
}) => {
  const [activeTab, setActiveTab] = useState<'dependence' | 'exculpatory'>('dependence');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedGroupFilter, setSelectedGroupFilter] = useState<string>('all');
  const [editingEvidenceId, setEditingEvidenceId] = useState<string | number | null>(null);
  const [customGroupInput, setCustomGroupInput] = useState('');
  const [savingId, setSavingId] = useState<string | number | null>(null);
  const [autoGrouping, setAutoGrouping] = useState(false);

  // Existing group names across all exhibits
  const existingGroupNames = useMemo(() => {
    const set = new Set<string>();
    evidenceList.forEach(e => {
      if (e.dependency_group) set.add(e.dependency_group);
    });
    if (dependencyData?.groups) {
      Object.keys(dependencyData.groups).forEach(g => set.add(g));
    }
    return Array.from(set).sort();
  }, [evidenceList, dependencyData]);

  // Filtered evidence list
  const filteredEvidence = useMemo(() => {
    return evidenceList.filter(e => {
      const g = e.dependency_group || '';
      if (selectedGroupFilter === 'grouped' && !g) return false;
      if (selectedGroupFilter === 'ungrouped' && g) return false;
      if (selectedGroupFilter !== 'all' && selectedGroupFilter !== 'grouped' && selectedGroupFilter !== 'ungrouped') {
        if (g !== selectedGroupFilter) return false;
      }
      const q = searchQuery.toLowerCase().trim();
      if (!q) return true;
      const title = (e.fileName || e.file_name || '').toLowerCase();
      const type = (e.evidence_type || e.fileType || '').toLowerCase();
      const group = g.toLowerCase();
      return title.includes(q) || type.includes(q) || group.includes(q);
    });
  }, [evidenceList, selectedGroupFilter, searchQuery]);

  if (!isOpen) return null;

  const handleStartEdit = (e: Evidence) => {
    setEditingEvidenceId(e.id);
    setCustomGroupInput(e.dependency_group || '');
  };

  const handleSaveGroup = async (evidenceId: string | number, newGroup: string | null) => {
    try {
      setSavingId(evidenceId);
      await onUpdateGroup(evidenceId, newGroup ? newGroup.trim() : null);
      setEditingEvidenceId(null);
    } finally {
      setSavingId(null);
    }
  };

  const handleRunAutoGroup = async () => {
    try {
      setAutoGrouping(true);
      await onAutoGroup();
    } finally {
      setAutoGrouping(false);
    }
  };

  const totalGrouped = evidenceList.filter(e => Boolean(e.dependency_group)).length;
  const totalClusters = existingGroupNames.length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in">
      <div className="bg-[#faf7f2] border border-[#d8d0c5] rounded-3xl w-full max-w-5xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden font-sans">
        
        {/* Header */}
        <div className="p-6 bg-white border-b border-[#eae4d9] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-purple-50 text-purple-700 flex items-center justify-center border border-purple-200">
              <GitBranch className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-serif font-bold text-[#191410]">
                  Evidentiary Dependence & Clearing Factors
                </h2>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-purple-100 text-purple-800 border border-purple-200">
                  ACH Change 5
                </span>
              </div>
              <p className="text-xs text-[#6e665d] mt-0.5">
                Manage shared-source exhibit groups, geometric weight damping, and first-class exculpatory clearing rules.
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-[#f5f0e8] hover:bg-[#eae4d9] flex items-center justify-center text-[#6e665d] hover:text-[#191410] transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="px-6 py-2.5 bg-[#f0ebe1] border-b border-[#eae4d9] flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab('dependence')}
              className={cn(
                "px-4 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-2 cursor-pointer",
                activeTab === 'dependence'
                  ? "bg-white text-purple-950 shadow-xs border border-purple-300"
                  : "text-[#6e665d] hover:text-[#191410]"
              )}
            >
              <GitBranch className="w-3.5 h-3.5 text-purple-700" />
              <span>Shared Sources & Damping</span>
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-purple-100 text-purple-800">
                {totalClusters} clusters ({totalGrouped} exhibits)
              </span>
            </button>

            <button
              onClick={() => setActiveTab('exculpatory')}
              className={cn(
                "px-4 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-2 cursor-pointer",
                activeTab === 'exculpatory'
                  ? "bg-white text-emerald-950 shadow-xs border border-emerald-300"
                  : "text-[#6e665d] hover:text-[#191410]"
              )}
            >
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-700" />
              <span>Exculpatory Rules & Unknown Hypothesis</span>
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-emerald-100 text-emerald-800">
                4 Categories
              </span>
            </button>
          </div>

          {activeTab === 'dependence' && (
            <button
              onClick={handleRunAutoGroup}
              disabled={autoGrouping || loading}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-purple-900 hover:bg-purple-800 text-white rounded-full text-xs font-bold transition-all shadow-xs cursor-pointer disabled:opacity-50"
              title="Automatically detect exhibits sharing underlying witness statements, CCTV clips, or duplicate forensics"
            >
              {autoGrouping ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 text-purple-300" />}
              <span>{autoGrouping ? 'Detecting Groups...' : 'Auto-Detect Shared Sources'}</span>
            </button>
          )}
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">

          {/* TAB 1: DEPENDENCE & CLUSTERS */}
          {activeTab === 'dependence' && (
            <div className="space-y-6">
              {/* Scientific Explanation Alert */}
              <div className="p-4 rounded-2xl bg-purple-50/70 border border-purple-200 text-xs flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-xs">
                <div className="flex items-start gap-2.5">
                  <Info className="w-4 h-4 text-purple-700 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold text-purple-950 font-serif">Richards J. Heuer Jr. ACH Step 3: Evidentiary Independence: </span>
                    <span className="text-purple-900 leading-relaxed">
                      Exhibits sharing a single underlying source (retold witness accounts, copies of the same test, transcripts of the same CCTV recording) must not be treated as independent evidence. Evidentia applies geometric damping (w_j = 0.50^(j-1)) so subsequent exhibits from the same source carry discounted weight (100%, 50%, 25%, 12.5%).
                    </span>
                  </div>
                </div>
                <div className="shrink-0 font-mono text-[11px] font-bold text-purple-900 bg-white/90 px-3 py-1.5 rounded-xl border border-purple-200 text-right">
                  <span>Damping Decay: $\beta = 0.50$</span>
                </div>
              </div>

              {/* Cluster Summary Pills */}
              {existingGroupNames.length > 0 && (
                <div className="p-4 rounded-2xl bg-white border border-[#eae4d9] space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold uppercase tracking-wider text-[#6e665d]">
                      Active Dependency Clusters
                    </span>
                    <span className="text-[11px] font-mono text-purple-700 font-semibold">
                      {totalClusters} Groups Detected
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {existingGroupNames.map(g => {
                      const count = evidenceList.filter(e => e.dependency_group === g).length;
                      return (
                        <button
                          key={g}
                          onClick={() => setSelectedGroupFilter(selectedGroupFilter === g ? 'all' : g)}
                          className={cn(
                            "px-3 py-1.5 rounded-xl text-xs font-mono font-bold flex items-center gap-2 border transition-all cursor-pointer",
                            selectedGroupFilter === g
                              ? "bg-purple-900 text-white border-purple-900 shadow-xs"
                              : "bg-purple-50 hover:bg-purple-100 text-purple-900 border-purple-200"
                          )}
                        >
                          <GitBranch className="w-3 h-3 text-purple-600" />
                          <span>{g}</span>
                          <span className={cn(
                            "px-1.5 py-0.2 rounded-full text-[10px]",
                            selectedGroupFilter === g ? "bg-purple-800 text-purple-200" : "bg-purple-200 text-purple-900"
                          )}>
                            {count} exhibits
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Filters & Search */}
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-serif font-bold text-[#191410]">Filter:</span>
                  <div className="flex items-center bg-[#f0ebe1] p-0.5 rounded-full border border-[#d8d0c5]">
                    <button
                      onClick={() => setSelectedGroupFilter('all')}
                      className={cn(
                        "px-3 py-1 rounded-full text-xs font-bold transition-all cursor-pointer",
                        selectedGroupFilter === 'all' ? "bg-white text-[#191410] shadow-xs" : "text-[#6e665d]"
                      )}
                    >
                      All Exhibits ({evidenceList.length})
                    </button>
                    <button
                      onClick={() => setSelectedGroupFilter('grouped')}
                      className={cn(
                        "px-3 py-1 rounded-full text-xs font-bold transition-all cursor-pointer",
                        selectedGroupFilter === 'grouped' ? "bg-white text-purple-900 shadow-xs" : "text-[#6e665d]"
                      )}
                    >
                      Grouped ({totalGrouped})
                    </button>
                    <button
                      onClick={() => setSelectedGroupFilter('ungrouped')}
                      className={cn(
                        "px-3 py-1 rounded-full text-xs font-bold transition-all cursor-pointer",
                        selectedGroupFilter === 'ungrouped' ? "bg-white text-[#191410] shadow-xs" : "text-[#6e665d]"
                      )}
                    >
                      Independent ({evidenceList.length - totalGrouped})
                    </button>
                  </div>
                </div>

                <div className="relative min-w-[240px]">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search exhibit name or group..."
                    className="w-full pl-3 pr-8 py-1.5 rounded-xl border border-[#d8d0c5] bg-white text-xs text-[#191410] placeholder-[#a89f91] focus:outline-hidden focus:border-purple-600"
                  />
                  {searchQuery && (
                    <button 
                      onClick={() => setSearchQuery('')}
                      className="absolute right-2.5 top-2 text-[#8c8276] hover:text-[#191410]"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>

              {/* Exhibits Table */}
              <div className="border border-[#eae4d9] rounded-2xl overflow-hidden bg-white shadow-xs">
                <table className="w-full text-left border-collapse text-xs">
                  <thead className="bg-[#f5f0e8] border-b border-[#eae4d9] font-mono text-[11px]">
                    <tr>
                      <th className="p-3 font-bold text-[#191410]">Exhibit</th>
                      <th className="p-3 font-bold text-[#191410]">Type & Source</th>
                      <th className="p-3 font-bold text-[#191410]">Dependency Group</th>
                      <th className="p-3 font-bold text-[#191410]">Damping Schedule</th>
                      <th className="p-3 font-bold text-[#191410] text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#eae4d9]">
                    {filteredEvidence.map((e) => {
                      const isEditing = editingEvidenceId === e.id;
                      const isSaving = savingId === e.id;
                      const hasGroup = Boolean(e.dependency_group);

                      // Calculate rank in group if grouped
                      let rankInGroup = 1;
                      let multiplier = 1.0;
                      if (hasGroup) {
                        const members = evidenceList.filter(m => m.dependency_group === e.dependency_group);
                        const idx = members.findIndex(m => String(m.id) === String(e.id));
                        rankInGroup = idx >= 0 ? idx + 1 : 1;
                        multiplier = Math.pow(0.50, rankInGroup - 1);
                      }

                      return (
                        <tr 
                          key={e.id}
                          className={cn(
                            "hover:bg-[#faf7f2]/80 transition-colors",
                            hasGroup && "bg-purple-50/20"
                          )}
                        >
                          <td className="p-3 align-middle font-medium text-[#191410]">
                            <div className="flex items-center gap-2">
                              {hasGroup && <div className="w-1.5 h-6 rounded-full bg-purple-500 shrink-0" />}
                              <div>
                                <span className="font-semibold block">{e.fileName || e.file_name}</span>
                                <span className="text-[10px] font-mono text-[#8c8276]">ID: {e.id}</span>
                              </div>
                            </div>
                          </td>

                          <td className="p-3 align-middle">
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-stone-100 text-stone-700 border border-stone-200">
                              {e.evidence_type || e.fileType || 'Document'}
                            </span>
                            <div className="text-[10px] text-[#8c8276] truncate max-w-[160px] mt-0.5">
                              {e.source || 'Judicial Registry'}
                            </div>
                          </td>

                          <td className="p-3 align-middle">
                            {isEditing ? (
                              <div className="space-y-1.5 min-w-[220px]">
                                <input
                                  type="text"
                                  value={customGroupInput}
                                  onChange={(ev) => setCustomGroupInput(ev.target.value)}
                                  placeholder="e.g. eyewitness_shinde_retold"
                                  className="w-full px-2.5 py-1 text-xs font-mono rounded-lg border border-purple-400 bg-white focus:outline-hidden"
                                />
                                {existingGroupNames.length > 0 && (
                                  <div className="flex flex-wrap gap-1">
                                    {existingGroupNames.slice(0, 4).map(gn => (
                                      <button
                                        key={gn}
                                        type="button"
                                        onClick={() => setCustomGroupInput(gn)}
                                        className="text-[9px] font-mono bg-purple-100 hover:bg-purple-200 text-purple-900 px-1.5 py-0.5 rounded cursor-pointer"
                                      >
                                        +{gn}
                                      </button>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ) : (
                              hasGroup ? (
                                <span className="px-2.5 py-1 rounded-md text-[11px] font-mono font-bold bg-purple-50 text-purple-900 border border-purple-300 inline-flex items-center gap-1.5">
                                  <GitBranch className="w-3 h-3 text-purple-700" />
                                  <span>{e.dependency_group}</span>
                                </span>
                              ) : (
                                <span className="text-stone-400 font-mono text-[11px] italic">
                                  Independent (No group)
                                </span>
                              )
                            )}
                          </td>

                          <td className="p-3 align-middle font-mono">
                            {hasGroup ? (
                              <div className="space-y-0.5">
                                <div className="text-xs font-bold text-purple-950 flex items-center gap-1">
                                  <span>Exhibit #{rankInGroup} in group</span>
                                  <span className="text-purple-700">({(multiplier * 100).toFixed(0)}% weight)</span>
                                </div>
                                {rankInGroup > 1 && (
                                  <div className="text-[10px] text-amber-700 font-semibold">
                                    -{( (1 - multiplier) * 100 ).toFixed(0)}% Damping Discount
                                  </div>
                                )}
                              </div>
                            ) : (
                              <div className="text-stone-500 text-[11px]">
                                100% full weight
                              </div>
                            )}
                          </td>

                          <td className="p-3 align-middle text-right">
                            {isEditing ? (
                              <div className="flex items-center justify-end gap-1.5">
                                <button
                                  onClick={() => handleSaveGroup(e.id, customGroupInput)}
                                  disabled={isSaving}
                                  className="px-2.5 py-1 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white font-bold text-xs flex items-center gap-1 cursor-pointer disabled:opacity-50"
                                >
                                  {isSaving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
                                  <span>Save</span>
                                </button>
                                <button
                                  onClick={() => setEditingEvidenceId(null)}
                                  className="px-2 py-1 rounded-lg bg-stone-100 hover:bg-stone-200 text-stone-700 text-xs cursor-pointer"
                                >
                                  Cancel
                                </button>
                              </div>
                            ) : (
                              <div className="flex items-center justify-end gap-1.5">
                                <button
                                  onClick={() => handleStartEdit(e)}
                                  className="px-2.5 py-1 rounded-lg bg-white hover:bg-purple-50 text-purple-900 border border-purple-200 hover:border-purple-400 font-medium text-xs cursor-pointer transition-all"
                                >
                                  {hasGroup ? 'Edit Group' : 'Assign Group'}
                                </button>
                                {hasGroup && (
                                  <button
                                    onClick={() => handleSaveGroup(e.id, null)}
                                    disabled={isSaving}
                                    className="px-2 py-1 rounded-lg bg-stone-50 hover:bg-rose-50 text-stone-500 hover:text-rose-700 text-xs cursor-pointer transition-all"
                                    title="Remove dependency group and make independent"
                                  >
                                    Clear
                                  </button>
                                )}
                              </div>
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

          {/* TAB 2: EXCULPATORY EVIDENCE & UNKNOWN HYPOTHESIS */}
          {activeTab === 'exculpatory' && (
            <div className="space-y-6">
              
              {/* Unknown Hypothesis Mechanics Card */}
              <div className="p-5 rounded-2xl bg-amber-500/10 border border-amber-300 space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-xl bg-amber-100 text-amber-900 shrink-0">
                      <HelpCircle className="w-5 h-5 text-amber-800" />
                    </div>
                    <div>
                      <h3 className="font-serif font-bold text-base text-amber-950">
                        Unknown / Other Explanation (Open-World Hypothesis)
                      </h3>
                      <p className="text-xs text-amber-900">
                        Automatically generated with every case to safeguard against closed-world tunnel vision.
                      </p>
                    </div>
                  </div>
                  <div className="text-right font-mono shrink-0">
                    <div className="text-sm font-black text-amber-950">10.0% Default Prior</div>
                    <div className="text-[10px] text-amber-800 uppercase tracking-wider">Baseline Plausibility</div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 text-xs">
                  <div className="p-3 rounded-xl bg-white/80 border border-amber-200/80 space-y-1">
                    <span className="font-serif font-bold text-amber-950 block">1. Dynamic Prior Expansion</span>
                    <span className="text-amber-900 text-[11px] leading-relaxed block">
                      Under open-world Bayesian updating, when evidence fits none of the listed suspects well, the unknown prior automatically expands to absorb the unexplained probability mass.
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-white/80 border border-amber-200/80 space-y-1">
                    <span className="font-serif font-bold text-amber-950 block">2. Dominant Lead Detection</span>
                    <span className="text-amber-900 text-[11px] leading-relaxed block">
                      When suspects accumulate strong alibis or DNA exclusions, their likelihood products plunge ($LR \ll 1$), propelling the Unknown hypothesis to Rank #1.
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-white/80 border border-amber-200/80 space-y-1">
                    <span className="font-serif font-bold text-amber-950 block">3. Investigative Directive</span>
                    <span className="text-amber-900 text-[11px] leading-relaxed block">
                      When leading, the system explicitly declares: <em>"The evidence does not clearly point to any listed suspect,"</em> preventing premature suspect targeting.
                    </span>
                  </div>
                </div>
              </div>

              {/* 4 First-Class Exculpatory Categories */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-serif font-bold text-[#191410]">
                      First-Class Exculpatory Evidence Categories
                    </h3>
                    <p className="text-xs text-[#6e665d]">
                      Scientific and legal clearing factors with strong negative likelihood ratios ($LR \in [10^{-5}, 5\cdot 10^{-3}]$ / $-50$ to $-23$ dB).
                    </p>
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-100 text-emerald-900 border border-emerald-300">
                    Reliability-Adjusted Clearing Factors
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {exculpatoryConfig && Object.entries(exculpatoryConfig.categories || {}).map(([key, cat]) => (
                    <div 
                      key={key}
                      className="p-4 rounded-2xl bg-white border border-[#eae4d9] hover:border-emerald-300 transition-all shadow-xs space-y-2.5"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <ShieldCheck className="w-4 h-4 text-emerald-600" />
                          <h4 className="font-serif font-bold text-sm text-[#191410]">{cat.name}</h4>
                        </div>
                        <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-emerald-50 text-emerald-800 border border-emerald-300">
                          {cat.clearing_level}
                        </span>
                      </div>

                      <p className="text-xs text-[#6e665d] leading-relaxed">
                        {cat.description}
                      </p>

                      <div className="flex items-center justify-between pt-2 border-t border-[#f0ebe1] text-xs font-mono">
                        <div>
                          <span className="text-[#8c8276] text-[10px] uppercase block">Default Likelihood Ratio</span>
                          <span className="font-bold text-blue-900">
                            {cat.default_lr < 0.001 ? cat.default_lr.toExponential(1) : cat.default_lr}× ({cat.decibans} dB)
                          </span>
                        </div>
                        <div className="text-right">
                          <span className="text-[#8c8276] text-[10px] uppercase block">Statutory Reference</span>
                          <span className="font-bold text-[#191410]">{cat.statutory_ref}</span>
                        </div>
                      </div>

                      <div className="text-[10px] font-mono text-[#8c8276] italic">
                        Citation: {cat.scientific_citation}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

            </div>
          )}

        </div>

        {/* Footer */}
        <div className="p-4 bg-[#f5f0e8] border-t border-[#eae4d9] flex items-center justify-between">
          <div className="text-xs text-[#6e665d]">
            Total exhibits in case docket: <strong className="text-[#191410] font-mono">{evidenceList.length}</strong> exhibits
          </div>
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-full bg-[#191410] hover:bg-[#2e261f] text-white font-bold text-xs transition-colors cursor-pointer"
          >
            Done
          </button>
        </div>

      </div>
    </div>
  );
};
