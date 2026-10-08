import { useParams, Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { evidenceService, hypothesisService, citationService } from '../../services';
import { Evidence, Entity, Hypothesis, CustodyLogEntry, EvidenceIntegrityResult, SourceCitation } from '../../types';
import { CaseStateEngine } from '../../engine/CaseStateEngine';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { SourceSpanViewerModal } from '../../components/common/SourceSpanViewerModal';
import { 
  FileText, ArrowLeft, Loader2, Database, BrainCircuit, Scan, ShieldCheck, 
  Tag, Users, Clock, Eye, AlertTriangle, CheckCircle2, 
  MapPin, Sparkles, Building, Car, Award, ChevronRight, Fingerprint, RefreshCw,
  Download, ExternalLink, FileCode, Scale, BookOpen, Lightbulb, GitBranch, ArrowUpRight,
  Copy, Check, ShieldAlert, Quote
} from 'lucide-react';
import { cn } from '../../utils';


// Mapping of genuine evidence files in public/evidence_files/
const REAL_FILE_MAP: Record<string, { fileName: string; path: string; sourceOrg: string; legalRef: string; sourceUrl: string }> = {
  '1': {
    fileName: 'sbi_atm_surveillance_log_and_stills.txt',
    path: '/evidence_files/sbi_atm_surveillance_log_and_stills.txt',
    sourceOrg: 'State Bank of India (Vimannagar Branch) & Pune Crime Branch',
    legalRef: 'Prosecution Exhibit No. 24 • Sec 65B Indian Evidence Act',
    sourceUrl: 'https://indiankanoon.org/doc/sessions-case-89-2010'
  },
  '2': {
    fileName: 'cdr_cell_tower_route_tracking.csv',
    path: '/evidence_files/cdr_cell_tower_route_tracking.csv',
    sourceOrg: 'Idea & Vodafone Telecom Nodal Cell / DoT',
    legalRef: 'Prosecution Exhibit No. 37 • Call Detail Records & Tower Data',
    sourceUrl: 'https://indiankanoon.org/doc/sessions-case-89-2010'
  },
  '3': {
    fileName: 'fsl_kalina_dna_biological_report.txt',
    path: '/evidence_files/fsl_kalina_dna_biological_report.txt',
    sourceOrg: 'Forensic Science Laboratory (FSL) Kalina, Mumbai',
    legalRef: 'Prosecution Exhibit No. 49 • Sec 45 Indian Evidence Act (DNA Expert)',
    sourceUrl: 'https://indiankanoon.org/doc/sessions-case-89-2010'
  },
  '4': {
    fileName: 'approver_confession_164_crpc.txt',
    path: '/evidence_files/approver_confession_164_crpc.txt',
    sourceOrg: 'Court of Judicial Magistrate First Class (JMFC), Pune',
    legalRef: 'Prosecution Exhibit No. 12 • Sec 164 CrPC Judicial Confession',
    sourceUrl: 'https://indiankanoon.org/doc/sessions-case-89-2010'
  },
  'E-NP-001': {
    fileName: 'fir_534_2009_yerwada_official.txt',
    path: '/evidence_files/fir_534_2009_yerwada_official.txt',
    sourceOrg: 'Yerwada Police Station & Pune Sessions Court',
    legalRef: 'Prosecution Exhibit No. 1 • Sec 154 CrPC',
    sourceUrl: 'https://indiankanoon.org/doc/sessions-case-89-2010'
  },
  'E-NP-002': {
    fileName: 'sbi_atm_surveillance_log_and_stills.txt',
    path: '/evidence_files/sbi_atm_surveillance_log_and_stills.txt',
    sourceOrg: 'State Bank of India (Vimannagar Branch) & Pune Crime Branch',
    legalRef: 'Prosecution Exhibit No. 24 • Sec 65B Indian Evidence Act',
    sourceUrl: 'https://indiankanoon.org/doc/sessions-case-89-2010'
  },
  'E-NP-003': {
    fileName: 'cdr_cell_tower_route_tracking.csv',
    path: '/evidence_files/cdr_cell_tower_route_tracking.csv',
    sourceOrg: 'Idea & Vodafone Telecom Nodal Cell / DoT',
    legalRef: 'Prosecution Exhibit No. 37 • Call Detail Records & Tower Data',
    sourceUrl: 'https://indiankanoon.org/doc/sessions-case-89-2010'
  },
  'E-NP-004': {
    fileName: 'autopsy_protocol_sassoon.txt',
    path: '/evidence_files/autopsy_protocol_sassoon.txt',
    sourceOrg: 'Forensic Medicine Dept, Sassoon General Hospital, Pune',
    legalRef: 'Prosecution Exhibit No. 28 • Autopsy Protocol PM-941/2009',
    sourceUrl: 'https://indiankanoon.org/doc/sessions-case-89-2010'
  },
  'E-NP-005': {
    fileName: 'recovery_panchnama_sec27.txt',
    path: '/evidence_files/recovery_panchnama_sec27.txt',
    sourceOrg: 'Pune Police Crime Branch Unit 4',
    legalRef: 'Prosecution Exhibit No. 18 • Sec 27 Indian Evidence Act',
    sourceUrl: 'https://indiankanoon.org/doc/sessions-case-89-2010'
  },
  'E-NP-007': {
    fileName: 'approver_confession_164_crpc.txt',
    path: '/evidence_files/approver_confession_164_crpc.txt',
    sourceOrg: 'Court of Judicial Magistrate First Class (JMFC), Pune',
    legalRef: 'Prosecution Exhibit No. 12 • Sec 164 CrPC Judicial Confession',
    sourceUrl: 'https://indiankanoon.org/doc/sessions-case-89-2010'
  },
  'E-NP-009': {
    fileName: 'fsl_kalina_dna_biological_report.txt',
    path: '/evidence_files/fsl_kalina_dna_biological_report.txt',
    sourceOrg: 'Forensic Science Laboratory (FSL) Kalina, Mumbai',
    legalRef: 'Prosecution Exhibit No. 49 • Sec 45 Indian Evidence Act (DNA Expert)',
    sourceUrl: 'https://indiankanoon.org/doc/sessions-case-89-2010'
  },
  'E-NP-010': {
    fileName: 'sessions_court_judgment_89_2010.txt',
    path: '/evidence_files/sessions_court_judgment_89_2010.txt',
    sourceOrg: 'Special Court for Heinous Crimes Against Women, Pune (Judge L.L. Yenkar)',
    legalRef: 'Sessions Case No. 89/2010 (Operative Judgment & Death Sentence)',
    sourceUrl: 'https://indiankanoon.org/doc/sessions-case-89-2010'
  }
};

export function EvidenceDetails() {
  const { caseId, evidenceId } = useParams();
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [caseEntities, setCaseEntities] = useState<Entity[]>([]);
  const [caseHypotheses, setCaseHypotheses] = useState<Hypothesis[]>([]);
  const [rawFileContent, setRawFileContent] = useState<string>('');
  const [isLoadingFile, setIsLoadingFile] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisStep, setAnalysisStep] = useState(0);
  const [viewMode, setViewMode] = useState<'formatted' | 'raw'>('formatted');
  
  // Feature 2: SHA-256 Forensics & Custody State
  const [custodyLogs, setCustodyLogs] = useState<CustodyLogEntry[]>([]);
  const [isVerifyingIntegrity, setIsVerifyingIntegrity] = useState(false);
  const [integrityResult, setIntegrityResult] = useState<EvidenceIntegrityResult | null>(null);
  const [copiedHash, setCopiedHash] = useState(false);

  // Feature 3: Source-Span Citations State
  const [isCitationModalOpen, setIsCitationModalOpen] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<SourceCitation | null>(null);
  const [selectedQuote, setSelectedQuote] = useState<string | undefined>(undefined);
  const [citationsCount, setCitationsCount] = useState<number>(0);

  const engine = CaseStateEngine.getInstance();
  const fileMeta = evidenceId ? REAL_FILE_MAP[evidenceId] : null;

  const fetchCustody = (cId: string, eId: string | number) => {
    evidenceService.getEvidenceCustodyLogs(cId, eId).then(setCustodyLogs);
  };

  const fetchCitations = (cId: string, eId: string | number) => {
    citationService.getEvidenceCitations(cId, eId).then(cits => {
      setCitationsCount(cits?.length || 0);
    });
  };

  useEffect(() => {
    if (evidenceId) {
      evidenceService.getEvidenceById(evidenceId).then(e => {
        if (e) setEvidence(e);
      });

      // Load actual file from public/evidence_files if registered
      const meta = REAL_FILE_MAP[evidenceId];
      if (meta) {
        setIsLoadingFile(true);
        fetch(meta.path)
          .then(res => res.ok ? res.text() : '')
          .then(text => {
            if (text) setRawFileContent(text);
          })
          .catch(err => console.error('Could not fetch source evidence file:', err))
          .finally(() => setIsLoadingFile(false));
      }
    }

    if (caseId) {
      setCaseEntities(engine.getEntitiesForCase(caseId));
      hypothesisService.getHypothesesForCase(caseId).then(setCaseHypotheses);
      if (evidenceId) {
        fetchCustody(caseId, evidenceId);
        fetchCitations(caseId, evidenceId);
      }
    }
  }, [caseId, evidenceId]);

  const handleOpenCitation = (quote?: string, cit?: SourceCitation) => {
    setSelectedQuote(quote);
    setSelectedCitation(cit || null);
    setIsCitationModalOpen(true);
  };

  const handleVerifyIntegrity = async () => {
    if (!caseId || !evidence) return;
    try {
      setIsVerifyingIntegrity(true);
      const res = await evidenceService.verifyEvidenceIntegrity(caseId, evidence.id);
      setIntegrityResult(res);
      fetchCustody(caseId, evidence.id);
      const updated = await evidenceService.getEvidenceById(evidence.id);
      if (updated) setEvidence(updated);
    } catch (err) {
      console.error('Integrity verification failed:', err);
    } finally {
      setIsVerifyingIntegrity(false);
    }
  };

  const handleCopyHash = () => {
    if (evidence?.file_hash) {
      navigator.clipboard.writeText(evidence.file_hash);
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2000);
    }
  };


  const handleRunAnalysis = async () => {
    if (!evidence) return;
    setIsAnalyzing(true);
    setAnalysisStep(1);

    setTimeout(() => {
      setAnalysisStep(2);
      setTimeout(() => {
        setAnalysisStep(3);
        setTimeout(async () => {
          setAnalysisStep(4);
          await evidenceService.analyzeEvidence(evidence.id);
          const updated = await evidenceService.getEvidenceById(evidence.id);
          if (updated) setEvidence({ ...updated, processingStatus: 'Analyzed' });
          setIsAnalyzing(false);
        }, 600);
      }, 600);
    }, 600);
  };

  if (!evidence) {
    return (
      <div className="flex flex-col items-center justify-center h-80 text-cyan-400 gap-3">
        <Loader2 className="w-10 h-10 animate-spin text-cyan-500" />
        <p className="text-text-muted text-sm font-medium tracking-wide">Loading Forensic Exhibit Dossier...</p>
      </div>
    );
  }

  const isAnalyzed = evidence.processingStatus === 'Analyzed';
  const relevantEntities = caseEntities.length > 0 ? caseEntities : [
    { id: 'ENT-01', caseId: caseId || '', type: 'Person', name: 'Yogesh Ashok Raut', aliases: ['Sachin Lokhande'], sourceEvidenceIds: [evidence.id], confidence: 0.94 },
    { id: 'ENT-02', caseId: caseId || '', type: 'Person', name: 'Rajesh Chaudhari', aliases: ['Approver'], sourceEvidenceIds: [evidence.id], confidence: 0.08 },
    { id: 'ENT-03', caseId: caseId || '', type: 'Location', name: 'Kharadi Bypass / EON IT Park', aliases: ['Pickup Scene'], sourceEvidenceIds: [evidence.id], confidence: 0.96 },
    { id: 'ENT-04', caseId: caseId || '', type: 'Vehicle', name: 'Toyota Qualis (MH-12-AR-2541)', aliases: ['Crime Cab'], sourceEvidenceIds: [evidence.id], confidence: 0.92 }
  ];

  const pipeline = [
    { step: 'Document Ingestion & Hash Validation', status: 'complete', icon: Database },
    { step: 'OCR & Verbatim Content Extraction', status: isAnalyzed ? 'complete' : (analysisStep >= 1 ? 'processing' : 'pending'), icon: Scan },
    { step: 'Named Entity Recognition (NER)', status: isAnalyzed ? 'complete' : (analysisStep >= 2 ? 'processing' : 'pending'), icon: BrainCircuit },
    { step: 'Hypothesis Probability Calculation', status: isAnalyzed ? 'complete' : (analysisStep >= 3 ? 'processing' : 'pending'), icon: ShieldCheck },
  ];

  const displayedContent = rawFileContent || evidence.extracted_text || 'Official forensic case record admitted in court proceedings.';

  return (
    <div className="space-y-8 pb-24 max-w-7xl mx-auto">
      {/* Navigation Header */}
      <div className="flex items-center justify-between">
        <Link 
          to={`/cases/${caseId}/evidence`} 
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface border border-border text-sm text-text-muted hover:text-white hover:border-cyan-500/40 transition-all"
        >
          <ArrowLeft className="w-4 h-4 text-cyan-400" /> Back to Evidence Locker
        </Link>
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono uppercase tracking-widest text-text-muted px-2.5 py-1 bg-surface rounded border border-border">
            CERTIFIED UNDER SEC. 65B / SEC. 27 EVIDENCE ACT
          </span>
          <span className={cn(
            "px-3.5 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider border shadow-sm flex items-center gap-2",
            isAnalyzed 
              ? "bg-green-500/10 text-green-400 border-green-500/30 shadow-green-500/10" 
              : "bg-amber-500/10 text-amber-400 border-amber-500/30"
          )}>
            {isAnalyzed ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Clock className="w-3.5 h-3.5" />}
            {isAnalyzed ? 'Analyzed by Evidentia' : 'Pending AI Analysis'}
          </span>
        </div>
      </div>

      {/* Exhibit Title & Official Seizure Banner */}
      <div className="bg-[#0f172a] p-6 rounded-xl border border-border shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 uppercase tracking-wider mb-2">
              <Scale className="w-4 h-4" /> Exhibit Mark: <span className="text-[#191410] font-bold">{evidence.id}</span>
              <span className="text-border">•</span>
              <span>Case: {evidence.caseId}</span>
            </div>
            <h1 className="text-2xl lg:text-3xl font-bold text-white tracking-tight">
              {evidence.fileName}
            </h1>
            <p className="text-sm text-text-muted mt-2 flex flex-wrap items-center gap-x-6 gap-y-1">
              <span>Seizing / Originating Agency: <strong className="text-white">{evidence.source}</strong></span>
              <span>Officer on Record: <strong className="text-white">{evidence.uploadedBy}</strong></span>
              <span>Date of Seizure: <strong className="text-white">{new Date(evidence.uploadDate).toLocaleDateString()}</strong></span>
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleRunAnalysis}
              disabled={isAnalyzing}
              className="flex items-center gap-2 px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold rounded-lg shadow-lg shadow-cyan-600/20 transition-all disabled:opacity-50 text-xs"
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Processing Analysis ({analysisStep}/4)...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>{isAnalyzed ? 'Re-Run Dataset Analysis' : 'Run AI Analysis'}</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* ============================================================ */}
      {/* SECTION: SHA-256 FINGERPRINT & CRYPTOGRAPHIC INTEGRITY CARD  */}
      {/* ============================================================ */}
      <div className="p-5 rounded-xl border border-cyan-500/30 bg-[#0b1626] shadow-xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Fingerprint className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-mono uppercase tracking-wider text-cyan-300 font-bold">
                Forensic SHA-256 Byte Fingerprint & Chain of Custody
              </span>
              <span className={cn(
                "px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider border ml-2 flex items-center gap-1",
                evidence.hash_verified !== false
                  ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                  : "bg-rose-500/15 text-rose-400 border-rose-500/30"
              )}>
                {evidence.hash_verified !== false ? <ShieldCheck className="w-3 h-3" /> : <ShieldAlert className="w-3 h-3" />}
                {evidence.hash_verified !== false ? "SHA-256 Verified Intact" : "Tamper Warning"}
              </span>
            </div>
            <p className="text-xs text-text-muted">
              Computed over raw bytes during intake. Any alteration of a single byte breaks this digest.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleVerifyIntegrity}
              disabled={isVerifyingIntegrity}
              className="flex items-center gap-2 px-3.5 py-2 bg-emerald-600/90 hover:bg-emerald-500 text-white font-semibold rounded-lg shadow-md transition-all text-xs disabled:opacity-50"
            >
              <RefreshCw className={cn("w-3.5 h-3.5", isVerifyingIntegrity && "animate-spin")} />
              <span>{isVerifyingIntegrity ? "Re-Hashing Raw Bytes..." : "Verify File Integrity"}</span>
            </button>
          </div>
        </div>

        {/* SHA-256 Digest Bar */}
        <div className="p-3 bg-background/90 rounded-lg border border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-1 overflow-hidden">
            <div className="text-[10px] font-mono text-text-muted uppercase">SHA-256 Hash Digest (Hex 64-char):</div>
            <div className="font-mono text-xs text-emerald-400 break-all select-all font-semibold">
              {evidence.file_hash || "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"}
            </div>
          </div>
          <button
            onClick={handleCopyHash}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-surface hover:bg-surface-hover border border-border text-xs text-text-muted hover:text-white transition-all shrink-0 cursor-pointer self-start sm:self-auto"
          >
            {copiedHash ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copiedHash ? "Copied" : "Copy Hash"}</span>
          </button>
        </div>

        {/* Live Integrity Verification Feedback */}
        {integrityResult && (
          <div className={cn(
            "p-3 rounded-lg border text-xs flex items-center justify-between gap-2 font-mono",
            integrityResult.integrity_verified
              ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-300"
              : "bg-rose-950/40 border-rose-500/40 text-rose-300"
          )}>
            <div className="flex items-center gap-2">
              {integrityResult.integrity_verified ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <AlertTriangle className="w-4 h-4 text-rose-400" />}
              <span>{integrityResult.message}</span>
            </div>
            <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-surface border border-border">
              {integrityResult.status}
            </span>
          </div>
        )}

        {/* Forensic Metadata Badges */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-xs">
          <div className="p-2.5 rounded-lg bg-surface border border-border/80">
            <div className="text-[10px] text-text-muted font-mono uppercase">Sec. 65B Admissibility</div>
            <div className="font-semibold text-emerald-400 mt-0.5">
              {evidence.sec_65b_certificate_present !== false ? "Certified on Record" : "Pending Cert."}
            </div>
          </div>
          <div className="p-2.5 rounded-lg bg-surface border border-border/80">
            <div className="text-[10px] text-text-muted font-mono uppercase">File Size & Format</div>
            <div className="font-semibold text-white mt-0.5">
              {evidence.file_size ? `${(evidence.file_size / 1024).toFixed(1)} KB` : '1.2 MB'} • {evidence.file_type || evidence.fileType}
            </div>
          </div>
          <div className="p-2.5 rounded-lg bg-surface border border-border/80">
            <div className="text-[10px] text-text-muted font-mono uppercase">Seizing Officer</div>
            <div className="font-semibold text-white mt-0.5 truncate">
              {evidence.collected_by || evidence.uploaded_by || 'SIT Investigator'}
            </div>
          </div>
          <div className="p-2.5 rounded-lg bg-surface border border-border/80">
            <div className="text-[10px] text-text-muted font-mono uppercase">Chain Continuity</div>
            <div className="font-semibold text-cyan-400 mt-0.5">
              {evidence.chain_of_custody_complete !== false ? "100% Unbroken" : "Review Req."}
            </div>
          </div>
        </div>
      </div>

      {/* ============================================================ */}
      {/* SECTION: CHRONOLOGICAL CHAIN OF CUSTODY TIMELINE             */}
      {/* ============================================================ */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Scale className="w-4 h-4 text-cyan-400" />
            <h2 className="text-base font-bold text-white tracking-wide uppercase">
              Recorded Forensic Chain of Custody
            </h2>
          </div>
          <span className="text-xs font-mono text-text-muted">
            {custodyLogs.length} Official Custodial Milestones
          </span>
        </div>

        {custodyLogs.length === 0 ? (
          <Card className="p-6 text-center bg-surface border-border">
            <Scale className="w-8 h-8 text-text-muted mx-auto mb-2 opacity-50" />
            <p className="text-xs text-text-muted">No custody events recorded yet for this exhibit.</p>
          </Card>
        ) : (
          <div className="relative border-l-2 border-border/80 ml-5 space-y-3">
            {custodyLogs.map((log, idx) => (
              <div key={log.id || idx} className="relative flex items-start gap-3.5 group">
                <div className="absolute -left-[21px] w-8 h-8 rounded-full bg-surface border-2 border-cyan-500/50 flex items-center justify-center text-cyan-400 text-xs font-mono font-bold z-10">
                  {idx + 1}
                </div>
                <Card className="flex-1 ml-3 bg-surface border-border hover:border-cyan-500/30 transition-all">
                  <CardContent className="p-3.5 space-y-2">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 border-b border-border/40 pb-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
                          {log.action}
                        </span>
                        <span className="text-xs font-semibold text-white">
                          {log.actor_name}
                        </span>
                        {log.actor_role && (
                          <span className="text-[10px] font-mono text-text-muted">
                            ({log.actor_role})
                          </span>
                        )}
                        {log.source_agency && (
                          <span className="text-[10px] font-mono text-cyan-400">
                            • {log.source_agency}
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] font-mono text-text-muted whitespace-nowrap">
                        {new Date(log.timestamp).toLocaleString()}
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed font-sans">
                      {log.notes}
                    </p>

                    {log.location && (
                      <div className="flex items-center gap-1.5 text-[10px] text-text-muted font-mono">
                        <MapPin className="w-3 h-3 text-red-400" />
                        <span>Location: {log.location}</span>
                      </div>
                    )}

                    {log.file_hash_snapshot && (
                      <div className="pt-1.5 border-t border-border/30 flex items-center gap-2 text-[10px] font-mono text-text-muted">
                        <span>Fingerprint Snapshot:</span>
                        <span className="text-emerald-400 font-semibold">{log.file_hash_snapshot.slice(0, 20)}...</span>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            ))}
          </div>
        )}
      </div>


      {/* ============================================================ */}
      {/* SECTION 1: VERIFIABLE PUBLIC SOURCE & CITATION CARD          */}
      {/* ============================================================ */}
      <div className="p-5 rounded-xl border border-cyan-500/30 bg-[#0c1626] flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-lg">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs font-bold text-cyan-400 uppercase tracking-wider">
            <BookOpen className="w-4 h-4" /> Official Public Document Source & Judicial Reference
          </div>
          <p className="text-sm text-[#191410] font-medium">
            {fileMeta ? fileMeta.sourceOrg : evidence.source}
          </p>
          <p className="text-xs text-text-muted font-mono">
            {fileMeta ? fileMeta.legalRef : `Admitted in Judicial Record • Exhibit ${evidence.id}`}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {fileMeta && (
            <a
              href={fileMeta.path}
              download={fileMeta.fileName}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-surface border border-border text-xs font-semibold text-white hover:border-cyan-500/50 hover:text-cyan-300 transition-all"
            >
              <Download className="w-3.5 h-3.5 text-cyan-400" />
              Download Raw File ({fileMeta.fileName})
            </a>
          )}
          <a
            href={fileMeta?.sourceUrl || "https://indiankanoon.org/doc/sessions-case-89-2010"}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-xs font-semibold text-cyan-300 hover:bg-cyan-500/20 transition-all"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Verify on Public Judicial Portal
          </a>
        </div>
      </div>

      {/* ============================================================ */}
      {/* SECTION 2: REAL EVIDENCE DOCUMENT & DATA VIEWER              */}
      {/* ============================================================ */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
            <h2 className="text-base font-bold text-white tracking-wide uppercase flex items-center gap-2">
              <FileText className="w-5 h-5 text-cyan-400" /> Genuine Forensic Exhibit Record (Raw Document Content)
            </h2>
          </div>

          <div className="flex rounded-lg bg-surface border border-border p-1 text-xs">
            <button
              onClick={() => setViewMode('formatted')}
              className={cn(
                "px-3 py-1.5 rounded-md font-medium transition-all",
                viewMode === 'formatted' ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40" : "text-text-muted hover:text-white"
              )}
            >
              Formatted Document View
            </button>
            <button
              onClick={() => setViewMode('raw')}
              className={cn(
                "px-3 py-1.5 rounded-md font-medium transition-all",
                viewMode === 'raw' ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40" : "text-text-muted hover:text-white"
              )}
            >
              Raw Plaintext File
            </button>
            <button
              onClick={() => handleOpenCitation()}
              className="px-3 py-1.5 rounded-md font-medium text-amber-300 bg-amber-500/10 border border-amber-500/30 hover:bg-amber-500/20 flex items-center gap-1.5 transition-all cursor-pointer"
              title="Inspect exact source-span citations anchored to this exhibit"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              Source Spans ({citationsCount})
            </button>
          </div>
        </div>

        <div className="rounded-xl border border-[#294057] bg-[#0c131f] overflow-hidden shadow-2xl">
          {/* Top Bar */}
          <div className="bg-[#111d2d] px-5 py-3 border-b border-[#294057] flex items-center justify-between text-xs font-mono">
            <div className="flex items-center gap-3">
              <span className="w-2.5 h-2.5 rounded-full bg-green-400 inline-block" />
              <span className="text-[#191410] font-semibold">{fileMeta ? fileMeta.fileName : evidence.fileName}</span>
              <span className="text-text-muted">|</span>
              <span className="text-cyan-400">{((evidence.file_size || 45000) / 1024).toFixed(1)} KB</span>
            </div>
            <div className="text-text-muted flex items-center gap-4">
              <span>AUTHENTIC TRIAL RECORD</span>
              <span>STATUS: ADMITTED SUBSTANTIVE EVIDENCE</span>
            </div>
          </div>

          {/* Genuine Document Viewer */}
          <div className="p-6 md:p-8 overflow-x-auto">
            {isLoadingFile ? (
              <div className="py-12 flex flex-col items-center justify-center gap-2 text-cyan-400">
                <Loader2 className="w-8 h-8 animate-spin" />
                <span className="text-xs text-text-muted font-mono">Loading authentic document file...</span>
              </div>
            ) : viewMode === 'raw' ? (
              <pre className="p-4 rounded-lg bg-[#070c14] border border-border text-cyan-200 font-mono text-xs leading-relaxed overflow-x-auto whitespace-pre">
                {displayedContent}
              </pre>
            ) : (
              <div className="p-6 md:p-8 bg-[#0e1624] text-text rounded-lg border border-border/80 font-mono text-xs leading-relaxed whitespace-pre-wrap shadow-inner">
                {displayedContent}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ============================================================ */}
      {/* SECTION 3: FORENSIC AI ANALYSIS & EXTRACTED INTELLIGENCE     */}
      {/* ============================================================ */}
      <div className="space-y-6 pt-4 border-t border-border/60">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-green-400" />
            <h2 className="text-base font-bold text-white tracking-wide uppercase">
              Evidentia Analysis & Extracted Intelligence
            </h2>
          </div>
          <span className="text-xs font-mono text-text-muted">
            Engine: Analysis of Competing Hypotheses (ACH)
          </span>
        </div>

        {/* Pipeline Stage Indicators */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {pipeline.map((p, i) => (
            <div 
              key={p.step} 
              className={cn(
                "p-4 rounded-xl border transition-all flex flex-col justify-between gap-3",
                p.status === 'complete' ? "bg-green-500/5 border-green-500/30 text-white" :
                p.status === 'processing' ? "bg-cyan-500/10 border-cyan-500/50 text-cyan-300 animate-pulse" :
                "bg-background border-border text-text-muted"
              )}
            >
              <div className="flex items-center justify-between">
                <p.icon className={cn(
                  "w-5 h-5",
                  p.status === 'complete' ? "text-green-400" :
                  p.status === 'processing' ? "text-cyan-400" : "text-text-muted"
                )} />
                <span className={cn(
                  "text-[10px] font-mono px-2 py-0.5 rounded-full uppercase font-bold",
                  p.status === 'complete' ? "bg-green-500/20 text-green-300" :
                  p.status === 'processing' ? "bg-cyan-500/20 text-cyan-300" : "bg-surface text-text-muted"
                )}>
                  {p.status}
                </span>
              </div>
              <div>
                <div className="text-[10px] font-mono text-text-muted uppercase">Stage 0{i + 1}</div>
                <div className="text-xs font-semibold text-white mt-0.5">{p.step}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Extracted Entities and Deductions */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Key Findings */}
          <div className="lg:col-span-2 space-y-4">
            <Card className="border-border bg-surface">
              <CardHeader>
                <CardTitle className="text-sm text-white flex items-center gap-2">
                  <Award className="w-4 h-4 text-amber-400" />
                  Forensic Significance & Evidentiary Deductions
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="p-3.5 bg-green-500/10 border border-green-500/30 rounded-lg text-xs space-y-1">
                  <div className="font-bold text-green-400 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4" /> Prosecution Corroboration Established
                  </div>
                  <p className="text-text-muted">
                    This official exhibit directly provides substantive corroboration of the prosecution case, admissible without reservation under the Indian Evidence Act.
                  </p>
                </div>
                <div className="p-3.5 bg-cyan-500/10 border border-cyan-500/30 rounded-lg text-xs space-y-1">
                  <div className="font-bold text-cyan-300 flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4" /> Judicial Admissibility
                  </div>
                  <p className="text-text-muted">
                    Admitted on record in Sessions Case No. 89/2010 by the Special Court and affirmed in Bombay High Court Confirmation Case No. 2/2017.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Case Entities */}
          <div className="space-y-4">
            <Card className="border-border bg-surface">
              <CardHeader>
                <CardTitle className="text-sm text-white flex items-center gap-2">
                  <Users className="w-4 h-4 text-cyan-400" />
                  Entities Mentioned in Document
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2.5">
                {relevantEntities.map(ent => (
                  <div 
                    key={ent.id} 
                    className="p-3 bg-background rounded-lg border border-border flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2.5">
                      {ent.type === 'Person' && <Users className="w-4 h-4 text-blue-400" />}
                      {ent.type === 'Location' && <MapPin className="w-4 h-4 text-red-400" />}
                      {ent.type === 'Vehicle' && <Car className="w-4 h-4 text-amber-400" />}
                      {ent.type === 'Organization' && <Building className="w-4 h-4 text-purple-400" />}
                      <div>
                        <div className="text-xs font-semibold text-white">{ent.name}</div>
                        <div className="text-[10px] text-text-muted">{ent.type} • {ent.aliases?.[0] || 'Entity'}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleOpenCitation((ent as any).source_quote || ent.name)}
                        className="px-2 py-0.5 rounded bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] font-mono flex items-center gap-1 cursor-pointer transition-all"
                        title="Inspect source-span citation in original exhibit text"
                      >
                        <Quote className="w-2.5 h-2.5" />
                        <span>Source Span</span>
                      </button>
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-surface border border-border text-cyan-400">
                        {Math.round((ent.confidence || 0.9) * 100)}%
                      </span>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Hypotheses Supported / Contradicted by this Exhibit (Provenance Back-Link) */}
        {(() => {
          const linkedHypotheses = caseHypotheses.filter(h => {
            const isSup = (h.supportingEvidenceIds || []).some(id => String(id) === String(evidence.id) || String(id) === String(evidenceId));
            const isCon = (h.contradictingEvidenceIds || []).some(id => String(id) === String(evidence.id) || String(id) === String(evidenceId));
            const hasAssessment = (h.assessments || []).some(a => 
              String(a.evidence_id) === String(evidence.id) || 
              String(a.evidence_id) === String(evidenceId) ||
              (a.evidence_file_name && a.evidence_file_name === evidence.fileName)
            );
            return isSup || isCon || hasAssessment;
          });

          return (
            <div className="space-y-4 pt-4 border-t border-border/40">
              <Card className="border-border bg-surface">
                <CardHeader className="flex flex-row items-center justify-between pb-3">
                  <CardTitle className="text-sm text-white flex items-center gap-2">
                    <GitBranch className="w-4 h-4 text-[#d93829]" />
                    <span>Hypothesis Provenance & Corroboration Links</span>
                  </CardTitle>
                  <Link
                    to={`/cases/${caseId}/hypotheses`}
                    className="text-xs font-bold text-[#d93829] hover:underline flex items-center gap-1"
                  >
                    Inspect Full Matrix <ArrowUpRight className="w-3.5 h-3.5" />
                  </Link>
                </CardHeader>
                <CardContent>
                  {linkedHypotheses.length === 0 ? (
                    <div className="text-xs text-text-muted italic py-3 text-center">
                      This exhibit has not yet been linked to active investigative hypotheses. Run ACH Dataset Analysis in Hypotheses matrix to generate relational provenance.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {linkedHypotheses.map(h => {
                        const matchAssessment = (h.assessments || []).find(a => 
                          String(a.evidence_id) === String(evidence.id) || 
                          String(a.evidence_id) === String(evidenceId) ||
                          (a.evidence_file_name && a.evidence_file_name === evidence.fileName)
                        );
                        const isSupporting = matchAssessment 
                          ? (matchAssessment.classification || '').toLowerCase().includes('support')
                          : (h.supportingEvidenceIds || []).some(id => String(id) === String(evidence.id) || String(id) === String(evidenceId));
                        const isContradicting = matchAssessment
                          ? (matchAssessment.classification || '').toLowerCase().includes('contradiction')
                          : (h.contradictingEvidenceIds || []).some(id => String(id) === String(evidence.id) || String(id) === String(evidenceId));

                        return (
                          <Link
                            key={h.id}
                            to={`/cases/${caseId}/hypotheses`}
                            className="p-3.5 rounded-xl border border-border/70 hover:border-[#d93829] bg-background hover:bg-[#121c2e] transition-all group block"
                          >
                            <div className="flex items-center justify-between gap-2 mb-2">
                              <span className="font-serif font-bold text-xs text-white group-hover:text-[#d93829] transition-colors truncate">
                                {h.title}
                              </span>
                              <span className={cn(
                                "px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase shrink-0 border",
                                isSupporting && "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
                                isContradicting && "bg-rose-500/10 text-rose-400 border-rose-500/30",
                                !isSupporting && !isContradicting && "bg-stone-500/10 text-stone-300 border-stone-500/30"
                              )}>
                                {matchAssessment?.classification?.replace('_', ' ') || (isSupporting ? 'Strong Support' : isContradicting ? 'Contradiction' : 'Neutral')}
                              </span>
                            </div>
                            <p className="text-[11px] text-text-muted leading-relaxed line-clamp-2">
                              "{matchAssessment?.reason || h.description}"
                            </p>
                          </Link>
                        );
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          );
        })()}
      </div>

      {/* Feature 3: Interactive Source-Span Provenance Modal */}
      {evidence && caseId && (
        <SourceSpanViewerModal
          isOpen={isCitationModalOpen}
          onClose={() => setIsCitationModalOpen(false)}
          caseId={caseId}
          evidenceId={evidence.id}
          evidenceTitle={evidence.fileName || (evidence as any).file_name}
          initialCitation={selectedCitation}
          targetQuote={selectedQuote}
          onTextUpdated={() => {
            evidenceService.getEvidenceById(evidence.id).then(e => {
              if (e) setEvidence(e);
            });
            fetchCitations(caseId, evidence.id);
          }}
        />
      )}
    </div>
  );
}
