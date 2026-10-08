import React, { useState } from 'react';
import { Search, Bell, ChevronRight, Shield, LogOut, ChevronDown, User, KeyRound, Lock, Sparkles } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export function Topbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const pathnames = location.pathname.split('/').filter(x => x);
  const { user, role, logout, loginAsDemoRole } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const initials = user?.full_name
    ? user.full_name.split(' ').map((n: string) => n[0]).join('').slice(0, 2).toUpperCase()
    : 'US';

  const roleLabels: Record<string, { label: string; bg: string; text: string }> = {
    admin: { label: 'Administrator', bg: 'bg-[#fdeee9]', text: 'text-[#d93829]' },
    lead_investigator: { label: 'Lead Investigator', bg: 'bg-[#ebf4fd]', text: 'text-[#1b64b8]' },
    analyst: { label: 'Forensic Analyst', bg: 'bg-[#f0eaff]', text: 'text-[#6b38fb]' },
    reviewer: { label: 'Judicial Reviewer (Read-Only)', bg: 'bg-[#ebf7ee]', text: 'text-[#1b7a37]' },
  };

  const currentRoleConfig = roleLabels[role] || { label: role, bg: 'bg-[#f4efe6]', text: 'text-[#70685e]' };

  return (
    <div className="h-16 bg-[#faf7f2]/95 backdrop-blur-md border-b border-[#eae4d9] flex items-center justify-between px-6 sticky top-0 z-30 select-none">
      {/* Breadcrumb Path */}
      <div className="flex items-center gap-2 text-xs font-medium text-[#70685e]">
        <span className="font-serif font-bold text-base text-[#191410] tracking-tight">Evidentia</span>
        {pathnames.map((name, index) => (
          <React.Fragment key={name}>
            <ChevronRight className="w-3.5 h-3.5 text-[#b0a89d]" />
            <span className={index === pathnames.length - 1 ? "text-[#d93829] font-semibold capitalize" : "capitalize text-[#70685e]"}>
              {name.replace('-', ' ')}
            </span>
          </React.Fragment>
        ))}
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-4">
        {/* Search */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3.5 top-1/2 -translate-y-1/2 text-[#8c8276]" />
          <input 
            type="text" 
            placeholder="Search evidence, FIR, suspects..." 
            className="bg-white border border-[#eae4d9] rounded-full pl-9 pr-10 py-1.5 text-xs text-[#191410] placeholder:text-[#999084] focus:outline-none focus:border-[#d93829] focus:ring-2 focus:ring-[#d93829]/10 w-64 shadow-2xs transition-all"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-mono text-[#999084] bg-[#f5f0e6] px-1.5 py-0.5 rounded-full">
            ⌘K
          </div>
        </div>
        
        <button className="relative p-2 rounded-full text-[#70685e] hover:text-[#191410] hover:bg-[#f0ebe1] transition-colors">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-[#d93829] rounded-full ring-2 ring-white"></span>
        </button>

        {/* User Profile & Role Switcher */}
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2.5 pl-3 border-l border-[#eae4d9] hover:opacity-85 transition-opacity cursor-pointer text-left"
          >
            <div className="w-8 h-8 rounded-full bg-[#d93829] flex items-center justify-center text-white font-bold text-xs shadow-xs">
              {initials}
            </div>
            <div className="hidden sm:block">
              <div className="text-xs font-semibold text-[#191410] flex items-center gap-1.5">
                {user?.full_name || 'Officer'}
                <ChevronDown className="w-3 h-3 text-[#999084]" />
              </div>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded-full uppercase tracking-wider ${currentRoleConfig.bg} ${currentRoleConfig.text}`}>
                  {currentRoleConfig.label}
                </span>
              </div>
            </div>
          </button>

          {/* Role Switcher Menu */}
          {dropdownOpen && (
            <div 
              className="absolute right-0 mt-2 w-64 rounded-2xl bg-white border border-[#eae4d9] shadow-lg py-2 z-50 animate-fadeIn space-y-1"
              onMouseLeave={() => setDropdownOpen(false)}
            >
              <div className="px-3.5 py-2 border-b border-[#eae4d9]">
                <div className="text-xs font-bold text-[#191410]">{user?.full_name}</div>
                <div className="text-[10px] text-[#70685e] font-mono">{user?.email}</div>
                <div className="text-[9px] text-[#999084] mt-0.5">Badge: {user?.badge_number || 'N/A'}</div>
              </div>

              <div className="px-3.5 py-1.5 text-[9px] font-bold text-[#999084] uppercase tracking-wider font-mono">
                Switch Role (Live Evaluation)
              </div>

              <button
                onClick={() => { loginAsDemoRole('admin'); setDropdownOpen(false); }}
                className={`w-full px-3.5 py-2 text-left text-xs flex items-center justify-between hover:bg-[#faf7f2] transition-colors cursor-pointer ${role === 'admin' ? 'bg-[#fef8f6] font-bold text-[#d93829]' : 'text-[#191410]'}`}
              >
                <div className="flex items-center gap-2">
                  <Shield className="w-3.5 h-3.5 text-[#d93829]" />
                  <span>Administrator</span>
                </div>
                {role === 'admin' && <span className="text-[10px] text-[#d93829]">Active</span>}
              </button>

              <button
                onClick={() => { loginAsDemoRole('lead_investigator'); setDropdownOpen(false); }}
                className={`w-full px-3.5 py-2 text-left text-xs flex items-center justify-between hover:bg-[#faf7f2] transition-colors cursor-pointer ${role === 'lead_investigator' ? 'bg-[#f2f7fd] font-bold text-[#1b64b8]' : 'text-[#191410]'}`}
              >
                <div className="flex items-center gap-2">
                  <User className="w-3.5 h-3.5 text-[#1b64b8]" />
                  <span>Lead Investigator</span>
                </div>
                {role === 'lead_investigator' && <span className="text-[10px] text-[#1b64b8]">Active</span>}
              </button>

              <button
                onClick={() => { loginAsDemoRole('analyst'); setDropdownOpen(false); }}
                className={`w-full px-3.5 py-2 text-left text-xs flex items-center justify-between hover:bg-[#faf7f2] transition-colors cursor-pointer ${role === 'analyst' ? 'bg-[#f6f2ff] font-bold text-[#6b38fb]' : 'text-[#191410]'}`}
              >
                <div className="flex items-center gap-2">
                  <KeyRound className="w-3.5 h-3.5 text-[#6b38fb]" />
                  <span>Forensic Analyst</span>
                </div>
                {role === 'analyst' && <span className="text-[10px] text-[#6b38fb]">Active</span>}
              </button>

              <button
                onClick={() => { loginAsDemoRole('reviewer'); setDropdownOpen(false); }}
                className={`w-full px-3.5 py-2 text-left text-xs flex items-center justify-between hover:bg-[#faf7f2] transition-colors cursor-pointer ${role === 'reviewer' ? 'bg-[#f2f9f4] font-bold text-[#1b7a37]' : 'text-[#191410]'}`}
              >
                <div className="flex items-center gap-2">
                  <Lock className="w-3.5 h-3.5 text-[#1b7a37]" />
                  <span>Judicial Reviewer</span>
                </div>
                {role === 'reviewer' && <span className="text-[10px] text-[#1b7a37]">Active</span>}
              </button>

              <div className="border-t border-[#eae4d9] pt-1">
                <button
                  onClick={() => { logout(); navigate('/login'); setDropdownOpen(false); }}
                  className="w-full px-3.5 py-2 text-left text-xs text-[#d93829] hover:bg-[#fdeee9] flex items-center gap-2 transition-colors cursor-pointer font-medium"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
