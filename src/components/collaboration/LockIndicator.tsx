import React, { useState } from 'react';
import { useCollaboration } from '../../context/CollaborationContext';
import { useAuth } from '../../context/AuthContext';
import { Lock, Unlock, ShieldAlert, KeyRound } from 'lucide-react';

interface LockIndicatorProps {
  itemType: string;
  itemId: string | number;
  className?: string;
  onOverrideSuccess?: () => void;
}

export function LockIndicator({ itemType, itemId, className = '', onOverrideSuccess }: LockIndicatorProps) {
  const { getLockForItem, isItemLockedByOther, overrideLock } = useCollaboration();
  const { user, role } = useAuth();
  const [isOverriding, setIsOverriding] = useState(false);
  const [overrideReason, setOverrideReason] = useState('');
  const [showOverridePrompt, setShowOverridePrompt] = useState(false);

  const lock = getLockForItem(itemType, String(itemId));
  if (!lock) return null;

  const isHeldByMe = user && lock.user_id === user.id;
  const isLeadOrAdmin = role === 'admin' || role === 'lead_investigator';

  const handleBreakLock = async () => {
    if (!overrideReason.trim()) return;
    setIsOverriding(true);
    try {
      const ok = await overrideLock(itemType, String(itemId), overrideReason);
      if (ok) {
        setShowOverridePrompt(false);
        setOverrideReason('');
        if (onOverrideSuccess) onOverrideSuccess();
      }
    } finally {
      setIsOverriding(false);
    }
  };

  if (isHeldByMe) {
    return (
      <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#ebf4fd] border border-[#bcdbf7] text-[#1b64b8] text-xs font-medium ${className}`}>
        <Unlock className="w-3.5 h-3.5" />
        <span>You hold the edit lock (renews as you type)</span>
      </div>
    );
  }

  return (
    <div className={`flex flex-col gap-2 p-3 rounded-xl bg-[#fff8ea] border border-[#f4c153] text-[#8a5b00] text-xs ${className}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Lock className="w-4 h-4 text-[#d93829] shrink-0" />
          <span>
            <strong>{lock.user_name}</strong> ({lock.user_role}) is currently editing this {itemType}.
          </span>
        </div>

        {isLeadOrAdmin && !showOverridePrompt && (
          <button
            onClick={() => setShowOverridePrompt(true)}
            className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-white border border-[#f4c153] text-[#8a5b00] hover:bg-[#fff2d4] font-semibold text-[11px] transition-colors cursor-pointer shadow-2xs"
          >
            <KeyRound className="w-3 h-3 text-[#d93829]" />
            <span>Break Lock (Override)</span>
          </button>
        )}
      </div>

      {/* Admin Override Reason Input */}
      {showOverridePrompt && (
        <div className="pt-2 border-t border-[#f4c153]/50 flex flex-col sm:flex-row items-center gap-2">
          <input
            type="text"
            placeholder="Mandatory administrative justification..."
            value={overrideReason}
            onChange={(e) => setOverrideReason(e.target.value)}
            className="flex-1 bg-white border border-[#f4c153] rounded-lg px-2.5 py-1 text-xs text-[#191410] placeholder:text-[#8c8276] focus:outline-none focus:ring-1 focus:ring-[#d93829]"
          />
          <div className="flex items-center gap-1.5 self-end sm:self-auto">
            <button
              onClick={handleBreakLock}
              disabled={isOverriding || !overrideReason.trim()}
              className="px-3 py-1 rounded-lg bg-[#d93829] text-white font-semibold text-xs hover:bg-[#b82a1c] disabled:opacity-50 transition-colors cursor-pointer"
            >
              {isOverriding ? 'Breaking...' : 'Confirm Override'}
            </button>
            <button
              onClick={() => setShowOverridePrompt(false)}
              className="px-2.5 py-1 rounded-lg text-xs text-[#70685e] hover:bg-[#ffeec7] transition-colors cursor-pointer"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

