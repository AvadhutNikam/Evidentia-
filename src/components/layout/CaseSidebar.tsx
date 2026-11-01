import React, { useEffect, useState, useMemo, useRef, useCallback } from 'react';
import { NavLink, useParams, useNavigate, useLocation } from 'react-router-dom';
import { caseService } from '../../services';
import { Case } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { 
  ChevronDown, ChevronRight, Menu, X, ArrowLeft, 
  Pin, Sparkles, HelpCircle, PanelLeftClose, PanelLeft,
  Sliders, Shield, SlidersHorizontal, LucideIcon
} from 'lucide-react';
import { 
  CASE_NAV_GROUPS, 
  SETTINGS_TECHNICAL_ITEMS, 
  findGroupForSubpath,
  CaseNavItem,
  CaseNavGroup 
} from '../../config/caseNav';
import { useCaseNavSummary, CaseNavBadges } from '../../hooks/useCaseNavSummary';
import { cn } from '../../utils';

export function CaseSidebar() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { role } = useAuth();
  const badges = useCaseNavSummary(caseId);

  const [currentCase, setCurrentCase] = useState<Case | null>(null);
  
  // Collapse entire sidebar to icons only
  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    return localStorage.getItem('evidentia_sidebar_collapsed') === 'true';
  });

  // Mobile drawer open state
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  // Open groups state in localStorage
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() => {
    try {
      const saved = localStorage.getItem('evidentia_sidebar_open_groups');
      if (saved) return JSON.parse(saved);
    } catch {}
    // Default: 'my_case' is open, all others collapsed for a clean initial view
    return {
      my_case: true,
      evidence: false,
      people_links: false,
      closing_case: false,
      team: false
    };
  });

  // Pinned items (up to 3)
  const [pinnedItemIds, setPinnedItemIds] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem('evidentia_sidebar_pinned_items');
      if (saved) return JSON.parse(saved);
    } catch {}
    return ['priorities', 'exhibits', 'suspects'];
  });

  // Recent items
  const [recentItemIds, setRecentItemIds] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem('evidentia_sidebar_recent_items');
      if (saved) return JSON.parse(saved);
    } catch {}
    return [];
  });

  // 3-step guided tour state
  const [tourStep, setTourStep] = useState<number | null>(() => {
    const done = localStorage.getItem('evidentia_tour_completed');
    return done ? null : 1;
  });

  // Load case metadata
  useEffect(() => {
    if (caseId) {
      caseService.getCaseById(caseId).then(data => {
        if (data) setCurrentCase(data);
      }).catch(() => {});
    }
  }, [caseId]);

  // Save collapsed state
  const toggleSidebarCollapse = () => {
    setIsCollapsed(prev => {
      const next = !prev;
      localStorage.setItem('evidentia_sidebar_collapsed', String(next));
      return next;
    });
  };

  // Toggle group open/closed
  const toggleGroup = (groupId: string) => {
    setOpenGroups(prev => {
      const next = { ...prev, [groupId]: !prev[groupId] };
      localStorage.setItem('evidentia_sidebar_open_groups', JSON.stringify(next));
      return next;
    });
  };

  // Auto-open group matching current path
  const currentSubpath = useMemo(() => {
    if (!caseId) return '';
    const prefix = `/cases/${caseId}/`;
    if (location.pathname.startsWith(prefix)) {
      return location.pathname.slice(prefix.length).split('/')[0];
    }
    return '';
  }, [location.pathname, caseId]);

  useEffect(() => {
    if (currentSubpath) {
      const group = findGroupForSubpath(currentSubpath);
      if (group && !openGroups[group.id]) {
        setOpenGroups(prev => {
          const next = { ...prev, [group.id]: true };
          localStorage.setItem('evidentia_sidebar_open_groups', JSON.stringify(next));
          return next;
        });
      }

      // Track recents
      setRecentItemIds(prev => {
        const item = CASE_NAV_GROUPS.flatMap(g => g.items).find(i => i.path === currentSubpath);
        if (item) {
          const filtered = prev.filter(id => id !== item.id);
          const updated = [item.id, ...filtered].slice(0, 4);
          localStorage.setItem('evidentia_sidebar_recent_items', JSON.stringify(updated));
          return updated;
        }
        return prev;
      });
    }
  }, [currentSubpath]);

  // Toggle pinned item
  const togglePin = (itemId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setPinnedItemIds(prev => {
      let updated: string[];
      if (prev.includes(itemId)) {
        updated = prev.filter(id => id !== itemId);
      } else {
        updated = [...prev, itemId].slice(-3);
      }
      localStorage.setItem('evidentia_sidebar_pinned_items', JSON.stringify(updated));
      return updated;
    });
  };

  const completeTour = () => {
    setTourStep(null);
    localStorage.setItem('evidentia_tour_completed', 'true');
  };

  const nextTourStep = () => {
    if (tourStep === 3) {
      completeTour();
    } else if (tourStep !== null) {
      setTourStep(tourStep + 1);
    }
  };

  // Helper to render badges
  const renderBadge = (source?: string) => {
    if (!source) return null;
    const count = badges[source as keyof CaseNavBadges];

    if (source === 'handover_changed') {
      if (badges.handover_changed) {
        return <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse shrink-0" title="Updates pending review" />;
      }
      return null;
    }

    if (typeof count === 'number' && count > 0) {
      const isCritical = source === 'critical_gaps' || source === 'priorities_due';
      return (
        <span 
          className={cn(
            "px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold shrink-0",
            isCritical ? "bg-rose-500 text-white" : "bg-stone-200 text-stone-800"
          )}
        >
          {count}
        </span>
      );
    }
    return null;
  };

  const caseTitle = currentCase?.title || currentCase?.name || `Investigation Docket #${caseId}`;
  const docketId = currentCase?.fir_number || currentCase?.id || caseId;

  // Flattened items for lookups
  const allItemsMap = useMemo(() => {
    const map = new Map<string, CaseNavItem>();
    CASE_NAV_GROUPS.forEach(g => {
      g.items.forEach(i => map.set(i.id, i));
    });
    return map;
  }, []);

  const pinnedItems = pinnedItemIds.map(id => allItemsMap.get(id)).filter(Boolean) as CaseNavItem[];

  const sidebarContent = (
    <div className="h-full flex flex-col justify-between text-[#191410] select-none">
      {/* Top Header */}
      <div className="border-b border-[#eae4d9] bg-[#faf7f2]/80 shrink-0">
        {/* Workspace switch button & collapse toggle */}
        <div className="p-3 pb-2 flex items-center justify-between gap-2">
          {!isCollapsed ? (
            <button 
              onClick={() => navigate('/cases')}
              className="flex items-center gap-1.5 text-[11px] font-semibold text-[#6e665d] hover:text-[#d93829] uppercase tracking-wider transition-colors group cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
              <span>All Cases</span>
            </button>
          ) : (
            <button 
              onClick={() => navigate('/cases')}
              className="p-1 rounded-lg text-[#6e665d] hover:text-[#d93829] cursor-pointer"
              title="All Cases"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
          )}

          <button
            onClick={toggleSidebarCollapse}
            className="p-1.5 rounded-lg text-[#6e665d] hover:text-[#191410] hover:bg-[#eae4d9]/50 transition-colors cursor-pointer"
            title={isCollapsed ? "Expand sidebar" : "Collapse sidebar (icons only)"}
          >
            {isCollapsed ? <PanelLeft className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
          </button>
        </div>

        {/* Case Context Card */}
        {!isCollapsed ? (
          <div className="px-3 pb-3">
            <div className="bg-white p-3 rounded-2xl border border-[#eae4d9] shadow-xs">
              <div className="flex items-center gap-1.5 mb-1">
                <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse" />
                <span className="text-[10px] text-[#d93829] font-bold uppercase tracking-wider">
                  Active Docket
                </span>
              </div>
              <h2 className="text-xs font-serif font-bold text-[#191410] line-clamp-1 leading-snug" title={caseTitle}>
                {caseTitle}
              </h2>
              <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-[#f0ebe1] text-[10px] text-[#6e665d] font-mono">
                <span className="truncate max-w-[120px] font-medium" title={String(docketId)}>
                  {docketId}
                </span>
                <span className="bg-[#f5f0e6] px-1.5 py-0.5 rounded text-[9px] font-semibold text-[#191410]">
                  {currentCase?.status || 'Active'}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-2 flex flex-col items-center">
            <span className="w-2 h-2 rounded-full bg-emerald-600 mb-1" />
            <span className="text-[9px] font-mono font-bold text-[#6e665d] truncate">
              #{caseId}
            </span>
          </div>
        )}
      </div>

      {/* Guided Tour Tooltip Banner */}
      {tourStep !== null && !isCollapsed && (
        <div className="m-3 p-3 rounded-2xl bg-amber-50 border border-amber-300 shadow-sm animate-in fade-in duration-200">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-mono font-bold uppercase text-amber-900 flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-amber-700" />
              <span>Investigator Tour ({tourStep}/3)</span>
            </span>
            <button onClick={completeTour} className="text-amber-800 hover:text-amber-950">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          <p className="text-[11px] font-serif text-amber-950 leading-snug">
            {tourStep === 1 && "“This is your case”: Review your Situation Board, Today’s Priorities, and legal FIR File."}
            {tourStep === 2 && "“This is where evidence goes”: Register exhibits, field photos, CCTV streams, and run integrity checks."}
            {tourStep === 3 && "“This is where you close the case”: Detect missing proof, stress-test against reasonable doubt, and file the chargesheet."}
          </p>
          <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-amber-200/80">
            <button 
              onClick={completeTour} 
              className="text-[10px] font-mono text-amber-800 hover:underline cursor-pointer"
            >
              Skip
            </button>
            <button
              onClick={nextTourStep}
              className="px-2.5 py-0.5 rounded-full bg-amber-900 text-white font-mono text-[10px] font-bold hover:bg-amber-950 cursor-pointer"
            >
              {tourStep === 3 ? "Got it!" : "Next →"}
            </button>
          </div>
        </div>
      )}

      {/* Pinned Items Quick Access (Expanded mode only) */}
      {!isCollapsed && pinnedItems.length > 0 && (
        <div className="px-3 pt-2 pb-1">
          <div className="text-[10px] font-mono font-bold text-[#8c8276] uppercase tracking-wider mb-1 flex items-center gap-1 px-2">
            <Pin className="w-2.5 h-2.5" />
            <span>Pinned Shortcuts</span>
          </div>
          <div className="flex items-center gap-1 overflow-x-auto pb-1 scrollbar-none">
            {pinnedItems.map(item => (
              <NavLink
                key={`pinned-${item.id}`}
                to={`/cases/${caseId}/${item.path}`}
                className={({ isActive }) => cn(
                  "px-2.5 py-1 rounded-lg text-[11px] font-serif font-bold transition-all flex items-center gap-1 truncate shrink-0 border cursor-pointer",
                  isActive 
                    ? "bg-[#d93829] text-white border-[#d93829]" 
                    : "bg-white text-[#191410] border-[#eae4d9] hover:bg-[#faf7f2]"
                )}
                title={item.label}
              >
                <item.icon className="w-3 h-3 shrink-0" />
                <span className="truncate max-w-[85px]">{item.label}</span>
              </NavLink>
            ))}
          </div>
        </div>
      )}

      {/* Scrollable Navigation Groups */}
      <div className="flex-1 overflow-y-auto py-2 px-2.5 scrollbar-thin space-y-3">
        {CASE_NAV_GROUPS.map((group) => {
          const isOpen = openGroups[group.id];
          const hasActiveChild = group.items.some(item => currentSubpath === item.path || item.replaces?.includes(currentSubpath) || item.oldPaths?.includes(currentSubpath));

          if (isCollapsed) {
            // Collapsed mode: icon only items
            return (
              <div key={group.id} className="space-y-1 pt-1 border-t border-[#eae4d9]/50 first:border-t-0">
                {group.items.map(item => {
                  const toPath = `/cases/${caseId}/${item.path}`;
                  return (
                    <NavLink
                      key={item.id}
                      to={toPath}
                      className={({ isActive }) => cn(
                        "w-9 h-9 rounded-xl flex items-center justify-center transition-all mx-auto relative group cursor-pointer",
                        isActive
                          ? "bg-[#d93829] text-white shadow-xs"
                          : "text-[#6e665d] hover:bg-[#faf7f2] hover:text-[#191410]"
                      )}
                      title={item.label}
                    >
                      <item.icon className="w-4 h-4 shrink-0" />
                      {/* Floating tooltip on hover */}
                      <div className="absolute left-full ml-2 px-2.5 py-1 bg-[#191410] text-white text-[11px] font-serif font-medium rounded-lg shadow-lg opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 whitespace-nowrap">
                        {item.label}
                      </div>
                    </NavLink>
                  );
                })}
              </div>
            );
          }

          return (
            <div key={group.id} className="space-y-1">
              {/* Group Collapsible Header */}
              <button
                type="button"
                onClick={() => toggleGroup(group.id)}
                className={cn(
                  "w-full flex items-center justify-between px-2.5 py-1.5 rounded-xl text-xs font-serif font-bold transition-all text-left cursor-pointer group",
                  hasActiveChild ? "text-[#d93829]" : "text-[#6e665d] hover:text-[#191410]"
                )}
              >
                <div className="flex items-center gap-2">
                  <group.icon className={cn("w-3.5 h-3.5 transition-colors", hasActiveChild ? "text-[#d93829]" : "text-[#8c8276] group-hover:text-[#191410]")} />
                  <span className="uppercase text-[11px] tracking-wider">{group.label}</span>
                </div>
                {isOpen ? (
                  <ChevronDown className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100 transition-transform" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100 transition-transform" />
                )}
              </button>

              {/* Group Items */}
              {isOpen && (
                <div className="space-y-0.5 pl-2 animate-in fade-in slide-in-from-top-1 duration-150">
                  {group.items.map(item => {
                    const toPath = `/cases/${caseId}/${item.path}`;
                    const isPinned = pinnedItemIds.includes(item.id);

                    return (
                      <NavLink
                        key={item.id}
                        to={toPath}
                        className={({ isActive }) => cn(
                          "flex items-center justify-between px-3 py-1.5 rounded-xl text-xs font-medium transition-all group cursor-pointer relative",
                          isActive
                            ? "bg-[#d93829]/10 text-[#d93829] font-bold border border-[#d93829]/25 shadow-2xs"
                            : "text-[#6e665d] hover:bg-[#faf7f2] hover:text-[#191410]"
                        )}
                      >
                        <div className="flex items-center gap-2.5 truncate">
                          <item.icon className="w-3.5 h-3.5 opacity-75 group-hover:opacity-100 transition-opacity shrink-0" />
                          <span className="truncate">{item.label}</span>
                        </div>

                        <div className="flex items-center gap-1.5 shrink-0">
                          {renderBadge(item.badgeSource)}
                          <button
                            type="button"
                            onClick={(e) => togglePin(item.id, e)}
                            className={cn(
                              "p-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity text-stone-400 hover:text-stone-700",
                              isPinned && "opacity-80 text-amber-600"
                            )}
                            title={isPinned ? "Unpin shortcut" : "Pin shortcut to top"}
                          >
                            <Pin className="w-2.5 h-2.5" />
                          </button>
                        </div>
                      </NavLink>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Bottom Footer: Settings & Case Wall */}
      <div className="p-3 border-t border-[#eae4d9] bg-[#faf7f2]/60 shrink-0 space-y-1">
        {!isCollapsed ? (
          <>
            <a
              href={`/cases/${caseId}/wall`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between px-3 py-1.5 rounded-xl text-xs font-mono font-medium text-[#6e665d] hover:bg-white hover:text-[#191410] border border-transparent hover:border-[#eae4d9] transition-all cursor-pointer"
              title="Open full-screen Situation Board on a second monitor"
            >
              <span>Live Case Wall (2nd Screen)</span>
              <span className="text-[10px] text-[#d93829] font-bold">↗</span>
            </a>

            <NavLink
              to={`/cases/${caseId}/config`}
              className={({ isActive }) => cn(
                "flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-medium transition-all",
                isActive 
                  ? "bg-[#191410] text-white font-bold" 
                  : "text-[#6e665d] hover:bg-white hover:text-[#191410]"
              )}
            >
              <Sliders className="w-3.5 h-3.5 text-[#8c8276]" />
              <span>Scoring & Settings</span>
            </NavLink>
          </>
        ) : (
          <div className="flex flex-col items-center gap-1">
            <a
              href={`/cases/${caseId}/wall`}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-xl text-[#6e665d] hover:text-[#191410] hover:bg-white cursor-pointer"
              title="Live Case Wall"
            >
              ↗
            </a>
            <NavLink
              to={`/cases/${caseId}/config`}
              className="p-2 rounded-xl text-[#6e665d] hover:text-[#191410] hover:bg-white cursor-pointer"
              title="Settings"
            >
              <Sliders className="w-4 h-4" />
            </NavLink>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile Drawer Trigger Pill */}
      <div className="md:hidden fixed top-3 left-4 z-40">
        <button
          onClick={() => setIsMobileOpen(true)}
          className="p-2 rounded-xl bg-white border border-[#eae4d9] text-[#191410] shadow-md cursor-pointer"
          title="Open Case Navigation"
        >
          <Menu className="w-5 h-5 text-[#d93829]" />
        </button>
      </div>

      {/* Desktop Sidebar */}
      <aside 
        className={cn(
          "hidden md:flex bg-white/95 backdrop-blur-md border-r border-[#eae4d9] h-full flex-col shrink-0 shadow-xs transition-all duration-200",
          isCollapsed ? "w-16" : "w-64"
        )}
      >
        {sidebarContent}
      </aside>

      {/* Mobile Slide-In Drawer */}
      {isMobileOpen && (
        <div className="md:hidden fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex">
          <div className="w-72 bg-white h-full shadow-2xl flex flex-col animate-in slide-in-from-left duration-200">
            <div className="p-2 flex justify-end border-b border-[#eae4d9]">
              <button 
                onClick={() => setIsMobileOpen(false)}
                className="p-1.5 rounded-xl hover:bg-[#faf7f2] text-stone-500 hover:text-stone-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-hidden" onClick={() => setIsMobileOpen(false)}>
              {sidebarContent}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
