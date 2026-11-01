import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  Clock, AlertTriangle, FileText, ArrowRight, Calendar, 
  ShieldAlert, Sparkles, CheckCircle2, User, RefreshCw, 
  Timer, ArrowUpRight, Scale, Users, Plus, Check, ChevronDown, 
  ChevronUp, BellRing, PhoneCall, Building2, UserPlus, FileCheck, 
  Info, ExternalLink, X, ShieldCheck, AlertCircle
} from 'lucide-react';
import { prioritiesService } from '../../services/prioritiesService';
import { 
  PrioritiesResponse, 
  ReportRequest, 
  PersonRegister, 
  PriorityActionItem, 
  NeedsYourReviewItem 
} from '../../types';
import { cn } from '../../utils';

export function TodaysPriorities() {
  const { caseId } = useParams<{ caseId: string }>();
  const [priorities, setPriorities] = useState<PrioritiesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showShiftDetails, setShowShiftDetails] = useState(false);
  const [showSnapshot, setShowSnapshot] = useState(false);
  const [reviewFilter, setReviewFilter] = useState<'all' | 'contradiction' | 'data_quality' | 'alert'>('all');

  // Modal states
  const [showReportModal, setShowReportModal] = useState(false);
  const [newReportType, setNewReportType] = useState('DNA Profiling & Semen Serology');
  const [newReportFrom, setNewReportFrom] = useState('Forensic Science Laboratory (FSL)');
  const [newReportDays, setNewReportDays] = useState('14');
  const [newReportUrgency, setNewReportUrgency] = useState<'high' | 'critical' | 'medium'>('high');

  const [showPersonModal, setShowPersonModal] = useState(false);
  const [newPersonName, setNewPersonName] = useState('');
  const [newPersonRole, setNewPersonRole] = useState('Eye Witness');
  const [newPersonContact, setNewPersonContact] = useState('');
  const [newPersonImportant, setNewPersonImportant] = useState(true);

  // Missing dates form
  const [arrestDateInput, setArrestDateInput] = useState('');
  const [remandDateInput, setRemandDateInput] = useState('');
  const [limitDaysInput, setLimitDaysInput] = useState('90');
  const [savingDates, setSavingDates] = useState(false);

  // Debounced live event listener
  const debounceTimerRef = useRef<any>(null);

  const fetchPriorities = useCallback(async (skipCache = false) => {
    if (!caseId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await prioritiesService.getCasePriorities(caseId, skipCache);
      setPriorities(data);
    } catch (err: any) {
      console.error('Failed to fetch case priorities:', err);
      setError(err?.message || 'Failed to load case operational priorities.');
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    fetchPriorities(false);
  }, [fetchPriorities]);

  // Handle live collaboration and streaming events with debouncing
  useEffect(() => {
    const handleLiveEvent = () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      debounceTimerRef.current = setTimeout(() => {
        fetchPriorities(true);
      }, 1000);
    };

    window.addEventListener('evidentia:live-event', handleLiveEvent);
    return () => {
      window.removeEventListener('evidentia:live-event', handleLiveEvent);
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [fetchPriorities]);

  // Handle saving missing dates
  const handleSaveDates = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId || !arrestDateInput) return;
    try {
      setSavingDates(true);
      await prioritiesService.updateCaseProcedure(caseId, {
        arrest_date: arrestDateInput ? new Date(arrestDateInput).toISOString() : null,
        remand_date: remandDateInput ? new Date(remandDateInput).toISOString() : null,
        statutory_time_limit_days: parseInt(limitDaysInput, 10) || 90
      });
      await fetchPriorities(true);
    } catch (err: any) {
      alert('Failed to update case dates: ' + (err?.message || 'Unknown error'));
    } finally {
      setSavingDates(false);
    }
  };

  // Handle creating a new report request
  const handleCreateReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId || !newReportType.trim() || !newReportFrom.trim()) return;
    try {
      const days = parseInt(newReportDays, 10) || 14;
      const expDate = new Date(Date.now() + days * 86400000).toISOString();
      await prioritiesService.createReportRequest(caseId, {
        report_type: newReportType.trim(),
        requested_from: newReportFrom.trim(),
        expected_date: expDate,
        urgency: newReportUrgency,
        status: 'requested'
      });
      setShowReportModal(false);
      setNewPersonName('');
      await fetchPriorities(true);
    } catch (err: any) {
      alert('Failed to create report request: ' + (err?.message || 'Unknown error'));
    }
  };

  // Handle adding a person
  const handleCreatePerson = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId || !newPersonName.trim()) return;
    try {
      await prioritiesService.createPerson(caseId, {
        name: newPersonName.trim(),
        role: newPersonRole.trim(),
        contact_info: newPersonContact.trim() || undefined,
        is_important: newPersonImportant
      });
      setShowPersonModal(false);
      setNewPersonName('');
      setNewPersonContact('');
      await fetchPriorities(true);
    } catch (err: any) {
      alert('Failed to add person to register: ' + (err?.message || 'Unknown error'));
    }
  };

  // 1-Click add AI suggested person
  const handleAddAiSuggestedPerson = async (suggested: { name: string; role: string; linked_entity_id?: number | null }) => {
    if (!caseId) return;
    try {
      await prioritiesService.createPerson(caseId, {
        name: suggested.name,
        role: suggested.role,
        linked_entity_id: suggested.linked_entity_id || undefined,
        is_important: true
      });
      await fetchPriorities(true);
    } catch (err: any) {
      alert('Failed to add suggested witness: ' + (err?.message || 'Unknown error'));
    }
  };

  // Helper for deadline band color
  const getBandStyles = (band?: string) => {
    switch (band) {
      case 'overdue':
        return {
          cardBg: 'bg-rose-50/90 border-rose-400',
          badgeBg: 'bg-rose-600 text-white',
          textAccent: 'text-rose-700',
          label: 'OVERDUE'
        };
      case 'critical':
        return {
          cardBg: 'bg-rose-50/70 border-rose-300',
          badgeBg: 'bg-rose-100 text-rose-800 border border-rose-300',
          textAccent: 'text-rose-700',
          label: 'CRITICAL (< 3 DAYS)'
        };
      case 'urgent':
        return {
          cardBg: 'bg-amber-50/70 border-amber-300',
          badgeBg: 'bg-amber-100 text-amber-900 border border-amber-300',
          textAccent: 'text-amber-800',
          label: 'URGENT (3-7 DAYS)'
        };
      case 'watch':
        return {
          cardBg: 'bg-yellow-50/60 border-yellow-200',
          badgeBg: 'bg-yellow-100 text-yellow-800 border border-yellow-300',
          textAccent: 'text-yellow-800',
          label: 'WATCH (7-14 DAYS)'
        };
      case 'calm':
      default:
        return {
          cardBg: 'bg-emerald-50/50 border-emerald-200',
          badgeBg: 'bg-emerald-100 text-emerald-800 border border-emerald-300',
          textAccent: 'text-emerald-800',
          label: 'ON SCHEDULE (> 14 DAYS)'
        };
    }
  };

  const clock = priorities?.statutory_clock;
  const away = priorities?.since_you_were_away;
  const reports = priorities?.pending_reports;
  const witnesses = priorities?.witnesses_and_statements;
  const review = priorities?.needs_your_review;
  const snapshot = priorities?.case_snapshot;

  const filteredReviewItems = review?.items.filter(item => {
    if (reviewFilter === 'all') return true;
    if (reviewFilter === 'contradiction') return item.type === 'contradiction';
    if (reviewFilter === 'data_quality') return item.type === 'data_quality' || item.type === 'low_confidence_ocr' || item.type === 'unverified_citation';
    if (reviewFilter === 'alert') return item.type === 'alert' || item.type === 'signoff';
    return true;
  }) || [];

  return (
    <div className="space-y-6 pb-16">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#eae4d9]">
        <div>
          <div className="text-[11px] font-mono tracking-widest text-[#d93829] uppercase font-bold mb-1 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-[#d93829]" />
            <span>Operational Priorities & Statutory Docket</span>
            {priorities?.fir_number && (
              <span className="text-[#8c8276] font-normal">• {priorities.fir_number}</span>
            )}
          </div>
          <h1 className="text-2xl lg:text-3xl font-serif font-bold text-[#191410]">
            Today's Priorities
          </h1>
          <p className="text-xs text-[#6e665d] mt-1 max-w-2xl leading-relaxed">
            Statutory default-bail countdowns, awaiting forensic and telecommunication reports, witness examination registry, and court-integrity review items.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => fetchPriorities(true)}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#faf7f2] hover:bg-[#eae4d9] text-[#191410] rounded-full text-xs font-bold transition-all border border-[#d8d0c5] cursor-pointer shadow-xs disabled:opacity-50"
            title="Refresh priorities from database"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin text-[#d93829]")} />
            <span>Refresh</span>
            {priorities?.cached && (
              <span className="text-[10px] text-[#8c8276] font-mono font-normal">(cached 30s)</span>
            )}
          </button>
          <Link
            to={`/cases/${caseId}/case-file`}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-[#faf7f2] text-[#191410] rounded-full text-xs font-bold transition-all border border-[#d8d0c5] cursor-pointer shadow-xs"
          >
            <span>Case File & FIR</span>
          </Link>
          <Link
            to={`/cases/${caseId}/chargesheet`}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-[#d93829] hover:bg-[#bf2b1d] text-white rounded-full text-xs font-bold transition-all shadow-xs cursor-pointer"
          >
            <span>Chargesheet Assistant</span>
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </div>

      {/* Top Strip: Since You Were Away Shift Briefing */}
      {away && (
        <div className="p-4 rounded-3xl bg-gradient-to-r from-amber-50/80 via-white to-amber-50/60 border border-amber-200 shadow-xs transition-all">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-2xl bg-amber-100 border border-amber-300 flex items-center justify-center text-amber-900 shrink-0 mt-0.5">
                <Sparkles className="w-4 h-4 text-amber-800" />
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-serif font-bold text-[#191410]">
                    Since You Were Away ({away.hours_away.toFixed(1)} hrs shift gap)
                  </span>
                  <span className="px-2 py-0.5 rounded-full text-[9px] font-mono font-bold bg-amber-100 text-amber-900 border border-amber-200">
                    Shift Briefing
                  </span>
                </div>
                <p className="text-xs text-[#191410] font-medium mt-0.5 leading-snug">
                  {away.headline}
                </p>
                <div className="flex items-center gap-3 mt-1.5 text-[11px] font-mono text-[#6e665d] flex-wrap">
                  {away.new_evidence_count > 0 && (
                    <span className="flex items-center gap-1 font-semibold text-blue-800 bg-blue-50 px-2 py-0.5 rounded-md border border-blue-200">
                      +{away.new_evidence_count} Exhibits Uploaded
                    </span>
                  )}
                  {away.changed_hypotheses_count > 0 && (
                    <span className="flex items-center gap-1 font-semibold text-purple-800 bg-purple-50 px-2 py-0.5 rounded-md border border-purple-200">
                      +{away.changed_hypotheses_count} Hypothesis Shifts
                    </span>
                  )}
                  {away.unresolved_alerts_count > 0 && (
                    <span className="flex items-center gap-1 font-semibold text-rose-800 bg-rose-50 px-2 py-0.5 rounded-md border border-rose-200">
                      {away.unresolved_alerts_count} Unresolved Alerts
                    </span>
                  )}
                  {away.open_tasks_count > 0 && (
                    <span className="flex items-center gap-1 font-semibold text-stone-800 bg-stone-100 px-2 py-0.5 rounded-md border border-stone-200">
                      {away.open_tasks_count} Tasks Active
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
              {away.summary_points?.length > 0 && (
                <button
                  onClick={() => setShowShiftDetails(!showShiftDetails)}
                  className="flex items-center gap-1 text-xs font-mono text-[#6e665d] hover:text-[#191410] px-2.5 py-1 rounded-full bg-white border border-[#eae4d9] cursor-pointer"
                >
                  <span>{showShiftDetails ? 'Hide Details' : 'View Shift Points'}</span>
                  {showShiftDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>
              )}
              <Link
                to={`/cases/${caseId}/handover`}
                className="text-xs font-mono font-bold text-[#d93829] hover:underline flex items-center gap-1 px-3 py-1 bg-white rounded-full border border-rose-200 cursor-pointer shadow-2xs"
              >
                <span>Handover Dossier</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {showShiftDetails && away.summary_points?.length > 0 && (
            <div className="mt-3 pt-3 border-t border-amber-200/70 text-xs space-y-1.5 pl-12">
              {away.summary_points.map((pt, idx) => (
                <div key={idx} className="flex items-start gap-2 text-[#4a4238]">
                  <span className="text-[#d93829] font-bold">•</span>
                  <span>{pt}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Row 1: Statutory Deadlines with Countdowns */}
      <div className="space-y-2">
        {clock?.has_dates ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Chargesheet Filing Deadline Card */}
            {(() => {
              const styles = getBandStyles(clock.chargesheet_band);
              return (
                <div className={cn(
                  "p-5 rounded-3xl border shadow-xs transition-all relative overflow-hidden flex flex-col justify-between",
                  styles.cardBg
                )}>
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#d93829] flex items-center gap-1.5">
                        <Timer className="w-4 h-4 text-[#d93829]" />
                        <span>Statutory Chargesheet Filing Clock</span>
                      </span>
                      <span className={cn("px-2.5 py-0.5 rounded-full text-[9px] font-mono font-bold tracking-wide", styles.badgeBg)}>
                        {styles.label}
                      </span>
                    </div>

                    <div className="flex items-baseline gap-3 my-2">
                      <span className="text-4xl lg:text-5xl font-mono font-bold text-[#191410] tracking-tight">
                        {clock.chargesheet_days_left !== null && clock.chargesheet_days_left !== undefined
                          ? clock.chargesheet_days_left
                          : '—'}
                      </span>
                      <div className="flex flex-col">
                        <span className="text-xs font-serif font-bold text-[#191410]">Days Remaining</span>
                        <span className="text-[11px] font-mono text-[#6e665d]">
                          {clock.chargesheet_hours_left ? `(${clock.chargesheet_hours_left} hrs)` : ''} until statutory expiry
                        </span>
                      </div>
                    </div>

                    <div className="text-xs text-[#4a4238] mt-2 leading-relaxed bg-white/60 p-3 rounded-2xl border border-[#eae4d9]/70">
                      <p className="font-semibold text-[#191410] mb-0.5">
                        {clock.statutory_provision} ({clock.chargesheet_limit_days}-Day Rule)
                      </p>
                      <p className="text-[11px] text-[#6e665d]">
                        {clock.chargesheet_legal_note}
                      </p>
                      {clock.chargesheet_deadline && (
                        <div className="mt-2 text-[10px] font-mono text-[#8c8276] flex items-center gap-1">
                          <Calendar className="w-3 h-3 text-[#d93829]" />
                          <span>Filing Date: {new Date(clock.chargesheet_deadline).toLocaleString()}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 mt-4 pt-3 border-t border-[#eae4d9]">
                    <Link
                      to={`/cases/${caseId}/chargesheet`}
                      className="flex-1 text-center py-2 px-3 rounded-xl bg-[#d93829] hover:bg-[#bf2b1d] text-white text-xs font-bold transition-all shadow-xs"
                    >
                      Draft Section 173 Final Report
                    </Link>
                    <Link
                      to={`/cases/${caseId}/case-file`}
                      className="py-2 px-3 rounded-xl bg-white hover:bg-[#faf7f2] text-[#191410] border border-[#d8d0c5] text-xs font-bold transition-all shadow-2xs"
                    >
                      Record Extension
                    </Link>
                  </div>
                </div>
              );
            })()}

            {/* Remand Custody Expiry Card */}
            {(() => {
              const styles = getBandStyles(clock.remand_band);
              return (
                <div className={cn(
                  "p-5 rounded-3xl border shadow-xs transition-all relative overflow-hidden flex flex-col justify-between",
                  styles.cardBg
                )}>
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#d93829] flex items-center gap-1.5">
                        <Scale className="w-4 h-4 text-[#d93829]" />
                        <span>Magisterial Police Custody Remand</span>
                      </span>
                      <span className={cn("px-2.5 py-0.5 rounded-full text-[9px] font-mono font-bold tracking-wide", styles.badgeBg)}>
                        {styles.label}
                      </span>
                    </div>

                    <div className="flex items-baseline gap-3 my-2">
                      <span className="text-4xl lg:text-5xl font-mono font-bold text-[#191410] tracking-tight">
                        {clock.remand_days_left !== null && clock.remand_days_left !== undefined
                          ? clock.remand_days_left
                          : '—'}
                      </span>
                      <div className="flex flex-col">
                        <span className="text-xs font-serif font-bold text-[#191410]">Days in Custody Left</span>
                        <span className="text-[11px] font-mono text-[#6e665d]">
                          {clock.remand_hours_left ? `(${clock.remand_hours_left} hrs)` : ''} until remand review
                        </span>
                      </div>
                    </div>

                    <div className="text-xs text-[#4a4238] mt-2 leading-relaxed bg-white/60 p-3 rounded-2xl border border-[#eae4d9]/70">
                      <p className="font-semibold text-[#191410] mb-0.5">
                        Custody Expiry Warning
                      </p>
                      <p className="text-[11px] text-[#6e665d]">
                        {clock.remand_legal_note}
                      </p>
                      {clock.remand_deadline && (
                        <div className="mt-2 text-[10px] font-mono text-[#8c8276] flex items-center gap-1">
                          <Calendar className="w-3 h-3 text-[#d93829]" />
                          <span>Hearing Expiry: {new Date(clock.remand_deadline).toLocaleString()}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 mt-4 pt-3 border-t border-[#eae4d9]">
                    <Link
                      to={`/cases/${caseId}/case-file`}
                      className="flex-1 text-center py-2 px-3 rounded-xl bg-white hover:bg-[#faf7f2] text-[#191410] border border-[#d8d0c5] text-xs font-bold transition-all shadow-2xs"
                    >
                      Inspect Remand & Custody Diary
                    </Link>
                  </div>
                </div>
              );
            })()}
          </div>
        ) : (
          /* Inline Date Prompt Form if dates are missing */
          <div className="p-6 rounded-3xl bg-amber-50/70 border border-amber-300 shadow-xs">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-2xl bg-amber-100 border border-amber-300 flex items-center justify-center text-amber-900 shrink-0">
                <AlertCircle className="w-5 h-5 text-amber-800" />
              </div>
              <div className="flex-1">
                <h3 className="text-base font-serif font-bold text-[#191410]">
                  Initialize Statutory Filing & Custody Clock
                </h3>
                <p className="text-xs text-[#6e665d] mt-1 max-w-2xl leading-relaxed">
                  No arrest date or initial remand date has been recorded for this case docket. Enter the arrest date below to automatically initialize the statutory Section 167(2) CrPC / Section 187(3) BNSS default bail countdown.
                </p>

                <form onSubmit={handleSaveDates} className="mt-4 grid grid-cols-1 md:grid-cols-4 gap-3">
                  <div>
                    <label className="block text-[10px] font-mono uppercase tracking-wider text-[#6e665d] font-bold mb-1">
                      Accused Arrest Date & Time
                    </label>
                    <input
                      type="datetime-local"
                      required
                      value={arrestDateInput}
                      onChange={(e) => setArrestDateInput(e.target.value)}
                      className="w-full text-xs p-2 rounded-xl bg-white border border-[#eae4d9] text-[#191410] focus:outline-hidden focus:border-[#d93829]"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-mono uppercase tracking-wider text-[#6e665d] font-bold mb-1">
                      Initial Remand Order Date
                    </label>
                    <input
                      type="datetime-local"
                      value={remandDateInput}
                      onChange={(e) => setRemandDateInput(e.target.value)}
                      className="w-full text-xs p-2 rounded-xl bg-white border border-[#eae4d9] text-[#191410] focus:outline-hidden focus:border-[#d93829]"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-mono uppercase tracking-wider text-[#6e665d] font-bold mb-1">
                      Statutory Window
                    </label>
                    <select
                      value={limitDaysInput}
                      onChange={(e) => setLimitDaysInput(e.target.value)}
                      className="w-full text-xs p-2 rounded-xl bg-white border border-[#eae4d9] text-[#191410] focus:outline-hidden focus:border-[#d93829]"
                    >
                      <option value="90">90 Days (Homicide, Rape, Life Imprisonment)</option>
                      <option value="60">60 Days (Other Statutory Offences)</option>
                    </select>
                  </div>
                  <div className="flex items-end">
                    <button
                      type="submit"
                      disabled={savingDates || !arrestDateInput}
                      className="w-full py-2 px-4 rounded-xl bg-[#d93829] hover:bg-[#bf2b1d] text-white text-xs font-bold transition-all shadow-xs disabled:opacity-50 cursor-pointer"
                    >
                      {savingDates ? 'Saving...' : 'Start Statutory Clock'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        )}

        <div className="text-[11px] text-[#8c8276] font-mono italic px-2 flex items-center gap-1.5">
          <Info className="w-3.5 h-3.5 text-[#8c8276]" />
          <span>Statutory filing reminders under CrPC 167(2) / BNSS 187(3) are operational aids for investigative planning and do not constitute formal legal counsel.</span>
        </div>
      </div>

      {/* Row 2: Two Columns (Pending Reports & Witnesses/Statements Tracker) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Pending Laboratory & Telecom Reports */}
        <div className="p-5 rounded-3xl bg-white border border-[#eae4d9] shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9]">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-purple-700" />
              <h2 className="text-base font-serif font-bold text-[#191410]">
                Awaiting Laboratory & Technical Reports ({reports?.total_requested || 0})
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowReportModal(true)}
                className="flex items-center gap-1 text-[11px] font-mono font-bold text-[#d93829] hover:bg-rose-50 px-2.5 py-1 rounded-full border border-rose-200 transition-colors cursor-pointer"
              >
                <Plus className="w-3 h-3" />
                <span>Request Report</span>
              </button>
              <Link
                to={`/cases/${caseId}/evidence`}
                className="text-[11px] text-[#6e665d] hover:text-[#191410] font-mono flex items-center gap-0.5"
              >
                <span>Exhibits</span>
                <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
          </div>

          {/* Unrequested Protocol Exhibits Warning */}
          {reports?.unrequested_protocol_exhibits && reports.unrequested_protocol_exhibits.length > 0 && (
            <div className="p-3 rounded-2xl bg-rose-50/70 border border-rose-200 text-xs space-y-1.5">
              <div className="flex items-center gap-1.5 text-rose-900 font-bold text-[11px] font-mono uppercase">
                <AlertTriangle className="w-3.5 h-3.5 text-rose-700" />
                <span>Missing Statutory Protocol Requisitions</span>
              </div>
              {reports.unrequested_protocol_exhibits.map((item, idx) => (
                <div key={idx} className="flex items-center justify-between gap-2 text-[11px] text-rose-950">
                  <span>• {item.item}: {item.description}</span>
                  <button
                    onClick={() => {
                      setNewReportType(item.item);
                      setShowReportModal(true);
                    }}
                    className="text-[10px] font-mono font-bold text-rose-800 underline hover:text-rose-950 shrink-0 cursor-pointer"
                  >
                    Requisition Now
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Requested Reports List */}
          {(!reports?.items || reports.items.length === 0) ? (
            <div className="py-8 text-center text-xs font-mono text-[#8c8276] space-y-2">
              <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
              <p>No external forensic lab reports or telecom records currently awaited.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {reports.items.map((rep) => (
                <div 
                  key={rep.id}
                  className="p-3.5 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] hover:border-purple-300 transition-all flex items-start justify-between gap-3 text-xs"
                >
                  <div className="space-y-1 flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-serif font-bold text-[#191410] truncate">
                        {rep.report_type}
                      </span>
                      <span className={cn(
                        "px-2 py-0.5 rounded-full text-[9px] font-mono font-bold uppercase",
                        rep.status === 'received' ? "bg-emerald-100 text-emerald-800 border border-emerald-300" :
                        rep.is_overdue || rep.status === 'overdue' ? "bg-rose-100 text-rose-800 border border-rose-300" :
                        "bg-amber-100 text-amber-900 border border-amber-300"
                      )}>
                        {rep.status}
                      </span>
                      {rep.urgency === 'critical' && (
                        <span className="px-1.5 py-0.2 rounded-md text-[9px] font-mono bg-rose-200 text-rose-900 font-bold">
                          CRITICAL
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2 text-[11px] text-[#6e665d]">
                      <Building2 className="w-3 h-3 text-[#8c8276]" />
                      <span>{rep.requested_from}</span>
                    </div>

                    <div className="flex items-center gap-3 text-[10px] font-mono text-[#8c8276] pt-1">
                      <span>Waiting: {rep.days_waiting} days</span>
                      {rep.expected_date && (
                        <span>Expected: {new Date(rep.expected_date).toLocaleDateString()}</span>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-1 shrink-0">
                    <button
                      onClick={async () => {
                        const confirmPrompt = window.confirm(`Mark "${rep.report_type}" as received?`);
                        if (confirmPrompt) {
                          await prioritiesService.updateReportRequest(caseId!, rep.id, {
                            status: 'received',
                            received_date: new Date().toISOString()
                          });
                          await fetchPriorities(true);
                        }
                      }}
                      className="px-2.5 py-1 rounded-lg bg-white hover:bg-emerald-50 text-emerald-800 border border-[#eae4d9] text-[10px] font-mono font-bold transition-all shadow-2xs cursor-pointer flex items-center gap-1"
                      title="Mark report received"
                    >
                      <Check className="w-3 h-3 text-emerald-700" />
                      <span>Received</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Witnesses and Statements Tracker */}
        <div className="p-5 rounded-3xl bg-white border border-[#eae4d9] shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9]">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-blue-700" />
              <h2 className="text-base font-serif font-bold text-[#191410]">
                Witness & Statement Examination ({witnesses?.unexamined_count || 0} Pending)
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowPersonModal(true)}
                className="flex items-center gap-1 text-[11px] font-mono font-bold text-[#d93829] hover:bg-rose-50 px-2.5 py-1 rounded-full border border-rose-200 transition-colors cursor-pointer"
              >
                <UserPlus className="w-3 h-3" />
                <span>Add Person</span>
              </button>
              <Link
                to={`/cases/${caseId}/interviews`}
                className="text-[11px] text-[#6e665d] hover:text-[#191410] font-mono flex items-center gap-0.5"
              >
                <span>Interviews</span>
                <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
          </div>

          {/* AI-Suggested Witnesses from Evidence */}
          {witnesses?.ai_suggested_persons && witnesses.ai_suggested_persons.length > 0 && (
            <div className="p-3 rounded-2xl bg-blue-50/70 border border-blue-200 text-xs space-y-2">
              <div className="flex items-center justify-between text-blue-900 font-bold text-[11px] font-mono uppercase">
                <span className="flex items-center gap-1">
                  <Sparkles className="w-3.5 h-3.5 text-blue-700" />
                  <span>AI-Extracted Mentions Awaiting Registration</span>
                </span>
              </div>
              <div className="space-y-1.5">
                {witnesses.ai_suggested_persons.map((sug, idx) => (
                  <div key={idx} className="flex items-center justify-between gap-2 p-2 rounded-xl bg-white border border-blue-200 text-[11px]">
                    <div>
                      <div className="font-bold text-[#191410]">{sug.name} ({sug.role})</div>
                      <div className="text-[10px] text-[#6e665d]">{sug.reason} • Mentioned {sug.mention_count}x</div>
                    </div>
                    <button
                      onClick={() => handleAddAiSuggestedPerson(sug)}
                      className="px-2 py-1 rounded-lg bg-blue-700 hover:bg-blue-800 text-white font-mono font-bold text-[10px] shrink-0 cursor-pointer shadow-2xs"
                    >
                      + Add to Register
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Witnesses Register List */}
          {(!witnesses?.items || witnesses.items.length === 0) ? (
            <div className="py-8 text-center text-xs font-mono text-[#8c8276] space-y-2">
              <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
              <p>All recorded witnesses examined and statements logged.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {witnesses.items.map((person) => (
                <div 
                  key={person.id}
                  className="p-3.5 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] hover:border-blue-300 transition-all flex items-start justify-between gap-3 text-xs"
                >
                  <div className="space-y-1 flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-serif font-bold text-[#191410]">
                        {person.name}
                      </span>
                      <span className="px-2 py-0.5 rounded-full text-[9px] font-mono font-bold bg-blue-100 text-blue-900 border border-blue-200">
                        {person.role}
                      </span>
                      {person.is_important && (
                        <span className="px-1.5 py-0.2 rounded-md text-[9px] font-mono bg-amber-100 text-amber-900 border border-amber-300 font-bold">
                          KEY WITNESS
                        </span>
                      )}
                    </div>

                    <div className="text-[11px] text-[#6e665d] flex items-center gap-2">
                      <FileCheck className="w-3 h-3 text-[#8c8276]" />
                      <span>{person.statement_type || 'Section 161 CrPC (Police Examination)'}</span>
                    </div>

                    <div className="flex items-center gap-3 text-[10px] font-mono text-[#8c8276] pt-1">
                      <span className={cn(
                        "font-bold uppercase",
                        person.statement_status === 'recorded' ? "text-emerald-700" :
                        person.statement_status === 'refused' ? "text-rose-700" : "text-amber-800"
                      )}>
                        Status: {person.statement_status?.replace('_', ' ')}
                      </span>
                      {person.scheduled_date && (
                        <span>Scheduled: {new Date(person.scheduled_date).toLocaleDateString()}</span>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-1 shrink-0">
                    <Link
                      to={`/cases/${caseId}/interviews`}
                      className="px-2.5 py-1 rounded-lg bg-white hover:bg-blue-50 text-blue-800 border border-[#eae4d9] text-[10px] font-mono font-bold transition-all shadow-2xs cursor-pointer flex items-center gap-1"
                    >
                      <PhoneCall className="w-3 h-3 text-blue-700" />
                      <span>Record 161</span>
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Row 3: "Needs Your Review" & Active Alerts Combined List */}
      <div className="p-5 rounded-3xl bg-white border border-[#eae4d9] shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#eae4d9]">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-[#d93829]" />
            <h2 className="text-base font-serif font-bold text-[#191410]">
              Needs Your Review ({review?.total_items || 0})
            </h2>
            <span className="text-xs text-[#8c8276] font-mono">
              • Contradictions, Section 65B gaps, and unverified data
            </span>
          </div>

          <div className="flex items-center gap-1.5 flex-wrap">
            {(['all', 'contradiction', 'data_quality', 'alert'] as const).map(tabKey => (
              <button
                key={tabKey}
                onClick={() => setReviewFilter(tabKey)}
                className={cn(
                  "px-3 py-1 rounded-full text-xs font-mono font-bold capitalize transition-all cursor-pointer",
                  reviewFilter === tabKey
                    ? "bg-[#191410] text-white"
                    : "bg-[#faf7f2] text-[#6e665d] hover:bg-[#eae4d9]"
                )}
              >
                {tabKey === 'all' ? 'All Items' : tabKey.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>

        {filteredReviewItems.length === 0 ? (
          <div className="py-8 text-center text-xs font-mono text-[#8c8276] space-y-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
            <p>No critical evidentiary contradictions or data quality discrepancies pending review.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {filteredReviewItems.map(item => (
              <div 
                key={item.id}
                className="p-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] hover:border-amber-300 transition-all flex flex-col justify-between gap-3 text-xs"
              >
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-serif font-bold text-[#191410] text-sm">
                      {item.title}
                    </span>
                    <span className={cn(
                      "px-2 py-0.5 rounded-full text-[9px] font-mono font-bold uppercase",
                      item.severity === 'critical' ? "bg-rose-100 text-rose-800 border border-rose-300" :
                      item.severity === 'high' ? "bg-amber-100 text-amber-900 border border-amber-300" :
                      "bg-stone-200 text-stone-800"
                    )}>
                      Impact: {item.impact_score.toFixed(1)}
                    </span>
                  </div>
                  <p className="text-[11px] text-[#6e665d] leading-relaxed">
                    {item.reason}
                  </p>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-[#eae4d9]">
                  <span className="text-[10px] font-mono uppercase text-[#8c8276]">
                    Type: {item.type.replace('_', ' ')}
                  </span>
                  <Link
                    to={item.action_link}
                    className="flex items-center gap-1 px-3 py-1 bg-white hover:bg-[#eae4d9] text-[#d93829] rounded-lg font-mono font-bold text-[11px] border border-[#d8d0c5] transition-all shadow-2xs"
                  >
                    <span>{item.action_label}</span>
                    <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Bottom Collapsible: Case Dossier Snapshot */}
      <div className="p-4 rounded-3xl bg-white border border-[#eae4d9] shadow-xs">
        <button
          onClick={() => setShowSnapshot(!showSnapshot)}
          className="w-full flex items-center justify-between text-xs font-serif font-bold text-[#191410] cursor-pointer"
        >
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#d93829]" />
            <span>Case Dossier Forensic Snapshot</span>
            <span className="text-[11px] font-mono text-[#8c8276] font-normal">
              ({snapshot?.exhibits_count || 0} exhibits • {snapshot?.entities_count || 0} entities • {snapshot?.timeline_events_count || 0} events)
            </span>
          </div>
          {showSnapshot ? <ChevronUp className="w-4 h-4 text-[#6e665d]" /> : <ChevronDown className="w-4 h-4 text-[#6e665d]" />}
        </button>

        {showSnapshot && snapshot && (
          <div className="mt-4 pt-4 border-t border-[#eae4d9] grid grid-cols-2 md:grid-cols-4 gap-4">
            <Link to={`/cases/${caseId}/evidence`} className="p-3 rounded-2xl bg-[#faf7f2] hover:bg-[#eae4d9] transition-all">
              <div className="text-[10px] font-mono uppercase text-[#8c8276]">Master Exhibits</div>
              <div className="text-2xl font-mono font-bold text-[#191410] mt-1">{snapshot.exhibits_count}</div>
              <div className="text-[11px] text-[#6e665d] mt-0.5">Chain of custody verified</div>
            </Link>

            <Link to={`/cases/${caseId}/link-analysis`} className="p-3 rounded-2xl bg-[#faf7f2] hover:bg-[#eae4d9] transition-all">
              <div className="text-[10px] font-mono uppercase text-[#8c8276]">Link Analysis Entities</div>
              <div className="text-2xl font-mono font-bold text-[#191410] mt-1">{snapshot.entities_count}</div>
              <div className="text-[11px] text-[#6e665d] mt-0.5">Suspects, vehicles & places</div>
            </Link>

            <Link to={`/cases/${caseId}/map-timeline`} className="p-3 rounded-2xl bg-[#faf7f2] hover:bg-[#eae4d9] transition-all">
              <div className="text-[10px] font-mono uppercase text-[#8c8276]">Chronology Events</div>
              <div className="text-2xl font-mono font-bold text-[#191410] mt-1">{snapshot.timeline_events_count}</div>
              <div className="text-[11px] text-[#6e665d] mt-0.5">Spatio-temporal sequence</div>
            </Link>

            <Link to={`/cases/${caseId}/hypotheses`} className="p-3 rounded-2xl bg-[#faf7f2] hover:bg-[#eae4d9] transition-all">
              <div className="text-[10px] font-mono uppercase text-[#8c8276]">Leading Suspect Theory</div>
              <div className="text-2xl font-mono font-bold text-[#d93829] mt-1">
                {snapshot.top_hypothesis ? `${Math.round((snapshot.top_hypothesis.probability || 0) * 100)}%` : '—'}
              </div>
              <div className="text-[11px] text-[#6e665d] mt-0.5 truncate">
                {snapshot.top_hypothesis?.title || 'None analyzed yet'}
              </div>
            </Link>
          </div>
        )}
      </div>

      {/* Modal: Request Laboratory / Technical Report */}
      {showReportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="w-full max-w-lg bg-white rounded-3xl p-6 shadow-2xl border border-[#eae4d9] space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9]">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-purple-700" />
                <h3 className="text-lg font-serif font-bold text-[#191410]">
                  Requisition Laboratory / Technical Report
                </h3>
              </div>
              <button
                onClick={() => setShowReportModal(false)}
                className="p-1 rounded-full hover:bg-[#faf7f2] text-[#8c8276] hover:text-[#191410]"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateReport} className="space-y-3">
              <div>
                <label className="block text-[11px] font-mono uppercase font-bold text-[#6e665d] mb-1">
                  Report Type / Requisition Spec
                </label>
                <input
                  type="text"
                  required
                  value={newReportType}
                  onChange={(e) => setNewReportType(e.target.value)}
                  placeholder="e.g. DNA Profiling, Ballistic Comparison, CDR Dump, Post-Mortem"
                  className="w-full text-xs p-2.5 rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-[#191410]"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono uppercase font-bold text-[#6e665d] mb-1">
                  Requested Agency / Institution
                </label>
                <input
                  type="text"
                  required
                  value={newReportFrom}
                  onChange={(e) => setNewReportFrom(e.target.value)}
                  placeholder="e.g. FSL Kalina Mumbai, Airtel Nodal Officer, Civil Hospital"
                  className="w-full text-xs p-2.5 rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-[#191410]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-mono uppercase font-bold text-[#6e665d] mb-1">
                    Expected Within (Days)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="90"
                    value={newReportDays}
                    onChange={(e) => setNewReportDays(e.target.value)}
                    className="w-full text-xs p-2.5 rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-[#191410]"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-mono uppercase font-bold text-[#6e665d] mb-1">
                    Urgency Band
                  </label>
                  <select
                    value={newReportUrgency}
                    onChange={(e: any) => setNewReportUrgency(e.target.value)}
                    className="w-full text-xs p-2.5 rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-[#191410]"
                  >
                    <option value="high">High Priority</option>
                    <option value="critical">Critical (Trial Bottleneck)</option>
                    <option value="medium">Medium Priority</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-4 border-t border-[#eae4d9]">
                <button
                  type="button"
                  onClick={() => setShowReportModal(false)}
                  className="px-4 py-2 rounded-xl bg-white hover:bg-[#faf7f2] text-[#191410] border border-[#eae4d9] text-xs font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-[#d93829] hover:bg-[#bf2b1d] text-white text-xs font-bold shadow-xs cursor-pointer"
                >
                  Log Requisition
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Add Person to Register */}
      {showPersonModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="w-full max-w-lg bg-white rounded-3xl p-6 shadow-2xl border border-[#eae4d9] space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9]">
              <div className="flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-blue-700" />
                <h3 className="text-lg font-serif font-bold text-[#191410]">
                  Register Person for Examination
                </h3>
              </div>
              <button
                onClick={() => setShowPersonModal(false)}
                className="p-1 rounded-full hover:bg-[#faf7f2] text-[#8c8276] hover:text-[#191410]"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreatePerson} className="space-y-3">
              <div>
                <label className="block text-[11px] font-mono uppercase font-bold text-[#6e665d] mb-1">
                  Full Legal Name
                </label>
                <input
                  type="text"
                  required
                  value={newPersonName}
                  onChange={(e) => setNewPersonName(e.target.value)}
                  placeholder="e.g. Ramesh Kadam"
                  className="w-full text-xs p-2.5 rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-[#191410]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-mono uppercase font-bold text-[#6e665d] mb-1">
                    Role in Case
                  </label>
                  <select
                    value={newPersonRole}
                    onChange={(e) => setNewPersonRole(e.target.value)}
                    className="w-full text-xs p-2.5 rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-[#191410]"
                  >
                    <option value="Eye Witness">Eye Witness</option>
                    <option value="Panch Witness">Panch Witness (Seizure Memo)</option>
                    <option value="Approver / Accomplice">Approver / Accomplice</option>
                    <option value="Expert Witness">Forensic / Medical Expert</option>
                    <option value="Informant">Confidential Informant</option>
                    <option value="Suspect">Suspect / Person of Interest</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] font-mono uppercase font-bold text-[#6e665d] mb-1">
                    Contact / Address
                  </label>
                  <input
                    type="text"
                    value={newPersonContact}
                    onChange={(e) => setNewPersonContact(e.target.value)}
                    placeholder="Phone or police station"
                    className="w-full text-xs p-2.5 rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-[#191410]"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="personImportant"
                  checked={newPersonImportant}
                  onChange={(e) => setNewPersonImportant(e.target.checked)}
                  className="rounded text-[#d93829] focus:ring-[#d93829]"
                />
                <label htmlFor="personImportant" className="text-xs text-[#191410] font-medium cursor-pointer">
                  Mark as Key Witness (Crucial to trial prosecution)
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-4 border-t border-[#eae4d9]">
                <button
                  type="button"
                  onClick={() => setShowPersonModal(false)}
                  className="px-4 py-2 rounded-xl bg-white hover:bg-[#faf7f2] text-[#191410] border border-[#eae4d9] text-xs font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-[#d93829] hover:bg-[#bf2b1d] text-white text-xs font-bold shadow-xs cursor-pointer"
                >
                  Add to Register
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
