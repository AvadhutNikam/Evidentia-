import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Link2,
  Phone,
  Car,
  MapPin,
  User,
  Terminal,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  ExternalLink,
  ChevronRight,
  Sparkles,
  Lock,
  X,
  MessageSquare,
  AlertCircle
} from 'lucide-react';
import { crossCaseService, jobService } from '../../services';
import { ConnectedCasesSummary, ConnectedCaseGroup, MatchingFeatureDetail } from '../../types';

interface PossiblyConnectedCasesBadgeProps {
  caseId: string | number;
  className?: string;
  compact?: boolean;
}

export function PossiblyConnectedCasesBadge({
  caseId,
  className = '',
  compact = false
}: PossiblyConnectedCasesBadgeProps) {
  const [summary, setSummary] = useState<ConnectedCasesSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [reviewingLinkId, setReviewingLinkId] = useState<number | null>(null);
  const [reviewNotes, setReviewNotes] = useState<string>('');
  const [actionError, setActionError] = useState<string | null>(null);

  const loadData = async () => {
    if (!caseId) return;
    try {
      setLoading(true);
      const data = await crossCaseService.getConnectedCases(caseId);
      setSummary(data);
    } catch (err) {
      console.debug('No cross-case connections or access restricted:', err);
      setSummary(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [caseId]);

  // Subscribe to real-time events for live badge update
  useEffect(() => {
    if (!caseId) return;
    const unsubscribe = jobService.subscribeCaseEvents(caseId, (event: any) => {
      if (
        event?.event_type === 'cross_case_candidate_flagged' ||
        event?.event_type === 'alert.created' ||
        event?.event_type === 'item.changed'
      ) {
        loadData();
      }
    });
    return () => {
      if (unsubscribe) unsubscribe();
    };
  }, [caseId]);

  const handleReview = async (linkId: number, status: 'confirmed' | 'rejected') => {
    if (!caseId) return;
    try {
      setActionError(null);
      await crossCaseService.reviewLink(caseId, linkId, status, reviewNotes || undefined);
      setReviewingLinkId(null);
      setReviewNotes('');
      await loadData();
    } catch (err: any) {
      setActionError(err?.message || 'Permission denied: You must have authorization to access both cases to review linkages.');
    }
  };

  if (!summary || summary.total_connected_cases === 0) {
    return null;
  }

  const hasPending = summary.pending_candidates_count > 0;
  const allFeatures = Array.from(
    new Set(summary.connected_cases.flatMap(c => c.feature_types))
  );

  const getFeatureIcon = (type: string) => {
    const t = type.toLowerCase();
    if (t.includes('phone')) return <Phone className="w-3 h-3 text-emerald-600" />;
    if (t.includes('vehicle') || t.includes('car')) return <Car className="w-3 h-3 text-blue-600" />;
    if (t.includes('address') || t.includes('location')) return <MapPin className="w-3 h-3 text-amber-600" />;
    if (t.includes('digital')) return <Terminal className="w-3 h-3 text-cyan-600" />;
    return <User className="w-3 h-3 text-purple-600" />;
  };

  return (
    <>
      {/* Badge Button */}
      <button
        onClick={() => setModalOpen(true)}
        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold transition-all cursor-pointer shadow-2xs ${
          hasPending
            ? 'bg-rose-50 hover:bg-rose-100 border border-rose-300 text-rose-900 animate-pulse'
            : 'bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 text-emerald-900'
        } ${className}`}
        title="Real-time Cross-Case Candidate Matching: Click to view matching features and confirm/reject linkages"
      >
        <span className="relative flex h-2 w-2">
          {hasPending && (
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75" />
          )}
          <span className={`relative inline-flex rounded-full h-2 w-2 ${hasPending ? 'bg-rose-600' : 'bg-emerald-600'}`} />
        </span>

        <Link2 className="w-3.5 h-3.5" />

        <span>
          {summary.total_connected_cases} {summary.total_connected_cases === 1 ? 'Possibly Connected Case' : 'Possibly Connected Cases'}
        </span>

        {!compact && (
          <div className="flex items-center gap-1 pl-1 border-l border-rose-200">
            {allFeatures.map((ft, idx) => (
              <span key={idx} title={`Matched ${ft}`}>
                {getFeatureIcon(ft)}
              </span>
            ))}
          </div>
        )}

        {hasPending && (
          <span className="bg-rose-200/80 text-rose-900 px-1.5 py-0.2 rounded-full text-[10px] font-mono">
            {summary.pending_candidates_count} Pending
          </span>
        )}
      </button>

      {/* Modal / Slide-Over Drawer */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full border border-[#eae4d9] shadow-2xl overflow-hidden flex flex-col max-h-[88vh]">
            {/* Header */}
            <div className="p-5 border-b border-[#f0ebe1] flex items-center justify-between bg-[#faf7f2]">
              <div className="flex items-center gap-2.5">
                <span className="p-2 rounded-xl bg-rose-100 text-rose-800">
                  <Link2 className="w-5 h-5" />
                </span>
                <div>
                  <h3 className="text-base font-serif font-bold text-[#191410]">
                    Possibly Connected Cases
                  </h3>
                  <p className="text-xs text-[#6e665d] mt-0.5">
                    Real-time cross-case matcher detected matching identifiers with cases you are authorized to access.
                  </p>
                </div>
              </div>

              <button
                onClick={() => setModalOpen(false)}
                className="p-1 rounded-lg text-[#6e665d] hover:bg-[#eae4d9] transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Non-Merging Safeguard Alert Banner */}
            <div className="px-5 py-3 bg-amber-50/80 border-b border-amber-200 flex items-start gap-2.5 text-xs text-amber-900 leading-relaxed">
              <ShieldAlert className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">Human Confirmation Required (Never Auto-Merged):</span> Candidate links are flagged for review. Cases and entities remain strictly unmerged unless an authorized investigator confirms the connection.
              </div>
            </div>

            {actionError && (
              <div className="px-5 py-2.5 bg-rose-50 border-b border-rose-200 text-xs text-rose-900 flex items-center justify-between">
                <span>{actionError}</span>
                <button onClick={() => setActionError(null)} className="font-bold">✕</button>
              </div>
            )}

            {/* Connected Cases List */}
            <div className="p-5 overflow-y-auto space-y-4 flex-1">
              {summary.connected_cases.map((group) => (
                <div
                  key={group.linked_case_id}
                  className="bg-white border border-[#eae4d9] hover:border-stone-400 rounded-xl p-4 shadow-2xs space-y-3 transition-all"
                >
                  {/* Case Title and Status */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-[#f0ebe1]">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-[#6e665d] font-mono">
                          Case #{group.linked_case_id}
                        </span>
                        <span className="w-1.5 h-1.5 rounded-full bg-stone-400" />
                        <span className="text-xs font-semibold text-emerald-800">
                          {Math.round(group.highest_similarity_score * 100)}% Match Confidence
                        </span>
                      </div>
                      <h4 className="text-sm font-serif font-bold text-[#191410] mt-0.5">
                        {group.linked_case_title}
                      </h4>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                        group.has_pending_review
                          ? 'bg-amber-100 text-amber-900 border border-amber-300'
                          : group.status === 'confirmed'
                          ? 'bg-emerald-100 text-emerald-900 border border-emerald-300'
                          : 'bg-rose-100 text-rose-900'
                      }`}>
                        {group.has_pending_review ? 'Pending Review' : group.status === 'confirmed' ? 'Confirmed Link' : 'Rejected'}
                      </span>

                      <Link
                        to={`/cases/${group.linked_case_id}`}
                        target="_blank"
                        className="p-1 rounded text-[#6e665d] hover:text-[#191410]"
                        title="Open connected case in new tab"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </Link>
                    </div>
                  </div>

                  {/* Matching Features List */}
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#6e665d] block mb-1.5">
                      Matching Features Detected:
                    </span>
                    <div className="space-y-2">
                      {group.matching_features.map((feat) => (
                        <div
                          key={feat.link_id}
                          className="bg-[#faf7f2] p-3 rounded-xl border border-[#eae4d9] text-xs space-y-1.5"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              {getFeatureIcon(feat.entity_type)}
                              <span className="font-bold text-[#191410] font-mono">
                                {feat.match_value}
                              </span>
                              <span className="text-[10px] px-2 py-0.2 rounded-full bg-white border border-[#eae4d9] font-medium text-[#6e665d]">
                                {feat.entity_type.toUpperCase()}
                              </span>
                            </div>

                            <span className="text-[10px] font-semibold text-[#6e665d]">
                              {feat.status === 'pending_review' ? 'Candidate Lead' : feat.status}
                            </span>
                          </div>

                          <p className="text-[11px] text-[#6e665d] leading-relaxed">
                            {feat.confidence_reason}
                          </p>

                          {/* Quick Review Action on this feature */}
                          {feat.status === 'pending_review' && (
                            <div className="pt-1.5 border-t border-[#f0ebe1] flex items-center justify-between gap-2">
                              {reviewingLinkId === feat.link_id ? (
                                <div className="w-full flex items-center gap-2">
                                  <input
                                    type="text"
                                    placeholder="Add investigator note..."
                                    value={reviewNotes}
                                    onChange={(e) => setReviewNotes(e.target.value)}
                                    className="flex-1 text-xs px-2.5 py-1 rounded-lg border border-[#eae4d9] bg-white focus:outline-none"
                                  />
                                  <button
                                    onClick={() => handleReview(feat.link_id, 'confirmed')}
                                    className="px-2.5 py-1 rounded-lg text-[11px] font-bold text-white bg-emerald-600 hover:bg-emerald-700 cursor-pointer"
                                  >
                                    Confirm
                                  </button>
                                  <button
                                    onClick={() => handleReview(feat.link_id, 'rejected')}
                                    className="px-2.5 py-1 rounded-lg text-[11px] font-bold text-white bg-rose-600 hover:bg-rose-700 cursor-pointer"
                                  >
                                    Reject
                                  </button>
                                  <button
                                    onClick={() => { setReviewingLinkId(null); setReviewNotes(''); }}
                                    className="text-xs text-[#6e665d]"
                                  >
                                    Cancel
                                  </button>
                                </div>
                              ) : (
                                <div className="flex items-center gap-2 ml-auto">
                                  <button
                                    onClick={() => { setReviewingLinkId(feat.link_id); setReviewNotes(''); }}
                                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-bold text-emerald-800 bg-emerald-100 hover:bg-emerald-200 transition cursor-pointer"
                                  >
                                    <CheckCircle2 className="w-3.5 h-3.5" />
                                    Confirm Link
                                  </button>
                                  <button
                                    onClick={() => handleReview(feat.link_id, 'rejected')}
                                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-bold text-rose-800 bg-rose-100 hover:bg-rose-200 transition cursor-pointer"
                                  >
                                    <XCircle className="w-3.5 h-3.5" />
                                    Reject Lead
                                  </button>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Footer with Link to full Cross-Case page */}
            <div className="p-4 border-t border-[#f0ebe1] bg-[#faf7f2] flex items-center justify-between text-xs">
              <span className="text-[#6e665d] flex items-center gap-1">
                <Lock className="w-3.5 h-3.5 text-stone-500" />
                Links strictly isolated to dual-case authorized personnel
              </span>
              <Link
                to={`/cases/${caseId}/cross-case`}
                onClick={() => setModalOpen(false)}
                className="inline-flex items-center gap-1 font-bold text-[#d93829] hover:underline"
              >
                <span>Open Full Cross-Case Intelligence Suite</span>
                <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

