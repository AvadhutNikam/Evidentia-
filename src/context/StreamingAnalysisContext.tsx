// src/context/StreamingAnalysisContext.tsx
import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import { jobService } from '../services';

export interface StreamEntityFact {
  id: number | string;
  name: string;
  type: string;
  confidence?: number;
}

export interface StreamEventFact {
  id: number | string;
  title: string;
  timestamp?: string;
}

export interface StreamScoreDelta {
  hypothesis_id: number;
  code: string;
  title: string;
  prev_pct: number;
  new_pct: number;
  delta_pct: number;
}

export interface StreamingAnalysisState {
  isStreaming: boolean;
  stage: string | null;
  stageLabel: string;
  progressPct: number;
  evidenceId: number | null;
  evidenceFileName: string | null;
  textPreview: string | null;
  textLength: number;
  newEntities: StreamEntityFact[];
  newEvents: StreamEventFact[];
  newContradictionsCount: number;
  scoreDeltas: StreamScoreDelta[];
  scoreMovementSummary: string | null;
  whatChangedSummary: string | null;
  completedAt: string | null;
}

interface StreamingAnalysisContextType {
  state: StreamingAnalysisState;
  isItemHighlighted: (type: 'entity' | 'event' | 'contradiction' | 'hypothesis', id: string | number) => boolean;
  highlightedEntityIds: Set<string | number>;
  highlightedEventIds: Set<string | number>;
  highlightedContradictionIds: Set<string | number>;
  highlightedHypothesisIds: Set<string | number>;
  remainingHighlightSec: number;
  dismissWhatChanged: () => void;
  clearHighlights: () => void;
  simulateStream: () => Promise<void>;
}

const defaultState: StreamingAnalysisState = {
  isStreaming: false,
  stage: null,
  stageLabel: '',
  progressPct: 0,
  evidenceId: null,
  evidenceFileName: null,
  textPreview: null,
  textLength: 0,
  newEntities: [],
  newEvents: [],
  newContradictionsCount: 0,
  scoreDeltas: [],
  scoreMovementSummary: null,
  whatChangedSummary: null,
  completedAt: null,
};

const StreamingAnalysisContext = createContext<StreamingAnalysisContextType>({
  state: defaultState,
  isItemHighlighted: () => false,
  highlightedEntityIds: new Set(),
  highlightedEventIds: new Set(),
  highlightedContradictionIds: new Set(),
  highlightedHypothesisIds: new Set(),
  remainingHighlightSec: 0,
  dismissWhatChanged: () => {},
  clearHighlights: () => {},
  simulateStream: async () => {},
});

const HIGHLIGHT_DURATION_SECONDS = 300; // 5 minutes

export function StreamingAnalysisProvider({ children }: { children: React.ReactNode }) {
  const { caseId: paramCaseId } = useParams<{ caseId?: string }>();
  const location = useLocation();

  const pathParts = location.pathname.split('/').filter(Boolean);
  const rawId = paramCaseId || (pathParts[0] === 'cases' && pathParts[1] ? pathParts[1] : null);
  const cleanCaseId = rawId ? String(rawId).replace(/^C-/, '') : null;

  const [state, setState] = useState<StreamingAnalysisState>(defaultState);
  const [highlightExpiresAt, setHighlightExpiresAt] = useState<number>(0);
  const [remainingHighlightSec, setRemainingHighlightSec] = useState<number>(0);

  const [highlightedEntityIds, setHighlightedEntityIds] = useState<Set<string | number>>(new Set());
  const [highlightedEventIds, setHighlightedEventIds] = useState<Set<string | number>>(new Set());
  const [highlightedContradictionIds, setHighlightedContradictionIds] = useState<Set<string | number>>(new Set());
  const [highlightedHypothesisIds, setHighlightedHypothesisIds] = useState<Set<string | number>>(new Set());

  // Countdown timer for item highlighting
  useEffect(() => {
    if (!highlightExpiresAt) {
      setRemainingHighlightSec(0);
      return;
    }

    const interval = setInterval(() => {
      const remaining = Math.max(0, Math.floor((highlightExpiresAt - Date.now()) / 1000));
      setRemainingHighlightSec(remaining);
      if (remaining <= 0) {
        setHighlightedEntityIds(new Set());
        setHighlightedEventIds(new Set());
        setHighlightedContradictionIds(new Set());
        setHighlightedHypothesisIds(new Set());
        clearInterval(interval);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [highlightExpiresAt]);

  // Load initial / latest streaming state on mount or case change
  useEffect(() => {
    if (!cleanCaseId) return;

    jobService.getLatestStreamingState(cleanCaseId)
      .then(res => {
        if (res && res.has_stream && res.payload) {
          const p = res.payload;
          const completedAtTime = p.completed_at ? new Date(p.completed_at).getTime() : 0;
          const isRecent = completedAtTime > Date.now() - HIGHLIGHT_DURATION_SECONDS * 1000;

          if (isRecent) {
            setState({
              isStreaming: false,
              stage: 'completed',
              stageLabel: 'Analysis Complete',
              progressPct: 100,
              evidenceId: p.evidence_id || null,
              evidenceFileName: p.evidence_file_name || 'Exhibit',
              textPreview: null,
              textLength: 0,
              newEntities: p.new_entities || [],
              newEvents: p.new_events || [],
              newContradictionsCount: p.new_contradictions_count || 0,
              scoreDeltas: p.score_deltas || [],
              scoreMovementSummary: p.score_movement_summary || null,
              whatChangedSummary: p.what_changed_summary || res.what_changed_summary,
              completedAt: p.completed_at || res.timestamp,
            });

            // Restore highlights if within 5-minute window
            const expiry = completedAtTime + HIGHLIGHT_DURATION_SECONDS * 1000;
            setHighlightExpiresAt(expiry);

            if (Array.isArray(p.new_entities)) {
              setHighlightedEntityIds(new Set(p.new_entities.map((e: any) => e.id || e.name)));
            }
            if (Array.isArray(p.score_deltas)) {
              setHighlightedHypothesisIds(new Set(p.score_deltas.map((s: any) => s.hypothesis_id)));
            }
          }
        }
      })
      .catch(() => {});
  }, [cleanCaseId]);

  // Listen to SSE live events
  useEffect(() => {
    if (!cleanCaseId) return;

    const unsubscribe = jobService.subscribeCaseEvents(
      cleanCaseId,
      (ev: any) => {
        if (!ev) return;
        const eventType = ev.event_type || ev.type;
        const payload = ev.payload || ev;

        // Stage 1: Text Extracted
        if (eventType === 'stream_stage_text') {
          setState(prev => ({
            ...prev,
            isStreaming: true,
            stage: 'extract_text',
            stageLabel: 'Text Extracted',
            progressPct: 25,
            evidenceId: payload.evidence_id || prev.evidenceId,
            evidenceFileName: payload.evidence_file_name || prev.evidenceFileName,
            textPreview: payload.text_preview || null,
            textLength: payload.text_length || 0,
          }));
        }

        // Stage 2: Entities & Claims Extracted
        else if (eventType === 'stream_stage_entities') {
          const entities = payload.new_entities || [];
          const events = payload.new_events || [];

          setState(prev => ({
            ...prev,
            isStreaming: true,
            stage: 'extract_entities_claims',
            stageLabel: 'Entities & Claims',
            progressPct: 65,
            newEntities: entities,
            newEvents: events,
          }));

          // Highlight newly discovered entities immediately
          setHighlightedEntityIds(new Set(entities.map((e: any) => e.id || e.name)));
          setHighlightedEventIds(new Set(events.map((e: any) => e.id || e.title)));
          setHighlightExpiresAt(Date.now() + HIGHLIGHT_DURATION_SECONDS * 1000);
        }

        // Stage 3: Citations Verified
        else if (eventType === 'stream_stage_citations') {
          setState(prev => ({
            ...prev,
            isStreaming: true,
            stage: 'verify_citations',
            stageLabel: 'Citations Verified',
            progressPct: 78,
          }));
        }

        // Stage 4: Contradictions Detected
        else if (eventType === 'stream_stage_contradictions') {
          const count = payload.new_contradictions_count || payload.contradictions_found || 0;
          setState(prev => ({
            ...prev,
            isStreaming: true,
            stage: 'detect_contradictions',
            stageLabel: 'Contradictions Checked',
            progressPct: 85,
            newContradictionsCount: count,
          }));
        }

        // Stage 5: Recalculated Scores
        else if (eventType === 'stream_stage_scores') {
          const deltas = payload.score_deltas || [];
          setState(prev => ({
            ...prev,
            isStreaming: true,
            stage: 'recalculate_scores',
            stageLabel: 'ACH Recalculated',
            progressPct: 99,
            scoreDeltas: deltas,
            scoreMovementSummary: payload.score_movement_summary || null,
          }));

          // Highlight hypotheses that had a score delta
          setHighlightedHypothesisIds(new Set(deltas.filter((d: any) => Math.abs(d.delta_pct) >= 1).map((d: any) => d.hypothesis_id)));
          setHighlightExpiresAt(Date.now() + HIGHLIGHT_DURATION_SECONDS * 1000);
        }

        // Final: Stream Stage Completed with "What Changed" summary
        else if (eventType === 'stream_stage_completed') {
          const whatChanged = payload.what_changed_summary || ev.summary;
          const entities = payload.new_entities || [];
          const deltas = payload.score_deltas || [];

          setState(prev => ({
            ...prev,
            isStreaming: false,
            stage: 'completed',
            stageLabel: 'Analysis Complete',
            progressPct: 100,
            whatChangedSummary: whatChanged,
            newEntities: entities.length > 0 ? entities : prev.newEntities,
            newEvents: payload.new_events || prev.newEvents,
            newContradictionsCount: payload.new_contradictions_count ?? prev.newContradictionsCount,
            scoreDeltas: deltas.length > 0 ? deltas : prev.scoreDeltas,
            scoreMovementSummary: payload.score_movement_summary || prev.scoreMovementSummary,
            completedAt: payload.completed_at || new Date().toISOString(),
          }));

          // Activate 5-minute highlight window for all new items
          if (entities.length > 0) {
            setHighlightedEntityIds(new Set(entities.map((e: any) => e.id || e.name)));
          }
          if (deltas.length > 0) {
            setHighlightedHypothesisIds(new Set(deltas.filter((d: any) => Math.abs(d.delta_pct) >= 1).map((d: any) => d.hypothesis_id)));
          }
          setHighlightExpiresAt(Date.now() + HIGHLIGHT_DURATION_SECONDS * 1000);
        }
      }
    );

    return () => unsubscribe();
  }, [cleanCaseId]);

  const isItemHighlighted = useCallback((
    type: 'entity' | 'event' | 'contradiction' | 'hypothesis',
    id: string | number
  ): boolean => {
    if (Date.now() > highlightExpiresAt) return false;
    const strId = String(id).toLowerCase();
    const numId = Number(id);

    if (type === 'entity') {
      return (
        highlightedEntityIds.has(id) ||
        highlightedEntityIds.has(numId) ||
        highlightedEntityIds.has(strId) ||
        Array.from(highlightedEntityIds).some(e => String(e).toLowerCase() === strId)
      );
    } else if (type === 'event') {
      return highlightedEventIds.has(id) || highlightedEventIds.has(numId);
    } else if (type === 'contradiction') {
      return highlightedContradictionIds.has(id) || highlightedContradictionIds.has(numId);
    } else if (type === 'hypothesis') {
      return highlightedHypothesisIds.has(id) || highlightedHypothesisIds.has(numId);
    }
    return false;
  }, [highlightExpiresAt, highlightedEntityIds, highlightedEventIds, highlightedContradictionIds, highlightedHypothesisIds]);

  const dismissWhatChanged = useCallback(() => {
    setState(prev => ({ ...prev, whatChangedSummary: null }));
  }, []);

  const clearHighlights = useCallback(() => {
    setHighlightExpiresAt(0);
    setHighlightedEntityIds(new Set());
    setHighlightedEventIds(new Set());
    setHighlightedContradictionIds(new Set());
    setHighlightedHypothesisIds(new Set());
  }, []);

  const simulateStream = useCallback(async () => {
    if (!cleanCaseId) return;
    try {
      await jobService.simulateStreamingAnalysis(cleanCaseId);
    } catch (err) {
      console.error('Failed to trigger simulated stream:', err);
    }
  }, [cleanCaseId]);

  return (
    <StreamingAnalysisContext.Provider
      value={{
        state,
        isItemHighlighted,
        highlightedEntityIds,
        highlightedEventIds,
        highlightedContradictionIds,
        highlightedHypothesisIds,
        remainingHighlightSec,
        dismissWhatChanged,
        clearHighlights,
        simulateStream,
      }}
    >
      {children}
    </StreamingAnalysisContext.Provider>
  );
}

export function useStreamingAnalysis() {
  return useContext(StreamingAnalysisContext);
}
export default StreamingAnalysisContext;

