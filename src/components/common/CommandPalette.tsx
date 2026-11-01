import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { 
  Search, Command, FileText, CheckSquare, ShieldCheck, Award, 
  Tv, Clock, MapPin, Activity, Network, Sparkles, X, ChevronRight, 
  CornerDownLeft, Loader2, ArrowRight, BookOpen, Quote, Users, 
  BrainCircuit, ShieldAlert, Fingerprint, ExternalLink, Hash, Filter
} from 'lucide-react';
import { omniSearchService } from '../../services';
import { OmniSearchResultItem, PaletteCommand } from '../../types';
import { isDemoMode, setDemoMode } from '../../config/api';
import { CASE_NAV_GROUPS, SETTINGS_TECHNICAL_ITEMS } from '../../config/caseNav';

interface CommandPaletteProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ 
  isOpen: controlledIsOpen, 
  onClose: controlledOnClose 
}) => {
  const [internalIsOpen, setInternalIsOpen] = useState(false);
  const isOpen = controlledIsOpen !== undefined ? controlledIsOpen : internalIsOpen;

  const [query, setQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState<string>('all');
  const [results, setResults] = useState<OmniSearchResultItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);

  const location = useLocation();
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const resultsContainerRef = useRef<HTMLDivElement>(null);

  // Extract caseId if currently navigating inside a case
  const pathParts = location.pathname.split('/').filter(Boolean);
  const currentCaseId = (pathParts[0] === 'cases' && pathParts[1] && pathParts[1] !== 'dashboard') 
    ? pathParts[1] 
    : null;

  const handleClose = () => {
    if (controlledOnClose) {
      controlledOnClose();
    } else {
      setInternalIsOpen(false);
    }
    setQuery('');
    setResults([]);
    setSelectedIndex(0);
  };

  const handleOpen = () => {
    if (controlledIsOpen === undefined) {
      setInternalIsOpen(true);
    }
  };

  // Keyboard shortcut listener: Ctrl+K, Cmd+K, and '/'
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Toggle palette on Cmd+K / Ctrl+K
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (isOpen) {
          handleClose();
        } else {
          handleOpen();
        }
        return;
      }

      // Open on '/' if not currently focusing an editable input
      if (e.key === '/' && !isOpen) {
        const target = e.target as HTMLElement | null;
        const isEditable = target && (
          target.tagName === 'INPUT' || 
          target.tagName === 'TEXTAREA' || 
          target.isContentEditable
        );
        if (!isEditable) {
          e.preventDefault();
          handleOpen();
          return;
        }
      }

      // Close on Escape
      if (e.key === 'Escape' && isOpen) {
        e.preventDefault();
        handleClose();
      }
    };

    const handleCustomOpen = (e: Event) => {
      const customEvent = e as CustomEvent<{ query?: string; category?: string }>;
      handleOpen();
      if (customEvent.detail?.query) {
        setQuery(customEvent.detail.query);
      }
      if (customEvent.detail?.category) {
        setActiveCategory(customEvent.detail.category);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('evidentia:open-command-palette', handleCustomOpen);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('evidentia:open-command-palette', handleCustomOpen);
    };
  }, [isOpen]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => {
        inputRef.current?.focus();
        inputRef.current?.select();
      }, 50);
    }
  }, [isOpen]);

  // Built-in system and investigation commands derived dynamically from navigation config
  const commands: PaletteCommand[] = useMemo(() => {
    const dynamicNavCommands: PaletteCommand[] = [];

    // Map all navigation groups into dynamic searchable palette commands
    CASE_NAV_GROUPS.forEach(group => {
      group.items.forEach(item => {
        dynamicNavCommands.push({
          id: `cmd-nav-${item.id}`,
          title: item.label,
          description: item.description || `Navigate to ${item.label}`,
          category: group.id === 'evidence' ? 'forensics' : group.id === 'my_case' ? 'investigation' : 'navigation',
          iconName: item.id === 'suspects_theories' || item.id === 'suspects' ? 'BrainCircuit' : item.id === 'exhibits' ? 'FileText' : item.id === 'missing_evidence' ? 'CheckSquare' : 'Activity',
          keywords: [
            ...item.searchKeywords,
            ...(item.replaces || []),
            ...(item.oldPaths || []),
            item.label.toLowerCase(),
            (item.methodologyLabel || '').toLowerCase(),
            group.label.toLowerCase()
          ],
          action: () => {
            navigate(currentCaseId ? `/cases/${currentCaseId}/${item.path}` : '/cases');
          }
        });
      });
    });

    // Map admin settings items
    SETTINGS_TECHNICAL_ITEMS.forEach(item => {
      dynamicNavCommands.push({
        id: `cmd-admin-${item.id}`,
        title: item.label,
        description: item.description || `Configure ${item.label}`,
        category: 'system',
        iconName: 'ShieldCheck',
        keywords: [
          ...item.searchKeywords,
          ...(item.replaces || []),
          ...(item.oldPaths || []),
          item.label.toLowerCase(),
          (item.methodologyLabel || '').toLowerCase(),
          'settings',
          'admin'
        ],
        action: () => {
          navigate(`/settings?section=${item.id}`);
        }
      });
    });

    // System-wide utilities
    const systemCommands: PaletteCommand[] = [
      {
        id: 'cmd-add-task',
        title: 'Add Investigation Task',
        description: currentCaseId 
          ? `Create a priority task or investigative gap resolution in Case #${currentCaseId}`
          : 'Open investigation planning dashboard to log new leads',
        category: 'investigation',
        iconName: 'CheckSquare',
        keywords: ['task', 'add task', 'todo', 'plan', 'gap', 'action'],
        action: () => {
          navigate(currentCaseId ? `/cases/${currentCaseId}/investigation-plan?action=new-task` : '/cases');
        }
      },
      {
        id: 'cmd-case-wall',
        title: 'Open Situation Board (Case Wall)',
        description: currentCaseId 
          ? `Launch live auto-refreshing wallboard for team room or second monitor (Case #${currentCaseId})`
          : 'Launch live situation board for case overview',
        category: 'navigation',
        iconName: 'Tv',
        keywords: ['wall', 'case wall', 'situation board', 'monitor', 'live', 'tv', 'display'],
        action: () => {
          if (currentCaseId) {
            window.open(`/cases/${currentCaseId}/wall`, '_blank');
          } else {
            navigate('/cases');
          }
        }
      },
      {
        id: 'cmd-system-health',
        title: 'Open Live System Health & Diagnostics',
        description: 'Monitor worker queues, API availability, and database disaster recovery backups',
        category: 'system',
        iconName: 'Activity',
        keywords: ['health', 'system health', 'telemetry', 'status', 'backup', 'queue', 'uptime'],
        action: () => {
          navigate('/system-health');
        }
      },
      {
        id: 'cmd-toggle-demo',
        title: isDemoMode() ? 'Switch to Live Backend Mode' : 'Switch to Demo Mock Mode',
        description: isDemoMode() 
          ? 'Enforce real FastAPI backend queries and live database sync'
          : 'Enable safe offline demo sandbox with simulated responses',
        category: 'system',
        iconName: 'Sparkles',
        keywords: ['demo', 'mode', 'mock', 'live', 'switch', 'backend'],
        action: () => {
          const next = !isDemoMode();
          setDemoMode(next);
        }
      }
    ];

    return [...dynamicNavCommands, ...systemCommands];
  }, [currentCaseId, navigate]);

  // Filter commands by query
  const matchingCommands = useMemo(() => {
    if (activeCategory !== 'all' && activeCategory !== 'commands') {
      return [];
    }
    const cleanQ = query.trim().replace(/^>\s*/, '').toLowerCase();
    if (!cleanQ) {
      return commands;
    }
    return commands.filter(cmd => {
      if (cmd.title.toLowerCase().includes(cleanQ)) return true;
      if (cmd.description.toLowerCase().includes(cleanQ)) return true;
      return cmd.keywords?.some(k => k.toLowerCase().includes(cleanQ));
    });
  }, [commands, query, activeCategory]);

  // Debounced search query across the backend omni-search engine
  useEffect(() => {
    const cleanQ = query.trim().replace(/^>\s*/, '');
    
    // If empty or purely a command prompt (e.g. ">"), don't call backend search
    if (!cleanQ || query.startsWith('>')) {
      setResults([]);
      setIsLoading(false);
      return;
    }

    // Skip API search if only 'commands' category is selected
    if (activeCategory === 'commands') {
      setResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        setIsLoading(true);
        const searchCategory = activeCategory === 'all' ? undefined : activeCategory;
        let response;
        if (currentCaseId) {
          response = await omniSearchService.searchCase(currentCaseId, cleanQ, searchCategory, 35);
        } else {
          response = await omniSearchService.searchGlobal(cleanQ, searchCategory, 35);
        }
        setResults(response.matches || []);
        setSelectedIndex(0);
      } catch (err) {
        console.warn('Omni-search query failed:', err);
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    }, 180);

    return () => clearTimeout(timer);
  }, [query, activeCategory, currentCaseId]);

  // Combined selectable items list for keyboard navigation
  const combinedItems = useMemo(() => {
    const items: Array<{ type: 'command'; item: PaletteCommand } | { type: 'result'; item: OmniSearchResultItem }> = [];
    matchingCommands.forEach(c => items.push({ type: 'command', item: c }));
    results.forEach(r => items.push({ type: 'result', item: r }));
    return items;
  }, [matchingCommands, results]);

  // Handle keyboard up/down/enter inside palette
  const handleKeyDownInInput = (e: React.KeyboardEvent) => {
    if (combinedItems.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (prev + 1) % combinedItems.length);
      scrollSelectedIntoView((selectedIndex + 1) % combinedItems.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (prev - 1 + combinedItems.length) % combinedItems.length);
      scrollSelectedIntoView((selectedIndex - 1 + combinedItems.length) % combinedItems.length);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const current = combinedItems[selectedIndex];
      if (current) {
        handleExecuteItem(current);
      }
    }
  };

  const scrollSelectedIntoView = (index: number) => {
    if (!resultsContainerRef.current) return;
    const items = resultsContainerRef.current.querySelectorAll('[data-palette-item]');
    const target = items[index] as HTMLElement | undefined;
    if (target) {
      target.scrollIntoView({ block: 'nearest' });
    }
  };

  const handleExecuteItem = (entry: { type: 'command'; item: PaletteCommand } | { type: 'result'; item: OmniSearchResultItem }) => {
    handleClose();
    if (entry.type === 'command') {
      entry.item.action();
    } else {
      const result = entry.item;
      if (result.target_url) {
        navigate(result.target_url);
      }
    }
  };

  // Helper to render matched snippet with highlight marks
  const renderHighlightedSnippet = (snippet: string, highlightTerm: string) => {
    if (!snippet || !highlightTerm) return snippet;
    const parts = snippet.split(new RegExp(`(${highlightTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
    return parts.map((part, idx) => {
      if (part.toLowerCase() === highlightTerm.toLowerCase()) {
        return (
          <mark 
            key={idx} 
            className="bg-[#fef08a] text-[#854d0e] font-semibold px-1 rounded-sm shadow-2xs"
          >
            {part}
          </mark>
        );
      }
      return <span key={idx}>{part}</span>;
    });
  };

  // Icon selector helper
  const getCategoryIcon = (category: string) => {
    switch (category.toLowerCase()) {
      case 'exhibit':
        return <FileText className="w-4 h-4 text-sky-600" />;
      case 'quote':
      case 'citation':
        return <Quote className="w-4 h-4 text-emerald-600" />;
      case 'entity':
        return <Users className="w-4 h-4 text-indigo-600" />;
      case 'claim':
      case 'hypothesis':
        return <BrainCircuit className="w-4 h-4 text-purple-600" />;
      case 'suspect':
        return <ShieldAlert className="w-4 h-4 text-rose-600" />;
      case 'task':
        return <CheckSquare className="w-4 h-4 text-amber-600" />;
      case 'alert':
        return <Activity className="w-4 h-4 text-red-600" />;
      default:
        return <Search className="w-4 h-4 text-stone-500" />;
    }
  };

  const getCommandIcon = (iconName: string) => {
    switch (iconName) {
      case 'BrainCircuit': return <BrainCircuit className="w-4 h-4 text-purple-600" />;
      case 'CheckSquare': return <CheckSquare className="w-4 h-4 text-amber-600" />;
      case 'ShieldCheck': return <ShieldCheck className="w-4 h-4 text-emerald-600" />;
      case 'Award': return <Award className="w-4 h-4 text-blue-600" />;
      case 'Tv': return <Tv className="w-4 h-4 text-[#d93829]" />;
      case 'Clock': return <Clock className="w-4 h-4 text-amber-600" />;
      case 'Activity': return <Activity className="w-4 h-4 text-emerald-600" />;
      case 'Network': return <Network className="w-4 h-4 text-indigo-600" />;
      case 'Sparkles': return <Sparkles className="w-4 h-4 text-amber-500" />;
      default: return <Command className="w-4 h-4 text-stone-600" />;
    }
  };

  const categories = [
    { id: 'all', label: 'All Results' },
    { id: 'commands', label: 'Commands' },
    { id: 'exhibit', label: 'Exhibits' },
    { id: 'quote', label: 'Quotes & Spans' },
    { id: 'entity', label: 'Entities' },
    { id: 'claim', label: 'Claims' },
    { id: 'suspect', label: 'Suspects' },
    { id: 'task', label: 'Tasks' },
    { id: 'alert', label: 'Alerts' },
  ];

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-start justify-center pt-[9vh] px-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150"
      onClick={handleClose}
    >
      <div 
        className="w-full max-w-2xl bg-[#faf7f2] rounded-2xl shadow-2xl border border-[#eae4d9] overflow-hidden flex flex-col max-h-[82vh] transition-all"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Search Input Bar */}
        <div className="p-4 bg-white border-b border-[#eae4d9] flex items-center gap-3">
          <div className="p-2 rounded-xl bg-[#f5efe6] text-[#70685e]">
            {isLoading ? (
              <Loader2 className="w-5 h-5 text-[#d93829] animate-spin" />
            ) : (
              <Search className="w-5 h-5 text-[#8c8276]" />
            )}
          </div>
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setSelectedIndex(0);
              }}
              onKeyDown={handleKeyDownInInput}
              placeholder={
                currentCaseId
                  ? `Search Case #${currentCaseId} exhibits, quotes, entities, claims, or run a command...`
                  : 'Search across all cases, quotes, entities, claims, or run a command...'
              }
              className="w-full bg-transparent text-sm md:text-base font-medium text-[#191410] placeholder:text-[#a89f91] focus:outline-hidden"
            />
          </div>
          {query && (
            <button
              onClick={() => {
                setQuery('');
                setResults([]);
                setSelectedIndex(0);
                inputRef.current?.focus();
              }}
              className="p-1 rounded-md text-[#8c8276] hover:text-[#191410] hover:bg-[#f5efe6] transition"
              title="Clear search"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <div className="hidden sm:flex items-center gap-1.5 px-2 py-1 rounded-md bg-[#f5efe6] text-[11px] font-mono text-[#70685e] border border-[#e5dec0]/60">
            <span>ESC</span>
          </div>
        </div>

        {/* Category Filters Bar */}
        <div className="px-4 py-2 bg-[#f6f2ea] border-b border-[#eae4d9] flex items-center gap-1.5 overflow-x-auto no-scrollbar">
          <Filter className="w-3.5 h-3.5 text-[#8c8276] shrink-0 mr-1" />
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => {
                setActiveCategory(cat.id);
                setSelectedIndex(0);
              }}
              className={`px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-all cursor-pointer ${
                activeCategory === cat.id
                  ? 'bg-[#d93829] text-white shadow-2xs'
                  : 'bg-white/80 text-[#70685e] hover:bg-white hover:text-[#191410] border border-[#eae4d9]'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Results & Commands List Container */}
        <div 
          ref={resultsContainerRef}
          className="flex-1 overflow-y-auto p-3 space-y-4 max-h-[58vh] divide-y divide-[#eae4d9]/60"
        >
          {/* Section A: Matching Commands */}
          {matchingCommands.length > 0 && (
            <div className="space-y-1.5 pt-1 first:pt-0">
              <div className="px-2 py-1 text-[11px] font-mono font-bold tracking-wider uppercase text-[#8c8276] flex items-center justify-between">
                <span>Investigative Commands</span>
                <span className="text-[10px] text-[#a89f91]">{matchingCommands.length} available</span>
              </div>
              <div className="space-y-1">
                {matchingCommands.map((cmd, idx) => {
                  const isSelected = selectedIndex === idx;
                  return (
                    <div
                      key={cmd.id}
                      data-palette-item
                      onClick={() => handleExecuteItem({ type: 'command', item: cmd })}
                      onMouseEnter={() => setSelectedIndex(idx)}
                      className={`p-2.5 rounded-xl flex items-center justify-between gap-3 cursor-pointer transition-all ${
                        isSelected 
                          ? 'bg-[#f0e9dc] border border-[#d93829]/40 shadow-xs' 
                          : 'bg-white hover:bg-[#f6f2ea] border border-[#eae4d9]'
                      }`}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className={`p-2 rounded-lg ${isSelected ? 'bg-white text-[#d93829]' : 'bg-[#faf7f2] text-[#70685e]'}`}>
                          {getCommandIcon(cmd.iconName)}
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-xs md:text-sm text-[#191410] truncate">
                              {cmd.title}
                            </span>
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-mono uppercase bg-[#ede6d8] text-[#70685e]">
                              {cmd.category}
                            </span>
                          </div>
                          <p className="text-xs text-[#70685e] truncate mt-0.5">
                            {cmd.description}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-[10px] font-mono text-[#8c8276] hidden sm:inline">Run</span>
                        <CornerDownLeft className="w-3.5 h-3.5 text-[#8c8276]" />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Section B: Backend Evidence & Operational Search Results */}
          {results.length > 0 && (
            <div className="space-y-1.5 pt-3">
              <div className="px-2 py-1 text-[11px] font-mono font-bold tracking-wider uppercase text-[#8c8276] flex items-center justify-between">
                <span>Matching Exhibits & Findings</span>
                <span className="text-[10px] text-[#a89f91]">{results.length} matches</span>
              </div>
              <div className="space-y-2">
                {results.map((res, rIdx) => {
                  const globalIdx = matchingCommands.length + rIdx;
                  const isSelected = selectedIndex === globalIdx;
                  return (
                    <div
                      key={res.id || rIdx}
                      data-palette-item
                      onClick={() => handleExecuteItem({ type: 'result', item: res })}
                      onMouseEnter={() => setSelectedIndex(globalIdx)}
                      className={`p-3 rounded-xl flex flex-col gap-2 cursor-pointer transition-all ${
                        isSelected 
                          ? 'bg-[#f0e9dc] border border-[#d93829]/50 shadow-xs' 
                          : 'bg-white hover:bg-[#f6f2ea] border border-[#eae4d9]'
                      }`}
                    >
                      {/* Match Header */}
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <div className={`p-1.5 rounded-lg ${isSelected ? 'bg-white' : 'bg-[#faf7f2]'}`}>
                            {getCategoryIcon(res.category)}
                          </div>
                          <span className="font-bold text-xs md:text-sm text-[#191410] truncate">
                            {res.title}
                          </span>
                        </div>
                        {/* Match Source Badge: Shows where the hit originated */}
                        <div className="flex items-center gap-1.5 shrink-0">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-[#fff1ee] text-[#d93829] border border-[#fbd0c8]">
                            {res.match_source}
                          </span>
                          {res.metadata?.evidence_id && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-[#f5efe6] text-[#70685e]">
                              Ex #{res.metadata.evidence_id}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Highlighted Snippet */}
                      {res.matched_snippet && (
                        <div className="text-xs text-[#524a41] bg-[#faf7f2]/90 p-2 rounded-lg border border-[#eae4d9] font-mono leading-relaxed line-clamp-2">
                          {renderHighlightedSnippet(res.matched_snippet, res.highlight_term)}
                        </div>
                      )}

                      {/* Deep-link action hint */}
                      <div className="flex items-center justify-between text-[11px] text-[#8c8276] pt-1">
                        <div className="flex items-center gap-1">
                          <span className="capitalize">{res.category}</span>
                          {res.page_number && <span>• Page {res.page_number}</span>}
                          {res.char_start !== undefined && res.char_start !== null && (
                            <span>• Byte offset {res.char_start}</span>
                          )}
                        </div>
                        <div className="flex items-center gap-1 text-[#d93829] font-semibold">
                          <span>Jump straight to highlighted passage</span>
                          <ArrowRight className="w-3 h-3" />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Empty State */}
          {combinedItems.length === 0 && !isLoading && query && (
            <div className="py-12 text-center space-y-2">
              <div className="w-12 h-12 rounded-2xl bg-[#f5efe6] text-[#8c8276] flex items-center justify-center mx-auto">
                <Search className="w-6 h-6" />
              </div>
              <h4 className="font-serif font-bold text-base text-[#191410]">
                No matching results found
              </h4>
              <p className="text-xs text-[#70685e] max-w-sm mx-auto">
                No exhibits, normalized texts, regional translations, quotes, entities, claims, or tasks matched &ldquo;{query}&rdquo;.
              </p>
            </div>
          )}
        </div>

        {/* Footer Navigation Bar */}
        <div className="p-3 bg-[#f6f2ea] border-t border-[#eae4d9] flex flex-wrap items-center justify-between text-[11px] text-[#70685e] gap-2">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 rounded bg-white border border-[#eae4d9] text-[10px] font-mono font-bold text-[#191410]">↑</kbd>
              <kbd className="px-1.5 py-0.5 rounded bg-white border border-[#eae4d9] text-[10px] font-mono font-bold text-[#191410]">↓</kbd>
              <span>to navigate</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 rounded bg-white border border-[#eae4d9] text-[10px] font-mono font-bold text-[#191410]">↵</kbd>
              <span>to select</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 rounded bg-white border border-[#eae4d9] text-[10px] font-mono font-bold text-[#191410]">ESC</kbd>
              <span>to close</span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono bg-white px-2 py-0.5 rounded-full border border-[#eae4d9]">
              Type <strong className="text-[#d93829]">&gt;</strong> for commands only
            </span>
            {currentCaseId && (
              <span className="text-[10px] font-mono font-bold text-[#d93829] bg-[#fdeee9] px-2 py-0.5 rounded-full">
                Case #{currentCaseId} Context
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

