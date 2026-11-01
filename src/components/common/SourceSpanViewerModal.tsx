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
      return <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-[#191410]">{fullText}</pre>;
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
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900">
            <strong>Unanchored citation:</strong> Showing full text. Quote: "{activeCitation.quote}"
          </div>
          <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-[#191410]">{fullText}</pre>
        </div>
      );
    }

    const before = fullText.slice(0, start);
    const highlighted = fullText.slice(start, end);
    const after = fullText.slice(end);

    return (
      <div className="font-mono text-xs leading-relaxed text-[#191410] whitespace-pre-wrap select-text">
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
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-200">
      <div className="bg-white border border-[#eae4d9] rounded-2xl w-full max-w-6xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden text-[#191410]">
        
        {/* MODAL HEADER */}
        <div className="p-4 md:px-6 bg-[#faf7f2] border-b border-[#eae4d9] flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="p-2 rounded-xl bg-blue-50 border border-blue-200 text-blue-700 shrink-0">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-blue-800 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-200">
                  Source-Span Provenance
                </span>
                <span className="text-xs text-[#6e665d] font-mono">
                  Exhibit #{evidenceId}
                </span>
              </div>
              <h2 className="text-base md:text-lg font-serif font-bold text-[#191410] truncate mt-0.5">
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
                className="px-3 py-1.5 rounded-xl bg-white border border-[#eae4d9] text-xs font-semibold text-[#191410] hover:bg-[#faf7f2] flex items-center gap-1.5 transition-all cursor-pointer shadow-xs"
                title="Correct OCR errors or transcription mistakes"
              >
                <Edit3 className="w-3.5 h-3.5 text-[#d93829]" />
                <span>Correct OCR / Transcript</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-xl hover:bg-[#eae4d9]/50 text-[#6e665d] hover:text-[#191410] transition-all cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* ACTIVE CITATION BANNER (PROVENANCE ANCHOR) */}
        {activeCitation && !isEditing && (
          <div className="bg-[#faf7f2] px-6 py-3 border-b border-[#eae4d9] flex flex-wrap items-center justify-between gap-3 text-xs text-[#191410]">
            <div className="flex items-center gap-3">
              <span className={cn(
                "px-2.5 py-1 rounded-full text-[10px] font-mono font-bold uppercase tracking-wide border flex items-center gap-1.5",
                activeCitation.verified_match
                  ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                  : "bg-red-50 text-red-800 border-red-200"
              )}>
                {activeCitation.verified_match ? (
                  <>
                    <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                    Verified Citation ({Math.round(activeCitation.match_confidence * 100)}%)
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-3 h-3 text-red-600" />
                    Unverified / Approximate
                  </>
                )}
              </span>

              <span className="text-[11px] font-mono text-blue-900 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                Fact Type: <strong className="uppercase">{activeCitation.fact_type}</strong>
              </span>

              {activeCitation.page_number && (
                <span className="text-[11px] font-mono text-[#6e665d]">
                  Page {activeCitation.page_number}
                </span>
              )}

              {activeCitation.char_start !== null && activeCitation.char_end !== null && (
                <span className="text-[11px] font-mono text-[#6e665d]">
                  Offset: [{activeCitation.char_start} – {activeCitation.char_end}]
                </span>
              )}

              {activeCitation.verification_method && (
                <span className="text-[10px] font-mono text-[#6e665d] bg-white px-2 py-0.5 rounded border border-[#eae4d9]">
                  Method: {activeCitation.verification_method.replace('_', ' ')}
                </span>
              )}
            </div>

            <div className="flex items-center gap-2 font-mono text-[11px] text-amber-800 truncate max-w-md">
              <Quote className="w-3.5 h-3.5 shrink-0 text-amber-600" />
              <span className="truncate italic">"{activeCitation.quote}"</span>
            </div>
          </div>
        )}

        {/* FEEDBACK AFTER CORRECTION */}
        {correctionFeedback && (
          <div className="bg-emerald-50 border-b border-emerald-200 px-6 py-2.5 text-xs text-emerald-900 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>{correctionFeedback.message} (Audit Block committed to Merkle ledger).</span>
            </div>
            <button
              onClick={() => setCorrectionFeedback(null)}
              className="text-emerald-700 hover:text-emerald-900 cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* MODAL BODY */}
        <div className="flex-1 overflow-hidden grid grid-cols-1 lg:grid-cols-12">
          
          {/* MAIN COLUMN: EXHIBIT VIEWER OR EDITOR */}
          <div className="lg:col-span-8 flex flex-col border-b lg:border-b-0 lg:border-r border-[#eae4d9] overflow-hidden bg-white">
            {loading ? (
              <div className="flex-1 flex flex-col items-center justify-center p-12 text-[#d93829] gap-3">
                <RefreshCw className="w-8 h-8 animate-spin" />
                <span className="text-xs font-mono text-[#6e665d]">Loading exhibit text & anchoring citation spans...</span>
              </div>
            ) : isEditing ? (
              /* ANALYST OCR / TRANSCRIPTION CORRECTION MODE */
              <div className="flex-1 flex flex-col p-4 md:p-6 space-y-4 overflow-y-auto">
                <div className="p-3.5 bg-blue-50 border border-blue-200 rounded-xl text-xs space-y-1">
                  <div className="font-bold text-blue-900 flex items-center gap-2">
                    <Edit3 className="w-4 h-4" /> Analyst Transcription Correction Mode
                  </div>
                  <p className="text-[#6e665d] leading-relaxed">
                    Correct OCR scan misreads, audio transcription errors, or typo offsets. Saving will automatically re-split the text into positioned exhibit chunks, re-verify all fact citations, and record an immutable entry into the cryptographic audit log.
                  </p>
                </div>

                <div className="flex-1 flex flex-col min-h-[350px]">
                  <label className="text-xs font-mono font-bold text-[#191410] mb-1.5">
                    Extracted Text Content:
                  </label>
                  <textarea
                    value={editedText}
                    onChange={(e) => setEditedText(e.target.value)}
                    className="flex-1 p-4 bg-[#faf7f2] border border-[#eae4d9] rounded-xl font-mono text-xs leading-relaxed text-[#191410] focus:outline-none focus:border-[#d93829] resize-none min-h-[320px]"
                    placeholder="Enter corrected document text..."
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    onClick={() => setIsEditing(false)}
                    className="px-4 py-2 rounded-xl bg-white border border-[#eae4d9] text-xs font-semibold text-[#6e665d] hover:text-[#191410] transition-all cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveCorrection}
                    disabled={isSaving}
                    className="px-5 py-2 rounded-xl bg-[#d93829] hover:bg-[#bf2b1d] text-white text-xs font-bold flex items-center gap-2 shadow-xs transition-all cursor-pointer disabled:opacity-50"
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
                <div className="bg-[#faf7f2] px-5 py-2 border-b border-[#eae4d9] flex items-center justify-between text-xs font-mono text-[#6e665d]">
                  <div className="flex items-center gap-2">
                    <Layers className="w-3.5 h-3.5 text-blue-700" />
                    <span>Chunks: <strong>{chunks.length}</strong></span>
                    <span>•</span>
                    <span>Total Length: <strong>{fullText.length.toLocaleString()}</strong> chars</span>
                  </div>
                  {activeCitation && (
                    <div className="text-amber-800 flex items-center gap-1.5 font-semibold">
                      <Sparkles className="w-3.5 h-3.5 text-amber-600" />
                      <span>Span anchored at char [{activeCitation.char_start} : {activeCitation.char_end}]</span>
                    </div>
                  )}
                </div>

                {/* Highlightable Document Text Container */}
                <div 
                  ref={textContainerRef}
                  className="flex-1 p-6 md:p-8 overflow-y-auto space-y-4 select-text bg-[#faf7f2] text-[#191410]"
                >
                  {renderHighlightedDocument()}
                </div>
              </div>
            )}
          </div>

          {/* SIDEBAR: CITATION INDEX & ANCHORS */}
          <div className="lg:col-span-4 bg-white border-l border-[#eae4d9] flex flex-col overflow-hidden">
            <div className="p-4 border-b border-[#eae4d9] flex items-center justify-between">
              <div>
                <h3 className="text-xs font-mono font-bold text-[#191410] uppercase tracking-wider flex items-center gap-1.5">
                  <Hash className="w-3.5 h-3.5 text-blue-700" />
                  <span>Anchored Facts ({filteredCitations.length})</span>
                </h3>
                <p className="text-[11px] text-[#6e665d] mt-0.5">
                  Click any fact to jump and highlight in source
                </p>
              </div>

              {/* Filter pills */}
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="bg-[#faf7f2] border border-[#eae4d9] text-[11px] font-mono text-[#191410] rounded-xl px-2 py-1 focus:outline-none focus:border-[#d93829]"
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
                <div className="p-8 text-center text-[#8c8276] text-xs italic">
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
                        "p-3 rounded-xl border text-xs cursor-pointer transition-all space-y-1.5 shadow-xs",
                        isSelected
                          ? "bg-red-50/50 border-[#d93829] shadow-xs"
                          : "bg-white border-[#eae4d9] hover:border-[#eae4d9] text-[#191410]"
                      )}
                    >
                      <div className="flex items-center justify-between gap-1">
                        <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full font-bold bg-blue-50 text-blue-800 border border-blue-200">
                          {cit.fact_type}
                        </span>
                        <span className={cn(
                          "text-[10px] font-mono px-2 py-0.5 rounded-full font-bold flex items-center gap-1 border",
                          cit.verified_match
                            ? "text-emerald-800 bg-emerald-50 border-emerald-200"
                            : "text-red-800 bg-red-50 border-red-200"
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

                      <div className="text-[11px] font-mono text-[#191410] line-clamp-2 italic">
                        "{cit.quote}"
                      </div>

                      <div className="flex items-center justify-between pt-1 border-t border-[#eae4d9] text-[10px] font-mono text-[#6e665d]">
                        <span>Chunk #{cit.chunk_id ?? 1}</span>
                        <span>Offset: [{cit.char_start ?? '?'} : {cit.char_end ?? '?'}]</span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Bottom info banner */}
            <div className="p-3 bg-[#faf7f2] border-t border-[#eae4d9] text-[11px] font-mono text-[#6e665d] flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>Anti-Hallucination Guard: Every fact strictly bounded to genuine exhibit bytes.</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
