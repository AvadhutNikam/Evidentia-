import React from 'react';
import { useCollaboration } from '../../context/CollaborationContext';
import { PresenceUser, CollaborationEvent } from '../../types';
import { X, Activity, Edit3, Lock, Unlock, UserCheck, RefreshCw, CheckCircle, ShieldAlert } from 'lucide-react';

export function ActivityFeedDrawer() {
  const { isActivityFeedOpen, setIsActivityFeedOpen, recentEvents, activeUsers } = useCollaboration();

  if (!isActivityFeedOpen) return null;

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'item.changed':
        return <Edit3 className="w-3.5 h-3.5 text-[#1b64b8]" />;
      case 'lock.acquired':
        return <Lock className="w-3.5 h-3.5 text-[#d93829]" />;
      case 'lock.released':
        return <Unlock className="w-3.5 h-3.5 text-[#22c55e]" />;
      case 'presence.joined':
      case 'presence.moved':
        return <UserCheck className="w-3.5 h-3.5 text-[#6b38fb]" />;
      case 'scores.updated':
        return <RefreshCw className="w-3.5 h-3.5 text-[#8a5b00]" />;
      case 'job.progress':
        return <CheckCircle className="w-3.5 h-3.5 text-[#1b7a37]" />;
      default:
        return <Activity className="w-3.5 h-3.5 text-[#70685e]" />;
    }
  };

  const formatTime = (isoString?: string) => {
    if (!isoString) return 'just now';
    try {
      const date = new Date(isoString);
      const diffSeconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
      if (diffSeconds < 60) return `${diffSeconds}s ago`;
      if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`;
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return 'recent';
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 w-80 sm:w-96 bg-white border-l border-[#eae4d9] shadow-2xl z-50 flex flex-col animate-slideLeft">
      {/* Header */}
      <div className="px-5 py-4 border-b border-[#eae4d9] flex items-center justify-between bg-[#faf7f2]">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-[#d93829]" />
          <h2 className="font-serif font-bold text-sm text-[#191410]">Live Collaboration Feed</h2>
        </div>
        <button
          onClick={() => setIsActivityFeedOpen(false)}
          className="p-1 rounded-full text-[#70685e] hover:text-[#191410] hover:bg-[#eae4d9] transition-colors cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Online Investigators Section */}
      <div className="px-5 py-3 border-b border-[#eae4d9] bg-[#faf7f2]/50">
        <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#8c8276] mb-2 flex items-center justify-between">
          <span>Active in Case Now</span>
          <span className="text-[#22c55e]">{activeUsers.length} online</span>
        </div>
        <div className="flex flex-col gap-1.5">
          {activeUsers.map((u: PresenceUser) => (
            <div key={u.user_id} className="flex items-center justify-between text-xs bg-white border border-[#eae4d9] rounded-lg px-2.5 py-1.5 shadow-2xs">
              <div className="flex items-center gap-2 truncate">
                <span className="w-2 h-2 rounded-full bg-[#22c55e]" />
                <span className="font-semibold text-[#191410] truncate">{u.user_name}</span>
                <span className="text-[9px] font-mono px-1 rounded bg-[#f4efe6] text-[#70685e]">
                  {u.user_role}
                </span>
              </div>
              <span className="text-[10px] text-[#8c8276] ml-2 truncate max-w-[100px]" title={u.current_location}>
                {u.current_location}
              </span>
            </div>
          ))}
          {activeUsers.length === 0 && (
            <div className="text-xs text-[#8c8276] italic py-1">No other investigators currently present.</div>
          )}
        </div>
      </div>

      {/* Live Activity Stream */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#8c8276]">
          Recent Actions & Changes
        </div>

        {recentEvents.map((ev: CollaborationEvent, idx: number) => (
          <div 
            key={`${ev.id}-${idx}`}
            className="p-3 rounded-xl border border-[#eae4d9] bg-[#faf7f2]/30 hover:bg-[#faf7f2] transition-colors flex items-start gap-3"
          >
            <div className="mt-0.5 p-1.5 rounded-lg bg-white border border-[#eae4d9] shadow-2xs shrink-0">
              {getEventIcon(ev.event_type)}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-1 mb-0.5">
                <span className="text-xs font-semibold text-[#191410] truncate">
                  {ev.user_name || 'System'}
                </span>
                <span className="text-[10px] font-mono text-[#8c8276] shrink-0">
                  {formatTime(ev.created_at || ev.timestamp)}
                </span>
              </div>
              <p className="text-xs text-[#554e45] leading-snug break-words">
                {ev.summary}
              </p>
              {ev.is_restricted && (
                <div className="mt-1 flex items-center gap-1 text-[9px] font-mono text-[#8a5b00]">
                  <ShieldAlert className="w-3 h-3" />
                  <span>Role-restricted record update</span>
                </div>
              )}
            </div>
          </div>
        ))}

        {recentEvents.length === 0 && (
          <div className="text-center py-8 text-xs text-[#8c8276] italic">
            Waiting for real-time collaboration events...
          </div>
        )}
      </div>

      {/* Footer Notice */}
      <div className="p-3 border-t border-[#eae4d9] bg-[#faf7f2] text-[10px] text-[#8c8276] text-center font-mono">
        Rides on SSE live stream with Merkle transactional ledger
      </div>
    </div>
  );
}
