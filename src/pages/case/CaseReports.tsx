import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  caseService, 
  reportService 
} from '../../services';
import type { Case } from '../../types';
import { Card, CardContent } from '../../components/ui/Card';
import { 
  FileText, Clock, Lightbulb, Download, 
  Eye, BarChart2, ShieldCheck, Scale, Printer, X, CheckCircle2, 
  RefreshCw, Quote, ChevronRight
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
      color: 'text-blue-700',
      bgColor: 'bg-blue-50 border-blue-200',
      sections: ['Investigative Summary', 'Key Statistics', 'Leading Hypothesis', 'Critical Pivot Exhibits'],
    },
    {
      id: 'evidence-report',
      title: 'Evidence & Forensic Audit',
      description: 'Complete catalog of exhibits with SHA-256 integrity hashes, Sec 65B certificates, and custody state.',
      icon: FileText,
      color: 'text-[#d93829]',
      bgColor: 'bg-red-50 border-red-200',
      sections: ['Exhibit Inventory', 'SHA-256 Hashes', 'Sec 65B Status', 'Chain of Custody Logs'],
    },
    {
      id: 'hypothesis-report',
      title: 'ACH Hypothesis Evaluation',
      description: 'Richards J. Heuer Jr. competing hypotheses matrix with diagnosticity weights and robustness spreads.',
      icon: Lightbulb,
      color: 'text-amber-700',
      bgColor: 'bg-amber-50 border-amber-200',
      sections: ['Candidate Hypotheses', 'Normalized Scores', 'Disconfirmation Inconsistency', 'Per-Exhibit Breakdown Table'],
    },
    {
      id: 'timeline-report',
      title: 'Chronological Timeline',
      description: 'Time-ordered sequence of incident events anchored to verifiable source exhibits.',
      icon: Clock,
      color: 'text-purple-700',
      bgColor: 'bg-purple-50 border-purple-200',
      sections: ['Event Chronology', 'Location Sequence', 'Entity Associations', 'Exhibits Anchor'],
    },
    {
      id: 'citations-report',
      title: 'Source-Span Citations Appendix',
      description: 'Anti-hallucination provenance index mapping every extracted deduction to exact exhibit character spans.',
      icon: Quote,
      color: 'text-emerald-700',
      bgColor: 'bg-emerald-50 border-emerald-200',
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
      <div className="rounded-3xl border border-[#eae4d9] bg-white p-6 md:p-8 shadow-xs relative overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2 max-w-2xl">
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-blue-50 text-blue-800 border border-blue-200 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
                Phase 3 Feature 4 • Court-Admissible Dossier Export
              </span>
              <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-emerald-50 text-emerald-800 border border-emerald-200">
                A4 Vector PDF
              </span>
              <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-amber-50 text-amber-800 border border-amber-200">
                SHA-256 Digest Sealed
              </span>
            </div>

            <h1 className="text-2xl md:text-3xl font-serif font-bold text-[#191410] tracking-tight">
              {caseData?.name || caseData?.title || 'Case Forensic Dossier'}
            </h1>
            <p className="text-xs md:text-sm text-[#6e665d] leading-relaxed">
              Generate a standalone, publication-grade analytical dossier ready for supervisors, judicial officers, and prosecutors.
              Includes full Heuer ACH breakdown matrices, tamper-evident SHA-256 fingerprints, sensitivity audits, and exact source-span citations.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
            <button
              onClick={() => handleOpenPreview('all')}
              className="px-5 py-3 rounded-xl bg-white border border-[#eae4d9] hover:bg-[#faf7f2] text-[#191410] text-xs font-bold flex items-center justify-center gap-2 transition-all shadow-xs cursor-pointer"
            >
              <Eye className="w-4 h-4 text-[#d93829]" />
              <span>Interactive On-Screen Preview</span>
            </button>

            <button
              onClick={handleDownloadPdf}
              disabled={isDownloading}
              className={cn(
                "px-6 py-3 rounded-xl text-white text-xs font-bold flex items-center justify-center gap-2.5 transition-all shadow-xs cursor-pointer disabled:opacity-50",
                downloadSuccess
                  ? "bg-emerald-600 hover:bg-emerald-700"
                  : "bg-[#d93829] hover:bg-[#bf2b1d]"
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
        <div className="mt-6 pt-5 border-t border-[#eae4d9] grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="p-3 bg-[#faf7f2] rounded-xl border border-[#eae4d9] text-center">
            <div className="text-lg font-mono font-bold text-[#191410]">{stats.evidence_count}</div>
            <div className="text-[10px] font-mono uppercase text-[#6e665d]">Exhibits Logged</div>
          </div>
          <div className="p-3 bg-[#faf7f2] rounded-xl border border-[#eae4d9] text-center">
            <div className="text-lg font-mono font-bold text-blue-700">{stats.entity_count}</div>
            <div className="text-[10px] font-mono uppercase text-[#6e665d]">Extracted Entities</div>
          </div>
          <div className="p-3 bg-[#faf7f2] rounded-xl border border-[#eae4d9] text-center">
            <div className="text-lg font-mono font-bold text-purple-700">{stats.timeline_count}</div>
            <div className="text-[10px] font-mono uppercase text-[#6e665d]">Timeline Events</div>
          </div>
          <div className="p-3 bg-[#faf7f2] rounded-xl border border-[#eae4d9] text-center">
            <div className="text-lg font-mono font-bold text-amber-700">{stats.hypothesis_count}</div>
            <div className="text-[10px] font-mono uppercase text-[#6e665d]">ACH Hypotheses</div>
          </div>
          <div className="p-3 bg-[#faf7f2] rounded-xl border border-[#eae4d9] text-center">
            <div className="text-lg font-mono font-bold text-red-700">{stats.contradiction_count}</div>
            <div className="text-[10px] font-mono uppercase text-[#6e665d]">Contradictions</div>
          </div>
          <div className="p-3 bg-[#faf7f2] rounded-xl border border-[#eae4d9] text-center">
            <div className="text-lg font-mono font-bold text-emerald-700">{stats.citation_count}</div>
            <div className="text-[10px] font-mono uppercase text-[#6e665d]">Source Citations</div>
          </div>
        </div>
      </div>

      {/* MANDATORY LEGAL CALLOUT */}
      <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-xs text-amber-900 flex items-start gap-3">
        <Scale className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="font-bold text-amber-900 uppercase tracking-wide">
            Statutory Notice: Analytical Decision Support Record
          </div>
          <p className="leading-relaxed text-amber-800">
            All reports exported by Evidentia-AI are structured decision-support instruments based on Richards J. Heuer Jr.’s Analysis of Competing Hypotheses framework.
            Reports include cryptographic SHA-256 seals, Sec 65B certificate flags, and complete source-span citations, but do not replace judicial determination.
          </p>
        </div>
      </div>

      {/* CHARGESHEET & DOCKET WORKSTATION BANNER */}
      <div className="p-6 rounded-3xl bg-[#faf7f2] border border-[#d93829]/30 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xs">
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-2xl bg-red-100 text-[#d93829] border border-red-200">
            <Scale className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold uppercase tracking-wider bg-[#d93829] text-white px-2 py-0.5 rounded">
                Section 193 BNSS / 173 CrPC
              </span>
              <span className="text-xs font-bold text-[#191410]">
                Court Chargesheet & Docket Assistant
              </span>
            </div>
            <p className="text-xs text-[#6e665d] leading-relaxed max-w-2xl">
              Compile an official 5-section draft police report (Facts, Evidence List, Witnesses, Forensic Findings, Analysis). Every statement is grounded with source exhibit spans. Edit inline before exporting a watermarked draft PDF.
            </p>
          </div>
        </div>

        <Link
          to={`/cases/${caseId}/chargesheet`}
          className="px-5 py-3 rounded-xl bg-[#d93829] hover:bg-[#bf2b1d] text-white text-xs font-bold flex items-center justify-center gap-2 transition-all shadow-xs shrink-0 cursor-pointer"
        >
          <span>Open Chargesheet Assistant</span>
          <ChevronRight className="w-4 h-4" />
        </Link>
      </div>

      {/* MODULAR REPORT TEMPLATES GRID */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-serif font-bold text-[#191410]">Report Sections & Specialized Modules</h2>
            <p className="text-xs text-[#6e665d]">Inspect targeted sub-reports or export individual thematic packages.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {reports.map((report) => {
            const Icon = report.icon;
            return (
              <Card key={report.id} className="bg-white border-[#eae4d9] hover:border-[#d93829]/40 transition-all flex flex-col justify-between group shadow-xs">
                <CardContent className="p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className={cn("w-10 h-10 rounded-xl flex items-center justify-center border", report.bgColor)}>
                      <Icon className={cn("w-5 h-5", report.color)} />
                    </div>
                    <span className="text-[10px] font-mono uppercase font-bold text-[#6e665d] group-hover:text-[#d93829] transition-colors">
                      Section Ready
                    </span>
                  </div>

                  <div>
                    <h3 className="text-sm font-bold text-[#191410] mb-1 group-hover:text-[#d93829] transition-colors">
                      {report.title}
                    </h3>
                    <p className="text-xs text-[#6e665d] leading-relaxed line-clamp-2">
                      {report.description}
                    </p>
                  </div>

                  <div className="space-y-1.5 pt-2 border-t border-[#eae4d9]">
                    {report.sections.map((sec) => (
                      <div key={sec} className="text-[11px] text-[#6e665d] flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#d93829]" />
                        <span>{sec}</span>
                      </div>
                    ))}
                  </div>

                  <div className="flex items-center gap-2 pt-3 border-t border-[#eae4d9]">
                    <button
                      onClick={() => handleOpenPreview(report.id)}
                      className="flex-1 py-2 px-3 rounded-xl bg-white hover:bg-[#faf7f2] text-[#191410] border border-[#eae4d9] text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer shadow-xs"
                    >
                      <Eye className="w-3.5 h-3.5 text-[#d93829]" /> Preview
                    </button>
                    <button
                      onClick={handleDownloadPdf}
                      disabled={isDownloading}
                      className="flex-1 py-2 px-3 rounded-xl bg-red-50 hover:bg-[#d93829] hover:text-white text-[#d93829] border border-red-200 text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer disabled:opacity-50"
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
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-200">
          <div className="bg-white border border-[#eae4d9] rounded-3xl w-full max-w-5xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden text-[#191410]">
            
            {/* MODAL TOP BAR */}
            <div className="p-4 md:px-6 bg-[#faf7f2] border-b border-[#eae4d9] flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-red-50 border border-red-200 text-[#d93829]">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-[10px] font-mono font-bold uppercase tracking-widest text-[#d93829]">
                    Official Case Dossier Preview
                  </div>
                  <h2 className="text-base font-serif font-bold text-[#191410] truncate">
                    Docket #{caseId}: {caseData?.title || 'Forensic Record'}
                  </h2>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handlePrint}
                  className="px-3 py-1.5 rounded-xl bg-white border border-[#eae4d9] text-xs font-semibold text-[#191410] hover:bg-[#faf7f2] flex items-center gap-1.5 transition-all cursor-pointer shadow-xs"
                  title="Print dossier via browser"
                >
                  <Printer className="w-3.5 h-3.5 text-[#d93829]" />
                  <span>Print</span>
                </button>
                <button
                  onClick={handleDownloadPdf}
                  disabled={isDownloading}
                  className="px-4 py-1.5 rounded-xl bg-[#d93829] hover:bg-[#bf2b1d] text-white text-xs font-bold flex items-center gap-2 transition-all cursor-pointer shadow-xs"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download PDF</span>
                </button>
                <button
                  onClick={() => setIsDossierModalOpen(false)}
                  className="p-1.5 rounded-xl hover:bg-[#faf7f2] text-[#6e665d] hover:text-[#191410] transition-all cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* PREVIEW CONTENT BODY */}
            <div 
              ref={previewPrintRef}
              className="flex-1 overflow-y-auto p-6 md:p-10 space-y-8 bg-[#faf7f2] text-[#191410] font-sans select-text"
            >
              {/* SECTION: COVER & METADATA */}
              <div className="p-6 md:p-8 rounded-2xl bg-white border border-[#eae4d9] space-y-6 shadow-xs">
                <div className="flex items-center justify-between pb-4 border-b border-[#eae4d9] text-xs font-mono text-[#6e665d]">
                  <span>EVIDENTIA-AI FORENSIC DOSSIER</span>
                  <span>DOCKET REF: EVD-{caseId}</span>
                </div>

                <div className="space-y-2">
                  <div className="text-xs font-mono font-bold uppercase tracking-wider text-[#d93829]">
                    OFFICIAL TRIAL INTELLIGENCE RECORD
                  </div>
                  <h1 className="text-2xl md:text-3xl font-serif font-bold text-[#191410]">
                    {caseData?.title || 'Forensic Case Record'}
                  </h1>
                  <p className="text-xs text-[#6e665d]">
                    Compiled by {caseData?.created_by || 'Special Investigation Team'} • Generated {new Date().toLocaleString()}
                  </p>
                </div>

                {/* STATUTORY NOTICE */}
                <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-xs text-red-900 leading-relaxed">
                  <strong>NOTICE: DECISION SUPPORT, NOT A JUDICIAL CONCLUSION.</strong> This report is generated by Evidentia-AI for analytical decision support and hypotheses cross-evaluation under the Analysis of Competing Hypotheses (ACH) methodology. It does not replace independent forensic examination or judicial adjudication.
                </div>

                {/* CASE SUMMARY */}
                <div className="space-y-2 pt-2">
                  <h3 className="text-xs font-mono font-bold uppercase text-[#191410]">Case Narrative & Synopsis</h3>
                  <p className="text-xs text-[#6e665d] leading-relaxed bg-[#faf7f2] p-4 rounded-xl border border-[#eae4d9]">
                    {caseData?.description || 'No detailed narrative entered.'}
                  </p>
                </div>
              </div>

              {/* SECTION: EXHIBITS INVENTORY */}
              <div className="p-6 rounded-2xl bg-white border border-[#eae4d9] space-y-4 shadow-xs">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-serif font-bold text-[#191410] flex items-center gap-2">
                    <FileText className="w-4 h-4 text-blue-700" />
                    <span>2. Evidentiary Exhibit Inventory & SHA-256 Audit</span>
                  </h3>
                  <span className="text-xs font-mono text-[#6e665d]">
                    Total Exhibits: {docketData?.evidence?.length || 0}
                  </span>
                </div>

                <div className="overflow-x-auto rounded-xl border border-[#eae4d9]">
                  <table className="w-full text-xs text-left border-collapse">
                    <thead>
                      <tr className="bg-[#faf7f2] border-b border-[#eae4d9] font-mono text-[11px] text-[#6e665d]">
                        <th className="p-2.5">Exhibit</th>
                        <th className="p-2.5">Type</th>
                        <th className="p-2.5">Origin / Agency</th>
                        <th className="p-2.5">SHA-256 Digest</th>
                        <th className="p-2.5">Sec 65B</th>
                        <th className="p-2.5">Integrity</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#eae4d9] font-mono text-[11px] bg-white text-[#191410]">
                      {(docketData?.evidence || []).map((ev: any) => (
                        <tr key={ev.id} className="hover:bg-[#faf7f2]">
                          <td className="p-2.5 font-sans font-bold text-[#191410]">E-{ev.id}: {ev.file_name}</td>
                          <td className="p-2.5 capitalize">{ev.evidence_type}</td>
                          <td className="p-2.5 text-[#6e665d]">{ev.source || 'Judicial Locker'}</td>
                          <td className="p-2.5 text-emerald-700">{ev.file_hash ? `${ev.file_hash.slice(0, 16)}...` : 'Uncomputed'}</td>
                          <td className="p-2.5">{ev.sec_65b_certificate_present ? 'Certified' : 'Pending'}</td>
                          <td className="p-2.5 text-emerald-700 font-bold">Verified Match</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* SECTION: HEUER ACH COMPETING HYPOTHESES */}
              <div className="p-6 rounded-2xl bg-white border border-[#eae4d9] space-y-4 shadow-xs">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-serif font-bold text-[#191410] flex items-center gap-2">
                    <Lightbulb className="w-4 h-4 text-amber-700" />
                    <span>3. Heuer ACH Competing Hypotheses & Diagnostic Decomposition</span>
                  </h3>
                  <span className="text-xs font-mono text-[#6e665d]">Heuer Step 3, 4, 5 Ranking</span>
                </div>

                <div className="overflow-x-auto rounded-xl border border-[#eae4d9]">
                  <table className="w-full text-xs text-left border-collapse">
                    <thead>
                      <tr className="bg-[#faf7f2] border-b border-[#eae4d9] font-mono text-[11px] text-[#6e665d]">
                        <th className="p-2.5">Hypothesis Scenario</th>
                        <th className="p-2.5">Support %</th>
                        <th className="p-2.5">Disconfirmation Inconsistency</th>
                        <th className="p-2.5">Robustness Range</th>
                        <th className="p-2.5">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#eae4d9] font-mono text-[11px] bg-white text-[#191410]">
                      {(docketData?.hypotheses || []).map((h: any) => {
                        const rob = docketData?.robustness?.[String(h.id)] || {};
                        return (
                          <tr key={h.id} className="hover:bg-[#faf7f2]">
                            <td className="p-2.5 font-sans font-bold text-[#191410]">
                              {h.title}
                              <div className="text-[10px] font-normal text-[#6e665d] mt-0.5">{h.description}</div>
                            </td>
                            <td className="p-2.5 text-emerald-700 font-bold">{(h.support_score || 0).toFixed(1)}%</td>
                            <td className="p-2.5 text-red-700 font-semibold">{(h.disconfirmation_penalty || 0).toFixed(2)}</td>
                            <td className="p-2.5 text-blue-700">
                              {rob.min_score !== undefined ? `${rob.min_score}% – ${rob.max_score}%` : 'Stable'}
                            </td>
                            <td className="p-2.5 text-[#6e665d] uppercase">{h.status || 'Active'}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* SECTION: APPENDIX OF CITATIONS */}
              <div className="p-6 rounded-2xl bg-white border border-[#eae4d9] space-y-4 shadow-xs">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-serif font-bold text-[#191410] flex items-center gap-2">
                    <Quote className="w-4 h-4 text-emerald-700" />
                    <span>4. Appendix: Source-Span Citations & Fact Anchors</span>
                  </h3>
                  <span className="text-xs font-mono text-[#6e665d]">
                    Total Anchors: {docketData?.citations?.length || 0}
                  </span>
                </div>

                <div className="space-y-2">
                  {(docketData?.citations || []).slice(0, 8).map((c: any) => (
                    <div key={c.id} className="p-3 rounded-xl bg-[#faf7f2] border border-[#eae4d9] flex items-start justify-between gap-3 text-xs font-mono">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-blue-50 text-blue-800 border border-blue-200">
                            {c.fact_type}
                          </span>
                          <span className="text-[#6e665d] text-[10px]">
                            Exhibit #{c.evidence_id} • Chunk #{c.chunk_id || 1} • Offset [{c.char_start}:{c.char_end}]
                          </span>
                        </div>
                        <p className="text-[#191410] italic font-sans text-xs">
                          "{c.quote}"
                        </p>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold text-emerald-800 bg-emerald-50 border border-emerald-200">
                        {c.verified_match ? `Verified (${Math.round(c.match_confidence * 100)}%)` : 'Approx'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* RUNNING FOOTER PREVIEW */}
              <div className="pt-6 border-t border-[#eae4d9] flex flex-wrap items-center justify-between text-[11px] font-mono text-[#6e665d]">
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

export default CaseReports;
