import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { useLocation, useParams } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { PresenceUser, EditLock, CollaborationEvent, ConflictDetail } from '../types';
import { collaborationService, jobService } from '../services';

interface CollaborationContextType {
  caseId: number | null;
  activeUsers: PresenceUser[];
  activeLocks: EditLock[];
  recentEvents: CollaborationEvent[];
  isConnected: boolean;
  isOffline: boolean;
  acquireLock: (itemType: string, itemId: string, ttlSeconds?: number) => Promise<boolean>;
  releaseLock: (itemType: string, itemId: string) => Promise<boolean>;
  overrideLock: (itemType: string, itemId: string, reason?: string) => Promise<boolean>;
  getLockForItem: (itemType: string, itemId: string) => EditLock | undefined;
  isItemLockedByOther: (itemType: string, itemId: string) => boolean;
  conflictModalData: ConflictDetail | null;
  setConflictModalData: (data: ConflictDetail | null) => void;
  isActivityFeedOpen: boolean;
  setIsActivityFeedOpen: (open: boolean) => void;
  lastScoreUpdate: string | null;
  setCurrentViewItem: (itemId: string | null) => void;
}

const defaultCollaborationState: CollaborationContextType = {
  caseId: null,
  activeUsers: [],
  activeLocks: [],
  recentEvents: [],
  isConnected: true,
  isOffline: false,
  acquireLock: async () => false,
  releaseLock: async () => false,
  overrideLock: async () => false,
  getLockForItem: () => undefined,
  isItemLockedByOther: () => false,
  conflictModalData: null,
  setConflictModalData: () => {},
  isActivityFeedOpen: false,
  setIsActivityFeedOpen: () => {},
  lastScoreUpdate: null,
  setCurrentViewItem: () => {},
};

const CollaborationContext = createContext<CollaborationContextType>(defaultCollaborationState);

export function CollaborationProvider({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const params = useParams<{ caseId?: string }>();
  const { user } = useAuth();

  // Extract caseId from route params or pathname
  const pathParts = location.pathname.split('/').filter(Boolean);
  const rawCaseId = params.caseId || (pathParts[0] === 'cases' && pathParts[1] ? pathParts[1] : null);
  const caseId = rawCaseId ? parseInt(String(rawCaseId).replace(/^C-/, ''), 10) : null;

  const [activeUsers, setActiveUsers] = useState<PresenceUser[]>([]);
  const [activeLocks, setActiveLocks] = useState<EditLock[]>([]);
  const [recentEvents, setRecentEvents] = useState<CollaborationEvent[]>([]);
  const [isConnected, setIsConnected] = useState<boolean>(true);
  const [isOffline, setIsOffline] = useState<boolean>(false);
  const [conflictModalData, setConflictModalData] = useState<ConflictDetail | null>(null);
  const [isActivityFeedOpen, setIsActivityFeedOpen] = useState<boolean>(false);
  const [lastScoreUpdate, setLastScoreUpdate] = useState<string | null>(null);
  const [currentViewItem, setCurrentViewItem] = useState<string | null>(null);

  const heartbeatTimerRef = useRef<any>(null);
  const activeItemIdRef = useRef<string | null>(currentViewItem);
  activeItemIdRef.current = currentViewItem;

  // Compute user-friendly location name based on pathname
  const computeLocationName = useCallback((pathname: string, itemId: string | null) => {
    const parts = pathname.split('/').filter(Boolean);
    const subpage = parts[2] || 'overview';
    switch (subpage) {
      case 'hypotheses':
        return itemId ? `Hypothesis #${itemId}` : 'Hypotheses Analysis';
      case 'suspect-profile':
        return itemId ? `Suspect Profile (${itemId})` : 'Suspect Profiles';
      case 'evidence':
        return itemId ? `Evidence Exhibit #${itemId}` : 'Evidence Locker';
      case 'contradictions':
        return 'Contradiction Matrix';
      case 'scoring-config':
        return 'Scoring Calibration';
      case 'reports':
        return 'Case Reports';
      default:
        return 'Case Workspace';
    }
  }, []);

  // 1. Initial fetch of presence & active locks
  const loadInitialState = useCallback(async (cId: number) => {
    try {
      const [users, locks, history] = await Promise.all([
        collaborationService.getActivePresence(cId).catch(() => []),
        collaborationService.getLocks(cId).catch(() => []),
        collaborationService.getHistory(cId, 0).catch(() => [])
      ]);
      setActiveUsers(users);
      setActiveLocks(locks);
      if (Array.isArray(history) && history.length > 0) {
        setRecentEvents(history.slice(-30).reverse());
      }
    } catch (err) {
      console.warn('[Collaboration] Failed to load initial collaboration state:', err);
    }
  }, []);

  // 2. Periodic presence heartbeat (every 25 seconds)
  useEffect(() => {
    if (!caseId || !user) return;

    loadInitialState(caseId);

    const sendBeat = async () => {
      try {
        const loc = computeLocationName(location.pathname, activeItemIdRef.current);
        await collaborationService.sendHeartbeat(caseId, loc, activeItemIdRef.current);
        const latestPresence = await collaborationService.getActivePresence(caseId);
        setActiveUsers(latestPresence);
        setIsOffline(false);
      } catch (err) {
        console.warn('[Collaboration] Heartbeat error:', err);
      }
    };

    // Send immediately on route/item change
    sendBeat();

    // Set recurring interval
    heartbeatTimerRef.current = setInterval(sendBeat, 25000);

    return () => {
      if (heartbeatTimerRef.current) {
        clearInterval(heartbeatTimerRef.current);
        heartbeatTimerRef.current = null;
      }
    };
  }, [caseId, user, location.pathname, computeLocationName, loadInitialState]);

  // 3. SSE Live Event Stream
  useEffect(() => {
    if (!caseId) return;

    const unsubscribe = jobService.subscribeCaseEvents(
      caseId,
      (event: any) => {
        setIsConnected(true);
        setIsOffline(false);

        // Handle collaboration events
        if (event && event.event_type) {
          const collabEv = event as CollaborationEvent;
          setRecentEvents(prev => [collabEv, ...prev.slice(0, 49)]);

          // Update active locks on lock events
          if (collabEv.event_type === 'lock.acquired' && collabEv.payload) {
            setActiveLocks(prev => {
              const filtered = prev.filter(l => !(l.item_type === collabEv.item_type && l.item_id === collabEv.item_id));
              return [...filtered, collabEv.payload];
            });
          } else if (collabEv.event_type === 'lock.released') {
            setActiveLocks(prev => prev.filter(l => !(l.item_type === collabEv.item_type && l.item_id === collabEv.item_id)));
          }

          // Update scores timestamp
          if (collabEv.event_type === 'scores.updated') {
            setLastScoreUpdate(new Date().toISOString());
            // Dispatch a window event so active scoring pages can refresh their matrix without overwriting form inputs
            window.dispatchEvent(new CustomEvent('evidentia:scores-updated', { detail: collabEv }));
          }

          // Refresh presence on join/leave/move
          if (collabEv.event_type.startsWith('presence.')) {
            collaborationService.getActivePresence(caseId)
              .then(users => setActiveUsers(users))
              .catch(() => {});
          }

          // Dispatch item.changed so active detail views can update
          if (collabEv.event_type === 'item.changed') {
            window.dispatchEvent(new CustomEvent('evidentia:item-changed', { detail: collabEv }));
          }

          // Dispatch alert events for NotificationBellDropdown & Handover views
          if (collabEv.event_type.startsWith('alert.')) {
            window.dispatchEvent(new CustomEvent('evidentia:alert-event', { detail: collabEv }));
          }
        }
      },
      (err: any) => {
        console.warn('[Collaboration] Stream disconnected:', err);
        setIsConnected(false);
        setIsOffline(true);
      }
    );

    return () => {
      unsubscribe();
    };
  }, [caseId]);

  // Lock helper methods
  const acquireLock = useCallback(async (itemType: string, itemId: string, ttlSeconds = 120): Promise<boolean> => {
    if (!caseId) return false;
    try {
      const lock = await collaborationService.acquireLock(caseId, itemType, itemId, ttlSeconds);
      if (lock) {
        setActiveLocks(prev => {
          const filtered = prev.filter(l => !(l.item_type === itemType && l.item_id === itemId));
          return [...filtered, lock];
        });
        return true;
      }
      return false;
    } catch (err: any) {
      if (err?.status === 423) {
        console.warn(`[Collaboration] Item ${itemType} #${itemId} is locked by another investigator.`);
      }
      return false;
    }
  }, [caseId]);

  const releaseLock = useCallback(async (itemType: string, itemId: string): Promise<boolean> => {
    if (!caseId) return false;
    try {
      const ok = await collaborationService.releaseLock(caseId, itemType, itemId);
      setActiveLocks(prev => prev.filter(l => !(l.item_type === itemType && l.item_id === itemId)));
      return ok;
    } catch {
      return false;
    }
  }, [caseId]);

  const overrideLock = useCallback(async (itemType: string, itemId: string, reason?: string): Promise<boolean> => {
    if (!caseId) return false;
    try {
      const lock = await collaborationService.overrideLock(caseId, itemType, itemId, reason);
      if (lock) {
        setActiveLocks(prev => {
          const filtered = prev.filter(l => !(l.item_type === itemType && l.item_id === itemId));
          return [...filtered, lock];
        });
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }, [caseId]);

  const getLockForItem = useCallback((itemType: string, itemId: string): EditLock | undefined => {
    const cleanId = String(itemId).trim();
    return activeLocks.find(l => l.item_type === itemType && String(l.item_id).trim() === cleanId);
  }, [activeLocks]);

  const isItemLockedByOther = useCallback((itemType: string, itemId: string): boolean => {
    const lock = getLockForItem(itemType, itemId);
    if (!lock || !user) return false;
    return lock.user_id !== user.id;
  }, [getLockForItem, user]);

  return (
    <CollaborationContext.Provider
      value={{
        caseId,
        activeUsers,
        activeLocks,
        recentEvents,
        isConnected,
        isOffline,
        acquireLock,
        releaseLock,
        overrideLock,
        getLockForItem,
        isItemLockedByOther,
        conflictModalData,
        setConflictModalData,
        isActivityFeedOpen,
        setIsActivityFeedOpen,
        lastScoreUpdate,
        setCurrentViewItem,
      }}
    >
      {children}
    </CollaborationContext.Provider>
  );
}

export function useCollaboration() {
  const context = useContext(CollaborationContext);
  return context;
}
