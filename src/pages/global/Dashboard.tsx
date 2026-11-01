import { useEffect, useState } from 'react';
import { caseService, prioritiesService } from '../../services';
import { Case, GlobalCasePriority } from '../../types';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { Briefcase, AlertTriangle, FileText, CheckSquare, ChevronRight, Activity, ArrowUpRight, Scale, Clock, Timer, Users } from 'lucide-react';
import { Link } from 'react-router-dom';
import { cn } from '../../utils';
import { GeographicCaseMap } from '../../components/map/GeographicCaseMap';

export function Dashboard() {
  const [cases, setCases] = useState<Case[]>([]);
  const [globalPriorities, setGlobalPriorities] = useState<GlobalCasePriority[]>([]);
  const [loadingPriorities, setLoadingPriorities] = useState(false);

  useEffect(() => {
    caseService.getCases().then(setCases);
    setLoadingPriorities(true);
    prioritiesService.getGlobalPriorities()
      .then(setGlobalPriorities)
      .catch((err) => console.warn('Global priorities fetch:', err))
      .finally(() => setLoadingPriorities(false));
  }, []);

  const activeCases = cases.filter(c => c.status === 'Active' || c.status === 'Under Investigation');


  return (
    <div className="space-y-8 pb-20 max-w-7xl mx-auto">
      {/* Dashboard Header */}
      <div>
        <div className="text-[11px] font-mono tracking-widest text-[#d93829] uppercase font-bold mb-1">
          Operations Overview
        </div>
        <h1 className="text-3xl lg:text-4xl font-serif font-bold text-[#191410] tracking-tight">
          Global Intelligence Dashboard
        </h1>
        <p className="text-sm text-[#6e665d] mt-1">
          Active investigations, real-time forensic processing queues, and ACH analytical status.
        </p>
      </div>

      {/* Top Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Active Cases', value: activeCases.length || 4, icon: Briefcase, color: 'text-[#d93829]', bg: 'bg-[#fdeee9] border-[#d93829]/20' },
          { label: 'Pending Analysis', value: 12, icon: Activity, color: 'text-purple-600', bg: 'bg-purple-50 border-purple-200' },
          { label: 'Open Contradictions', value: 8, icon: AlertTriangle, color: 'text-amber-600', bg: 'bg-amber-50 border-amber-200' },
          { label: 'Investigation Tasks', value: 15, icon: CheckSquare, color: 'text-emerald-600', bg: 'bg-emerald-50 border-emerald-200' }
        ].map((stat, i) => (
          <div 
            key={i} 
            className="flex items-center p-5 gap-4 rounded-2xl bg-white border border-[#eae4d9] shadow-xs hover:-translate-y-0.5 transition-all"
          >
            <div className={cn("w-12 h-12 rounded-xl flex items-center justify-center border", stat.bg)}>
              <stat.icon className={cn("w-6 h-6", stat.color)} />
            </div>
            <div>
              <div className="text-2xl font-serif font-bold text-[#191410]">{stat.value}</div>
              <div className="text-xs text-[#6e665d] uppercase tracking-wider font-semibold mt-0.5">{stat.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Statutory Filing Deadlines Across Dockets */}
      {globalPriorities.length > 0 && (
        <div className="rounded-3xl bg-white border border-[#eae4d9] shadow-xs p-6 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#f0ebe1] pb-4">
            <div>
              <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#d93829] flex items-center gap-1.5 mb-0.5">
                <Timer className="w-3.5 h-3.5" />
                <span>Default Bail Statutory Watch</span>
              </div>
              <h3 className="font-serif font-bold text-lg text-[#191410]">
                Impending Deadlines & Remand Countdowns
              </h3>
              <p className="text-xs text-[#6e665d]">
                Ranked by nearest Section 167(2) CrPC / Section 187(3) BNSS chargesheet filing limit across active dockets.
              </p>
            </div>
            <span className="px-3 py-1 bg-amber-50 text-amber-900 border border-amber-300 rounded-full text-xs font-mono font-bold self-start sm:self-auto">
              {globalPriorities.filter(p => p.top_urgency === 'critical' || p.top_urgency === 'urgent').length} Action Required
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {globalPriorities.slice(0, 6).map((item) => (
              <Link
                key={item.case_id}
                to={`/cases/${item.case_id}/priorities`}
                className="p-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] hover:border-[#d93829] transition-all flex flex-col justify-between gap-3 group"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-[10px] font-mono text-[#8c8276]">{item.fir_number}</span>
                    <span className={cn(
                      "px-2 py-0.5 rounded-full text-[9px] font-mono font-bold uppercase",
                      item.top_urgency === 'critical' ? "bg-rose-100 text-rose-800 border border-rose-300" :
                      item.top_urgency === 'urgent' ? "bg-amber-100 text-amber-900 border border-amber-300" :
                      "bg-emerald-50 text-emerald-800 border border-emerald-200"
                    )}>
                      {item.top_urgency}
                    </span>
                  </div>
                  <h4 className="font-serif font-bold text-sm text-[#191410] group-hover:text-[#d93829] transition-colors line-clamp-1">
                    {item.case_title}
                  </h4>
                  {item.has_dates ? (
                    <div className="mt-2 flex items-baseline gap-2">
                      <span className="text-2xl font-mono font-bold text-[#191410]">
                        {item.chargesheet_days_left !== null && item.chargesheet_days_left !== undefined ? item.chargesheet_days_left : '—'}
                      </span>
                      <span className="text-[11px] font-serif text-[#6e665d]">days to chargesheet</span>
                    </div>
                  ) : (
                    <div className="mt-2 text-[11px] font-mono text-amber-800 bg-amber-50 p-1.5 rounded-lg border border-amber-200">
                      Dates missing — configure countdown
                    </div>
                  )}
                  {item.next_action_title && (
                    <p className="text-[11px] text-[#6e665d] mt-1.5 line-clamp-1">
                      • {item.next_action_title}
                    </p>
                  )}
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-[#eae4d9] text-[10px] font-mono text-[#8c8276]">
                  <span>{item.overdue_reports_count} reports overdue</span>
                  <span className="text-[#d93829] font-bold group-hover:underline flex items-center gap-0.5">
                    Today's Priorities <ChevronRight className="w-3 h-3" />
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Cases Table */}
        <div className="lg:col-span-2 space-y-8">
          <div className="rounded-3xl bg-white border border-[#eae4d9] shadow-xs overflow-hidden">
            <div className="p-6 border-b border-[#f0ebe1] flex items-center justify-between">
              <div>
                <h3 className="font-serif font-bold text-lg text-[#191410]">Recent Active Cases</h3>
                <p className="text-xs text-[#6e665d] mt-0.5">Priority criminal dockets under substantive evaluation</p>
              </div>
              <Link 
                to="/cases" 
                className="inline-flex items-center gap-1 px-4 py-1.5 rounded-full bg-[#fdeee9] text-[#d93829] hover:bg-[#d93829] hover:text-white text-xs font-bold transition-colors"
              >
                View All <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-[11px] text-[#8c8276] uppercase tracking-wider bg-[#faf7f2] border-b border-[#eae4d9] font-mono">
                  <tr>
                    <th className="px-6 py-3.5">Case ID & Name</th>
                    <th className="px-6 py-3.5">Status</th>
                    <th className="px-6 py-3.5">Priority</th>
                    <th className="px-6 py-3.5 text-right">Evidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#f0ebe1] text-[#191410]">
                  {cases.slice(0, 4).map((c) => (
                    <tr key={c.id} className="hover:bg-[#faf7f2] transition-colors group">
                      <td className="px-6 py-4">
                        <Link to={`/cases/${c.id}/overview`} className="block">
                          <div className="font-serif font-bold text-sm text-[#191410] group-hover:text-[#d93829] transition-colors">
                            {(c as any).title || c.name}
                          </div>
                          <div className="text-xs font-mono text-[#8c8276] mt-0.5">{c.id}</div>
                        </Link>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider bg-[#fdeee9] text-[#d93829] border border-[#d93829]/20 rounded-full">
                          {c.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={cn(
                          "px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-full border",
                          c.priority === 'High' ? "bg-red-50 text-red-700 border-red-200" : "bg-amber-50 text-amber-700 border-amber-200"
                        )}>
                          {c.priority}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right font-medium whitespace-nowrap">
                        <div className="flex items-center justify-end gap-1.5 text-xs text-[#70685e]">
                          <FileText className="w-3.5 h-3.5 text-[#d93829]" />
                          <span className="font-bold text-[#191410]">{c.evidenceCount || 6}</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Activity Timeline Card */}
          <div className="rounded-3xl bg-white border border-[#eae4d9] shadow-xs p-6">
            <h3 className="font-serif font-bold text-lg text-[#191410] mb-1">Investigation Audit Activity</h3>
            <p className="text-xs text-[#6e665d] mb-5">Chronological system events, forensic uploads, and hypothesis updates</p>

            <div className="space-y-4">
              {[
                { time: '10 mins ago', user: 'PI Kishor Mhaswade', action: 'uploaded Exhibit', target: 'sbi_atm_cctv_swargate_withdrawal.mp4', case: 'FIR-2009-MH-PUN-534' },
                { time: '45 mins ago', user: 'ACH Engine', action: 'derived Prime Accused', target: 'Yogesh Raut (94% Probability)', case: 'FIR-2009-MH-PUN-534' },
                { time: '2 hours ago', user: 'Forensic Lab (FSL Kalina)', action: 'submitted DNA Report', target: '15 STR Loci Allelic Match', case: 'FIR-2009-MH-PUN-534' },
                { time: '5 hours ago', user: 'JMFC Court Pune', action: 'admitted Approver Confession', target: 'Rajesh Chaudhari (Sec 164 CrPC)', case: 'FIR-2009-MH-PUN-534' },
              ].map((act, i) => (
                <div key={i} className="flex gap-4 items-start p-3 rounded-2xl hover:bg-[#faf7f2] transition-colors">
                  <div className="mt-1.5 w-2.5 h-2.5 rounded-full bg-[#d93829] ring-4 ring-[#d93829]/15" />
                  <div className="flex-1">
                    <p className="text-xs text-[#191410]">
                      <span className="font-bold text-[#191410]">{act.user}</span>{' '}
                      <span className="text-[#6e665d]">{act.action}</span>{' '}
                      <span className="font-semibold text-[#d93829]">{act.target}</span>
                    </p>
                    <div className="text-[11px] text-[#8c8276] mt-0.5 flex gap-2">
                      <span>{act.time}</span>
                      <span>•</span>
                      <span className="font-mono text-[#d93829]">{act.case}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Processing Pipeline & Action Required */}
        <div className="space-y-8">
          <div className="rounded-3xl bg-white border border-[#eae4d9] shadow-xs p-6 space-y-5">
            <h3 className="font-serif font-bold text-base text-[#191410]">Evidence Processing Pipeline</h3>

            <div className="space-y-2">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-blue-700">Optical Character Recognition</span>
                <span className="font-mono text-[#191410] font-bold">45%</span>
              </div>
              <div className="h-2 w-full bg-[#faf7f2] rounded-full overflow-hidden border border-[#eae4d9]">
                <div className="h-full bg-blue-600 rounded-full w-[45%]" />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-amber-700">Cellular Tower Hop Queued</span>
                <span className="font-mono text-[#191410] font-bold">12 items</span>
              </div>
              <div className="h-2 w-full bg-[#faf7f2] rounded-full overflow-hidden border border-[#eae4d9]">
                <div className="h-full bg-amber-500 rounded-full w-[25%]" />
              </div>
            </div>
          </div>
          
          {/* Action Required Card */}
          <div className="rounded-3xl border border-red-200 bg-red-50/70 p-6 space-y-3">
            <div className="text-sm font-bold text-red-700 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-600" /> Action Required: Evidentiary Audit
            </div>
            <p className="text-xs text-[#6e665d] leading-relaxed">
              <strong className="text-[#191410] block mb-1">Encrypted Evidence Inspection Required</strong>
              FSL Kalina report pending confirmation of Section 65B electronic certificate compliance.
            </p>
            <button className="px-4 py-2 bg-[#d93829] hover:bg-[#bf2b1d] text-white rounded-full text-xs font-bold shadow-xs transition-colors">
              Review Evidentiary Certificate
            </button>
          </div>
        </div>
      </div>

      {/* Geographic Case Map */}
      <GeographicCaseMap />
    </div>
  );
}
