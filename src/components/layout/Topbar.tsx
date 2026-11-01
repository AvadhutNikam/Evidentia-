import React, { useState, useEffect } from 'react';
import { Search, Bell, ChevronRight, Shield, LogOut, ChevronDown, User, KeyRound, Lock, Sparkles, Database, Server, Tv, Activity, SlidersHorizontal, Languages } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { isDemoMode, setDemoMode } from '../../config/api';
import { PresenceAvatars } from '../collaboration/PresenceAvatars';
import { NotificationBellDropdown } from '../alerts/NotificationBellDropdown';
import { PossiblyConnectedCasesBadge } from '../case/PossiblyConnectedCasesBadge';
import { findGroupForSubpath, findNavItemByPath } from '../../config/caseNav';
import { useTranslation } from 'react-i18next';
import { setApplicationLanguage, getApplicationLanguage, SupportedLanguage } from '../../i18n';
import { isLightMode, toggleLightMode } from '../../utils/lightMode';
import { FirstRunWizard } from '../setup/FirstRunWizard';
import { ErrorBoundary } from '../common/ErrorBoundary';
import { apiRequest } from '../../services/apiClient';

export function Topbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const pathnames = location.pathname.split('/').filter(x => x);
  const { user, role, logout, loginAsDemoRole } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [demoMode, setDemoModeState] = useState<boolean>(isDemoMode());
  const [currentLang, setCurrentLang] = useState<SupportedLanguage>(getApplicationLanguage());
  const [lightModeActive, setLightModeActive] = useState<boolean>(isLightMode());
  const [showFirstRunWizard, setShowFirstRunWizard] = useState<boolean>(false);
  const [aiModeInfo, setAiModeInfo] = useState<{ mode: string; label: string; color: string }>({
    mode: 'private_only',
    label: 'AI: Private (On Server)',
    color: 'emerald'
  });

  useEffect(() => {
    // Check if first-run setup is completed
    const firstRunDone = localStorage.getItem('evidentia_first_run_completed');
    if (!firstRunDone && role === 'admin') {
      setShowFirstRunWizard(true);
    }

    // Fetch live system AI mode
    apiRequest('/security/ai-mode', {
      suppressBanner: true,
      fallback: {
        mode: 'cloud_allowed',
        mode_label: 'AI: Cloud Allowed',
        chip_color: 'amber'
      }
    })
      .then(res => {
        if (res) {
          setAiModeInfo({
            mode: res.mode,
            label: res.mode_label || 'AI: Private',
            color: res.chip_color || 'emerald'
          });
        }
      })
      .catch(() => {});

    const handleLightModeChange = (e: Event) => {
      const customEvent = e as CustomEvent<{ enabled: boolean }>;
      setLightModeActive(customEvent.detail.enabled);
    };
    window.addEventListener('evidentia:light-mode-changed', handleLightModeChange);
    return () => window.removeEventListener('evidentia:light-mode-changed', handleLightModeChange);
  }, [role]);

  const handleToggleLightMode = () => {
    const next = toggleLightMode();
    setLightModeActive(next);
  };

  const handleLanguageChange = (lang: SupportedLanguage) => {
    setApplicationLanguage(lang);
    setCurrentLang(lang);
  };

  const isCaseRoute = pathnames[0] === 'cases' && pathnames[1] && pathnames[1] !== 'dashboard';
  const currentCaseId = isCaseRoute ? pathnames[1] : null;
  const activeSubpath = isCaseRoute ? (pathnames[2] || 'overview') : '';
  const currentNavGroup = isCaseRoute ? findGroupForSubpath(activeSubpath) : undefined;
  const currentNavItem = isCaseRoute ? findNavItemByPath(activeSubpath) : undefined;

  useEffect(() => {
    if (isCaseRoute && currentNavItem) {
      const groupLabel = currentNavGroup ? ` • ${currentNavGroup.label}` : '';
      document.title = `${currentNavItem.label}${groupLabel} | Evidentia AI`;
    } else {
      document.title = 'Evidentia AI • Forensic & Investigative Intelligence';
    }
  }, [location.pathname, isCaseRoute, currentNavItem, currentNavGroup]);

  useEffect(() => {
    const handleDemoChange = (e: Event) => {
      const customEvent = e as CustomEvent<{ enabled: boolean }>;
      setDemoModeState(customEvent.detail.enabled);
    };
    window.addEventListener('evidentia:demo-mode-changed', handleDemoChange);
    return () => window.removeEventListener('evidentia:demo-mode-changed', handleDemoChange);
  }, []);

  const handleToggleDemo = () => {
    const next = !demoMode;
    setDemoMode(next);
    setDemoModeState(next);
  };

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
        {isCaseRoute && currentCaseId ? (
          <>
            <ChevronRight className="w-3.5 h-3.5 text-[#b0a89d]" />
            <span className="text-[#70685e] font-mono">Case #{currentCaseId}</span>
            {currentNavGroup && (
              <>
                <ChevronRight className="w-3.5 h-3.5 text-[#b0a89d]" />
                <span className="text-[#70685e] font-medium">{currentNavGroup.label}</span>
              </>
            )}
            <ChevronRight className="w-3.5 h-3.5 text-[#b0a89d]" />
            <span className="text-[#d93829] font-bold">
              {currentNavItem ? currentNavItem.label : activeSubpath.replace('-', ' ')}
            </span>
          </>
        ) : (
          pathnames.map((name, index) => (
            <React.Fragment key={name}>
              <ChevronRight className="w-3.5 h-3.5 text-[#b0a89d]" />
              <span className={index === pathnames.length - 1 ? "text-[#d93829] font-semibold capitalize" : "capitalize text-[#70685e]"}>
                {name.replace('-', ' ')}
              </span>
            </React.Fragment>
          ))
        )}
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-4">
        {/* Methodology View Link for Expert Users */}
        {isCaseRoute && currentCaseId && (
          <button
            onClick={() => navigate(`/cases/${currentCaseId}/config`)}
            className="hidden lg:flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-mono font-bold bg-white hover:bg-[#faf7f2] border border-[#eae4d9] hover:border-purple-300 text-[#6e665d] hover:text-purple-900 transition-all cursor-pointer shadow-2xs"
            title="Inspect underlying Bayesian Likelihood Ratios, Richards Heuer elimination formulas, and Section 54 partitions"
          >
            <SlidersHorizontal className="w-3.5 h-3.5 text-purple-700" />
            <span>Methodology View</span>
          </button>
        )}

        {/* Persistent AI Security Status Chip */}
        <button
          type="button"
          onClick={() => setShowFirstRunWizard(true)}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono font-bold border transition-all cursor-pointer shadow-2xs ${
            aiModeInfo.color === 'emerald'
              ? 'bg-emerald-50 text-emerald-800 border-emerald-300 hover:bg-emerald-100'
              : aiModeInfo.color === 'amber'
              ? 'bg-amber-50 text-amber-800 border-amber-300 hover:bg-amber-100'
              : 'bg-neutral-100 text-neutral-700 border-neutral-300 hover:bg-neutral-200'
          }`}
          title="Click to view AI Data Boundaries, Outbound Call Register, or switch between Private/Cloud modes"
        >
          <span className={`w-2 h-2 rounded-full ${
            aiModeInfo.color === 'emerald' ? 'bg-emerald-600' : aiModeInfo.color === 'amber' ? 'bg-amber-500' : 'bg-neutral-400'
          }`} />
          <span>{aiModeInfo.label}</span>
        </button>

        {/* Light Hardware Mode Toggle (Old PCs & 2G) */}
        <button
          type="button"
          onClick={handleToggleLightMode}
          className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold border transition-all cursor-pointer shadow-2xs ${
            lightModeActive
              ? 'bg-amber-100 border-amber-400 text-amber-950 font-bold'
              : 'bg-white border-[#eae4d9] text-[#70685e] hover:text-[#191410]'
          }`}
          title="Light Mode: Optimizes for 4GB RAM PCs & 2G networks by disabling animations, blurs, and interactive map tile rendering"
        >
          <span className="font-mono text-[10px]">⚡ Light:</span>
          <span>{lightModeActive ? 'ON' : 'OFF'}</span>
        </button>

        {/* Language Switcher (EN | HI | MR) */}
        <div className="flex items-center bg-white border border-[#eae4d9] rounded-full p-0.5 shadow-2xs text-[11px] font-semibold notranslate" translate="no">
          <button
            key="topbar-lang-en"
            type="button"
            onClick={() => handleLanguageChange('en')}
            className={`px-2.5 py-1 rounded-full transition-all cursor-pointer ${
              currentLang === 'en'
                ? 'bg-[#d93829] text-white shadow-xs font-bold'
                : 'text-[#70685e] hover:text-[#191410]'
            }`}
            title="English Interface"
          >
            EN
          </button>
          <button
            key="topbar-lang-hi"
            type="button"
            onClick={() => handleLanguageChange('hi')}
            className={`px-2.5 py-1 rounded-full transition-all cursor-pointer ${
              currentLang === 'hi'
                ? 'bg-[#d93829] text-white shadow-xs font-bold'
                : 'text-[#70685e] hover:text-[#191410]'
            }`}
            title="हिन्दी (Hindi Interface)"
          >
            हिन्दी
          </button>
          <button
            key="topbar-lang-mr"
            type="button"
            onClick={() => handleLanguageChange('mr')}
            className={`px-2.5 py-1 rounded-full transition-all cursor-pointer ${
              currentLang === 'mr'
                ? 'bg-[#d93829] text-white shadow-xs font-bold'
                : 'text-[#70685e] hover:text-[#191410]'
            }`}
            title="मराठी (Marathi Interface)"
          >
            मराठी
          </button>
        </div>

        {/* Search & Command Palette Trigger */}
        <button
          type="button"
          onClick={() => window.dispatchEvent(new CustomEvent('evidentia:open-command-palette'))}
          className="relative flex items-center bg-white hover:bg-[#faf7f2] border border-[#eae4d9] hover:border-[#d93829]/40 rounded-full pl-9 pr-10 py-1.5 text-xs text-[#191410] w-64 shadow-2xs transition-all text-left cursor-pointer group"
          title="Open Global Search & Command Palette (Ctrl+K or /)"
        >
          <Search className="w-3.5 h-3.5 absolute left-3.5 top-1/2 -translate-y-1/2 text-[#8c8276] group-hover:text-[#d93829] transition-colors" />
          <span className="text-[#999084] truncate select-none">
            Search exhibits, quotes, tasks...
          </span>
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-mono text-[#999084] group-hover:text-[#191410] bg-[#f5f0e6] px-1.5 py-0.5 rounded-full border border-[#eae4d9]">
            ⌘K
          </div>
        </button>
        
        {/* Demo Mode Explicit Switch with Visible Status Label */}
        <button
          onClick={handleToggleDemo}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all cursor-pointer shadow-2xs ${
            demoMode
              ? 'bg-[#fff8ea] border-[#f4c153] text-[#8a5b00] hover:bg-[#fff2d4]'
              : 'bg-[#f0fbf4] border-[#9fe0b2] text-[#1b7a37] hover:bg-[#e4f7eb]'
          }`}
          title={
            demoMode
              ? 'Demo Mode is ACTIVE: Mock data fallback enabled. Click to switch to Live Backend.'
              : 'Live Backend is ACTIVE: Real API calls required; errors display error banner. Click to switch to Demo Mode.'
          }
        >
          <span
            className={`w-2 h-2 rounded-full ${
              demoMode ? 'bg-[#e59b00] animate-pulse' : 'bg-[#22c55e]'
            }`}
          />
          <span className="text-[11px] uppercase tracking-wider font-bold">
            {demoMode ? 'Demo Mode Active' : 'Live Backend'}
          </span>
          <span
            className={`text-[9px] px-1.5 py-0.5 rounded font-mono font-bold tracking-tight ${
              demoMode
                ? 'bg-[#ffe8a8] text-[#6d4800]'
                : 'bg-[#d1f5dc] text-[#14532d]'
            }`}
          >
            {demoMode ? 'MOCK DATA ACTIVE' : 'LIVE API'}
          </span>
        </button>

        {/* Multi-User Collaboration Presence Avatars & Live Activity */}
        <PresenceAvatars />

        {/* Real-time Possibly Connected Cases Badge */}
        {currentCaseId && (
          <PossiblyConnectedCasesBadge caseId={currentCaseId} />
        )}

        {/* Case Wall Quick Launch */}
        {currentCaseId && (
          <a
            href={`/cases/${currentCaseId}/wall`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold font-mono text-stone-800 bg-[#f5efe6] hover:bg-[#eae4d9] border border-[#d8d0c2] transition shadow-2xs"
            title="Launch Live Case Wall for Team Room / Second Monitor"
          >
            <Tv className="w-3.5 h-3.5 text-[#d93829]" />
            <span className="hidden md:inline">Case Wall</span>
          </a>
        )}

        {/* Live System Health Status Pill */}
        <button
          onClick={() => navigate('/system-health')}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold font-mono text-stone-800 bg-[#f5efe6] hover:bg-[#eae4d9] border border-[#d8d0c2] transition shadow-2xs"
          title="Open Live System Health & Telemetry Status Page"
        >
          <Activity className="w-3.5 h-3.5 text-emerald-600" />
          <span className="hidden md:inline">Health</span>
        </button>

        {/* Case Alerts & Live Notification Bell */}
        <NotificationBellDropdown />

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

              <div className="border-t border-[#eae4d9] pt-1 pb-1">
                <div className="px-3.5 py-1.5 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2 text-[#59524c]">
                    <Database className="w-3.5 h-3.5 text-[#8c8276]" />
                    <span className="font-medium">Demo Mode</span>
                  </div>
                  <button
                    onClick={handleToggleDemo}
                    className={`text-[10px] font-bold px-2 py-0.5 rounded cursor-pointer transition-colors ${
                      demoMode
                        ? 'bg-amber-100 text-amber-900 border border-amber-300'
                        : 'bg-stone-100 text-stone-700 border border-stone-200 hover:bg-stone-200'
                    }`}
                  >
                    {demoMode ? 'ON (Mock)' : 'OFF (Live)'}
                  </button>
                </div>
              </div>

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

      <ErrorBoundary fallbackTitle="Station Setup Notice">
        <FirstRunWizard 
          isOpen={showFirstRunWizard} 
          onClose={() => setShowFirstRunWizard(false)} 
        />
      </ErrorBoundary>
    </div>
  );
}
