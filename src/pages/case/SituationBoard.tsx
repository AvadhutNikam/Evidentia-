// src/pages/case/SituationBoard.tsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  situationBoardService,
  jobService,
  SituationBoardData
} from '../../services';
import {
  ShieldAlert,
  AlertTriangle,
  Clock,
  Users,
  BrainCircuit,
  FileText,
  CheckCircle2,
  TrendingUp,
  Maximize2,
  Minimize2,
  Eye,
  EyeOff,
  RotateCcw,
  Sparkles,
  ArrowRight,
  ExternalLink,
  ChevronRight,
  Zap,
  Activity,
  Calendar,
  Lock,
  Layers,
  Check,
  AlertOctagon,
  Radio
} from 'lucide-react';
import { cn } from '../../utils';

export function SituationBoard() {
  const { caseId: paramCaseId } = useParams<{ caseId?: string }>();
  const cleanCaseId = paramCaseId ? String(paramCaseId).replace(/^C-/, '') : '1';

  const [data, setData] = useState<SituationBoardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [presentationMode, setPresentationMode] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date>(new Date());
  const [streamActive, setStreamActive] = useState(true);
  const [currentClock, setCurrentClock] = useState<string>('');

  // Live wall clock timer (HH:mm:ss UTC / Local)
  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      setCurrentClock(now.toLocaleTimeString('en-US', { hour12: false }));
    };
    updateClock();
    const timer = setInterval(updateClock, 1000);
    return () => clearInterval(timer);
  }, []);

  // Fetch situation board data
  const loadData = useCallback(async (isPresentation: boolean, showLoading = false) => {
    if (showLoading) setLoading(true);
    try {
      const res = await situationBoardService.getSituationBoard(cleanCaseId, isPresentation);
      setData(res);
      setLastRefreshedAt(new Date());
    } catch (err) {
      console.error('Failed to load situation board data:', err);
    } finally {
      if (showLoading) setLoading(false);
    }
  }, [cleanCaseId]);

  // Initial load and whenever presentation mode toggles
  useEffect(() => {
    loadData(presentationMode, true);
  }, [cleanCaseId, presentationMode, loadData]);

  // Live 1-second interval to tick countdown timers smoothly
  useEffect(() => {
    const interval = setInterval(() => {
      setData(prev => {
        if (!prev) return prev;
        const now = Date.now();
        const updatedDeadlines = prev.deadline_countdowns.map(d => {
          const dueTime = new Date(d.due_date).getTime();
          const totalSeconds = Math.floor((dueTime - now) / 1000);
          const isOverdue = totalSeconds < 0;
          const absSec = Math.abs(totalSeconds);
          const days = Math.floor(absSec / 86400);
          const hours = Math.floor((absSec % 86400) / 3600);
          const minutes = Math.floor((absSec % 3600) / 60);
          const seconds = absSec % 60;

          let urgency: 'overdue' | 'critical' | 'urgent' | 'normal' = 'normal';
          if (isOverdue) urgency = 'overdue';
          else if (days <= 3) urgency = 'critical';
          else if (days <= 14) urgency = 'urgent';

          return {
            ...d,
            total_seconds: totalSeconds,
            is_overdue: isOverdue,
            days_remaining: isOverdue ? -days : days,
            hours_remaining: hours,
            minutes_remaining: minutes,
            seconds_remaining: seconds,
            urgency,
            formatted_countdown: `${isOverdue ? '-' : ''}${days}d ${String(hours).padStart(2, '0')}h ${String(minutes).padStart(2, '0')}m ${String(seconds).padStart(2, '0')}s`,
          };
        });

        return {
          ...prev,
          deadline_countdowns: updatedDeadlines,
        };
      });
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Listen to SSE live events for zero-click automatic updates
  useEffect(() => {
    if (!cleanCaseId) return;

    const unsubscribe = jobService.subscribeCaseEvents(
      cleanCaseId,
      (event: any) => {
        setStreamActive(true);
        // Refresh situation board in background upon receiving any event
        loadData(presentationMode, false);
      }
    );

    // Periodic low-frequency background poll (every 25 seconds) as fallback
    const pollInterval = setInterval(() => {
      loadData(presentationMode, false);
    }, 25000);

    return () => {
      unsubscribe();
      clearInterval(pollInterval);
    };
  }, [cleanCaseId, presentationMode, loadData]);

  // Fullscreen toggle handler
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {});
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {});
    }
  };

  // Keyboard shortcuts: 'F' for fullscreen, 'P' for presentation mode
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key.toLowerCase() === 'f') {
        toggleFullscreen();
      } else if (e.key.toLowerCase() === 'p') {
        setPresentationMode(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  if (loading && !data) {
    return (
      <div className="min-h-screen bg-[#faf7f2] text-[#191410] flex flex-col items-center justify-center p-8">
        <div className="relative flex h-14 w-14 mb-4">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-14 w-14 bg-[#d93829] items-center justify-center">
            <Radio className="w-7 h-7 text-white animate-pulse" />
          </span>
        </div>
        <h2 className="text-xl font-mono font-bold tracking-widest text-[#191410] uppercase">
          Initializing Live Case Wall
        </h2>
        <p className="text-xs font-mono text-[#6e665d] mt-2">
          Syncing leading hypotheses, statutory countdowns & SSE telemetry...
        </p>
      </div>
    );
  }

  const caseInfo = data?.case_info;
  const hypotheses = data?.leading_hypotheses || [];
  const evidence = data?.newest_evidence || [];
  const alerts = data?.open_alerts || [];
  const deadlines = data?.deadline_countdowns || [];
  const onlineUsers = data?.who_is_online || [];
  const tasks = data?.tasks_due || [];
  const jobs = data?.jobs_running || [];

  const topHypothesis = hypotheses.length > 0 ? hypotheses[0] : null;
  const criticalDeadline = deadlines.length > 0 ? deadlines[0] : null;
  const criticalAlertsCount = alerts.filter(a => a.severity === 'critical').length;

  return (
    <div className="min-h-screen bg-[#faf7f2] text-[#191410] flex flex-col select-none antialiased">
      {/* 1. TOP SITUATION COMMAND BAR */}
      <header className="border-b border-[#eae4d9] bg-white/95 backdrop-blur-md px-6 py-3.5 sticky top-0 z-40 shadow-xs">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          {/* Case Identity & Live Telemetry Pill */}
          <div className="flex items-center gap-4 flex-wrap">
            <Link
              to={`/cases/${cleanCaseId}`}
              className="text-[#6e665d] hover:text-[#191410] transition flex items-center gap-1.5 text-xs font-mono uppercase tracking-wider"
              title="Return to standard case workspace"
            >
              <ArrowRight className="w-3.5 h-3.5 rotate-180" />
              <span>Workspace</span>
            </Link>

            <div className="h-4 w-px bg-stone-300 hidden sm:block" />

            <div className="flex items-center gap-2.5">
              <span className="px-2.5 py-0.5 rounded font-mono text-xs font-bold bg-red-50 text-red-800 border border-red-200 tracking-wide">
                {caseInfo?.fir_number || `CASE #${cleanCaseId}`}
              </span>
              <h1 className="text-lg lg:text-xl font-bold font-serif text-[#191410] tracking-tight truncate max-w-xl">
                {caseInfo?.title || 'Forensic Investigation'}
              </h1>
            </div>

            <div className="flex items-center gap-2">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
              </span>
              <span className="text-[11px] font-mono uppercase tracking-widest text-emerald-700 font-bold">
                Live SSE Telemetry
              </span>
            </div>
          </div>

          {/* Quick Controls: Clock, Presentation Mode, Fullscreen */}
          <div className="flex items-center gap-3">
            {/* Live Clock */}
            <div className="px-3 py-1 bg-[#faf7f2] border border-[#eae4d9] rounded-lg text-right">
              <span className="text-xs font-mono font-bold text-amber-800 tracking-wider">
                {currentClock}
              </span>
              <span className="text-[9px] font-mono text-[#6e665d] uppercase ml-1.5">UTC+5:30</span>
            </div>

            {/* Presentation Mode Toggle */}
            <button
              onClick={() => setPresentationMode(!presentationMode)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-bold font-mono uppercase tracking-wider transition-all flex items-center gap-1.5 border cursor-pointer",
                presentationMode
                  ? "bg-amber-100 text-amber-900 border-amber-300 shadow-xs"
                  : "bg-white hover:bg-[#faf7f2] text-[#191410] border-[#eae4d9]"
              )}
              title="Toggle Briefing Mode: Redacts prior criminal convictions and suspect profiling (Key: P)"
            >
              {presentationMode ? (
                <>
                  <Lock className="w-3.5 h-3.5 text-amber-700" />
                  <span>Briefing Mode: Active</span>
                </>
              ) : (
                <>
                  <Eye className="w-3.5 h-3.5 text-[#6e665d]" />
                  <span>Briefing Mode: Off</span>
                </>
              )}
            </button>

            {/* Fullscreen Button */}
            <button
              onClick={toggleFullscreen}
              className="p-1.5 rounded-lg bg-white hover:bg-[#faf7f2] text-[#191410] border border-[#eae4d9] transition cursor-pointer"
              title="Toggle Fullscreen display (Key: F)"
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>

            {/* Manual Sync Trigger */}
            <button
              onClick={() => loadData(presentationMode, false)}
              className="p-1.5 rounded-lg bg-white hover:bg-[#faf7f2] text-[#191410] border border-[#eae4d9] transition cursor-pointer"
              title="Refresh Situation Data"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Presentation Mode Warning Banner */}
        {presentationMode && (
          <div className="mt-2.5 py-1 px-3 bg-amber-50 border border-amber-200 rounded text-center text-xs font-mono text-amber-900 flex items-center justify-center gap-2">
            <Lock className="w-3.5 h-3.5 text-amber-700 shrink-0" />
            <span>
              PRESENTATION / BRIEFING MODE ACTIVE • Prior criminal records & suspect profiling factors automatically redacted (Sec 54 Indian Evidence Act / Sec 52 BSA compliant)
            </span>
            {data?.redacted_items_count ? (
              <span className="px-1.5 py-0.2 rounded bg-amber-100 font-bold border border-amber-300">
                {data.redacted_items_count} items restricted
              </span>
            ) : null}
          </div>
        )}
      </header>

      {/* 2. GLANCEABLE TICKER / KPI SUMMARY ROW */}
      <section className="grid grid-cols-2 lg:grid-cols-5 gap-3 p-4 bg-white border-b border-[#eae4d9] text-xs">
        {/* Leading Suspect Theory */}
        <div className="p-3 bg-[#faf7f2] rounded-xl border border-[#eae4d9]">
          <div className="text-[10px] uppercase font-mono tracking-wider text-[#6e665d] mb-1 flex items-center justify-between">
            <span>Primary Suspect Theory</span>
            <TrendingUp className="w-3 h-3 text-emerald-600" />
          </div>
          <div className="text-xl font-bold font-serif text-[#191410] truncate">
            {topHypothesis?.title || 'No Hypotheses'}
          </div>
          <div className="text-[11px] font-mono text-emerald-700 font-bold mt-0.5">
            {topHypothesis ? `${topHypothesis.score}% Case Strength (Prime Suspect)` : 'Awaiting Data'}
          </div>
        </div>

        {/* Next Statutory Deadline */}
        <div className={cn(
          "p-3 rounded-xl border transition-all",
          criticalDeadline?.is_overdue
            ? "bg-red-50 border-red-300"
            : criticalDeadline?.urgency === 'critical'
            ? "bg-rose-50 border-rose-300"
            : "bg-[#faf7f2] border-[#eae4d9]"
        )}>
          <div className="text-[10px] uppercase font-mono tracking-wider text-[#6e665d] mb-1 flex items-center justify-between">
            <span>Statutory Charge Sheet Due</span>
            <Clock className="w-3 h-3 text-amber-600" />
          </div>
          <div className={cn(
            "text-xl font-mono font-bold truncate",
            criticalDeadline?.is_overdue ? "text-red-700" : criticalDeadline?.urgency === 'critical' ? "text-rose-700" : "text-amber-800"
          )}>
            {criticalDeadline ? criticalDeadline.formatted_countdown : '00d 00h 00m'}
          </div>
          <div className="text-[11px] text-[#6e665d] truncate mt-0.5">
            {criticalDeadline?.title || 'BNSS Sec 187 Filing'}
          </div>
        </div>

        {/* Forensic & Custody Alerts */}
        <div className="p-3 bg-[#faf7f2] rounded-xl border border-[#eae4d9]">
          <div className="text-[10px] uppercase font-mono tracking-wider text-[#6e665d] mb-1 flex items-center justify-between">
            <span>Active Alerts</span>
            <ShieldAlert className="w-3 h-3 text-[#d93829]" />
          </div>
          <div className="text-xl font-mono font-bold text-[#191410] flex items-center gap-2">
            <span>{alerts.length}</span>
            {criticalAlertsCount > 0 && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 bg-red-100 text-red-800 border border-red-300 rounded font-bold uppercase animate-pulse">
                {criticalAlertsCount} Critical
              </span>
            )}
          </div>
          <div className="text-[11px] font-mono text-[#6e665d] mt-0.5">
            {alerts.length === 0 ? 'All parameters normal' : 'Requires investigation team review'}
          </div>
        </div>

        {/* Active Team in Docket */}
        <div className="p-3 bg-[#faf7f2] rounded-xl border border-[#eae4d9]">
          <div className="text-[10px] uppercase font-mono tracking-wider text-[#6e665d] mb-1 flex items-center justify-between">
            <span>Personnel Online</span>
            <Users className="w-3 h-3 text-blue-600" />
          </div>
          <div className="text-xl font-mono font-bold text-[#191410]">
            {onlineUsers.length} <span className="text-xs text-[#6e665d] font-normal">Active Members</span>
          </div>
          <div className="text-[11px] text-[#6e665d] truncate mt-0.5">
            {onlineUsers.map(u => u.user_name.split(' ')[0]).join(', ') || 'Investigator connected'}
          </div>
        </div>

        {/* Worker Processing Jobs */}
        <div className="p-3 bg-[#faf7f2] rounded-xl border border-[#eae4d9]">
          <div className="text-[10px] uppercase font-mono tracking-wider text-[#6e665d] mb-1 flex items-center justify-between">
            <span>Worker Pipeline</span>
            <BrainCircuit className="w-3 h-3 text-purple-600" />
          </div>
          <div className="text-xl font-mono font-bold text-[#191410] flex items-center gap-2">
            <span>{jobs.length}</span>
            {jobs.length > 0 ? (
              <span className="text-[10px] font-mono px-1.5 py-0.5 bg-purple-100 text-purple-800 border border-purple-300 rounded font-bold uppercase animate-pulse">
                Running
              </span>
            ) : (
              <span className="text-[10px] font-mono px-1.5 py-0.5 bg-stone-100 text-stone-600 rounded">
                Idle
              </span>
            )}
          </div>
          <div className="text-[11px] font-mono text-[#6e665d] mt-0.5 truncate">
            {jobs.length > 0 ? `${jobs[0].current_stage} (${jobs[0].progress_pct}%)` : 'Ready for evidence ingestion'}
          </div>
        </div>
      </section>

      {/* 3. MAIN SITUATION BOARD GRID (Designed for Glanceability & Zero Clicking) */}
      <main className="flex-1 p-4 lg:p-6 grid grid-cols-1 lg:grid-cols-12 gap-5 overflow-y-auto">
        {/* ====================================================================== */}
        {/* PANEL A: LEADING HYPOTHESES WITH CONFIDENCE RANGES (Lg: col-span-7)   */}
        {/* ====================================================================== */}
        <div className="lg:col-span-7 bg-white border border-[#eae4d9] rounded-2xl p-5 flex flex-col shadow-xs">
          <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9] mb-4">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-red-50 border border-red-200 rounded-lg text-[#d93829]">
                <TrendingUp className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold font-serif text-[#191410] tracking-wide">
                  Prime Suspects & Case Strength
                </h3>
                <p className="text-xs text-[#6e665d]">
                  Evidence-backed certainty scores derived from {evidence.length} verified exhibits
                </p>
              </div>
            </div>
            <Link
              to={`/cases/${cleanCaseId}/hypotheses`}
              className="text-xs font-mono text-[#6e665d] hover:text-[#191410] flex items-center gap-1 transition"
            >
              Theories & Proof <ExternalLink className="w-3 h-3" />
            </Link>
          </div>

          <div className="space-y-4 flex-1">
            {hypotheses.length === 0 ? (
              <div className="h-48 flex flex-col items-center justify-center text-[#6e665d] font-mono text-xs">
                No active suspect theories registered for this case.
              </div>
            ) : (
              hypotheses.map((h, idx) => {
                const isPrime = idx === 0;
                return (
                  <div
                    key={h.id}
                    className={cn(
                      "p-4 rounded-xl border transition-all",
                      isPrime
                        ? "bg-emerald-50/40 border-emerald-300 shadow-xs"
                        : "bg-[#faf7f2] border-[#eae4d9] hover:border-stone-300"
                    )}
                  >
                    <div className="flex items-start justify-between gap-4 mb-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={cn(
                            "font-mono text-xs font-bold px-2 py-0.5 rounded",
                            isPrime ? "bg-emerald-600 text-white font-extrabold" : "bg-stone-200 text-stone-800"
                          )}>
                            {h.code || `H${idx + 1}`}
                          </span>
                          <h4 className="text-base font-bold font-serif text-[#191410] truncate">
                            {h.title}
                          </h4>
                          {isPrime && (
                            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-300 uppercase tracking-wider">
                              Prime Suspect
                            </span>
                          )}
                          {h.is_unknown && (
                            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300 uppercase tracking-wider">
                              Unidentified External Suspect
                            </span>
                          )}
                        </div>

                        {h.description && (
                          <p className="text-xs text-[#6e665d] line-clamp-1">
                            {h.description}
                          </p>
                        )}
                      </div>

                      {/* Large Posterior Percentage Display */}
                      <div className="text-right shrink-0">
                        <div className={cn(
                          "text-3xl lg:text-4xl font-mono font-extrabold tracking-tight",
                          isPrime ? "text-emerald-700" : h.score >= 35 ? "text-amber-700" : "text-[#6e665d]"
                        )}>
                          {h.score}%
                        </div>
                        <div className="text-[10px] font-mono text-[#6e665d] uppercase tracking-wider">
                          Case Strength
                        </div>
                      </div>
                    </div>

                    {/* Visual Confidence Range Bar [range_min to range_max] */}
                    <div className="mt-3 pt-3 border-t border-[#eae4d9]">
                      <div className="flex items-center justify-between text-[11px] font-mono text-[#6e665d] mb-1.5">
                        <span className="flex items-center gap-1.5">
                          <span>Case Certainty Bounds:</span>
                          <strong className="text-[#191410]">
                            [{h.range_min}% — {h.range_max}%]
                          </strong>
                        </span>
                        <span>
                          Corroborating Proof: <strong className="text-[#191410]">{h.evidence_score}%</strong>
                          {h.disconfirmation_penalty > 0 && (
                            <span className="text-rose-600 ml-2 font-semibold">
                              (-{h.disconfirmation_penalty} alibi conflict)
                            </span>
                          )}
                        </span>
                      </div>

                      {/* Range slider visual */}
                      <div className="relative w-full bg-stone-200 h-2.5 rounded-full overflow-hidden">
                        {/* Background track */}
                        <div
                          className="absolute top-0 bottom-0 bg-stone-300 rounded-full"
                          style={{
                            left: `${Math.max(0, h.range_min)}%`,
                            width: `${Math.min(100, h.range_max - h.range_min)}%`,
                          }}
                        />
                        {/* Core point indicator */}
                        <div
                          className={cn(
                            "absolute top-0 bottom-0 rounded-full",
                            isPrime ? "bg-emerald-600 shadow-xs" : "bg-amber-500"
                          )}
                          style={{
                            left: `${Math.max(0, h.score - 1)}%`,
                            width: '2%',
                          }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* ====================================================================== */}
        {/* PANEL B: STATUTORY DEADLINES & URGENT TIMERS (Lg: col-span-5)          */}
        {/* ====================================================================== */}
        <div className="lg:col-span-5 bg-white border border-[#eae4d9] rounded-2xl p-5 flex flex-col shadow-xs">
          <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9] mb-4">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-amber-50 border border-amber-200 rounded-lg text-amber-700">
                <Clock className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold font-serif text-[#191410] tracking-wide">
                  Statutory Deadlines & Remand Countdowns
                </h3>
                <p className="text-xs text-[#6e665d]">
                  Mandatory BNSS / CrPC procedural filing time limits
                </p>
              </div>
            </div>
            <span className="text-xs font-mono font-bold text-amber-800 bg-amber-100 border border-amber-300 px-2 py-0.5 rounded">
              Active Clock
            </span>
          </div>

          <div className="space-y-3 flex-1">
            {deadlines.length === 0 ? (
              <div className="h-48 flex flex-col items-center justify-center text-[#6e665d] font-mono text-xs">
                No active statutory deadlines configured.
              </div>
            ) : (
              deadlines.slice(0, 4).map(d => {
                const isOverdue = d.is_overdue;
                const isCritical = d.urgency === 'critical';
                return (
                  <div
                    key={d.id}
                    className={cn(
                      "p-3.5 rounded-xl border transition-all",
                      isOverdue
                        ? "bg-red-50 border-red-300 shadow-xs"
                        : isCritical
                        ? "bg-rose-50 border-rose-300 shadow-xs"
                        : "bg-[#faf7f2] border-[#eae4d9]"
                    )}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <h4 className="text-sm font-bold text-[#191410] truncate">
                        {d.title}
                      </h4>
                      <span className={cn(
                        "text-[10px] font-mono font-extrabold px-2 py-0.5 rounded uppercase tracking-wider",
                        isOverdue ? "bg-red-200 text-red-900 border border-red-300 animate-pulse" :
                        isCritical ? "bg-rose-200 text-rose-900 border border-rose-300" :
                        "bg-stone-200 text-stone-700"
                      )}>
                        {d.urgency}
                      </span>
                    </div>

                    <div className="flex items-baseline justify-between">
                      {/* Large Countdown Type */}
                      <div className={cn(
                        "text-2xl font-mono font-extrabold tracking-tight",
                        isOverdue ? "text-red-700" : isCritical ? "text-rose-700" : "text-amber-800"
                      )}>
                        {d.formatted_countdown}
                      </div>

                      <div className="text-[11px] font-mono text-[#6e665d]">
                        Target: {new Date(d.due_date).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* ====================================================================== */}
        {/* PANEL C: NEWEST EVIDENCE EXHIBITS (Lg: col-span-4)                     */}
        {/* ====================================================================== */}
        <div className="lg:col-span-4 bg-white border border-[#eae4d9] rounded-2xl p-5 flex flex-col shadow-xs">
          <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9] mb-4">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-blue-50 border border-blue-200 rounded-lg text-blue-700">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold font-serif text-[#191410] tracking-wide">
                  Newest Evidence Exhibits
                </h3>
                <p className="text-xs text-[#6e665d]">Integrity verification & Sec 65B</p>
              </div>
            </div>
            <Link
              to={`/cases/${cleanCaseId}/evidence`}
              className="text-xs font-mono text-[#6e665d] hover:text-[#191410] flex items-center gap-1 transition"
            >
              All ({evidence.length}) <ExternalLink className="w-3 h-3" />
            </Link>
          </div>

          <div className="space-y-2.5 flex-1">
            {evidence.length === 0 ? (
              <div className="h-40 flex items-center justify-center text-[#6e665d] font-mono text-xs">
                No evidentiary exhibits uploaded yet.
              </div>
            ) : (
              evidence.slice(0, 5).map(ev => (
                <div
                  key={ev.id}
                  className="p-3 bg-[#faf7f2] border border-[#eae4d9] hover:bg-white rounded-xl flex items-center justify-between gap-3 transition shadow-xs"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center shrink-0 text-blue-700">
                      <FileText className="w-4 h-4 text-blue-600" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs font-bold text-[#191410] truncate" title={ev.file_name}>
                        {ev.file_name}
                      </div>
                      <div className="text-[10px] font-mono text-[#6e665d] mt-0.5">
                        {ev.evidence_type} • {new Date(ev.upload_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    {ev.hash_verified ? (
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center gap-1" title="SHA-256 Hash Verified against tamper log">
                        <Check className="w-2.5 h-2.5 text-emerald-600" />
                        <span>HASH</span>
                      </span>
                    ) : (
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-stone-100 text-stone-600 border border-stone-200">
                        UNVERIFIED
                      </span>
                    )}

                    {ev.sec_65b_present && (
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-blue-50 text-blue-800 border border-blue-200" title="Section 65B Indian Evidence Act Certificate on file">
                        65B
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* ====================================================================== */}
        {/* PANEL D: OPEN ALERTS & TAMPER WARNINGS (Lg: col-span-4)                */}
        {/* ====================================================================== */}
        <div className="lg:col-span-4 bg-white border border-[#eae4d9] rounded-2xl p-5 flex flex-col shadow-xs">
          <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9] mb-4">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-rose-50 border border-rose-200 rounded-lg text-rose-700">
                <ShieldAlert className="w-5 h-5 text-[#d93829]" />
              </div>
              <div>
                <h3 className="text-base font-bold font-serif text-[#191410] tracking-wide">
                  Open Case & Custody Alerts
                </h3>
                <p className="text-xs text-[#6e665d]">Real-time statutory & evidentiary alerts</p>
              </div>
            </div>
            <span className="text-xs font-mono font-bold text-red-800 bg-red-100 border border-red-300 px-2 py-0.5 rounded">
              {alerts.length} Open
            </span>
          </div>

          <div className="space-y-2.5 flex-1">
            {alerts.length === 0 ? (
              <div className="h-40 flex flex-col items-center justify-center text-[#6e665d] font-mono text-xs">
                <CheckCircle2 className="w-6 h-6 text-emerald-600 mb-1.5" />
                <span>Zero unaddressed case alerts</span>
              </div>
            ) : (
              alerts.slice(0, 4).map(a => {
                const isCrit = a.severity === 'critical';
                const isWarn = a.severity === 'warning';
                return (
                  <div
                    key={a.id}
                    className={cn(
                      "p-3 rounded-xl border transition",
                      isCrit ? "bg-red-50 border-red-300" :
                      isWarn ? "bg-amber-50 border-amber-300" :
                      "bg-[#faf7f2] border-[#eae4d9]"
                    )}
                  >
                    <div className="flex items-start gap-2.5">
                      <div className={cn(
                        "w-5 h-5 rounded-full flex items-center justify-center shrink-0 mt-0.5",
                        isCrit ? "bg-red-600 text-white" : "bg-amber-500 text-white"
                      )}>
                        <AlertTriangle className="w-3 h-3" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <h5 className="text-xs font-bold text-[#191410] truncate">
                            {a.title}
                          </h5>
                          <span className="text-[9px] font-mono text-[#6e665d] shrink-0">
                            {new Date(a.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                        <p className="text-[11px] text-[#6e665d] line-clamp-1 mt-0.5">
                          {a.message}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* ====================================================================== */}
        {/* PANEL E: TASKS DUE & INVESTIGATION NEXT STEPS (Lg: col-span-4)         */}
        {/* ====================================================================== */}
        <div className="lg:col-span-4 bg-white border border-[#eae4d9] rounded-2xl p-5 flex flex-col shadow-xs">
          <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9] mb-4">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-700">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold font-serif text-[#191410] tracking-wide">
                  Investigative Tasks Due
                </h3>
                <p className="text-xs text-[#6e665d]">Active assignments & next best steps</p>
              </div>
            </div>
            <Link
              to={`/cases/${cleanCaseId}/tasks`}
              className="text-xs font-mono text-[#6e665d] hover:text-[#191410] flex items-center gap-1 transition"
            >
              All Tasks <ExternalLink className="w-3 h-3" />
            </Link>
          </div>

          <div className="space-y-2.5 flex-1">
            {tasks.length === 0 ? (
              <div className="h-40 flex items-center justify-center text-[#6e665d] font-mono text-xs">
                All investigative action items complete.
              </div>
            ) : (
              tasks.slice(0, 4).map(t => (
                <div
                  key={t.id}
                  className="p-3 bg-[#faf7f2] border border-[#eae4d9] rounded-xl flex items-center justify-between gap-3 shadow-xs"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={cn(
                        "text-[9px] font-mono font-bold px-1.5 py-0.2 rounded uppercase",
                        t.priority === 'Critical' ? "bg-red-100 text-red-800 border border-red-300" :
                        t.priority === 'High' ? "bg-amber-100 text-amber-800 border border-amber-300" :
                        "bg-stone-200 text-stone-800"
                      )}>
                        {t.priority}
                      </span>
                      <span className="text-xs font-bold text-[#191410] truncate">
                        {t.task}
                      </span>
                    </div>
                    <div className="text-[10px] text-[#6e665d] font-mono">
                      Assignee: {t.assigned_to}
                    </div>
                  </div>

                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-white text-stone-700 border border-[#eae4d9] shrink-0">
                    {t.status}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* ====================================================================== */}
        {/* PANEL F: TEAM PRESENCE & BACKGROUND WORKER JOBS (Full 12 cols row)     */}
        {/* ====================================================================== */}
        <div className="lg:col-span-12 grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Who is Online in Room */}
          <div className="bg-white border border-[#eae4d9] rounded-2xl p-5 shadow-xs">
            <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9] mb-3">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-blue-600" />
                <h4 className="text-sm font-bold text-[#191410] font-serif">
                  Active Team Members in Docket
                </h4>
              </div>
              <span className="text-[11px] font-mono text-emerald-700 font-bold">
                {onlineUsers.length} Online Now
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {onlineUsers.map((u, idx) => (
                <div key={idx} className="p-2.5 bg-[#faf7f2] border border-[#eae4d9] rounded-xl flex items-center gap-3">
                  <div className="relative">
                    <div className="w-8 h-8 rounded-full bg-stone-200 border border-stone-300 flex items-center justify-center font-bold text-xs text-[#191410]">
                      {u.user_name.charAt(0).toUpperCase()}
                    </div>
                    <span className="absolute bottom-0 right-0 w-2 h-2 rounded-full bg-emerald-500 border border-white" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-bold text-[#191410] truncate">
                      {u.user_name}
                    </div>
                    <div className="text-[10px] font-mono text-[#6e665d] truncate">
                      {u.user_role} • {u.current_location}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Running Background Pipeline Jobs */}
          <div className="bg-white border border-[#eae4d9] rounded-2xl p-5 shadow-xs">
            <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9] mb-3">
              <div className="flex items-center gap-2">
                <BrainCircuit className="w-4 h-4 text-purple-600" />
                <h4 className="text-sm font-bold text-[#191410] font-serif">
                  Forensic Worker Pipeline Queue
                </h4>
              </div>
              <span className="text-[11px] font-mono text-purple-700 font-bold">
                {jobs.length > 0 ? `${jobs.length} Active` : 'Queue Idle'}
              </span>
            </div>

            {jobs.length === 0 ? (
              <div className="h-16 flex items-center justify-center text-xs font-mono text-[#6e665d]">
                All background jobs concluded. Pipeline standing by.
              </div>
            ) : (
              <div className="space-y-2">
                {jobs.map(j => (
                  <div key={j.id} className="p-2.5 bg-[#faf7f2] border border-[#eae4d9] rounded-xl">
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="font-bold text-[#191410]">
                        Job #{j.id}: {j.job_type}
                      </span>
                      <span className="font-mono text-purple-700 font-bold">
                        {j.current_stage} ({j.progress_pct}%)
                      </span>
                    </div>
                    <div className="w-full bg-stone-200 h-1.5 rounded-full overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-purple-500 to-indigo-500 h-1.5 rounded-full transition-all duration-300"
                        style={{ width: `${j.progress_pct}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>

      {/* 4. FOOTER STATUS BAR */}
      <footer className="border-t border-[#eae4d9] bg-white px-6 py-2 flex flex-col sm:flex-row items-center justify-between text-[11px] font-mono text-[#6e665d]">
        <div className="flex items-center gap-4">
          <span>EVIDENTIA FORENSIC SITUATION ROOM</span>
          <span>•</span>
          <span>AUTONOMOUS STREAM: {streamActive ? 'CONNECTED (100ms)' : 'RECONNECTING'}</span>
        </div>
        <div className="flex items-center gap-4 mt-1 sm:mt-0">
          <span>SHORTCUTS: [F] FULLSCREEN • [P] BRIEFING MODE</span>
          <span>•</span>
          <span>SYNCED: {lastRefreshedAt.toLocaleTimeString()}</span>
        </div>
      </footer>
    </div>
  );
}

export default SituationBoard;

