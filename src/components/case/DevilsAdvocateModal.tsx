import React, { useState, useEffect } from 'react';
import { 
  Scale, ShieldAlert, ShieldCheck, CheckCircle2, 
  X, RefreshCw, BookOpen, Quote, 
  ArrowRight, TrendingDown
} from 'lucide-react';
import { DevilsAdvocateResponse } from '../../types';
import { decisionQualityService, hypothesisService } from '../../services';
import { cn } from '../../utils';

interface DevilsAdvocateModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  allHypotheses?: any[];
  initialTargetId?: number;
}

export const DevilsAdvocateModal: React.FC<DevilsAdvocateModalProps> = ({
  isOpen,
  onClose,
  caseId,
  allHypotheses,
  initialTargetId,
}) => {
  const [data, setData] = useState<DevilsAdvocateResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'brief' | 'counter_evidence' | 'vulnerabilities' | 'suppression'>('brief');
  const [availableHypotheses, setAvailableHypotheses] = useState<Array<{ id: number; title: string }>>([]);
  const [selectedCounterId, setSelectedCounterId] = useState<number | undefined>(initialTargetId);

  const fetchDevilsAdvocate = async (counterId?: number) => {
    try {
      setLoading(true);
      const res = await decisionQualityService.getDevilsAdvocateView(caseId, counterId);
      setData(res);
      if (res.counter_hypothesis && !selectedCounterId) {
        setSelectedCounterId(res.counter_hypothesis.id);
      }
    } catch (err) {
      console.error("Failed to load Devil's Advocate stress-test:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchDevilsAdvocate(selectedCounterId || initialTargetId);
      if (allHypotheses && allHypotheses.length > 0) {
        setAvailableHypotheses(allHypotheses.map((h: any) => ({ id: h.id, title: h.title })));
      } else {
        hypothesisService.getHypothesesForCase(caseId).then((hyps) => {
          setAvailableHypotheses(hyps.map((h: any) => ({ id: h.id, title: h.title })));
        }).catch(() => {});
      }
    }
  }, [isOpen, caseId, selectedCounterId, initialTargetId, allHypotheses]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-4 overflow-y-auto">
      <div className="bg-white border border-[#eae4d9] rounded-2xl w-full max-w-5xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden animate-scaleUp text-[#191410]">
        
        {/* ============================================================ */}
        {/* MODAL HEADER                                                 */}
        {/* ============================================================ */}
        <div className="p-4 sm:p-5 bg-[#faf7f2] border-b border-[#eae4d9] flex items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-red-50 border border-red-200 flex items-center justify-center text-[#d93829]">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm sm:text-base font-serif font-bold text-[#191410]">
                  Trial Defense Counter-Case & Stress-Test
                </h3>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-red-50 text-red-800 border border-red-200">
                  Defense Cross-Examination Review
                </span>
              </div>
              <p className="text-xs text-[#6e665d] mt-0.5">
                Stress-tests your case theory against reasonable doubt: assembles the defense attorney's strongest counter-argument using the same case exhibits.
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-xl hover:bg-[#eae4d9]/50 text-[#6e665d] hover:text-[#191410] transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* ============================================================ */}
        {/* COMPARISON BAR & ALTERNATIVE SELECTOR                        */}
        {/* ============================================================ */}
        {data && data.leading_hypothesis && data.counter_hypothesis && (
          <div className="bg-[#faf7f2] p-4 border-b border-[#eae4d9] flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs font-mono shrink-0">
            {/* Lead vs Counter */}
            <div className="flex items-center gap-3 flex-wrap">
              <div className="p-2.5 rounded-xl bg-white border border-[#eae4d9] space-y-0.5 min-w-[200px] shadow-xs">
                <div className="text-[10px] text-blue-700 uppercase font-bold">#1 Prime Suspect Theory</div>
                <div className="font-semibold text-[#191410] truncate max-w-[220px]">{data.leading_hypothesis.title}</div>
                <div className="text-blue-700 font-bold">{data.leading_hypothesis.score_pct}% Case Strength</div>
              </div>

              <div className="text-[#6e665d] font-bold text-lg">VS</div>

              <div className="p-2.5 rounded-xl bg-white border border-red-200 space-y-0.5 min-w-[200px] shadow-xs">
                <div className="text-[10px] text-red-700 uppercase font-bold">#2 Defense Alternative Theory</div>
                <div className="font-semibold text-[#191410] truncate max-w-[220px]">{data.counter_hypothesis.title}</div>
                <div className="text-red-700 font-bold">{data.counter_hypothesis.score_pct}% Strength</div>
              </div>
            </div>

            {/* Change Target Counter Hypothesis */}
            {availableHypotheses.length > 2 && (
              <div className="flex items-center gap-2">
                <span className="text-[#6e665d]">Stress-test against:</span>
                <select
                  value={selectedCounterId || ''}
                  onChange={(e) => setSelectedCounterId(Number(e.target.value))}
                  className="p-1.5 rounded-xl bg-white border border-[#eae4d9] text-[#191410] text-xs font-mono focus:outline-none focus:border-[#d93829]"
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

        {/* ============================================================ */}
        {/* TABS NAVIGATION                                              */}
        {/* ============================================================ */}
        <div className="flex items-center gap-1 px-4 sm:px-6 border-b border-[#eae4d9] bg-white text-xs font-mono shrink-0 overflow-x-auto">
          <button
            onClick={() => setActiveTab('brief')}
            className={cn(
              "px-3.5 py-3 border-b-2 font-bold transition-all flex items-center gap-1.5 cursor-pointer whitespace-nowrap",
              activeTab === 'brief'
                ? "border-[#d93829] text-[#d93829] bg-red-50/50"
                : "border-transparent text-[#6e665d] hover:text-[#191410]"
            )}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>1. Legal Defense Brief</span>
          </button>

          <button
            onClick={() => setActiveTab('counter_evidence')}
            className={cn(
              "px-3.5 py-3 border-b-2 font-bold transition-all flex items-center gap-1.5 cursor-pointer whitespace-nowrap",
              activeTab === 'counter_evidence'
                ? "border-[#d93829] text-[#d93829] bg-red-50/50"
                : "border-transparent text-[#6e665d] hover:text-[#191410]"
            )}
          >
            <BookOpen className="w-3.5 h-3.5 text-blue-700" />
            <span>2. Corroborating Points ({data?.counter_corroborating_points.length || 0})</span>
          </button>

          <button
            onClick={() => setActiveTab('vulnerabilities')}
            className={cn(
              "px-3.5 py-3 border-b-2 font-bold transition-all flex items-center gap-1.5 cursor-pointer whitespace-nowrap",
              activeTab === 'vulnerabilities'
                ? "border-[#d93829] text-[#d93829] bg-red-50/50"
                : "border-transparent text-[#6e665d] hover:text-[#191410]"
            )}
          >
            <Scale className="w-3.5 h-3.5 text-amber-700" />
            <span>3. Lead Vulnerabilities ({data?.lead_vulnerabilities.length || 0})</span>
          </button>

          <button
            onClick={() => setActiveTab('suppression')}
            className={cn(
              "px-3.5 py-3 border-b-2 font-bold transition-all flex items-center gap-1.5 cursor-pointer whitespace-nowrap",
              activeTab === 'suppression'
                ? "border-[#d93829] text-[#d93829] bg-red-50/50"
                : "border-transparent text-[#6e665d] hover:text-[#191410]"
            )}
          >
            <TrendingDown className="w-3.5 h-3.5 text-amber-700" />
            <span>4. Evidence Exclusion Test</span>
            {data?.suppression_simulation?.rank_flipped && (
              <span className="w-2 h-2 rounded-full bg-red-600 animate-ping" />
            )}
          </button>
        </div>

        {/* ============================================================ */}
        {/* TAB CONTENTS                                                 */}
        {/* ============================================================ */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
          {loading ? (
            <div className="py-16 flex flex-col items-center justify-center gap-2 text-[#d93829]">
              <RefreshCw className="w-8 h-8 animate-spin" />
              <span className="text-xs font-mono text-[#6e665d]">Simulating counter-case & suppression stress-tests...</span>
            </div>
          ) : !data || !data.success ? (
            <div className="p-8 text-center text-[#8c8276] text-xs font-mono">
              {data?.message || "Unable to assemble Devil's Advocate counter-case."}
            </div>
          ) : activeTab === 'brief' ? (
            /* TAB 1: STRUCTURED LEGAL CHALLENGE BRIEF */
            <div className="space-y-4">
              {/* Executive Challenge */}
              <div className="p-4 rounded-xl border border-red-200 bg-red-50/40 space-y-2">
                <div className="text-xs font-bold text-red-700 uppercase tracking-wider flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4" /> 1. Executive Defense Challenge
                </div>
                <p className="text-xs text-[#191410] leading-relaxed font-sans">
                  {data.legal_challenge_brief?.executive_challenge}
                </p>
              </div>

              {/* Counter-Case Factual Narrative */}
              <div className="p-4 rounded-xl border border-[#eae4d9] bg-white space-y-2 shadow-xs">
                <div className="text-xs font-bold text-blue-700 uppercase tracking-wider flex items-center gap-2">
                  <BookOpen className="w-4 h-4" /> 2. Grounded Alternative Narrative
                </div>
                <p className="text-xs text-[#191410] leading-relaxed font-sans">
                  {data.legal_challenge_brief?.counter_case_narrative}
                </p>
              </div>

              {/* Defense Cross-Examination Angles */}
              <div className="p-4 rounded-xl border border-[#eae4d9] bg-white space-y-2.5 shadow-xs">
                <div className="text-xs font-bold text-amber-700 uppercase tracking-wider flex items-center gap-2">
                  <Scale className="w-4 h-4" /> 3. Anticipated Defense Cross-Examination Lines
                </div>
                <div className="space-y-2">
                  {data.legal_challenge_brief?.defense_cross_examination_angles.map((angle, idx) => (
                    <div key={idx} className="flex items-start gap-2.5 text-xs text-[#191410]">
                      <span className="w-5 h-5 rounded-full bg-amber-50 border border-amber-200 text-amber-800 flex items-center justify-center text-[10px] font-mono shrink-0 mt-0.5 font-bold">
                        {idx + 1}
                      </span>
                      <p className="leading-relaxed font-sans">{angle}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Stress-Test Recommendations for Prosecution */}
              <div className="p-4 rounded-xl border border-emerald-200 bg-emerald-50/40 space-y-2.5">
                <div className="text-xs font-bold text-emerald-800 uppercase tracking-wider flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" /> 4. Actionable Stress-Testing Steps (Pre-Trial Fortification)
                </div>
                <div className="space-y-2">
                  {data.legal_challenge_brief?.stress_test_recommendations.map((rec, idx) => (
                    <div key={idx} className="flex items-start gap-2.5 text-xs text-emerald-900">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                      <p className="leading-relaxed font-sans">{rec}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : activeTab === 'counter_evidence' ? (
            /* TAB 2: CORROBORATING POINTS FOR COUNTER-HYPOTHESIS */
            <div className="space-y-3">
              <div className="text-xs font-mono text-[#6e665d] flex items-center justify-between pb-1 border-b border-[#eae4d9]">
                <span>Exhibits that corroborate the alternative hypothesis or contradict the prosecution lead:</span>
                <span>{data.counter_corroborating_points.length} findings identified</span>
              </div>

              {data.counter_corroborating_points.length === 0 ? (
                <div className="p-8 text-center text-[#8c8276] text-xs font-mono">
                  No corroborating exhibits found for this alternative in the current file.
                </div>
              ) : (
                data.counter_corroborating_points.map((point) => (
                  <div 
                    key={point.evidence_id}
                    className="p-3.5 rounded-xl border border-[#eae4d9] bg-white space-y-2 hover:border-[#d93829]/40 transition-all shadow-xs"
                  >
                    <div className="flex items-center justify-between gap-2 text-[10px] font-mono border-b border-[#eae4d9] pb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-[#191410]">Exhibit #{point.evidence_id}</span>
                        <span className="text-[#6e665d]">({point.evidence_title})</span>
                        <span className="px-1.5 py-0.5 rounded bg-[#faf7f2] border border-[#eae4d9] uppercase font-semibold text-[#191410]">
                          {point.evidence_type}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded-full bg-red-50 text-red-800 border border-red-200 font-bold uppercase">
                          {point.role_in_counter_case}
                        </span>
                        <span className="text-amber-700 font-bold">
                          Weight: +{point.probative_weight}
                        </span>
                      </div>
                    </div>

                    {point.counter_rationale && (
                      <p className="text-xs text-[#191410] leading-relaxed font-sans">
                        {point.counter_rationale}
                      </p>
                    )}

                    {point.quoted_source_span && (
                      <div className="p-2 rounded-lg bg-[#faf7f2] border border-[#eae4d9] text-[11px] font-mono text-blue-700 italic flex items-start gap-1.5">
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
              <div className="text-xs font-mono text-[#6e665d] pb-1 border-b border-[#eae4d9]">
                Evidentiary weak points, missing certificates, or unverified claims supporting the current lead:
              </div>

              {data.lead_vulnerabilities.length === 0 ? (
                <div className="p-8 text-center text-emerald-700 text-xs font-mono flex flex-col items-center gap-2">
                  <ShieldCheck className="w-8 h-8 text-emerald-600" />
                  <span>No glaring procedural vulnerabilities detected in current lead exhibits.</span>
                </div>
              ) : (
                data.lead_vulnerabilities.map((vuln) => (
                  <div
                    key={vuln.evidence_id}
                    className="p-3.5 rounded-xl border border-amber-200 bg-amber-50/30 space-y-2.5 shadow-xs"
                  >
                    <div className="flex items-center justify-between text-[10px] font-mono border-b border-amber-200/60 pb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-[#191410]">Exhibit #{vuln.evidence_id}</span>
                        <span className="text-[#6e665d]">({vuln.evidence_title})</span>
                      </div>
                      <span className="text-amber-800 font-bold">
                        Contribution to Lead: {vuln.contribution_to_lead} pts
                      </span>
                    </div>

                    <div className="space-y-1">
                      <div className="text-[10px] font-mono text-red-700 uppercase font-semibold">Identified Weaknesses:</div>
                      <ul className="list-disc list-inside text-xs text-red-800 space-y-0.5">
                        {vuln.vulnerabilities.map((v, i) => (
                          <li key={i}>{v}</li>
                        ))}
                      </ul>
                    </div>

                    <div className="pt-1.5 border-t border-amber-200/60 text-xs text-[#191410] font-sans">
                      <span className="font-semibold text-amber-800">Defense Attack Angle: </span>
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
                <div className="space-y-4">
                  <div className="p-4 rounded-xl border border-amber-200 bg-amber-50/40 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="text-xs font-bold text-amber-900 uppercase tracking-wider flex items-center gap-2">
                        <TrendingDown className="w-4 h-4 text-amber-700" />
                        Suppression Scenario: Excluding Exhibit #{data.suppression_simulation.suppressed_exhibit_id} ('{data.suppression_simulation.suppressed_exhibit_title}')
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white border border-[#eae4d9] text-[#6e665d]">
                        Sec. 65B / 27 IEA Motion
                      </span>
                    </div>

                    <p className="text-xs text-[#191410] leading-relaxed font-sans">
                      {data.suppression_simulation.impact_summary}
                    </p>

                    {/* Before vs After Scores Comparison */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 font-mono text-xs">
                      <div className="p-3 rounded-xl bg-white border border-[#eae4d9] space-y-1 shadow-xs">
                        <div className="text-[10px] text-[#6e665d] uppercase">Prosecution Lead Score</div>
                        <div className="flex items-center gap-2">
                          <span className="text-[#8c8276] line-through">{data.suppression_simulation.original_lead_score}%</span>
                          <ArrowRight className="w-3.5 h-3.5 text-red-600" />
                          <span className="text-red-700 font-bold text-sm">{data.suppression_simulation.new_lead_score}%</span>
                          <span className="text-[10px] text-red-700">(-{data.suppression_simulation.score_drop_pct}%)</span>
                        </div>
                      </div>

                      <div className="p-3 rounded-xl bg-white border border-[#eae4d9] space-y-1 shadow-xs">
                        <div className="text-[10px] text-[#6e665d] uppercase">Counter-Hypothesis Score</div>
                        <div className="flex items-center gap-2">
                          <span className="text-[#8c8276] line-through">{data.suppression_simulation.original_counter_score}%</span>
                          <ArrowRight className="w-3.5 h-3.5 text-emerald-600" />
                          <span className="text-emerald-700 font-bold text-sm">{data.suppression_simulation.new_counter_score}%</span>
                        </div>
                      </div>
                    </div>

                    {data.suppression_simulation.rank_flipped && (
                      <div className="p-3 rounded-xl bg-red-100 border border-red-300 text-red-900 text-xs font-mono flex items-center gap-2">
                        <ShieldAlert className="w-4 h-4 text-red-600 shrink-0" />
                        <span>
                          CRITICAL PIVOT: Excluding this single exhibit causes the entire prosecution ranking to invert! The alternative suspect becomes #1.
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="p-8 text-center text-[#8c8276] text-xs font-mono">
                  No single exhibit suppression causes a meaningful probability drop in the current matrix.
                </div>
              )}
            </div>
          )}
        </div>

        {/* ============================================================ */}
        {/* MODAL FOOTER                                                 */}
        {/* ============================================================ */}
        <div className="p-3 bg-[#faf7f2] border-t border-[#eae4d9] flex items-center justify-between text-xs font-mono text-[#6e665d] shrink-0">
          <span>Heuer Analysis of Competing Hypotheses • Stress-Testing Standard</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl bg-white hover:bg-[#faf7f2] border border-[#eae4d9] text-[#191410] text-xs font-semibold cursor-pointer shadow-xs"
          >
            Close Dossier
          </button>
        </div>
      </div>
    </div>
  );
};
