// src/components/case/StreamingAnalysisStrip.tsx
import React, { useState } from 'react';
import { useStreamingAnalysis } from '../../context/StreamingAnalysisContext';
import {
  Sparkles,
  Zap,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  TrendingUp,
  FileText,
  Users,
  X,
  Play,
  RotateCcw,
  Loader2,
  Clock,
  EyeOff
} from 'lucide-react';

export function StreamingAnalysisStrip() {
  const {
    state,
    remainingHighlightSec,
    dismissWhatChanged,
    clearHighlights,
    simulateStream,
  } = useStreamingAnalysis();

  const [isSimulating, setIsSimulating] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  const handleSimulate = async () => {
    setIsSimulating(true);
    try {
      await simulateStream();
    } finally {
      setTimeout(() => setIsSimulating(false), 8000);
    }
  };

  const formatCountdown = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs < 10 ? '0' : ''}${secs}s`;
  };

  // If not streaming, no whatChangedSummary, and no active highlights, return a clean minimal floating test button or null
  const hasActiveHighlights = remainingHighlightSec > 0;
  const showBanner = state.isStreaming || Boolean(state.whatChangedSummary) || hasActiveHighlights;

  if (!showBanner) {
    return (
      <div className="mb-4 flex items-center justify-end">
        <button
          onClick={handleSimulate}
          disabled={isSimulating}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-amber-900 bg-amber-50 hover:bg-amber-100 border border-amber-200/80 rounded-md transition shadow-xs cursor-pointer"
          title="Simulate partial facts streaming live stage-by-stage as worker analyzes evidence"
        >
          {isSimulating ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-700" />
          ) : (
            <Play className="w-3.5 h-3.5 text-amber-700" />
          )}
          <span>Simulate Live Pipeline Stream</span>
        </button>
      </div>
    );
  }

  return (
    <div className="mb-5 space-y-2">
      {/* 1. Live Streaming Stage Indicator (Active while worker runs) */}
      {state.isStreaming && (
        <div className="bg-gradient-to-r from-amber-500/10 via-orange-500/10 to-amber-500/10 border border-amber-300 rounded-xl p-4 shadow-sm relative overflow-hidden animate-pulse-subtle">
          <div className="flex items-center justify-between gap-3 mb-2">
            <div className="flex items-center gap-2.5">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-amber-500"></span>
              </span>
              <div>
                <h4 className="text-sm font-semibold text-amber-950 flex items-center gap-2">
                  <span>Live Streaming Analysis</span>
                  <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
                    {state.stageLabel || 'Processing...'}
                  </span>
                </h4>
                <p className="text-xs text-amber-800/90 mt-0.5">
                  {state.evidenceFileName ? (
                    <>Processing exhibit <span className="font-semibold">{state.evidenceFileName}</span></>
                  ) : (
                    'Worker executing pipeline stages and streaming partial facts...'
                  )}
                </p>
              </div>
            </div>

            <div className="text-right">
              <span className="text-xs font-bold text-amber-900">{state.progressPct}%</span>
            </div>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-amber-200/60 rounded-full h-1.5 overflow-hidden mb-3">
            <div
              className="bg-gradient-to-r from-amber-500 to-orange-500 h-1.5 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${state.progressPct}%` }}
            />
          </div>

          {/* Streaming Partial Facts Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-2 text-xs">
            {/* Fact 1: Text */}
            <div className={`p-2 rounded-lg border transition-all ${state.textLength > 0 ? 'bg-white border-amber-200 shadow-xs' : 'bg-amber-100/40 border-amber-200/50 text-amber-600'}`}>
              <div className="flex items-center gap-1.5 font-medium text-amber-950 mb-1">
                <FileText className="w-3.5 h-3.5 text-amber-600" />
                <span>Extracted Text</span>
              </div>
              <div className="truncate text-stone-600">
                {state.textLength > 0 ? `${state.textLength} chars extracted` : 'Pending stage 1...'}
              </div>
            </div>

            {/* Fact 2: Entities */}
            <div className={`p-2 rounded-lg border transition-all ${state.newEntities.length > 0 ? 'bg-white border-amber-200 shadow-xs' : 'bg-amber-100/40 border-amber-200/50 text-amber-600'}`}>
              <div className="flex items-center gap-1.5 font-medium text-amber-950 mb-1">
                <Users className="w-3.5 h-3.5 text-amber-600" />
                <span>Entities Discovered</span>
              </div>
              <div className="truncate text-stone-600">
                {state.newEntities.length > 0 ? (
                  <span className="text-amber-800 font-semibold">{state.newEntities.length} new entities identified</span>
                ) : (
                  'Pending stage 3...'
                )}
              </div>
            </div>

            {/* Fact 3: Contradictions */}
            <div className={`p-2 rounded-lg border transition-all ${state.newContradictionsCount > 0 ? 'bg-white border-rose-200 shadow-xs' : 'bg-amber-100/40 border-amber-200/50 text-amber-600'}`}>
              <div className="flex items-center gap-1.5 font-medium text-amber-950 mb-1">
                <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />
                <span>Contradictions</span>
              </div>
              <div className="truncate text-stone-600">
                {state.newContradictionsCount > 0 ? (
                  <span className="text-rose-700 font-semibold">{state.newContradictionsCount} conflict detected</span>
                ) : (
                  'Checking cross-exhibit claims...'
                )}
              </div>
            </div>

            {/* Fact 4: Scores */}
            <div className={`p-2 rounded-lg border transition-all ${state.scoreMovementSummary ? 'bg-white border-emerald-200 shadow-xs' : 'bg-amber-100/40 border-amber-200/50 text-amber-600'}`}>
              <div className="flex items-center gap-1.5 font-medium text-amber-950 mb-1">
                <TrendingUp className="w-3.5 h-3.5 text-emerald-600" />
                <span>ACH Probability Shift</span>
              </div>
              <div className="truncate text-stone-600">
                {state.scoreMovementSummary ? (
                  <span className="text-emerald-800 font-semibold">{state.scoreMovementSummary}</span>
                ) : (
                  'Awaiting Bayesian update...'
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 2. "What Changed" Strip (Completed state) */}
      {!state.isStreaming && (state.whatChangedSummary || hasActiveHighlights) && (
        <div className="bg-gradient-to-r from-amber-50 via-orange-50/60 to-amber-50 border border-amber-200/90 rounded-xl p-3.5 shadow-xs transition-all">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-start sm:items-center gap-3">
              <div className="p-2 bg-amber-500/10 rounded-lg text-amber-700 shrink-0">
                <Zap className="w-5 h-5 fill-amber-500/20 text-amber-600" />
              </div>

              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-amber-900 bg-amber-200/70 px-2 py-0.5 rounded">
                    What Changed
                  </span>
                  <h4 className="text-sm font-semibold text-stone-900">
                    {state.whatChangedSummary || 'New forensic intelligence extracted and synthesized.'}
                  </h4>
                </div>

                {/* Subtext info & live highlight countdown */}
                <div className="flex flex-wrap items-center gap-3 mt-1 text-xs text-stone-600">
                  {hasActiveHighlights && (
                    <span className="inline-flex items-center gap-1 text-amber-800 font-medium">
                      <Clock className="w-3.5 h-3.5 text-amber-600" />
                      Highlighting new items (active for {formatCountdown(remainingHighlightSec)})
                    </span>
                  )}
                  {state.scoreMovementSummary && (
                    <span className="inline-flex items-center gap-1 text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                      <TrendingUp className="w-3 h-3 text-emerald-600" />
                      {state.scoreMovementSummary}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="text-xs font-medium text-stone-700 hover:text-stone-900 px-2.5 py-1 rounded bg-white hover:bg-stone-100 border border-stone-200 transition"
              >
                {showDetails ? 'Hide Details' : 'View Facts'}
              </button>

              {hasActiveHighlights && (
                <button
                  onClick={clearHighlights}
                  className="text-xs font-medium text-stone-600 hover:text-stone-800 px-2.5 py-1 rounded bg-white hover:bg-stone-100 border border-stone-200 transition flex items-center gap-1"
                  title="Remove highlight borders and badges from newly added elements"
                >
                  <EyeOff className="w-3.5 h-3.5" />
                  <span>Clear Highlights</span>
                </button>
              )}

              <button
                onClick={handleSimulate}
                disabled={isSimulating}
                className="text-xs font-medium text-amber-900 hover:text-amber-950 px-2.5 py-1 rounded bg-amber-100 hover:bg-amber-200 border border-amber-300 transition flex items-center gap-1"
                title="Re-run live streaming simulation"
              >
                {isSimulating ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <RotateCcw className="w-3.5 h-3.5" />
                )}
                <span>Simulate</span>
              </button>

              <button
                onClick={dismissWhatChanged}
                className="text-stone-400 hover:text-stone-600 p-1 rounded-md hover:bg-stone-200/50 transition"
                title="Dismiss banner"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Expandable detailed partial facts view */}
          {showDetails && (
            <div className="mt-3 pt-3 border-t border-amber-200/70 grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
              {/* Entities list */}
              <div className="bg-white p-3 rounded-lg border border-amber-200 shadow-2xs">
                <h5 className="font-semibold text-stone-800 mb-2 flex items-center justify-between">
                  <span>Discovered Entities</span>
                  <span className="bg-amber-100 text-amber-800 text-[10px] px-1.5 py-0.5 rounded font-bold">
                    {state.newEntities.length}
                  </span>
                </h5>
                {state.newEntities.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {state.newEntities.map((ent, idx) => (
                      <span
                        key={idx}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-amber-50 text-amber-900 border border-amber-200"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                        {ent.name}
                        {ent.type && <span className="text-[9px] text-amber-700/80 uppercase">({ent.type})</span>}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-stone-500 italic">No new entities in this batch.</p>
                )}
              </div>

              {/* Contradictions & Claims */}
              <div className="bg-white p-3 rounded-lg border border-amber-200 shadow-2xs">
                <h5 className="font-semibold text-stone-800 mb-2 flex items-center justify-between">
                  <span>Contradictions & Timeline</span>
                  <span className="bg-rose-100 text-rose-800 text-[10px] px-1.5 py-0.5 rounded font-bold">
                    {state.newContradictionsCount} Conflicts
                  </span>
                </h5>
                <div className="space-y-1.5">
                  <p className="text-stone-600">
                    Cross-referenced claims against prior exhibits for alibi validity and factual divergence.
                  </p>
                  {state.newEvents.length > 0 && (
                    <div className="text-[11px] text-stone-700 font-medium">
                      + {state.newEvents.length} chronological timestamp event(s) integrated.
                    </div>
                  )}
                </div>
              </div>

              {/* Hypothesis shifts */}
              <div className="bg-white p-3 rounded-lg border border-amber-200 shadow-2xs">
                <h5 className="font-semibold text-stone-800 mb-2 flex items-center justify-between">
                  <span>ACH Probability Movements</span>
                  <span className="bg-emerald-100 text-emerald-800 text-[10px] px-1.5 py-0.5 rounded font-bold">
                    Bayesian
                  </span>
                </h5>
                {state.scoreDeltas.length > 0 ? (
                  <div className="space-y-1.5">
                    {state.scoreDeltas.map((s, idx) => (
                      <div key={idx} className="flex items-center justify-between text-[11px] py-0.5 border-b border-stone-100 last:border-0">
                        <span className="font-semibold text-stone-800">{s.code || `H${s.hypothesis_id}`}</span>
                        <div className="flex items-center gap-1.5">
                          <span className="text-stone-500">{s.prev_pct}%</span>
                          <ArrowRight className="w-3 h-3 text-stone-400" />
                          <span className="font-bold text-stone-900">{s.new_pct}%</span>
                          <span className={`text-[10px] font-bold px-1 rounded ${s.delta_pct >= 0 ? 'text-emerald-700 bg-emerald-50' : 'text-rose-700 bg-rose-50'}`}>
                            {s.delta_pct > 0 ? `+${s.delta_pct}%` : `${s.delta_pct}%`}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-stone-500 italic">
                    {state.scoreMovementSummary || 'No significant probability shifts recorded.'}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default StreamingAnalysisStrip;
