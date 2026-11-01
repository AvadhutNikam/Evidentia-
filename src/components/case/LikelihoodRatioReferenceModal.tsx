import React, { useState, useMemo } from 'react';
import { LikelihoodRatioReference } from '../../types';
import { 
  X, Scale, Search, Sparkles, RotateCcw, Check, 
  ExternalLink, ShieldCheck, AlertCircle, Info, Edit3, Loader2, BookOpen
} from 'lucide-react';
import { cn } from '../../utils';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  entries: LikelihoodRatioReference[];
  onSaveEntry: (entry: LikelihoodRatioReference, updates: { typical_lr: number; min_lr: number; max_lr: number }) => Promise<void>;
  onResetDefaults: () => Promise<void>;
  loading?: boolean;
}

export const LikelihoodRatioReferenceModal: React.FC<Props> = ({
  isOpen,
  onClose,
  entries,
  onSaveEntry,
  onResetDefaults,
  loading = false
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editTypical, setEditTypical] = useState<number>(1.0);
  const [editMin, setEditMin] = useState<number>(1.0);
  const [editMax, setEditMax] = useState<number>(1.0);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [resetting, setResetting] = useState(false);

  // Evidence types available in entries
  const evidenceTypes = useMemo(() => {
    const types = Array.from(new Set(entries.map(e => e.evidence_type))).filter(Boolean);
    return ['all', ...types];
  }, [entries]);

  // Filtered entries
  const filteredEntries = useMemo(() => {
    return entries.filter(e => {
      const matchesType = selectedType === 'all' || e.evidence_type.toLowerCase() === selectedType.toLowerCase();
      const q = searchQuery.toLowerCase().trim();
      if (!q) return matchesType;
      const matchesText = 
        e.finding_name.toLowerCase().includes(q) ||
        e.category_key.toLowerCase().includes(q) ||
        e.evidence_type.toLowerCase().includes(q) ||
        (e.source_citation && e.source_citation.toLowerCase().includes(q)) ||
        (e.forensic_error_rate && e.forensic_error_rate.toLowerCase().includes(q)) ||
        (e.notes && e.notes.toLowerCase().includes(q));
      return matchesType && matchesText;
    });
  }, [entries, selectedType, searchQuery]);

  if (!isOpen) return null;

  const startEditing = (e: LikelihoodRatioReference) => {
    setEditingKey(e.category_key);
    setEditTypical(e.typical_lr);
    setEditMin(e.min_lr);
    setEditMax(e.max_lr);
  };

  const cancelEditing = () => {
    setEditingKey(null);
  };

  const handleSave = async (e: LikelihoodRatioReference) => {
    try {
      setSavingKey(e.category_key);
      await onSaveEntry(e, {
        typical_lr: Number(editTypical),
        min_lr: Number(editMin),
        max_lr: Number(editMax)
      });
      setEditingKey(null);
    } finally {
      setSavingKey(null);
    }
  };

  const handleReset = async () => {
    try {
      setResetting(true);
      await onResetDefaults();
      setEditingKey(null);
    } finally {
      setResetting(false);
    }
  };

  const formatLR = (val: number) => {
    if (val >= 10000) return `${val.toExponential(1)}×`;
    if (val >= 10) return `${val.toLocaleString()}×`;
    if (val >= 1) return `${val.toFixed(2)}×`;
    if (val <= 0.0001) return `${val.toExponential(1)}×`;
    return `${val.toFixed(4)}×`;
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-5 overflow-y-auto animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl max-w-6xl w-full p-6 space-y-5 border border-[#eae4d9] shadow-2xl max-h-[92vh] flex flex-col">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-[#eae4d9] gap-3">
          <div>
            <div className="text-[11px] font-mono font-bold uppercase tracking-wider text-blue-700 flex items-center gap-1.5">
              <Scale className="w-4 h-4 text-blue-700" />
              <span>Forensic Science Standards • Evidentiary Weight Rules</span>
            </div>
            <h2 className="text-xl font-serif font-bold text-[#191410] mt-0.5">
              Evidentiary Weight Guide: What Makes Proof Decisive in Court?
            </h2>
            <p className="text-xs text-[#6e665d] mt-1 max-w-3xl leading-relaxed">
              Standardized, peer-reviewed evidentiary weight standards and forensic error rates. The AI maps each exhibit's findings to established scientific literature; <strong className="text-[#191410]">this reference guide guarantees proof weights are grounded in proven laboratory benchmarks rather than arbitrary guesses.</strong> Unreliable or disputed evidence shrinks toward neutral weight.
            </p>
          </div>
          <button 
            onClick={onClose}
            className="p-2 rounded-full hover:bg-stone-100 text-stone-500 hover:text-stone-800 cursor-pointer self-start sm:self-auto"
            title="Close Reference Table"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Toolbar: Search & Type Filter Tabs */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-1">
          {/* Search Input */}
          <div className="relative flex-1 max-w-md">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#8c8276]" />
            <input 
              type="text"
              placeholder="Search category, citation, finding (e.g. Butler, DNA, exclusion, 15-STR)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-full border border-[#d8d0c5] bg-[#faf7f2] text-xs font-mono placeholder:text-[#8c8276] focus:bg-white focus:outline-hidden focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Reset Defaults & Category Count */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-[#6e665d]">
              Showing <strong className="text-[#191410]">{filteredEntries.length}</strong> of {entries.length} categories
            </span>
            <button
              onClick={handleReset}
              disabled={resetting}
              className="flex items-center gap-1 px-3 py-1.5 bg-[#faf7f2] hover:bg-rose-50 text-rose-700 hover:border-rose-300 rounded-full text-xs font-bold transition-all border border-[#d8d0c5] cursor-pointer shadow-2xs disabled:opacity-50"
              title="Reset all 33 forensic categories to scientific baseline literature standards"
            >
              {resetting ? <Loader2 className="w-3 h-3 animate-spin text-rose-700" /> : <RotateCcw className="w-3 h-3 text-rose-700" />}
              <span>Reset to Defaults</span>
            </button>
          </div>
        </div>

        {/* Evidence Type Pills */}
        <div className="flex flex-wrap items-center gap-1.5 overflow-x-auto pb-1">
          {evidenceTypes.map((t) => (
            <button
              key={`type-pill-${t}`}
              onClick={() => setSelectedType(t)}
              className={cn(
                "px-3 py-1 rounded-full text-[11px] font-mono font-bold capitalize transition-all cursor-pointer border",
                selectedType === t 
                  ? "bg-[#191410] text-white border-[#191410] shadow-xs" 
                  : "bg-[#faf7f2] text-[#6e665d] border-[#eae4d9] hover:bg-[#eae4d9] hover:text-[#191410]"
              )}
            >
              {t === 'all' ? 'All Forensic Disciplines' : t}
            </button>
          ))}
        </div>

        {/* Scrollable Table Area */}
        <div className="flex-1 overflow-y-auto border border-[#eae4d9] rounded-2xl bg-white shadow-inner">
          <table className="w-full text-xs text-left border-collapse">
            <thead className="sticky top-0 bg-[#f5f0e8] border-b border-[#eae4d9] z-10 shadow-2xs">
              <tr className="text-[#191410] font-mono font-bold text-[11px]">
                <th className="p-3">Forensic Finding & Discipline</th>
                <th className="p-3 text-center">Direction</th>
                <th className="p-3 text-right">Likelihood Ratio (LR)</th>
                <th className="p-3">Literature Source & Citation</th>
                <th className="p-3">Forensic Error Rate</th>
                <th className="p-3 text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#eae4d9]">
              {loading ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-[#6e665d]">
                    <div className="flex items-center justify-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin text-blue-700" />
                      <span>Loading forensic reference entries...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredEntries.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-[#6e665d] font-mono">
                    No categories matched query "{searchQuery}".
                  </td>
                </tr>
              ) : (
                filteredEntries.map((e) => {
                  const isEditing = editingKey === e.category_key;
                  const isSaving = savingKey === e.category_key;

                  const isExculpatory = e.support_direction === 'exculpatory' || e.typical_lr < 1.0;
                  const isIncriminating = e.support_direction === 'supporting' || e.typical_lr > 1.0;

                  return (
                    <tr 
                      key={`ref-row-${e.category_key}`}
                      className="hover:bg-[#faf7f2]/70 transition-colors align-top"
                    >
                      {/* Name & Key */}
                      <td className="p-3 min-w-[200px]">
                        <div className="font-serif font-bold text-[#191410] text-xs">
                          {e.finding_name}
                        </div>
                        <div className="font-mono text-[10px] text-[#6e665d] mt-0.5 flex items-center gap-1.5">
                          <span className="px-1.5 py-0.2 bg-[#f0ebe1] rounded text-[#4a4238] font-bold">
                            {e.evidence_type}
                          </span>
                          <span className="text-stone-400">#</span>
                          <span className="truncate">{e.category_key}</span>
                        </div>
                        {e.notes && (
                          <div className="text-[10px] text-[#8c8276] mt-1 italic leading-tight">
                            {e.notes}
                          </div>
                        )}
                      </td>

                      {/* Direction Badge */}
                      <td className="p-3 text-center whitespace-nowrap">
                        <span className={cn(
                          "px-2 py-0.5 rounded-full text-[10px] font-mono font-bold border",
                          isIncriminating && "bg-emerald-50 text-emerald-800 border-emerald-300",
                          isExculpatory && "bg-rose-50 text-rose-800 border-rose-300",
                          !isIncriminating && !isExculpatory && "bg-stone-100 text-stone-700 border-stone-200"
                        )}>
                          {isIncriminating ? '▲ Supporting' : isExculpatory ? '▼ Exculpatory' : '● Neutral'}
                        </span>
                      </td>

                      {/* LR Values */}
                      <td className="p-3 text-right font-mono min-w-[170px]">
                        {isEditing ? (
                          <div className="space-y-1 bg-[#faf7f2] p-2 rounded-xl border border-[#d8d0c5]">
                            <div className="flex items-center justify-between text-[10px]">
                              <span className="text-[#6e665d]">Typical LR:</span>
                              <input 
                                type="number"
                                step="any"
                                value={editTypical}
                                onChange={(evt) => setEditTypical(parseFloat(evt.target.value) || 1.0)}
                                className="w-24 px-1.5 py-0.5 rounded border border-[#d8d0c5] bg-white text-right font-bold"
                              />
                            </div>
                            <div className="flex items-center justify-between text-[10px]">
                              <span className="text-[#6e665d]">Min LR:</span>
                              <input 
                                type="number"
                                step="any"
                                value={editMin}
                                onChange={(evt) => setEditMin(parseFloat(evt.target.value) || 1.0)}
                                className="w-24 px-1.5 py-0.5 rounded border border-[#d8d0c5] bg-white text-right"
                              />
                            </div>
                            <div className="flex items-center justify-between text-[10px]">
                              <span className="text-[#6e665d]">Max LR:</span>
                              <input 
                                type="number"
                                step="any"
                                value={editMax}
                                onChange={(evt) => setEditMax(parseFloat(evt.target.value) || 1.0)}
                                className="w-24 px-1.5 py-0.5 rounded border border-[#d8d0c5] bg-white text-right"
                              />
                            </div>
                          </div>
                        ) : (
                          <div>
                            <div className={cn(
                              "font-bold text-xs",
                              isIncriminating && "text-emerald-900",
                              isExculpatory && "text-rose-900",
                              !isIncriminating && !isExculpatory && "text-stone-700"
                            )}>
                              {formatLR(e.typical_lr)}
                            </div>
                            <div className="text-[10px] text-[#8c8276]">
                              Range: [{formatLR(e.min_lr)} – {formatLR(e.max_lr)}]
                            </div>
                          </div>
                        )}
                      </td>

                      {/* Citation */}
                      <td className="p-3 text-[11px] text-[#4a4238] max-w-[240px]">
                        <div className="flex items-start gap-1">
                          <BookOpen className="w-3 h-3 shrink-0 text-blue-700 mt-0.5" />
                          <span className="leading-tight font-serif">{e.source_citation}</span>
                        </div>
                      </td>

                      {/* Forensic Error Rate */}
                      <td className="p-3 text-[10px] font-mono text-[#6e665d] whitespace-nowrap">
                        <span className="px-2 py-0.5 bg-[#f5f0e8] rounded border border-[#eae4d9] font-medium">
                          {e.forensic_error_rate || 'N/A'}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="p-3 text-center whitespace-nowrap">
                        {isEditing ? (
                          <div className="flex items-center justify-center gap-1">
                            <button
                              onClick={() => handleSave(e)}
                              disabled={isSaving}
                              className="px-2 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded font-bold text-[10px] cursor-pointer"
                              title="Save custom LR range"
                            >
                              {isSaving ? '...' : 'Save'}
                            </button>
                            <button
                              onClick={cancelEditing}
                              className="px-2 py-1 bg-stone-200 hover:bg-stone-300 text-stone-700 rounded text-[10px] cursor-pointer"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => startEditing(e)}
                            className="p-1 rounded hover:bg-[#eae4d9] text-[#6e665d] hover:text-[#191410] cursor-pointer transition-colors"
                            title="Edit likelihood ratio numbers for this finding"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Footer info & Close */}
        <div className="pt-2 border-t border-[#eae4d9] flex flex-col sm:flex-row sm:items-center justify-between text-xs text-[#6e665d] gap-3">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-700 shrink-0" />
            <span>
              <strong>Scientific Guarantee:</strong> Likelihood ratios multiply mathematically and normalize to strictly 100.0%. Irrelevant evidence ($LR=1.0$) leaves posteriors invariant.
            </span>
          </div>
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-full bg-[#191410] text-white text-xs font-bold hover:bg-[#2e261f] cursor-pointer transition-all self-end sm:self-auto shadow-xs"
          >
            Close Reference Table
          </button>
        </div>
      </div>
    </div>
  );
};
