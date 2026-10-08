import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Briefcase, Globe, BarChart2, Settings, User, Search, Shield, Award } from 'lucide-react';
import { cn } from '../../utils';

const globalNavItems = [
  { path: '/dashboard', icon: LayoutDashboard, label: 'Overview' },
  { path: '/cases', icon: Briefcase, label: 'Investigations' },
  { path: '/evaluation', icon: Award, label: 'ACH Benchmark' },
  { path: '/osint', icon: Globe, label: 'OSINT Intelligence' },
  { path: '/search', icon: Search, label: 'Cross-Examination' },
  { path: '/reports', icon: BarChart2, label: 'Briefings & Dossiers' },
];

export function GlobalSidebar() {
  return (
    <aside className="w-64 bg-[#faf7f2] border-r border-[#eae4d9] h-full flex flex-col shrink-0 select-none">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 border-b border-[#eae4d9]">
        <div className="flex items-center gap-3 text-[#191410]">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[#d93829] to-[#eb5a4b] flex items-center justify-center shadow-md shadow-[#d93829]/20">
            <Shield className="w-5 h-5 text-white stroke-[2.5]" />
          </div>
          <div>
            <div className="font-serif font-extrabold text-lg tracking-tight text-[#191410] leading-none">
              Evidentia
            </div>
            <div className="text-[9px] uppercase tracking-widest text-[#d93829] font-bold font-sans mt-0.5">
              AI Forensic Suite
            </div>
          </div>
        </div>
      </div>
      
      {/* Navigation Links */}
      <div className="p-4 flex-1 overflow-y-auto space-y-6">
        <div>
          <div className="text-[10px] font-bold text-[#999084] uppercase tracking-widest px-3 mb-2 font-mono">
            Command Center
          </div>
          <nav className="space-y-1">
            {globalNavItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 px-3.5 py-2.5 rounded-full text-xs font-medium transition-all',
                    isActive 
                      ? 'bg-[#d93829] text-white font-semibold shadow-sm shadow-[#d93829]/30' 
                      : 'text-[#6e665d] hover:bg-[#f0ebe1] hover:text-[#191410]'
                  )
                }
              >
                <item.icon className="w-4 h-4" />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Feature Spotlight Card */}
        <div className="p-4 rounded-2xl bg-white border border-[#eae4d9] shadow-xs space-y-2">
          <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-[#fdeee9] text-[#d93829] font-bold text-[10px] uppercase">
            <span>ACH Algorithm</span>
          </div>
          <h4 className="text-xs font-bold text-[#191410] font-serif">Analysis of Competing Hypotheses</h4>
          <p className="text-[11px] text-[#70685e] leading-relaxed">
            Eliminates cognitive bias by deriving suspect guilt from 14 real forensic vectors.
          </p>
        </div>
      </div>

      {/* Footer Controls */}
      <div className="p-4 border-t border-[#eae4d9] space-y-1">
        <NavLink 
          to="/settings" 
          className="flex items-center gap-3 px-3.5 py-2 rounded-full text-xs font-medium text-[#6e665d] hover:bg-[#f0ebe1] hover:text-[#191410] transition-colors"
        >
          <Settings className="w-4 h-4" />
          Settings & Policies
        </NavLink>
      </div>
    </aside>
  );
}
