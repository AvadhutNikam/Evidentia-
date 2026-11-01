import React, { useState } from 'react';
import { useCollaboration } from '../../context/CollaborationContext';
import { Users, Activity, Wifi, WifiOff } from 'lucide-react';

export function PresenceAvatars() {
  const collab = useCollaboration();
  const [hoveredUser, setHoveredUser] = useState<number | null>(null);

  if (!collab || !collab.caseId) return null;

  const { activeUsers, isOffline, isActivityFeedOpen, setIsActivityFeedOpen, recentEvents } = collab;

  const getRoleColors = (role: string) => {
    switch (role?.toLowerCase()) {
      case 'admin':
        return { bg: 'bg-[#d93829]', border: 'border-[#d93829]', text: 'text-white', badge: 'bg-[#fdeee9] text-[#d93829]' };
      case 'lead_investigator':
        return { bg: 'bg-[#1b64b8]', border: 'border-[#1b64b8]', text: 'text-white', badge: 'bg-[#ebf4fd] text-[#1b64b8]' };
      case 'analyst':
        return { bg: 'bg-[#6b38fb]', border: 'border-[#6b38fb]', text: 'text-white', badge: 'bg-[#f0eaff] text-[#6b38fb]' };
      case 'reviewer':
        return { bg: 'bg-[#1b7a37]', border: 'border-[#1b7a37]', text: 'text-white', badge: 'bg-[#ebf7ee] text-[#1b7a37]' };
      default:
        return { bg: 'bg-[#8c8276]', border: 'border-[#8c8276]', text: 'text-white', badge: 'bg-[#f4efe6] text-[#70685e]' };
    }
  };

  const getInitials = (name: string) => {
    if (!name) return 'U';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    return name.slice(0, 2).toUpperCase();
  };

  const displayUsers = activeUsers.slice(0, 4);
  const overflowCount = Math.max(0, activeUsers.length - 4);

  return (
    <div className="flex items-center gap-3">
      {/* Live Stream Connectivity Status */}
      <div 
        className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-mono font-medium border transition-all cursor-help"
        title={isOffline ? "SSE live stream interrupted. Attempting to reconnect..." : "Connected to live case collaboration stream."}
      >
        {isOffline ? (
          <>
            <WifiOff className="w-3 h-3 text-[#d93829] animate-pulse" />
            <span className="text-[#d93829] font-bold">Reconnecting</span>
          </>
        ) : (
          <>
            <span className="w-2 h-2 rounded-full bg-[#22c55e] animate-pulse" />
            <span className="text-[#1b7a37] font-semibold">Live</span>
          </>
        )}
      </div>

      {/* Active User Avatars */}
      {activeUsers.length > 0 && (
        <div className="flex items-center -space-x-2">
          {displayUsers.map((u) => {
            const colors = getRoleColors(u.user_role);
            const isHovered = hoveredUser === u.user_id;

            return (
              <div 
                key={u.user_id} 
                className="relative group cursor-pointer"
                onMouseEnter={() => setHoveredUser(u.user_id)}
                onMouseLeave={() => setHoveredUser(null)}
              >
                <div 
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold ring-2 ring-white shadow-xs transition-transform hover:scale-110 hover:z-20 ${colors.bg} ${colors.text}`}
                  title={`${u.user_name} (${u.user_role}) - ${u.current_location}`}
                >
                  {getInitials(u.user_name)}
                </div>

                {/* Hover Tooltip Card */}
                {isHovered && (
                  <div className="absolute right-0 top-9 w-52 bg-white rounded-xl shadow-xl border border-[#eae4d9] p-3 z-50 animate-fadeIn text-left pointer-events-none">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold text-[#191410] truncate">{u.user_name}</span>
                      <span className="w-2 h-2 rounded-full bg-[#22c55e]" />
                    </div>
                    <div className="flex items-center gap-1.5 mb-2">
                      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${colors.badge}`}>
                        {u.user_role?.replace('_', ' ')}
                      </span>
                      <span className="text-[10px] text-[#70685e]">Active now</span>
                    </div>
                    <div className="pt-2 border-t border-[#f4efe6] text-[11px] text-[#554e45]">
                      <span className="text-[#8c8276] text-[10px] block">Currently viewing:</span>
                      <span className="font-medium text-[#191410] block truncate">{u.current_location}</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {overflowCount > 0 && (
            <div 
              className="w-7 h-7 rounded-full bg-[#f4efe6] text-[#70685e] border-2 border-white flex items-center justify-center text-[10px] font-bold shadow-xs cursor-pointer hover:bg-[#eae4d9]"
              title={`${overflowCount} more investigator${overflowCount > 1 ? 's' : ''} in case`}
            >
              +{overflowCount}
            </div>
          )}
        </div>
      )}

      {/* Live Activity Feed Button */}
      <button
        onClick={() => setIsActivityFeedOpen(!isActivityFeedOpen)}
        className={`relative flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-xs font-medium border transition-colors cursor-pointer ${
          isActivityFeedOpen
            ? 'bg-[#191410] text-white border-[#191410]'
            : 'bg-white border-[#eae4d9] text-[#70685e] hover:text-[#191410] hover:border-[#8c8276]'
        }`}
        title="Open Live Collaboration Feed"
      >
        <Activity className="w-3.5 h-3.5 text-[#d93829]" />
        <span className="hidden md:inline text-[11px] font-semibold">Activity</span>
        {recentEvents.length > 0 && (
          <span className="w-4 h-4 rounded-full bg-[#d93829] text-white text-[9px] font-bold flex items-center justify-center">
            {Math.min(99, recentEvents.length)}
          </span>
        )}
      </button>
    </div>
  );
}
