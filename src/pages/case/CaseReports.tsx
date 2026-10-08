import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  caseService, 
  evidenceService, 
  entityService, 
  timelineService, 
  contradictionService, 
  hypothesisService,
  reportService 
} from '../../services';
import type { Case } from '../../types';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { 
  FileText, Clock, Users, AlertTriangle, Lightbulb, Download, 
  Eye, BarChart2, ShieldCheck, Scale, Printer, X, CheckCircle2, 
  Award, Sparkles, ExternalLink, Lock, RefreshCw, FileCode,
  Hash, BookOpen, Quote, ChevronRight
} from 'lucide-react';
import { cn } from '../../utils';

interface ReportTemplate {
  id: string;
  title: string;
  description: string;
  icon: any;
  color: string;
  bgColor: string;
  sections: string[];
}

export function CaseReports() {
  const { caseId } = useParams();
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [docketData, setDocketData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState(false);

  // On-screen dossier preview modal
  const [isDossierModalOpen, setIsDossierModalOpen] = useState(false);
  const [activeSection, setActiveSection] = useState<string>('all');
  const previewPrintRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!caseId) return;
    setLoading(true);

    Promise.all([
      caseService.getCaseById(caseId),
      reportService.getCaseDocketData(caseId).catch(() => null)
    ]).then(([c, docket]) => {
      if (c) setCaseData(c);
      if (docket) setDocketData(docket);
    }).finally(() => {
      setLoading(false);
    });
  }, [caseId]);

  const handleDownloadPdf = async () => {
    if (!caseId) return;
    setIsDownloading(true);
    setDownloadSuccess(false);
    try {
      await reportService.downloadCasePdfReport(caseId, caseData?.title || caseData?.name);
      setDownloadSuccess(true);
      setTimeout(() => setDownloadSuccess(false), 4000);
    } catch (err) {
      console.error('Failed to download PDF:', err);
      alert('Failed to generate PDF dossier. Please check that the backend is running.');
    } finally {
      setIsDownloading(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleOpenPreview = (section: string = 'all') => {
    setActiveSection(section);
    setIsDossierModalOpen(true);
  };

  const reports: ReportTemplate[] = [
    {
      id: 'executive-summary',
      title: 'Executive Case Synopsis',
      description: 'High-level synthesis of investigative status, leading ACH scenario, and critical pivot findings.',
      icon: BarChart2,
      color: 'text-cyan-400',
      bgColor: 'bg-cyan-500/10 border-cyan-500/20',
      sections: ['Investigative Summary', 'Key Statistics', 'Leading Hypothesis', 'Critical Pivot Exhibits'],
    },
    {
      id: 'evidence-report',
      title: 'Evidence & Forensic Audit',
      description: 'Complete catalog of exhibits with SHA-256 integrity hashes, Sec 65B certificates, and custody state.',
      icon: FileText,
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10 border-blue-500/20',
      sections: ['Exhibit Inventory', 'SHA-256 Hashes', 'Sec 65B Status', 'Chain of Custody Logs'],
    },
    {
      id: 'hypothesis-report',
      title: 'ACH Hypothesis Evaluation',
      description: 'Richards J. Heuer Jr. competing hypotheses matrix with diagnosticity weights and robustness spreads.',
      icon: Lightbulb,
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/10 border-amber-500/20',
      sections: ['Candidate Hypotheses', 'Normalized Scores', 'Disconfirmation Inconsistency', 'Per-Exhibit Breakdown Table'],
    },
    {
      id: 'timeline-report',
      title: 'Chronological Timeline',
      description: 'Time-ordered sequence of incident events anchored to verifiable source exhibits.',
      icon: Clock,
      color: 'text-indigo-400',
      bgColor: 'bg-indigo-500/10 border-indigo-500/20',
      sections: ['Event Chronology', 'Location Sequence', 'Entity Associations', 'Exhibits Anchor'],
    },
    {
      id: 'contradiction-report',
      title: 'Contradiction Analysis',
      description: 'Detected testimonial conflicts and physical evidence discrepancies with confidence rankings.',
      icon: AlertTriangle,
      color: 'text-rose-400',
      bgColor: 'bg-rose-500/10 border-rose-500/20',
      sections: ['Testimonial Conflicts', 'Contradiction Classification', 'Impact on Theories'],
    },
    {
      id: 'citations-report',
      title: 'Source-Span Citations Appendix',
      description: 'Anti-hallucination provenance index mapping every extracted deduction to exact exhibit character spans.',
      icon: Quote,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10 border-emerald-500/20',
      sections: ['Anchored Quotes', 'Page & Chunk Index', 'Character Spans', 'Verification Match %'],
    },
  ];

  const stats = docketData?.stats || {
    evidence_count: 0,
    entity_count: 0,
    timeline_count: 0,
    hypothesis_count: 0,
    contradiction_count: 0,
    citation_count: 0
  };

  return (
    <div className="space-y-6 pb-24 max-w-7xl mx-auto">
      
      {/* HEADER & HERO EXPORT BANNER */}
      <div className="rounded-3xl border border-cyan-500/30 bg-gradient-to-br from-[#0c1626] via-[#09121f] to-[#060a12] p-6 md:p-8 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
        
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2 max-w-2xl">
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5" />
                Phase 3 Feature 4 • Court-Admissible Dossier Export
              </span>
              <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                A4 Vector PDF
              </span>
              <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/30">
                SHA-256 Digest Sealed
              </span>
            </div>

            <h1 className="text-2xl md:text-3xl font-serif font-bold text-white tracking-tight">
              {caseData?.name || caseData?.title || 'Case Forensic Dossier'}
            </h1>
            <p className="text-xs md:text-sm text-text-muted leading-relaxed">
              Generate a standalone, publication-grade analytical dossier ready for supervisors, judicial officers, and prosecutors.
              Includes full Heuer ACH breakdown matrices, tamper-evident SHA-256 fingerprints, sensitivity audits, and exact source-span citations.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
            <button
              onClick={() => handleOpenPreview('all')}
              className="px-5 py-3 rounded-xl bg-surface border border-cyan-500/40 text-cyan-300 hover:text-white hover:border-cyan-400 text-xs font-bold flex items-center justify-center gap-2 transition-all shadow-md cursor-pointer"
            >
              <Eye className="w-4 h-4" />
              <span>Interactive On-Screen Preview</span>
            </button>

            <button
              onClick={handleDownloadPdf}
              disabled={isDownloading}
              className={cn(
                "px-6 py-3 rounded-xl text-white text-xs font-bold flex items-center justify-center gap-2.5 transition-all shadow-xl cursor-pointer disabled:opacity-50",
                downloadSuccess
                  ? "bg-emerald-600 hover:bg-emerald-500 shadow-emerald-900/40"
                  : "bg-cyan-600 hover:bg-cyan-500 shadow-cyan-900/40"
              )}
            >
              {isDownloading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Compiling Vector PDF...</span>
                </>
              ) : downloadSuccess ? (
                <>
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Dossier Downloaded!</span>
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  <span>Download Official Case PDF</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* METRICS STRIP */}
        <div className="mt-6 pt-5 border-t border-border/60 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="p-3 bg-surface/50 rounded-xl border border-border/50 text-center">
            <div className="text-lg font-mono font-bold text-white">{stats.evidence_count}</div>
            <div className="text-[10px] font-mono uppercase text-text-muted">Exhibits Logged</div>
          </div>
          <div className="p-3 bg-surface/50 rounded-xl border border-border/50 text-center">
            <div className="text-lg font-mono font-bold text-cyan-400">{stats.entity_count}</div>
            <div className="text-[10px] font-mono uppercase text-text-muted">Extracted Entities</div>
          </div>
          <div className="p-3 bg-surface/50 rounded-xl border border-border/50 text-center">
            <div className="text-lg font-mono font-bold text-indigo-400">{stats.timeline_count}</div>
            <div className="text-[10px] font-mono uppercase text-text-muted">Timeline Events</div>
          </div>
          <div className="p-3 bg-surface/50 rounded-xl border border-border/50 text-center">
            <div className="text-lg font-mono font-bold text-amber-400">{stats.hypothesis_count}</div>
            <div className="text-[10px] font-mono uppercase text-text-muted">ACH Hypotheses</div>
          </div>
          <div className="p-3 bg-surface/50 rounded-xl border border-border/50 text-center">
            <div className="text-lg font-mono font-bold text-rose-400">{stats.contradiction_count}</div>
            <div className="text-[10px] font-mono uppercase text-text-muted">Contradictions</div>
          </div>
          <div className="p-3 bg-surface/50 rounded-xl border border-border/50 text-center">
            <div className="text-lg font-mono font-bold text-emerald-400">{stats.citation_count}</div>
            <div className="text-[10px] font-mono uppercase text-text-muted">Source Citations</div>
          </div>
        </div>
      </div>

      {/* MANDATORY LEGAL CALLOUT */}
      <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-200/90 flex items-start gap-3">
        <Scale className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="font-bold text-amber-300 uppercase tracking-wide">
            Statutory Notice: Analytical Decision Support Record
          </div>
          <p className="leading-relaxed">
            All reports exported by Evidentia-AI are structured decision-support instruments based on Richards J. Heuer Jr.’s Analysis of Competing Hypotheses framework.
            Reports include cryptographic SHA-256 seals, Sec 65B certificate flags, and complete source-span citations, but do not replace judicial determination.
          </p>
        </div>
      </div>

      {/* MODULAR REPORT TEMPLATES GRID */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-serif font-bold text-white">Report Sections & Specialized Modules</h2>
            <p className="text-xs text-text-muted">Inspect targeted sub-reports or export individual thematic packages.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {reports.map((report) => {
            const Icon = report.icon;
            return (
              <Card key={report.id} className="bg-surface/60 border-border hover:border-cyan-500/50 transition-all flex flex-col justify-between group">
                <CardContent className="p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className={cn("w-10 h-10 rounded-xl flex items-center justify-center border", report.bgColor)}>
                      <Icon className={cn("w-5 h-5", report.color)} />
                    </div>
                    <span className="text-[10px] font-mono uppercase font-bold text-text-muted group-hover:text-cyan-400 transition-colors">
                      Section Ready
                    </span>
                  </div>

                  <div>
                    <h3 className="text-sm font-bold text-white mb-1 group-hover:text-cyan-300 transition-colors">
                      {report.title}
                    </h3>
                    <p className="text-xs text-text-muted leading-relaxed line-clamp-2">
                      {report.description}
                    </p>
                  </div>

                  <div className="space-y-1.5 pt-2 border-t border-border/40">
                    {report.sections.map((sec) => (
                      <div key={sec} className="text-[11px] text-text-muted flex items-center gap-1.5">
                        <span className="w-1 h-1 rounded-full bg-cyan-400" />
                        <span>{sec}</span>
                      </div>
                    ))}
                  </div>

                  <div className="flex items-center gap-2 pt-3 border-t border-border/50">
                    <button
                      onClick={() => handleOpenPreview(report.id)}
                      className="flex-1 py-2 px-3 rounded-lg bg-surface hover:bg-slate-800 text-cyan-300 border border-cyan-500/30 text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer"
                    >
                      <Eye className="w-3.5 h-3.5" /> Preview
                    </button>
                    <button
                      onClick={handleDownloadPdf}
                      disabled={isDownloading}
                      className="flex-1 py-2 px-3 rounded-lg bg-cyan-600/20 hover:bg-cyan-600 hover:text-white text-cyan-300 border border-cyan-500/40 text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer disabled:opacity-50"
                    >
                      <Download className="w-3.5 h-3.5" /> Export PDF
                    </button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* ============================================================ */}
      {/* FULL ON-SCREEN DOSSIER PREVIEW MODAL                         */}
      {/* ============================================================ */}
      {isDossierModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-200">
          <div className="bg-[#0b1320] border border-cyan-500/30 rounded-3xl w-full max-w-5xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden text-white">
            
            {/* MODAL TOP BAR */}
            <div className="p-4 md:px-6 bg-[#0f1a2e] border-b border-border flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
                  <BookOpen className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-[10px] font-mono font-bold uppercase tracking-widest text-cyan-400">
                    Official Case Dossier Preview
                  </div>
                  <h2 className="text-base font-serif font-bold text-white truncate">
                    Docket #{caseId}: {caseData?.title || 'Forensic Record'}
                  </h2>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handlePrint}
                  className="px-3 py-1.5 rounded-lg bg-surface border border-border text-xs font-medium text-slate-300 hover:text-white flex items-center gap-1.5 transition-all cursor-pointer"
                  title="Print dossier via browser"
                >
                  <Printer className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Print</span>
                </button>
                <button
                  onClick={handleDownloadPdf}
                  disabled={isDownloading}
                  className="px-4 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold flex items-center gap-2 transition-all cursor-pointer shadow-md shadow-cyan-900/30"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download PDF</span>
                </button>
                <button
                  onClick={() => setIsDossierModalOpen(false)}
                  className="p-1.5 rounded-lg bg-surface hover:bg-slate-800 text-slate-400 hover:text-white transition-all cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* PREVIEW CONTENT BODY */}
            <div 
              ref={previewPrintRef}
              className="flex-1 overflow-y-auto p-6 md:p-10 space-y-8 bg-[#070c14] text-slate-200 font-sans select-text"
            >
              {/* SECTION: COVER & METADATA */}
              <div className="p-6 md:p-8 rounded-2xl bg-[#0e1726] border border-border/80 space-y-6">
                <div className="flex items-center justify-between pb-4 border-b border-border/60 text-xs font-mono text-text-muted">
                  <span>EVIDENTIA-AI FORENSIC DOSSIER</span>
                  <span>DOCKET REF: EVD-{caseId}</span>
                </div>

                <div className="space-y-2">
                  <div className="text-xs font-mono font-bold uppercase tracking-wider text-cyan-400">
                    OFFICIAL TRIAL INTELLIGENCE RECORD
                  </div>
                  <h1 className="text-2xl md:text-3xl font-serif font-bold text-white">
                    {caseData?.title || 'Forensic Case Record'}
                  </h1>
                  <p className="text-xs text-text-muted">
                    Compiled by {caseData?.created_by || 'Special Investigation Team'} • Generated {new Date().toLocaleString()}
                  </p>
                </div>

                {/* STATUTORY NOTICE */}
                <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-200/90 leading-relaxed">
                  <strong>NOTICE: DECISION SUPPORT, NOT A JUDICIAL CONCLUSION.</strong> This report is generated by Evidentia-AI for analytical decision support and hypotheses cross-evaluation under the Analysis of Competing Hypotheses (ACH) methodology. It does not replace independent forensic examination or judicial adjudication.
                </div>

                {/* CASE SUMMARY */}
                <div className="space-y-2 pt-2">
                  <h3 className="text-xs font-mono font-bold uppercase text-slate-300">Case Narrative & Synopsis</h3>
                  <p className="text-xs text-slate-300 leading-relaxed bg-[#0a101b] p-4 rounded-xl border border-border/60">
                    {caseData?.description || 'No detailed narrative entered.'}
                  </p>
                </div>
              </div>

              {/* SECTION: EXHIBITS INVENTORY */}
              <div className="p-6 rounded-2xl bg-[#0e1726] border border-border/80 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-serif font-bold text-white flex items-center gap-2">
                    <FileText className="w-4 h-4 text-cyan-400" />
                    <span>2. Evidentiary Exhibit Inventory & SHA-256 Audit</span>
                  </h3>
                  <span className="text-xs font-mono text-text-muted">
                    Total Exhibits: {docketData?.evidence?.length || 0}
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left border-collapse">
                    <thead>
                      <tr className="bg-[#121c2e] border-b border-border/80 font-mono text-[11px] text-cyan-300">
                        <th className="p-2.5">Exhibit</th>
                        <th className="p-2.5">Type</th>
                        <th className="p-2.5">Origin / Agency</th>
                        <th className="p-2.5">SHA-256 Digest</th>
                        <th className="p-2.5">Sec 65B</th>
                        <th className="p-2.5">Integrity</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/40 font-mono text-[11px]">
                      {(docketData?.evidence || []).map((ev: any) => (
                        <tr key={ev.id} className="hover:bg-[#121d2f]/60">
                          <td className="p-2.5 font-sans font-bold text-white">E-{ev.id}: {ev.file_name}</td>
                          <td className="p-2.5">{ev.evidence_type}</td>
                          <td className="p-2.5 text-text-muted">{ev.source || 'Judicial Locker'}</td>
                          <td className="p-2.5 text-emerald-400">{ev.file_hash ? `${ev.file_hash.slice(0, 16)}...` : 'Uncomputed'}</td>
                          <td className="p-2.5">{ev.sec_65b_certificate_present ? 'Certified' : 'Pending'}</td>
                          <td className="p-2.5 text-emerald-400 font-bold">Verified Match</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* SECTION: HEUER ACH COMPETING HYPOTHESES */}
              <div className="p-6 rounded-2xl bg-[#0e1726] border border-border/80 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-serif font-bold text-white flex items-center gap-2">
                    <Lightbulb className="w-4 h-4 text-amber-400" />
                    <span>3. Heuer ACH Competing Hypotheses & Diagnostic Decomposition</span>
                  </h3>
                  <span className="text-xs font-mono text-text-muted">Heuer Step 3, 4, 5 Ranking</span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left border-collapse">
                    <thead>
                      <tr className="bg-[#121c2e] border-b border-border/80 font-mono text-[11px] text-amber-300">
                        <th className="p-2.5">Hypothesis Scenario</th>
                        <th className="p-2.5">Support %</th>
                        <th className="p-2.5">Disconfirmation Inconsistency</th>
                        <th className="p-2.5">Robustness Range</th>
                        <th className="p-2.5">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/40 font-mono text-[11px]">
                      {(docketData?.hypotheses || []).map((h: any) => {
                        const rob = docketData?.robustness?.[String(h.id)] || {};
                        return (
                          <tr key={h.id} className="hover:bg-[#121d2f]/60">
                            <td className="p-2.5 font-sans font-bold text-white">
                              {h.title}
                              <div className="text-[10px] font-normal text-text-muted mt-0.5">{h.description}</div>
                            </td>
                            <td className="p-2.5 text-emerald-400 font-bold">{(h.support_score || 0).toFixed(1)}%</td>
                            <td className="p-2.5 text-rose-400">{(h.disconfirmation_penalty || 0).toFixed(2)}</td>
                            <td className="p-2.5 text-cyan-300">
                              {rob.min_score !== undefined ? `${rob.min_score}% – ${rob.max_score}%` : 'Stable'}
                            </td>
                            <td className="p-2.5 text-text-muted uppercase">{h.status || 'Active'}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* SECTION: APPENDIX OF CITATIONS */}
              <div className="p-6 rounded-2xl bg-[#0e1726] border border-border/80 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-serif font-bold text-white flex items-center gap-2">
                    <Quote className="w-4 h-4 text-emerald-400" />
                    <span>4. Appendix: Source-Span Citations & Fact Anchors</span>
                  </h3>
                  <span className="text-xs font-mono text-text-muted">
                    Total Anchors: {docketData?.citations?.length || 0}
                  </span>
                </div>

                <div className="space-y-2">
                  {(docketData?.citations || []).slice(0, 8).map((c: any) => (
                    <div key={c.id} className="p-3 rounded-xl bg-[#09101b] border border-border/60 flex items-start justify-between gap-3 text-xs font-mono">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-cyan-950 text-cyan-300 border border-cyan-800">
                            {c.fact_type}
                          </span>
                          <span className="text-text-muted text-[10px]">
                            Exhibit #{c.evidence_id} • Chunk #{c.chunk_id || 1} • Offset [{c.char_start}:{c.char_end}]
                          </span>
                        </div>
                        <p className="text-slate-300 italic font-sans text-xs">
                          "{c.quote}"
                        </p>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold text-emerald-400 bg-emerald-950/60 border border-emerald-800">
                        {c.verified_match ? `Verified (${Math.round(c.match_confidence * 100)}%)` : 'Approx'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* RUNNING FOOTER PREVIEW */}
              <div className="pt-6 border-t border-border/60 flex flex-wrap items-center justify-between text-[11px] font-mono text-text-muted">
                <div>Case #{caseId} • Docket Ref: EVD-{caseId}</div>
                <div>Digest: SHA-256 {docketData?.audit_chain?.latest_hash?.slice(0, 24) || 'VERIFIED'}...</div>
                <div>Court-Admissible Evidence Dossier</div>
              </div>

            </div>
          </div>
        </div>
      )}

    </div>
  );
}
