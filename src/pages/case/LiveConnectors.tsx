// src/pages/case/LiveConnectors.tsx
import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  Radio, FolderSync, Mail, Globe, Zap, Play, Pause, Trash2, 
  RefreshCw, Plus, ShieldCheck, CheckCircle2, AlertTriangle, 
  ArrowLeft, FileText, Copy, Check, ExternalLink, HardDrive, 
  Clock, Database, Eye, Terminal, Sparkles, Filter
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { dataConnectorService, caseService } from '../../services';
import { 
  DataConnector, 
  ConnectorIngestRecord, 
  ConnectorPollResponse, 
  Case 
} from '../../types';
import { cn } from '../../utils';

export function LiveConnectors() {
  const { caseId } = useParams<{ caseId: string }>();
  const { user } = useAuth();

  const [currentCase, setCurrentCase] = useState<Case | null>(null);
  const [connectors, setConnectors] = useState<DataConnector[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  // Modal States
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isDropModalOpen, setIsDropModalOpen] = useState(false);
  const [selectedConnectorForDrop, setSelectedConnectorForDrop] = useState<DataConnector | null>(null);

  // Ingest History Drawer / Table
  const [selectedConnectorForHistory, setSelectedConnectorForHistory] = useState<DataConnector | null>(null);
  const [historyRecords, setHistoryRecords] = useState<ConnectorIngestRecord[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Feedback Notification
  const [feedback, setFeedback] = useState<{
    type: 'success' | 'error' | 'info';
    message: string;
    details?: string;
  } | null>(null);

  // Create Form State
  const [newName, setNewName] = useState('');
  const [newType, setNewType] = useState<'folder_watch' | 'email_inbox' | 'api_pull' | 'webhook'>('folder_watch');
  const [newSourceId, setNewSourceId] = useState('');
  const [newConfigJson, setNewConfigJson] = useState('{\n  "file_patterns": ["*.pdf", "*.txt", "*.csv", "*.pcap", "*.jpg"]\n}');

  // Simulate Drop Form State
  const [sampleType, setSampleType] = useState<string>('cdr_export');
  const [customFilename, setCustomFilename] = useState('');
  const [customContent, setCustomContent] = useState('');

  // Clipboard Copy State
  const [copiedToken, setCopiedToken] = useState<string | null>(null);

  useEffect(() => {
    if (!caseId) return;
    loadCaseAndConnectors();
  }, [caseId]);

  const loadCaseAndConnectors = async () => {
    if (!caseId) return;
    setLoading(true);
    try {
      const [c, connList] = await Promise.all([
        caseService.getCaseById(caseId).catch(() => null),
        dataConnectorService.getConnectors(caseId).catch(() => [])
      ]);
      setCurrentCase(c || null);
      setConnectors(connList || []);
      if (connList && connList.length > 0 && !selectedConnectorForHistory) {
        setSelectedConnectorForHistory(connList[0]);
        loadHistory(connList[0].id);
      }
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: 'Failed to load case data connectors',
        details: err?.message || String(err)
      });
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async (connectorId: number) => {
    if (!caseId) return;
    setLoadingHistory(true);
    try {
      const records = await dataConnectorService.getIngestHistory(caseId, connectorId);
      setHistoryRecords(records || []);
    } catch (err: any) {
      console.error('Failed to load ingest history:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleCreateConnector = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId || !newName.trim() || !newSourceId.trim()) return;

    try {
      const created = await dataConnectorService.createConnector(caseId, {
        name: newName.trim(),
        connector_type: newType,
        source_identifier: newSourceId.trim(),
        config_json: newConfigJson,
        is_active: true
      });

      setConnectors(prev => [created, ...prev]);
      setIsCreateModalOpen(false);
      setNewName('');
      setNewSourceId('');
      setFeedback({
        type: 'success',
        message: `Registered connector '${created.name}' (${created.connector_type}) successfully.`,
      });
      if (!selectedConnectorForHistory) {
        setSelectedConnectorForHistory(created);
        loadHistory(created.id);
      }
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: 'Could not register live connector',
        details: err?.message || String(err)
      });
    }
  };

  const handlePollConnector = async (connector: DataConnector) => {
    if (!caseId) return;
    setActionLoading(connector.id);
    try {
      const res = await dataConnectorService.pollConnector(caseId, connector.id);
      setFeedback({
        type: res.success ? 'success' : 'error',
        message: res.message,
        details: res.ingested_evidence_ids.length > 0 
          ? `Generated exhibits: ${res.ingested_evidence_ids.map(id => `#${id}`).join(', ')}`
          : undefined
      });
      loadCaseAndConnectors();
      if (selectedConnectorForHistory?.id === connector.id) {
        loadHistory(connector.id);
      }
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: `Failed polling connector '${connector.name}'`,
        details: err?.message || String(err)
      });
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleActive = async (connector: DataConnector) => {
    if (!caseId) return;
    try {
      const updated = await dataConnectorService.updateConnector(caseId, connector.id, {
        is_active: !connector.is_active
      });
      setConnectors(prev => prev.map(c => c.id === connector.id ? updated : c));
      setFeedback({
        type: 'info',
        message: `Connector '${connector.name}' is now ${updated.is_active ? 'active' : 'paused'}.`
      });
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: 'Failed to update connector state',
        details: err?.message || String(err)
      });
    }
  };

  const handleDeleteConnector = async (connector: DataConnector) => {
    if (!caseId) return;
    if (!window.confirm(`Are you sure you want to delete connector '${connector.name}'?`)) return;

    try {
      await dataConnectorService.deleteConnector(caseId, connector.id);
      setConnectors(prev => prev.filter(c => c.id !== connector.id));
      if (selectedConnectorForHistory?.id === connector.id) {
        setSelectedConnectorForHistory(null);
        setHistoryRecords([]);
      }
      setFeedback({
        type: 'success',
        message: `Connector '${connector.name}' deleted successfully.`
      });
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: 'Failed to delete connector',
        details: err?.message || String(err)
      });
    }
  };

  const handleSimulateDropSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId || !selectedConnectorForDrop) return;

    setActionLoading(selectedConnectorForDrop.id);
    try {
      const res = await dataConnectorService.simulateDrop(caseId, selectedConnectorForDrop.id, {
        sample_type: sampleType,
        custom_filename: customFilename.trim() || undefined,
        custom_content: customContent.trim() || undefined
      });

      setIsDropModalOpen(false);
      setCustomFilename('');
      setCustomContent('');
      setFeedback({
        type: res.success ? 'success' : 'error',
        message: res.message,
        details: res.ingested_evidence_ids.length > 0
          ? `Exhibit #${res.ingested_evidence_ids[0]} ingested with full chain of custody.`
          : undefined
      });

      loadCaseAndConnectors();
      if (selectedConnectorForHistory?.id === selectedConnectorForDrop.id) {
        loadHistory(selectedConnectorForDrop.id);
      }
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: 'Simulation drop failed',
        details: err?.message || String(err)
      });
    } finally {
      setActionLoading(null);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedToken(id);
    setTimeout(() => setCopiedToken(null), 2500);
  };

  const totalIngested = connectors.reduce((sum, c) => sum + (c.items_ingested_count || 0), 0);
  const activeCount = connectors.filter(c => c.is_active && c.status !== 'error').length;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-fade-in text-[#191410]">
      {/* Top Breadcrumb & Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#eae4d9] pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#d93829] mb-1">
            <Link to={`/cases/${caseId}/overview`} className="hover:underline flex items-center gap-1">
              <ArrowLeft className="w-3.5 h-3.5" /> Case Overview
            </Link>
            <span>/</span>
            <Link to={`/cases/${caseId}/evidence`} className="hover:underline">
              Evidence Docket
            </Link>
            <span>/</span>
            <span className="text-[#6e665d]">Live Connectors</span>
          </div>
          <h1 className="text-3xl font-serif font-bold text-[#191410] tracking-tight flex items-center gap-3">
            <Radio className="w-8 h-8 text-[#d93829] animate-pulse" />
            Live Evidence Connectors
          </h1>
          <p className="text-sm text-[#6e665d] mt-1 max-w-3xl">
            Stream electronic evidence into the case docket automatically from forensic lab drops, telecom CDR exports, whistleblower email tip-lines, and real-time dispatch webhooks with guaranteed chain-of-custody provenance.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to={`/cases/${caseId}/evidence`}
            className="px-4 py-2 text-sm font-semibold rounded-xl border border-[#eae4d9] bg-white text-[#191410] hover:bg-[#faf7f2] transition-colors flex items-center gap-2 shadow-xs"
          >
            <FileText className="w-4 h-4 text-[#6e665d]" />
            View Evidence Docket
          </Link>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="px-4 py-2 text-sm font-semibold rounded-xl bg-[#d93829] hover:bg-[#b82d20] text-white shadow-xs flex items-center gap-2 transition-transform active:scale-95 cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            Register Connector
          </button>
        </div>
      </div>

      {/* Feedback Banner */}
      {feedback && (
        <div className={cn(
          "p-4 rounded-xl border flex items-start justify-between gap-3 shadow-xs transition-all",
          feedback.type === 'success' && "bg-emerald-50 border-emerald-200 text-emerald-900",
          feedback.type === 'error' && "bg-red-50 border-red-200 text-red-900",
          feedback.type === 'info' && "bg-blue-50 border-blue-200 text-blue-900"
        )}>
          <div className="flex items-start gap-3">
            {feedback.type === 'success' && <CheckCircle2 className="w-5 h-5 text-emerald-600 mt-0.5" />}
            {feedback.type === 'error' && <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5" />}
            {feedback.type === 'info' && <RefreshCw className="w-5 h-5 text-blue-600 mt-0.5" />}
            <div>
              <p className="font-semibold text-sm">{feedback.message}</p>
              {feedback.details && <p className="text-xs mt-1 opacity-90">{feedback.details}</p>}
            </div>
          </div>
          <button onClick={() => setFeedback(null)} className="text-xs font-bold hover:opacity-75 cursor-pointer">✕</button>
        </div>
      )}

      {/* KPI Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 bg-white border border-[#eae4d9] rounded-xl shadow-xs">
          <div className="flex items-center justify-between text-[#6e665d] text-xs font-semibold uppercase tracking-wider">
            <span>Configured Streams</span>
            <Database className="w-4 h-4 text-[#6e665d]" />
          </div>
          <div className="text-3xl font-serif font-black mt-2 text-[#191410]">
            {connectors.length}
          </div>
          <p className="text-xs text-[#6e665d] mt-1">Watch folders, inboxes & webhooks</p>
        </div>

        <div className="p-5 bg-white border border-[#eae4d9] rounded-xl shadow-xs">
          <div className="flex items-center justify-between text-[#6e665d] text-xs font-semibold uppercase tracking-wider">
            <span>Active Polling</span>
            <RefreshCw className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-3xl font-serif font-black mt-2 text-emerald-700">
            {activeCount}
          </div>
          <p className="text-xs text-[#6e665d] mt-1">Continuous ingestion pipelines</p>
        </div>

        <div className="p-5 bg-white border border-[#eae4d9] rounded-xl shadow-xs">
          <div className="flex items-center justify-between text-[#6e665d] text-xs font-semibold uppercase tracking-wider">
            <span>Exhibits Ingested</span>
            <FileText className="w-4 h-4 text-[#d93829]" />
          </div>
          <div className="text-3xl font-serif font-black mt-2 text-[#d93829]">
            {totalIngested}
          </div>
          <p className="text-xs text-[#6e665d] mt-1">Automatic handover to docket</p>
        </div>

        <div className="p-5 bg-white border border-[#eae4d9] rounded-xl shadow-xs">
          <div className="flex items-center justify-between text-[#6e665d] text-xs font-semibold uppercase tracking-wider">
            <span>Section 65B Provenance</span>
            <ShieldCheck className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-3xl font-serif font-black mt-2 text-blue-700">
            100%
          </div>
          <p className="text-xs text-[#6e665d] mt-1">Source & timestamp verified</p>
        </div>
      </div>

      {/* Main Grid: Connector Cards & History Viewer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Configured Connectors (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-serif font-bold text-[#191410] flex items-center gap-2">
              <HardDrive className="w-5 h-5 text-[#6e665d]" />
              Configured Live Streams
            </h2>
            <button
              onClick={loadCaseAndConnectors}
              className="text-xs font-semibold text-[#6e665d] hover:text-[#191410] flex items-center gap-1 cursor-pointer"
            >
              <RefreshCw className={cn("w-3.5 h-3.5 text-[#d93829]", loading && "animate-spin")} />
              Refresh
            </button>
          </div>

          {loading ? (
            <div className="p-12 text-center bg-white rounded-xl border border-[#eae4d9]">
              <RefreshCw className="w-8 h-8 text-[#d93829] animate-spin mx-auto mb-3" />
              <p className="text-sm text-[#6e665d]">Loading case data connectors...</p>
            </div>
          ) : connectors.length === 0 ? (
            <div className="p-12 text-center bg-white rounded-xl border border-dashed border-[#eae4d9] space-y-4">
              <Radio className="w-12 h-12 text-[#6e665d]/50 mx-auto" />
              <div className="max-w-md mx-auto">
                <h3 className="text-base font-serif font-bold text-[#191410]">No Live Connectors Configured</h3>
                <p className="text-sm text-[#6e665d] mt-1">
                  Connect a local watch folder, an email tip inbox, or a real-time webhook to stream evidence into Case #{caseId} automatically.
                </p>
              </div>
              <button
                onClick={() => setIsCreateModalOpen(true)}
                className="px-4 py-2 bg-[#d93829] hover:bg-[#b82d20] text-white text-sm font-semibold rounded-xl inline-flex items-center gap-2 cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                Configure First Live Connector
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {connectors.map(conn => {
                const isSelected = selectedConnectorForHistory?.id === conn.id;
                const isPolling = actionLoading === conn.id;

                return (
                  <div
                    key={conn.id}
                    className={cn(
                      "p-5 rounded-xl border transition-all bg-white shadow-xs hover:border-stone-400",
                      isSelected ? "ring-2 ring-[#d93829]/50 border-[#d93829]" : "border-[#eae4d9]"
                    )}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3">
                        <div className={cn(
                          "p-2.5 rounded-lg text-white shrink-0 mt-0.5",
                          conn.connector_type === 'folder_watch' && "bg-amber-600",
                          conn.connector_type === 'email_inbox' && "bg-blue-600",
                          conn.connector_type === 'webhook' && "bg-purple-600",
                          conn.connector_type === 'api_pull' && "bg-emerald-600"
                        )}>
                          {conn.connector_type === 'folder_watch' && <FolderSync className="w-5 h-5" />}
                          {conn.connector_type === 'email_inbox' && <Mail className="w-5 h-5" />}
                          {conn.connector_type === 'webhook' && <Zap className="w-5 h-5" />}
                          {conn.connector_type === 'api_pull' && <Globe className="w-5 h-5" />}
                        </div>

                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-serif font-bold text-base text-[#191410]">
                              {conn.name}
                            </h3>
                            <span className={cn(
                              "px-2 py-0.5 text-xs font-bold rounded-full uppercase tracking-wider",
                              conn.status === 'active' && "bg-emerald-50 text-emerald-800 border border-emerald-200",
                              conn.status === 'polling' && "bg-blue-50 text-blue-800 border border-blue-200",
                              conn.status === 'idle' && "bg-stone-100 text-stone-700 border border-stone-200",
                              conn.status === 'paused' && "bg-amber-50 text-amber-800 border border-amber-200",
                              conn.status === 'error' && "bg-red-50 text-red-800 border border-red-200"
                            )}>
                              {conn.status}
                            </span>
                            {!conn.is_active && (
                              <span className="text-xs text-amber-700 font-semibold">(Paused)</span>
                            )}
                          </div>

                          <p className="text-xs font-mono text-[#6e665d] mt-1 break-all bg-[#faf7f2] p-1.5 rounded border border-[#eae4d9]">
                            {conn.source_identifier}
                          </p>

                          <div className="flex flex-wrap items-center gap-4 text-xs text-[#6e665d] mt-3">
                            <span className="flex items-center gap-1">
                              <Clock className="w-3.5 h-3.5" />
                              Last polled: {conn.last_polled_at ? new Date(conn.last_polled_at).toLocaleTimeString() : 'Never'}
                            </span>
                            <span className="flex items-center gap-1 font-semibold text-[#191410]">
                              <FileText className="w-3.5 h-3.5 text-[#d93829]" />
                              {conn.items_ingested_count} exhibits ingested
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Top Action Buttons */}
                      <div className="flex items-center gap-1.5 shrink-0">
                        <button
                          onClick={() => {
                            setSelectedConnectorForHistory(conn);
                            loadHistory(conn.id);
                          }}
                          className={cn(
                            "px-2.5 py-1.5 text-xs font-semibold rounded-lg border transition-colors flex items-center gap-1 cursor-pointer",
                            isSelected 
                              ? "bg-red-50 border-red-200 text-red-700"
                              : "border-[#eae4d9] hover:bg-[#faf7f2] text-[#191410]"
                          )}
                          title="View Ingestion Log"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          Log
                        </button>

                        <button
                          onClick={() => handleToggleActive(conn)}
                          className="p-1.5 text-[#6e665d] hover:text-[#191410] rounded-lg border border-[#eae4d9] hover:bg-[#faf7f2] cursor-pointer"
                          title={conn.is_active ? "Pause Connector" : "Resume Connector"}
                        >
                          {conn.is_active ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 text-emerald-600" />}
                        </button>

                        <button
                          onClick={() => handleDeleteConnector(conn)}
                          className="p-1.5 text-[#6e665d] hover:text-[#d93829] rounded-lg border border-[#eae4d9] hover:bg-red-50 cursor-pointer"
                          title="Delete Connector"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Webhook Endpoint Banner (if Webhook type) */}
                    {conn.connector_type === 'webhook' && conn.webhook_url && (
                      <div className="mt-4 p-3 bg-purple-50 border border-purple-200 rounded-lg flex items-center justify-between gap-2">
                        <div className="text-xs font-mono text-purple-950 truncate">
                          <span className="font-bold uppercase text-[10px] tracking-wider bg-purple-200 text-purple-900 px-1.5 py-0.5 rounded mr-2">POST</span>
                          {conn.webhook_url}
                        </div>
                        <button
                          onClick={() => copyToClipboard(conn.webhook_url!, String(conn.id))}
                          className="text-xs px-2 py-1 bg-white border border-purple-300 rounded font-semibold text-purple-900 flex items-center gap-1 shrink-0 hover:bg-purple-100 cursor-pointer"
                        >
                          {copiedToken === String(conn.id) ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                          Copy URL
                        </button>
                      </div>
                    )}

                    {/* Bottom Action Strip */}
                    <div className="mt-4 pt-3 border-t border-[#eae4d9] flex items-center justify-between gap-3">
                      <button
                        onClick={() => handlePollConnector(conn)}
                        disabled={isPolling || !conn.is_active}
                        className={cn(
                          "px-3 py-1.5 text-xs font-bold rounded-lg border flex items-center gap-1.5 transition-all cursor-pointer",
                          isPolling 
                            ? "bg-[#faf7f2] text-[#6e665d]/50 border-[#eae4d9] cursor-not-allowed"
                            : "bg-white border-[#eae4d9] hover:border-stone-400 text-[#191410]"
                        )}
                      >
                        <RefreshCw className={cn("w-3.5 h-3.5", isPolling && "animate-spin text-[#d93829]")} />
                        {isPolling ? 'Polling Stream...' : 'Poll Stream Now'}
                      </button>

                      <button
                        onClick={() => {
                          setSelectedConnectorForDrop(conn);
                          setIsDropModalOpen(true);
                        }}
                        className="px-3 py-1.5 text-xs font-bold rounded-lg bg-red-50 hover:bg-red-100 text-[#d93829] border border-red-200 flex items-center gap-1.5 transition-transform active:scale-95 cursor-pointer"
                      >
                        <Sparkles className="w-3.5 h-3.5 text-[#d93829]" />
                        Simulate Evidence Drop
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Custody Ingestion Event Log (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-serif font-bold text-[#191410] flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-600" />
              Cryptographic Ingestion Ledger
            </h2>
            {selectedConnectorForHistory && (
              <span className="text-xs font-bold text-[#6e665d]">
                {selectedConnectorForHistory.name}
              </span>
            )}
          </div>

          <div className="bg-white border border-[#eae4d9] rounded-xl p-5 shadow-xs">
            {!selectedConnectorForHistory ? (
              <div className="p-8 text-center text-[#6e665d] text-xs">
                Select a connector on the left to view its tamper-evident ingestion history.
              </div>
            ) : loadingHistory ? (
              <div className="p-8 text-center text-[#6e665d] text-xs">
                <RefreshCw className="w-6 h-6 text-[#d93829] animate-spin mx-auto mb-2" />
                Loading cryptographic custody ledger...
              </div>
            ) : historyRecords.length === 0 ? (
              <div className="p-8 text-center text-[#6e665d] text-xs space-y-2">
                <Clock className="w-8 h-8 text-[#6e665d]/40 mx-auto" />
                <p className="font-medium text-[#191410]">No files ingested yet via this connector.</p>
                <p className="text-[11px] text-[#6e665d]">
                  Drop a file in the watch folder or click "Simulate Evidence Drop" to test.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="text-xs font-semibold text-[#6e665d] uppercase tracking-wider pb-2 border-b border-[#eae4d9] flex items-center justify-between">
                  <span>Recent Stream Events ({historyRecords.length})</span>
                  <span>Section 65B (§61/§63 BSA)</span>
                </div>

                <div className="divide-y divide-[#eae4d9] max-h-[560px] overflow-y-auto pr-1">
                  {historyRecords.map(rec => (
                    <div key={rec.id} className="py-3 space-y-1.5">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold text-xs text-[#191410] truncate max-w-[200px]" title={rec.source_filename}>
                          {rec.source_filename}
                        </span>
                        <span className={cn(
                          "px-2 py-0.5 text-[10px] font-bold rounded-full uppercase",
                          rec.status === 'success' && "bg-emerald-50 text-emerald-800 border border-emerald-200",
                          rec.status === 'duplicate_skipped' && "bg-amber-50 text-amber-800 border border-amber-200",
                          rec.status === 'failed' && "bg-red-50 text-red-800 border border-red-200"
                        )}>
                          {rec.status === 'duplicate_skipped' ? 'Duplicate Skipped' : rec.status}
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-[#6e665d]">
                        <span className="font-mono text-[10px] truncate max-w-[160px]" title={rec.source_system}>
                          {rec.source_system}
                        </span>
                        <span>{new Date(rec.receipt_time).toLocaleString()}</span>
                      </div>

                      <div className="flex items-center justify-between text-[10px] text-[#6e665d] font-mono bg-[#faf7f2] p-1.5 rounded border border-[#eae4d9]">
                        <span title={rec.file_hash}>SHA256: {rec.file_hash.slice(0, 16)}...</span>
                        {rec.evidence_id && (
                          <Link
                            to={`/cases/${caseId}/evidence`}
                            className="text-[#d93829] font-sans font-bold hover:underline flex items-center gap-0.5"
                          >
                            Exhibit #{rec.evidence_id} <ExternalLink className="w-2.5 h-2.5" />
                          </Link>
                        )}
                      </div>

                      {rec.error_message && (
                        <p className="text-[11px] text-amber-800 bg-amber-50 p-1.5 rounded border border-amber-200">
                          {rec.error_message}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ===================================================================== */}
      {/* MODAL 1: REGISTER CONNECTOR */}
      {/* ===================================================================== */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-[#eae4d9] rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-5 animate-scale-in">
            <div className="flex items-center justify-between border-b border-[#eae4d9] pb-4">
              <h3 className="font-serif font-bold text-lg text-[#191410] flex items-center gap-2">
                <Radio className="w-5 h-5 text-[#d93829]" />
                Register Live Evidence Connector
              </h3>
              <button onClick={() => setIsCreateModalOpen(false)} className="text-[#6e665d] hover:text-[#191410] font-bold cursor-pointer">✕</button>
            </div>

            <form onSubmit={handleCreateConnector} className="space-y-4 text-sm">
              <div>
                <label className="block text-xs font-bold uppercase text-[#6e665d] mb-1">
                  Connector Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g., Forensic Lab Drop Box / Whistleblower Tip-Line"
                  value={newName}
                  onChange={e => setNewName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-[#eae4d9] bg-[#faf7f2] text-[#191410] focus:ring-2 focus:ring-[#d93829] outline-hidden"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-[#6e665d] mb-1">
                  Connector Stream Type
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: 'folder_watch', label: 'Watch Folder', icon: FolderSync, desc: 'Shared drop-box / local directory' },
                    { id: 'email_inbox', label: 'Email Tip-Line', icon: Mail, desc: 'RFC 822 .eml tip-off parsing' },
                    { id: 'webhook', label: 'Webhook Push', icon: Zap, desc: 'Real-time REST push endpoint' },
                    { id: 'api_pull', label: 'Scheduled API', icon: Globe, desc: 'Periodic authorized laboratory pull' },
                  ].map(item => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => setNewType(item.id as any)}
                      className={cn(
                        "p-3 rounded-xl border text-left flex flex-col gap-1 transition-all cursor-pointer",
                        newType === item.id 
                          ? "border-[#d93829] bg-red-50/60 text-[#191410]"
                          : "border-[#eae4d9] hover:bg-[#faf7f2] text-[#191410]"
                      )}
                    >
                      <div className="flex items-center gap-2 font-bold text-xs">
                        <item.icon className="w-4 h-4 text-[#d93829]" />
                        {item.label}
                      </div>
                      <span className="text-[11px] text-[#6e665d] leading-tight">{item.desc}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-[#6e665d] mb-1">
                  Source Identifier
                </label>
                <input
                  type="text"
                  required
                  placeholder={
                    newType === 'folder_watch' ? "e.g., ./data/lab_drops or D:/CFSL_Exports" :
                    newType === 'email_inbox' ? "e.g., ./data/inbox_tips" :
                    newType === 'webhook' ? "e.g., dispatch_gateway_anpr" :
                    "e.g., https://portal.forensics.state.gov/api/v1/exhibits"
                  }
                  value={newSourceId}
                  onChange={e => setNewSourceId(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-[#eae4d9] bg-[#faf7f2] text-[#191410] font-mono text-xs focus:ring-2 focus:ring-[#d93829] outline-hidden"
                />
                <p className="text-[11px] text-[#6e665d] mt-1">
                  {newType === 'folder_watch' && "Directory path monitored for uningested forensic files."}
                  {newType === 'email_inbox' && "Folder holding incoming .eml messages sent by whistleblowers or dispatch."}
                  {newType === 'webhook' && "Internal label. A secure random token will be generated automatically."}
                  {newType === 'api_pull' && "REST API endpoint polled for certified exhibit manifests."}
                </p>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-[#6e665d] mb-1">
                  Configuration Settings (JSON)
                </label>
                <textarea
                  rows={3}
                  value={newConfigJson}
                  onChange={e => setNewConfigJson(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-[#eae4d9] bg-[#faf7f2] text-[#191410] font-mono text-xs focus:ring-2 focus:ring-[#d93829] outline-hidden"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#eae4d9]">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-4 py-2 rounded-xl border border-[#eae4d9] text-[#6e665d] hover:bg-[#faf7f2] font-semibold text-xs cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-[#d93829] hover:bg-[#b82d20] text-white font-bold text-xs shadow-xs flex items-center gap-1.5 cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Activate Connector
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 2: SIMULATE EVIDENCE DROP */}
      {/* ===================================================================== */}
      {isDropModalOpen && selectedConnectorForDrop && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-[#eae4d9] rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-5 animate-scale-in">
            <div className="flex items-center justify-between border-b border-[#eae4d9] pb-4">
              <div>
                <h3 className="font-serif font-bold text-lg text-[#191410] flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-[#d93829]" />
                  Simulate Live Evidence Drop
                </h3>
                <p className="text-xs text-[#6e665d] mt-0.5">
                  Target: {selectedConnectorForDrop.name} ({selectedConnectorForDrop.connector_type})
                </p>
              </div>
              <button onClick={() => setIsDropModalOpen(false)} className="text-[#6e665d] hover:text-[#191410] font-bold cursor-pointer">✕</button>
            </div>

            <form onSubmit={handleSimulateDropSubmit} className="space-y-4 text-sm">
              <div>
                <label className="block text-xs font-bold uppercase text-[#6e665d] mb-2">
                  Select Realistic Forensic Sample
                </label>
                <div className="space-y-2">
                  {[
                    { id: 'cdr_export', title: 'Telco CDR Tower Export (.csv)', desc: 'Call detail record dump with cell tower azimuth, duration, IMEI/IMSI' },
                    { id: 'lab_toxicology', title: 'CFSL Chemical & Toxicology Report (.txt)', desc: 'Forensic laboratory swab findings and chemical residue analysis' },
                    { id: 'bank_statement', title: 'Bank NEFT/RTGS Transaction Ledger (.csv)', desc: 'ATM cash withdrawals, IMPS timestamps, and account ledger' },
                    { id: 'cctv_metadata', title: 'Toll Plaza ANPR Camera Telemetry (.json)', desc: 'Automatic number plate recognition with speed and frame timestamps' },
                    { id: 'whistleblower_email', title: 'Informant Tip-Off Testimony (.txt / .eml)', desc: 'Whistleblower dispatch with suspect identification and alibi rebuttal' },
                  ].map(s => (
                    <label
                      key={s.id}
                      className={cn(
                        "p-3 rounded-xl border flex items-start gap-3 cursor-pointer transition-all",
                        sampleType === s.id
                          ? "border-[#d93829] bg-red-50/50"
                          : "border-[#eae4d9] hover:bg-[#faf7f2]"
                      )}
                    >
                      <input
                        type="radio"
                        name="sample_type"
                        value={s.id}
                        checked={sampleType === s.id}
                        onChange={() => setSampleType(s.id)}
                        className="mt-1 text-[#d93829] focus:ring-[#d93829]"
                      />
                      <div>
                        <div className="font-bold text-xs text-[#191410]">{s.title}</div>
                        <div className="text-[11px] text-[#6e665d]">{s.desc}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-[#6e665d] mb-1">
                  Custom Content (Optional Override)
                </label>
                <textarea
                  rows={2}
                  placeholder="Leave empty to use realistic sample forensic payload..."
                  value={customContent}
                  onChange={e => setCustomContent(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-[#eae4d9] bg-[#faf7f2] text-[#191410] font-mono text-xs focus:ring-2 focus:ring-[#d93829] outline-hidden"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#eae4d9]">
                <button
                  type="button"
                  onClick={() => setIsDropModalOpen(false)}
                  className="px-4 py-2 rounded-xl border border-[#eae4d9] text-[#6e665d] hover:bg-[#faf7f2] font-semibold text-xs cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading === selectedConnectorForDrop.id}
                  className="px-4 py-2 rounded-xl bg-[#d93829] hover:bg-[#b82d20] text-white font-bold text-xs shadow-xs flex items-center gap-1.5 cursor-pointer"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  {actionLoading === selectedConnectorForDrop.id ? 'Streaming Artifact...' : 'Stream Artifact Now'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default LiveConnectors;
