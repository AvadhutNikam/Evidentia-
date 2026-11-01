// src/pages/case/Handover.tsx
import { useParams, useNavigate } from 'react-router-dom';
import { useEffect, useState, useMemo, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';
import { handoverService, alertService } from '../../services';
import type { 
  HandoverSummary, SinceYouWereAwaySummary, CaseDeadline 
} from '../../types';
import { Card, CardContent } from '../../components/ui/Card';
import {
  ClipboardList, Clock, Calendar, CheckCircle2, AlertTriangle, AlertOctagon,
  FileText, ShieldCheck, Printer, RefreshCw, Plus, ArrowRight, Check,
  ChevronDown, ChevronUp, Scale, Bell, Users, History, Sparkles, Filter
} from 'lucide-react';
import { cn } from '../../utils';

export function Handover() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const { role, user } = useAuth();

  const [sinceAway, setSinceAway] = useState<SinceYouWereAwaySummary | null>(null);
  const [deadlines, setDeadlines] = useState<CaseDeadline[]>([]);
  const [handovers, setHandovers] = useState<HandoverSummary[]>([]);
  const [selectedHandover, setSelectedHandover] = useState<HandoverSummary | null>(null);

  const [loading, setLoading] = useState(true);
  const [sinceAwayAcked, setSinceAwayAcked] = useState(false);

  // Generation Modal State
  const [isGenerateOpen, setIsGenerateOpen] = useState(false);
  const [periodHours, setPeriodHours] = useState<number>(24);
  const [turnoverNotes, setTurnoverNotes] = useState<string>('');
  const [generating, setGenerating] = useState(false);

  // Extension Modal State
  const [isExtendOpen, setIsExtendOpen] = useState(false);
  const [selectedDeadline, setSelectedDeadline] = useState<CaseDeadline | null>(null);
  const [extensionDays, setExtensionDays] = useState<number>(14);
  const [extensionReason, setExtensionReason] = useState<string>('');
  const [extending, setExtending] = useState(false);

  const isLeadOrAdmin = role === 'lead_investigator' || role === 'admin';

  const loadAllData = useCallback(async () => {
    if (!caseId) return;
    try {
      setLoading(true);
      const [awayRes, dlRes, hoRes] = await Promise.allSettled([
        handoverService.getSinceLastVisit(caseId),
        alertService.getDeadlines(caseId),
        handoverService.getHandovers(caseId),
      ]);

      if (awayRes.status === 'fulfilled') setSinceAway(awayRes.value);
      if (dlRes.status === 'fulfilled') setDeadlines(dlRes.value || []);
      if (hoRes.status === 'fulfilled') {
        const hList = hoRes.value || [];
        setHandovers(hList);
        if (hList.length > 0 && !selectedHandover) {
          setSelectedHandover(hList[0]);
        }
      }
    } catch (err) {
      console.error('Failed to load handover data:', err);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  const handleAcknowledgeBriefing = async () => {
    setSinceAwayAcked(true);
  };

  const handleGenerateHandover = async () => {
    if (!caseId) return;
    try {
      setGenerating(true);
      const newSummary = await handoverService.generateHandover(caseId, {
        period_hours: periodHours,
        custom_notes: turnoverNotes.trim() || undefined,
      });
      setHandovers(prev => [newSummary, ...prev]);
      setSelectedHandover(newSummary);
      setIsGenerateOpen(false);
      setTurnoverNotes('');
    } catch (err) {
      console.error('Failed to generate shift handover:', err);
      alert('Could not generate shift handover. Please verify backend connectivity.');
    } finally {
      setGenerating(false);
    }
  };

  const handleExtendDeadline = async () => {
    if (!caseId || !selectedDeadline || !extensionReason.trim()) return;
    try {
      setExtending(true);
      const targetDate = new Date(selectedDeadline.due_date);
      targetDate.setDate(targetDate.getDate() + extensionDays);

      const updated = await alertService.updateDeadline(caseId, selectedDeadline.id, {
        status: 'extended',
        extended_until: targetDate.toISOString(),
        extension_reason: extensionReason.trim(),
      });

      setDeadlines(prev => prev.map(d => d.id === updated.id ? updated : d));
      setIsExtendOpen(false);
      setSelectedDeadline(null);
      setExtensionReason('');
    } catch (err) {
      console.error('Failed to extend statutory deadline:', err);
      alert('Failed to extend deadline.');
    } finally {
      setExtending(false);
    }
  };

  const handleSatisfyDeadline = async (dl: CaseDeadline) => {
    if (!caseId) return;
    if (!window.confirm(`Mark '${dl.title}' as satisfied / filed with the court?`)) return;
    try {
      const updated = await alertService.updateDeadline(caseId, dl.id, {
        status: 'satisfied',
      });
      setDeadlines(prev => prev.map(d => d.id === updated.id ? updated : d));
    } catch (err) {
      console.error('Failed to mark deadline satisfied:', err);
    }
  };

  const handlePrintHandover = () => {
    window.print();
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#eae4d9]">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-[#d93829]">
              <ClipboardList className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold font-serif text-[#191410] flex items-center gap-2">
                Shift Handover & Case Briefing Dossiers
              </h1>
              <p className="text-xs text-[#70685e]">
                Factual synthesis of evidentiary updates, hypothesis shifts, statutory deadlines, and audit entries.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => loadAllData()}
            className="px-3 py-1.5 text-xs font-semibold text-[#70685e] hover:text-[#191410] bg-white border border-[#eae4d9] rounded-xl hover:bg-[#faf7f2] transition-colors flex items-center gap-1.5 cursor-pointer shadow-2xs"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin")} />
            Refresh
          </button>

          <button
            onClick={() => setIsGenerateOpen(true)}
            className="px-3.5 py-1.5 text-xs font-bold text-white bg-[#d93829] hover:bg-[#b82a1d] rounded-xl transition-all flex items-center gap-1.5 cursor-pointer shadow-xs"
          >
            <Plus className="w-4 h-4" />
            Generate Shift Briefing
          </button>
        </div>
      </div>

      {/* 1. "SINCE YOU WERE AWAY" BRIEFING DOSSIER */}
      {sinceAway && !sinceAwayAcked && (
        <div className="rounded-2xl border-2 border-[#d93829]/20 bg-gradient-to-br from-[#fffcf9] via-white to-[#fbf8f3] p-5 shadow-xs relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-[#d93829]/5 rounded-bl-full pointer-events-none" />
          
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[#fdeee9] text-[#d93829] uppercase tracking-wider flex items-center gap-1">
                  <Sparkles className="w-3 h-3" />
                  Since You Were Away
                </span>
                <span className="text-xs text-[#70685e] font-medium">
                  {sinceAway.hours_away > 0 ? `Past ${sinceAway.hours_away} hours of case activity` : 'Current session update'}
                </span>
              </div>

              <h2 className="text-base font-bold text-[#191410]">
                {sinceAway.headline}
              </h2>

              <ul className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-3 pt-2 border-t border-[#eae4d9]/60">
                {sinceAway.summary_points.map((point, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-xs text-[#423c33] leading-relaxed">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#d93829] mt-1.5 shrink-0" />
                    <span>{point}</span>
                  </li>
                ))}
              </ul>

              {sinceAway.recent_active_users.length > 0 && (
                <div className="text-[11px] text-[#70685e] pt-1 flex items-center gap-1.5">
                  <Users className="w-3.5 h-3.5 text-[#8c8276]" />
                  <span>Investigators active during your absence:</span>
                  <span className="font-semibold text-[#191410]">{sinceAway.recent_active_users.join(', ')}</span>
                </div>
              )}
            </div>

            <div className="shrink-0 flex items-center gap-2 self-start md:self-center">
              <button
                onClick={handleAcknowledgeBriefing}
                className="px-4 py-2 text-xs font-bold text-white bg-[#191410] hover:bg-[#332c25] rounded-xl transition-all flex items-center gap-1.5 cursor-pointer shadow-xs"
              >
                <Check className="w-3.5 h-3.5 text-[#22c55e]" />
                Acknowledge & Mark Read
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 2. STATUTORY INVESTIGATION DEADLINES & REMAND TRACKER */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Scale className="w-4 h-4 text-[#1b64b8]" />
            <h2 className="text-sm font-bold text-[#191410] uppercase tracking-wider font-mono">
              Statutory Deadlines & Compliance Status
            </h2>
          </div>
          <span className="text-[11px] text-[#70685e]">
            CrPC 167(2) / BNSS 187(3) Default Bail Controls
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {deadlines.length === 0 ? (
            <div className="col-span-full p-4 rounded-xl border border-dashed border-[#eae4d9] text-center text-xs text-[#70685e]">
              No statutory deadlines flagged for this case. Provide FIR, arrest, or remand dates in case settings to auto-schedule legal limits.
            </div>
          ) : (
            deadlines.map(dl => {
              const isOverdue = dl.status === 'overdue' || dl.days_remaining <= 0;
              const isImminent = dl.days_remaining <= 3 && !isOverdue;
              const isSatisfied = dl.status === 'satisfied';
              const isExtended = dl.status === 'extended';

              return (
                <div 
                  key={dl.id}
                  className={`p-4 rounded-xl border transition-all ${
                    isOverdue 
                      ? 'border-[#d93829] bg-[#fffbf9]' 
                      : isImminent 
                      ? 'border-[#f4c153] bg-[#fffdf5]' 
                      : isSatisfied 
                      ? 'border-[#9fe0b2] bg-[#f4fcf6]' 
                      : 'border-[#eae4d9] bg-white'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-xs font-bold text-[#191410] leading-snug">
                      {dl.title}
                    </span>
                    <span className={`text-[9px] font-mono font-bold uppercase px-2 py-0.5 rounded-full shrink-0 ${
                      isOverdue 
                        ? 'bg-[#fdeee9] text-[#d93829] animate-pulse' 
                        : isImminent 
                        ? 'bg-[#fff8ea] text-[#8a5b00]' 
                        : isSatisfied 
                        ? 'bg-[#ebf7ee] text-[#1b7a37]' 
                        : 'bg-[#ebf4fd] text-[#1b64b8]'
                    }`}>
                      {dl.status}
                    </span>
                  </div>

                  <div className="mt-3 flex items-center justify-between text-xs">
                    <div className="space-y-0.5">
                      <div className="text-[10px] text-[#70685e]">Statutory Expiry</div>
                      <div className="font-mono font-semibold text-[#191410]">
                        {new Date(dl.due_date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
                      </div>
                    </div>

                    <div className="text-right space-y-0.5">
                      <div className="text-[10px] text-[#70685e]">Time Remaining</div>
                      <div className={`font-mono font-bold text-sm ${
                        isOverdue 
                          ? 'text-[#d93829]' 
                          : isImminent 
                          ? 'text-[#b87600]' 
                          : 'text-[#191410]'
                      }`}>
                        {dl.status === 'satisfied' ? 'Filed / Done' : `${dl.days_remaining} Days`}
                      </div>
                    </div>
                  </div>

                  {isExtended && dl.extension_reason && (
                    <div className="mt-2.5 pt-2 border-t border-[#eae4d9] text-[10px] text-[#70685e] leading-snug">
                      <span className="font-semibold text-[#191410]">Court Extension: </span>
                      {dl.extension_reason}
                    </div>
                  )}

                  {/* Actions for Lead / Admin */}
                  {isLeadOrAdmin && dl.status !== 'satisfied' && (
                    <div className="mt-3 pt-2.5 border-t border-[#eae4d9] flex items-center justify-end gap-2 text-[11px]">
                      <button
                        onClick={() => {
                          setSelectedDeadline(dl);
                          setIsExtendOpen(true);
                        }}
                        className="px-2.5 py-1 text-[#1b64b8] hover:bg-[#ebf4fd] font-semibold rounded-md transition-colors cursor-pointer"
                      >
                        Extend...
                      </button>
                      <button
                        onClick={() => handleSatisfyDeadline(dl)}
                        className="px-2.5 py-1 text-[#1b7a37] hover:bg-[#ebf7ee] font-semibold rounded-md transition-colors cursor-pointer"
                      >
                        Mark Satisfied
                      </button>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* 3. HISTORICAL SHIFT HANDOVER BRIEFS & DOSSIER VIEWER */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 pt-2">
        {/* Left Column: Handover List */}
        <div className="lg:col-span-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold text-[#191410] uppercase tracking-wider font-mono flex items-center gap-1.5">
              <History className="w-3.5 h-3.5 text-[#8c8276]" />
              Historical Turnovers
            </h2>
            <span className="text-[10px] font-mono text-[#8c8276]">
              {handovers.length} recorded
            </span>
          </div>

          <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
            {handovers.length === 0 ? (
              <div className="p-6 text-center border border-dashed border-[#eae4d9] rounded-xl text-xs text-[#70685e]">
                No shift handovers generated yet. Click "Generate Shift Briefing" above to record one.
              </div>
            ) : (
              handovers.map(ho => {
                const isSelected = selectedHandover?.id === ho.id;
                return (
                  <div
                    key={ho.id}
                    onClick={() => setSelectedHandover(ho)}
                    className={`p-3.5 rounded-xl border text-left cursor-pointer transition-all ${
                      isSelected 
                        ? 'border-[#d93829] bg-[#fffaf8] shadow-2xs' 
                        : 'border-[#eae4d9] bg-white hover:bg-[#faf7f2]'
                    }`}
                  >
                    <div className="flex items-center justify-between text-[10px] text-[#70685e]">
                      <span className="font-mono font-medium">
                        {new Date(ho.created_at).toLocaleString('en-GB', { 
                          day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' 
                        })}
                      </span>
                      <span className="capitalize font-mono px-1.5 py-0.2 bg-[#f4efe6] rounded text-[#70685e]">
                        {ho.generation_type}
                      </span>
                    </div>

                    <div className="text-xs font-bold text-[#191410] mt-1.5 line-clamp-2 leading-snug">
                      {ho.headline}
                    </div>

                    <div className="mt-2 flex items-center justify-between text-[10px] text-[#8c8276]">
                      <span>By: {ho.generated_by}</span>
                      <span className="text-[#d93829] font-medium flex items-center gap-0.5">
                        View Dossier <ArrowRight className="w-2.5 h-2.5" />
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Handover Markdown Dossier Viewer */}
        <div className="lg:col-span-8">
          {selectedHandover ? (
            <div className="rounded-2xl border border-[#eae4d9] bg-white shadow-xs overflow-hidden">
              {/* Dossier Header */}
              <div className="p-5 bg-[#faf7f2] border-b border-[#eae4d9] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono font-bold bg-[#191410] text-white px-2 py-0.5 rounded-full">
                      Dossier #{selectedHandover.id}
                    </span>
                    <span className="text-xs text-[#70685e]">
                      Period: {new Date(selectedHandover.period_start).toLocaleDateString('en-GB')} – {new Date(selectedHandover.period_end).toLocaleDateString('en-GB')}
                    </span>
                  </div>
                  <h3 className="text-sm font-bold text-[#191410] mt-1">
                    {selectedHandover.headline}
                  </h3>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handlePrintHandover}
                    className="px-3 py-1.5 text-xs font-semibold text-[#191410] bg-white border border-[#eae4d9] hover:bg-[#f0ebe1] rounded-xl transition-colors flex items-center gap-1.5 cursor-pointer shadow-2xs"
                  >
                    <Printer className="w-3.5 h-3.5 text-[#70685e]" />
                    Print / Export PDF
                  </button>
                </div>
              </div>

              {/* Dossier Body */}
              <div className="p-6 overflow-y-auto max-h-[650px] font-sans text-xs text-[#2b251f] space-y-4 whitespace-pre-wrap leading-relaxed select-text">
                {selectedHandover.rendered_text}
              </div>

              {/* Dossier Footer with Merkle Assurance */}
              <div className="px-6 py-3 bg-[#faf7f2] border-t border-[#eae4d9] flex items-center justify-between text-[11px] text-[#70685e]">
                <div className="flex items-center gap-1.5 text-[#1b7a37] font-medium">
                  <ShieldCheck className="w-4 h-4 text-[#1b7a37]" />
                  <span>Derived deterministically from Merkle audit ledger</span>
                </div>
                <div className="font-mono text-[10px]">
                  Generated by: {selectedHandover.generated_by}
                </div>
              </div>
            </div>
          ) : (
            <div className="h-64 rounded-2xl border border-dashed border-[#eae4d9] flex flex-col items-center justify-center text-center p-6 text-xs text-[#70685e]">
              <FileText className="w-8 h-8 text-[#b0a89d] mb-2" />
              <div>Select a shift handover dossier from the list to view full details.</div>
            </div>
          )}
        </div>
      </div>

      {/* GENERATE HANDOVER MODAL */}
      {isGenerateOpen && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-white rounded-2xl border border-[#eae4d9] shadow-2xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-[#eae4d9] pb-3">
              <h3 className="text-sm font-bold text-[#191410] flex items-center gap-2">
                <ClipboardList className="w-4 h-4 text-[#d93829]" />
                Generate Shift Handover Briefing
              </h3>
              <button 
                onClick={() => setIsGenerateOpen(false)}
                className="text-[#8c8276] hover:text-[#191410] cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-[#191410] mb-1">
                  Shift Window Duration
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {[8, 12, 24, 48].map(hrs => (
                    <button
                      key={hrs}
                      type="button"
                      onClick={() => setPeriodHours(hrs)}
                      className={`py-2 text-center rounded-xl font-bold font-mono border transition-all cursor-pointer ${
                        periodHours === hrs 
                          ? 'border-[#d93829] bg-[#fdeee9] text-[#d93829]' 
                          : 'border-[#eae4d9] bg-white text-[#70685e] hover:bg-[#faf7f2]'
                      }`}
                    >
                      {hrs} Hours
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block font-semibold text-[#191410] mb-1">
                  Turnover Notes & Handover Directives (Optional)
                </label>
                <textarea
                  rows={3}
                  value={turnoverNotes}
                  onChange={(e) => setTurnoverNotes(e.target.value)}
                  placeholder="e.g. Ballistics pending from State FSL; morning team to follow up on CDR subscriber records for Suspect B..."
                  className="w-full p-2.5 bg-[#faf7f2] border border-[#eae4d9] rounded-xl text-xs focus:outline-none focus:border-[#d93829]"
                />
              </div>

              <div className="p-3 bg-[#ebf4fd] border border-[#bedcfc] rounded-xl text-[11px] text-[#1b64b8] space-y-1">
                <div className="font-bold">Automated Synthesis:</div>
                <div>
                  The briefing will synthesize all exhibit uploads, classification changes, overrides, pending tasks, and statutory countdowns without subjective editorializing.
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#eae4d9]">
              <button
                type="button"
                onClick={() => setIsGenerateOpen(false)}
                className="px-3 py-1.5 text-xs text-[#70685e] hover:text-[#191410] cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={generating}
                onClick={handleGenerateHandover}
                className="px-4 py-2 text-xs font-bold text-white bg-[#d93829] hover:bg-[#b82a1d] rounded-xl transition-all cursor-pointer shadow-xs disabled:opacity-50"
              >
                {generating ? 'Compiling Dossier...' : 'Synthesize Handover'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* EXTEND DEADLINE MODAL */}
      {isExtendOpen && selectedDeadline && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-white rounded-2xl border border-[#eae4d9] shadow-2xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-[#eae4d9] pb-3">
              <h3 className="text-sm font-bold text-[#191410] flex items-center gap-2">
                <Scale className="w-4 h-4 text-[#1b64b8]" />
                Record Statutory Deadline Extension
              </h3>
              <button 
                onClick={() => setIsExtendOpen(false)}
                className="text-[#8c8276] hover:text-[#191410] cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-[10px] text-[#70685e]">Deadline Title</span>
                <div className="font-bold text-[#191410]">{selectedDeadline.title}</div>
              </div>

              <div>
                <label className="block font-semibold text-[#191410] mb-1">
                  Additional Days Extension
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[7, 14, 30].map(d => (
                    <button
                      key={d}
                      type="button"
                      onClick={() => setExtensionDays(d)}
                      className={`py-1.5 text-center rounded-xl font-bold font-mono border transition-all cursor-pointer ${
                        extensionDays === d 
                          ? 'border-[#1b64b8] bg-[#ebf4fd] text-[#1b64b8]' 
                          : 'border-[#eae4d9] bg-white text-[#70685e] hover:bg-[#faf7f2]'
                      }`}
                    >
                      +{d} Days
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block font-semibold text-[#191410] mb-1">
                  Court / Judicial Order & Reason (Audit Log)
                </label>
                <textarea
                  rows={2}
                  value={extensionReason}
                  onChange={(e) => setExtensionReason(e.target.value)}
                  placeholder="e.g., Sessions Court Order No. Cr-294/2026 granting 14 days under BNSS 187(3)..."
                  className="w-full p-2.5 bg-[#faf7f2] border border-[#eae4d9] rounded-xl text-xs focus:outline-none focus:border-[#1b64b8]"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#eae4d9]">
              <button
                type="button"
                onClick={() => setIsExtendOpen(false)}
                className="px-3 py-1.5 text-xs text-[#70685e] hover:text-[#191410] cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={extending || !extensionReason.trim()}
                onClick={handleExtendDeadline}
                className="px-4 py-2 text-xs font-bold text-white bg-[#1b64b8] hover:bg-[#155094] rounded-xl transition-all cursor-pointer shadow-xs disabled:opacity-50"
              >
                {extending ? 'Recording...' : 'Commit Extension'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
export default Handover;

