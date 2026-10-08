import React, { useState, useEffect, useRef } from 'react';
import { 
  X, CheckCircle2, AlertTriangle, ShieldCheck, FileText, Quote, 
  ExternalLink, Edit3, Save, RefreshCw, Layers, Sparkles, 
  Search, Eye, Clock, Volume2, BookOpen, Hash
} from 'lucide-react';
import { citationService, evidenceService } from '../../services';
import { ExhibitChunk, SourceCitation, TextCorrectionResult, Evidence } from '../../types';
import { cn } from '../../utils';

interface SourceSpanViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  evidenceId: string | number;
  evidenceTitle?: string;
  initialCitation?: SourceCitation | null;
  targetQuote?: string;
  onTextUpdated?: () => void;
}

export const SourceSpanViewerModal: React.FC<SourceSpanViewerModalProps> = ({
  isOpen,
  onClose,
  caseId,
  evidenceId,
  evidenceTitle,
  initialCitation,
  targetQuote,
  onTextUpdated
}) => {
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [chunks, setChunks] = useState<ExhibitChunk[]>([]);
  const [citations, setCitations] = useState<SourceCitation[]>([]);
  const [activeCitation, setActiveCitation] = useState<SourceCitation | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  
  // Correction Mode State
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [editedText, setEditedText] = useState<string>('');
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [correctionFeedback, setCorrectionFeedback] = useState<TextCorrectionResult | null>(null);
  const [filterType, setFilterType] = useState<string>('all');

  const highlightRef = useRef<HTMLSpanElement | null>(null);
  const textContainerRef = useRef<HTMLDivElement | null>(null);

  // Fetch exhibit data, chunks and citations
  useEffect(() => {
    if (!isOpen || !caseId || !evidenceId) return;

    let isMounted = true;
    setLoading(true);

    Promise.all([
      evidenceService.getEvidenceById(evidenceId),
      citationService.getEvidenceChunks(caseId, evidenceId),
      citationService.getEvidenceCitations(caseId, evidenceId)
    ])
      .then(([ev, chs, cits]) => {
        if (!isMounted) return;
        setEvidence(ev || null);
        setChunks(chs || []);
        setCitations(cits || []);
        if (ev?.extracted_text) {
          setEditedText(ev.extracted_text);
        }

        // Set active citation
        if (initialCitation) {
          setActiveCitation(initialCitation);
        } else if (targetQuote && cits && cits.length > 0) {
          const found = cits.find(c => 
            c.quote.toLowerCase().includes(targetQuote.toLowerCase()) || 
            targetQuote.toLowerCase().includes(c.quote.toLowerCase())
          );
          setActiveCitation(found || cits[0]);
        } else if (cits && cits.length > 0) {
          setActiveCitation(cits[0]);
        }
      })
      .catch(err => {
        console.error('Error fetching citation data:', err);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, caseId, evidenceId, initialCitation, targetQuote]);

  // Scroll to active citation highlight whenever activeCitation changes
  useEffect(() => {
    if (!isEditing && highlightRef.current && textContainerRef.current) {
      setTimeout(() => {
        highlightRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'center'
        });
      }, 150);
    }
  }, [activeCitation, isEditing, chunks]);

  if (!isOpen) return null;

  const fullText = evidence?.extracted_text || chunks.map(c => c.text).join('\n\n') || '';

  // Handle OCR/Transcription correction save
  const handleSaveCorrection = async () => {
    if (!caseId || !evidenceId || !editedText.trim()) return;
    setIsSaving(true);
    try {
      const res = await citationService.updateExtractedText(caseId, evidenceId, editedText);
      setCorrectionFeedback(res);
      setIsEditing(false);

      // Refresh chunks & citations
      const [newChunks, newCits, updatedEv] = await Promise.all([
        citationService.getEvidenceChunks(caseId, evidenceId),
        citationService.getEvidenceCitations(caseId, evidenceId),
        evidenceService.getEvidenceById(evidenceId)
      ]);
      setChunks(newChunks);
      setCitations(newCits);
      if (updatedEv) setEvidence(updatedEv);

      if (newCits.length > 0) {
        setActiveCitation(newCits[0]);
      }
      if (onTextUpdated) {
        onTextUpdated();
      }
    } catch (err: any) {
      console.error('Failed to update text:', err);
      alert(`Error updating extracted text: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  // Render text with highlighting
  const renderHighlightedDocument = () => {
    if (!fullText) {
      return (
        <div className="p-8 text-center text-text-muted italic">
          No extracted text available for this exhibit.
        </div>
      );
    }

    if (!activeCitation) {
      return <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-slate-200">{fullText}</pre>;
    }

    // Determine target span
    let start = activeCitation.char_start;
    let end = activeCitation.char_end;

    // If offsets are missing or out of bounds, fallback to substring match in fullText
    if (start === null || start === undefined || end === null || end === undefined || start < 0 || end > fullText.length || start >= end) {
      if (activeCitation.quote) {
        const idx = fullText.toLowerCase().indexOf(activeCitation.quote.toLowerCase());
        if (idx !== -1) {
          start = idx;
          end = idx + activeCitation.quote.length;
        }
      }
    }

    if (start === null || start === undefined || end === null || end === undefined || start < 0 || start >= fullText.length) {
      // Cannot highlight exact span
      return (
        <div className="space-y-4">
          <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg text-xs text-amber-300">
            <strong>Unanchored citation:</strong> Showing full text. Quote: "{activeCitation.quote}"
          </div>
          <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-slate-200">{fullText}</pre>
        </div>
      );
    }

    const before = fullText.slice(0, start);
    const highlighted = fullText.slice(start, end);
    const after = fullText.slice(end);

    return (
      <div className="font-mono text-xs leading-relaxed text-slate-200 whitespace-pre-wrap select-text">
        <span>{before}</span>
        <mark
          ref={highlightRef}
          className={cn(
            "rounded px-1.5 py-0.5 font-bold transition-all inline-block shadow-md",
            activeCitation.verified_match
              ? "bg-amber-400/30 text-amber-200 border-b-2 border-amber-400 ring-2 ring-amber-400/30"
              : "bg-rose-500/30 text-rose-200 border-b-2 border-rose-500 ring-2 ring-rose-500/30"
          )}
        >
          {highlighted}
        </mark>
        <span>{after}</span>
      </div>
    );
  };

  const filteredCitations = citations.filter(c => {
    if (filterType === 'all') return true;
    return c.fact_type === filterType;
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-200">
      <div className="bg-[#0b1320] border border-cyan-500/30 rounded-2xl w-full max-w-6xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden text-white">
        
        {/* MODAL HEADER */}
        <div className="p-4 md:px-6 bg-[#0f1a2e] border-b border-border flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shrink-0">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                  Source-Span Provenance
                </span>
                <span className="text-xs text-text-muted font-mono">
                  Exhibit #{evidenceId}
                </span>
              </div>
              <h2 className="text-base md:text-lg font-serif font-bold text-white truncate mt-0.5">
                {evidenceTitle || evidence?.fileName || (evidence as any)?.file_name || 'Forensic Exhibit Record'}
              </h2>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {!isEditing && (
              <button
                onClick={() => {
                  setEditedText(fullText);
                  setIsEditing(true);
                }}
                className="px-3 py-1.5 rounded-lg bg-surface border border-border text-xs font-medium text-slate-300 hover:text-white hover:border-cyan-500/40 flex items-center gap-1.5 transition-all cursor-pointer"
                title="Correct OCR errors or transcription mistakes"
              >
                <Edit3 className="w-3.5 h-3.5 text-cyan-400" />
                <span>Correct OCR / Transcript</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 rounded-lg bg-surface hover:bg-slate-800 text-slate-400 hover:text-white transition-all cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* ACTIVE CITATION BANNER (PROVENANCE ANCHOR) */}
        {activeCitation && !isEditing && (
          <div className="bg-[#0e1c31] px-6 py-3 border-b border-cyan-500/20 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-3">
              <span className={cn(
                "px-2.5 py-1 rounded-full text-[10px] font-mono font-bold uppercase tracking-wide border flex items-center gap-1.5",
                activeCitation.verified_match
                  ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
                  : "bg-rose-500/10 text-rose-300 border-rose-500/30"
              )}>
                {activeCitation.verified_match ? (
                  <>
                    <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                    Verified Citation ({Math.round(activeCitation.match_confidence * 100)}%)
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-3 h-3 text-rose-400" />
                    Unverified / Approximate
                  </>
                )}
              </span>

              <span className="text-[11px] font-mono text-cyan-300 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/40">
                Fact Type: <strong className="uppercase">{activeCitation.fact_type}</strong>
              </span>

              {activeCitation.page_number && (
                <span className="text-[11px] font-mono text-slate-300">
                  Page {activeCitation.page_number}
                </span>
              )}

              {activeCitation.char_start !== null && activeCitation.char_end !== null && (
                <span className="text-[11px] font-mono text-text-muted">
                  Offset: [{activeCitation.char_start} – {activeCitation.char_end}]
                </span>
              )}

              {activeCitation.verification_method && (
                <span className="text-[10px] font-mono text-text-muted bg-slate-900 px-2 py-0.5 rounded">
                  Method: {activeCitation.verification_method.replace('_', ' ')}
                </span>
              )}
            </div>

            <div className="flex items-center gap-2 font-mono text-[11px] text-amber-300 truncate max-w-md">
              <Quote className="w-3.5 h-3.5 shrink-0 text-amber-400" />
              <span className="truncate italic">"{activeCitation.quote}"</span>
            </div>
          </div>
        )}

        {/* FEEDBACK AFTER CORRECTION */}
        {correctionFeedback && (
          <div className="bg-emerald-500/10 border-b border-emerald-500/30 px-6 py-2.5 text-xs text-emerald-300 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>{correctionFeedback.message} (Audit Block committed to Merkle ledger).</span>
            </div>
            <button
              onClick={() => setCorrectionFeedback(null)}
              className="text-emerald-400 hover:text-white"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* MODAL BODY */}
        <div className="flex-1 overflow-hidden grid grid-cols-1 lg:grid-cols-12">
          
          {/* MAIN COLUMN: EXHIBIT VIEWER OR EDITOR */}
          <div className="lg:col-span-8 flex flex-col border-b lg:border-b-0 lg:border-r border-border overflow-hidden bg-[#070d16]">
            {loading ? (
              <div className="flex-1 flex flex-col items-center justify-center p-12 text-cyan-400 gap-3">
                <RefreshCw className="w-8 h-8 animate-spin" />
                <span className="text-xs font-mono text-text-muted">Loading exhibit text & anchoring citation spans...</span>
              </div>
            ) : isEditing ? (
              /* ANALYST OCR / TRANSCRIPTION CORRECTION MODE */
              <div className="flex-1 flex flex-col p-4 md:p-6 space-y-4 overflow-y-auto">
                <div className="p-3.5 bg-cyan-500/10 border border-cyan-500/30 rounded-xl text-xs space-y-1">
                  <div className="font-bold text-cyan-300 flex items-center gap-2">
                    <Edit3 className="w-4 h-4" /> Analyst Transcription Correction Mode
                  </div>
                  <p className="text-text-muted leading-relaxed">
                    Correct OCR scan misreads, audio transcription errors, or typo offsets. Saving will automatically re-split the text into positioned exhibit chunks, re-verify all fact citations, and record an immutable entry into the cryptographic audit log.
                  </p>
                </div>

                <div className="flex-1 flex flex-col min-h-[350px]">
                  <label className="text-xs font-mono font-bold text-slate-300 mb-1.5">
                    Extracted Text Content:
                  </label>
                  <textarea
                    value={editedText}
                    onChange={(e) => setEditedText(e.target.value)}
                    className="flex-1 p-4 bg-[#0a1220] border border-cyan-500/40 rounded-xl font-mono text-xs leading-relaxed text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 resize-none min-h-[320px]"
                    placeholder="Enter corrected document text..."
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    onClick={() => setIsEditing(false)}
                    className="px-4 py-2 rounded-xl bg-surface border border-border text-xs font-medium text-slate-300 hover:text-white transition-all cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveCorrection}
                    disabled={isSaving}
                    className="px-5 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold flex items-center gap-2 shadow-lg shadow-cyan-900/30 transition-all cursor-pointer disabled:opacity-50"
                  >
                    {isSaving ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Re-indexing Citations...</span>
                      </>
                    ) : (
                      <>
                        <Save className="w-3.5 h-3.5" />
                        <span>Save Corrections & Audit Re-index</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            ) : (
              /* VIEW MODE: HIGH-FIDELITY DOCUMENT VIEWER WITH GLOWING HIGHLIGHT */
              <div className="flex-1 flex flex-col overflow-hidden">
                {/* Chunk Bar */}
                <div className="bg-[#0b1422] px-5 py-2 border-b border-border/60 flex items-center justify-between text-xs font-mono text-text-muted">
                  <div className="flex items-center gap-2">
                    <Layers className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Chunks: <strong>{chunks.length}</strong></span>
                    <span>•</span>
                    <span>Total Length: <strong>{fullText.length.toLocaleString()}</strong> chars</span>
                  </div>
                  {activeCitation && (
                    <div className="text-amber-300 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                      <span>Span anchored at char [{activeCitation.char_start} : {activeCitation.char_end}]</span>
                    </div>
                  )}
                </div>

                {/* Highlightable Document Text Container */}
                <div 
                  ref={textContainerRef}
                  className="flex-1 p-6 md:p-8 overflow-y-auto space-y-4 select-text bg-[#070c14]"
                >
                  {renderHighlightedDocument()}
                </div>
              </div>
            )}
          </div>

          {/* SIDEBAR: CITATION INDEX & ANCHORS */}
          <div className="lg:col-span-4 bg-[#0a1220] flex flex-col overflow-hidden">
            <div className="p-4 border-b border-border/80 flex items-center justify-between">
              <div>
                <h3 className="text-xs font-mono font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                  <Hash className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Anchored Facts ({filteredCitations.length})</span>
                </h3>
                <p className="text-[11px] text-text-muted mt-0.5">
                  Click any fact to jump and highlight in source
                </p>
              </div>

              {/* Filter pills */}
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="bg-[#0f1b2f] border border-border text-[11px] font-mono text-cyan-300 rounded-md px-2 py-1 focus:outline-none"
              >
                <option value="all">All Facts</option>
                <option value="entity">Entities</option>
                <option value="event">Events</option>
                <option value="assessment">ACH Assessments</option>
                <option value="claim">Claims</option>
              </select>
            </div>

            {/* Citations List */}
            <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
              {filteredCitations.length === 0 ? (
                <div className="p-8 text-center text-text-muted text-xs italic">
                  No citations anchored for this filter.
                </div>
              ) : (
                filteredCitations.map((cit) => {
                  const isSelected = activeCitation?.id === cit.id;
                  return (
                    <div
                      key={`cit-${cit.id}`}
                      onClick={() => {
                        setActiveCitation(cit);
                        setIsEditing(false);
                      }}
                      className={cn(
                        "p-3 rounded-xl border text-xs cursor-pointer transition-all space-y-1.5",
                        isSelected
                          ? "bg-cyan-500/10 border-cyan-500/60 shadow-md ring-1 ring-cyan-500/40"
                          : "bg-surface/50 border-border/60 hover:bg-surface hover:border-border text-slate-300"
                      )}
                    >
                      <div className="flex items-center justify-between gap-1">
                        <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded font-bold bg-[#0d182b] text-cyan-300 border border-cyan-800/40">
                          {cit.fact_type}
                        </span>
                        <span className={cn(
                          "text-[10px] font-mono px-2 py-0.5 rounded font-bold flex items-center gap-1",
                          cit.verified_match
                            ? "text-emerald-400 bg-emerald-500/10"
                            : "text-rose-400 bg-rose-500/10"
                        )}>
                          {cit.verified_match ? (
                            <>
                              <CheckCircle2 className="w-2.5 h-2.5" />
                              <span>{Math.round(cit.match_confidence * 100)}%</span>
                            </>
                          ) : (
                            <>
                              <AlertTriangle className="w-2.5 h-2.5" />
                              <span>Unverified</span>
                            </>
                          )}
                        </span>
                      </div>

                      <div className="text-[11px] font-mono text-slate-200 line-clamp-2 italic">
                        "{cit.quote}"
                      </div>

                      <div className="flex items-center justify-between pt-1 border-t border-border/30 text-[10px] font-mono text-text-muted">
                        <span>Chunk #{cit.chunk_id ?? 1}</span>
                        <span>Offset: [{cit.char_start ?? '?'} : {cit.char_end ?? '?'}]</span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Bottom info banner */}
            <div className="p-3 bg-[#0d1626] border-t border-border/80 text-[11px] font-mono text-text-muted flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Anti-Hallucination Guard: Every fact strictly bounded to genuine exhibit bytes.</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
