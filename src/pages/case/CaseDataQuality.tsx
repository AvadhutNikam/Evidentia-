import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { 
  ShieldCheck, AlertTriangle, CheckCircle2, RefreshCw, FileText, 
  Hash, Award, Globe, ArrowUpDown, Filter, ChevronRight, AlertOctagon, 
  ExternalLink, Sparkles, Check, ArrowLeft
} from 'lucide-react';
import { cn } from '../../utils';
import { evidenceDataQualityService } from '../../services';
import { CaseDataQualityReport, ExhibitDataQualityItem } from '../../types';

export function CaseDataQuality() {
  const { caseId } = useParams<{ caseId: string }>();
  const [report, setReport] = useState<CaseDataQualityReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [sortOrder, setSortOrder] = useState<'weakest_first' | 'strongest_first'>('weakest_first');
  const [filterWeakOnly, setFilterWeakOnly] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [recomputingId, setRecomputingId] = useState<number | null>(null);
  const [actionMsg, setActionMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchReport = useCallback(async (isSilent = false) => {
    if (!caseId) return;
    if (!isSilent) setRefreshing(true);
    try {
      const data = await evidenceDataQualityService.getCaseQualityReport(caseId, sortOrder);
      setReport(data);
    } catch (err: any) {
      console.error('Failed to load data quality report:', err);
      setActionMsg({ type: 'error', text: err?.message || 'Could not fetch exhibit data quality report.' });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [caseId, sortOrder]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const handleVerifyHash = async (evidenceId: number) => {
    if (!caseId) return;
    setRecomputingId(evidenceId);
    setActionMsg(null);
    try {
      const updated = await evidenceDataQualityService.verifyExhibitHash(caseId, evidenceId);
      setActionMsg({ 
        type: 'success', 
        text: `SHA-256 byte stream verified for Exhibit #${evidenceId}! Quality score increased to ${updated.overall_quality_score}%.` 
      });
      fetchReport(true);
    } catch (err: any) {
      setActionMsg({ type: 'error', text: `Hash verification failed: ${err.message}` });
    } finally {
      setRecomputingId(null);
    }
  };

  if (loading && !report) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <RefreshCw className="w-10 h-10 text-[#d93829] animate-spin" />
        <p className="text-[#6e665d] font-mono text-sm">Auditing exhibit 4-pillar data quality...</p>
      </div>
    );
  }

  const exhibits = (report?.sorted_exhibits || []).filter((item) => {
    if (filterWeakOnly && !item.is_weak_item) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        item.title.toLowerCase().includes(q) ||
        item.file_name.toLowerCase().includes(q) ||
        item.warning_flags.some(f => f.toLowerCase().includes(q))
      );
    }
    return true;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Back to Evidence and Header */}
      <div className="flex items-center justify-between">
        <Link 
          to={`/cases/${caseId}/evidence`}
          className="inline-flex items-center text-xs font-semibold text-[#6e665d] hover:text-[#d93829] transition"
        >
          <ArrowLeft className="w-3.5 h-3.5 mr-1" />
          Back to Evidence Exhibits
        </Link>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => fetchReport(false)}
            disabled={refreshing}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-white hover:bg-[#faf7f2] text-[#191410] text-xs font-semibold rounded-xl border border-[#eae4d9] transition shadow-xs cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={cn("w-3.5 h-3.5 text-[#d93829]", refreshing && "animate-spin")} />
            <span>Re-Audit</span>
          </button>
        </div>
      </div>

      {/* Main Audit Header */}
      <div className="bg-white border border-[#eae4d9] p-6 rounded-2xl shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-1.5">
            <div className="flex items-center space-x-3">
              <h1 className="text-xl font-serif font-bold text-[#191410] tracking-tight">Exhibit Data-Quality Audit & Scoring</h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-50 text-[#d93829] border border-red-200">
                Weakest-First Prioritized
              </span>
            </div>
            <p className="text-xs text-[#6e665d] max-w-2xl leading-relaxed">
              Automated legal and forensic audit evaluating every exhibit against 4 judicial pillars: 
              <strong className="text-[#191410]"> Text Confidence (25%)</strong>, 
              <strong className="text-[#191410]"> Hash Integrity (25%)</strong>, 
              <strong className="text-[#191410]"> Section 65B/63 Certificate (25%)</strong>, and 
              <strong className="text-[#191410]"> Language Dialect Review (25%)</strong>.
            </p>
          </div>

          {/* Average Quality Metric Card */}
          <div className="flex items-center space-x-4 bg-[#faf7f2] border border-[#eae4d9] p-4 rounded-xl shrink-0">
            <div className="text-center pr-3 border-r border-[#eae4d9]">
              <div className="text-xs text-[#6e665d] font-mono">Case Quality Average</div>
              <div className={cn(
                "text-3xl font-extrabold font-mono",
                (report?.average_quality_score || 0) >= 80 ? "text-emerald-700" :
                (report?.average_quality_score || 0) >= 65 ? "text-amber-700" :
                "text-red-700"
              )}>
                {report?.average_quality_score}%
              </div>
            </div>
            <div className="space-y-1 text-xs">
              <div className="text-[#6e665d]">Total Audited: <span className="font-mono font-bold text-[#191410]">{report?.total_exhibits}</span></div>
              <div className="text-red-700 font-semibold">Weak Items: <span className="font-mono font-bold">{report?.weak_exhibits_count}</span></div>
            </div>
          </div>
        </div>
      </div>

      {/* Action / Success Banner */}
      {actionMsg && (
        <div className={cn(
          "p-4 rounded-xl border flex items-center justify-between text-sm transition animate-in fade-in",
          actionMsg.type === 'success' ? "bg-emerald-50 border-emerald-200 text-emerald-900" : "bg-red-50 border-red-200 text-red-900"
        )}>
          <div className="flex items-center space-x-3">
            {actionMsg.type === 'success' ? <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" /> : <AlertTriangle className="w-5 h-5 text-red-600 shrink-0" />}
            <p className="font-mono text-xs">{actionMsg.text}</p>
          </div>
          <button onClick={() => setActionMsg(null)} className="text-xs hover:underline text-[#6e665d] hover:text-[#191410] cursor-pointer">Dismiss</button>
        </div>
      )}

      {/* 4 Pillars Summary Counters */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 bg-white border border-[#eae4d9] rounded-2xl shadow-xs space-y-1">
          <div className="flex items-center justify-between text-xs text-[#6e665d]">
            <span className="font-semibold">Low Confidence Text</span>
            <FileText className="w-4 h-4 text-blue-700" />
          </div>
          <div className="text-2xl font-bold font-mono text-[#191410]">
            {report?.low_confidence_text_count}
          </div>
          <p className="text-[11px] text-[#8c8276]">Below 65% OCR fidelity</p>
        </div>

        <div className="p-4 bg-white border border-[#eae4d9] rounded-2xl shadow-xs space-y-1">
          <div className="flex items-center justify-between text-xs text-[#6e665d]">
            <span className="font-semibold">Unverified Hashes</span>
            <Hash className="w-4 h-4 text-purple-700" />
          </div>
          <div className={cn("text-2xl font-bold font-mono", (report?.unverified_hashes_count || 0) > 0 ? "text-amber-700" : "text-emerald-700")}>
            {report?.unverified_hashes_count}
          </div>
          <p className="text-[11px] text-[#8c8276]">Awaiting byte-stream match</p>
        </div>

        <div className="p-4 bg-white border border-[#eae4d9] rounded-2xl shadow-xs space-y-1">
          <div className="flex items-center justify-between text-xs text-[#6e665d]">
            <span className="font-semibold">Missing Sec 65B</span>
            <Award className="w-4 h-4 text-red-700" />
          </div>
          <div className={cn("text-2xl font-bold font-mono", (report?.missing_certificates_count || 0) > 0 ? "text-red-700" : "text-emerald-700")}>
            {report?.missing_certificates_count}
          </div>
          <p className="text-[11px] text-[#8c8276]">Legal certificate missing</p>
        </div>

        <div className="p-4 bg-white border border-[#eae4d9] rounded-2xl shadow-xs space-y-1">
          <div className="flex items-center justify-between text-xs text-[#6e665d]">
            <span className="font-semibold">Pending Translations</span>
            <Globe className="w-4 h-4 text-amber-700" />
          </div>
          <div className="text-2xl font-bold font-mono text-[#191410]">
            {report?.pending_language_reviews_count}
          </div>
          <p className="text-[11px] text-[#8c8276]">Regional dialects unreviewed</p>
        </div>
      </div>

      {/* Filter and Sorting Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white border border-[#eae4d9] p-3.5 rounded-2xl shadow-xs">
        <div className="flex items-center space-x-3 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-72">
            <input
              type="text"
              placeholder="Search exhibit title, filename, or warnings..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#faf7f2] border border-[#eae4d9] text-xs text-[#191410] pl-3 pr-8 py-2 rounded-xl focus:outline-none focus:border-[#d93829]"
            />
          </div>
          <button
            onClick={() => setFilterWeakOnly(!filterWeakOnly)}
            className={cn(
              "px-3 py-2 rounded-xl text-xs font-semibold border flex items-center space-x-1.5 transition shrink-0 cursor-pointer",
              filterWeakOnly 
                ? "bg-red-50 border-red-300 text-red-800"
                : "bg-white border-[#eae4d9] text-[#6e665d] hover:text-[#191410] hover:bg-[#faf7f2]"
            )}
          >
            <Filter className="w-3.5 h-3.5" />
            <span>Weak Only ({report?.weak_exhibits_count})</span>
          </button>
        </div>

        <div className="flex items-center space-x-2 self-end sm:self-auto">
          <span className="text-xs text-[#6e665d]">Sort Priority:</span>
          <button
            onClick={() => setSortOrder(sortOrder === 'weakest_first' ? 'strongest_first' : 'weakest_first')}
            className="flex items-center space-x-1.5 px-3 py-2 bg-white hover:bg-[#faf7f2] text-[#191410] text-xs font-semibold rounded-xl border border-[#eae4d9] transition shadow-xs cursor-pointer"
          >
            <ArrowUpDown className="w-3.5 h-3.5 text-[#d93829]" />
            <span>{sortOrder === 'weakest_first' ? 'Weakest Items First (Audit Priority)' : 'Highest Quality First'}</span>
          </button>
        </div>
      </div>

      {/* Prioritized Exhibits List */}
      <div className="space-y-4">
        {exhibits.length === 0 ? (
          <div className="p-8 text-center text-xs text-[#8c8276] font-mono bg-white rounded-2xl border border-[#eae4d9]">
            No exhibits match the current filter or search criteria.
          </div>
        ) : (
          exhibits.map((item, index) => {
            const isCritical = item.overall_quality_score < 55;
            const isWeak = item.overall_quality_score < 70;
            const pillars = item.pillars;

            return (
              <Card 
                key={item.evidence_id} 
                className={cn(
                  "border transition overflow-hidden shadow-xs",
                  isCritical 
                    ? "bg-red-50/30 border-red-200 hover:border-red-300" 
                    : isWeak 
                    ? "bg-amber-50/30 border-amber-200 hover:border-amber-300" 
                    : "bg-white border-[#eae4d9] hover:border-[#d93829]/30"
                )}
              >
                <div className="p-5 space-y-4">
                  {/* Top Bar: Title, Tier & Composite Score */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#eae4d9]">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-3">
                        <span className="font-mono text-xs text-[#6e665d] font-bold">#{index + 1}</span>
                        <h3 className="text-sm font-bold text-[#191410] tracking-tight flex items-center space-x-2">
                          <span>{item.title}</span>
                          <span className="text-[11px] font-mono text-[#6e665d] font-normal">({item.file_name})</span>
                        </h3>
                      </div>
                      <div className="flex items-center space-x-3 text-xs text-[#6e665d]">
                        <span>Exhibit ID: <strong className="text-[#191410]">#{item.evidence_id}</strong></span>
                        <span>•</span>
                        <span>Type: <strong className="capitalize text-[#191410]">{item.evidence_type}</strong></span>
                        <span>•</span>
                        <span>Officer: <strong className="text-[#191410]">{item.uploaded_by}</strong></span>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3 self-end sm:self-auto">
                      <span className={cn(
                        "px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider border",
                        isCritical 
                          ? "bg-red-50 text-red-800 border-red-200 animate-pulse" 
                          : isWeak 
                          ? "bg-amber-50 text-amber-800 border-amber-200" 
                          : "bg-emerald-50 text-emerald-800 border-emerald-200"
                      )}>
                        {item.quality_tier}
                      </span>
                      <div className="text-right">
                        <span className={cn(
                          "text-2xl font-extrabold font-mono",
                          isCritical ? "text-red-700" : isWeak ? "text-amber-700" : "text-emerald-700"
                        )}>
                          {item.overall_quality_score}%
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* 4 Pillars Breakdown Grid */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                    {/* Pillar 1: Text Confidence */}
                    <div className="p-3 bg-[#faf7f2] rounded-xl border border-[#eae4d9] space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-[#191410] flex items-center">
                          <FileText className="w-3.5 h-3.5 text-blue-700 mr-1.5" />
                          1. Text Confidence
                        </span>
                        <span className="font-mono font-bold text-[#191410]">
                          {pillars.text_confidence_score} / 25
                        </span>
                      </div>
                      <div className="w-full bg-[#eae4d9] rounded-full h-1.5 overflow-hidden">
                        <div 
                          className={cn("h-full rounded-full", pillars.text_confidence_pct < 60 ? "bg-red-600" : pillars.text_confidence_pct < 85 ? "bg-amber-600" : "bg-emerald-600")}
                          style={{ width: `${Math.min(100, Math.max(5, pillars.text_confidence_pct))}%` }}
                        />
                      </div>
                      <p className="text-[11px] text-[#6e665d] line-clamp-2">
                        {pillars.text_notes}
                      </p>
                    </div>

                    {/* Pillar 2: Hash Integrity */}
                    <div className="p-3 bg-[#faf7f2] rounded-xl border border-[#eae4d9] space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-[#191410] flex items-center">
                          <Hash className="w-3.5 h-3.5 text-purple-700 mr-1.5" />
                          2. Hash Status
                        </span>
                        <span className="font-mono font-bold text-[#191410]">
                          {pillars.hash_score} / 25
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className={cn(
                          "px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border",
                          pillars.hash_status === 'verified' ? "bg-emerald-50 text-emerald-800 border-emerald-200" :
                          pillars.hash_status === 'unverified' ? "bg-amber-50 text-amber-800 border-amber-200" :
                          "bg-red-50 text-red-800 border-red-200"
                        )}>
                          {pillars.hash_status}
                        </span>
                        {pillars.hash_status !== 'verified' && (
                          <button
                            onClick={() => handleVerifyHash(item.evidence_id)}
                            disabled={recomputingId === item.evidence_id}
                            className="text-[11px] text-blue-700 hover:underline font-semibold disabled:opacity-50 cursor-pointer"
                          >
                            {recomputingId === item.evidence_id ? 'Verifying...' : 'Verify Hash'}
                          </button>
                        )}
                      </div>
                      <p className="text-[11px] font-mono text-[#6e665d] truncate">
                        {pillars.hash_value ? `${pillars.hash_value.slice(0, 16)}...` : 'No hash recorded'}
                      </p>
                    </div>

                    {/* Pillar 3: Legal Certificate */}
                    <div className="p-3 bg-[#faf7f2] rounded-xl border border-[#eae4d9] space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-[#191410] flex items-center">
                          <Award className="w-3.5 h-3.5 text-amber-700 mr-1.5" />
                          3. Sec 65B Certificate
                        </span>
                        <span className="font-mono font-bold text-[#191410]">
                          {pillars.certificate_score} / 25
                        </span>
                      </div>
                      <div>
                        <span className={cn(
                          "px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border",
                          pillars.certificate_status === 'certified' ? "bg-emerald-50 text-emerald-800 border-emerald-200" :
                          "bg-red-50 text-red-800 border-red-200"
                        )}>
                          {pillars.certificate_status}
                        </span>
                      </div>
                      <p className="text-[11px] text-[#6e665d] line-clamp-2">
                        {pillars.certificate_notes}
                      </p>
                    </div>

                    {/* Pillar 4: Language Review */}
                    <div className="p-3 bg-[#faf7f2] rounded-xl border border-[#eae4d9] space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-[#191410] flex items-center">
                          <Globe className="w-3.5 h-3.5 text-emerald-700 mr-1.5" />
                          4. Language Review
                        </span>
                        <span className="font-mono font-bold text-[#191410]">
                          {pillars.language_review_score} / 25
                        </span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-[10px] font-mono px-1.5 py-0.5 bg-[#eae4d9] rounded uppercase text-[#191410] font-semibold">
                          {pillars.primary_language}
                        </span>
                        <span className={cn(
                          "px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border",
                          pillars.language_status === 'verified' || pillars.language_status === 'native_english' ? "bg-emerald-50 text-emerald-800 border-emerald-200" :
                          pillars.language_status === 'pending_review' ? "bg-amber-50 text-amber-800 border-amber-200" :
                          "bg-red-50 text-red-800 border-red-200"
                        )}>
                          {pillars.language_status.replace('_', ' ')}
                        </span>
                      </div>
                      <p className="text-[11px] text-[#6e665d] line-clamp-2">
                        {pillars.language_notes}
                      </p>
                    </div>
                  </div>

                  {/* Warning Flags & Recommended Remediation */}
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-2 bg-[#faf7f2] p-3.5 rounded-xl border border-[#eae4d9]">
                    <div className="space-y-1">
                      {item.warning_flags.length > 0 ? (
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="text-[11px] font-bold text-red-700 flex items-center mr-1">
                            <AlertTriangle className="w-3.5 h-3.5 mr-1" />
                            Warning Flags:
                          </span>
                          {item.warning_flags.map((flag, i) => (
                            <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-red-50 border border-red-200 text-red-800 font-semibold">
                              {flag}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <div className="text-[11px] text-emerald-700 font-semibold flex items-center">
                          <CheckCircle2 className="w-3.5 h-3.5 mr-1.5 text-emerald-600" />
                          Zero evidentiary warnings detected. All 4 pillars verified for court docket.
                        </div>
                      )}
                    </div>

                    <div className="shrink-0 flex items-center space-x-2 text-xs">
                      <span className="text-[#6e665d]">Action:</span>
                      <span className="font-semibold text-blue-800 bg-blue-50 px-2.5 py-1 rounded-lg border border-blue-200">
                        {item.recommended_action}
                      </span>
                    </div>
                  </div>
                </div>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
}

export default CaseDataQuality;
