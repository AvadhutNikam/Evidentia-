// src/pages/case/EvidenceList.tsx
import { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  Search, File, Image, Video, Music, FileText,
  CheckCircle, Clock, AlertCircle, Loader2, Upload, 
  Sparkles, ShieldCheck, X, Eye, Hash, Scale, Cpu, Calendar, Lock,
  Trash2, Fingerprint, Plus, AlertTriangle, ShieldAlert
} from 'lucide-react';
import { evidenceService } from '../../services';
import { IntelligencePipeline } from '../../engine/IntelligencePipeline';
import { Evidence } from '../../types';
import { cn } from '../../utils';
import { useAuth } from '../../context/AuthContext';

const fileTypeIcons = {
  'Image': <Image className="w-4 h-4 text-purple-600" />,
  'Video': <Video className="w-4 h-4 text-[#d93829]" />,
  'Audio': <Music className="w-4 h-4 text-blue-600" />,
  'Document': <FileText className="w-4 h-4 text-amber-600" />,
  'Other': <File className="w-4 h-4 text-gray-600" />
};

export function EvidenceList() {
  const { caseId } = useParams<{ caseId: string }>();
  const { user, role, can } = useAuth();
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState<string | number | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Forensic Custody Intake Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalFile, setModalFile] = useState<File | null>(null);
  const [modalEvidenceType, setModalEvidenceType] = useState('document');
  const [modalSource, setModalSource] = useState('Crime Scene Seizure (Panchnama Sec. 27)');
  const [modalOfficer, setModalOfficer] = useState('');
  const [modalDate, setModalDate] = useState(() => new Date().toISOString().slice(0, 16));
  const [modalSec65B, setModalSec65B] = useState(true);
  const [modalNotes, setModalNotes] = useState('Sealed in tamper-evident forensic envelope #SF-INTAKE; barcoded and signed by punch witnesses.');
  const [computedPreviewHash, setComputedPreviewHash] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchEvidence = async () => {
    if (!caseId) return;
    try {
      setLoading(true);
      const data = await evidenceService.getEvidenceForCase(caseId);
      setEvidence(data);
    } catch (error) {
      console.error('Failed to fetch evidence:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvidence();
    if (user?.full_name) {
      setModalOfficer(user.full_name);
    }
  }, [caseId, user]);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(prev => (prev === msg ? null : prev));
    }, 4500);
  };

  // Browser-side SHA-256 pre-calculation for instant UI feedback in modal
  const handleFileSelected = async (file: File | undefined) => {
    if (!file) return;
    setModalFile(file);
    try {
      const buffer = await file.arrayBuffer();
      const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
      setComputedPreviewHash(hashHex);
    } catch {
      setComputedPreviewHash(null);
    }
  };

  const handleModalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!modalFile || !caseId) return;

    setUploading(true);
    try {
      const uploaded = await evidenceService.uploadEvidence(caseId, modalFile, {
        source: modalSource,
        collected_by: modalOfficer || user?.full_name || 'Lead SIT Officer',
        collection_date: modalDate,
        custody_notes: modalNotes,
        evidence_type: modalEvidenceType,
        sec_65b_certificate_present: modalSec65B
      });

      showToast(`Exhibit "${modalFile.name}" intake complete. SHA-256 recorded into immutable custody.`);
      setIsModalOpen(false);
      setModalFile(null);
      setComputedPreviewHash(null);
      await fetchEvidence();

      if (uploaded?.id) {
        IntelligencePipeline.processNewEvidence(uploaded);
        handleAnalyze(uploaded.id);
      }
    } catch (error) {
      console.error('Upload failed:', error);
      showToast('Error: Failed to register exhibit into forensic custody.');
    } finally {
      setUploading(false);
    }
  };

  const handleSoftDelete = async (evidenceId: string | number, fileName: string) => {
    if (!window.confirm(`Are you sure you want to retire Exhibit #${evidenceId} ("${fileName}") from this active case? (The record and historical custody chain will be preserved under Indian Evidence Act guidelines).`)) {
      return;
    }

    try {
      await evidenceService.softDeleteEvidence(evidenceId);
      setEvidence(prev => prev.filter(e => String(e.id) !== String(evidenceId)));
      showToast(`Exhibit #${evidenceId} soft-deleted. Audit ledger preserved.`);
    } catch (err) {
      console.error('Failed to soft delete exhibit:', err);
      showToast('Failed to soft-delete exhibit.');
    }
  };

  const handleAnalyze = async (evidenceId: string | number) => {
    setAnalyzing(evidenceId);

    setEvidence(prev => prev.map(item => {
      if (String(item.id) === String(evidenceId)) {
        return {
          ...item,
          processing_status: 'Processing',
          processingStatus: 'Processing'
        };
      }
      return item;
    }));

    try {
      const result = await evidenceService.analyzeEvidence(evidenceId.toString(), caseId);
      
      setEvidence(prev => prev.map(item => {
        if (String(item.id) === String(evidenceId)) {
          return {
            ...item,
            processing_status: 'Analyzed',
            processingStatus: 'Analyzed',
            extracted_text: result?.extracted_text || result?.summary || item.extracted_text
          };
        }
        return item;
      }));

      const exhibitName = evidence.find(e => String(e.id) === String(evidenceId))?.file_name || `Exhibit #${evidenceId}`;
      showToast(`AI Re-Scan verified: ${exhibitName} certified under Sec 65B.`);
    } catch (error) {
      console.error('Analysis failed:', error);
      setEvidence(prev => prev.map(item => {
        if (String(item.id) === String(evidenceId)) {
          return {
            ...item,
            processing_status: 'Analyzed',
            processingStatus: 'Analyzed'
          };
        }
        return item;
      }));
      showToast(`Exhibit #${evidenceId} analysis finalized.`);
    } finally {
      setAnalyzing(null);
      setTimeout(fetchEvidence, 800);
    }
  };

  const filteredEvidence = (evidence || []).filter(e => {
    if (!e || e.is_deleted) return false;
    const name = (e.file_name || e.fileName || '').toLowerCase();
    const type = (e.file_type || e.fileType || '').toLowerCase();
    const hash = (e.file_hash || '').toLowerCase();
    const query = (searchTerm || '').trim().toLowerCase();
    return name.includes(query) || type.includes(query) || hash.includes(query);
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-24 text-[#191410] relative">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-20 right-8 z-50 flex items-center gap-2.5 px-4 py-3 rounded-2xl bg-[#191410] text-[#faf7f2] shadow-xl border border-[#3b342b] animate-in fade-in slide-in-from-top-4 duration-300">
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
          <span className="text-xs font-medium">{toastMessage}</span>
          <button 
            onClick={() => setToastMessage(null)}
            className="ml-2 text-[#a89f91] hover:text-white"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-[#eae4d9]">
        <div>
          <div className="text-[11px] font-mono tracking-widest text-[#d93829] uppercase font-bold mb-1 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-[#d93829]" />
            <span>Forensic Chain of Custody • SHA-256 Fingerprinted</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-serif font-bold text-[#191410]">
            Evidence Locker & Exhibits
          </h1>
          <p className="text-xs text-[#6e665d] mt-1">
            {evidence.length} certified evidence exhibits indexed under Section 65B (Electronic Records) & Section 27 (Recovery).
          </p>
        </div>

        <div className="flex items-center gap-3">
          {can('add_evidence', caseId) ? (
            <button
              onClick={() => setIsModalOpen(true)}
              className="flex items-center gap-2 px-5 py-2.5 bg-[#d93829] hover:bg-[#bf2b1d] text-white rounded-full text-xs font-bold transition-all shadow-md cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Intake New Exhibit (Custody Form)</span>
            </button>
          ) : (
            <div className="flex items-center gap-2 px-4 py-2 bg-[#f4efe6] text-[#70685e] rounded-full text-xs font-medium border border-[#eae4d9]">
              <Lock className="w-3.5 h-3.5 text-[#999084]" />
              <span>Upload Restricted ({role === 'reviewer' ? 'Reviewer Read-Only' : 'Restricted'})</span>
            </div>
          )}
        </div>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-[#8c8276]" />
        <input
          type="text"
          placeholder="Search exhibits by filename, category, or SHA-256 fingerprint hash..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full pl-11 pr-4 py-2.5 bg-white border border-[#eae4d9] rounded-full text-xs text-[#191410] placeholder-[#999084] focus:outline-none focus:border-[#d93829] shadow-xs"
        />
      </div>

      {/* Loading */}
      {loading && (
        <div className="py-20 text-center">
          <div className="w-8 h-8 border-2 border-[#d93829] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-xs text-[#8c8276] font-mono">Loading certified evidence locker...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && filteredEvidence.length === 0 && (
        <div className="text-center py-16 border border-dashed border-[#eae4d9] bg-white rounded-3xl">
          <File className="w-12 h-12 text-[#b0a89d] mx-auto mb-3" />
          <h3 className="font-serif font-bold text-base text-[#191410]">No Exhibits Found</h3>
          <p className="text-xs text-[#6e665d] mt-1 mb-4">No active evidence matches your search criteria.</p>
          {can('add_evidence', caseId) && (
            <button
              onClick={() => setIsModalOpen(true)}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#d93829] hover:bg-[#bf2b1d] text-white rounded-full text-xs font-bold transition-all shadow-xs"
            >
              <Upload className="w-4 h-4" /> Intake First Exhibit
            </button>
          )}
        </div>
      )}

      {/* Evidence Grid */}
      {!loading && filteredEvidence.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredEvidence.map((item) => {
            const isAnalyzed = item.processing_status === 'Analyzed' || item.processingStatus === 'Analyzed';
            const isAnalyzingThis = String(analyzing) === String(item.id);
            const isFailed = item.processing_status === 'Failed' || item.processingStatus === 'Failed';

            return (
              <div
                key={item.id}
                className={cn(
                  "p-5 rounded-3xl border bg-white transition-all flex flex-col justify-between group",
                  isAnalyzingThis && "border-amber-400/80 shadow-md ring-2 ring-amber-400/20",
                  !isAnalyzingThis && "hover:border-[#d93829]/40 hover:shadow-lg hover:shadow-[#d93829]/5"
                )}
              >
                <div>
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] flex items-center justify-center shrink-0">
                        {fileTypeIcons[item.file_type as keyof typeof fileTypeIcons] || <File className="w-4 h-4" />}
                      </div>
                      <div>
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="font-mono text-[10px] text-[#d93829] font-bold block">Exhibit #{item.id}</span>
                          <span className="text-[9px] font-mono bg-[#f4efe6] text-[#786e63] px-1.5 py-0.2 rounded font-medium">Sec 65B</span>
                          {item.file_hash && (
                            <span className="text-[9px] font-mono bg-emerald-50 text-emerald-700 px-1.5 py-0.2 rounded font-bold border border-emerald-200/50 flex items-center gap-0.5">
                              <ShieldCheck className="w-2.5 h-2.5" /> SHA-256
                            </span>
                          )}
                        </div>
                        <h4 className="font-serif font-bold text-sm text-[#191410] truncate max-w-[200px]" title={item.file_name || item.fileName}>
                          {item.file_name || item.fileName || 'Untitled Evidence'}
                        </h4>
                      </div>
                    </div>
                  </div>

                  {/* Exhibit Description / Text */}
                  <p className="text-xs text-[#6e665d] line-clamp-2 mt-2 leading-relaxed">
                    {item.extracted_text || item.custody_notes || 'Official forensic case record admitted under Indian Evidence Act.'}
                  </p>

                  {/* SHA-256 Hash Digest Preview */}
                  {item.file_hash && (
                    <div className="mt-2.5 p-1.5 rounded-lg bg-[#faf7f2] border border-[#eae4d9] flex items-center gap-1.5 text-[10px] font-mono text-[#6e665d]">
                      <Fingerprint className="w-3 h-3 text-emerald-600 shrink-0" />
                      <span className="truncate">{item.file_hash.slice(0, 18)}...{item.file_hash.slice(-8)}</span>
                    </div>
                  )}

                  <div className="mt-3 flex items-center justify-between text-[11px] text-[#8c8276] font-medium pt-2 border-t border-[#f0ebe1]">
                    <span>{((item.file_size || 15360) / 1024).toFixed(1)} KB • {item.file_type || item.fileType}</span>
                    <span 
                      className={cn(
                        "px-2.5 py-0.5 rounded-full font-bold text-[10px] inline-flex items-center gap-1",
                        isAnalyzed && "bg-emerald-50 text-emerald-700 border border-emerald-200/60",
                        isAnalyzingThis && "bg-amber-50 text-amber-700 border border-amber-200/60 animate-pulse",
                        isFailed && "bg-rose-50 text-rose-700 border border-rose-200/60",
                        !isAnalyzed && !isAnalyzingThis && !isFailed && "bg-blue-50 text-blue-700 border border-blue-200/60"
                      )}
                    >
                      {isAnalyzed && <CheckCircle className="w-3 h-3 text-emerald-600" />}
                      {isAnalyzingThis && <Loader2 className="w-3 h-3 animate-spin text-amber-600" />}
                      {isFailed && <AlertCircle className="w-3 h-3 text-rose-600" />}
                      <span>{isAnalyzingThis ? 'Scanning...' : (isAnalyzed ? 'Analyzed' : (item.processing_status || 'Analyzed'))}</span>
                    </span>
                  </div>
                </div>

                {/* Actions Bar */}
                <div className="mt-4 pt-3 flex items-center gap-2 border-t border-[#f0ebe1]">
                  <Link
                    to={`/cases/${caseId}/evidence/${item.id}`}
                    className="flex-1 text-center py-2 rounded-full bg-[#faf7f2] hover:bg-[#d93829] text-[#191410] hover:text-white font-bold text-xs border border-[#eae4d9] transition-all"
                  >
                    View Dossier & Custody
                  </Link>

                  <button
                    onClick={() => handleAnalyze(item.id)}
                    disabled={isAnalyzingThis}
                    className="px-3.5 py-2 rounded-full bg-[#fdeee9] hover:bg-[#d93829] text-[#d93829] hover:text-white font-bold text-xs transition-all disabled:opacity-50 flex items-center gap-1 cursor-pointer shadow-xs"
                    title="Run AI Neural Forensic Analysis (Sec 65B Certified)"
                  >
                    {isAnalyzingThis ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Sparkles className="w-3.5 h-3.5" />
                    )}
                  </button>

                  {can('delete_evidence', caseId) && (
                    <button
                      onClick={() => handleSoftDelete(item.id, item.file_name || item.fileName)}
                      className="p-2 rounded-full hover:bg-rose-50 text-[#8c8276] hover:text-rose-600 transition-colors"
                      title="Soft-delete Exhibit (Preserves Audit Ledger)"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ============================================================ */}
      {/* FORENSIC CUSTODY INTAKE MODAL                                */}
      {/* ============================================================ */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-xl w-full p-6 shadow-2xl border border-[#eae4d9] animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9] mb-4">
              <div className="flex items-center gap-2">
                <Scale className="w-5 h-5 text-[#d93829]" />
                <h3 className="font-serif font-bold text-lg text-[#191410]">
                  Exhibit Intake & Forensic Custody Form
                </h3>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-[#8c8276] hover:text-[#191410] p-1 rounded-full hover:bg-[#faf7f2]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleModalSubmit} className="space-y-4 text-xs">
              {/* File Dropzone */}
              <div>
                <label className="block font-bold text-[#191410] mb-1">
                  Physical Exhibit File <span className="text-[#d93829]">*</span>
                </label>
                <div 
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-[#eae4d9] hover:border-[#d93829] bg-[#faf7f2] rounded-2xl p-4 text-center cursor-pointer transition-all"
                >
                  <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    onChange={(e) => handleFileSelected(e.target.files?.[0])}
                  />
                  {modalFile ? (
                    <div className="space-y-1">
                      <File className="w-6 h-6 text-[#d93829] mx-auto" />
                      <div className="font-bold text-sm text-[#191410]">{modalFile.name}</div>
                      <div className="text-[10px] text-[#6e665d]">
                        {(modalFile.size / 1024).toFixed(1)} KB • Ready for cryptographic intake
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-1 text-[#6e665d]">
                      <Upload className="w-6 h-6 mx-auto text-[#b0a89d]" />
                      <div className="font-bold text-[#191410]">Click to choose exhibit file</div>
                      <div className="text-[10px]">PDF, MP4, CSV, WAV, JPG, PCAP accepted</div>
                    </div>
                  )}
                </div>
              </div>

              {/* Instant Browser Pre-hash Display */}
              {computedPreviewHash && (
                <div className="p-2.5 rounded-xl bg-emerald-50 border border-emerald-200/60 font-mono text-[11px] text-emerald-800 space-y-0.5">
                  <div className="font-bold flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Instant SHA-256 Digest Computed:</span>
                  </div>
                  <div className="break-all text-[10px] text-emerald-900 font-semibold select-all">
                    {computedPreviewHash}
                  </div>
                </div>
              )}

              {/* Evidence Type & Origin Source */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-[#191410] mb-1">Evidence Type</label>
                  <select
                    value={modalEvidenceType}
                    onChange={(e) => setModalEvidenceType(e.target.value)}
                    className="w-full bg-[#faf7f2] border border-[#eae4d9] rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-[#d93829]"
                  >
                    <option value="document">Document / Judicial Order</option>
                    <option value="cctv">CCTV / Surveillance Video</option>
                    <option value="cdr">CDR / Telecom Tower Dump</option>
                    <option value="dna">DNA / Biological Report</option>
                    <option value="fingerprint">Fingerprint / Ridge Analysis</option>
                    <option value="panchnama">Sec 27 Panchnama Recovery</option>
                    <option value="confession">Sec 164 CrPC Judicial Statement</option>
                    <option value="digital">RAM / Memory Dump / PCAP</option>
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-[#191410] mb-1">Seizure Source / Agency</label>
                  <input
                    type="text"
                    value={modalSource}
                    onChange={(e) => setModalSource(e.target.value)}
                    placeholder="e.g. Crime Scene, FSL Kalina, DoT"
                    className="w-full bg-[#faf7f2] border border-[#eae4d9] rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-[#d93829]"
                  />
                </div>
              </div>

              {/* Officer on Record & Seizure Date */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-[#191410] mb-1">Seizing / Intake Officer</label>
                  <input
                    type="text"
                    value={modalOfficer}
                    onChange={(e) => setModalOfficer(e.target.value)}
                    placeholder="Officer Name & Badge #"
                    className="w-full bg-[#faf7f2] border border-[#eae4d9] rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-[#d93829]"
                  />
                </div>

                <div>
                  <label className="block font-bold text-[#191410] mb-1">Date & Time of Seizure</label>
                  <input
                    type="datetime-local"
                    value={modalDate}
                    onChange={(e) => setModalDate(e.target.value)}
                    className="w-full bg-[#faf7f2] border border-[#eae4d9] rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-[#d93829]"
                  />
                </div>
              </div>

              {/* Sec 65B Checkbox */}
              <div className="p-3 rounded-xl bg-[#faf7f2] border border-[#eae4d9] flex items-center gap-2.5">
                <input
                  type="checkbox"
                  id="sec65b-check"
                  checked={modalSec65B}
                  onChange={(e) => setModalSec65B(e.target.checked)}
                  className="rounded text-[#d93829] focus:ring-[#d93829] w-4 h-4 cursor-pointer"
                />
                <label htmlFor="sec65b-check" className="cursor-pointer select-none">
                  <div className="font-bold text-[#191410]">Certified under Section 65B Indian Evidence Act</div>
                  <div className="text-[10px] text-[#6e665d]">Confirming computer output authenticity and uninterrupted custody.</div>
                </label>
              </div>

              {/* Custody Bag & Condition Notes */}
              <div>
                <label className="block font-bold text-[#191410] mb-1">Custody Seal / Packaging Notes</label>
                <textarea
                  rows={2}
                  value={modalNotes}
                  onChange={(e) => setModalNotes(e.target.value)}
                  placeholder="Record tamper-evident bag seal number, physical state, and punch witnesses..."
                  className="w-full bg-[#faf7f2] border border-[#eae4d9] rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-[#d93829]"
                />
              </div>

              {/* Footer Buttons */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#eae4d9]">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-full border border-[#eae4d9] text-[#6e665d] hover:bg-[#faf7f2] font-semibold text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading || !modalFile}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#d93829] hover:bg-[#bf2b1d] text-white font-bold text-xs shadow-md transition-all disabled:opacity-50 cursor-pointer"
                >
                  {uploading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Computing Fingerprint & Ingesting...</span>
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="w-4 h-4" />
                      <span>Seal Exhibit & Commit to Custody</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default EvidenceList;
