import { NavLink, useParams, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { caseService } from '../../services';
import { Case } from '../../types';
import { 
  LayoutDashboard, FileText, Network, Clock, 
  Users, AlertTriangle, Lightbulb, CheckSquare, 
  Mic, Map, Bot, BarChart2, Activity, ArrowLeft, Shield
} from 'lucide-react';
import { cn } from '../../utils';

export function CaseSidebar() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const [currentCase, setCurrentCase] = useState<Case | null>(null);

  useEffect(() => {
    if (caseId) {
      caseService.getCaseById(caseId).then(data => {
        if (data) setCurrentCase(data);
      });
    }
  }, [caseId]);

  const caseNavItems = [
    { path: `/cases/${caseId}/overview`, icon: LayoutDashboard, label: 'Overview' },
    { path: `/cases/${caseId}/evidence`, icon: FileText, label: 'Evidence' },
    { path: `/cases/${caseId}/analysis`, icon: Network, label: 'Analysis Workspace' },
    { path: `/cases/${caseId}/timeline`, icon: Clock, label: 'Timeline' },
    { path: `/cases/${caseId}/entities`, icon: Users, label: 'Entities' },
    { path: `/cases/${caseId}/graph`, icon: Network, label: 'Knowledge Graph' },
    { path: `/cases/${caseId}/contradictions`, icon: AlertTriangle, label: 'Contradictions' },
    { path: `/cases/${caseId}/hypotheses`, icon: Lightbulb, label: 'Hypotheses' },
    { path: `/cases/${caseId}/investigation-plan`, icon: CheckSquare, label: 'Investigation Plan' },
    { path: `/cases/${caseId}/interviews`, icon: Mic, label: 'Interviews' },
    { path: `/cases/${caseId}/map`, icon: Map, label: 'Case Map' },
    { path: `/cases/${caseId}/assistant`, icon: Bot, label: 'AI Assistant' },
    { path: `/cases/${caseId}/reports`, icon: BarChart2, label: 'Reports' },
    { path: `/cases/${caseId}/activity`, icon: Activity, label: 'Activity Log' },
  ];

  const caseTitle = currentCase?.title || currentCase?.name || `Investigation Docket #${caseId}`;
  const docketId = currentCase?.id || caseId;

  return (
    <aside className="w-64 bg-white/95 backdrop-blur-md border-r border-[#eae4d9] h-full flex flex-col shrink-0 shadow-xs text-[#191410]">
      {/* Sidebar Header with Case Context */}
      <div className="p-4 border-b border-[#eae4d9] bg-[#faf7f2]/60">
        <button 
          onClick={() => navigate('/cases')}
          className="flex items-center gap-1.5 text-[11px] font-semibold text-[#6e665d] hover:text-[#d93829] uppercase tracking-wider mb-3 transition-colors group cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
          <span>Global Workspaces</span>
        </button>
        
        <div className="bg-white p-3 rounded-xl border border-[#eae4d9] shadow-xs">
          <div className="flex items-center gap-1.5 mb-1">
            <span className="w-2 h-2 rounded-full bg-[#15803d] animate-pulse" />
            <span className="text-[10px] text-[#d93829] font-bold uppercase tracking-wider">Active Investigation</span>
          </div>
          <h2 className="text-xs font-serif font-bold text-[#191410] line-clamp-2 leading-snug" title={caseTitle}>
            {caseTitle}
          </h2>
          <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-[#f0ebe1] text-[10px] text-[#6e665d]">
            <span className="font-mono font-medium">Ref: {docketId}</span>
            <span className="bg-[#f5f0e6] px-1.5 py-0.5 rounded text-[9px] font-semibold text-[#191410]">
              {currentCase?.status || 'Active'}
            </span>
          </div>
        </div>
      </div>
      
      {/* Navigation List */}
      <div className="flex-1 overflow-y-auto py-3 px-3 scrollbar-thin">
        <nav className="space-y-1">
          {caseNavItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all duration-150 group',
                  isActive 
                    ? 'bg-[#d93829]/10 text-[#d93829] font-bold border border-[#d93829]/25 shadow-xs' 
                    : 'text-[#6e665d] hover:bg-[#f5f0e6] hover:text-[#191410]'
                )
              }
            >
              <item.icon className="w-4 h-4 opacity-75 group-hover:opacity-100 transition-opacity shrink-0" />
              <span className="truncate">{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </div>
    </aside>
  );
}
