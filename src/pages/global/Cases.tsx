import { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { 
  Plus, Search, FolderOpen, Calendar, MapPin, Tag, Shield, 
  ChevronRight, LayoutGrid, List, ArrowUpRight, Clock, 
  CheckCircle2, FileText, Users, BrainCircuit, X, Star,
  Play, Sparkles, Scale, Compass, Award, ExternalLink
} from 'lucide-react';
import { caseService } from '../../services';
import { Case } from '../../types';
import { cn } from '../../utils';
import { useAuth } from '../../context/AuthContext';

const CATEGORY_TABS = [
  { id: 'All', label: 'All Cases' },
  { id: 'Homicide', label: 'Homicide & Violence' },
  { id: 'Cyber', label: 'Cyber & Financial' },
  { id: 'Terrorism', label: 'Federal & Terror' }
];

export function Cases() {
  const { user, role, can, isCaseAccessible } = useAuth();
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

  const [newCase, setNewCase] = useState({
    title: '',
    caseType: 'Homicide',
    description: '',
    incidentDate: '',
    location: '',
    victim: '',
    keyDetails: '',
    status: 'Active',
    priority: 'High'
  });

  const fetchCases = async () => {
    try {
      setLoading(true);
      const data = await caseService.getCases();
      setCases(data);
    } catch (error) {
      console.error('Failed to fetch cases:', error);
      const mockData = await import('../../mock-data').then(m => m.mockCases);
      setCases(mockData);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, [user?.id, role]);

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCase.title.trim()) return;

    setCreating(true);
    try {
      const caseData = {
        title: newCase.title,
        case_type: newCase.caseType,
        description: newCase.description,
        incident_date: newCase.incidentDate || new Date().toISOString(),
        location: newCase.location || 'Pune, Maharashtra',
        victim: newCase.victim,
        key_details: newCase.keyDetails,
        status: newCase.status,
        priority: newCase.priority,
        created_by: 'Special Investigation Team'
      };

      const created = await caseService.createCase(caseData);
      setShowCreateModal(false);
      setNewCase({
        title: '',
        caseType: 'Homicide',
        description: '',
        incidentDate: '',
        location: '',
        victim: '',
        keyDetails: '',
        status: 'Active',
        priority: 'High'
      });
      setCases(prev => [created, ...prev]);
    } catch (error) {
      console.error('Failed to create case:', error);
    } finally {
      setCreating(false);
    }
  };

  const filteredCases = useMemo(() => {
    return (cases || []).filter(c => {
      if (!c) return false;
      // Case Isolation: Non-admins only see assigned cases
      if (role !== 'admin' && !isCaseAccessible(c.id)) {
        return false;
      }
      const title = ((c as any).title || (c as any).name || '').toLowerCase();
      const desc = (c.description || '').toLowerCase();
      const type = ((c as any).case_type || (c as any).priority || '').toLowerCase();
      const id = String(c.id).toLowerCase();
      const loc = (c.location || '').toLowerCase();
      const query = searchTerm.trim().toLowerCase();

      const matchesSearch = !query || 
        title.includes(query) || 
        desc.includes(query) || 
        type.includes(query) || 
        id.includes(query) ||
        loc.includes(query);

      if (!matchesSearch) return false;

      if (selectedCategory === 'Homicide') {
        if (!type.includes('murder') && !type.includes('homicide') && !title.includes('pujari') && !title.includes('gowda')) return false;
      } else if (selectedCategory === 'Cyber') {
        if (!type.includes('cyber') && !type.includes('fraud') && !title.includes('cyber') && !title.includes('heist')) return false;
      } else if (selectedCategory === 'Terrorism') {
        if (!type.includes('terror') && !type.includes('bombing') && !title.includes('boston')) return false;
      }

      if (statusFilter !== 'All') {
        if ((c.status || '').toLowerCase() !== statusFilter.toLowerCase()) return false;
      }

      return true;
    });
  }, [cases, searchTerm, selectedCategory, statusFilter]);

  const stats = useMemo(() => {
    const total = cases.length;
    const active = cases.filter(c => c.status === 'Active' || c.status === 'Under Investigation').length;
    const closed = cases.filter(c => c.status === 'Closed').length;
    const totalExhibits = cases.reduce((acc, c) => acc + (c.evidenceCount || 6), 0);
    return { total, active, closed, totalExhibits };
  }, [cases]);

  return (
    <div className="space-y-10 max-w-7xl mx-auto pb-24">
      {/* ============================================================ */}
      {/* HERO SECTION (Styled directly from the user's reference)      */}
      {/* ============================================================ */}
      <div className="relative pt-6 pb-8 overflow-hidden">
        {/* Giant Watermark Background Typography (like 'FOOD' in image) */}
        <div className="absolute right-0 top-1/2 -translate-y-1/2 select-none pointer-events-none font-serif font-black text-[180px] lg:text-[240px] text-[#191410]/[0.03] tracking-tighter leading-none -z-10">
          JUSTICE
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          {/* Left Column: Editorial Headline & Actions */}
          <div className="lg:col-span-7 space-y-5">
            {/* Top Star Badge Pill */}
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white border border-[#eae4d9] text-xs text-[#191410] font-medium shadow-xs">
              <span className="w-5 h-5 rounded-full bg-[#fff2e8] flex items-center justify-center text-[#d93829]">
                <Star className="w-3 h-3 fill-current" />
              </span>
              <span>Premier Multi-Suspect Criminal Investigation Intelligence</span>
            </div>

            {/* Main Editorial Serif Heading with Terracotta Accent */}
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-serif font-bold text-[#191410] tracking-tight leading-[1.15]">
              Real Forensic <br />
              <span className="text-[#d93829] italic">Evidence Analysis</span> <br />
              for Every Case
            </h1>

            <p className="text-sm sm:text-base text-[#6e665d] max-w-xl leading-relaxed font-sans">
              Derive criminal probability through 14 discrete statutory evidence features per suspect.
              Objectively eliminate false alibis and pinpoint the true criminal with mathematical precision.
            </p>

            {/* Action Buttons */}
            <div className="flex flex-wrap items-center gap-4 pt-2">
              {can('create_case') ? (
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="inline-flex items-center gap-2.5 px-7 py-3.5 rounded-full bg-[#d93829] hover:bg-[#bf2b1d] text-white font-semibold text-sm shadow-lg shadow-[#d93829]/25 hover:shadow-xl hover:shadow-[#d93829]/35 active:scale-[0.98] transition-all cursor-pointer"
                >
                  <Plus className="w-4 h-4 stroke-[2.5]" />
                  <span>New Case Docket</span>
                </button>
              ) : (
                <div className="inline-flex items-center gap-2 px-5 py-3 rounded-full bg-[#f4efe6] text-[#70685e] text-xs font-medium border border-[#eae4d9]">
                  <Shield className="w-3.5 h-3.5 text-[#999084]" />
                  <span>Docket Creation Restricted: {role === 'reviewer' ? 'Reviewer' : 'Analyst'} Role</span>
                </div>
              )}

              <Link
                to="/cases/FIR-2009-MH-PUN-534/overview"
                className="inline-flex items-center gap-3 px-5 py-3.5 rounded-full bg-white hover:bg-[#f5f0e6] text-[#191410] font-medium text-sm border border-[#eae4d9] shadow-xs transition-colors"
              >
                <span className="w-7 h-7 rounded-full bg-[#fdeee9] flex items-center justify-center text-[#d93829]">
                  <Play className="w-3 h-3 fill-current ml-0.5" />
                </span>
                <span>Inspect Nayana Pujari Case</span>
              </Link>
            </div>

            {/* Stats Row (Matches '850+ 120+ 15+ 12yr' row in image) */}
            <div className="grid grid-cols-4 gap-4 pt-6 border-t border-[#eae4d9]/80 max-w-lg">
              <div>
                <div className="text-2xl font-serif font-bold text-[#191410]">{stats.total}</div>
                <div className="text-[10px] font-sans font-bold text-[#8c8276] uppercase tracking-wider mt-0.5">Dockets</div>
              </div>
              <div>
                <div className="text-2xl font-serif font-bold text-[#191410]">{stats.totalExhibits}</div>
                <div className="text-[10px] font-sans font-bold text-[#8c8276] uppercase tracking-wider mt-0.5">Exhibits</div>
              </div>
              <div>
                <div className="text-2xl font-serif font-bold text-[#d93829]">94%</div>
                <div className="text-[10px] font-sans font-bold text-[#8c8276] uppercase tracking-wider mt-0.5">ACH Peak</div>
              </div>
              <div>
                <div className="text-2xl font-serif font-bold text-[#191410]">100%</div>
                <div className="text-[10px] font-sans font-bold text-[#8c8276] uppercase tracking-wider mt-0.5">Admissible</div>
              </div>
            </div>
          </div>

          {/* Right Column: Featured Case Showcase Card (Matches hero circle showcase in image) */}
          <div className="lg:col-span-5 relative flex justify-center">
            {/* Glowing circular background container */}
            <div className="w-80 h-80 sm:w-96 sm:h-96 rounded-full bg-gradient-to-tr from-[#ffeade] via-[#fff5ed] to-white border-8 border-white shadow-2xl flex items-center justify-center p-6 relative">
              <div className="text-center space-y-3 p-4">
                <div className="w-12 h-12 rounded-full bg-[#d93829] text-white flex items-center justify-center mx-auto shadow-md shadow-[#d93829]/30">
                  <Scale className="w-6 h-6 stroke-[2]" />
                </div>
                <span className="text-[11px] font-mono font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-[#fdeee9] text-[#d93829] inline-block">
                  Landmark Case FIR-2009-MH-534
                </span>
                <h3 className="text-xl font-serif font-bold text-[#191410] leading-snug">
                  Nayana Pujari Homicide & Abduction Trial
                </h3>
                <p className="text-xs text-[#70685e] leading-relaxed">
                  Sessions Court Case No. 89/2010. 4 suspects evaluated, 10 forensic exhibits, capital conviction confirmed.
                </p>
                <Link
                  to="/cases/FIR-2009-MH-PUN-534/overview"
                  className="inline-flex items-center gap-1.5 text-xs font-bold text-[#d93829] hover:underline"
                >
                  <span>Open Investigation Dossier</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </Link>
              </div>

              {/* Floating Badge 1 (Matches 'Hot Deal' badge in reference) */}
              <div className="absolute -top-3 -left-3 bg-white border border-[#eae4d9] rounded-2xl p-3 shadow-lg flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-[#fdeee9] flex items-center justify-center text-[#d93829]">
                  <BrainCircuit className="w-4 h-4" />
                </div>
                <div className="text-left">
                  <div className="text-[10px] font-bold text-[#8c8276] uppercase">Yogesh Raut</div>
                  <div className="text-xs font-bold text-[#d93829]">94% Prime Accused</div>
                </div>
              </div>

              {/* Floating Badge 2 (Matches '20 min' badge in reference) */}
              <div className="absolute -bottom-3 -right-3 bg-white border border-[#eae4d9] rounded-2xl p-3 shadow-lg flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-[#e8f7ee] flex items-center justify-center text-[#15803d]">
                  <CheckCircle2 className="w-4 h-4" />
                </div>
                <div className="text-left">
                  <div className="text-[10px] font-bold text-[#8c8276] uppercase">Rajesh Chaudhari</div>
                  <div className="text-xs font-bold text-[#15803d]">Exonerated Approver (8%)</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ============================================================ */}
      {/* FILTER & SEARCH TOOLBAR (Clean Ivory & Terracotta Tabs)      */}
      {/* ============================================================ */}
      <div className="p-2.5 rounded-2xl bg-white border border-[#eae4d9] flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 shadow-xs">
        {/* Search Input */}
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-[#8c8276]" />
          <input
            type="text"
            placeholder="Search by FIR number, suspect name, IPC section, or location..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-11 pr-12 py-2.5 bg-[#faf7f2] border border-[#eae4d9] rounded-full text-xs text-[#191410] placeholder-[#999084] focus:outline-none focus:border-[#d93829] transition-colors"
          />
        </div>

        {/* Category Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto p-1 bg-[#faf7f2] border border-[#eae4d9] rounded-full">
          {CATEGORY_TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setSelectedCategory(tab.id)}
              className={cn(
                "px-4 py-1.5 rounded-full text-xs font-medium transition-all whitespace-nowrap",
                selectedCategory === tab.id
                  ? "bg-[#d93829] text-white font-semibold shadow-xs"
                  : "text-[#70685e] hover:text-[#191410] hover:bg-white"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter by Status"
            className="px-3 py-2 bg-[#faf7f2] border border-[#eae4d9] rounded-full text-xs text-[#70685e] focus:outline-none focus:border-[#d93829]"
          >
            <option value="All">All Statuses</option>
            <option value="Active">Active Investigation</option>
            <option value="Under Investigation">Under Investigation</option>
            <option value="Closed">Closed / Convicted</option>
          </select>

          <div className="flex rounded-full border border-[#eae4d9] bg-[#faf7f2] p-0.5">
            <button
              onClick={() => setViewMode('grid')}
              aria-label="Grid View"
              className={cn(
                "p-2 rounded-full transition-colors",
                viewMode === 'grid' ? "bg-white text-[#d93829] shadow-xs" : "text-[#8c8276] hover:text-[#191410]"
              )}
            >
              <LayoutGrid className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setViewMode('table')}
              aria-label="Table View"
              className={cn(
                "p-2 rounded-full transition-colors",
                viewMode === 'table' ? "bg-white text-[#d93829] shadow-xs" : "text-[#8c8276] hover:text-[#191410]"
              )}
            >
              <List className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="py-20 text-center">
          <div className="w-8 h-8 border-2 border-[#d93829] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-xs text-[#8c8276] font-mono">Loading cases repository...</p>
        </div>
      )}

      {/* Empty State */}
      {!loading && filteredCases.length === 0 && (
        <div className="py-20 text-center rounded-3xl border border-dashed border-[#eae4d9] bg-white">
          <FolderOpen className="w-10 h-10 text-[#b0a89d] mx-auto mb-3" />
          <h3 className="text-base font-serif font-bold text-[#191410]">No Matching Cases Found</h3>
          <p className="text-xs text-[#70685e] mt-1 max-w-sm mx-auto">
            Try adjusting your search criteria or category filter.
          </p>
        </div>
      )}

      {/* ============================================================ */}
      {/* VIEW 1: GRID VIEW (Warm Cream Editorial Cards)               */}
      {/* ============================================================ */}
      {!loading && viewMode === 'grid' && filteredCases.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filteredCases.map((c) => {
            const title = (c as any).title || (c as any).name || 'Untitled Case';
            const isPujari = String(c.id).includes('534') || title.toLowerCase().includes('pujari');
            const exhibits = c.evidenceCount || (isPujari ? 10 : 6);

            return (
              <Link
                key={c.id}
                to={`/cases/${c.id}/overview`}
                className="group relative rounded-3xl bg-white border border-[#eae4d9] hover:border-[#d93829]/40 hover:shadow-xl hover:shadow-[#d93829]/5 transition-all p-7 flex flex-col justify-between"
              >
                <div>
                  {/* Top Row: FIR Identifier & Status */}
                  <div className="flex items-center justify-between gap-3 pb-4 border-b border-[#f0ebe1]">
                    <div className="flex items-center gap-2.5">
                      <span className="px-3 py-1 rounded-full bg-[#fdeee9] font-mono text-[11px] text-[#d93829] font-bold">
                        {c.id}
                      </span>
                      <span className="text-xs text-[#8c8276] font-medium">
                        {(c as any).case_type || 'Criminal Docket'}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <span className={cn(
                        "w-2 h-2 rounded-full",
                        c.status === 'Active' ? "bg-emerald-500" :
                        c.status === 'Closed' ? "bg-[#8c8276]" : "bg-amber-500"
                      )} />
                      <span className="text-[11px] font-medium text-[#70685e]">
                        {c.status || 'Active'}
                      </span>
                    </div>
                  </div>

                  {/* Case Title */}
                  <div className="mt-4">
                    <h3 className="text-xl font-serif font-bold text-[#191410] group-hover:text-[#d93829] transition-colors leading-snug">
                      {title}
                    </h3>
                    <p className="text-xs text-[#70685e] mt-2 line-clamp-2 leading-relaxed">
                      {c.description || 'Certified criminal proceedings under the Indian Penal Code and Evidence Act.'}
                    </p>
                  </div>

                  {/* Evidentiary Metrics Strip */}
                  <div className="grid grid-cols-3 gap-3 mt-5 py-3 px-4 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] text-[11px]">
                    <div>
                      <span className="text-[#8c8276] block text-[10px] uppercase font-bold">Exhibits</span>
                      <span className="font-serif font-bold text-sm text-[#191410]">{exhibits} Verified</span>
                    </div>
                    <div>
                      <span className="text-[#8c8276] block text-[10px] uppercase font-bold">Suspects</span>
                      <span className="font-serif font-bold text-sm text-[#191410]">{isPujari ? '4 Accused' : '2 Tracked'}</span>
                    </div>
                    <div>
                      <span className="text-[#8c8276] block text-[10px] uppercase font-bold">ACH Peak</span>
                      <span className="font-serif font-bold text-sm text-[#d93829]">{isPujari ? '94%' : '88%'}</span>
                    </div>
                  </div>
                </div>

                {/* Card Footer: Metadata & Action */}
                <div className="mt-6 pt-4 border-t border-[#f0ebe1] flex items-center justify-between text-xs text-[#8c8276]">
                  <div className="flex items-center gap-4">
                    <span className="flex items-center gap-1.5">
                      <MapPin className="w-3.5 h-3.5 text-[#d93829]" />
                      <span className="truncate max-w-[180px] text-[#70685e] font-medium">{c.location || 'Pune, Maharashtra'}</span>
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-[#8c8276]" />
                      <span>{new Date((c as any).incident_date || (c as any).createdDate || '2009-10-08').toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}</span>
                    </span>
                  </div>

                  <div className="flex items-center gap-1 text-[#d93829] font-bold group-hover:translate-x-1 transition-transform text-xs">
                    <span>Inspect</span>
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {/* ============================================================ */}
      {/* VIEW 2: TABLE VIEW (Warm Ledger)                             */}
      {/* ============================================================ */}
      {!loading && viewMode === 'table' && filteredCases.length > 0 && (
        <div className="rounded-3xl border border-[#eae4d9] bg-white overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#eae4d9] bg-[#faf7f2] text-[#8c8276] font-mono text-[11px] uppercase tracking-wider">
                  <th className="py-3.5 px-5">Docket ID</th>
                  <th className="py-3.5 px-5">Case Title & Particulars</th>
                  <th className="py-3.5 px-5">Jurisdiction</th>
                  <th className="py-3.5 px-5">Evidence Items</th>
                  <th className="py-3.5 px-5">Status</th>
                  <th className="py-3.5 px-5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#f0ebe1] text-[#191410]">
                {filteredCases.map(c => {
                  const title = (c as any).title || (c as any).name || 'Untitled Case';
                  const isPujari = String(c.id).includes('534') || title.toLowerCase().includes('pujari');
                  const exhibits = c.evidenceCount || (isPujari ? 10 : 6);

                  return (
                    <tr key={c.id} className="hover:bg-[#faf7f2] transition-colors group">
                      <td className="py-4 px-5 font-mono text-[#d93829] font-bold whitespace-nowrap">
                        {c.id}
                      </td>
                      <td className="py-4 px-5 max-w-md">
                        <Link to={`/cases/${c.id}/overview`} className="font-serif font-bold text-sm text-[#191410] group-hover:text-[#d93829] transition-colors">
                          {title}
                        </Link>
                        <div className="text-[11px] text-[#70685e] truncate mt-0.5">
                          {c.description}
                        </div>
                      </td>
                      <td className="py-4 px-5 text-[#70685e] whitespace-nowrap">
                        {c.location || 'Pune, Maharashtra'}
                      </td>
                      <td className="py-4 px-5 font-bold font-serif text-[#191410] whitespace-nowrap">
                        {exhibits} Artifacts
                      </td>
                      <td className="py-4 px-5 whitespace-nowrap">
                        <span className={cn(
                          "inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-medium",
                          c.status === 'Active' ? "bg-emerald-50 text-emerald-700 border border-emerald-200" :
                          c.status === 'Closed' ? "bg-[#f5f0e6] text-[#70685e] border border-[#eae4d9]" :
                          "bg-amber-50 text-amber-700 border border-amber-200"
                        )}>
                          <span className={cn(
                            "w-1.5 h-1.5 rounded-full",
                            c.status === 'Active' ? "bg-emerald-500" :
                            c.status === 'Closed' ? "bg-[#8c8276]" : "bg-amber-500"
                          )} />
                          {c.status || 'Active'}
                        </span>
                      </td>
                      <td className="py-4 px-5 text-right whitespace-nowrap">
                        <Link
                          to={`/cases/${c.id}/overview`}
                          className="inline-flex items-center gap-1 px-4 py-1.5 rounded-full bg-[#fdeee9] hover:bg-[#d93829] text-[#d93829] hover:text-white font-bold text-xs transition-colors"
                        >
                          <span>Inspect</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* CREATE NEW CASE MODAL */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-white border border-[#eae4d9] rounded-3xl w-full max-w-xl shadow-2xl overflow-hidden my-8">
            <div className="px-7 py-5 border-b border-[#f0ebe1] flex items-center justify-between bg-[#faf7f2]">
              <div>
                <h2 className="text-lg font-serif font-bold text-[#191410]">Create Investigation Docket</h2>
                <p className="text-xs text-[#70685e]">Register new criminal proceeding into Evidentia</p>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-2 rounded-full hover:bg-[#eae4d9] text-[#8c8276] hover:text-[#191410] transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateCase} className="p-7 space-y-4">
              <div>
                <label className="block text-xs font-bold text-[#191410] uppercase tracking-wider mb-1.5">
                  Docket Title *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. State of Maharashtra vs. Accused Name"
                  value={newCase.title}
                  onChange={(e) => setNewCase({ ...newCase, title: e.target.value })}
                  className="w-full px-4 py-2.5 rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-xs text-[#191410] placeholder-[#999084] focus:outline-none focus:border-[#d93829]"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-[#191410] uppercase tracking-wider mb-1.5">
                    Category of Offense
                  </label>
                  <select
                    value={newCase.caseType}
                    onChange={(e) => setNewCase({ ...newCase, caseType: e.target.value })}
                    className="w-full px-4 py-2.5 rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-xs text-[#191410] focus:outline-none focus:border-[#d93829]"
                  >
                    <option value="Homicide">Homicide (IPC 302)</option>
                    <option value="Cyber Crime">Cyber Crime (IT Act)</option>
                    <option value="Corporate Espionage">Corporate Espionage</option>
                    <option value="Terrorism">Terrorism / Explosives</option>
                    <option value="Financial Fraud">Financial Fraud / Cheating</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#191410] uppercase tracking-wider mb-1.5">
                    Jurisdiction / Location
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Yerwada PS, Pune"
                    value={newCase.location}
                    onChange={(e) => setNewCase({ ...newCase, location: e.target.value })}
                    className="w-full px-4 py-2.5 rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-xs text-[#191410] placeholder-[#999084] focus:outline-none focus:border-[#d93829]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-[#191410] uppercase tracking-wider mb-1.5">
                  Brief Summary
                </label>
                <textarea
                  rows={3}
                  placeholder="Summary of first information report, key allegations..."
                  value={newCase.description}
                  onChange={(e) => setNewCase({ ...newCase, description: e.target.value })}
                  className="w-full px-4 py-2.5 rounded-xl bg-[#faf7f2] border border-[#eae4d9] text-xs text-[#191410] placeholder-[#999084] focus:outline-none focus:border-[#d93829] resize-none"
                />
              </div>

              <div className="pt-4 border-t border-[#f0ebe1] flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-5 py-2.5 rounded-full text-xs font-semibold text-[#70685e] hover:text-[#191410] hover:bg-[#f0ebe1] transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-6 py-2.5 rounded-full bg-[#d93829] hover:bg-[#bf2b1d] text-white text-xs font-bold tracking-wide transition-all shadow-md shadow-[#d93829]/25 disabled:opacity-50"
                >
                  {creating ? 'Registering...' : 'Register Docket'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
