import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Radio,
  Landmark,
  PhoneCall,
  Clock,
  ArrowRight,
  TrendingUp,
  AlertTriangle,
  Upload,
  FileSpreadsheet,
  Search,
  CheckCircle2,
  XCircle,
  ExternalLink,
  ChevronRight,
  ShieldAlert,
  Zap,
  RefreshCw,
  Sliders,
  DollarSign,
  FileText,
  Layers,
  Activity,
  MapPin,
  Calendar,
  CreditCard,
  User,
  HelpCircle,
  Network,
  Crosshair,
  Car,
  Plus,
  Trash2,
  Filter,
  ShieldCheck,
  Eye,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Check
} from 'lucide-react';
import {
  telecomFinancialService,
  caseService,
  watchlistService,
  WatchlistEntry,
  LiveNetworkData,
  LiveNetworkNode,
  LiveNetworkEdge,
  jobService
} from '../../services';
import {
  CDRAnalyticsOverview,
  MoneyFlowAnalysis,
  CDRRecord,
  BankTransaction,
  CoLocationEvent,
  CommonContact,
  ShortLivedNumber,
  ImpossibleTravelEvent,
  Case
} from '../../types';

export function CDRFinancialAnalytics() {
  const { caseId } = useParams<{ caseId: string }>();
  const [currentCase, setCurrentCase] = useState<Case | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Active top-level tab
  const [activeTab, setActiveTab] = useState<'network' | 'watchlists' | 'telecom' | 'financial'>('network');

  // Telecom Sub-tabs
  const [telecomTab, setTelecomTab] = useState<'colocation' | 'common_contacts' | 'burners' | 'impossible_travel' | 'ledger'>('colocation');

  // Financial Sub-tabs
  const [financialTab, setFinancialTab] = useState<'flow' | 'alerts' | 'ledger'>('flow');

  // Analytics Data
  const [cdrOverview, setCdrOverview] = useState<CDRAnalyticsOverview | null>(null);
  const [moneyFlow, setMoneyFlow] = useState<MoneyFlowAnalysis | null>(null);
  const [cdrRecords, setCdrRecords] = useState<CDRRecord[]>([]);
  const [bankTxns, setBankTxns] = useState<BankTransaction[]>([]);

  // Config parameters
  const [coLocationWindow, setCoLocationWindow] = useState<number>(15);
  const [cdrSearch, setCdrSearch] = useState<string>('');
  const [bankSearch, setBankSearch] = useState<string>('');

  // Live Correlated Network State
  const [liveNetwork, setLiveNetwork] = useState<LiveNetworkData | null>(null);
  const [networkLoading, setNetworkLoading] = useState<boolean>(false);
  const [netMode, setNetMode] = useState<'all' | 'calls' | 'transfers'>('all');
  const [netSearch, setNetSearch] = useState<string>('');
  const [netMinAmount, setNetMinAmount] = useState<number>(0);
  const [selectedNode, setSelectedNode] = useState<LiveNetworkNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<LiveNetworkEdge | null>(null);
  const [zoomScale, setZoomScale] = useState<number>(1.0);

  // Watchlists State
  const [watchlists, setWatchlists] = useState<WatchlistEntry[]>([]);
  const [watchlistMatches, setWatchlistMatches] = useState<any[]>([]);
  const [watchlistFilterType, setWatchlistFilterType] = useState<string>('all');
  const [watchlistModalOpen, setWatchlistModalOpen] = useState<boolean>(false);
  const [newWatchlist, setNewWatchlist] = useState({
    entity_type: 'phone',
    entity_value: '',
    label: '',
    priority: 'critical',
    notes: '',
    is_case_specific: false
  });

  // Automated Pipeline Scan State
  const [runningLiveScan, setRunningLiveScan] = useState<boolean>(false);
  const [scanMessage, setScanMessage] = useState<string | null>(null);

  // Import Modals
  const [cdrModalOpen, setCdrModalOpen] = useState<boolean>(false);
  const [bankModalOpen, setBankModalOpen] = useState<boolean>(false);
  const [importing, setImporting] = useState<boolean>(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [bankAccHint, setBankAccHint] = useState<string>('');
  const [bankNameHint, setBankNameHint] = useState<string>('');

  const loadData = async () => {
    if (!caseId) return;
    try {
      setLoading(true);
      setError(null);
      const [caseData, cdrData, flowData, txnsData, netData, wlData, wlMatches] = await Promise.all([
        caseService.getCaseById(caseId),
        telecomFinancialService.getCDRAnalytics(caseId, coLocationWindow),
        telecomFinancialService.getMoneyFlowAnalysis(caseId),
        telecomFinancialService.getBankTransactions(caseId, { limit: 100 }),
        telecomFinancialService.getLiveNetwork(caseId, {
          mode: netMode,
          min_amount: netMinAmount,
          search_number: netSearch
        }),
        watchlistService.getWatchlists(),
        watchlistService.getWatchlistMatches(caseId)
      ]);

      if (caseData) setCurrentCase(caseData);
      if (cdrData) {
        setCdrOverview(cdrData);
        setCdrRecords(cdrData.records_sample || []);
      }
      if (flowData) setMoneyFlow(flowData);
      if (txnsData) setBankTxns(txnsData);
      if (netData) setLiveNetwork(netData);
      if (wlData) setWatchlists(wlData);
      if (wlMatches) setWatchlistMatches(wlMatches);
    } catch (err: any) {
      console.error('Failed to load telecom/financial analytics:', err);
      setError(err?.message || 'Failed to load telecom and financial analytics.');
    } finally {
      setLoading(false);
    }
  };

  const loadNetworkData = async () => {
    if (!caseId) return;
    try {
      setNetworkLoading(true);
      const netData = await telecomFinancialService.getLiveNetwork(caseId, {
        mode: netMode,
        min_amount: netMinAmount,
        search_number: netSearch
      });
      if (netData) setLiveNetwork(netData);
    } catch (err) {
      console.error('Failed to update live network:', err);
    } finally {
      setNetworkLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [caseId, coLocationWindow]);

  useEffect(() => {
    loadNetworkData();
  }, [netMode, netMinAmount, netSearch]);

  // Subscribe to real-time events for live updates
  useEffect(() => {
    if (!caseId) return;
    const unsubscribe = jobService.subscribeCaseEvents(caseId, (event: any) => {
      if (
        event?.event_type === 'cdr_financial_analyzed' ||
        event?.event_type === 'alert.created' ||
        event?.event_type === 'item.changed' ||
        event?.type === 'alert.created'
      ) {
        loadData();
      }
    });
    return () => {
      if (unsubscribe) unsubscribe();
    };
  }, [caseId]);

  const handleTriggerLiveScan = async () => {
    if (!caseId) return;
    try {
      setRunningLiveScan(true);
      setScanMessage(null);
      const res = await telecomFinancialService.runLiveAnalysis(caseId);
      setScanMessage(res?.message || 'Live forensic scan complete: co-location, common contacts, burner SIMs, money flow, and watchlists evaluated.');
      await loadData();
    } catch (err: any) {
      alert(`Live analysis scan failed: ${err?.message || 'Error executing automated scan.'}`);
    } finally {
      setRunningLiveScan(false);
    }
  };

  const handleImportCDR = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId || !selectedFile) return;
    try {
      setImporting(true);
      const formData = new FormData();
      formData.append('file', selectedFile);
      await telecomFinancialService.importCDRFile(caseId, formData);
      setCdrModalOpen(false);
      setSelectedFile(null);
      setScanMessage('CDR exhibit ingested. Automated co-location, common contact, burner SIM, and cross-case watchlist analysis executed.');
      await loadData();
    } catch (err: any) {
      alert(`CDR import failed: ${err?.message || 'Error parsing file.'}`);
    } finally {
      setImporting(false);
    }
  };

  const handleImportBank = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId || !selectedFile) return;
    try {
      setImporting(true);
      const formData = new FormData();
      formData.append('file', selectedFile);
      if (bankAccHint) formData.append('account_number', bankAccHint);
      if (bankNameHint) formData.append('bank_name', bankNameHint);
      await telecomFinancialService.importBankStatement(caseId, formData);
      setBankModalOpen(false);
      setSelectedFile(null);
      setScanMessage('Bank statement ingested. Automated structuring, layering, money flow, and cross-case watchlist analysis executed.');
      await loadData();
    } catch (err: any) {
      alert(`Bank statement import failed: ${err?.message || 'Error parsing statement.'}`);
    } finally {
      setImporting(false);
    }
  };

  const handleCreateWatchlist = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWatchlist.entity_value.trim() || !newWatchlist.label.trim()) return;
    try {
      await watchlistService.createWatchlist({
        entity_type: newWatchlist.entity_type,
        entity_value: newWatchlist.entity_value.trim(),
        label: newWatchlist.label.trim(),
        priority: newWatchlist.priority,
        notes: newWatchlist.notes.trim(),
        case_id: newWatchlist.is_case_specific && caseId ? Number(String(caseId).replace(/^C-/, '')) : undefined
      });
      setWatchlistModalOpen(false);
      setNewWatchlist({
        entity_type: 'phone',
        entity_value: '',
        label: '',
        priority: 'critical',
        notes: '',
        is_case_specific: false
      });
      // Trigger a live analysis to match the new watchlist across case files
      if (caseId) {
        await telecomFinancialService.runLiveAnalysis(caseId);
      }
      await loadData();
    } catch (err: any) {
      alert(`Failed to register watchlist target: ${err?.message || 'Unknown error'}`);
    }
  };

  const handleToggleWatchlistStatus = async (item: WatchlistEntry) => {
    try {
      await watchlistService.updateWatchlist(item.id, { is_active: !item.is_active });
      setWatchlists(prev => prev.map(w => w.id === item.id ? { ...w, is_active: !w.is_active } : w));
    } catch (err: any) {
      alert(`Failed to update watchlist status: ${err?.message || 'Unknown error'}`);
    }
  };

  const handleDeleteWatchlist = async (id: number) => {
    if (!confirm('Are you sure you want to remove this target from the investigative watchlist?')) return;
    try {
      await watchlistService.deleteWatchlist(id);
      setWatchlists(prev => prev.filter(w => w.id !== id));
      if (caseId) {
        await loadData();
      }
    } catch (err: any) {
      alert(`Failed to delete watchlist target: ${err?.message || 'Unknown error'}`);
    }
  };

  const openWatchlistModalWithEntity = (type: string, value: string, label: string) => {
    setNewWatchlist({
      entity_type: type,
      entity_value: value,
      label: label || `Target: ${value}`,
      priority: 'critical',
      notes: 'Added directly from Live Network Graph Inspector.',
      is_case_specific: false
    });
    setWatchlistModalOpen(true);
  };

  const filteredCdrRecords = cdrRecords.filter(r => {
    if (!cdrSearch.trim()) return true;
    const q = cdrSearch.toLowerCase();
    return (
      r.calling_number.toLowerCase().includes(q) ||
      (r.called_number || '').toLowerCase().includes(q) ||
      r.cell_id.toLowerCase().includes(q) ||
      (r.site_name || '').toLowerCase().includes(q)
    );
  });

  const filteredBankTxns = bankTxns.filter(t => {
    if (!bankSearch.trim()) return true;
    const q = bankSearch.toLowerCase();
    return (
      t.description.toLowerCase().includes(q) ||
      (t.reference_number || '').toLowerCase().includes(q) ||
      t.account_number.toLowerCase().includes(q) ||
      (t.counterparty_name || '').toLowerCase().includes(q) ||
      (t.counterparty_account || '').toLowerCase().includes(q)
    );
  });

  const filteredWatchlists = watchlists.filter(w => {
    if (watchlistFilterType === 'all') return true;
    return w.entity_type === watchlistFilterType;
  });

  const formatCurrency = (val?: number | null) => {
    if (val === undefined || val === null) return '-';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(val);
  };

  // Node Positions Calculation for the Interactive Correlated Network Canvas
  const networkLayout = useMemo(() => {
    const nodes = liveNetwork?.nodes || [];
    const positions = new Map<string, { x: number; y: number; node: LiveNetworkNode }>();
    if (nodes.length === 0) return { positions, width: 920, height: 600 };

    const phones = nodes.filter(n => n.type === 'phone');
    const accounts = nodes.filter(n => n.type === 'account');
    const others = nodes.filter(n => n.type !== 'phone' && n.type !== 'account');

    const width = 920;
    const height = 600;
    const cy = height / 2;

    // Place phones in a left arc / column
    if (phones.length > 0) {
      const px = accounts.length > 0 ? 250 : width / 2;
      const radiusY = Math.min(230, 45 * Math.max(phones.length, 3));
      phones.forEach((node, i) => {
        const angle = phones.length === 1 ? 0 : ((i / (phones.length - 1 || 1)) - 0.5) * Math.PI * 0.9;
        const x = px + Math.cos(angle) * (accounts.length > 0 ? -120 : 0);
        const y = cy + Math.sin(angle) * radiusY;
        positions.set(node.id, { x: Math.max(90, Math.min(width - 90, x)), y: Math.max(70, Math.min(height - 70, y)), node });
      });
    }

    // Place accounts in a right arc / column
    if (accounts.length > 0) {
      const ax = phones.length > 0 ? 670 : width / 2;
      const radiusY = Math.min(230, 45 * Math.max(accounts.length, 3));
      accounts.forEach((node, i) => {
        const angle = accounts.length === 1 ? 0 : ((i / (accounts.length - 1 || 1)) - 0.5) * Math.PI * 0.9;
        const x = ax + Math.cos(angle) * (phones.length > 0 ? 120 : 0);
        const y = cy + Math.sin(angle) * radiusY;
        positions.set(node.id, { x: Math.max(90, Math.min(width - 90, x)), y: Math.max(70, Math.min(height - 70, y)), node });
      });
    }

    // Place others (persons/towers) in the center column
    if (others.length > 0) {
      others.forEach((node, i) => {
        const y = cy + (i - (others.length - 1) / 2) * 90;
        positions.set(node.id, { x: width / 2, y: Math.max(70, Math.min(height - 70, y)), node });
      });
    }

    return { positions, width, height };
  }, [liveNetwork?.nodes]);

  return (
    <div className="min-h-screen bg-[#faf7f2] p-6 lg:p-8 space-y-6 text-[#191410]">
      {/* Header & Intelligence Dossier Banner */}
      <div className="bg-white border border-[#eae4d9] rounded-2xl p-6 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="p-1.5 rounded-lg bg-[#d93829]/10 text-[#d93829]">
                <Radio className="w-5 h-5" />
              </span>
              <span className="text-xs font-bold uppercase tracking-wider text-[#d93829]">
                Forensic Analytics Suite
              </span>
            </div>
            <h1 className="text-2xl font-serif font-bold text-[#191410]">
              CDR & Financial Intelligence
            </h1>
            <p className="text-xs text-[#6e665d] mt-1 max-w-2xl leading-relaxed">
              Structured telecom tower-dump parsing, co-location discovery, common contacts, burner SIM identification,
              speed-based impossible travel, and bank statement money-flow modeling with automated cross-case watchlists.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={handleTriggerLiveScan}
              disabled={runningLiveScan}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold text-white bg-[#d93829] hover:bg-[#b82e21] shadow-xs transition-all cursor-pointer disabled:opacity-60"
            >
              <RefreshCw className={`w-4 h-4 ${runningLiveScan ? 'animate-spin' : ''}`} />
              <span>{runningLiveScan ? 'Running Live Scan...' : '⚡ Run Live Forensic Scan'}</span>
            </button>

            <button
              onClick={() => { setSelectedFile(null); setCdrModalOpen(true); }}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold text-[#191410] bg-[#faf7f2] hover:bg-[#f0ebe1] border border-[#eae4d9] transition-all cursor-pointer"
            >
              <FileSpreadsheet className="w-4 h-4 text-[#d93829]" />
              <span>Import CDR</span>
            </button>

            <button
              onClick={() => { setSelectedFile(null); setBankModalOpen(true); }}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold text-white bg-[#15803d] hover:bg-[#166534] shadow-xs transition-all cursor-pointer"
            >
              <Landmark className="w-4 h-4" />
              <span>Import Statement</span>
            </button>
          </div>
        </div>

        {/* Live Scan Notification Banner */}
        {scanMessage && (
          <div className="mt-4 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-900 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
              <span>{scanMessage}</span>
            </div>
            <button
              onClick={() => setScanMessage(null)}
              className="text-emerald-700 hover:text-emerald-900 text-xs font-bold"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Global Key Metrics Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3 mt-6 pt-5 border-t border-[#f0ebe1]">
          <div className="bg-[#faf7f2] rounded-xl p-3 border border-[#eae4d9]">
            <span className="text-[10px] font-bold text-[#6e665d] uppercase tracking-wider block">CDR Records</span>
            <span className="text-lg font-bold font-serif text-[#191410] mt-0.5 block">{cdrOverview?.total_records ?? 0}</span>
          </div>

          <div className="bg-rose-50/60 rounded-xl p-3 border border-rose-200">
            <span className="text-[10px] font-bold text-rose-800 uppercase tracking-wider block">Co-Locations</span>
            <span className="text-lg font-bold font-serif text-rose-900 mt-0.5 block">{cdrOverview?.co_location_events?.length ?? 0}</span>
          </div>

          <div className="bg-purple-50/60 rounded-xl p-3 border border-purple-200">
            <span className="text-[10px] font-bold text-purple-800 uppercase tracking-wider block">Common Contacts</span>
            <span className="text-lg font-bold font-serif text-purple-900 mt-0.5 block">{cdrOverview?.common_contacts?.length ?? 0}</span>
          </div>

          <div className="bg-amber-50/60 rounded-xl p-3 border border-amber-200">
            <span className="text-[10px] font-bold text-amber-800 uppercase tracking-wider block">Burner SIMs</span>
            <span className="text-lg font-bold font-serif text-amber-900 mt-0.5 block">{cdrOverview?.short_lived_numbers?.length ?? 0}</span>
          </div>

          <div className="bg-red-50/60 rounded-xl p-3 border border-red-200">
            <span className="text-[10px] font-bold text-red-800 uppercase tracking-wider block">Impossible Travel</span>
            <span className="text-lg font-bold font-serif text-red-900 mt-0.5 block">{cdrOverview?.impossible_travel?.length ?? 0}</span>
          </div>

          <div className="bg-emerald-50/60 rounded-xl p-3 border border-emerald-200">
            <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider block">Financial Volume</span>
            <span className="text-lg font-bold font-serif text-emerald-900 mt-0.5 block">{formatCurrency(moneyFlow?.total_volume ?? 0)}</span>
          </div>

          <div className="bg-blue-50/60 rounded-xl p-3 border border-blue-200">
            <span className="text-[10px] font-bold text-blue-800 uppercase tracking-wider block">Flow Alerts</span>
            <span className="text-lg font-bold font-serif text-blue-900 mt-0.5 block">
              {(moneyFlow?.structuring_alerts?.length ?? 0) + (moneyFlow?.layering_alerts?.length ?? 0)}
            </span>
          </div>

          <div className="bg-crimson-50/70 bg-red-50 rounded-xl p-3 border border-red-300">
            <span className="text-[10px] font-bold text-red-800 uppercase tracking-wider block">Watchlist Hits</span>
            <span className="text-lg font-bold font-serif text-red-900 mt-0.5 block flex items-center gap-1.5">
              <Crosshair className="w-4 h-4 text-red-600 animate-pulse" />
              {watchlistMatches.length}
            </span>
          </div>
        </div>
      </div>

      {/* Main Mode Tabs */}
      <div className="flex items-center gap-2 border-b border-[#eae4d9] pb-2 overflow-x-auto">
        <button
          onClick={() => setActiveTab('network')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap ${
            activeTab === 'network'
              ? 'bg-[#191410] text-white shadow-xs'
              : 'text-[#6e665d] hover:bg-white hover:text-[#191410]'
          }`}
        >
          <Network className="w-4 h-4 text-amber-400" />
          <span>Live Correlated Network</span>
          <span className="bg-white/20 px-2 py-0.5 rounded-full text-[10px]">
            {liveNetwork?.nodes?.length ?? 0}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('watchlists')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap ${
            activeTab === 'watchlists'
              ? 'bg-[#191410] text-white shadow-xs'
              : 'text-[#6e665d] hover:bg-white hover:text-[#191410]'
          }`}
        >
          <Crosshair className="w-4 h-4 text-red-500" />
          <span>Target Watchlists & Alerts</span>
          <span className={`px-2 py-0.5 rounded-full text-[10px] ${watchlistMatches.length > 0 ? 'bg-red-500 text-white animate-pulse' : 'bg-white/20'}`}>
            {watchlistMatches.length} Hits
          </span>
        </button>

        <button
          onClick={() => setActiveTab('telecom')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap ${
            activeTab === 'telecom'
              ? 'bg-[#191410] text-white shadow-xs'
              : 'text-[#6e665d] hover:bg-white hover:text-[#191410]'
          }`}
        >
          <Radio className="w-4 h-4" />
          <span>Telecommunications & Tower Dumps</span>
          <span className="bg-white/20 px-2 py-0.5 rounded-full text-[10px]">
            {cdrOverview?.total_records ?? 0}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('financial')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap ${
            activeTab === 'financial'
              ? 'bg-[#191410] text-white shadow-xs'
              : 'text-[#6e665d] hover:bg-white hover:text-[#191410]'
          }`}
        >
          <Landmark className="w-4 h-4" />
          <span>Forensic Banking & Money-Flow</span>
          <span className="bg-white/20 px-2 py-0.5 rounded-full text-[10px]">
            {bankTxns.length}
          </span>
        </button>
      </div>

      {/* ===================================================================== */}
      {/* SECTION 0: LIVE CORRELATED NETWORK (CALLS + TRANSFERS + WATCHLISTS) */}
      {/* ===================================================================== */}
      {activeTab === 'network' && (
        <div className="space-y-4">
          {/* Network Filter Bar */}
          <div className="bg-white border border-[#eae4d9] rounded-2xl p-4 shadow-xs flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold text-[#191410] mr-1 flex items-center gap-1.5">
                <Filter className="w-3.5 h-3.5 text-[#6e665d]" />
                Mode:
              </span>
              {[
                { id: 'all', label: 'All Interactions', icon: Network },
                { id: 'calls', label: 'Calls Only', icon: PhoneCall },
                { id: 'transfers', label: 'Transfers Only', icon: Landmark }
              ].map(m => (
                <button
                  key={m.id}
                  onClick={() => setNetMode(m.id as any)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    netMode === m.id
                      ? 'bg-[#191410] text-white shadow-xs'
                      : 'bg-[#faf7f2] text-[#6e665d] hover:bg-[#f0ebe1]'
                  }`}
                >
                  <m.icon className="w-3.5 h-3.5" />
                  <span>{m.label}</span>
                </button>
              ))}
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {/* Search target input */}
              <div className="relative min-w-[200px]">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#6e665d]" />
                <input
                  type="text"
                  placeholder="Filter phone / account..."
                  value={netSearch}
                  onChange={e => setNetSearch(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-[#eae4d9] text-xs bg-[#faf7f2] focus:outline-none focus:ring-1 focus:ring-[#d93829]"
                />
              </div>

              {/* Min Amount Filter */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-[#6e665d] font-semibold">Min ₹:</span>
                <select
                  value={netMinAmount}
                  onChange={e => setNetMinAmount(Number(e.target.value))}
                  className="bg-[#faf7f2] border border-[#eae4d9] rounded-lg px-2.5 py-1 text-xs font-medium focus:outline-none focus:ring-1 focus:ring-[#d93829]"
                >
                  <option value={0}>All Amounts (₹0+)</option>
                  <option value={50000}>≥ ₹50,000</option>
                  <option value={200000}>≥ ₹2,00,000</option>
                  <option value={500000}>≥ ₹5,00,000</option>
                  <option value={1000000}>≥ ₹10,00,000</option>
                </select>
              </div>

              {/* Zoom Controls */}
              <div className="flex items-center gap-1 bg-[#faf7f2] border border-[#eae4d9] rounded-lg p-1">
                <button
                  onClick={() => setZoomScale(z => Math.max(0.6, z - 0.15))}
                  className="p-1 text-[#6e665d] hover:text-[#191410] rounded"
                  title="Zoom Out"
                >
                  <ZoomOut className="w-3.5 h-3.5" />
                </button>
                <span className="text-[10px] font-mono px-1 font-bold text-[#6e665d]">{Math.round(zoomScale * 100)}%</span>
                <button
                  onClick={() => setZoomScale(z => Math.min(2.0, z + 0.15))}
                  className="p-1 text-[#6e665d] hover:text-[#191410] rounded"
                  title="Zoom In"
                >
                  <ZoomIn className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setZoomScale(1.0)}
                  className="p-1 text-[#6e665d] hover:text-[#191410] rounded ml-0.5 border-l border-[#eae4d9]"
                  title="Reset Zoom"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>

          {/* Network Canvas & Interactive Inspector Split */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* SVG Graph View (Spans 2 columns) */}
            <div className="lg:col-span-2 bg-white border border-[#eae4d9] rounded-2xl p-4 shadow-xs relative overflow-hidden flex flex-col justify-between min-h-[580px]">
              {/* Overlay Badges */}
              <div className="absolute top-4 left-4 z-10 flex flex-wrap items-center gap-2">
                <span className="bg-white/95 backdrop-blur-xs text-[#191410] text-[11px] font-semibold px-2.5 py-1 rounded-lg border border-[#eae4d9] shadow-xs flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-amber-600" />
                  <span>Nodes: {liveNetwork?.nodes?.length ?? 0}</span>
                </span>
                <span className="bg-white/95 backdrop-blur-xs text-[#191410] text-[11px] font-semibold px-2.5 py-1 rounded-lg border border-[#eae4d9] shadow-xs flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-indigo-600 inline-block" />
                  <span>Calls: {liveNetwork?.total_calls ?? 0}</span>
                </span>
                <span className="bg-white/95 backdrop-blur-xs text-[#191410] text-[11px] font-semibold px-2.5 py-1 rounded-lg border border-[#eae4d9] shadow-xs flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-600 inline-block" />
                  <span>Transfers: {formatCurrency(liveNetwork?.total_transfers_amount ?? 0)}</span>
                </span>
                {liveNetwork && liveNetwork.watchlist_matches_in_network > 0 && (
                  <span className="bg-red-50 text-red-800 text-[11px] font-bold px-2.5 py-1 rounded-lg border border-red-200 shadow-xs flex items-center gap-1.5 animate-pulse">
                    <Crosshair className="w-3.5 h-3.5 text-red-600" />
                    <span>Watchlist Hits: {liveNetwork.watchlist_matches_in_network}</span>
                  </span>
                )}
              </div>

              {/* Instructions Pill */}
              <div className="absolute bottom-4 left-4 z-10 text-[10px] text-[#6e665d] bg-white/95 px-3 py-1.5 rounded-lg border border-[#eae4d9] shadow-xs flex items-center gap-2">
                <span>💡 Click any node or link to view exact judicial citations and evidence line items.</span>
              </div>

              {/* SVG Canvas */}
              {(!liveNetwork?.nodes || liveNetwork.nodes.length === 0) ? (
                <div className="flex flex-col items-center justify-center h-[520px] text-[#6e665d] space-y-3">
                  <Network className="w-12 h-12 text-[#6e665d]/50 animate-pulse" />
                  <p className="text-sm font-semibold text-[#191410]">No Network Entities Extracted Yet</p>
                  <p className="text-xs text-[#6e665d] max-w-sm text-center">
                    Import a CDR dump or bank statement to automatically model communication links and money flow routes.
                  </p>
                  <button
                    onClick={handleTriggerLiveScan}
                    className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-[#d93829] hover:bg-[#b82e21] shadow-xs cursor-pointer"
                  >
                    Run Live Scan Now
                  </button>
                </div>
              ) : (
                <div className="w-full h-[520px] overflow-hidden flex items-center justify-center">
                  <svg
                    viewBox={`0 0 ${networkLayout.width} ${networkLayout.height}`}
                    className="w-full h-full select-none"
                    style={{ transform: `scale(${zoomScale})`, transformOrigin: 'center center', transition: 'transform 0.2s ease-out' }}
                  >
                    <defs>
                      <marker
                        id="arrow-emerald"
                        viewBox="0 0 10 10"
                        refX="22"
                        refY="5"
                        markerWidth="6"
                        markerHeight="6"
                        orient="auto-start-reverse"
                      >
                        <path d="M 0 0 L 10 5 L 0 10 z" fill="#10b981" />
                      </marker>
                      <marker
                        id="arrow-indigo"
                        viewBox="0 0 10 10"
                        refX="22"
                        refY="5"
                        markerWidth="6"
                        markerHeight="6"
                        orient="auto-start-reverse"
                      >
                        <path d="M 0 0 L 10 5 L 0 10 z" fill="#6366f1" />
                      </marker>
                      <filter id="glow-red" x="-20%" y="-20%" width="140%" height="140%">
                        <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#ef4444" floodOpacity="0.8" />
                      </filter>
                    </defs>

                    {/* Background grid dots */}
                    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                      <circle cx="20" cy="20" r="0.75" fill="#eae4d9" />
                    </pattern>
                    <rect width="100%" height="100%" fill="url(#grid)" />

                    {/* Edges */}
                    {liveNetwork.edges.map(edge => {
                      const sp = networkLayout.positions.get(edge.source);
                      const tp = networkLayout.positions.get(edge.target);
                      if (!sp || !tp) return null;

                      const isSelected = selectedEdge?.id === edge.id;
                      const isCall = edge.type === 'call';
                      const strokeColor = isCall ? '#6366f1' : '#10b981';
                      const mx = (sp.x + tp.x) / 2;
                      const my = (sp.y + tp.y) / 2;
                      const dx = tp.x - sp.x;
                      const dy = tp.y - sp.y;
                      const len = Math.hypot(dx, dy) || 1;
                      const curviness = 22;
                      const qx = mx - (dy / len) * curviness;
                      const qy = my + (dx / len) * curviness;

                      return (
                        <g key={edge.id} className="cursor-pointer group" onClick={() => { setSelectedEdge(edge); setSelectedNode(null); }}>
                          {/* Hitbox */}
                          <path
                            d={`M ${sp.x} ${sp.y} Q ${qx} ${qy} ${tp.x} ${tp.y}`}
                            stroke="transparent"
                            strokeWidth="20"
                            fill="none"
                          />
                          {/* Visible Edge */}
                          <path
                            d={`M ${sp.x} ${sp.y} Q ${qx} ${qy} ${tp.x} ${tp.y}`}
                            stroke={strokeColor}
                            strokeWidth={isSelected ? 4 : isCall ? 2 : 2.5}
                            strokeDasharray={isCall && edge.count < 3 ? '4,4' : undefined}
                            strokeOpacity={isSelected ? 1.0 : 0.65}
                            markerEnd={isCall ? 'url(#arrow-indigo)' : 'url(#arrow-emerald)'}
                            fill="none"
                            className="transition-all group-hover:stroke-amber-500 group-hover:stroke-opacity-100"
                          />
                          {/* Midpoint Pill */}
                          <g transform={`translate(${qx}, ${qy})`}>
                            <rect
                              x="-26"
                              y="-10"
                              width="52"
                              height="20"
                              rx="10"
                              fill="#ffffff"
                              stroke={isSelected ? '#d93829' : strokeColor}
                              strokeWidth="1.2"
                            />
                            <text
                              textAnchor="middle"
                              dominantBaseline="central"
                              fill="#191410"
                              fontSize="9"
                              fontWeight="bold"
                              fontFamily="monospace"
                            >
                              {isCall ? `${edge.count} calls` : edge.total_amount >= 100000 ? `₹${(edge.total_amount / 100000).toFixed(1)}L` : `₹${Math.round(edge.total_amount / 1000)}k`}
                            </text>
                          </g>
                        </g>
                      );
                    })}

                    {/* Nodes */}
                    {Array.from(networkLayout.positions.values()).map(({ x, y, node }) => {
                      const isSelected = selectedNode?.id === node.id;
                      const isPhone = node.type === 'phone';
                      const isAccount = node.type === 'account';
                      const isHit = node.is_watchlist_match;

                      return (
                        <g
                          key={node.id}
                          transform={`translate(${x}, ${y})`}
                          className="cursor-pointer group"
                          onClick={() => { setSelectedNode(node); setSelectedEdge(null); }}
                        >
                          {/* Watchlist Pulsing Halo */}
                          {isHit && (
                            <>
                              <circle r="32" stroke="#ef4444" strokeWidth="2" fill="none" opacity="0.4" className="animate-ping" />
                              <circle r="26" stroke="#ef4444" strokeWidth="2" fill="none" opacity="0.8" filter="url(#glow-red)" />
                            </>
                          )}

                          {/* Selected Ring */}
                          {isSelected && (
                            <circle r="24" stroke="#d93829" strokeWidth="3" fill="none" />
                          )}

                          {/* Main Node Circle */}
                          <circle
                            r="18"
                            fill={isHit ? '#fee2e2' : isPhone ? '#e0e7ff' : isAccount ? '#d1fae5' : '#f5f5f4'}
                            stroke={isHit ? '#dc2626' : isPhone ? '#4f46e5' : isAccount ? '#059669' : '#78716c'}
                            strokeWidth="2.5"
                            className="transition-all group-hover:scale-110"
                          />

                          {/* Inside Glyph */}
                          <text
                            textAnchor="middle"
                            dominantBaseline="central"
                            fontSize="10"
                            fill="#191410"
                            fontWeight="bold"
                          >
                            {isPhone ? '📞' : isAccount ? '🏦' : '👤'}
                          </text>

                          {/* Watchlist Pill on Top */}
                          {isHit && (
                            <g transform="translate(0, -28)">
                              <rect x="-35" y="-8" width="70" height="16" rx="8" fill="#dc2626" />
                              <text textAnchor="middle" dominantBaseline="central" fill="#ffffff" fontSize="8" fontWeight="bold">
                                🎯 TARGET HIT
                              </text>
                            </g>
                          )}

                          {/* Primary Label */}
                          <text
                            y="28"
                            textAnchor="middle"
                            fill="#191410"
                            fontSize="10.5"
                            fontWeight="bold"
                            fontFamily="monospace"
                            className="pointer-events-none drop-shadow"
                          >
                            {node.id}
                          </text>

                          {/* Secondary Alias */}
                          {node.label && (
                            <text
                              y="41"
                              textAnchor="middle"
                              fill="#6e665d"
                              fontSize="8.5"
                              className="pointer-events-none drop-shadow"
                            >
                              {node.label.length > 22 ? `${node.label.substring(0, 20)}...` : node.label}
                            </text>
                          )}
                        </g>
                      );
                    })}
                  </svg>
                </div>
              )}
            </div>

            {/* Inspector Panel (Spans 1 column) */}
            <div className="bg-white border border-[#eae4d9] rounded-2xl p-5 shadow-xs flex flex-col justify-between space-y-4">
              <div>
                <div className="flex items-center justify-between pb-3 border-b border-[#f0ebe1]">
                  <div className="flex items-center gap-2">
                    <span className="p-1.5 rounded-lg bg-[#faf7f2] text-[#191410] border border-[#eae4d9]">
                      <Eye className="w-4 h-4 text-[#d93829]" />
                    </span>
                    <h3 className="text-sm font-serif font-bold text-[#191410]">Inspector & Judicial Citations</h3>
                  </div>
                  {(selectedNode || selectedEdge) && (
                    <button
                      onClick={() => { setSelectedNode(null); setSelectedEdge(null); }}
                      className="text-xs text-[#6e665d] hover:text-[#191410]"
                    >
                      Clear
                    </button>
                  )}
                </div>

                {/* Node Inspector View */}
                {selectedNode && (
                  <div className="mt-4 space-y-4">
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-[#6e665d]">
                          {selectedNode.type === 'phone' ? '📱 Cellular Handset / MSISDN' : '🏦 Banking Ledger Node'}
                        </span>
                        {selectedNode.is_watchlist_match ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-100 text-red-800 border border-red-300 flex items-center gap-1">
                            <Crosshair className="w-3 h-3 text-red-600 animate-pulse" />
                            CRITICAL WATCHLIST
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-gray-100 text-gray-700">
                            Unmonitored
                          </span>
                        )}
                      </div>
                      <p className="text-sm font-mono font-bold text-[#191410]">{selectedNode.id}</p>
                      <p className="text-xs text-[#6e665d]">{selectedNode.label || 'No known alias registered'}</p>
                    </div>

                    {/* Node Stats */}
                    <div className="grid grid-cols-3 gap-2 py-2">
                      <div className="bg-[#faf7f2] p-2.5 rounded-xl border border-[#eae4d9] text-center">
                        <span className="text-[9px] font-bold uppercase text-[#6e665d] block">Links</span>
                        <span className="text-sm font-bold font-serif text-[#191410]">{selectedNode.degree}</span>
                      </div>
                      <div className="bg-[#faf7f2] p-2.5 rounded-xl border border-[#eae4d9] text-center">
                        <span className="text-[9px] font-bold uppercase text-[#6e665d] block">Calls</span>
                        <span className="text-sm font-bold font-serif text-indigo-700">{selectedNode.total_calls}</span>
                      </div>
                      <div className="bg-[#faf7f2] p-2.5 rounded-xl border border-[#eae4d9] text-center">
                        <span className="text-[9px] font-bold uppercase text-[#6e665d] block">Volume</span>
                        <span className="text-xs font-bold font-serif text-emerald-800 truncate block">
                          {selectedNode.total_volume > 0 ? formatCurrency(selectedNode.total_volume) : '-'}
                        </span>
                      </div>
                    </div>

                    {/* Quick Watchlist Action */}
                    {!selectedNode.is_watchlist_match ? (
                      <button
                        onClick={() => openWatchlistModalWithEntity(selectedNode.type, selectedNode.id, selectedNode.label)}
                        className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-xs font-bold text-white bg-[#d93829] hover:bg-[#b82e21] shadow-xs cursor-pointer transition-all"
                      >
                        <Crosshair className="w-4 h-4" />
                        <span>Add Node to Cross-Case Watchlist</span>
                      </button>
                    ) : (
                      <div className="bg-red-50 p-3 rounded-xl border border-red-200 text-xs text-red-900 space-y-1">
                        <p className="font-bold flex items-center gap-1.5">
                          <ShieldAlert className="w-4 h-4 text-red-700" />
                          Subject Under Active Cross-Case Surveillance
                        </p>
                        <p className="text-[11px] text-red-800 leading-relaxed">
                          This identifier automatically triggers judicial tamper alerts on all incoming exhibits across authorized police cases.
                        </p>
                      </div>
                    )}

                    {/* Direct Connections List */}
                    <div>
                      <span className="text-[10px] font-bold text-[#6e665d] uppercase tracking-wider block mb-2">
                        Direct Network Counterparties:
                      </span>
                      <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                        {liveNetwork?.edges
                          .filter(e => e.source === selectedNode.id || e.target === selectedNode.id)
                          .map((edge, idx) => {
                            const otherId = edge.source === selectedNode.id ? edge.target : edge.source;
                            return (
                              <div
                                key={idx}
                                onClick={() => setSelectedEdge(edge)}
                                className="bg-[#faf7f2] hover:bg-[#f0ebe1] p-2 rounded-xl border border-[#eae4d9] text-xs flex items-center justify-between cursor-pointer transition-all"
                              >
                                <span className="font-mono font-bold text-[#191410] truncate max-w-[150px]">{otherId}</span>
                                <span className="text-[10px] font-semibold text-[#6e665d]">
                                  {edge.type === 'call' ? `${edge.count} calls` : formatCurrency(edge.total_amount)}
                                </span>
                              </div>
                            );
                          })}
                      </div>
                    </div>
                  </div>
                )}

                {/* Edge Inspector View */}
                {selectedEdge && (
                  <div className="mt-4 space-y-4">
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-[#6e665d]">
                          {selectedEdge.type === 'call' ? '📞 Telecom Interaction Bridge' : '🏦 Money Flow Transfer Edge'}
                        </span>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${selectedEdge.type === 'call' ? 'bg-indigo-100 text-indigo-800' : 'bg-emerald-100 text-emerald-800'}`}>
                          {selectedEdge.type === 'call' ? `${selectedEdge.count} Events` : formatCurrency(selectedEdge.total_amount)}
                        </span>
                      </div>
                      <p className="text-xs font-mono font-bold text-[#191410] truncate">{selectedEdge.source}</p>
                      <p className="text-[10px] text-center font-bold text-[#6e665d]">⬇ connected to ⬇</p>
                      <p className="text-xs font-mono font-bold text-[#191410] truncate">{selectedEdge.target}</p>
                    </div>

                    {/* Modes */}
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {selectedEdge.modes.map((mode, mIdx) => (
                        <span key={mIdx} className="bg-[#faf7f2] text-[#191410] text-[10px] font-bold px-2 py-0.5 rounded border border-[#eae4d9]">
                          {mode}
                        </span>
                      ))}
                    </div>

                    {/* Exact Judicial Exhibit Citations */}
                    <div>
                      <span className="text-[10px] font-bold text-[#6e665d] uppercase tracking-wider block mb-1">
                        Section 65B Line Citations:
                      </span>
                      <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
                        {selectedEdge.linked_rows.map((row, rIdx) => (
                          <div key={rIdx} className="bg-[#faf7f2] p-2.5 rounded-xl border border-[#eae4d9] text-xs space-y-1">
                            <div className="flex items-center justify-between">
                              <span className="font-mono font-bold text-[#d93829] text-[10px]">Row #{row.row_number}</span>
                              <span className="text-[10px] text-[#6e665d]">{row.timestamp || row.date || 'Timestamp logged'}</span>
                            </div>
                            <p className="text-[11px] text-[#191410] font-medium leading-tight">
                              {row.description || (row.tower ? `Cell Tower CGI: ${row.tower}` : `${row.mode} transaction`)}
                            </p>
                            {row.amount && (
                              <p className="text-[11px] font-bold text-emerald-800">{formatCurrency(row.amount)}</p>
                            )}
                            <p className="text-[9px] text-[#6e665d] truncate italic" title={row.source_file}>
                              Exhibit: {row.source_file}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Default Empty Inspector View */}
                {!selectedNode && !selectedEdge && (
                  <div className="py-16 text-center space-y-2">
                    <Crosshair className="w-8 h-8 text-[#6e665d] mx-auto opacity-40" />
                    <p className="text-xs font-bold text-[#191410]">Select a Node or Edge</p>
                    <p className="text-[11px] text-[#6e665d] max-w-xs mx-auto leading-relaxed">
                      Click any caller, account, or transfer edge on the canvas to inspect its degree, counterparty linkages, and raw exhibit row citations.
                    </p>
                  </div>
                )}
              </div>

              {/* Judicial Trust Footer */}
              <div className="pt-3 border-t border-[#f0ebe1] flex items-center justify-between text-[10px] text-[#6e665d]">
                <span className="flex items-center gap-1 text-emerald-800 font-semibold">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Sec 65B Audit Compliant
                </span>
                <span>SHA-256 Verified Exhibits</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* SECTION 1: TARGET WATCHLISTS & CROSS-CASE MATCH ALERTS */}
      {/* ===================================================================== */}
      {activeTab === 'watchlists' && (
        <div className="space-y-6">
          {/* Watchlists Header Action Bar */}
          <div className="bg-white border border-[#eae4d9] rounded-2xl p-5 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="p-1.5 rounded-lg bg-red-100 text-red-800">
                  <Crosshair className="w-4 h-4" />
                </span>
                <h3 className="text-base font-serif font-bold text-[#191410]">
                  Cross-Case Investigative Watchlists
                </h3>
              </div>
              <p className="text-xs text-[#6e665d] max-w-2xl leading-relaxed">
                Register monitored phone numbers, bank accounts, vehicle license plates, or suspect names. Every incoming
                CDR dump, bank statement, or exhibit is cross-matched automatically in real-time, raising alerts strictly on new detections.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setWatchlistModalOpen(true)}
                className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold text-white bg-[#d93829] hover:bg-[#b82e21] shadow-xs cursor-pointer transition-all"
              >
                <Plus className="w-4 h-4" />
                <span>Register Monitored Target</span>
              </button>
            </div>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-2 overflow-x-auto">
            {[
              { id: 'all', label: 'All Targets', count: watchlists.length },
              { id: 'phone', label: 'Phone Numbers', count: watchlists.filter(w => w.entity_type === 'phone').length },
              { id: 'account', label: 'Bank Accounts', count: watchlists.filter(w => w.entity_type === 'account').length },
              { id: 'vehicle', label: 'Vehicle Plates', count: watchlists.filter(w => w.entity_type === 'vehicle').length },
              { id: 'person', label: 'Persons / Names', count: watchlists.filter(w => w.entity_type === 'person').length }
            ].map(f => (
              <button
                key={f.id}
                onClick={() => setWatchlistFilterType(f.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  watchlistFilterType === f.id
                    ? 'bg-[#191410] text-white shadow-xs'
                    : 'bg-white border border-[#eae4d9] text-[#6e665d] hover:bg-[#faf7f2]'
                }`}
              >
                <span>{f.label}</span>
                <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${watchlistFilterType === f.id ? 'bg-white/20 text-white' : 'bg-[#eae4d9] text-[#191410]'}`}>
                  {f.count}
                </span>
              </button>
            ))}
          </div>

          {/* Targets Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredWatchlists.map(item => (
              <div
                key={item.id}
                className={`bg-white border rounded-2xl p-5 shadow-xs transition-all space-y-3 ${
                  item.is_active ? 'border-[#eae4d9] hover:border-red-300' : 'border-gray-200 opacity-60'
                }`}
              >
                <div className="flex items-center justify-between pb-2 border-b border-[#f0ebe1]">
                  <div className="flex items-center gap-2">
                    <span className="p-1.5 rounded-lg bg-[#faf7f2] border border-[#eae4d9]">
                      {item.entity_type === 'phone' && <PhoneCall className="w-4 h-4 text-indigo-600" />}
                      {item.entity_type === 'account' && <Landmark className="w-4 h-4 text-emerald-600" />}
                      {item.entity_type === 'vehicle' && <Car className="w-4 h-4 text-amber-600" />}
                      {item.entity_type === 'person' && <User className="w-4 h-4 text-purple-600" />}
                    </span>
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-[#6e665d]">
                        {item.entity_type} target
                      </span>
                      <h4 className="text-xs font-bold text-[#191410] truncate max-w-[160px]">{item.label}</h4>
                    </div>
                  </div>

                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                    item.priority === 'critical' ? 'bg-red-100 text-red-800' : item.priority === 'high' ? 'bg-amber-100 text-amber-800' : 'bg-blue-100 text-blue-800'
                  }`}>
                    {item.priority}
                  </span>
                </div>

                <div>
                  <p className="text-sm font-mono font-bold text-[#191410]">{item.entity_value}</p>
                  {item.notes && (
                    <p className="text-xs text-[#6e665d] mt-1 line-clamp-2 leading-relaxed">{item.notes}</p>
                  )}
                </div>

                <div className="bg-[#faf7f2] p-2.5 rounded-xl border border-[#eae4d9] flex items-center justify-between text-xs">
                  <div>
                    <span className="text-[10px] text-[#6e665d] block">Cross-Case Matches:</span>
                    <span className="font-bold font-serif text-red-800">{item.match_count} detections</span>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-[#6e665d] block">Scope:</span>
                    <span className="font-semibold text-[#191410] text-[11px]">
                      {item.case_id ? `Case #${item.case_id}` : 'Global (All Cases)'}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-[#f0ebe1]">
                  <button
                    onClick={() => handleToggleWatchlistStatus(item)}
                    className="text-xs font-semibold text-[#6e665d] hover:text-[#191410] cursor-pointer"
                  >
                    {item.is_active ? '⏸ Pause Surveillance' : '▶ Activate Target'}
                  </button>

                  <button
                    onClick={() => handleDeleteWatchlist(item.id)}
                    className="p-1.5 rounded-lg text-rose-600 hover:bg-rose-50 cursor-pointer"
                    title="Delete target"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Cross-Case Real-Time Match Alerts Feed */}
          <div className="bg-white border border-[#eae4d9] rounded-2xl p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#f0ebe1]">
              <div className="flex items-center gap-2">
                <span className="p-1.5 rounded-lg bg-red-100 text-red-800">
                  <ShieldAlert className="w-4 h-4" />
                </span>
                <div>
                  <h3 className="text-sm font-serif font-bold text-[#191410]">Live Watchlist Match Alert Feed</h3>
                  <span className="text-[11px] text-[#6e665d]">
                    Alerts automatically generated on ingestion of CDR pings, bank statement transactions, and suspect filings.
                  </span>
                </div>
              </div>
              <span className="text-xs font-bold text-red-700 bg-red-50 px-2.5 py-1 rounded-lg border border-red-200">
                {watchlistMatches.length} Critical Alerts
              </span>
            </div>

            {watchlistMatches.length === 0 ? (
              <div className="py-12 text-center text-[#6e665d] space-y-2">
                <Check className="w-8 h-8 mx-auto text-emerald-600 opacity-80" />
                <p className="text-xs font-bold text-[#191410]">No Watchlist Violations Detected</p>
                <p className="text-[11px] text-[#6e665d] max-w-sm mx-auto">
                  None of the registered monitored numbers, accounts, or vehicle license plates appear in ingested exhibit files.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {watchlistMatches.map(alert => (
                  <div
                    key={alert.id}
                    className="bg-[#faf7f2] border border-red-200 rounded-xl p-4 shadow-xs hover:border-red-400 transition-all space-y-2"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
                      <div className="flex items-center gap-2">
                        <Crosshair className="w-4 h-4 text-red-600 animate-pulse shrink-0" />
                        <h4 className="text-xs font-bold text-[#191410]">{alert.title}</h4>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-100 text-red-800 border border-red-300 uppercase">
                          {alert.severity}
                        </span>
                        <span className="text-[10px] text-[#6e665d]">
                          {alert.created_at ? new Date(alert.created_at).toLocaleString() : 'Recent'}
                        </span>
                      </div>
                    </div>

                    <p className="text-xs text-[#191410] leading-relaxed bg-white p-2.5 rounded-lg border border-[#eae4d9]">
                      {alert.message}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* SECTION 2: TELECOM & TOWER DUMP ANALYTICS */}
      {/* ===================================================================== */}
      {activeTab === 'telecom' && (
        <div className="space-y-4">
          {/* Sub Navigation Bar */}
          <div className="bg-white border border-[#eae4d9] rounded-xl p-2 shadow-xs flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-1.5">
              {[
                { id: 'colocation', label: 'Co-Location Matrix', count: cdrOverview?.co_location_events?.length ?? 0, icon: MapPin },
                { id: 'common_contacts', label: 'Common Contacts', count: cdrOverview?.common_contacts?.length ?? 0, icon: PhoneCall },
                { id: 'burners', label: 'Burner SIMs', count: cdrOverview?.short_lived_numbers?.length ?? 0, icon: Zap },
                { id: 'impossible_travel', label: 'Impossible Travel', count: cdrOverview?.impossible_travel?.length ?? 0, icon: ShieldAlert },
                { id: 'ledger', label: 'Call Detail Ledger', count: cdrRecords.length, icon: FileText },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setTelecomTab(tab.id as any)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    telecomTab === tab.id
                      ? 'bg-[#d93829] text-white shadow-xs'
                      : 'bg-[#faf7f2] text-[#6e665d] hover:bg-[#f0ebe1]'
                  }`}
                >
                  <tab.icon className="w-3.5 h-3.5" />
                  <span>{tab.label}</span>
                  <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${telecomTab === tab.id ? 'bg-white/25 text-white' : 'bg-[#eae4d9] text-[#191410]'}`}>
                    {tab.count}
                  </span>
                </button>
              ))}
            </div>

            {telecomTab === 'colocation' && (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-[#6e665d] font-semibold text-[11px]">Window:</span>
                <select
                  value={coLocationWindow}
                  onChange={e => setCoLocationWindow(Number(e.target.value))}
                  className="bg-[#faf7f2] border border-[#eae4d9] rounded-lg px-2.5 py-1 text-xs font-medium focus:outline-none focus:ring-1 focus:ring-[#d93829]"
                >
                  <option value={5}>± 5 mins</option>
                  <option value={10}>± 10 mins</option>
                  <option value={15}>± 15 mins</option>
                  <option value={30}>± 30 mins</option>
                  <option value={60}>± 60 mins</option>
                </select>
              </div>
            )}
          </div>

          {/* 1A. CO-LOCATION VIEW */}
          {telecomTab === 'colocation' && (
            <div className="space-y-3">
              {(!cdrOverview?.co_location_events || cdrOverview.co_location_events.length === 0) ? (
                <div className="bg-white border border-[#eae4d9] rounded-2xl p-12 text-center shadow-xs">
                  <MapPin className="w-8 h-8 text-[#6e665d] mx-auto mb-2 opacity-50" />
                  <h3 className="text-sm font-bold text-[#191410]">No Co-Location Instances Detected</h3>
                  <p className="text-xs text-[#6e665d] mt-1 max-w-md mx-auto">
                    No two distinct handsets registered in the same cell tower sector within the selected ±{coLocationWindow} minutes window.
                  </p>
                </div>
              ) : (
                cdrOverview.co_location_events.map(event => (
                  <div
                    key={event.event_id}
                    className="bg-white border border-[#eae4d9] hover:border-rose-300 rounded-2xl p-5 shadow-xs transition-all"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[#f0ebe1]">
                      <div className="flex items-center gap-2">
                        <span className="p-1.5 rounded-lg bg-rose-50 text-rose-700">
                          <MapPin className="w-4 h-4" />
                        </span>
                        <div>
                          <span className="text-xs font-bold text-[#191410]">Tower: {event.site_name || event.cell_id}</span>
                          <span className="text-[10px] text-[#6e665d] block font-mono">CGI: {event.cell_id}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-300">
                          Δt {event.time_delta_minutes} mins
                        </span>
                        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
                          {event.confidence}% Confidence
                        </span>
                      </div>
                    </div>

                    {/* Dual Handset Comparison Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-3.5">
                      {/* Phone A */}
                      <div className="bg-[#faf7f2] p-3.5 rounded-xl border border-[#eae4d9] space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-[#6e665d]">Handset A</span>
                          <span className="text-[10px] font-mono bg-white px-2 py-0.5 rounded border border-[#eae4d9] text-[#191410] font-bold">
                            File Row #{event.phone_a.row_number}
                          </span>
                        </div>
                        <p className="text-xs font-bold font-mono text-[#191410]">{event.phone_a.number}</p>
                        <p className="text-[11px] text-[#6e665d]">
                          Timestamp: <span className="font-semibold text-[#191410]">{new Date(event.phone_a.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span> ({event.phone_a.duration_sec}s call)
                        </p>
                        <p className="text-[10px] text-[#6e665d] truncate">
                          Source Exhibit: <span className="italic">{event.phone_a.source_file}</span>
                        </p>
                      </div>

                      {/* Phone B */}
                      <div className="bg-rose-50/40 p-3.5 rounded-xl border border-rose-200 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-rose-800">Handset B</span>
                          <span className="text-[10px] font-mono bg-white px-2 py-0.5 rounded border border-rose-200 text-rose-900 font-bold">
                            File Row #{event.phone_b.row_number}
                          </span>
                        </div>
                        <p className="text-xs font-bold font-mono text-[#191410]">{event.phone_b.number}</p>
                        <p className="text-[11px] text-[#6e665d]">
                          Timestamp: <span className="font-semibold text-[#191410]">{new Date(event.phone_b.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span> ({event.phone_b.duration_sec}s call)
                        </p>
                        <p className="text-[10px] text-[#6e665d] truncate">
                          Source Exhibit: <span className="italic">{event.phone_b.source_file}</span>
                        </p>
                      </div>
                    </div>

                    <p className="text-xs text-[#191410] leading-relaxed bg-[#faf7f2]/80 p-2.5 rounded-xl border border-[#eae4d9]">
                      <span className="font-bold text-rose-700 mr-1.5">[Forensic Finding]:</span>
                      {event.reasoning}
                    </p>
                  </div>
                ))
              )}
            </div>
          )}

          {/* 1B. COMMON CONTACTS (BRIDGE NODES) */}
          {telecomTab === 'common_contacts' && (
            <div className="space-y-3">
              {(!cdrOverview?.common_contacts || cdrOverview.common_contacts.length === 0) ? (
                <div className="bg-white border border-[#eae4d9] rounded-2xl p-12 text-center shadow-xs">
                  <PhoneCall className="w-8 h-8 text-[#6e665d] mx-auto mb-2 opacity-50" />
                  <h3 className="text-sm font-bold text-[#191410]">No Shared Bridge Contacts Found</h3>
                  <p className="text-xs text-[#6e665d] mt-1 max-w-md mx-auto">
                    No external telephone number was dialed by or communicated with multiple suspect handsets.
                  </p>
                </div>
              ) : (
                cdrOverview.common_contacts.map((contact, idx) => (
                  <div
                    key={idx}
                    className="bg-white border border-[#eae4d9] hover:border-purple-300 rounded-2xl p-5 shadow-xs transition-all space-y-3"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[#f0ebe1]">
                      <div>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-purple-800 block">Bridge Node</span>
                        <span className="text-base font-mono font-bold text-[#191410]">{contact.contact_number}</span>
                      </div>
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-100 text-purple-800 border border-purple-300">
                        Connected to {contact.suspects_connected_count} Targets
                      </span>
                    </div>

                    <div>
                      <span className="text-[10px] font-bold text-[#6e665d] uppercase tracking-wider block mb-1">
                        Connected Suspect Handsets:
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {contact.suspects_connected.map((s, sIdx) => (
                          <span key={sIdx} className="bg-[#faf7f2] px-2.5 py-1 rounded-lg border border-[#eae4d9] text-xs font-mono font-semibold text-[#191410]">
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>

                    <p className="text-xs text-[#191410] leading-relaxed bg-purple-50/40 p-2.5 rounded-xl border border-purple-200">
                      {(contact as any).reasoning || `Intermediary bridge contact connecting ${contact.suspects_connected_count} suspect handsets across ${contact.total_calls} observed events.`}
                    </p>
                  </div>
                ))
              )}
            </div>
          )}

          {/* 1C. BURNER SIMS */}
          {telecomTab === 'burners' && (
            <div className="space-y-3">
              {(!cdrOverview?.short_lived_numbers || cdrOverview.short_lived_numbers.length === 0) ? (
                <div className="bg-white border border-[#eae4d9] rounded-2xl p-12 text-center shadow-xs">
                  <Zap className="w-8 h-8 text-[#6e665d] mx-auto mb-2 opacity-50" />
                  <h3 className="text-sm font-bold text-[#191410]">No Short-Lived Burner Numbers Found</h3>
                  <p className="text-xs text-[#6e665d] mt-1 max-w-md mx-auto">
                    All observed handsets show regular lifespan beyond the 48-hour burner SIM anomaly threshold.
                  </p>
                </div>
              ) : (
                cdrOverview.short_lived_numbers.map((sim, idx) => (
                  <div
                    key={idx}
                    className="bg-white border border-[#eae4d9] hover:border-amber-300 rounded-2xl p-5 shadow-xs transition-all space-y-3"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[#f0ebe1]">
                      <div className="flex items-center gap-2">
                        <span className="p-1.5 rounded-lg bg-amber-50 text-amber-700">
                          <Zap className="w-4 h-4" />
                        </span>
                        <div>
                          <span className="text-xs font-bold font-mono text-[#191410]">{sim.phone_number}</span>
                          <span className="text-[10px] text-[#6e665d] block">Total Tower Interactions: {sim.total_events}</span>
                        </div>
                      </div>

                      <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-900 border border-amber-300">
                        Active {sim.active_duration_hours.toFixed(1)} Hours
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-3 text-xs bg-[#faf7f2] p-3 rounded-xl border border-[#eae4d9]">
                      <div>
                        <span className="text-[10px] text-[#6e665d] block">First Seen Ping:</span>
                        <span className="font-semibold">{new Date(sim.first_seen).toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-[#6e665d] block">Last Seen Ping:</span>
                        <span className="font-semibold">{new Date(sim.last_seen).toLocaleString()}</span>
                      </div>
                    </div>

                    <p className="text-xs text-[#191410] leading-relaxed bg-amber-50/50 p-2.5 rounded-xl border border-amber-200">
                      {sim.reasoning}
                    </p>
                  </div>
                ))
              )}
            </div>
          )}

          {/* 1D. IMPOSSIBLE TRAVEL BREACHES */}
          {telecomTab === 'impossible_travel' && (
            <div className="space-y-3">
              {(!cdrOverview?.impossible_travel || cdrOverview.impossible_travel.length === 0) ? (
                <div className="bg-white border border-[#eae4d9] rounded-2xl p-12 text-center shadow-xs">
                  <ShieldAlert className="w-8 h-8 text-[#6e665d] mx-auto mb-2 opacity-50" />
                  <h3 className="text-sm font-bold text-[#191410]">Zero Velocity Anomalies</h3>
                  <p className="text-xs text-[#6e665d] mt-1 max-w-md mx-auto">
                    All tower jumps between consecutive pings conform to standard terrestrial transit speeds (under 160 km/h).
                  </p>
                </div>
              ) : (
                cdrOverview.impossible_travel.map((travel, idx) => (
                  <div
                    key={idx}
                    className="bg-white border border-red-300 rounded-2xl p-5 shadow-xs transition-all space-y-3"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-red-100">
                      <div>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-red-800 block">Impossible Speed Violation</span>
                        <span className="text-sm font-mono font-bold text-[#191410]">{travel.phone_number}</span>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-900 border border-red-300">
                          {travel.calculated_speed_kmh} km/h Required
                        </span>
                        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-800 border border-rose-200">
                          {travel.distance_km} km in {travel.time_delta_minutes}m
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div className="bg-[#faf7f2] p-3 rounded-xl border border-[#eae4d9] space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-[#6e665d]">Origin Tower Event</span>
                          <span className="font-mono font-bold text-[#d93829] text-[10px]">Row #{travel.event_a.row_number}</span>
                        </div>
                        <p className="text-xs font-bold text-[#191410]">{travel.event_a.site_name || travel.event_a.cell_id}</p>
                        <p className="text-[10px] text-[#6e665d]">{new Date(travel.event_a.timestamp).toLocaleTimeString()} ({travel.event_a.source_file})</p>
                      </div>

                      <div className="bg-red-50/40 p-3 rounded-xl border border-red-200 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-red-800">Destination Tower Event</span>
                          <span className="font-mono font-bold text-[#d93829] text-[10px]">Row #{travel.event_b.row_number}</span>
                        </div>
                        <p className="text-xs font-bold text-[#191410]">{travel.event_b.site_name || travel.event_b.cell_id}</p>
                        <p className="text-[10px] text-[#6e665d]">{new Date(travel.event_b.timestamp).toLocaleTimeString()} ({travel.event_b.source_file})</p>
                      </div>
                    </div>

                    <p className="text-xs text-[#191410] leading-relaxed bg-red-50/60 p-2.5 rounded-xl border border-red-200">
                      <span className="font-bold text-red-800 mr-1.5">[Teleportation Breach]:</span>
                      {travel.reasoning}
                    </p>
                  </div>
                ))
              )}
            </div>
          )}

          {/* 1E. RAW CALL DETAIL LEDGER */}
          {telecomTab === 'ledger' && (
            <div className="bg-white border border-[#eae4d9] rounded-2xl shadow-xs overflow-hidden">
              <div className="p-4 border-b border-[#f0ebe1] flex items-center justify-between gap-3">
                <span className="text-xs font-bold text-[#191410]">Extracted CDR Line Records</span>
                <div className="relative min-w-[240px]">
                  <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#6e665d]" />
                  <input
                    type="text"
                    placeholder="Search phone, tower, site..."
                    value={cdrSearch}
                    onChange={e => setCdrSearch(e.target.value)}
                    className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-[#eae4d9] text-xs bg-[#faf7f2] focus:outline-none focus:ring-1 focus:ring-[#d93829]"
                  />
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#faf7f2] border-b border-[#eae4d9] text-[#6e665d] font-bold uppercase text-[10px]">
                    <tr>
                      <th className="py-2.5 px-4">Line Row</th>
                      <th className="py-2.5 px-4">Caller (A)</th>
                      <th className="py-2.5 px-4">Called (B)</th>
                      <th className="py-2.5 px-4">Datetime</th>
                      <th className="py-2.5 px-4">Duration</th>
                      <th className="py-2.5 px-4">Tower Sector</th>
                      <th className="py-2.5 px-4">Site / Locality</th>
                      <th className="py-2.5 px-4">Source Exhibit</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#f0ebe1]">
                    {filteredCdrRecords.map(r => (
                      <tr key={r.id} className="hover:bg-[#faf7f2]/60">
                        <td className="py-2 px-4 font-mono font-bold text-[#d93829]">Row #{r.row_number}</td>
                        <td className="py-2 px-4 font-mono font-semibold">{r.calling_number}</td>
                        <td className="py-2 px-4 font-mono text-[#6e665d]">{r.called_number || 'N/A (Tower Dump)'}</td>
                        <td className="py-2 px-4 whitespace-nowrap">{new Date(r.call_datetime).toLocaleString()}</td>
                        <td className="py-2 px-4">{r.call_duration_sec}s</td>
                        <td className="py-2 px-4 font-mono text-[11px]">{r.cell_id}</td>
                        <td className="py-2 px-4 text-[#6e665d]">{r.site_name || '-'}</td>
                        <td className="py-2 px-4 text-[11px] text-[#6e665d] truncate max-w-[140px]" title={r.source_file_name}>
                          {r.source_file_name}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===================================================================== */}
      {/* SECTION 3: FORENSIC FINANCIAL & MONEY-FLOW */}
      {/* ===================================================================== */}
      {activeTab === 'financial' && (
        <div className="space-y-4">
          {/* Sub Navigation Bar */}
          <div className="bg-white border border-[#eae4d9] rounded-xl p-2 shadow-xs flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-1.5">
              {[
                { id: 'flow', label: 'Directed Money-Flow Network', count: moneyFlow?.edges?.length ?? 0, icon: TrendingUp },
                { id: 'alerts', label: 'Structuring & Layering Alerts', count: (moneyFlow?.structuring_alerts?.length ?? 0) + (moneyFlow?.layering_alerts?.length ?? 0), icon: AlertTriangle },
                { id: 'ledger', label: 'Bank Statement Transactions', count: bankTxns.length, icon: Landmark },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setFinancialTab(tab.id as any)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    financialTab === tab.id
                      ? 'bg-[#15803d] text-white shadow-xs'
                      : 'bg-[#faf7f2] text-[#6e665d] hover:bg-[#f0ebe1]'
                  }`}
                >
                  <tab.icon className="w-3.5 h-3.5" />
                  <span>{tab.label}</span>
                  <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${financialTab === tab.id ? 'bg-white/25 text-white' : 'bg-[#eae4d9] text-[#191410]'}`}>
                    {tab.count}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* 3A. DIRECTED MONEY FLOW NETWORK */}
          {financialTab === 'flow' && (
            <div className="space-y-4">
              {(!moneyFlow?.edges || moneyFlow.edges.length === 0) ? (
                <div className="bg-white border border-[#eae4d9] rounded-2xl p-12 text-center shadow-xs">
                  <Landmark className="w-8 h-8 text-[#6e665d] mx-auto mb-2 opacity-50" />
                  <h3 className="text-sm font-bold text-[#191410]">No Bank Transfers Logged</h3>
                  <p className="text-xs text-[#6e665d] mt-1 max-w-md mx-auto">
                    Import bank statements using the "Import Bank Statement" button to generate directed money flow graphs.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {moneyFlow.edges.map((edge, idx) => (
                    <div
                      key={idx}
                      className="bg-white border border-[#eae4d9] hover:border-emerald-300 rounded-2xl p-5 shadow-xs transition-all space-y-3"
                    >
                      <div className="flex items-center justify-between pb-3 border-b border-[#f0ebe1]">
                        <span className="text-xs font-bold text-[#191410]">{edge.transaction_count} Aggregate Transfer(s)</span>
                        <span className="text-base font-serif font-bold text-emerald-800">
                          {formatCurrency(edge.total_amount)}
                        </span>
                      </div>

                      {/* Direction Flow Visual */}
                      <div className="flex items-center justify-between gap-3 bg-[#faf7f2] p-3 rounded-xl border border-[#eae4d9]">
                        <div className="truncate">
                          <span className="text-[10px] font-bold text-[#6e665d] uppercase block">Origin Account</span>
                          <span className="text-xs font-mono font-bold text-[#191410] truncate block">{edge.source}</span>
                        </div>
                        <ArrowRight className="w-4 h-4 text-emerald-600 shrink-0" />
                        <div className="text-right truncate">
                          <span className="text-[10px] font-bold text-[#6e665d] uppercase block">Beneficiary / Target</span>
                          <span className="text-xs font-mono font-bold text-[#191410] truncate block">{edge.target}</span>
                        </div>
                      </div>

                      {/* Modes pills */}
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {edge.modes.map((mode, mIdx) => (
                          <span key={mIdx} className="bg-emerald-50 text-emerald-800 text-[10px] font-semibold px-2 py-0.5 rounded border border-emerald-200">
                            {mode}
                          </span>
                        ))}
                      </div>

                      {/* Linked rows */}
                      <div>
                        <span className="text-[10px] font-bold text-[#6e665d] uppercase tracking-wider block mb-1">
                          Statement Line Citations:
                        </span>
                        <div className="space-y-1">
                          {edge.linked_rows.map((lr, lIdx) => (
                            <div key={lIdx} className="text-[10px] bg-[#faf7f2] p-2 rounded-lg border border-[#eae4d9] flex items-center justify-between">
                              <span className="truncate max-w-[260px]">{lr.description} ({formatCurrency(lr.amount)})</span>
                              <span className="font-mono font-bold text-[#d93829] shrink-0">Row #{lr.row_number}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 3B. FINANCIAL STRUCTURING & LAYERING ALERTS */}
          {financialTab === 'alerts' && (
            <div className="space-y-4">
              {/* Structuring Alerts */}
              {moneyFlow?.structuring_alerts?.map((alert, aIdx) => (
                <div key={aIdx} className="bg-white border border-rose-300 rounded-2xl p-5 shadow-xs space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-rose-100">
                    <div className="flex items-center gap-2">
                      <span className="p-1.5 rounded-lg bg-rose-100 text-rose-800">
                        <AlertTriangle className="w-4 h-4" />
                      </span>
                      <h4 className="text-sm font-serif font-bold text-rose-900">{alert.title}</h4>
                    </div>
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800">
                      {formatCurrency(alert.total_structured_amount)} Structured
                    </span>
                  </div>

                  <p className="text-xs text-[#191410] leading-relaxed bg-rose-50/50 p-3 rounded-xl border border-rose-200">
                    {alert.reasoning}
                  </p>

                  <div>
                    <span className="text-[10px] font-bold text-[#6e665d] uppercase tracking-wider block mb-1">
                      Audited Statement Rows:
                    </span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {alert.linked_rows.map((lr, lIdx) => (
                        <div key={lIdx} className="bg-[#faf7f2] p-2.5 rounded-xl border border-[#eae4d9] text-xs flex items-center justify-between">
                          <span className="truncate">{lr.description} ({formatCurrency(lr.amount)})</span>
                          <span className="font-mono font-bold text-[#d93829]">Row #{lr.row_number}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}

              {/* Layering Alerts */}
              {moneyFlow?.layering_alerts?.map((layer, lIdx) => (
                <div key={lIdx} className="bg-white border border-purple-300 rounded-2xl p-5 shadow-xs space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-purple-100">
                    <div className="flex items-center gap-2">
                      <span className="p-1.5 rounded-lg bg-purple-100 text-purple-800">
                        <TrendingUp className="w-4 h-4" />
                      </span>
                      <h4 className="text-sm font-serif font-bold text-purple-900">{layer.title}</h4>
                    </div>
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-100 text-purple-800">
                      Within {layer.timeframe_hours} hrs
                    </span>
                  </div>

                  <p className="text-xs text-[#191410] leading-relaxed bg-purple-50/50 p-3 rounded-xl border border-purple-200">
                    {layer.reasoning}
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="bg-[#faf7f2] p-3 rounded-xl border border-[#eae4d9] text-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase text-[#6e665d]">Inflow Transaction</span>
                        <span className="font-mono font-bold text-[#d93829]">Row #{layer.inflow_row.row_number}</span>
                      </div>
                      <p className="font-bold text-emerald-800">{formatCurrency(layer.inflow_row.amount)}</p>
                      <p className="text-[11px] text-[#6e665d]">{layer.inflow_row.description}</p>
                    </div>

                    <div className="bg-[#faf7f2] p-3 rounded-xl border border-[#eae4d9] text-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase text-[#6e665d]">Rapid Outflow Dispersal</span>
                        <span className="font-bold text-rose-800">{formatCurrency(layer.dispersed_amount)}</span>
                      </div>
                      <div className="space-y-1">
                        {layer.outflow_rows.map((orw, oIdx) => (
                          <div key={oIdx} className="text-[10px] flex items-center justify-between bg-white px-2 py-1 rounded border border-[#eae4d9]">
                            <span className="truncate">{orw.description} ({formatCurrency(orw.amount)})</span>
                            <span className="font-mono font-bold text-[#d93829]">Row #{orw.row_number}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 3C. BANK STATEMENT TRANSACTION LEDGER */}
          {financialTab === 'ledger' && (
            <div className="bg-white border border-[#eae4d9] rounded-2xl shadow-xs overflow-hidden">
              <div className="p-4 border-b border-[#f0ebe1] flex items-center justify-between gap-3">
                <span className="text-xs font-bold text-[#191410]">Bank Statement Line Records</span>
                <div className="relative min-w-[240px]">
                  <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#6e665d]" />
                  <input
                    type="text"
                    placeholder="Search narration, UTR, ref..."
                    value={bankSearch}
                    onChange={e => setBankSearch(e.target.value)}
                    className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-[#eae4d9] text-xs bg-[#faf7f2] focus:outline-none focus:ring-1 focus:ring-[#15803d]"
                  />
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#faf7f2] border-b border-[#eae4d9] text-[#6e665d] font-bold uppercase text-[10px]">
                    <tr>
                      <th className="py-2.5 px-4">Line Row</th>
                      <th className="py-2.5 px-4">Date</th>
                      <th className="py-2.5 px-4">Narration / Description</th>
                      <th className="py-2.5 px-4">Ref / UTR</th>
                      <th className="py-2.5 px-4">Mode</th>
                      <th className="py-2.5 px-4 text-right">Debit (₹)</th>
                      <th className="py-2.5 px-4 text-right">Credit (₹)</th>
                      <th className="py-2.5 px-4 text-right">Balance (₹)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#f0ebe1]">
                    {filteredBankTxns.map(t => (
                      <tr key={t.id} className="hover:bg-[#faf7f2]/60">
                        <td className="py-2 px-4 font-mono font-bold text-[#d93829]">Row #{t.row_number}</td>
                        <td className="py-2 px-4 whitespace-nowrap">{new Date(t.transaction_date).toLocaleDateString()}</td>
                        <td className="py-2 px-4 max-w-[260px] truncate" title={t.description}>{t.description}</td>
                        <td className="py-2 px-4 font-mono text-[11px] text-[#6e665d]">{t.reference_number || '-'}</td>
                        <td className="py-2 px-4 font-bold text-[10px]">
                          <span className="bg-[#faf7f2] px-2 py-0.5 rounded border border-[#eae4d9]">{t.transaction_mode}</span>
                        </td>
                        <td className="py-2 px-4 text-right font-mono text-rose-700 font-semibold">
                          {t.debit_amount > 0 ? formatCurrency(t.debit_amount) : '-'}
                        </td>
                        <td className="py-2 px-4 text-right font-mono text-emerald-700 font-semibold">
                          {t.credit_amount > 0 ? formatCurrency(t.credit_amount) : '-'}
                        </td>
                        <td className="py-2 px-4 text-right font-mono font-bold">
                          {t.balance !== null ? formatCurrency(t.balance) : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL: REGISTER NEW WATCHLIST TARGET */}
      {/* ===================================================================== */}
      {watchlistModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full border border-[#eae4d9] shadow-xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#f0ebe1]">
              <div className="flex items-center gap-2">
                <Crosshair className="w-5 h-5 text-red-600" />
                <h3 className="text-base font-serif font-bold text-[#191410]">Register Monitored Target</h3>
              </div>
              <button
                onClick={() => setWatchlistModalOpen(false)}
                className="text-[#6e665d] hover:text-[#191410]"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateWatchlist} className="space-y-4">
              <div>
                <label className="text-xs font-bold text-[#191410] block mb-1">
                  Target Entity Type:
                </label>
                <select
                  value={newWatchlist.entity_type}
                  onChange={e => setNewWatchlist({ ...newWatchlist, entity_type: e.target.value })}
                  className="w-full text-xs p-2.5 rounded-xl border border-[#eae4d9] bg-[#faf7f2] focus:outline-none focus:bg-white"
                >
                  <option value="phone">📱 Phone Number (MSISDN / IMEI)</option>
                  <option value="account">🏦 Bank Account Number</option>
                  <option value="vehicle">🚗 Vehicle Registration (License Plate)</option>
                  <option value="person">👤 Person of Interest / Suspect Name</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-[#191410] block mb-1">
                  Identifier / Value:
                </label>
                <input
                  type="text"
                  placeholder={
                    newWatchlist.entity_type === 'phone'
                      ? 'e.g. +91-98200-44911'
                      : newWatchlist.entity_type === 'account'
                      ? 'e.g. SBIN-00044911-YR'
                      : newWatchlist.entity_type === 'vehicle'
                      ? 'e.g. MH12-DE-1433'
                      : 'e.g. Yogesh Raut'
                  }
                  value={newWatchlist.entity_value}
                  onChange={e => setNewWatchlist({ ...newWatchlist, entity_value: e.target.value })}
                  className="w-full text-xs p-2.5 rounded-xl border border-[#eae4d9] bg-[#faf7f2] focus:outline-none focus:bg-white font-mono"
                  required
                />
              </div>

              <div>
                <label className="text-xs font-bold text-[#191410] block mb-1">
                  Investigative Label / Alias:
                </label>
                <input
                  type="text"
                  placeholder="e.g. Prime Suspect Handset / Shell Account"
                  value={newWatchlist.label}
                  onChange={e => setNewWatchlist({ ...newWatchlist, label: e.target.value })}
                  className="w-full text-xs p-2.5 rounded-xl border border-[#eae4d9] bg-[#faf7f2] focus:outline-none focus:bg-white"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-[#191410] block mb-1">
                    Priority:
                  </label>
                  <select
                    value={newWatchlist.priority}
                    onChange={e => setNewWatchlist({ ...newWatchlist, priority: e.target.value as any })}
                    className="w-full text-xs p-2.5 rounded-xl border border-[#eae4d9] bg-[#faf7f2] focus:outline-none focus:bg-white"
                  >
                    <option value="critical">Critical (Red Alert)</option>
                    <option value="high">High (Priority Review)</option>
                    <option value="medium">Medium (Informational)</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-bold text-[#191410] block mb-1">
                    Surveillance Scope:
                  </label>
                  <select
                    value={newWatchlist.is_case_specific ? 'case' : 'global'}
                    onChange={e => setNewWatchlist({ ...newWatchlist, is_case_specific: e.target.value === 'case' })}
                    className="w-full text-xs p-2.5 rounded-xl border border-[#eae4d9] bg-[#faf7f2] focus:outline-none focus:bg-white"
                  >
                    <option value="global">Global (All Accessible Cases)</option>
                    <option value="case">Current Case Only</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-[#191410] block mb-1">
                  Investigative Rationale / Notes:
                </label>
                <textarea
                  rows={2}
                  placeholder="Describe why this target is monitored..."
                  value={newWatchlist.notes}
                  onChange={e => setNewWatchlist({ ...newWatchlist, notes: e.target.value })}
                  className="w-full text-xs p-2.5 rounded-xl border border-[#eae4d9] bg-[#faf7f2] focus:outline-none focus:bg-white"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#f0ebe1]">
                <button
                  type="button"
                  onClick={() => setWatchlistModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-[#6e665d] hover:bg-[#faf7f2]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-red-600 hover:bg-red-700 shadow-xs cursor-pointer"
                >
                  Activate Surveillance Target
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* IMPORT MODAL: CDR & TOWER DUMP */}
      {/* ===================================================================== */}
      {cdrModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full border border-[#eae4d9] shadow-xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#f0ebe1]">
              <div className="flex items-center gap-2">
                <FileSpreadsheet className="w-5 h-5 text-[#d93829]" />
                <h3 className="text-base font-serif font-bold text-[#191410]">Import CDR / Tower Dump</h3>
              </div>
              <button
                onClick={() => setCdrModalOpen(false)}
                className="text-[#6e665d] hover:text-[#191410]"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleImportCDR} className="space-y-4">
              <div>
                <label className="text-xs font-bold text-[#191410] block mb-1.5">
                  Select CSV or Excel (.xlsx) Exhibit:
                </label>
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={e => setSelectedFile(e.target.files?.[0] || null)}
                  className="w-full text-xs p-2.5 rounded-xl border border-[#eae4d9] bg-[#faf7f2] file:mr-3 file:py-1 file:px-2.5 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-[#191410] file:text-white"
                  required
                />
                <p className="text-[10px] text-[#6e665d] mt-1">
                  Supports Airtel, Vodafone-Idea, Jio, BSNL CDR schemas. Automatically extracts caller, called, timestamps, cell CGI, azimuth, and line citations.
                </p>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#f0ebe1]">
                <button
                  type="button"
                  onClick={() => setCdrModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-[#6e665d] hover:bg-[#faf7f2]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={importing || !selectedFile}
                  className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-[#d93829] hover:bg-[#b82e21] shadow-xs disabled:opacity-50"
                >
                  {importing ? 'Parsing & Mapping Rows...' : 'Ingest CDR Exhibit'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* IMPORT MODAL: BANK STATEMENT */}
      {/* ===================================================================== */}
      {bankModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full border border-[#eae4d9] shadow-xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#f0ebe1]">
              <div className="flex items-center gap-2">
                <Landmark className="w-5 h-5 text-[#15803d]" />
                <h3 className="text-base font-serif font-bold text-[#191410]">Import Bank Statement</h3>
              </div>
              <button
                onClick={() => setBankModalOpen(false)}
                className="text-[#6e665d] hover:text-[#191410]"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleImportBank} className="space-y-4">
              <div>
                <label className="text-xs font-bold text-[#191410] block mb-1">
                  Primary Account Number:
                </label>
                <input
                  type="text"
                  placeholder="e.g. SBIN-00044911-YR"
                  value={bankAccHint}
                  onChange={e => setBankAccHint(e.target.value)}
                  className="w-full text-xs p-2.5 rounded-xl border border-[#eae4d9] bg-[#faf7f2] focus:outline-none focus:bg-white"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-[#191410] block mb-1">
                  Bank Name / Branch:
                </label>
                <input
                  type="text"
                  placeholder="e.g. State Bank of India (Yerwada Branch)"
                  value={bankNameHint}
                  onChange={e => setBankNameHint(e.target.value)}
                  className="w-full text-xs p-2.5 rounded-xl border border-[#eae4d9] bg-[#faf7f2] focus:outline-none focus:bg-white"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-[#191410] block mb-1.5">
                  Statement File (CSV or Excel):
                </label>
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={e => setSelectedFile(e.target.files?.[0] || null)}
                  className="w-full text-xs p-2.5 rounded-xl border border-[#eae4d9] bg-[#faf7f2] file:mr-3 file:py-1 file:px-2.5 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-[#191410] file:text-white"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#f0ebe1]">
                <button
                  type="button"
                  onClick={() => setBankModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-[#6e665d] hover:bg-[#faf7f2]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={importing || !selectedFile}
                  className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-[#15803d] hover:bg-[#166534] shadow-xs disabled:opacity-50"
                >
                  {importing ? 'Ingesting Ledger...' : 'Import Statement'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
