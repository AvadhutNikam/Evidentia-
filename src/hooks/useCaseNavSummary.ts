import { useState, useEffect, useRef } from 'react';
import { 
  evidenceService, 
  contradictionService, 
  scoringService, 
  investigationService, 
  alertService 
} from '../services';

export interface CaseNavBadges {
  evidence_processing: number;
  data_quality_issues: number;
  unresolved_contradictions: number;
  critical_gaps: number;
  priorities_due: number;
  handover_changed: boolean;
}

const DEFAULT_BADGES: CaseNavBadges = {
  evidence_processing: 0,
  data_quality_issues: 0,
  unresolved_contradictions: 0,
  critical_gaps: 0,
  priorities_due: 0,
  handover_changed: false
};

// Global memory cache per caseId to prevent redundant fetches
const summaryCache: Record<string, { data: CaseNavBadges; timestamp: number }> = {};
const CACHE_TTL_MS = 15000; // 15 seconds

export function useCaseNavSummary(caseId: string | undefined): CaseNavBadges {
  const [badges, setBadges] = useState<CaseNavBadges>(() => {
    if (caseId && summaryCache[caseId]) {
      return summaryCache[caseId].data;
    }
    return DEFAULT_BADGES;
  });

  const isMounted = useRef(true);

  useEffect(() => {
    isMounted.current = true;
    if (!caseId) return;

    // Check cache
    const cached = summaryCache[caseId];
    const now = Date.now();
    if (cached && now - cached.timestamp < CACHE_TTL_MS) {
      setBadges(cached.data);
      return;
    }

    let isCancelled = false;

    async function fetchSummary() {
      try {
        const [
          evidenceList, 
          contradictionsList, 
          gapsList, 
          tasksList,
          alertsList
        ] = await Promise.all([
          evidenceService.getEvidenceForCase(caseId!).catch(() => []),
          contradictionService.getContradictionsForCase(caseId!).catch(() => []),
          scoringService.getInvestigativeGaps(caseId!).catch(() => []),
          investigationService.getTasksForCase(caseId!).catch(() => []),
          alertService.getAlerts(caseId!).catch(() => [])
        ]);

        if (isCancelled || !isMounted.current) return;

        // Compute badges
        const processingExhibits = (evidenceList || []).filter(
          (e: any) => e.status === 'processing' || e.status === 'pending' || e.status === 'error'
        ).length;

        const dataQualityIssues = (evidenceList || []).filter(
          (e: any) => e.integrity_verified === false || (typeof e.ocr_confidence === 'number' && e.ocr_confidence < 0.70)
        ).length;

        const openContradictions = (contradictionsList || []).filter(
          (c: any) => !c.resolved && c.status !== 'resolved'
        ).length;

        const criticalGaps = (gapsList || []).filter(
          (g: any) => (g.severity === 'high' || g.severity === 'critical') && !g.is_dismissed && !g.is_accepted
        ).length;

        const urgentTasks = (tasksList || []).filter(
          (t: any) => t.priority === 'urgent' || t.priority === 'high' || t.status === 'overdue'
        ).length;

        const unreadAlerts = (alertsList || []).filter(
          (a: any) => !a.is_read
        ).length;

        const newBadges: CaseNavBadges = {
          evidence_processing: processingExhibits,
          data_quality_issues: dataQualityIssues,
          unresolved_contradictions: openContradictions,
          critical_gaps: criticalGaps,
          priorities_due: urgentTasks + (unreadAlerts > 0 ? 1 : 0),
          handover_changed: unreadAlerts > 0
        };

        summaryCache[caseId!] = {
          data: newBadges,
          timestamp: Date.now()
        };

        setBadges(newBadges);
      } catch (err) {
        console.error('Failed to compute case nav badges:', err);
      }
    }

    fetchSummary();

    // Listen for live event stream triggers to refresh badge signals
    const handleLiveUpdate = () => {
      fetchSummary();
    };

    window.addEventListener('evidentia:live-event', handleLiveUpdate);
    window.addEventListener('evidentia:evidence-updated', handleLiveUpdate);
    window.addEventListener('evidentia:tasks-updated', handleLiveUpdate);

    return () => {
      isCancelled = true;
      isMounted.current = false;
      window.removeEventListener('evidentia:live-event', handleLiveUpdate);
      window.removeEventListener('evidentia:evidence-updated', handleLiveUpdate);
      window.removeEventListener('evidentia:tasks-updated', handleLiveUpdate);
    };
  }, [caseId]);

  return badges;
}
