// src/pages/case/EvidenceList.tsx
import { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  Search, File, Image, Video, Music, FileText,
  CheckCircle, Clock, AlertCircle, Loader2, Upload, 
  Sparkles, ShieldCheck, X, Eye, Hash, Scale, Cpu, Calendar, Lock,
  Trash2, Fingerprint, Plus, AlertTriangle, ShieldAlert,
  Activity, RotateCcw, RefreshCw, Layers, Smartphone, MapPin, Radio
} from 'lucide-react';
import { evidenceService, jobService, caseService, physicalEvidenceService } from '../../services';
import { UnifiedCustodyTimeline } from '../../components/evidence/UnifiedCustodyTimeline';
import { Archive, Package } from 'lucide-react';
import { IntelligencePipeline } from '../../engine/IntelligencePipeline';
import { Evidence, BackgroundJob, EvidenceChecklistResponse } from '../../types';
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

  // Physical Evidence & Unified Custody State
  const [kindFilter, setKindFilter] = useState<'all' | 'digital' | 'physical'>('all');
  const [timelineExhibit, setTimelineExhibit] = useState<Evidence | null>(null);
  const [isPhysicalModalOpen, setIsPhysicalModalOpen] = useState(false);
  const [physCategory, setPhysCategory] = useState('weapon');
  const [physDesc, setPhysDesc] = useState('');
  const [physMarks, setPhysMarks] = useState('');
  const [physQty, setPhysQty] = useState('');
  const [physCondition, setPhysCondition] = useState('intact');
  const [physPackaging, setPhysPackaging] = useState('sealed_plastic_bag');
  const [physSeizedFrom, setPhysSeizedFrom] = useState('');
  const [physSeizedAt, setPhysSeizedAt] = useState('');
  const [physMalkhanaNo, setPhysMalkhanaNo] = useState('');
  const [physRack, setPhysRack] = useState('');
  const [physIsBio, setPhysIsBio] = useState(false);
  const [physIsFirearm, setPhysIsFirearm] = useState(false);
  const [physSubmitting, setPhysSubmitting] = useState(false);

  const handlePhysicalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId || !physDesc.trim()) return;
    setPhysSubmitting(true);
    try {
      await physicalEvidenceService.registerPhysicalEvidence(caseId, {
        category: physCategory,
        description: physDesc.trim(),
        identifying_marks: physMarks.trim() || undefined,
        quantity_or_weight: physQty.trim() || undefined,
        condition: physCondition,
        packaging: physPackaging,
        seized_from: physSeizedFrom.trim() || undefined,
        seized_at: physSeizedAt.trim() || undefined,
        malkhana_entry_number: physMalkhanaNo.trim() || undefined,
        rack_or_shelf: physRack.trim() || undefined,
        is_biological: physIsBio,
        is_firearm: physIsFirearm,
      });
      setIsPhysicalModalOpen(false);
      resetPhysicalForm();
      showToast('Physical Forensic Exhibit registered and logged to custody chain.');
      fetchEvidence();
    } catch (err: any) {
      alert(err?.message || 'Failed to register physical evidence.');
    } finally {
      setPhysSubmitting(false);
    }
  };

  const resetPhysicalForm = () => {
    setPhysDesc('');
    setPhysMarks('');
    setPhysQty('');
    setPhysSeizedFrom('');
    setPhysSeizedAt('');
    setPhysMalkhanaNo('');
    setPhysRack('');
    setPhysIsBio(false);
    setPhysIsFirearm(false);
  };

  // Background Jobs State
  const [jobs, setJobs] = useState<BackgroundJob[]>([]);
  const [isJobsPanelOpen, setIsJobsPanelOpen] = useState(false);
  const [retryingJobId, setRetryingJobId] = useState<number | null>(null);
  const [cancellingJobId, setCancellingJobId] = useState<number | null>(null);

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
  const [checklist, setChecklist] = useState<EvidenceChecklistResponse | null>(null);
  const [isChecklistOpen, setIsChecklistOpen] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchEvidence = async () => {
    if (!caseId) return;
    try {
      setLoading(true);
      const [data, chk] = await Promise.allSettled([
        evidenceService.getEvidenceForCase(caseId),
        caseService.getEvidenceChecklist(caseId),
      ]);
      if (data.status === 'fulfilled') setEvidence(data.value);
      if (chk.status === 'fulfilled') setChecklist(chk.value);
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

  // Live Server-Sent Events (SSE) Stream for Case Jobs
  useEffect(() => {
    if (!caseId) return;
    const cleanId = caseId.replace(/^C-/, '');

    // Initial load of background jobs
    jobService.getCaseJobs(cleanId).then(setJobs).catch(console.error);

    // Live SSE subscription with automatic fallback polling
    const unsubscribe = jobService.subscribeCaseEvents(cleanId, (event) => {
      if (event.type === 'job_progress' || event.type === 'job_started') {
        setJobs(prev => {
          const idx = prev.findIndex(j => j.id === event.job.id);
          if (idx >= 0) {
            const next = [...prev];
            next[idx] = event.job;
            return next;
          }
          return [event.job, ...prev];
        });
      } else if (event.type === 'job_completed') {
        setJobs(prev => prev.map(j => j.id === event.job.id ? event.job : j));
        showToast(`AI extraction & forensic scoring complete for Exhibit #${event.job.exhibit_id || event.job.id}!`);
        fetchEvidence();
      } else if (event.type === 'job_failed') {
        setJobs(prev => prev.map(j => j.id === event.job.id ? event.job : j));
        showToast(`Background job #${event.job.id} failed: ${event.job.error_message || 'Processing error'}`);
        fetchEvidence();
      } else if (event.type === 'jobs_poll') {
        setJobs(event.jobs || []);
      }
    });

    return () => unsubscribe();
  }, [caseId]);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(prev => (prev === msg ? null : prev));
    }, 4500);
  };

  const formatStage = (stage?: string): string => {
    if (!stage) return 'Queued';
    switch (stage) {
      case 'extract_text': return 'Extracting text (OCR/STT)';
      case 'chunk_text': return 'Splitting into chunks';
      case 'extract_entities_claims': return 'Finding entities & claims';
      case 'verify_citations': return 'Verifying citations';
      case 'detect_contradictions': return 'Checking contradictions';
      case 'classify_hypotheses': return 'Classifying hypotheses';
      case 'recalculate_scores': return 'Recalculating scores';
      case 'completed': return 'Analysis complete';
      case 'queued': return 'Queued';
      default: return stage.replace(/_/g, ' ');
    }
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
      // Returns immediately (<1s) with the newly queued exhibit and job ID!
      const uploaded = await evidenceService.uploadEvidence(caseId, modalFile, {
        source: modalSource,
        collected_by: modalOfficer || user?.full_name || 'Lead SIT Officer',
        collection_date: modalDate,
        custody_notes: modalNotes,
        evidence_type: modalEvidenceType,
        sec_65b_certificate_present: modalSec65B
      });

      showToast(`Exhibit "${modalFile.name}" intake complete. Background analysis queued.`);
      setIsModalOpen(false);
      setModalFile(null);
      setComputedPreviewHash(null);
      
      await fetchEvidence();
      if (caseId) {
        const freshJobs = await jobService.getCaseJobs(caseId);
        setJobs(freshJobs);
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
    try {
      const cleanEvId = String(evidenceId).replace(/^E-/, '');
      await evidenceService.analyzeEvidence(cleanEvId, caseId);
      showToast(`AI background analysis queued for Exhibit #${evidenceId}.`);
      if (caseId) {
        const freshJobs = await jobService.getCaseJobs(caseId);
        setJobs(freshJobs);
      }
      fetchEvidence();
    } catch (error) {
      console.error('Analysis queue failed:', error);
      showToast(`Failed to queue analysis for Exhibit #${evidenceId}.`);
    } finally {
      setAnalyzing(null);
    }
  };

  const handleRetryJob = async (jobId: number) => {
    setRetryingJobId(jobId);
    try {
      const retried = await jobService.retryJob(jobId);
      setJobs(prev => prev.map(j => j.id === jobId ? retried : j));
      showToast(`Job #${jobId} re-queued (resuming from last stage checkpoint).`);
      fetchEvidence();
    } catch (err: any) {
      console.error('Failed to retry job:', err);
      showToast(`Retry failed: ${err.message || 'Unknown error'}`);
    } finally {
      setRetryingJobId(null);
    }
  };

  const handleCancelJob = async (jobId: number) => {
    setCancellingJobId(jobId);
    try {
      await jobService.cancelJob(jobId);
      setJobs(prev => prev.map(j => j.id === jobId ? { ...j, status: 'cancelled' } : j));
      showToast(`Job #${jobId} cancelled.`);
      fetchEvidence();
    } catch (err: any) {
      console.error('Failed to cancel job:', err);
      showToast(`Cancel failed: ${err.message || 'Unknown error'}`);
    } finally {
      setCancellingJobId(null);
    }
  };

  const activeJobs = jobs.filter(j => ['queued', 'running'].includes(j.status));

  const filteredEvidence = (evidence || []).filter(e => {
    if (!e || e.is_deleted) return false;
    if (kindFilter === 'digital' && e.evidence_kind === 'physical') return false;
    if (kindFilter === 'physical' && e.evidence_kind !== 'physical') return false;
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
            <span>Forensic Chain of Custody • Live Extraction Pipeline</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-serif font-bold text-[#191410]">
            Evidence Locker & Exhibits
          </h1>
          <p className="text-xs text-[#6e665d] mt-1">
            {evidence.length} certified evidence exhibits indexed under Section 65B (Electronic Records) & Section 27 (Recovery).
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Background Jobs Queue Toggle */}
          <button
            onClick={() => setIsJobsPanelOpen(prev => !prev)}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 rounded-full border text-xs font-bold transition-all shadow-xs cursor-pointer",
              isJobsPanelOpen
                ? "bg-[#191410] text-[#faf7f2] border-[#191410]"
                : "bg-white hover:bg-[#faf7f2] text-[#191410] border-[#eae4d9]"
            )}
          >
            <Activity className={cn("w-4 h-4", activeJobs.length > 0 ? "text-[#d93829] animate-pulse" : "text-[#8c8276]")} />
            <span>Jobs</span>
            {activeJobs.length > 0 ? (
              <span className="px-1.5 py-0.2 rounded-full bg-[#d93829] text-white text-[10px] font-mono animate-pulse">
                {activeJobs.length} active
              </span>
            ) : (
              <span className="text-[10px] text-[#8c8276] font-mono font-normal">
                ({jobs.length})
              </span>
            )}
          </button>

          {can('add_evidence', caseId) && (
            <Link
              to={`/cases/${caseId}/field-capture`}
              className="flex items-center gap-2 px-4 py-2.5 bg-purple-700 hover:bg-purple-800 text-white rounded-full text-xs font-bold transition-all shadow-md cursor-pointer"
              title="Photograph or record evidence live at the crime scene with on-device hashing and GPS location"
            >
              <Smartphone className="w-4 h-4" />
              <span>Mobile Field Capture</span>
            </Link>
          )}

          <Link
            to={`/cases/${caseId}/connectors`}
            className="flex items-center gap-2 px-4 py-2.5 bg-white hover:bg-[#faf7f2] text-[#191410] border border-[#eae4d9] rounded-full text-xs font-bold transition-all shadow-xs cursor-pointer"
            title="Automated live evidence ingestion from watch folders, email inboxes, and webhooks"
          >
            <Radio className="w-4 h-4 text-emerald-600" />
            <span>Live Connectors</span>
          </Link>

          <Link
            to={`/cases/${caseId}/data-quality`}
            className="flex items-center gap-2 px-4 py-2.5 bg-white hover:bg-[#faf7f2] text-[#191410] border border-[#eae4d9] rounded-full text-xs font-bold transition-all shadow-xs cursor-pointer"
            title="Exhibit 4-Pillar Quality Audit (Confidence, Hashes, 65B, Language)"
          >
            <ShieldCheck className="w-4 h-4 text-[#d93829]" />
            <span>Data-Quality Scoring</span>
          </Link>

          <Link
            to={`/cases/${caseId}/malkhana`}
            className="flex items-center gap-2 px-4 py-2.5 bg-white hover:bg-[#faf7f2] text-[#191410] border border-[#eae4d9] rounded-full text-xs font-bold transition-all shadow-xs cursor-pointer"
            title="Station Muddimalkhana inventory, rack allocations, and two-person issues"
          >
            <Archive className="w-4 h-4 text-amber-700" />
            <span>Malkhana Register</span>
          </Link>

          {can('add_evidence', caseId) && (
            <button
              onClick={() => setIsPhysicalModalOpen(true)}
              className="flex items-center gap-2 px-4 py-2.5 bg-amber-600 hover:bg-amber-700 text-white rounded-full text-xs font-bold transition-all shadow-md cursor-pointer"
              title="Register physical evidence (weapons, clothing, biological samples, vehicles)"
            >
              <Package className="w-4 h-4" />
              <span>+ Physical Article</span>
            </button>
          )}

          {can('add_evidence', caseId) ? (
            <button
              onClick={() => setIsModalOpen(true)}
              className="flex items-center gap-2 px-5 py-2.5 bg-[#d93829] hover:bg-[#bf2b1d] text-white rounded-full text-xs font-bold transition-all shadow-md cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Intake Digital File</span>
            </button>
          ) : (
            <div className="flex items-center gap-2 px-4 py-2 bg-[#f4efe6] text-[#70685e] rounded-full text-xs font-medium border border-[#eae4d9]">
              <Lock className="w-3.5 h-3.5 text-[#999084]" />
              <span>Upload Restricted ({role === 'reviewer' ? 'Reviewer Read-Only' : 'Restricted'})</span>
            </div>
          )}
        </div>
      </div>

      {/* Offence Protocol Evidence Checklist Banner */}
      {checklist && (
        <div className="p-4 rounded-2xl bg-white border border-[#eae4d9] shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Scale className="w-4 h-4 text-[#d93829]" />
              <span className="text-xs font-bold text-[#191410] font-serif">
                Offence Evidence Protocol: {checklist.offence_category.toUpperCase()}
              </span>
              <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${
                checklist.mandatory_missing_count > 0 
                  ? 'bg-[#fdeee9] text-[#d93829]' 
                  : 'bg-[#ebf7ee] text-[#1b7a37]'
              }`}>
                {checklist.present_count}/{checklist.total_expected} Gathered
                {checklist.mandatory_missing_count > 0 && ` (${checklist.mandatory_missing_count} Missing Mandatory)`}
              </span>
            </div>

            <button
              onClick={() => setIsChecklistOpen(!isChecklistOpen)}
              className="text-xs font-semibold text-[#1b64b8] hover:underline cursor-pointer"
            >
              {isChecklistOpen ? 'Hide Checklist ▲' : 'Show Full Statutory Checklist ▼'}
            </button>
          </div>

          {/* Quick Missing Badges */}
          {!isChecklistOpen && checklist.mandatory_missing_count > 0 && (
            <div className="flex flex-wrap items-center gap-2 text-[11px] pt-1 border-t border-[#f0ebe1]">
              <span className="text-[#8c8276] font-medium">Missing:</span>
              {checklist.items.filter(i => i.status === 'missing' && i.mandatory).map((item, idx) => (
                <span 
                  key={idx} 
                  className="px-2 py-0.5 rounded-md bg-[#fdeee9] text-[#d93829] font-medium border border-[#f5b8ad]"
                  title={item.consequence_if_missing}
                >
                  ⚠️ {item.title} ({item.legal_provision})
                </span>
              ))}
            </div>
          )}

          {/* Expanded Full Checklist */}
          {isChecklistOpen && (
            <div className="pt-2 border-t border-[#f0ebe1] grid grid-cols-1 md:grid-cols-2 gap-2.5 text-xs">
              {checklist.items.map((item, idx) => {
                const isPresent = item.status === 'present';
                return (
                  <div 
                    key={idx}
                    className={`p-2.5 rounded-xl border text-[11px] flex items-start justify-between gap-2 ${
                      isPresent ? 'border-[#9fe0b2] bg-[#f8fdf9]' : 'border-[#f5b8ad] bg-[#fffbf9]'
                    }`}
                  >
                    <div>
                      <div className="font-bold text-[#191410] flex items-center gap-1.5">
                        <span>{isPresent ? '✓' : '⚠️'}</span>
                        <span>{item.title}</span>
                      </div>
                      <div className="text-[10px] text-[#70685e] mt-0.5 font-mono">{item.legal_provision}</div>
                      {!isPresent && (
                        <div className="text-[10px] text-[#d93829] mt-0.5">{item.consequence_if_missing}</div>
                      )}
                    </div>
                    <span className={`text-[9px] font-mono uppercase px-1.5 py-0.2 rounded font-bold shrink-0 ${
                      isPresent ? 'bg-[#ebf7ee] text-[#1b7a37]' : 'bg-[#fdeee9] text-[#d93829]'
                    }`}>
                      {item.status}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Background Jobs Drawer / Panel */}
      {isJobsPanelOpen && (
        <div className="p-5 rounded-3xl bg-[#faf7f2] border border-[#eae4d9] space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9]">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-[#d93829]" />
              <h3 className="font-serif font-bold text-sm text-[#191410]">
                Background Processing Jobs & Worker Progress
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white border border-[#eae4d9] text-[#6e665d]">
                {jobs.length} total • {activeJobs.length} active
              </span>
            </div>
            <button
              onClick={() => setIsJobsPanelOpen(false)}
              className="text-[#8c8276] hover:text-[#191410] p-1 rounded-full hover:bg-white"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {jobs.length === 0 ? (
            <p className="text-xs text-[#8c8276] text-center py-4 font-mono">
              No background jobs recorded for this case yet.
            </p>
          ) : (
            <div className="space-y-3">
              {jobs.slice(0, 10).map((j) => {
                const isRunning = j.status === 'running';
                const isQueued = j.status === 'queued';
                const isFailed = j.status === 'failed';
                const isSucceeded = j.status === 'succeeded';
                const isCancelled = j.status === 'cancelled';

                return (
                  <div key={j.id} className="p-3.5 rounded-2xl bg-white border border-[#eae4d9] space-y-2.5">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-[#d93829]">Job #{j.id}</span>
                        <span className="font-semibold text-[#191410]">
                          {j.job_type === 'process_evidence' ? `Exhibit Processing (Exhibit #${j.exhibit_id})` : j.job_type}
                        </span>
                        <span className="text-[10px] text-[#8c8276] font-mono">
                          Attempt {j.attempt_count}/{j.max_attempts}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className={cn(
                          "px-2 py-0.5 rounded-full font-bold text-[10px] uppercase font-mono inline-flex items-center gap-1",
                          isRunning && "bg-amber-50 text-amber-800 border border-amber-300",
                          isQueued && "bg-blue-50 text-blue-800 border border-blue-200",
                          isFailed && "bg-rose-50 text-rose-800 border border-rose-300",
                          isSucceeded && "bg-emerald-50 text-emerald-800 border border-emerald-300",
                          isCancelled && "bg-gray-100 text-gray-700 border border-gray-300"
                        )}>
                          {isRunning && <Loader2 className="w-2.5 h-2.5 animate-spin text-amber-600" />}
                          {isQueued && <Clock className="w-2.5 h-2.5 text-blue-600" />}
                          {isFailed && <AlertCircle className="w-2.5 h-2.5 text-rose-600" />}
                          {isSucceeded && <CheckCircle className="w-2.5 h-2.5 text-emerald-600" />}
                          <span>{j.status}</span>
                        </span>

                        {(isRunning || isQueued) && (
                          <button
                            onClick={() => handleCancelJob(j.id)}
                            disabled={cancellingJobId === j.id}
                            className="text-[10px] px-2.5 py-0.5 rounded bg-gray-100 hover:bg-gray-200 text-gray-700 transition cursor-pointer"
                          >
                            {cancellingJobId === j.id ? 'Cancelling...' : 'Cancel'}
                          </button>
                        )}

                        {isFailed && (
                          <button
                            onClick={() => handleRetryJob(j.id)}
                            disabled={retryingJobId === j.id}
                            className="text-[10px] px-2.5 py-0.5 rounded bg-[#fdeee9] hover:bg-[#d93829] text-[#d93829] hover:text-white font-bold transition flex items-center gap-1 cursor-pointer"
                          >
                            {retryingJobId === j.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <RotateCcw className="w-3 h-3" />}
                            <span>Retry</span>
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Progress Bar & Stage Indicator */}
                    <div className="space-y-1">
                      <div className="flex justify-between text-[11px] text-[#6e665d]">
                        <span className="font-medium flex items-center gap-1.5">
                          {isRunning && <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-ping" />}
                          {formatStage(j.current_stage)}
                        </span>
                        <span className="font-mono font-bold text-[#191410]">{Math.round(j.progress_pct)}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-[#f0ebe1] rounded-full overflow-hidden">
                        <div 
                          className={cn(
                            "h-full transition-all duration-300 rounded-full",
                            isFailed ? "bg-rose-500" : isSucceeded ? "bg-emerald-500" : "bg-[#d93829]"
                          )}
                          style={{ width: `${Math.max(5, j.progress_pct)}%` }}
                        />
                      </div>
                    </div>

                    {j.error_message && (
                      <p className="text-[10px] text-rose-700 font-mono bg-rose-50 p-2 rounded border border-rose-200/50">
                        {j.error_message}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Filter Tabs & Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
          {[
            { id: 'all', label: `All Exhibits (${evidence.length})` },
            { id: 'digital', label: `Digital Media (${evidence.filter(e => e.evidence_kind !== 'physical').length})` },
            { id: 'physical', label: `Physical Articles (${evidence.filter(e => e.evidence_kind === 'physical').length})` },
          ].map(f => (
            <button
              key={f.id}
              onClick={() => setKindFilter(f.id as any)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-full border transition-all cursor-pointer whitespace-nowrap ${
                kindFilter === f.id
                  ? 'bg-[#191410] text-white border-[#191410] shadow-xs'
                  : 'bg-white text-[#59524c] border-[#eae4d9] hover:bg-[#faf7f2]'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-[#8c8276]" />
          <input
            type="text"
            placeholder="Search exhibits by name, category, or hash..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-11 pr-4 py-2 bg-white border border-[#eae4d9] rounded-full text-xs text-[#191410] placeholder-[#999084] focus:outline-none focus:border-[#d93829] shadow-xs"
          />
        </div>
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
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#d93829] hover:bg-[#bf2b1d] text-white rounded-full text-xs font-bold transition-all shadow-xs cursor-pointer"
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
            const cleanExhibitId = String(item.id).replace(/^E-/, '');
            const exhibitJob = jobs.find(j => 
              String(j.exhibit_id) === cleanExhibitId &&
              ['queued', 'running', 'failed'].includes(j.status)
            );

            const isJobRunning = exhibitJob?.status === 'running';
            const isJobQueued = exhibitJob?.status === 'queued';
            const isJobFailed = exhibitJob?.status === 'failed' || item.processing_status === 'Failed';
            const isAnalyzed = (item.processing_status === 'Analyzed' || item.processingStatus === 'Analyzed') && !isJobRunning && !isJobQueued;
            const isAnalyzingThis = String(analyzing) === String(item.id) || isJobRunning;

            return (
              <div
                key={item.id}
                className={cn(
                  "p-5 rounded-3xl border bg-white transition-all flex flex-col justify-between group",
                  isAnalyzingThis && "border-amber-400/80 shadow-md ring-2 ring-amber-400/20",
                  isJobFailed && "border-rose-300 shadow-xs",
                  !isAnalyzingThis && !isJobFailed && "hover:border-[#d93829]/40 hover:shadow-lg hover:shadow-[#d93829]/5"
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
                          {item.evidence_kind === 'physical' ? (
                            <span className="text-[9px] font-mono bg-red-100 text-[#d93829] border border-red-200 px-1.5 py-0.2 rounded font-bold flex items-center gap-0.5">
                              <Package className="w-2.5 h-2.5" /> PHYSICAL
                            </span>
                          ) : (
                            <span className="text-[9px] font-mono bg-blue-50 text-blue-800 border border-blue-200 px-1.5 py-0.2 rounded font-medium flex items-center gap-0.5">
                              <FileText className="w-2.5 h-2.5" /> DIGITAL
                            </span>
                          )}
                          {item.evidence_kind !== 'physical' && (
                            <span className="text-[9px] font-mono bg-[#f4efe6] text-[#786e63] px-1.5 py-0.2 rounded font-medium">Sec 65B</span>
                          )}
                          {item.file_hash && (
                            <span className="text-[9px] font-mono bg-emerald-50 text-emerald-700 px-1.5 py-0.2 rounded font-bold border border-emerald-200/50 flex items-center gap-0.5">
                              <ShieldCheck className="w-2.5 h-2.5" /> SHA-256
                            </span>
                          )}
                          {item.is_field_captured && (
                            <span className="text-[9px] font-mono bg-purple-100 text-purple-900 border border-purple-300 px-1.5 py-0.2 rounded font-bold flex items-center gap-1" title="Captured live in the field with on-device SHA-256 and GPS location">
                              <Smartphone className="w-2.5 h-2.5 text-purple-700" /> Field Captured
                            </span>
                          )}
                          {item.is_demo_fixture || item.extraction_mode === 'demo_fixture' ? (
                            <span className="text-[9px] font-mono bg-amber-50 text-amber-800 px-1.5 py-0.5 rounded font-bold border border-amber-300 flex items-center gap-1" title="Pre-calibrated demo exhibit dossier">
                              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" /> Demo fixture
                            </span>
                          ) : (
                            <span className="text-[9px] font-mono bg-emerald-50 text-emerald-800 px-1.5 py-0.5 rounded font-bold border border-emerald-300 flex items-center gap-1" title="Processed through live forensic extraction pipeline">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Extracted live
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

                  {/* Mobile Field Provenance Metatag */}
                  {item.is_field_captured && (
                    <div className="mt-2 p-1.5 rounded-lg bg-purple-50/70 border border-purple-200/80 flex items-center justify-between text-[10px] font-mono text-purple-900">
                      <span className="flex items-center gap-1 truncate max-w-[200px]" title={item.field_location_name || 'Scene GPS'}>
                        <MapPin className="w-3 h-3 text-purple-700 shrink-0" />
                        <span className="truncate">
                          {item.field_location_name || (item.field_latitude ? `GPS: ${item.field_latitude.toFixed(4)}, ${item.field_longitude?.toFixed(4)}` : 'On-Scene Recovery')}
                        </span>
                      </span>
                      {item.field_tamper_seal_number && (
                        <span className="text-purple-700 font-bold shrink-0">{item.field_tamper_seal_number}</span>
                      )}
                    </div>
                  )}

                  {/* Active Job Progress Bar on Card */}
                  {exhibitJob && (isJobRunning || isJobQueued) && (
                    <div className="mt-3 p-2.5 rounded-xl bg-amber-50/70 border border-amber-200/60 space-y-1.5">
                      <div className="flex items-center justify-between text-[10px] font-mono">
                        <span className="font-bold text-amber-900 flex items-center gap-1.5">
                          <Loader2 className="w-3 h-3 animate-spin text-amber-700" />
                          <span>{formatStage(exhibitJob.current_stage)}</span>
                        </span>
                        <span className="font-bold text-amber-800">{Math.round(exhibitJob.progress_pct)}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-amber-200/50 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#d93829] rounded-full transition-all duration-300"
                          style={{ width: `${Math.max(5, exhibitJob.progress_pct)}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Failed Job Card Notice & Quick Retry */}
                  {isJobFailed && exhibitJob && (
                    <div className="mt-3 p-2.5 rounded-xl bg-rose-50 border border-rose-200/60 space-y-2">
                      <div className="flex items-center justify-between text-[10px] text-rose-800">
                        <span className="font-bold flex items-center gap-1">
                          <AlertCircle className="w-3 h-3 text-rose-600" />
                          <span>Analysis Interrupted</span>
                        </span>
                        <button
                          onClick={() => handleRetryJob(exhibitJob.id)}
                          disabled={retryingJobId === exhibitJob.id}
                          className="px-2 py-0.5 rounded bg-rose-600 hover:bg-rose-700 text-white font-bold text-[10px] transition flex items-center gap-1 cursor-pointer"
                        >
                          {retryingJobId === exhibitJob.id ? <Loader2 className="w-2.5 h-2.5 animate-spin" /> : <RotateCcw className="w-2.5 h-2.5" />}
                          <span>Resume</span>
                        </button>
                      </div>
                      <p className="text-[10px] text-rose-700 font-mono line-clamp-2">
                        {exhibitJob.error_message || 'Background pipeline halted.'}
                      </p>
                    </div>
                  )}

                  <div className="mt-3 flex items-center justify-between text-[11px] text-[#8c8276] font-medium pt-2 border-t border-[#f0ebe1]">
                    <span>{((item.file_size || 15360) / 1024).toFixed(1)} KB • {item.file_type || item.fileType}</span>
                    <span 
                      className={cn(
                        "px-2.5 py-0.5 rounded-full font-bold text-[10px] inline-flex items-center gap-1",
                        isAnalyzed && "bg-emerald-50 text-emerald-700 border border-emerald-200/60",
                        (isAnalyzingThis || isJobQueued) && "bg-amber-50 text-amber-700 border border-amber-200/60 animate-pulse",
                        isJobFailed && "bg-rose-50 text-rose-700 border border-rose-200/60",
                        !isAnalyzed && !isAnalyzingThis && !isJobFailed && !isJobQueued && "bg-blue-50 text-blue-700 border border-blue-200/60"
                      )}
                    >
                      {isAnalyzed && <CheckCircle className="w-3 h-3 text-emerald-600" />}
                      {(isAnalyzingThis || isJobQueued) && <Loader2 className="w-3 h-3 animate-spin text-amber-600" />}
                      {isJobFailed && <AlertCircle className="w-3 h-3 text-rose-600" />}
                      <span>
                        {isJobRunning ? 'Processing...' : isJobQueued ? 'Queued...' : (isAnalyzed ? 'Analyzed' : (item.processing_status || 'Analyzed'))}
                      </span>
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
                    disabled={isAnalyzingThis || isJobQueued}
                    className="px-3.5 py-2 rounded-full bg-[#fdeee9] hover:bg-[#d93829] text-[#d93829] hover:text-white font-bold text-xs transition-all disabled:opacity-50 flex items-center gap-1 cursor-pointer shadow-xs"
                    title="Queue AI Neural Forensic Background Processing"
                  >
                    {isAnalyzingThis || isJobQueued ? (
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
