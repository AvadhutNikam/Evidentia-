import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { 
  FileText, Mic, MessageSquare, Camera, CheckCircle2, 
  AlertTriangle, UploadCloud, Plus, RefreshCw, Sparkles, 
  ShieldCheck, HelpCircle, ArrowRight, BookOpen, Clock, Check
} from 'lucide-react';
import { 
  fetchIntakeItems, fetchIntakeMetrics, submitIntakeText, 
  confirmIntakeItem, rejectIntakeItem, fetchLegalGlossary,
  IntakeItemModel, IntakeTrustMetrics, FieldConfirmation, LegalTermModel 
} from '../../services/intakeService';
import { ReadingCard } from '../../components/intake/ReadingCard';
import { formatIndianDate } from '../../utils/indianFormatters';
import { useAuth } from '../../context/AuthContext';
import { useTranslation } from 'react-i18next';

export function IntakeReviewInbox() {
  const { caseId } = useParams<{ caseId: string }>();
  const parsedCaseId = parseInt(caseId || '1', 10);
  const { user } = useAuth();
  const { t } = useTranslation();

  const [items, setItems] = useState<IntakeItemModel[]>([]);
  const [selectedItem, setSelectedItem] = useState<IntakeItemModel | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('ready_for_review');
  const [metrics, setMetrics] = useState<IntakeTrustMetrics | null>(null);
  const [legalTerms, setLegalTerms] = useState<LegalTermModel[]>([]);
  const [showGlossary, setShowGlossary] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [feedbackToast, setFeedbackToast] = useState<string | null>(null);

  // Quick Ingest Modal
  const [activeChannelModal, setActiveChannelModal] = useState<string | null>(null);
  const [inputTitle, setInputTitle] = useState<string>('');
  const [inputText, setInputText] = useState<string>('');

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [itemsData, metricsData, termsData] = await Promise.all([
        fetchIntakeItems(parsedCaseId, statusFilter),
        fetchIntakeMetrics(parsedCaseId),
        fetchLegalGlossary()
      ]);
      setItems(itemsData);
      setMetrics(metricsData);
      setLegalTerms(termsData);

      // Select first item by default if none selected
      if (itemsData.length > 0 && (!selectedItem || !itemsData.some(i => i.id === selectedItem.id))) {
        setSelectedItem(itemsData[0]);
      } else if (itemsData.length === 0) {
        setSelectedItem(null);
      }
    } catch (err) {
      console.error('Error loading intake inbox:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [parsedCaseId, statusFilter]);

  const handleConfirmItem = async (confirmations: FieldConfirmation[]) => {
    if (!selectedItem) return;
    setIsSubmitting(true);
    try {
      const updated = await confirmIntakeItem(
        parsedCaseId,
        selectedItem.id,
        user?.id || 1,
        user?.full_name || 'Inspector S. Patil',
        confirmations,
        true
      );
      setFeedbackToast(`Successfully committed ${updated.applied_entities_count} confirmed fields to official docket.`);
      setTimeout(() => setFeedbackToast(null), 4000);
      await loadData();
    } catch (err: any) {
      alert(`Error confirming item: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRejectAll = async (reason: string) => {
    if (!selectedItem) return;
    setIsSubmitting(true);
    try {
      await rejectIntakeItem(parsedCaseId, selectedItem.id, user?.full_name || 'Investigator', reason);
      setFeedbackToast('Intake item discarded.');
      setTimeout(() => setFeedbackToast(null), 4000);
      await loadData();
    } catch (err: any) {
      alert(`Error rejecting item: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateSubmission = async (channel: string) => {
    if (!inputText.trim() || !inputTitle.trim()) {
      alert('Please provide title and text content.');
      return;
    }
    setIsSubmitting(true);
    try {
      const created = await submitIntakeText(
        parsedCaseId,
        channel,
        inputTitle,
        inputText,
        user?.full_name || 'Inspector S. Patil'
      );
      setActiveChannelModal(null);
      setInputTitle('');
      setInputText('');
      setFeedbackToast(`Intake item created and analyzed by AI.`);
      setTimeout(() => setFeedbackToast(null), 4000);
      setStatusFilter('ready_for_review');
      await loadData();
      setSelectedItem(created);
    } catch (err: any) {
      alert(`Submission failed: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Toast Feedback */}
      {feedbackToast && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#191410] text-white px-4 py-3 rounded-lg shadow-xl border border-emerald-500/40 flex items-center gap-3 animate-fade-in font-medium text-sm">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{feedbackToast}</span>
        </div>
      )}

      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#eae4d9]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-[#fdeee9] text-[#d93829] uppercase">
              Multilingual Intake & Document Reading
            </span>
            <span className="text-xs text-[#70685e]">
              Marathi / Hindi Indic OCR • WhatsApp Parser • Voice Notes
            </span>
          </div>
          <h1 className="text-2xl font-serif font-bold text-[#191410]">
            {t('intake_inbox')}
          </h1>
          <p className="text-xs text-[#70685e] mt-0.5">
            Low-typing intake pipeline with instant field extraction, Indic transliteration, and human investigator confirmation.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowGlossary(!showGlossary)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white border border-[#eae4d9] text-[#70685e] hover:text-[#191410] hover:border-neutral-400 transition-colors cursor-pointer"
          >
            <BookOpen className="w-3.5 h-3.5 text-[#d93829]" />
            Legal Terms Glossary ({legalTerms.length})
          </button>
          <button
            onClick={loadData}
            disabled={isLoading}
            className="p-2 rounded-lg text-[#70685e] hover:text-[#191410] bg-white border border-[#eae4d9] hover:bg-[#faf7f2] transition-colors cursor-pointer"
            title="Refresh items"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Trust Metrics Top Banner */}
      {metrics && (
        <div className="p-4 bg-white border border-[#eae4d9] rounded-xl shadow-xs flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 font-bold">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold font-mono text-[#191410]">
                  {metrics.acceptance_rate_pct}%
                </span>
                <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                  Accepted Unchanged by IOs
                </span>
              </div>
              <p className="text-xs text-[#70685e]">
                {metrics.accepted_unchanged_count} verified without edits • {metrics.edited_count} corrected • {metrics.rejected_count} discarded
              </p>
            </div>
          </div>

          <div className="text-xs text-[#70685e] max-w-sm text-right hidden sm:block">
            <span className="font-semibold text-[#191410]">Safeguard Guarantee: </span>
            Unconfirmed AI suggestions are isolated in draft storage and never enter official scoring or court chargesheets.
          </div>
        </div>
      )}

      {/* 4 Multi-Channel Ingest Action Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Scanned FIR Copy */}
        <div 
          onClick={() => {
            setActiveChannelModal('fir_copy');
            setInputTitle('Scanned FIR Copy (प्रथम खबरी अहवाल)');
          }}
          className="p-4 bg-white border border-[#eae4d9] rounded-xl hover:border-[#d93829] hover:shadow-sm transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between mb-3">
            <div className="w-8 h-8 rounded-lg bg-[#fdeee9] text-[#d93829] flex items-center justify-center group-hover:scale-105 transition-transform">
              <FileText className="w-4 h-4" />
            </div>
            <span className="text-[10px] font-mono font-bold uppercase text-[#70685e]">Channel 1</span>
          </div>
          <h3 className="text-sm font-bold text-[#191410] group-hover:text-[#d93829] transition-colors">
            FIR Copy (प्रथम खबरी अहवाल)
          </h3>
          <p className="text-xs text-[#70685e] mt-1 line-clamp-2">
            Auto-extracts Crime No, Police Station, Penal Sections, Complainant, and Accused with date ambiguity detection.
          </p>
        </div>

        {/* Card 2: Handwritten Statement */}
        <div 
          onClick={() => {
            setActiveChannelModal('handwritten_statement');
            setInputTitle('Witness Handwritten Statement (साक्षीदाराचा जबाब)');
          }}
          className="p-4 bg-white border border-[#eae4d9] rounded-xl hover:border-[#d93829] hover:shadow-sm transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between mb-3">
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center group-hover:scale-105 transition-transform">
              <Camera className="w-4 h-4" />
            </div>
            <span className="text-[10px] font-mono font-bold uppercase text-[#70685e]">Channel 2</span>
          </div>
          <h3 className="text-sm font-bold text-[#191410] group-hover:text-blue-600 transition-colors">
            Handwritten Statement
          </h3>
          <p className="text-xs text-[#70685e] mt-1 line-clamp-2">
            Marathi / Hindi Devanagari OCR. Captures witness name, address, alibi timeline claims, and monetary details.
          </p>
        </div>

        {/* Card 3: Audio Voice Notes */}
        <div 
          onClick={() => {
            setActiveChannelModal('voice_note');
            setInputTitle('Investigator Field Voice Note (व्हॉइस नोट)');
          }}
          className="p-4 bg-white border border-[#eae4d9] rounded-xl hover:border-[#d93829] hover:shadow-sm transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between mb-3">
            <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center group-hover:scale-105 transition-transform">
              <Mic className="w-4 h-4" />
            </div>
            <span className="text-[10px] font-mono font-bold uppercase text-[#70685e]">Channel 3</span>
          </div>
          <h3 className="text-sm font-bold text-[#191410] group-hover:text-purple-600 transition-colors">
            Audio Voice Note
          </h3>
          <p className="text-xs text-[#70685e] mt-1 line-clamp-2">
            Marathi/Hindi Whisper transcription. Auto-generates draft Case Diary entry and suggested investigation tasks.
          </p>
        </div>

        {/* Card 4: WhatsApp Chat Export */}
        <div 
          onClick={() => {
            setActiveChannelModal('whatsapp_export');
            setInputTitle('WhatsApp Chat Extraction (व्हॉट्सॲप चॅट)');
          }}
          className="p-4 bg-white border border-[#eae4d9] rounded-xl hover:border-[#d93829] hover:shadow-sm transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between mb-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center group-hover:scale-105 transition-transform">
              <MessageSquare className="w-4 h-4" />
            </div>
            <span className="text-[10px] font-mono font-bold uppercase text-[#70685e]">Channel 4</span>
          </div>
          <h3 className="text-sm font-bold text-[#191410] group-hover:text-emerald-600 transition-colors">
            WhatsApp Export (.txt)
          </h3>
          <p className="text-xs text-[#70685e] mt-1 line-clamp-2">
            Multi-sender parser, transactions, deleted messages, and Section 63 BSA electronic certificate compliance prompt.
          </p>
        </div>
      </div>

      {/* Main Review Section: Left Queue + Right Reading Card */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Queue List (4 cols) */}
        <div className="lg:col-span-4 bg-white border border-[#eae4d9] rounded-xl p-4 shadow-xs space-y-4">
          {/* Status Tabs */}
          <div className="flex items-center gap-1 bg-[#faf7f2] p-1 rounded-lg border border-[#eae4d9]">
            <button
              onClick={() => setStatusFilter('ready_for_review')}
              className={`flex-1 py-1.5 px-2 rounded-md text-xs font-bold transition-all ${
                statusFilter === 'ready_for_review'
                  ? 'bg-white text-[#d93829] shadow-2xs border border-[#eae4d9]'
                  : 'text-[#70685e] hover:text-[#191410]'
              }`}
            >
              Ready ({items.length})
            </button>
            <button
              onClick={() => setStatusFilter('confirmed')}
              className={`flex-1 py-1.5 px-2 rounded-md text-xs font-bold transition-all ${
                statusFilter === 'confirmed'
                  ? 'bg-white text-emerald-700 shadow-2xs border border-[#eae4d9]'
                  : 'text-[#70685e] hover:text-[#191410]'
              }`}
            >
              Confirmed
            </button>
            <button
              onClick={() => setStatusFilter('rejected')}
              className={`flex-1 py-1.5 px-2 rounded-md text-xs font-bold transition-all ${
                statusFilter === 'rejected'
                  ? 'bg-white text-rose-700 shadow-2xs border border-[#eae4d9]'
                  : 'text-[#70685e] hover:text-[#191410]'
              }`}
            >
              Rejected
            </button>
          </div>

          {/* Queue Items */}
          <div className="space-y-2.5 max-h-[600px] overflow-y-auto pr-1">
            {isLoading ? (
              <div className="py-12 text-center text-xs text-[#70685e]">
                Loading intake items...
              </div>
            ) : items.length === 0 ? (
              <div className="py-12 text-center text-xs text-[#70685e] space-y-2">
                <p>No intake items in this view.</p>
                <p className="text-[11px] text-[#b0a89d]">
                  Click one of the ingest channels above to test document extraction.
                </p>
              </div>
            ) : (
              items.map((item) => {
                const isSelected = selectedItem?.id === item.id;
                return (
                  <div
                    key={item.id}
                    onClick={() => setSelectedItem(item)}
                    className={`p-3.5 rounded-lg border text-left transition-all cursor-pointer ${
                      isSelected
                        ? 'border-[#d93829] bg-[#fdeee9]/40 shadow-xs'
                        : 'border-[#eae4d9] bg-white hover:border-[#b0a89d]'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded bg-[#faf7f2] border border-[#eae4d9] text-[#70685e]">
                        {item.channel.replace('_', ' ')}
                      </span>
                      <span className="text-[11px] font-mono text-[#70685e]">
                        {item.proposed_fields.length} fields
                      </span>
                    </div>

                    <h4 className="text-xs font-bold text-[#191410] line-clamp-1 mb-1">
                      {item.title}
                    </h4>

                    <div className="flex items-center justify-between text-[11px] text-[#70685e]">
                      <span>{formatIndianDate(item.created_at, false)}</span>
                      <span className="font-mono text-[10px] text-[#b0a89d]">
                        #{item.id}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Reading Card or Empty State (8 cols) */}
        <div className="lg:col-span-8">
          {selectedItem ? (
            <ReadingCard
              item={selectedItem}
              onConfirm={handleConfirmItem}
              onRejectAll={handleRejectAll}
              isSubmitting={isSubmitting}
            />
          ) : (
            <div className="p-12 text-center bg-white border border-[#eae4d9] rounded-xl text-sm text-[#70685e]">
              Select an intake item from the left queue to review and confirm extracted fields.
            </div>
          )}
        </div>
      </div>

      {/* Statutory Legal Terms Reference Drawer */}
      {showGlossary && (
        <div className="p-6 bg-white border border-[#eae4d9] rounded-xl shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-[#eae4d9]">
            <div className="flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-[#d93829]" />
              <h3 className="text-base font-bold font-serif text-[#191410]">
                Statutory Legal Terms & Admissibility Glossary
              </h3>
            </div>
            <button
              onClick={() => setShowGlossary(false)}
              className="text-xs font-semibold text-[#70685e] hover:text-[#191410]"
            >
              Close
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {legalTerms.map(term => (
              <div key={term.id} className="p-4 rounded-lg border border-[#eae4d9] bg-[#faf7f2]/50 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-[#d93829]">
                    {term.statute} § {term.section}
                  </span>
                  <span className="text-xs text-[#70685e] font-medium">
                    {term.marathi_label}
                  </span>
                </div>
                <h4 className="text-sm font-bold text-[#191410]">
                  {term.english_label}
                </h4>
                <p className="text-xs text-[#6e665d]">
                  {term.plain_explanation}
                </p>
                {term.court_admissibility_notes && (
                  <p className="text-[11px] text-amber-900 bg-amber-50 p-2 rounded border border-amber-200">
                    <span className="font-semibold">Court Admissibility: </span>
                    {term.court_admissibility_notes}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Ingest Modal */}
      {activeChannelModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl border border-[#eae4d9] shadow-2xl max-w-xl w-full p-6 space-y-4 animate-scale-up">
            <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9]">
              <h3 className="text-base font-bold font-serif text-[#191410]">
                Ingest: {activeChannelModal.replace('_', ' ').toUpperCase()}
              </h3>
              <button
                onClick={() => setActiveChannelModal(null)}
                className="text-neutral-400 hover:text-neutral-700 font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-[#70685e] mb-1">
                  Document / Item Title
                </label>
                <input
                  type="text"
                  value={inputTitle}
                  onChange={(e) => setInputTitle(e.target.value)}
                  placeholder="e.g. Scanned FIR CR-534/2009"
                  className="w-full px-3 py-2 border border-[#eae4d9] rounded-lg text-sm font-sans focus:outline-none focus:ring-2 focus:ring-[#d93829]/20 focus:border-[#d93829]"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-[#70685e] mb-1">
                  Document Text / OCR Content / Chat Export
                </label>
                <textarea
                  rows={8}
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder="Paste text in Marathi, Hindi, or English..."
                  className="w-full px-3 py-2 border border-[#eae4d9] rounded-lg text-sm font-sans focus:outline-none focus:ring-2 focus:ring-[#d93829]/20 focus:border-[#d93829]"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#eae4d9]">
              <button
                type="button"
                onClick={() => setActiveChannelModal(null)}
                className="px-4 py-2 text-xs font-semibold text-[#70685e] hover:text-[#191410]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => handleCreateSubmission(activeChannelModal)}
                disabled={isSubmitting}
                className="px-4 py-2 text-xs font-bold bg-[#d93829] text-white rounded-lg hover:bg-[#bf2b1d] transition-colors cursor-pointer disabled:opacity-50"
              >
                {isSubmitting ? 'Analyzing with AI...' : 'Submit & Analyze'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
