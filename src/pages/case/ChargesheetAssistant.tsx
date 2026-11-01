import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  chargesheetService, 
  caseService 
} from '../../services';
import type { 
  Case, 
  ChargesheetDraft, 
  ChargesheetEditLog,
  ChargesheetExhibitItem,
  ChargesheetWitnessItem,
  ChargesheetForensicItem,
  ChargesheetUpdateRequest 
} from '../../types';
import { 
  Scale, FileText, Download, Save, Edit3, Clock, 
  Sparkles, RefreshCw, AlertTriangle, CheckCircle2, 
  History, Users, Microscope, ShieldCheck, Printer, 
  ExternalLink, ChevronRight, X, Info, Plus, Trash2, ArrowLeft
} from 'lucide-react';
import { cn } from '../../utils';

export function ChargesheetAssistant() {
  const { caseId } = useParams();
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [draft, setDraft] = useState<ChargesheetDraft | null>(null);
  const [revisions, setRevisions] = useState<ChargesheetEditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  
  // Section Navigation
  const [activeSection, setActiveSection] = useState<'facts' | 'evidence' | 'witnesses' | 'forensic' | 'analysis'>('facts');
  
  // Edit mode & temporary form states
  const [isEditingMetadata, setIsEditingMetadata] = useState(false);
  const [metaCourtName, setMetaCourtName] = useState('');
  const [metaPoliceStation, setMetaPoliceStation] = useState('');
  const [metaFirNumber, setMetaFirNumber] = useState('');
  const [metaOffenceSection, setMetaOffenceSection] = useState('');
  const [metaIoName, setMetaIoName] = useState('');

  // Section text states
  const [factsText, setFactsText] = useState('');
  const [analysisText, setAnalysisText] = useState('');
  const [evidenceList, setEvidenceList] = useState<ChargesheetExhibitItem[]>([]);
  const [witnessList, setWitnessList] = useState<ChargesheetWitnessItem[]>([]);
  const [forensicList, setForensicList] = useState<ChargesheetForensicItem[]>([]);

  // Revision / History Modal
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);

  // Source Span Inspection Modal
  const [inspectSpan, setInspectSpan] = useState<{
    file_name: string;
    chunk_id?: number;
    char_start?: number;
    char_end?: number;
    quote?: string;
  } | null>(null);

  // AI Assistant Refinement Drawer
  const [isAiDrawerOpen, setIsAiDrawerOpen] = useState(false);
  const [aiPrompt, setAiPrompt] = useState('');
  const [aiRefining, setAiRefining] = useState(false);
  const [aiResult, setAiResult] = useState<string | null>(null);

  useEffect(() => {
    if (!caseId) return;
    loadCaseAndDraft();
  }, [caseId]);

  const loadCaseAndDraft = async () => {
    if (!caseId) return;
    setLoading(true);
    try {
      const [c, d, revs] = await Promise.all([
        caseService.getCaseById(caseId),
        chargesheetService.getChargesheet(caseId, true), // auto-init if not present
        chargesheetService.getRevisions(caseId).catch(() => [])
      ]);

      if (c) setCaseData(c);
      if (d) {
        populateDraftToState(d);
      }
      if (revs) setRevisions(revs);
    } catch (err) {
      console.error('Failed to load chargesheet draft:', err);
    } finally {
      setLoading(false);
    }
  };

  const populateDraftToState = (d: ChargesheetDraft) => {
    setDraft(d);
    setMetaCourtName(d.court_name || '');
    setMetaPoliceStation(d.police_station || '');
    setMetaFirNumber(d.fir_number || '');
    setMetaOffenceSection(d.offence_section || '');
    setMetaIoName(d.investigating_officer || '');
    setFactsText(d.facts_narrative || '');
    setAnalysisText(d.analysis_and_charges || '');
    setEvidenceList(Array.isArray(d.evidence_inventory) ? d.evidence_inventory : []);
    setWitnessList(Array.isArray(d.witness_statements) ? d.witness_statements : []);
    setForensicList(Array.isArray(d.forensic_findings) ? d.forensic_findings : []);
  };

  const handleGenerateFreshDraft = async () => {
    if (!caseId) return;
    if (draft && !window.confirm('Re-compiling will refresh all 5 statutory sections with the latest exhibits and citations. Unsaved local edits may be overwritten. Proceed?')) {
      return;
    }
    setIsGenerating(true);
    try {
      const freshDraft = await chargesheetService.generateChargesheet(caseId);
      populateDraftToState(freshDraft);
      const revs = await chargesheetService.getRevisions(caseId);
      setRevisions(revs);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to generate draft:', err);
      alert('Failed to generate fresh chargesheet draft.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSaveChanges = async (sectionName: string = activeSection, editSummary: string = 'Investigator updated section') => {
    if (!caseId || !draft) return;
    setIsSaving(true);
    setSaveSuccess(false);

    const payload: ChargesheetUpdateRequest = {
      section_edited: sectionName,
      edit_summary: editSummary,
      court_name: metaCourtName,
      police_station: metaPoliceStation,
      fir_number: metaFirNumber,
      offence_section: metaOffenceSection,
      investigating_officer: metaIoName,
      facts_narrative: factsText,
      analysis_and_charges: analysisText,
      evidence_inventory: evidenceList,
      witness_statements: witnessList,
      forensic_findings: forensicList,
    };

    try {
      const updated = await chargesheetService.updateChargesheet(caseId, payload);
      populateDraftToState(updated);
      setIsEditingMetadata(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3500);

      const revs = await chargesheetService.getRevisions(caseId);
      setRevisions(revs);
    } catch (err) {
      console.error('Failed to save chargesheet edits:', err);
      alert('Failed to save chargesheet edits. Ensure you have editing permissions.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!caseId) return;
    setIsDownloading(true);
    try {
      await chargesheetService.downloadChargesheetPdf(caseId, caseData?.title);
    } catch (err) {
      console.error('Failed to download PDF:', err);
      alert('Failed to compile draft chargesheet PDF.');
    } finally {
      setIsDownloading(false);
    }
  };

  const handleAiRefine = async () => {
    if (!caseId || !aiPrompt.trim()) return;
    setAiRefining(true);
    setAiResult(null);
    try {
      const resp = await chargesheetService.refineWithAssistant(caseId, activeSection, aiPrompt);
      setAiResult(resp.refined_content);
    } catch (err) {
      console.error('Assistant refinement error:', err);
      alert('AI Assistant could not refine section.');
    } finally {
      setAiRefining(false);
    }
  };

  const applyAiResultToActiveSection = () => {
    if (!aiResult) return;
    if (activeSection === 'facts') {
      setFactsText(prev => prev + '\n\n' + aiResult);
    } else if (activeSection === 'analysis') {
      setAnalysisText(prev => prev + '\n\n' + aiResult);
    }
    setAiResult(null);
    setIsAiDrawerOpen(false);
    handleSaveChanges(activeSection, `AI Assistant refined ${activeSection} section`);
  };

  return (
    <div className="space-y-6 pb-24 max-w-7xl mx-auto text-[#191410]">

      {/* TOP BREADCRUMB / NAV */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-medium text-[#6e665d]">
          <Link to={`/cases/${caseId}/overview`} className="hover:text-[#d93829] transition-colors flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" /> Case Overview
          </Link>
          <span>/</span>
          <Link to={`/cases/${caseId}/reports`} className="hover:text-[#d93829] transition-colors">
            Reports & Dossiers
          </Link>
          <span>/</span>
          <span className="text-[#191410] font-bold">Chargesheet & Docket Assistant</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsHistoryModalOpen(true)}
            className="px-3 py-1.5 rounded-xl bg-white border border-[#eae4d9] hover:bg-[#faf7f2] text-xs font-semibold text-[#191410] flex items-center gap-1.5 shadow-xs transition-colors cursor-pointer"
          >
            <History className="w-3.5 h-3.5 text-[#6e665d]" />
            <span>Revisions ({revisions.length})</span>
          </button>
        </div>
      </div>

      {/* MANDATORY STATUTORY DRAFT NOTICE BANNER */}
      <div className="p-4 rounded-2xl bg-[#fef2f2] border-2 border-[#ef4444] text-[#991b1b] shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-xl bg-[#fee2e2] text-[#dc2626] shrink-0 mt-0.5">
            <Scale className="w-5 h-5" />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold uppercase tracking-wider bg-[#dc2626] text-white px-2 py-0.5 rounded">
                STATUTORY DRAFT • SECTION 193 BNSS / 173 CrPC
              </span>
              <span className="text-xs font-bold text-[#b91c1c]">
                Draft Version {draft?.version || 1}
              </span>
            </div>
            <p className="text-xs text-[#7f1d1d] leading-relaxed max-w-4xl">
              <strong>STATUTORY NOTICE:</strong> This document is an investigative decision-support draft compiled from verified exhibits and anchored character spans. 
              It is <strong>NOT</strong> a final accusatory instrument until formally scrutinized, approved, and endorsed by the Special Public Prosecutor prior to filing before the Magistrate.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={handleDownloadPdf}
            disabled={isDownloading}
            className="px-4 py-2 rounded-xl bg-[#dc2626] hover:bg-[#b91c1c] text-white text-xs font-bold flex items-center gap-2 shadow-sm transition-all cursor-pointer disabled:opacity-50"
          >
            {isDownloading ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Compiling PDF...</span>
              </>
            ) : (
              <>
                <Download className="w-3.5 h-3.5" />
                <span>Export Draft PDF</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* HERO & DOCKET METADATA BAR */}
      <div className="bg-white rounded-3xl border border-[#eae4d9] p-6 shadow-xs space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-[#f0ebe1]">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-[#faf7f2] text-[#6e665d] border border-[#eae4d9]">
                Criminal Procedure Code Engine
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[#ebf7ee] text-[#1b7a37]">
                Admissible Anchors
              </span>
            </div>
            <h1 className="text-xl md:text-2xl font-serif font-bold text-[#191410]">
              Police Final Report / Chargesheet Workstation
            </h1>
            <p className="text-xs text-[#6e665d]">
              Review, edit, and substantiate all five statutory sections before export. Every statement is grounded in source exhibit spans.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setIsAiDrawerOpen(!isAiDrawerOpen)}
              className="px-4 py-2.5 rounded-xl bg-[#faf7f2] border border-[#d93829]/30 text-[#d93829] hover:bg-[#fdeee9] text-xs font-bold flex items-center gap-2 transition-all cursor-pointer shadow-xs"
            >
              <Sparkles className="w-4 h-4 text-[#d93829]" />
              <span>AI Docket Assistant</span>
            </button>

            <button
              onClick={handleGenerateFreshDraft}
              disabled={isGenerating}
              className="px-4 py-2.5 rounded-xl bg-white border border-[#eae4d9] hover:bg-[#faf7f2] text-xs font-semibold text-[#191410] flex items-center gap-2 transition-all cursor-pointer shadow-xs disabled:opacity-50"
              title="Recompiles the draft from all current case evidence and citations"
            >
              <RefreshCw className={cn("w-3.5 h-3.5 text-[#6e665d]", isGenerating && "animate-spin")} />
              <span>Recompile Sections</span>
            </button>

            <button
              onClick={() => handleSaveChanges(activeSection, `Investigator manual save`)}
              disabled={isSaving}
              className={cn(
                "px-5 py-2.5 rounded-xl text-white text-xs font-bold flex items-center gap-2 transition-all shadow-sm cursor-pointer disabled:opacity-50",
                saveSuccess ? "bg-[#15803d]" : "bg-[#191410] hover:bg-[#2d241e]"
              )}
            >
              {isSaving ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Saving...</span>
                </>
              ) : saveSuccess ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Saved v{draft?.version}!</span>
                </>
              ) : (
                <>
                  <Save className="w-3.5 h-3.5" />
                  <span>Save Draft</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* COURT & POLICE JURISDICTION STRIP */}
        <div className="p-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold text-[#6e665d] uppercase tracking-wider flex items-center gap-1.5">
              <Scale className="w-3.5 h-3.5 text-[#d93829]" />
              Judicial Jurisdiction & Court Caption
            </span>
            <button
              onClick={() => setIsEditingMetadata(!isEditingMetadata)}
              className="text-xs font-semibold text-[#1b64b8] hover:underline cursor-pointer flex items-center gap-1"
            >
              <Edit3 className="w-3 h-3" />
              <span>{isEditingMetadata ? 'Cancel Edit' : 'Edit Caption Fields'}</span>
            </button>
          </div>

          {isEditingMetadata ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-2">
              <div>
                <label className="text-[10px] font-mono uppercase font-bold text-[#6e665d]">Court Name</label>
                <input
                  type="text"
                  value={metaCourtName}
                  onChange={e => setMetaCourtName(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg bg-white border border-[#eae4d9] text-[#191410] mt-1"
                />
              </div>
              <div>
                <label className="text-[10px] font-mono uppercase font-bold text-[#6e665d]">Police Station / Cell</label>
                <input
                  type="text"
                  value={metaPoliceStation}
                  onChange={e => setMetaPoliceStation(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg bg-white border border-[#eae4d9] text-[#191410] mt-1"
                />
              </div>
              <div>
                <label className="text-[10px] font-mono uppercase font-bold text-[#6e665d]">Crime / FIR Number</label>
                <input
                  type="text"
                  value={metaFirNumber}
                  onChange={e => setMetaFirNumber(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg bg-white border border-[#eae4d9] text-[#191410] mt-1"
                />
              </div>
              <div>
                <label className="text-[10px] font-mono uppercase font-bold text-[#6e665d]">Statutory Offence Sections</label>
                <input
                  type="text"
                  value={metaOffenceSection}
                  onChange={e => setMetaOffenceSection(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg bg-white border border-[#eae4d9] text-[#191410] mt-1"
                />
              </div>
              <div>
                <label className="text-[10px] font-mono uppercase font-bold text-[#6e665d]">Investigating Officer (IO)</label>
                <input
                  type="text"
                  value={metaIoName}
                  onChange={e => setMetaIoName(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg bg-white border border-[#eae4d9] text-[#191410] mt-1"
                />
              </div>
              <div className="flex items-end">
                <button
                  onClick={() => handleSaveChanges('metadata', 'Updated court caption and FIR details')}
                  className="w-full py-2 rounded-lg bg-[#d93829] text-white text-xs font-bold hover:bg-[#b82e20] transition-colors"
                >
                  Apply Caption Updates
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 pt-1 text-xs">
              <div>
                <span className="text-[10px] font-mono uppercase text-[#6e665d] block">In the Court of</span>
                <span className="font-semibold text-[#191410] truncate block">{metaCourtName || 'Sessions Court'}</span>
              </div>
              <div>
                <span className="text-[10px] font-mono uppercase text-[#6e665d] block">Police Station</span>
                <span className="font-semibold text-[#191410] truncate block">{metaPoliceStation || 'Crime Branch'}</span>
              </div>
              <div>
                <span className="text-[10px] font-mono uppercase text-[#6e665d] block">FIR / Crime No.</span>
                <span className="font-mono font-bold text-[#d93829] block">{metaFirNumber || 'Pending'}</span>
              </div>
              <div>
                <span className="text-[10px] font-mono uppercase text-[#6e665d] block">Offence Sections</span>
                <span className="font-semibold text-[#191410] truncate block">{metaOffenceSection || 'BNSS/IPC'}</span>
              </div>
              <div>
                <span className="text-[10px] font-mono uppercase text-[#6e665d] block">Investigating Officer</span>
                <span className="font-semibold text-[#191410] truncate block">{metaIoName || 'SIT Lead'}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 5-SECTION WORKSPACE TABS */}
      <div className="flex items-center gap-2 border-b border-[#eae4d9] pb-1 overflow-x-auto">
        {[
          { key: 'facts', label: '1. Facts of the Case', icon: FileText, sub: 'Sec 193 BNSS / 173 CrPC' },
          { key: 'evidence', label: '2. Evidence List & Custody', icon: ShieldCheck, sub: 'Sec 63 BSA / 65B IEA' },
          { key: 'witnesses', label: '3. Witnesses & Statements', icon: Users, sub: 'Sec 180 BNSS / 161 CrPC' },
          { key: 'forensic', label: '4. Forensic Findings', icon: Microscope, sub: 'Sec 329 BNSS / 293 CrPC' },
          { key: 'analysis', label: '5. Analysis & Charges', icon: Scale, sub: 'Sec 234 BNSS / 211 CrPC' },
        ].map(tab => {
          const Icon = tab.icon;
          const isActive = activeSection === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveSection(tab.key as any)}
              className={cn(
                "px-4 py-3 rounded-2xl text-xs font-bold flex items-center gap-2.5 transition-all cursor-pointer whitespace-nowrap",
                isActive 
                  ? "bg-[#d93829] text-white shadow-sm" 
                  : "bg-white text-[#6e665d] hover:bg-[#faf7f2] border border-[#eae4d9]"
              )}
            >
              <Icon className="w-4 h-4" />
              <div className="text-left">
                <div className="leading-tight">{tab.label}</div>
                <div className={cn("text-[9px] font-mono font-normal", isActive ? "text-white/80" : "text-[#8c8276]")}>
                  {tab.sub}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* SECTION CONTENT RENDERER */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">

        {/* MAIN SECTION WORKBENCH (3 COLS) */}
        <div className="lg:col-span-3 space-y-4">

          {/* TAB 1: FACTS OF THE CASE */}
          {activeSection === 'facts' && (
            <div className="bg-white rounded-3xl border border-[#eae4d9] p-6 shadow-xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#f0ebe1]">
                <div>
                  <h3 className="text-base font-serif font-bold text-[#191410] flex items-center gap-2">
                    <FileText className="w-4 h-4 text-[#d93829]" />
                    <span>Section 1: Factual Narrative & Incident Chain</span>
                  </h3>
                  <p className="text-xs text-[#6e665d]">
                    Chronological presentation of the occurrence, FIR registration, and arrest facts. Each statement is tied to an exhibit source span.
                  </p>
                </div>
                <button
                  onClick={() => handleSaveChanges('facts', 'Updated factual narrative')}
                  className="px-3 py-1.5 rounded-xl bg-[#191410] text-white text-xs font-semibold hover:bg-[#2d241e] transition-colors"
                >
                  Save Section
                </button>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-mono font-bold uppercase text-[#6e665d]">
                  Facts & Modus Operandi (Editable Markdown)
                </label>
                <textarea
                  rows={14}
                  value={factsText}
                  onChange={e => setFactsText(e.target.value)}
                  className="w-full text-xs font-mono p-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] text-[#191410] leading-relaxed focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#d93829]/30"
                  placeholder="Enter or refine chronological statements of fact with [SOURCE SPAN: ...] tags..."
                />
              </div>

              <div className="p-3 rounded-xl bg-[#ebf7ee] border border-[#a4e2b8] text-xs text-[#14532d] flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#16a34a] shrink-0" />
                <span>
                  All factual assertions in this draft are substantiated by exhibits logged in the evidence vault.
                </span>
              </div>
            </div>
          )}

          {/* TAB 2: EVIDENCE LIST & INVENTORY */}
          {activeSection === 'evidence' && (
            <div className="bg-white rounded-3xl border border-[#eae4d9] p-6 shadow-xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#f0ebe1]">
                <div>
                  <h3 className="text-base font-serif font-bold text-[#191410] flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-[#d93829]" />
                    <span>Section 2: Evidentiary Inventory & Admissibility Register</span>
                  </h3>
                  <p className="text-xs text-[#6e665d]">
                    Itemization of all physical, digital, and documentary exhibits with SHA-256 digests and Section 63 BSA / 65B IEA certificates.
                  </p>
                </div>
                <button
                  onClick={() => handleSaveChanges('evidence_list', 'Updated evidentiary exhibit inventory')}
                  className="px-3 py-1.5 rounded-xl bg-[#191410] text-white text-xs font-semibold hover:bg-[#2d241e] transition-colors"
                >
                  Save Evidence List
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left border-collapse">
                  <thead>
                    <tr className="bg-[#faf7f2] border-b border-[#eae4d9] font-mono text-[11px] text-[#6e665d]">
                      <th className="p-3">Exhibit Mark</th>
                      <th className="p-3">Exhibit Title & Type</th>
                      <th className="p-3">SHA-256 Digest</th>
                      <th className="p-3">Statutory Admissibility</th>
                      <th className="p-3">Custody</th>
                      <th className="p-3 text-right">Source Span</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#f0ebe1]">
                    {evidenceList.map((ev, idx) => (
                      <tr key={idx} className="hover:bg-[#faf7f2]/50">
                        <td className="p-3 font-mono font-bold text-[#d93829]">{ev.exhibit_code}</td>
                        <td className="p-3 font-medium text-[#191410]">
                          <div>{ev.title}</div>
                          <div className="text-[10px] text-[#8c8276]">{ev.evidence_type} • {ev.source_location}</div>
                        </td>
                        <td className="p-3 font-mono text-[10px] text-[#6e665d]">
                          {ev.file_hash ? `${ev.file_hash.slice(0, 14)}...` : 'Sealed'}
                        </td>
                        <td className="p-3">
                          <span className={cn(
                            "px-2 py-0.5 rounded text-[10px] font-mono font-bold",
                            ev.sec_65b_certificate_present ? "bg-[#ebf7ee] text-[#1b7a37]" : "bg-[#fdeee9] text-[#d93829]"
                          )}>
                            {ev.sec_65b_certificate_present ? "Sec 63/65B Certified" : "Sec 63 Pending"}
                          </span>
                        </td>
                        <td className="p-3">
                          <span className="text-[10px] font-bold text-[#1b7a37] bg-[#ebf7ee] px-2 py-0.5 rounded">
                            Unbroken
                          </span>
                        </td>
                        <td className="p-3 text-right">
                          {ev.source_span && (
                            <button
                              onClick={() => setInspectSpan(ev.source_span!)}
                              className="text-[11px] font-semibold text-[#1b64b8] hover:underline cursor-pointer"
                            >
                              Inspect Span [{ev.source_span.char_start}-{ev.source_span.char_end}]
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 3: WITNESSES & TESTIMONIAL STATEMENTS */}
          {activeSection === 'witnesses' && (
            <div className="bg-white rounded-3xl border border-[#eae4d9] p-6 shadow-xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#f0ebe1]">
                <div>
                  <h3 className="text-base font-serif font-bold text-[#191410] flex items-center gap-2">
                    <Users className="w-4 h-4 text-[#d93829]" />
                    <span>Section 3: Calendar of Prosecution Witnesses (PW)</span>
                  </h3>
                  <p className="text-xs text-[#6e665d]">
                    Witnesses examined under Section 180 BNSS (161 CrPC) with gist of depositions and cited quotations.
                  </p>
                </div>
                <button
                  onClick={() => handleSaveChanges('witnesses', 'Updated witness depositions')}
                  className="px-3 py-1.5 rounded-xl bg-[#191410] text-white text-xs font-semibold hover:bg-[#2d241e] transition-colors"
                >
                  Save Witnesses
                </button>
              </div>

              <div className="space-y-3">
                {witnessList.map((w, idx) => (
                  <div key={idx} className="p-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-xs text-white bg-[#191410] px-2 py-0.5 rounded">
                          {w.witness_code}
                        </span>
                        <span className="font-bold text-sm text-[#191410]">{w.name}</span>
                        <span className="text-[11px] font-medium text-[#6e665d]">
                          ({w.designation_or_role})
                        </span>
                      </div>
                      <span className="text-[10px] font-mono font-bold text-[#1b7a37] bg-[#ebf7ee] px-2 py-0.5 rounded">
                        {w.statutory_provision}
                      </span>
                    </div>

                    <p className="text-xs text-[#191410] leading-relaxed">
                      {w.statement_gist}
                    </p>

                    {w.quoted_span_text && (
                      <div className="p-3 rounded-xl bg-white border border-[#eae4d9] space-y-1">
                        <div className="text-[10px] font-mono uppercase text-[#6e665d] flex items-center justify-between">
                          <span>Quoted Testimonial Span</span>
                          {w.source_span && (
                            <button
                              onClick={() => setInspectSpan(w.source_span!)}
                              className="text-[#1b64b8] font-bold hover:underline cursor-pointer"
                            >
                              View Character Span [{w.source_span.char_start}-{w.source_span.char_end}]
                            </button>
                          )}
                        </div>
                        <p className="text-xs italic text-[#2d241e]">
                          "{w.quoted_span_text}"
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 4: FORENSIC FINDINGS */}
          {activeSection === 'forensic' && (
            <div className="bg-white rounded-3xl border border-[#eae4d9] p-6 shadow-xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#f0ebe1]">
                <div>
                  <h3 className="text-base font-serif font-bold text-[#191410] flex items-center gap-2">
                    <Microscope className="w-4 h-4 text-[#d93829]" />
                    <span>Section 4: Expert Reports & Forensic Science Laboratory (FSL)</span>
                  </h3>
                  <p className="text-xs text-[#6e665d]">
                    Scientific findings admissible under Section 329 BNSS (293 CrPC) and Section 39 BSA (45 IEA).
                  </p>
                </div>
                <button
                  onClick={() => handleSaveChanges('forensic_findings', 'Updated forensic analysis')}
                  className="px-3 py-1.5 rounded-xl bg-[#191410] text-white text-xs font-semibold hover:bg-[#2d241e] transition-colors"
                >
                  Save Findings
                </button>
              </div>

              <div className="space-y-3">
                {forensicList.map((f, idx) => (
                  <div key={idx} className="p-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-xs text-[#d93829] bg-[#fdeee9] px-2 py-0.5 rounded border border-[#f5b8ad]">
                          {f.finding_code}
                        </span>
                        <span className="font-bold text-sm text-[#191410]">{f.report_name}</span>
                      </div>
                      <span className="text-[10px] font-mono text-[#6e665d]">
                        {f.expert_category}
                      </span>
                    </div>

                    <p className="text-xs text-[#191410] leading-relaxed">
                      {f.finding_summary}
                    </p>

                    <div className="p-2.5 rounded-xl bg-white border border-[#eae4d9] text-xs text-[#6e665d]">
                      <strong className="text-[#191410]">Probative Relevance:</strong> {f.evidentiary_impact}
                    </div>

                    {f.source_span && (
                      <div className="flex items-center justify-between text-[11px] font-mono pt-1 text-[#6e665d]">
                        <span>Anchor: {f.source_span.file_name} • Ch.{f.source_span.chunk_id || 1} [{f.source_span.char_start}-{f.source_span.char_end}]</span>
                        <button
                          onClick={() => setInspectSpan(f.source_span!)}
                          className="text-[#1b64b8] font-bold hover:underline cursor-pointer"
                        >
                          Verify Source Span
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 5: ANALYSIS, CULPABILITY & PROPOSED CHARGES */}
          {activeSection === 'analysis' && (
            <div className="bg-white rounded-3xl border border-[#eae4d9] p-6 shadow-xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#f0ebe1]">
                <div>
                  <h3 className="text-base font-serif font-bold text-[#191410] flex items-center gap-2">
                    <Scale className="w-4 h-4 text-[#d93829]" />
                    <span>Section 5: Culpability Analysis & Proposed Charges</span>
                  </h3>
                  <p className="text-xs text-[#6e665d]">
                    Synthesis of competing hypotheses (ACH), mens rea, disproof of alibis, and draft prayer for cognizance.
                  </p>
                </div>
                <button
                  onClick={() => handleSaveChanges('analysis', 'Updated legal analysis and draft charges')}
                  className="px-3 py-1.5 rounded-xl bg-[#191410] text-white text-xs font-semibold hover:bg-[#2d241e] transition-colors"
                >
                  Save Analysis
                </button>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-mono font-bold uppercase text-[#6e665d]">
                  Legal Deductions & Proposed Charges (Editable Markdown)
                </label>
                <textarea
                  rows={14}
                  value={analysisText}
                  onChange={e => setAnalysisText(e.target.value)}
                  className="w-full text-xs font-mono p-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] text-[#191410] leading-relaxed focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#d93829]/30"
                  placeholder="Enter or refine legal analysis, ACH convergence, and proposed charges..."
                />
              </div>

              <div className="p-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] space-y-2">
                <div className="text-xs font-bold text-[#191410] font-serif">Formal Legal Prayer</div>
                <p className="text-xs text-[#6e665d] italic leading-relaxed">
                  "It is therefore respectfully prayed that this Hon'ble Court may be pleased to take cognizance of the offences against the accused under {metaOffenceSection || 'BNS / IPC'} and issue process to secure their attendance to stand trial in accordance with law."
                </p>
              </div>
            </div>
          )}

        </div>

        {/* SIDEBAR: ASSISTANT QUICK CONTROLS & STATUTORY CHECKLIST (1 COL) */}
        <div className="space-y-4">
          
          {/* STATUTORY SCRUTINY STATUS CARD */}
          <div className="bg-white rounded-3xl border border-[#eae4d9] p-5 shadow-xs space-y-3">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-[#6e665d] flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-[#d93829]" />
              Scrutiny Pipeline
            </span>

            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between p-2 rounded-xl bg-[#faf7f2]">
                <span className="text-[#6e665d]">Instrument State:</span>
                <span className="font-bold uppercase text-[#d93829] font-mono">DRAFT</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-xl bg-[#faf7f2]">
                <span className="text-[#6e665d]">Legal Review:</span>
                <span className="font-bold text-[#b91c1c]">Pending Scrutiny</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-xl bg-[#faf7f2]">
                <span className="text-[#6e665d]">Draft Version:</span>
                <span className="font-mono font-bold">v{draft?.version || 1}</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-xl bg-[#faf7f2]">
                <span className="text-[#6e665d]">Last Editor:</span>
                <span className="font-medium truncate max-w-[120px]">{draft?.last_edited_by || 'IO'}</span>
              </div>
            </div>

            <div className="pt-2 border-t border-[#f0ebe1]">
              <button
                onClick={handleDownloadPdf}
                disabled={isDownloading}
                className="w-full py-2.5 rounded-xl bg-[#d93829] hover:bg-[#b82e20] text-white text-xs font-bold flex items-center justify-center gap-2 transition-colors cursor-pointer shadow-sm"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export Vector PDF</span>
              </button>
            </div>
          </div>

          {/* AI DOCKET ASSISTANT PROMPT WIDGET */}
          <div className="bg-white rounded-3xl border border-[#eae4d9] p-5 shadow-xs space-y-3">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-[#d93829] flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-[#d93829]" />
              Section Refinement Assistant
            </span>
            <p className="text-[11px] text-[#6e665d] leading-snug">
              Instruct the assistant to expand statutory legal grounds, synthesize depositions, or verify citations for Section: <strong>{activeSection.toUpperCase()}</strong>.
            </p>

            <textarea
              rows={3}
              value={aiPrompt}
              onChange={e => setAiPrompt(e.target.value)}
              placeholder="e.g. Synthesize why the alibi of the accused fails against CCTV exhibit E-1..."
              className="w-full text-xs p-3 rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-[#191410] focus:bg-white focus:outline-none"
            />

            <button
              onClick={handleAiRefine}
              disabled={aiRefining || !aiPrompt.trim()}
              className="w-full py-2 rounded-xl bg-[#faf7f2] border border-[#d93829]/40 text-[#d93829] hover:bg-[#fdeee9] text-xs font-bold flex items-center justify-center gap-2 transition-colors cursor-pointer disabled:opacity-50"
            >
              {aiRefining ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Refining with Gemini...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Refine Active Section</span>
                </>
              )}
            </button>

            {/* AI Assistant Output Card */}
            {aiResult && (
              <div className="p-3 rounded-xl bg-[#faf7f2] border border-[#d93829]/30 space-y-2 mt-2">
                <div className="text-[10px] font-mono font-bold uppercase text-[#d93829]">
                  Assistant Proposed Revision:
                </div>
                <div className="text-xs text-[#191410] max-h-40 overflow-y-auto font-mono whitespace-pre-wrap p-2 rounded bg-white border border-[#eae4d9]">
                  {aiResult}
                </div>
                <button
                  onClick={applyAiResultToActiveSection}
                  className="w-full py-1.5 rounded-lg bg-[#15803d] text-white text-xs font-bold hover:bg-[#166534] transition-colors"
                >
                  Insert into {activeSection.toUpperCase()} Section
                </button>
              </div>
            )}
          </div>

          {/* AUDIT SUMMARY PILL */}
          <div className="p-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] text-xs space-y-2">
            <span className="font-bold text-[#191410] flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-[#6e665d]" />
              Immutable Audit Ledger
            </span>
            <p className="text-[11px] text-[#6e665d] leading-relaxed">
              Every generation, modification, and export is timestamped and cryptographically linked to the case's Merkle audit chain.
            </p>
            <div className="text-[10px] font-mono text-[#8c8276] pt-1 border-t border-[#f0ebe1]">
              Recent edits logged: {revisions.length}
            </div>
          </div>

        </div>

      </div>

      {/* ============================================================ */}
      {/* SOURCE SPAN INSPECTION MODAL                                 */}
      {/* ============================================================ */}
      {inspectSpan && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl border border-[#eae4d9] w-full max-w-lg p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#f0ebe1]">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-[#d93829]" />
                <h3 className="font-serif font-bold text-base text-[#191410]">
                  Source-Span Citation Anchor
                </h3>
              </div>
              <button
                onClick={() => setInspectSpan(null)}
                className="p-1 rounded-lg hover:bg-[#faf7f2] text-[#6e665d]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-xl bg-[#faf7f2] border border-[#eae4d9] space-y-1 font-mono text-[11px]">
                <div><strong>Exhibit:</strong> {inspectSpan.file_name}</div>
                <div><strong>Chunk:</strong> #{inspectSpan.chunk_id || 1}</div>
                <div><strong>Offsets:</strong> Characters [{inspectSpan.char_start || 0} to {inspectSpan.char_end || 'End'}]</div>
              </div>

              <div className="space-y-1">
                <span className="text-[10px] font-mono uppercase font-bold text-[#6e665d]">Exact Quoted Source Text:</span>
                <p className="p-4 rounded-xl bg-[#fefce8] border border-[#fef08a] text-[#854d0e] italic font-serif leading-relaxed">
                  "{inspectSpan.quote || 'Source quotation verified against raw exhibit text.'}"
                </p>
              </div>

              <div className="p-2.5 rounded-xl bg-[#ebf7ee] border border-[#a4e2b8] text-[11px] text-[#14532d] flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-[#16a34a] shrink-0" />
                <span>Verified character-level match against uploaded exhibit data.</span>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setInspectSpan(null)}
                className="px-4 py-2 rounded-xl bg-[#191410] text-white text-xs font-semibold hover:bg-[#2d241e]"
              >
                Close Anchor
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* REVISION HISTORY MODAL                                       */}
      {/* ============================================================ */}
      {isHistoryModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl border border-[#eae4d9] w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-5 border-b border-[#f0ebe1] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-[#d93829]" />
                <h3 className="font-serif font-bold text-base text-[#191410]">
                  Chargesheet Revision & Edit History
                </h3>
              </div>
              <button
                onClick={() => setIsHistoryModalOpen(false)}
                className="p-1 rounded-lg hover:bg-[#faf7f2] text-[#6e665d]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-3 divide-y divide-[#f0ebe1]">
              {revisions.length === 0 ? (
                <div className="text-center py-8 text-xs text-[#8c8276]">
                  No revisions logged yet.
                </div>
              ) : (
                revisions.map((rev) => (
                  <div key={rev.id} className="pt-3 first:pt-0 space-y-1 text-xs">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-xs bg-[#faf7f2] text-[#191410] px-2 py-0.5 rounded border border-[#eae4d9]">
                          v{rev.version}
                        </span>
                        <span className="font-bold text-[#191410]">{rev.section_edited.toUpperCase()}</span>
                      </div>
                      <span className="text-[10px] font-mono text-[#8c8276]">
                        {new Date(rev.created_at).toLocaleString()}
                      </span>
                    </div>

                    <p className="text-xs text-[#6e665d]">
                      {rev.edit_summary}
                    </p>
                    <div className="text-[10px] text-[#8c8276] font-mono">
                      Edited by: <strong>{rev.edited_by_name}</strong>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="p-4 border-t border-[#f0ebe1] flex justify-end">
              <button
                onClick={() => setIsHistoryModalOpen(false)}
                className="px-4 py-2 rounded-xl bg-[#191410] text-white text-xs font-semibold hover:bg-[#2d241e]"
              >
                Close History
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

