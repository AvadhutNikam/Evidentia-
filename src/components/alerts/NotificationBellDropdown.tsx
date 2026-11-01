import React, { useState, useEffect, useCallback, useRef } from 'react';
import { 
  Bell, AlertTriangle, AlertOctagon, Info, CheckCircle2, 
  Clock, Check, X, ExternalLink, Moon, Sparkles, ShieldAlert 
} from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useCollaboration } from '../../context/CollaborationContext';
import { alertService } from '../../services';
import { Alert } from '../../types';

export function NotificationBellDropdown() {
  const navigate = useNavigate();
  const location = useLocation();
  const collab = useCollaboration();
  const [isOpen, setIsOpen] = useState(false);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [filter, setFilter] = useState<'all' | 'unread' | 'critical'>('unread');
  const [loading, setLoading] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);
  const [snoozeOpenId, setSnoozeOpenId] = useState<number | null>(null);
  const [resolvePromptId, setResolvePromptId] = useState<number | null>(null);
  const [resolveNote, setResolveNote] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Extract caseId from collaboration context or location
  const pathParts = location.pathname.split('/').filter(Boolean);
  const pathCaseId = (pathParts[0] === 'cases' && pathParts[1]) ? pathParts[1] : null;
  const currentCaseId = collab?.caseId || (pathCaseId ? parseInt(pathCaseId.replace(/^C-/, ''), 10) : null);

  const fetchAlerts = useCallback(async () => {
    if (!currentCaseId) {
      setAlerts([]);
      return;
    }
    try {
      setLoading(true);
      const data = await alertService.getAlerts(currentCaseId);
      setAlerts(data || []);
    } catch (err) {
      console.warn('[Alerts] Could not fetch alerts:', err);
    } finally {
      setLoading(false);
    }
  }, [currentCaseId]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  // Subscribe to live alert events from SSE
  useEffect(() => {
    const handleAlertEvent = (e: Event) => {
      fetchAlerts();
    };
    window.addEventListener('evidentia:alert-event', handleAlertEvent);
    return () => window.removeEventListener('evidentia:alert-event', handleAlertEvent);
  }, [fetchAlerts]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setSnoozeOpenId(null);
        setResolvePromptId(null);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const unreadAlerts = alerts.filter(a => a.status === 'unread');
  const criticalCount = unreadAlerts.filter(a => a.severity === 'critical').length;
  const unreadCount = unreadAlerts.length;

  const filteredAlerts = alerts.filter(a => {
    if (filter === 'unread') return a.status === 'unread';
    if (filter === 'critical') return a.severity === 'critical' && a.status !== 'resolved';
    return a.status !== 'resolved';
  });

  const handleAcknowledge = async (alertId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!currentCaseId) return;
    try {
      setActionLoadingId(alertId);
      await alertService.acknowledgeAlert(currentCaseId, alertId);
      setAlerts(prev => prev.map(a => a.id === alertId ? { ...a, status: 'acknowledged' } : a));
    } catch (err) {
      console.error('Failed to acknowledge alert:', err);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleSnooze = async (alertId: number, hours: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!currentCaseId) return;
    try {
      setActionLoadingId(alertId);
      await alertService.snoozeAlert(currentCaseId, alertId, hours);
      setAlerts(prev => prev.filter(a => a.id !== alertId));
      setSnoozeOpenId(null);
    } catch (err) {
      console.error('Failed to snooze alert:', err);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleResolve = async (alertId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!currentCaseId || !resolveNote.trim()) return;
    try {
      setActionLoadingId(alertId);
      await alertService.resolveAlert(currentCaseId, alertId, resolveNote.trim());
      setAlerts(prev => prev.filter(a => a.id !== alertId));
      setResolvePromptId(null);
      setResolveNote('');
    } catch (err) {
      console.error('Failed to resolve alert:', err);
    } finally {
      setActionLoadingId(null);
    }
  };

  const navigateToLinkedItem = (alert: Alert) => {
    if (!currentCaseId) return;
    setIsOpen(false);
    if (alert.linked_item_type === 'hypothesis') {
      navigate(`/cases/${currentCaseId}/hypotheses`);
    } else if (alert.linked_item_type === 'evidence') {
      navigate(`/cases/${currentCaseId}/evidence`);
    } else if (alert.linked_item_type === 'deadline') {
      navigate(`/cases/${currentCaseId}/handover`);
    } else if (alert.linked_item_type === 'audit') {
      navigate(`/cases/${currentCaseId}/audit`);
    } else {
      navigate(`/cases/${currentCaseId}/handover`);
    }
  };

  const formatRelativeTime = (isoString?: string) => {
    if (!isoString) return '';
    const diff = (Date.now() - new Date(isoString).getTime()) / 1000;
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Trigger Button */}
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-full text-[#70685e] hover:text-[#191410] hover:bg-[#f0ebe1] transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#d93829]/20"
        title={unreadCount > 0 ? `${unreadCount} unread alert${unreadCount > 1 ? 's' : ''}` : "Alerts & Notifications"}
      >
        <Bell className="w-4 h-4" />
        
        {unreadCount > 0 && (
          <span className={`absolute -top-0.5 -right-0.5 min-w-4 h-4 px-1 rounded-full flex items-center justify-center text-[10px] font-bold text-white shadow-xs ring-2 ring-white ${
            criticalCount > 0 ? 'bg-[#d93829] animate-pulse' : 'bg-[#e59b00]'
          }`}>
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-96 max-w-[calc(100vw-2rem)] rounded-2xl bg-white border border-[#eae4d9] shadow-xl z-50 animate-fadeIn overflow-hidden flex flex-col">
          {/* Header */}
          <div className="px-4 py-3 bg-[#faf7f2] border-b border-[#eae4d9] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-[#d93829]" />
              <span className="text-xs font-bold text-[#191410]">Case Alerts & Reminders</span>
              {unreadCount > 0 && (
                <span className="text-[10px] font-mono font-bold bg-[#fdeee9] text-[#d93829] px-2 py-0.5 rounded-full">
                  {unreadCount} unread
                </span>
              )}
            </div>
            
            {currentCaseId && (
              <button 
                onClick={() => { setIsOpen(false); navigate(`/cases/${currentCaseId}/handover`); }}
                className="text-[11px] font-semibold text-[#1b64b8] hover:underline flex items-center gap-1 cursor-pointer"
              >
                Handover Dossier
                <ExternalLink className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* Filter Tabs */}
          <div className="flex border-b border-[#eae4d9] bg-white text-xs px-2 pt-1">
            <button
              onClick={() => setFilter('unread')}
              className={`px-3 py-1.5 font-medium border-b-2 text-[11px] transition-all cursor-pointer ${
                filter === 'unread' 
                  ? 'border-[#d93829] text-[#d93829] font-bold' 
                  : 'border-transparent text-[#70685e] hover:text-[#191410]'
              }`}
            >
              Unread ({unreadCount})
            </button>
            <button
              onClick={() => setFilter('critical')}
              className={`px-3 py-1.5 font-medium border-b-2 text-[11px] transition-all cursor-pointer ${
                filter === 'critical' 
                  ? 'border-[#d93829] text-[#d93829] font-bold' 
                  : 'border-transparent text-[#70685e] hover:text-[#191410]'
              }`}
            >
              Critical ({alerts.filter(a => a.severity === 'critical' && a.status !== 'resolved').length})
            </button>
            <button
              onClick={() => setFilter('all')}
              className={`px-3 py-1.5 font-medium border-b-2 text-[11px] transition-all cursor-pointer ${
                filter === 'all' 
                  ? 'border-[#d93829] text-[#d93829] font-bold' 
                  : 'border-transparent text-[#70685e] hover:text-[#191410]'
              }`}
            >
              Active ({alerts.filter(a => a.status !== 'resolved').length})
            </button>
          </div>

          {/* Alerts List */}
          <div className="max-h-96 overflow-y-auto divide-y divide-[#eae4d9]">
            {filteredAlerts.length === 0 ? (
              <div className="py-8 px-4 text-center">
                <CheckCircle2 className="w-8 h-8 text-[#22c55e] mx-auto mb-2 opacity-80" />
                <div className="text-xs font-semibold text-[#191410]">All Conditions Normal</div>
                <div className="text-[11px] text-[#70685e] mt-1 max-w-xs mx-auto">
                  No active alerts matching filter. Forensic integrity verified and statutory deadlines tracked.
                </div>
              </div>
            ) : (
              filteredAlerts.map(alert => {
                const isCritical = alert.severity === 'critical';
                const isWarning = alert.severity === 'warning';
                const isUnread = alert.status === 'unread';

                return (
                  <div 
                    key={alert.id}
                    onClick={() => navigateToLinkedItem(alert)}
                    className={`p-3.5 hover:bg-[#faf7f2] transition-colors cursor-pointer text-left relative ${
                      isUnread ? 'bg-[#fffcf9]' : 'bg-white'
                    }`}
                  >
                    {isUnread && (
                      <span className="absolute top-4 right-3 w-2 h-2 rounded-full bg-[#d93829]" />
                    )}

                    <div className="flex items-start gap-2.5">
                      {/* Icon */}
                      <div className="mt-0.5 shrink-0">
                        {isCritical ? (
                          <div className="w-6 h-6 rounded-full bg-[#fdeee9] text-[#d93829] flex items-center justify-center">
                            <AlertOctagon className="w-3.5 h-3.5" />
                          </div>
                        ) : isWarning ? (
                          <div className="w-6 h-6 rounded-full bg-[#fff8ea] text-[#e59b00] flex items-center justify-center">
                            <AlertTriangle className="w-3.5 h-3.5" />
                          </div>
                        ) : (
                          <div className="w-6 h-6 rounded-full bg-[#ebf4fd] text-[#1b64b8] flex items-center justify-center">
                            <Info className="w-3.5 h-3.5" />
                          </div>
                        )}
                      </div>

                      {/* Content */}
                      <div className="flex-1 pr-3">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-xs font-bold text-[#191410] leading-snug">
                            {alert.title}
                          </span>
                          <span className={`text-[9px] font-mono uppercase px-1.5 py-0.2 rounded font-bold ${
                            isCritical 
                              ? 'bg-[#fdeee9] text-[#d93829]' 
                              : isWarning 
                              ? 'bg-[#fff8ea] text-[#8a5b00]' 
                              : 'bg-[#ebf4fd] text-[#1b64b8]'
                          }`}>
                            {alert.severity}
                          </span>
                        </div>

                        <p className="text-[11px] text-[#554e44] mt-1 leading-relaxed line-clamp-3">
                          {alert.message}
                        </p>

                        <div className="flex items-center gap-2 mt-2 text-[10px] text-[#8c8276]">
                          <span>{formatRelativeTime(alert.created_at)}</span>
                          {alert.linked_item_type && (
                            <>
                              <span>•</span>
                              <span className="capitalize font-medium text-[#1b64b8] hover:underline">
                                {alert.linked_item_type} #{alert.linked_item_id}
                              </span>
                            </>
                          )}
                          {alert.acknowledged_by && (
                            <>
                              <span>•</span>
                              <span className="text-[#1b7a37] font-medium">
                                Ack by {alert.acknowledged_by}
                              </span>
                            </>
                          )}
                        </div>

                        {/* Actions Row */}
                        <div className="flex items-center gap-2 mt-2.5 pt-2 border-t border-[#f0ebe1]" onClick={e => e.stopPropagation()}>
                          {alert.status === 'unread' && (
                            <button
                              onClick={(e) => handleAcknowledge(alert.id, e)}
                              disabled={actionLoadingId === alert.id}
                              className="px-2.5 py-1 text-[10px] font-semibold text-[#191410] bg-[#f0ebe1] hover:bg-[#e4ddd1] rounded-md transition-colors flex items-center gap-1 cursor-pointer"
                              title="Acknowledge alert"
                            >
                              <Check className="w-3 h-3 text-[#1b7a37]" />
                              Acknowledge
                            </button>
                          )}

                          {/* Snooze Button */}
                          <div className="relative">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setSnoozeOpenId(snoozeOpenId === alert.id ? null : alert.id);
                              }}
                              className="px-2.5 py-1 text-[10px] font-semibold text-[#70685e] hover:text-[#191410] hover:bg-[#f0ebe1] rounded-md transition-colors flex items-center gap-1 cursor-pointer"
                              title="Snooze reminder"
                            >
                              <Moon className="w-3 h-3" />
                              Snooze
                            </button>

                            {snoozeOpenId === alert.id && (
                              <div className="absolute left-0 bottom-full mb-1 w-32 bg-white rounded-lg border border-[#eae4d9] shadow-lg py-1 z-20 text-[11px]">
                                <button
                                  onClick={(e) => handleSnooze(alert.id, 4, e)}
                                  className="w-full text-left px-3 py-1 hover:bg-[#faf7f2] text-[#191410] cursor-pointer"
                                >
                                  For 4 hours
                                </button>
                                <button
                                  onClick={(e) => handleSnooze(alert.id, 24, e)}
                                  className="w-full text-left px-3 py-1 hover:bg-[#faf7f2] text-[#191410] cursor-pointer"
                                >
                                  For 24 hours
                                </button>
                                <button
                                  onClick={(e) => handleSnooze(alert.id, 72, e)}
                                  className="w-full text-left px-3 py-1 hover:bg-[#faf7f2] text-[#191410] cursor-pointer"
                                >
                                  For 3 days
                                </button>
                              </div>
                            )}
                          </div>

                          {/* Resolve Button */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setResolvePromptId(resolvePromptId === alert.id ? null : alert.id);
                            }}
                            className="px-2.5 py-1 text-[10px] font-semibold text-[#1b7a37] hover:bg-[#ebf7ee] rounded-md transition-colors flex items-center gap-1 cursor-pointer"
                          >
                            <CheckCircle2 className="w-3 h-3" />
                            Resolve
                          </button>
                        </div>

                        {/* Inline Resolve Rationale Input */}
                        {resolvePromptId === alert.id && (
                          <div className="mt-2 p-2 bg-[#f4efe6] rounded-lg space-y-1.5" onClick={e => e.stopPropagation()}>
                            <div className="text-[10px] font-bold text-[#191410]">Resolution Rationale (Audit Record):</div>
                            <input
                              type="text"
                              value={resolveNote}
                              onChange={(e) => setResolveNote(e.target.value)}
                              placeholder="e.g., Certificate signed & attested by court commissioner..."
                              className="w-full px-2 py-1 text-xs bg-white border border-[#eae4d9] rounded focus:outline-none focus:border-[#1b7a37]"
                              autoFocus
                            />
                            <div className="flex justify-end gap-1.5">
                              <button
                                onClick={() => setResolvePromptId(null)}
                                className="px-2 py-0.5 text-[10px] text-[#70685e] hover:bg-white rounded cursor-pointer"
                              >
                                Cancel
                              </button>
                              <button
                                onClick={(e) => handleResolve(alert.id, e)}
                                disabled={!resolveNote.trim() || actionLoadingId === alert.id}
                                className="px-2.5 py-0.5 text-[10px] font-semibold bg-[#1b7a37] text-white rounded hover:bg-[#15602b] disabled:opacity-50 cursor-pointer"
                              >
                                Sign Off & Resolve
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Footer */}
          {currentCaseId && (
            <div className="p-2.5 bg-[#faf7f2] border-t border-[#eae4d9] text-center">
              <button
                onClick={() => {
                  setIsOpen(false);
                  navigate(`/cases/${currentCaseId}/handover`);
                }}
                className="w-full py-1.5 text-xs font-semibold text-[#191410] bg-white border border-[#eae4d9] rounded-xl hover:bg-[#f0ebe1] transition-colors cursor-pointer shadow-2xs"
              >
                Open Shift Handover & Statutory Deadlines →
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

