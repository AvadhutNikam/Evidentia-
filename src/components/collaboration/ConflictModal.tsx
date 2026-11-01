import React, { useState } from 'react';
import { useCollaboration } from '../../context/CollaborationContext';
import { AlertTriangle, Copy, Check, RefreshCw, ArrowRight, ShieldAlert } from 'lucide-react';

interface ConflictModalProps {
  onResolveOverwrite?: (latestVersion: number) => void;
  onResolveReload?: () => void;
}

export function ConflictModal({ onResolveOverwrite, onResolveReload }: ConflictModalProps) {
  const { conflictModalData, setConflictModalData } = useCollaboration();
  const [copied, setCopied] = useState(false);

  if (!conflictModalData) return null;

  const handleCopyDraft = () => {
    try {
      navigator.clipboard.writeText(JSON.stringify(conflictModalData.current_data, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.warn('Clipboard write failed:', err);
    }
  };

  const handleClose = () => {
    setConflictModalData(null);
  };

  const handleReload = () => {
    handleClose();
    if (onResolveReload) {
      onResolveReload();
    } else {
      window.location.reload();
    }
  };

  const handleOverwrite = () => {
    const nextVer = conflictModalData.current_version;
    handleClose();
    if (onResolveOverwrite) {
      onResolveOverwrite(nextVer);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-xs z-50 flex items-center justify-center p-4 animate-fadeIn">
      <div className="bg-white rounded-2xl max-w-lg w-full border border-[#eae4d9] shadow-2xl overflow-hidden flex flex-col">
        {/* Header Alert */}
        <div className="bg-[#fdeee9] border-b border-[#f9c7be] p-5 flex items-start gap-3.5">
          <div className="p-2 rounded-xl bg-[#d93829] text-white shrink-0 mt-0.5 shadow-sm">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h3 className="font-serif font-bold text-base text-[#961c10]">
                Concurrent Edit Conflict (HTTP 409)
              </h3>
            </div>
            <p className="text-xs text-[#b82a1c] mt-1 leading-relaxed">
              Another investigator submitted edits to this {conflictModalData.item_type} while you were drafting changes. 
              To prevent accidental overwrite, your save was rejected by optimistic concurrency control.
            </p>
          </div>
        </div>

        {/* Conflict Version Comparison */}
        <div className="p-5 space-y-4">
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-[#faf7f2] border border-[#eae4d9]">
              <div className="text-[10px] font-mono uppercase tracking-wider text-[#8c8276] mb-1">
                Your Draft Version
              </div>
              <div className="font-bold text-sm text-[#191410]">
                v{conflictModalData.submitted_version ?? 1}
              </div>
              <div className="text-[11px] text-[#70685e] mt-1">
                Contains your unsaved edits
              </div>
            </div>

            <div className="p-3 rounded-xl bg-[#ebf7ee] border border-[#b2e2be]">
              <div className="text-[10px] font-mono uppercase tracking-wider text-[#1b7a37] mb-1">
                Current Server Version
              </div>
              <div className="font-bold text-sm text-[#1b7a37]">
                v{conflictModalData.current_version}
              </div>
              <div className="text-[11px] text-[#14532d] mt-1">
                Committed by peer investigator
              </div>
            </div>
          </div>

          {/* Current Server Snapshot preview */}
          {conflictModalData.current_data && (
            <div>
              <div className="text-[11px] font-bold text-[#191410] mb-1.5 flex items-center justify-between">
                <span>Current Server Values:</span>
                <button
                  onClick={handleCopyDraft}
                  className="flex items-center gap-1 text-[10px] font-mono text-[#70685e] hover:text-[#191410] cursor-pointer"
                >
                  {copied ? <Check className="w-3 h-3 text-[#22c55e]" /> : <Copy className="w-3 h-3" />}
                  <span>{copied ? 'Copied' : 'Copy Data'}</span>
                </button>
              </div>
              <pre className="p-3 bg-[#faf7f2] rounded-xl border border-[#eae4d9] text-[10px] font-mono text-[#554e45] max-h-36 overflow-y-auto leading-relaxed">
                {JSON.stringify(conflictModalData.current_data, null, 2)}
              </pre>
            </div>
          )}

          <div className="flex items-center gap-2 p-2.5 rounded-lg bg-[#fff8ea] border border-[#f4c153] text-[11px] text-[#8a5b00]">
            <ShieldAlert className="w-4 h-4 shrink-0" />
            <span>All rejected conflicts are permanently audited in the tamper-evident Merkle ledger.</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="p-4 bg-[#faf7f2] border-t border-[#eae4d9] flex items-center justify-end gap-2.5">
          <button
            onClick={handleClose}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold text-[#70685e] hover:bg-[#eae4d9] transition-colors cursor-pointer"
          >
            Cancel
          </button>
          
          <button
            onClick={handleReload}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-white border border-[#eae4d9] text-[#191410] hover:bg-[#f4efe6] transition-colors shadow-2xs cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5 text-[#1b64b8]" />
            <span>Load Server Version</span>
          </button>

          {onResolveOverwrite && (
            <button
              onClick={handleOverwrite}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-[#d93829] text-white hover:bg-[#b82a1c] transition-colors shadow-xs cursor-pointer"
            >
              <span>Overwrite as v{conflictModalData.current_version + 1}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

