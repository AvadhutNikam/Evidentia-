import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Share2,
  CheckCircle2,
  XCircle,
  Clock,
  Phone,
  Car,
  User,
  MapPin,
  Terminal,
  ShieldCheck,
  Search,
  Sparkles,
  ArrowRight,
  ExternalLink,
  ChevronRight,
  RefreshCw,
  SlidersHorizontal,
  Flame,
  Info,
  Layers,
  Lock,
  GitCompare,
  AlertTriangle,
  FileCheck2
} from 'lucide-react';
import { crossCaseService, caseService } from '../../services';
import {
  CrossCaseEntityLink,
  CrossCaseMOSimilarCase,
  CrossCaseIntelligenceSummary,
  Case
} from '../../types';

export function CrossCaseIntelligence() {
  const { caseId } = useParams<{ caseId: string }>();
  const [currentCase, setCurrentCase] = useState<Case | null>(null);
  const [summary, setSummary] = useState<CrossCaseIntelligenceSummary | null>(null);
  const [links, setLinks] = useState<CrossCaseEntityLink[]>([]);
  const [similarCases, setSimilarCases] = useState<CrossCaseMOSimilarCase[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [scanning, setScanning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Filters & Tabs
  const [activeTab, setActiveTab] = useState<'entities' | 'mo_similarity'>('entities');
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending_review' | 'confirmed' | 'rejected'>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Review Modal State
  const [reviewModal, setReviewModal] = useState<{
    isOpen: boolean;
    link: CrossCaseEntityLink | null;
    targetStatus: 'confirmed' | 'rejected';
    notes: string;
    submitting: boolean;
  }>({
    isOpen: false,
    link: null,
    targetStatus: 'confirmed',
    notes: '',
    submitting: false
  });

  const loadData = async (isScan = false) => {
    if (!caseId) return;
    try {
      if (isScan) {
        setScanning(true);
      } else {
        setLoading(true);
      }
      setError(null);

      const [caseData, summaryData] = await Promise.all([
        caseService.getCaseById(caseId),
        crossCaseService.getSummary(caseId)
      ]);

      if (caseData) setCurrentCase(caseData);
      if (summaryData) {
        setSummary(summaryData);
        setLinks(summaryData.links || []);
        setSimilarCases(summaryData.similar_cases || []);
      }
    } catch (err: any) {
      console.error('Failed to load cross-case intelligence:', err);
      setError(err?.message || 'Failed to load cross-case intelligence. Access may be restricted.');
    } finally {
      setLoading(false);
      setScanning(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [caseId]);

  const handleTriggerScan = async () => {
    if (!caseId) return;
    try {
      setScanning(true);
      await crossCaseService.triggerResolution(caseId);
      await loadData(true);
    } catch (err: any) {
      console.error('Resolution scan error:', err);
      setError(err?.message || 'Cross-case scan failed.');
      setScanning(false);
    }
  };

  const handleOpenReviewModal = (link: CrossCaseEntityLink, targetStatus: 'confirmed' | 'rejected') => {
    setReviewModal({
      isOpen: true,
      link,
      targetStatus,
      notes: '',
      submitting: false
    });
  };

  const handleSubmitReview = async () => {
    if (!caseId || !reviewModal.link) return;
    try {
      setReviewModal(prev => ({ ...prev, submitting: true }));
      await crossCaseService.reviewLink(
        caseId,
        reviewModal.link.id,
        reviewModal.targetStatus,
        reviewModal.notes
      );
      setReviewModal(prev => ({ ...prev, isOpen: false, submitting: false }));
      // Reload links
      await loadData(false);
    } catch (err: any) {
      alert(`Review action failed: ${err?.message || 'Permission denied.'}`);
      setReviewModal(prev => ({ ...prev, submitting: false }));
    }
  };

  // Filter links
  const filteredLinks = links.filter(link => {
    if (statusFilter !== 'all' && link.status !== statusFilter) return false;
    if (typeFilter !== 'all' && link.entity_type.toLowerCase() !== typeFilter.toLowerCase()) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchVal = (link.match_value || '').toLowerCase();
      const sName = (link.source_entity?.name || '').toLowerCase();
      const tName = (link.linked_entity?.name || '').toLowerCase();
      const tTitle = (link.linked_case_title || '').toLowerCase();
      const reason = (link.confidence_reason || '').toLowerCase();
      if (!matchVal.includes(q) && !sName.includes(q) && !tName.includes(q) && !tTitle.includes(q) && !reason.includes(q)) {
        return false;
      }
    }
    return true;
  });

  const getEntityIcon = (type: string) => {
    const t = (type || '').toLowerCase();
    if (t.includes('phone') || t.includes('contact') || t.includes('cdr')) {
      return <Phone className="w-4 h-4 text-emerald-600" />;
    }
    if (t.includes('vehicle') || t.includes('car') || t.includes('cab') || t.includes('bus')) {
      return <Car className="w-4 h-4 text-blue-600" />;
    }
    if (t.includes('address') || t.includes('location') || t.includes('corridor')) {
      return <MapPin className="w-4 h-4 text-amber-600" />;
    }
    if (t.includes('digital') || t.includes('ip') || t.includes('crypto') || t.includes('imei')) {
      return <Terminal className="w-4 h-4 text-cyan-600" />;
    }
    return <User className="w-4 h-4 text-purple-600" />;
  };

  const getMatchTypeBadge = (matchType: string, score: number) => {
    if (matchType === 'exact_identifier') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
          <Lock className="w-3 h-3 text-emerald-600" />
          Tier 1: Exact Identifier (100%)
        </span>
      );
    }
    if (matchType === 'exact_name') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-800 border border-blue-200">
          <ShieldCheck className="w-3 h-3 text-blue-600" />
          Tier 2: Exact Name ({Math.round(score * 100)}%)
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200">
        <Sparkles className="w-3 h-3 text-amber-600" />
        Tier 3: Fuzzy Match ({Math.round(score * 100)}%)
      </span>
    );
  };

  const getStatusBadge = (status: string) => {
    if (status === 'confirmed') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700" />
          Confirmed Link
        </span>
      );
    }
    if (status === 'rejected') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-300">
          <XCircle className="w-3.5 h-3.5 text-rose-700" />
          Rejected Lead
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-300">
        <Clock className="w-3.5 h-3.5 text-amber-700" />
        Pending Review
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-[#faf7f2] p-6 lg:p-8 space-y-6 text-[#191410]">
      {/* Header & Intelligence Dossier Bar */}
      <div className="bg-white border border-[#eae4d9] rounded-2xl p-6 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="p-1.5 rounded-lg bg-[#d93829]/10 text-[#d93829]">
                <Share2 className="w-5 h-5" />
              </span>
              <span className="text-xs font-bold uppercase tracking-wider text-[#d93829]">
                Cross-Case Intelligence & Entity Resolution
              </span>
            </div>
            <h1 className="text-2xl font-serif font-bold text-[#191410]">
              Multi-Jurisdictional Intelligence Dossier
            </h1>
            <p className="text-xs text-[#6e665d] mt-1 max-w-2xl">
              Automated entity resolution detecting shared telephone numbers, vehicles, suspects, and locations across dockets.
              Respects statutory RBAC tenant isolation with mandatory reviewer validation.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleTriggerScan}
              disabled={scanning}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold text-white bg-[#d93829] hover:bg-[#b82e21] shadow-xs hover:shadow-md transition-all disabled:opacity-50 cursor-pointer"
            >
              <RefreshCw className={`w-4 h-4 ${scanning ? 'animate-spin' : ''}`} />
              <span>{scanning ? 'Resolving Cross-Case Entities...' : 'Scan Accessible Dockets'}</span>
            </button>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-5 border-t border-[#f0ebe1]">
          <div className="bg-[#faf7f2] rounded-xl p-3 border border-[#eae4d9]">
            <span className="text-[11px] font-medium text-[#6e665d] uppercase tracking-wider block">Total Resolved Links</span>
            <span className="text-xl font-bold font-serif text-[#191410] mt-0.5 block">{summary?.total_links ?? 0}</span>
          </div>
          <div className="bg-amber-50/60 rounded-xl p-3 border border-amber-200">
            <span className="text-[11px] font-medium text-amber-800 uppercase tracking-wider block">Pending Validation</span>
            <span className="text-xl font-bold font-serif text-amber-900 mt-0.5 block">{summary?.pending_links ?? 0}</span>
          </div>
          <div className="bg-emerald-50/60 rounded-xl p-3 border border-emerald-200">
            <span className="text-[11px] font-medium text-emerald-800 uppercase tracking-wider block">Confirmed Links</span>
            <span className="text-xl font-bold font-serif text-emerald-900 mt-0.5 block">{summary?.confirmed_links ?? 0}</span>
          </div>
          <div className="bg-purple-50/60 rounded-xl p-3 border border-purple-200">
            <span className="text-[11px] font-medium text-purple-800 uppercase tracking-wider block">MO Similar Dockets</span>
            <span className="text-xl font-bold font-serif text-purple-900 mt-0.5 block">{similarCases.length}</span>
          </div>
        </div>
      </div>

      {/* Main Tabs */}
      <div className="flex items-center gap-2 border-b border-[#eae4d9] pb-2">
        <button
          onClick={() => setActiveTab('entities')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
            activeTab === 'entities'
              ? 'bg-[#191410] text-white shadow-xs'
              : 'text-[#6e665d] hover:bg-white hover:text-[#191410]'
          }`}
        >
          <GitCompare className="w-4 h-4" />
          <span>Entity Resolution ({links.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('mo_similarity')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
            activeTab === 'mo_similarity'
              ? 'bg-[#191410] text-white shadow-xs'
              : 'text-[#6e665d] hover:bg-white hover:text-[#191410]'
          }`}
        >
          <Flame className="w-4 h-4" />
          <span>Modus Operandi (MO) Pattern Matrix ({similarCases.length})</span>
        </button>
      </div>

      {/* TAB 1: ENTITY RESOLUTION */}
      {activeTab === 'entities' && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="bg-white border border-[#eae4d9] rounded-xl p-3.5 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#6e665d] mr-1">Status:</span>
              {(['all', 'pending_review', 'confirmed', 'rejected'] as const).map(st => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-3 py-1 rounded-lg text-xs font-medium capitalize transition-all cursor-pointer ${
                    statusFilter === st
                      ? 'bg-[#d93829] text-white font-semibold'
                      : 'bg-[#faf7f2] text-[#6e665d] hover:bg-[#f0ebe1]'
                  }`}
                >
                  {st === 'pending_review' ? 'Pending Review' : st}
                </button>
              ))}

              <span className="text-[11px] font-bold uppercase tracking-wider text-[#6e665d] ml-3 mr-1">Entity:</span>
              {['all', 'phone', 'vehicle', 'person', 'address', 'digital'].map(et => (
                <button
                  key={et}
                  onClick={() => setTypeFilter(et)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium capitalize transition-all cursor-pointer ${
                    typeFilter === et
                      ? 'bg-[#191410] text-white font-semibold'
                      : 'bg-[#faf7f2] text-[#6e665d] hover:bg-[#f0ebe1]'
                  }`}
                >
                  {et}
                </button>
              ))}
            </div>

            <div className="relative min-w-[240px]">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#6e665d]" />
              <input
                type="text"
                placeholder="Search phone, plate, person..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-[#eae4d9] text-xs bg-[#faf7f2] focus:outline-none focus:ring-1 focus:ring-[#d93829] focus:bg-white"
              />
            </div>
          </div>

          {/* Links List */}
          {loading ? (
            <div className="bg-white border border-[#eae4d9] rounded-2xl p-12 text-center shadow-xs">
              <RefreshCw className="w-8 h-8 animate-spin text-[#d93829] mx-auto mb-3" />
              <p className="text-xs text-[#6e665d]">Scanning cross-case entities across accessible dockets...</p>
            </div>
          ) : filteredLinks.length === 0 ? (
            <div className="bg-white border border-[#eae4d9] rounded-2xl p-12 text-center shadow-xs">
              <div className="w-12 h-12 rounded-2xl bg-amber-50 text-amber-700 flex items-center justify-center mx-auto mb-3">
                <Search className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-serif font-bold text-[#191410]">No Cross-Case Links Found</h3>
              <p className="text-xs text-[#6e665d] mt-1 max-w-md mx-auto">
                No matching telephone numbers, vehicles, persons, or locations detected with the current filters.
                Click "Scan Accessible Dockets" above to initiate a multi-tier resolution scan across all jurisdictions.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredLinks.map(link => (
                <div
                  key={link.id}
                  className="bg-white border border-[#eae4d9] hover:border-[#d93829]/30 rounded-2xl p-5 shadow-xs transition-all duration-150"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#f0ebe1]">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="p-1.5 rounded-lg bg-[#faf7f2] border border-[#eae4d9]">
                        {getEntityIcon(link.entity_type)}
                      </span>
                      <span className="text-xs font-bold uppercase tracking-wider text-[#191410]">
                        {link.entity_type} Match
                      </span>
                      {getMatchTypeBadge(link.match_type, link.similarity_score)}
                    </div>

                    <div className="flex items-center gap-2">
                      {getStatusBadge(link.status)}
                    </div>
                  </div>

                  {/* Entity Match Comparison Row */}
                  <div className="grid grid-cols-1 md:grid-cols-11 gap-4 items-center py-4">
                    {/* Source Entity */}
                    <div className="md:col-span-5 bg-[#faf7f2] p-3.5 rounded-xl border border-[#eae4d9]">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-[#6e665d]">Current Investigation</span>
                        <span className="text-[10px] bg-white px-2 py-0.5 rounded border border-[#eae4d9] text-[#6e665d]">
                          {link.source_entity?.type || link.entity_type}
                        </span>
                      </div>
                      <p className="text-xs font-bold text-[#191410] line-clamp-1">{link.source_entity?.name || 'Unknown'}</p>
                    </div>

                    {/* Bridge Icon / Value */}
                    <div className="md:col-span-1 flex flex-col items-center justify-center">
                      <div className="w-8 h-8 rounded-full bg-[#191410] text-white flex items-center justify-center shadow-xs">
                        <ArrowRight className="w-4 h-4" />
                      </div>
                      <span className="text-[9px] font-mono font-bold text-[#6e665d] mt-1 text-center truncate max-w-[80px]">
                        {link.match_value}
                      </span>
                    </div>

                    {/* Target / Linked Entity */}
                    <div className="md:col-span-5 bg-blue-50/40 p-3.5 rounded-xl border border-blue-200">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-1">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-blue-900">Linked Docket</span>
                          <Link
                            to={`/cases/${link.linked_case_id}/overview`}
                            className="inline-flex items-center gap-0.5 text-[10px] font-semibold text-blue-700 hover:text-blue-900 underline"
                          >
                            <span>#{link.linked_case_id}</span>
                            <ExternalLink className="w-2.5 h-2.5" />
                          </Link>
                        </div>
                        <span className="text-[10px] bg-white px-2 py-0.5 rounded border border-blue-200 text-blue-800">
                          {link.linked_entity?.type || link.entity_type}
                        </span>
                      </div>
                      <p className="text-xs font-bold text-[#191410] line-clamp-1">{link.linked_entity?.name || 'Unknown'}</p>
                      <p className="text-[10px] text-[#6e665d] truncate mt-0.5">{link.linked_case_title}</p>
                    </div>
                  </div>

                  {/* Forensic Confidence Reason */}
                  <div className="bg-[#faf7f2]/80 px-3.5 py-2.5 rounded-xl border border-[#eae4d9] text-xs text-[#191410] flex items-start gap-2">
                    <Info className="w-4 h-4 text-[#d93829] shrink-0 mt-0.5" />
                    <span className="leading-relaxed">{link.confidence_reason}</span>
                  </div>

                  {/* Review Actions / Audited Notes */}
                  <div className="mt-3.5 pt-3 border-t border-[#f0ebe1] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                    {link.status === 'confirmed' ? (
                      <div className="text-[#15803d] flex items-center gap-1.5 font-medium">
                        <CheckCircle2 className="w-4 h-4 shrink-0" />
                        <span>Confirmed by {link.reviewed_by_name || 'Investigator'} on {link.reviewed_at ? new Date(link.reviewed_at).toLocaleDateString() : 'recent'}.</span>
                        {link.reviewer_notes && <span className="text-[#6e665d] italic">({link.reviewer_notes})</span>}
                      </div>
                    ) : link.status === 'rejected' ? (
                      <div className="text-rose-700 flex items-center gap-1.5 font-medium">
                        <XCircle className="w-4 h-4 shrink-0" />
                        <span>Rejected by {link.reviewed_by_name || 'Investigator'}.</span>
                        {link.reviewer_notes && <span className="text-[#6e665d] italic">Reason: {link.reviewer_notes}</span>}
                      </div>
                    ) : (
                      <div className="text-amber-800 flex items-center gap-1.5 font-medium">
                        <Clock className="w-4 h-4 shrink-0" />
                        <span>Awaiting lead investigator confirmation before feeding to ACH matrix.</span>
                      </div>
                    )}

                    <div className="flex items-center gap-2 shrink-0">
                      {link.status !== 'confirmed' && (
                        <button
                          onClick={() => handleOpenReviewModal(link, 'confirmed')}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 transition-all cursor-pointer"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Confirm Link</span>
                        </button>
                      )}

                      {link.status !== 'rejected' && (
                        <button
                          onClick={() => handleOpenReviewModal(link, 'rejected')}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold text-rose-800 bg-rose-50 hover:bg-rose-100 border border-rose-300 transition-all cursor-pointer"
                        >
                          <XCircle className="w-3.5 h-3.5" />
                          <span>Reject Lead</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: MODUS OPERANDI (MO) SIMILARITY MATRIX */}
      {activeTab === 'mo_similarity' && (
        <div className="space-y-4">
          <div className="bg-white border border-[#eae4d9] rounded-2xl p-5 shadow-xs">
            <div className="flex items-start gap-3">
              <span className="p-2 rounded-xl bg-purple-50 text-purple-700 shrink-0">
                <Flame className="w-5 h-5" />
              </span>
              <div>
                <h3 className="text-sm font-serif font-bold text-[#191410]">
                  5-Dimensional Tradecraft Relevance Engine
                </h3>
                <p className="text-xs text-[#6e665d] mt-1 leading-relaxed">
                  Evaluates criminal tradecraft vectors across Weapon/Intimidation, Ingress/Decoy Method, Victim Demographics,
                  Corridor Topology, and Temporal Windows. Only dockets accessible under your assigned permissions are compared.
                </p>
              </div>
            </div>
          </div>

          {similarCases.length === 0 ? (
            <div className="bg-white border border-[#eae4d9] rounded-2xl p-12 text-center shadow-xs">
              <Flame className="w-8 h-8 text-[#6e665d] mx-auto mb-2 opacity-50" />
              <h4 className="text-sm font-bold text-[#191410]">No Analogous Tradecraft Detected</h4>
              <p className="text-xs text-[#6e665d] mt-1">
                No accessible cases met the minimum 15% MO similarity threshold.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {similarCases.map(similar => (
                <div
                  key={similar.case_id}
                  className="bg-white border border-[#eae4d9] hover:border-purple-300 rounded-2xl p-6 shadow-xs transition-all duration-150"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[#f0ebe1]">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[10px] font-mono font-bold bg-[#faf7f2] px-2 py-0.5 rounded border border-[#eae4d9] text-[#6e665d]">
                          {similar.fir_number}
                        </span>
                        <span className="text-[10px] bg-emerald-50 text-emerald-800 font-semibold px-2 py-0.5 rounded border border-emerald-200">
                          {similar.status}
                        </span>
                        <span className="text-[10px] text-[#6e665d]">
                          Section: {similar.offence_section}
                        </span>
                      </div>
                      <h4 className="text-sm font-serif font-bold text-[#191410]">
                        {similar.title}
                      </h4>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <div className="text-right">
                        <span className="text-xs font-semibold text-[#6e665d] block">Tradecraft Match</span>
                        <span className="text-xl font-serif font-bold text-purple-700">
                          {similar.similarity_percentage}%
                        </span>
                      </div>

                      <Link
                        to={`/cases/${similar.case_id}/overview`}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold text-[#191410] bg-[#faf7f2] hover:bg-[#f0ebe1] border border-[#eae4d9] transition-all cursor-pointer"
                      >
                        <span>Open Docket</span>
                        <ExternalLink className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  </div>

                  {/* Description Snippet */}
                  {similar.description_snippet && (
                    <p className="text-xs text-[#6e665d] my-3 leading-relaxed italic">
                      "{similar.description_snippet}"
                    </p>
                  )}

                  {/* Matched Feature Pills */}
                  {similar.matched_features && similar.matched_features.length > 0 && (
                    <div className="mt-3">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-[#6e665d] block mb-1.5">
                        Matched Modus Operandi Vectors:
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {similar.matched_features.map((feat, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium bg-purple-50 text-purple-900 border border-purple-200"
                          >
                            <Sparkles className="w-3 h-3 text-purple-600" />
                            {feat}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 5-Dimensional Breakdown */}
                  {similar.field_scores && Object.keys(similar.field_scores).length > 0 && (
                    <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mt-4 pt-4 border-t border-[#f0ebe1]">
                      {Object.entries(similar.field_scores).map(([dim, score]) => (
                        <div key={dim} className="bg-[#faf7f2] p-2.5 rounded-xl border border-[#eae4d9]">
                          <div className="flex items-center justify-between text-[10px] text-[#6e665d] font-bold uppercase tracking-wider mb-1">
                            <span>{dim.replace('_', ' ')}</span>
                            <span>{Math.round(score * 100)}%</span>
                          </div>
                          <div className="w-full bg-[#eae4d9] h-1.5 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-purple-600 rounded-full"
                              style={{ width: `${Math.round(score * 100)}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* REVIEW CONFIRMATION / REJECTION MODAL */}
      {reviewModal.isOpen && reviewModal.link && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full border border-[#eae4d9] shadow-xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#f0ebe1]">
              <div className="flex items-center gap-2">
                {reviewModal.targetStatus === 'confirmed' ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                ) : (
                  <XCircle className="w-5 h-5 text-rose-600" />
                )}
                <h3 className="text-base font-serif font-bold text-[#191410]">
                  {reviewModal.targetStatus === 'confirmed' ? 'Confirm Cross-Case Link' : 'Reject Cross-Case Lead'}
                </h3>
              </div>
              <button
                onClick={() => setReviewModal(prev => ({ ...prev, isOpen: false }))}
                className="text-[#6e665d] hover:text-[#191410] p-1 rounded-lg hover:bg-[#faf7f2]"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <div className="bg-[#faf7f2] p-3 rounded-xl border border-[#eae4d9] text-xs space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-bold text-[#6e665d] uppercase">Entity Type:</span>
                <span className="font-semibold text-[#191410] capitalize">{reviewModal.link.entity_type}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-bold text-[#6e665d] uppercase">Match Value:</span>
                <span className="font-mono font-bold text-[#191410]">{reviewModal.link.match_value}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-bold text-[#6e665d] uppercase">Target Docket:</span>
                <span className="font-semibold text-[#191410] truncate max-w-[240px]">
                  #{reviewModal.link.linked_case_id} ({reviewModal.link.linked_case_title})
                </span>
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-[#191410] block mb-1">
                Investigator / Reviewer Notes (Immutable Audit Trail):
              </label>
              <textarea
                rows={3}
                placeholder={
                  reviewModal.targetStatus === 'confirmed'
                    ? 'e.g. Verified with Indiranagar PS via RTO chassis registration match; vehicle confirmed seized in related docket.'
                    : 'e.g. SIM card was re-allocated by cellular provider months prior to incident; false positive.'
                }
                value={reviewModal.notes}
                onChange={e => setReviewModal(prev => ({ ...prev, notes: e.target.value }))}
                className="w-full text-xs p-3 rounded-xl border border-[#eae4d9] focus:outline-none focus:ring-1 focus:ring-[#d93829] bg-[#faf7f2] focus:bg-white resize-none"
              />
              <p className="text-[10px] text-[#6e665d] mt-1">
                This validation action is cryptographically signed and chained into the case Merkle audit log.
              </p>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#f0ebe1]">
              <button
                type="button"
                onClick={() => setReviewModal(prev => ({ ...prev, isOpen: false }))}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-[#6e665d] hover:bg-[#faf7f2] cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={reviewModal.submitting}
                onClick={handleSubmitReview}
                className={`px-4 py-2 rounded-xl text-xs font-bold text-white shadow-xs cursor-pointer ${
                  reviewModal.targetStatus === 'confirmed'
                    ? 'bg-emerald-700 hover:bg-emerald-800'
                    : 'bg-rose-700 hover:bg-rose-800'
                }`}
              >
                {reviewModal.submitting ? 'Submitting...' : `Confirm as ${reviewModal.targetStatus}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

