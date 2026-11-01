import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  Scale, ShieldAlert, ShieldCheck, CheckCircle2, 
  RefreshCw, BookOpen, Quote, ArrowRight, TrendingDown, 
  Sparkles, AlertTriangle, ArrowUpRight
} from 'lucide-react';
import { DevilsAdvocateResponse } from '../../types';
import { decisionQualityService, hypothesisService } from '../../services';
import { cn } from '../../utils';

export function DefenseStressTest() {
  const { caseId } = useParams<{ caseId: string }>();
  const [data, setData] = useState<DevilsAdvocateResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'brief' | 'counter_evidence' | 'vulnerabilities' | 'suppression'>('brief');
  const [availableHypotheses, setAvailableHypotheses] = useState<Array<{ id: number; title: string }>>([]);
  const [selectedCounterId, setSelectedCounterId] = useState<number | undefined>(undefined);

  const fetchDevilsAdvocate = async (counterId?: number) => {
    if (!caseId) return;
    try {
      setLoading(true);
      const res = await decisionQualityService.getDevilsAdvocateView(caseId, counterId);
      setData(res);
      if (res.counter_hypothesis && !selectedCounterId) {
        setSelectedCounterId(res.counter_hypothesis.id);
      }
    } catch (err) {
      console.error("Failed to load trial defense stress-test:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (caseId) {
      fetchDevilsAdvocate(selectedCounterId);
      hypothesisService.getHypothesesForCase(caseId).then((hyps) => {
        setAvailableHypotheses(hyps.map((h: any) => ({ id: h.id, title: h.title })));
      }).catch(() => {});
    }
  }, [caseId, selectedCounterId]);

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#eae4d9]">
        <div>
          <div className="text-[11px] font-mono tracking-widest text-[#d93829] uppercase font-bold mb-1 flex items-center gap-1.5">
            <Scale className="w-3.5 h-3.5 text-[#d93829]" />
            <span>Adversarial Defense Stress-Test • Trial Readiness Review</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-serif font-bold text-[#191410]">
            Trial Defense Counter-Case & Stress-Test
          </h1>
          <p className="text-xs text-[#6e665d] mt-1 max-w-3xl">
            Stress-tests your prime theory against reasonable doubt: systematically assembles the defense attorney's strongest counter-arguments using the exact same case exhibits.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchDevilsAdvocate(selectedCounterId)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#faf7f2] hover:bg-[#eae4d9] text-[#191410] rounded-full text-xs font-bold transition-all border border-[#d8d0c5] cursor-pointer shadow-xs"
            title="Re-run stress test"
          >
            <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin text-[#d93829]")} />
            <span>Re-Run Test</span>
          </button>
          <Link
            to={`/cases/${caseId}/hypotheses`}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-[#191410] hover:bg-[#2e261f] text-white rounded-full text-xs font-bold transition-all shadow-xs cursor-pointer"
          >
            <span>Back to Suspects & Theories</span>
          </Link>
        </div>
      </div>

      {/* Comparison Head-to-Head Banner */}
      {data && data.leading_hypothesis && data.counter_hypothesis && (
        <div className="bg-[#faf7f2] p-5 rounded-3xl border border-[#eae4d9] flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs font-mono shadow-xs">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="p-3.5 rounded-2xl bg-white border border-[#eae4d9] space-y-1 min-w-[220px] shadow-xs">
              <div className="text-[10px] text-blue-700 uppercase font-bold flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 text-blue-600" />
                <span>#1 Prosecution Prime Lead</span>
              </div>
              <div className="font-serif font-bold text-sm text-[#191410] truncate max-w-[240px]">
                {data.leading_hypothesis.title}
              </div>
              <div className="text-blue-800 font-bold text-xs">
                {data.leading_hypothesis.score_pct}% Case Strength
              </div>
            </div>

            <div className="text-[#6e665d] font-bold text-lg px-2">VS</div>

            <div className="p-3.5 rounded-2xl bg-white border border-rose-200 space-y-1 min-w-[220px] shadow-xs">
              <div className="text-[10px] text-rose-700 uppercase font-bold flex items-center gap-1">
                <ShieldAlert className="w-3 h-3 text-rose-600" />
                <span>#2 Defense Alternative Theory</span>
              </div>
              <div className="font-serif font-bold text-sm text-[#191410] truncate max-w-[240px]">
                {data.counter_hypothesis.title}
              </div>
              <div className="text-rose-700 font-bold text-xs">
                {data.counter_hypothesis.score_pct}% Counter Strength
              </div>
            </div>
          </div>

          {availableHypotheses.length > 2 && (
            <div className="flex items-center gap-2 bg-white px-3 py-2 rounded-2xl border border-[#eae4d9] shadow-2xs">
              <span className="text-[#6e665d] font-serif font-semibold">Stress-test against:</span>
              <select
                value={selectedCounterId || ''}
                onChange={(e) => setSelectedCounterId(Number(e.target.value))}
                className="p-1 rounded-xl bg-[#faf7f2] border border-[#d8d0c5] text-[#191410] text-xs font-mono focus:outline-none focus:border-[#d93829]"
              >
                {availableHypotheses
                  .filter((h) => !data?.leading_hypothesis || h.id !== data.leading_hypothesis.id)
                  .map((h) => (
                    <option key={h.id} value={h.id}>
                      {h.title}
                    </option>
                  ))}
              </select>
            </div>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-[#eae4d9] pb-1 overflow-x-auto">
        <button
          onClick={() => setActiveTab('brief')}
          className={cn(
            "px-4 py-2.5 rounded-xl font-serif text-xs font-bold transition-all flex items-center gap-2 cursor-pointer whitespace-nowrap",
            activeTab === 'brief'
              ? "bg-[#d93829] text-white shadow-xs"
              : "text-[#6e665d] hover:bg-[#faf7f2] hover:text-[#191410]"
          )}
        >
          <ShieldAlert className="w-3.5 h-3.5" />
          <span>1. Legal Defense Brief</span>
        </button>

        <button
          onClick={() => setActiveTab('counter_evidence')}
          className={cn(
            "px-4 py-2.5 rounded-xl font-serif text-xs font-bold transition-all flex items-center gap-2 cursor-pointer whitespace-nowrap",
            activeTab === 'counter_evidence'
              ? "bg-[#d93829] text-white shadow-xs"
              : "text-[#6e665d] hover:bg-[#faf7f2] hover:text-[#191410]"
          )}
        >
          <BookOpen className="w-3.5 h-3.5" />
          <span>2. Corroborating Points ({data?.counter_corroborating_points.length || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab('vulnerabilities')}
          className={cn(
            "px-4 py-2.5 rounded-xl font-serif text-xs font-bold transition-all flex items-center gap-2 cursor-pointer whitespace-nowrap",
            activeTab === 'vulnerabilities'
              ? "bg-[#d93829] text-white shadow-xs"
              : "text-[#6e665d] hover:bg-[#faf7f2] hover:text-[#191410]"
          )}
        >
          <Scale className="w-3.5 h-3.5" />
          <span>3. Lead Vulnerabilities ({data?.lead_vulnerabilities.length || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab('suppression')}
          className={cn(
            "px-4 py-2.5 rounded-xl font-serif text-xs font-bold transition-all flex items-center gap-2 cursor-pointer whitespace-nowrap",
            activeTab === 'suppression'
              ? "bg-[#d93829] text-white shadow-xs"
              : "text-[#6e665d] hover:bg-[#faf7f2] hover:text-[#191410]"
          )}
        >
          <TrendingDown className="w-3.5 h-3.5" />
          <span>4. Evidence Exclusion Test</span>
          {data?.suppression_simulation?.rank_flipped && (
            <span className="w-2 h-2 rounded-full bg-red-600 animate-ping" />
          )}
        </button>
      </div>

      {/* Main Tab Content */}
      <div className="space-y-4">
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center gap-2 text-[#d93829]">
            <RefreshCw className="w-8 h-8 animate-spin" />
            <span className="text-xs font-mono text-[#6e665d]">Simulating trial defense challenges & suppression stress-tests...</span>
          </div>
        ) : !data || !data.success ? (
          <div className="p-12 text-center text-[#8c8276] text-xs font-mono bg-white rounded-3xl border border-[#eae4d9]">
            {data?.message || "Unable to assemble trial defense counter-case. Ensure case exhibits are evaluated."}
          </div>
        ) : activeTab === 'brief' ? (
          /* TAB 1: STRUCTURED LEGAL CHALLENGE BRIEF */
          <div className="space-y-4">
            {/* Executive Challenge */}
            <div className="p-5 rounded-3xl border border-rose-200 bg-rose-50/50 space-y-2 shadow-xs">
              <div className="text-xs font-serif font-bold text-rose-800 uppercase tracking-wider flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-600" />
                <span>1. Executive Defense Challenge to Prosecution Theory</span>
              </div>
              <p className="text-xs text-[#191410] leading-relaxed font-sans">
                {data.legal_challenge_brief?.executive_challenge}
              </p>
            </div>

            {/* Counter-Case Factual Narrative */}
            <div className="p-5 rounded-3xl border border-[#eae4d9] bg-white space-y-2 shadow-xs">
              <div className="text-xs font-serif font-bold text-blue-800 uppercase tracking-wider flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-blue-600" />
                <span>2. Plausible Alternative Narrative Creating Reasonable Doubt</span>
              </div>
              <p className="text-xs text-[#191410] leading-relaxed font-sans">
                {data.legal_challenge_brief?.counter_case_narrative}
              </p>
            </div>

            {/* Defense Cross-Examination Angles */}
            <div className="p-5 rounded-3xl border border-[#eae4d9] bg-white space-y-3 shadow-xs">
              <div className="text-xs font-serif font-bold text-amber-900 uppercase tracking-wider flex items-center gap-2">
                <Scale className="w-4 h-4 text-amber-700" />
                <span>3. Anticipated Defense Cross-Examination Angles in Court</span>
              </div>
              <div className="space-y-2">
                {data.legal_challenge_brief?.defense_cross_examination_angles.map((angle, idx) => (
                  <div key={idx} className="flex items-start gap-2.5 text-xs text-[#191410] p-2.5 rounded-2xl bg-[#faf7f2] border border-[#eae4d9]">
                    <span className="w-5 h-5 rounded-full bg-amber-100 border border-amber-300 text-amber-900 flex items-center justify-center text-[10px] font-mono shrink-0 font-bold">
                      {idx + 1}
                    </span>
                    <p className="leading-relaxed font-sans">{angle}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Stress-Test Recommendations for Prosecution */}
            <div className="p-5 rounded-3xl border border-emerald-200 bg-emerald-50/50 space-y-3 shadow-xs">
              <div className="text-xs font-serif font-bold text-emerald-900 uppercase tracking-wider flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-700" />
                <span>4. Pre-Trial Case Fortification Steps (How to Close These Gaps)</span>
              </div>
              <div className="space-y-2">
                {data.legal_challenge_brief?.stress_test_recommendations.map((rec, idx) => (
                  <div key={idx} className="flex items-start gap-2.5 text-xs text-emerald-950 p-2.5 rounded-2xl bg-white border border-emerald-200">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <p className="leading-relaxed font-sans">{rec}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : activeTab === 'counter_evidence' ? (
          /* TAB 2: CORROBORATING POINTS */
          <div className="space-y-3">
            {data.counter_corroborating_points.length === 0 ? (
              <div className="p-12 text-center text-[#8c8276] text-xs font-mono bg-white rounded-3xl border border-[#eae4d9]">
                No corroborating exhibits found for this alternative in the current file.
              </div>
            ) : (
              data.counter_corroborating_points.map((point) => (
                <div 
                  key={point.evidence_id}
                  className="p-4 rounded-3xl border border-[#eae4d9] bg-white space-y-2 hover:border-[#d93829]/40 transition-all shadow-xs"
                >
                  <div className="flex items-center justify-between gap-2 text-[10px] font-mono border-b border-[#eae4d9] pb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-[#191410]">Exhibit #{point.evidence_id}</span>
                      <span className="text-[#6e665d]">({point.evidence_title})</span>
                      <span className="px-2 py-0.5 rounded-full bg-[#faf7f2] border border-[#eae4d9] uppercase font-semibold text-[#191410]">
                        {point.evidence_type}
                      </span>
                    </div>
                    <span className="px-2.5 py-0.5 rounded-full bg-rose-50 text-rose-800 border border-rose-200 font-bold uppercase">
                      {point.role_in_counter_case}
                    </span>
                  </div>

                  {point.counter_rationale && (
                    <p className="text-xs text-[#191410] leading-relaxed font-sans">
                      {point.counter_rationale}
                    </p>
                  )}

                  {point.quoted_source_span && (
                    <div className="p-3 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] text-[11px] font-mono text-blue-800 italic flex items-start gap-1.5">
                      <Quote className="w-3.5 h-3.5 text-blue-600 shrink-0 mt-0.5" />
                      <span>"{point.quoted_source_span}"</span>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        ) : activeTab === 'vulnerabilities' ? (
          /* TAB 3: PROSECUTION LEAD VULNERABILITIES */
          <div className="space-y-3">
            {data.lead_vulnerabilities.length === 0 ? (
              <div className="p-12 text-center text-emerald-800 text-xs font-mono bg-white rounded-3xl border border-[#eae4d9] flex flex-col items-center gap-2">
                <ShieldCheck className="w-8 h-8 text-emerald-600" />
                <span>No glaring procedural vulnerabilities detected in current lead exhibits.</span>
              </div>
            ) : (
              data.lead_vulnerabilities.map((vuln) => (
                <div
                  key={vuln.evidence_id}
                  className="p-4 rounded-3xl border border-amber-200 bg-amber-50/40 space-y-2.5 shadow-xs"
                >
                  <div className="flex items-center justify-between text-[10px] font-mono border-b border-amber-200 pb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-[#191410]">Exhibit #{vuln.evidence_id}</span>
                      <span className="text-[#6e665d]">({vuln.evidence_title})</span>
                    </div>
                    <span className="text-amber-900 font-bold">
                      Weight in Lead: {vuln.contribution_to_lead} pts
                    </span>
                  </div>

                  <div className="space-y-1">
                    <div className="text-[10px] font-mono text-rose-800 uppercase font-semibold">Identified Weaknesses:</div>
                    <ul className="list-disc list-inside text-xs text-rose-900 space-y-0.5">
                      {vuln.vulnerabilities.map((v, i) => (
                        <li key={i}>{v}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="pt-2 border-t border-amber-200 text-xs text-[#191410] font-sans">
                    <span className="font-semibold text-amber-900">Defense Cross-Examination Vector: </span>
                    {vuln.defense_challenge_vector}
                  </div>
                </div>
              ))
            )}
          </div>
        ) : (
          /* TAB 4: SUPPRESSION STRESS-TEST */
          <div className="space-y-4">
            {data.suppression_simulation ? (
              <div className="p-5 rounded-3xl border border-amber-200 bg-amber-50/40 space-y-4 shadow-xs">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-serif font-bold text-amber-950 uppercase tracking-wider flex items-center gap-2">
                    <TrendingDown className="w-4 h-4 text-amber-700" />
                    <span>Suppression Scenario: Excluding Exhibit #{data.suppression_simulation.suppressed_exhibit_id} ('{data.suppression_simulation.suppressed_exhibit_title}')</span>
                  </div>
                  <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-white border border-[#eae4d9] text-[#6e665d]">
                    Sec. 65B BSA / Sec. 27 IEA Motion
                  </span>
                </div>

                <p className="text-xs text-[#191410] leading-relaxed font-sans">
                  {data.suppression_simulation.impact_summary}
                </p>

                {/* Before vs After Scores Comparison */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 font-mono text-xs">
                  <div className="p-4 rounded-2xl bg-white border border-[#eae4d9] space-y-1 shadow-xs">
                    <div className="text-[10px] text-[#6e665d] uppercase">Prosecution Lead Strength</div>
                    <div className="flex items-center gap-2">
                      <span className="text-[#8c8276] line-through">{data.suppression_simulation.original_lead_score}%</span>
                      <ArrowRight className="w-3.5 h-3.5 text-rose-600" />
                      <span className="text-rose-700 font-bold text-base">{data.suppression_simulation.new_lead_score}%</span>
                      <span className="text-[10px] text-rose-700">(-{data.suppression_simulation.score_drop_pct}%)</span>
                    </div>
                  </div>

                  <div className="p-4 rounded-2xl bg-white border border-[#eae4d9] space-y-1 shadow-xs">
                    <div className="text-[10px] text-[#6e665d] uppercase">Alternative Theory Strength</div>
                    <div className="flex items-center gap-2">
                      <span className="text-[#8c8276] line-through">{data.suppression_simulation.original_counter_score}%</span>
                      <ArrowRight className="w-3.5 h-3.5 text-emerald-600" />
                      <span className="text-emerald-700 font-bold text-base">{data.suppression_simulation.new_counter_score}%</span>
                    </div>
                  </div>
                </div>

                {data.suppression_simulation.rank_flipped && (
                  <div className="p-4 rounded-2xl bg-rose-100 border border-rose-300 text-rose-900 text-xs font-mono flex items-center gap-2.5">
                    <ShieldAlert className="w-5 h-5 text-rose-600 shrink-0" />
                    <span>
                      <strong>CRITICAL PIVOT DETECTED:</strong> Excluding this single exhibit causes the entire prosecution ranking to invert! The alternative suspect becomes #1. Prioritize Section 65B certification and search warrant audit immediately.
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-12 text-center text-[#8c8276] text-xs font-mono bg-white rounded-3xl border border-[#eae4d9]">
                No single exhibit suppression causes a meaningful probability shift in the current matrix.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

