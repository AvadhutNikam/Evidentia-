import React, { useState, useEffect } from 'react';
import { 
  UserCheck, ShieldCheck, AlertTriangle, CheckCircle2, 
  X, RefreshCw, Plus, Lock
} from 'lucide-react';
import { DecisionSignoff } from '../../types';
import { decisionQualityService } from '../../services';
import { useAuth } from '../../context/AuthContext';
import { cn } from '../../utils';

interface DecisionSignoffModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  onSignoffUpdated?: () => void;
}

export const DecisionSignoffModal: React.FC<DecisionSignoffModalProps> = ({
  isOpen,
  onClose,
  caseId,
  onSignoffUpdated,
}) => {
  const { user } = useAuth();
  const [signoffs, setSignoffs] = useState<DecisionSignoff[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedSignoff, setSelectedSignoff] = useState<DecisionSignoff | null>(null);

  // Review form state
  const [reviewNotes, setReviewNotes] = useState<string>('');
  const [isSubmittingReview, setIsSubmittingReview] = useState<boolean>(false);
  const [actionMessage, setActionMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // New Request Form state
  const [isRequestFormOpen, setIsRequestFormOpen] = useState<boolean>(false);
  const [newItemType, setNewItemType] = useState<string>('evidence_assessment');
  const [newItemId, setNewItemId] = useState<string>('');
  const [newItemSummary, setNewItemSummary] = useState<string>('');
  const [isSubmittingRequest, setIsSubmittingRequest] = useState<boolean>(false);

  const fetchSignoffs = async () => {
    try {
      setLoading(true);
      const list = await decisionQualityService.getSignoffs(caseId);
      setSignoffs(list);
      if (list.length > 0 && !selectedSignoff) {
        setSelectedSignoff(list[0]);
      }
    } catch (err) {
      console.error('Failed to load decision sign-offs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchSignoffs();
    }
  }, [isOpen, caseId]);

  const handleReview = async (approved: boolean) => {
    if (!selectedSignoff) return;
    if (!reviewNotes.trim()) {
      setActionMessage({ text: 'Please enter review notes explaining your decision.', type: 'error' });
      return;
    }

    try {
      setIsSubmittingReview(true);
      await decisionQualityService.reviewSignoff(caseId, selectedSignoff.id, {
        approved,
        review_notes: reviewNotes,
      });

      setActionMessage({
        text: `Sign-off ${approved ? 'APPROVED' : 'REJECTED'} successfully under Four-Eyes protocol.`,
        type: 'success',
      });
      setReviewNotes('');
      await fetchSignoffs();
      if (onSignoffUpdated) onSignoffUpdated();
    } catch (err: any) {
      setActionMessage({ text: err?.message || 'Failed to complete review.', type: 'error' });
    } finally {
      setIsSubmittingReview(false);
    }
  };

  const handleCreateRequest = async () => {
    if (!newItemId || !newItemSummary.trim()) {
      setActionMessage({ text: 'Please provide both Item ID and a descriptive summary.', type: 'error' });
      return;
    }

    try {
      setIsSubmittingRequest(true);
      await decisionQualityService.requestSignoff(caseId, {
        item_type: newItemType,
        item_id: Number(newItemId),
        item_summary: newItemSummary,
      });

      setActionMessage({ text: 'Sign-off request submitted to lead reviewers.', type: 'success' });
      setIsRequestFormOpen(false);
      setNewItemId('');
      setNewItemSummary('');
      await fetchSignoffs();
      if (onSignoffUpdated) onSignoffUpdated();
    } catch (err: any) {
      setActionMessage({ text: err?.message || 'Failed to submit request.', type: 'error' });
    } finally {
      setIsSubmittingRequest(false);
    }
  };

  if (!isOpen) return null;

  const currentUserId = user?.id ? Number(user.id) : null;
  const isMakerOfSelected = Boolean(
    selectedSignoff && currentUserId && selectedSignoff.maker_user_id === currentUserId
  );

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-4 overflow-y-auto">
      <div className="bg-white border border-[#eae4d9] rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-scaleUp text-[#191410]">
        
        {/* HEADER */}
        <div className="p-4 sm:p-5 bg-[#faf7f2] border-b border-[#eae4d9] flex items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-700">
              <UserCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm sm:text-base font-serif font-bold text-[#191410]">
                  Two-Analyst Sign-Offs (Four-Eyes Protocol)
                </h3>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-blue-50 text-blue-800 border border-blue-200">
                  Judicial Verification
                </span>
              </div>
              <p className="text-xs text-[#6e665d] mt-0.5">
                Enforces independent second reviewer verification on critical classifications, suspect clearing factors, and final chargesheet drafts.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsRequestFormOpen(!isRequestFormOpen)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#d93829] hover:bg-[#bf2b1d] text-white font-semibold text-xs shadow-xs transition-all cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Request Sign-off</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-xl hover:bg-[#eae4d9]/50 text-[#6e665d] hover:text-[#191410] transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Action Alert Banner */}
        {actionMessage && (
          <div className={cn(
            "p-3 text-xs flex items-center justify-between gap-2 font-mono border-b shrink-0",
            actionMessage.type === 'success'
              ? "bg-emerald-50 border-emerald-200 text-emerald-900"
              : "bg-red-50 border-red-200 text-red-900"
          )}>
            <div className="flex items-center gap-2">
              {actionMessage.type === 'success' ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <AlertTriangle className="w-4 h-4 text-red-600" />}
              <span>{actionMessage.text}</span>
            </div>
            <button onClick={() => setActionMessage(null)} className="text-[10px] hover:underline uppercase text-[#6e665d]">✕</button>
          </div>
        )}

        {/* REQUEST SIGN-OFF FORM (COLLAPSIBLE) */}
        {isRequestFormOpen && (
          <div className="p-4 bg-[#faf7f2] border-b border-[#eae4d9] space-y-3 shrink-0 animate-fadeIn text-xs">
            <div className="font-bold text-[#191410] uppercase tracking-wider flex items-center gap-2">
              <Plus className="w-3.5 h-3.5 text-[#d93829]" />
              Submit Item for Second Reviewer Scrutiny
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="text-[10px] font-mono text-[#6e665d] uppercase block mb-1">Item Category</label>
                <select
                  value={newItemType}
                  onChange={(e) => setNewItemType(e.target.value)}
                  className="w-full p-2 rounded-xl bg-white border border-[#eae4d9] text-[#191410] text-xs font-mono focus:outline-none focus:border-[#d93829]"
                >
                  <option value="evidence_assessment">Evidence Assessment / Override</option>
                  <option value="chargesheet_draft">Chargesheet Draft (Sec 193 BNSS / 173 CrPC)</option>
                  <option value="final_report">Final Investigative Docket</option>
                  <option value="hypothesis_ranking">Primary Suspect Conviction Ranking</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] font-mono text-[#6e665d] uppercase block mb-1">Target Item ID</label>
                <input
                  type="number"
                  placeholder="e.g. 1"
                  value={newItemId}
                  onChange={(e) => setNewItemId(e.target.value)}
                  className="w-full p-2 rounded-xl bg-white border border-[#eae4d9] text-[#191410] text-xs font-mono focus:outline-none focus:border-[#d93829]"
                />
              </div>

              <div>
                <label className="text-[10px] font-mono text-[#6e665d] uppercase block mb-1">Verification Summary / Notes</label>
                <input
                  type="text"
                  placeholder="e.g. Override classification to strongly consistent based on DNA electropherogram"
                  value={newItemSummary}
                  onChange={(e) => setNewItemSummary(e.target.value)}
                  className="w-full p-2 rounded-xl bg-white border border-[#eae4d9] text-[#191410] text-xs focus:outline-none focus:border-[#d93829]"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-1">
              <button
                onClick={() => setIsRequestFormOpen(false)}
                className="px-3 py-1.5 rounded-xl bg-white border border-[#eae4d9] text-[#6e665d] hover:text-[#191410] cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateRequest}
                disabled={isSubmittingRequest}
                className="px-4 py-1.5 rounded-xl bg-[#d93829] hover:bg-[#bf2b1d] text-white font-semibold flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                {isSubmittingRequest && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                <span>Submit Request</span>
              </button>
            </div>
          </div>
        )}

        {/* MAIN BODY: SPLIT VIEW (LIST ON LEFT, DETAILS & REVIEW FORM ON RIGHT) */}
        <div className="flex-1 grid grid-cols-1 md:grid-cols-12 overflow-hidden">
          {/* LEFT: LIST OF SIGNOFFS (COL-5) */}
          <div className="md:col-span-5 border-r border-[#eae4d9] overflow-y-auto p-3 space-y-2.5 bg-[#faf7f2]/50">
            <div className="text-[11px] font-mono text-[#6e665d] flex items-center justify-between pb-1 border-b border-[#eae4d9]">
              <span>Sign-off Requests ({signoffs.length})</span>
              <span>Maker-Checker</span>
            </div>

            {loading ? (
              <div className="py-12 flex flex-col items-center justify-center gap-2 text-[#d93829]">
                <RefreshCw className="w-6 h-6 animate-spin" />
                <span className="text-[11px] font-mono text-[#6e665d]">Loading verification records...</span>
              </div>
            ) : signoffs.length === 0 ? (
              <div className="p-6 text-center text-[#8c8276] text-xs font-mono">
                No sign-off records found for this case docket.
              </div>
            ) : (
              signoffs.map((s) => {
                const isSelected = selectedSignoff?.id === s.id;
                return (
                  <div
                    key={s.id}
                    onClick={() => setSelectedSignoff(s)}
                    className={cn(
                      "p-3 rounded-xl border transition-all cursor-pointer space-y-1.5 shadow-xs",
                      isSelected
                        ? "bg-white border-[#d93829] shadow-sm"
                        : "bg-white border-[#eae4d9] hover:border-[#eae4d9]"
                    )}
                  >
                    <div className="flex items-center justify-between gap-1 text-[10px] font-mono">
                      <span className="font-bold text-[#191410] uppercase">{s.item_type.replace('_', ' ')} #{s.item_id}</span>
                      <span className={cn(
                        "px-2 py-0.5 rounded-full uppercase font-bold text-[9px] border",
                        s.status === 'approved' && "bg-emerald-50 text-emerald-800 border-emerald-200",
                        s.status === 'rejected' && "bg-red-50 text-red-800 border-red-200",
                        s.status === 'pending' && "bg-amber-50 text-amber-800 border-amber-200"
                      )}>
                        {s.status}
                      </span>
                    </div>

                    <p className="text-xs text-[#191410] line-clamp-2 font-sans">
                      {s.item_summary}
                    </p>

                    <div className="text-[10px] font-mono text-[#6e665d] flex items-center justify-between pt-1 border-t border-[#eae4d9]">
                      <span>Maker: {s.maker_name}</span>
                      <span>{new Date(s.requested_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* RIGHT: SELECTED SIGNOFF INSPECTION & REVIEW ACTIONS (COL-7) */}
          <div className="md:col-span-7 overflow-y-auto p-4 sm:p-5 space-y-4">
            {selectedSignoff ? (
              <div className="space-y-4">
                {/* Details Card */}
                <div className="p-4 rounded-xl border border-[#eae4d9] bg-white space-y-3 shadow-xs">
                  <div className="flex items-center justify-between border-b border-[#eae4d9] pb-2">
                    <div>
                      <span className="text-[10px] font-mono text-[#6e665d] uppercase">Verification Request #{selectedSignoff.id}</span>
                      <h4 className="text-sm font-bold text-[#191410] uppercase tracking-wider">
                        {selectedSignoff.item_type.replace('_', ' ')} (ID: #{selectedSignoff.item_id})
                      </h4>
                    </div>
                    <span className={cn(
                      "px-2.5 py-1 rounded-full text-xs font-mono font-bold uppercase border",
                      selectedSignoff.status === 'approved' && "bg-emerald-50 text-emerald-800 border-emerald-200",
                      selectedSignoff.status === 'rejected' && "bg-red-50 text-red-800 border-red-200",
                      selectedSignoff.status === 'pending' && "bg-amber-50 text-amber-800 border-amber-200"
                    )}>
                      {selectedSignoff.status}
                    </span>
                  </div>

                  <div className="space-y-1">
                    <div className="text-[10px] font-mono text-[#6e665d] uppercase">Summary / Ground:</div>
                    <p className="text-xs text-[#191410] font-sans leading-relaxed">
                      {selectedSignoff.item_summary}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-xs font-mono pt-2 border-t border-[#eae4d9] text-[#6e665d]">
                    <div>
                      <span className="text-[10px] uppercase block">Submitted By (Maker):</span>
                      <span className="text-[#191410] font-semibold">{selectedSignoff.maker_name}</span>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase block">Submission Date:</span>
                      <span className="text-[#191410]">{new Date(selectedSignoff.requested_at).toLocaleString()}</span>
                    </div>
                    {selectedSignoff.checker_name && (
                      <>
                        <div>
                          <span className="text-[10px] uppercase block">Reviewed By (Checker):</span>
                          <span className="text-emerald-700 font-semibold">{selectedSignoff.checker_name} ({selectedSignoff.checker_role})</span>
                        </div>
                        <div>
                          <span className="text-[10px] uppercase block">Decision Timestamp:</span>
                          <span className="text-[#191410]">{selectedSignoff.reviewed_at ? new Date(selectedSignoff.reviewed_at).toLocaleString() : 'N/A'}</span>
                        </div>
                      </>
                    )}
                  </div>

                  {selectedSignoff.review_notes && (
                    <div className="p-3 rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-xs space-y-1">
                      <div className="text-[10px] font-mono text-[#6e665d] uppercase font-bold">Reviewer's Formal Notes:</div>
                      <p className="text-[#191410] italic font-sans">{selectedSignoff.review_notes}</p>
                    </div>
                  )}
                </div>

                {/* REVIEW ACTION PANEL (ONLY IF PENDING) */}
                {selectedSignoff.status === 'pending' ? (
                  <div className="p-4 rounded-xl border border-[#eae4d9] bg-[#faf7f2] space-y-3">
                    <div className="text-xs font-bold text-[#191410] uppercase tracking-wider flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-600" />
                      Execute Second Reviewer Determination
                    </div>

                    {isMakerOfSelected ? (
                      /* FOUR-EYES WARNING: MAKER CANNOT SIGN OFF */
                      <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs font-mono flex items-start gap-2">
                        <Lock className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                        <div>
                          <span className="font-bold">Four-Eyes Protocol Enforced: </span>
                          You drafted/submitted this classification. An independent second investigator or lead reviewer must execute the sign-off.
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="space-y-1">
                          <label className="text-[10px] font-mono text-[#6e665d] uppercase block">
                            Scrutiny Justification / Legal Review Notes:
                          </label>
                          <textarea
                            rows={3}
                            placeholder="State evidence cross-checked, verified electropherograms, or reason for clearance..."
                            value={reviewNotes}
                            onChange={(e) => setReviewNotes(e.target.value)}
                            className="w-full p-2.5 rounded-xl bg-white border border-[#eae4d9] text-[#191410] text-xs font-sans focus:outline-none focus:border-[#d93829]"
                          />
                        </div>

                        <div className="flex items-center justify-end gap-2.5 pt-1">
                          <button
                            onClick={() => handleReview(false)}
                            disabled={isSubmittingReview || !reviewNotes.trim()}
                            className="px-4 py-2 rounded-xl bg-red-50 hover:bg-red-100 border border-red-200 text-red-700 disabled:opacity-50 font-semibold text-xs transition-all cursor-pointer"
                          >
                            Reject Classification
                          </button>
                          <button
                            onClick={() => handleReview(true)}
                            disabled={isSubmittingReview || !reviewNotes.trim()}
                            className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-semibold text-xs shadow-xs transition-all flex items-center gap-1.5 cursor-pointer"
                          >
                            {isSubmittingReview && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                            <span>Approve & Certify</span>
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                ) : (
                  <div className="p-4 rounded-xl border border-emerald-200 bg-emerald-50 text-xs font-mono text-emerald-800 flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Four-eyes certification finalized. Recorded permanently into the Merkle audit trail.</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-12 text-center text-[#8c8276] text-xs font-mono">
                Select a verification request from the list to inspect details or execute sign-off.
              </div>
            )}
          </div>
        </div>

        {/* FOOTER */}
        <div className="p-3 bg-[#faf7f2] border-t border-[#eae4d9] flex items-center justify-between text-xs font-mono text-[#6e665d] shrink-0">
          <span>Indian Criminal Procedure & Forensic Quality Assurance Standard</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl bg-white hover:bg-[#eae4d9]/50 border border-[#eae4d9] text-[#191410] text-xs font-semibold cursor-pointer shadow-xs"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
