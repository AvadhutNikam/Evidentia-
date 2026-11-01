import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/Card';
import { 
  Settings as SettingsIcon, User, Shield, Database, Palette, Bell, Key, 
  Cpu, Lock, CheckCircle2, AlertTriangle, RefreshCw, Smartphone, 
  Trash2, Copy, Check, Eye, EyeOff, ShieldCheck, ShieldAlert, Server, HardDrive,
  Sliders, FileText, BarChart2, Activity, Scale
} from 'lucide-react';
import { cn } from '../../utils';
import { useAuth } from '../../context/AuthContext';
import { 
  securityAdminService 
} from '../../services';
import { 
  SystemSecurityConfig, 
  BackupRecord, 
  UserSession, 
  TwoFactorSetupResponse 
} from '../../types';
import { ScoringConfiguration } from '../case/ScoringConfiguration';
import { ResponsibleUse } from '../case/ResponsibleUse';
import { ModelCard } from './ModelCard';
import { Evaluation } from './Evaluation';
import { SystemHealth } from './SystemHealth';

const baseSections = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'security', label: 'Security & 2FA', icon: Shield },
  { id: 'ai_models', label: 'AI & Private Models', icon: Cpu },
  { id: 'storage', label: 'Backups & Retention', icon: Database },
  { id: 'notifications', label: 'Notifications', icon: Bell },
];

export function Settings() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { user, role } = useAuth();
  const isAdmin = role === 'admin';
  const isLeadOrAdmin = role === 'admin' || role === 'lead_investigator';
  const initialSection = searchParams.get('section') || 'security';
  const [activeSection, setActiveSection] = useState(initialSection);

  const sections = [
    ...baseSections,
    ...(isLeadOrAdmin ? [
      { id: 'scoring_config', label: 'Scoring Rules & Weights', icon: Sliders, badge: 'Lead/Admin' },
      { id: 'responsible_use', label: 'Responsible AI & Legal Limits', icon: Scale, badge: 'Statutory' },
      { id: 'model_card', label: 'Forensic AI Model Card', icon: FileText, badge: 'Specs' },
      { id: 'evaluation', label: 'Benchmark Evaluation', icon: BarChart2, badge: 'Audit' },
      { id: 'system_health', label: 'System Health & Telemetry', icon: Activity, badge: 'Live' },
    ] : [])
  ];

  const handleSelectSection = (id: string) => {
    setActiveSection(id);
    setSearchParams({ section: id });
  };

  // Security config
  const [secConfig, setSecConfig] = useState<SystemSecurityConfig | null>(null);
  const [sessions, setSessions] = useState<UserSession[]>([]);
  const [backups, setBackups] = useState<BackupRecord[]>([]);
  const [loadingSec, setLoadingSec] = useState(false);
  const [actionMsg, setActionMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // 2FA Setup Modal State
  const [is2FAModalOpen, setIs2FAModalOpen] = useState(false);
  const [setup2FAData, setSetup2FAData] = useState<TwoFactorSetupResponse | null>(null);
  const [verificationCode, setVerificationCode] = useState('');
  const [copiedCodes, setCopiedCodes] = useState(false);
  const [disablePassword, setDisablePassword] = useState('');
  const [isDisableModalOpen, setIsDisableModalOpen] = useState(false);

  // Load initial settings
  useEffect(() => {
    loadSettings();
    loadSessions();
    if (isAdmin) {
      loadBackups();
    }
  }, [isAdmin]);

  const loadSettings = async () => {
    try {
      setLoadingSec(true);
      const cfg = await securityAdminService.getSecuritySettings();
      setSecConfig(cfg);
    } catch (e: any) {
      console.warn('Could not load security config:', e);
    } finally {
      setLoadingSec(false);
    }
  };

  const loadSessions = async () => {
    try {
      const sessList = await securityAdminService.getActiveSessions();
      setSessions(sessList);
    } catch (e) {
      console.warn('Could not load active sessions:', e);
    }
  };

  const loadBackups = async () => {
    try {
      const bkList = await securityAdminService.getBackups();
      setBackups(bkList);
    } catch (e) {
      console.warn('Could not load backups:', e);
    }
  };

  const handleUpdateSecConfig = async (partial: Partial<SystemSecurityConfig>) => {
    try {
      const updated = await securityAdminService.updateSecuritySettings(partial);
      setSecConfig(updated);
      setActionMsg({ type: 'success', text: 'Security configuration saved successfully.' });
      setTimeout(() => setActionMsg(null), 4000);
    } catch (e: any) {
      setActionMsg({ type: 'error', text: e.message || 'Failed to update configuration.' });
    }
  };

  const handleStart2FASetup = async () => {
    try {
      const setup = await securityAdminService.setup2FA();
      setSetup2FAData(setup);
      setIs2FAModalOpen(true);
      setVerificationCode('');
      setCopiedCodes(false);
    } catch (e: any) {
      setActionMsg({ type: 'error', text: e.message || 'Failed to initialize 2FA setup.' });
    }
  };

  const handleConfirm2FA = async () => {
    if (!setup2FAData || !verificationCode) return;
    try {
      await securityAdminService.verifyAndEnable2FA(verificationCode, setup2FAData.secret);
      setIs2FAModalOpen(false);
      setSetup2FAData(null);
      setActionMsg({ type: 'success', text: 'Two-Factor Authentication activated successfully!' });
      setTimeout(() => setActionMsg(null), 5000);
      window.location.reload();
    } catch (e: any) {
      setActionMsg({ type: 'error', text: e.message || 'Invalid verification code.' });
    }
  };

  const handleDisable2FA = async () => {
    if (!disablePassword) return;
    try {
      await securityAdminService.disable2FA(disablePassword);
      setIsDisableModalOpen(false);
      setDisablePassword('');
      setActionMsg({ type: 'success', text: 'Two-Factor Authentication disabled.' });
      setTimeout(() => setActionMsg(null), 4000);
      window.location.reload();
    } catch (e: any) {
      setActionMsg({ type: 'error', text: e.message || 'Password incorrect.' });
    }
  };

  const handleRevokeSession = async (sessionId: number) => {
    try {
      await securityAdminService.revokeSession(sessionId);
      await loadSessions();
      setActionMsg({ type: 'success', text: 'Session revoked successfully.' });
      setTimeout(() => setActionMsg(null), 3000);
    } catch (e: any) {
      setActionMsg({ type: 'error', text: e.message || 'Failed to revoke session.' });
    }
  };

  const handleRevokeOtherSessions = async () => {
    try {
      await securityAdminService.revokeOtherSessions();
      await loadSessions();
      setActionMsg({ type: 'success', text: 'All other sessions have been logged out.' });
      setTimeout(() => setActionMsg(null), 3000);
    } catch (e: any) {
      setActionMsg({ type: 'error', text: e.message || 'Failed to revoke sessions.' });
    }
  };

  const handleCreateBackup = async () => {
    try {
      setActionMsg({ type: 'success', text: 'Snapshot backup creation in progress...' });
      const rec = await securityAdminService.createBackup();
      await loadBackups();
      setActionMsg({ type: 'success', text: `Backup ${rec.file_name} created successfully.` });
      setTimeout(() => setActionMsg(null), 4000);
    } catch (e: any) {
      setActionMsg({ type: 'error', text: e.message || 'Backup creation failed.' });
    }
  };

  const handleRunRestoreTest = async (backupId: number) => {
    try {
      setActionMsg({ type: 'success', text: 'Testing sandbox restore and running PRAGMA integrity_check...' });
      await securityAdminService.verifyBackupRestore(backupId);
      await loadBackups();
      setActionMsg({ type: 'success', text: 'Sandbox restore test passed with 100% database integrity!' });
      setTimeout(() => setActionMsg(null), 4000);
    } catch (e: any) {
      setActionMsg({ type: 'error', text: e.message || 'Restore verification failed.' });
    }
  };

  return (
    <div className="space-y-6 pb-20">
      <div>
        <h1 className="text-3xl font-bold text-white mb-1">System & Security Settings</h1>
        <p className="text-sm text-text-muted">
          Configure offline private models, air-gap firewalls, two-factor authentication, database encryption and automated backups.
        </p>
      </div>

      {actionMsg && (
        <div className={cn(
          "p-4 rounded-xl text-sm flex items-center justify-between border animate-in fade-in duration-200",
          actionMsg.type === 'success' 
            ? "bg-emerald-950/40 text-emerald-300 border-emerald-800/60" 
            : "bg-red-950/40 text-red-300 border-red-800/60"
        )}>
          <div className="flex items-center gap-2">
            {actionMsg.type === 'success' ? <CheckCircle2 className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
            <span>{actionMsg.text}</span>
          </div>
          <button onClick={() => setActionMsg(null)} className="text-xs text-text-muted hover:text-white">Dismiss</button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Navigation Sidebar */}
        <Card className="lg:col-span-1 h-fit">
          <CardContent className="p-2">
            <nav className="space-y-1">
              {sections.map(s => (
                <button
                  key={s.id}
                  onClick={() => handleSelectSection(s.id)}
                  className={cn(
                    'w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition-colors text-left cursor-pointer',
                    activeSection === s.id
                      ? 'bg-[#d93829] text-white shadow-xs'
                      : 'text-[#6e665d] hover:bg-[#faf7f2] hover:text-[#191410]'
                  )}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <s.icon className={cn("w-4 h-4 shrink-0", activeSection === s.id ? "text-white" : "text-[#8c8276]")} />
                    <span className="truncate">{s.label}</span>
                  </div>
                  {(s as any).badge && (
                    <span className={cn(
                      "text-[9px] font-mono px-1.5 py-0.5 rounded-full shrink-0 font-bold uppercase",
                      activeSection === s.id ? "bg-white/20 text-white" : "bg-[#f0ebe1] text-[#6e665d]"
                    )}>
                      {(s as any).badge}
                    </span>
                  )}
                </button>
              ))}
            </nav>
          </CardContent>
        </Card>

        {/* Content Pane */}
        <div className="lg:col-span-3 space-y-6">

          {/* SECTION 1: PROFILE */}
          {activeSection === 'profile' && (
            <Card>
              <CardHeader><CardTitle>Forensic Officer Profile</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-text-muted uppercase font-bold mb-1.5 block">Full Name</label>
                    <input type="text" readOnly value={user?.full_name || 'Investigator'} className="w-full px-3 py-2.5 bg-surface border border-border rounded-lg text-sm text-white focus:outline-none" />
                  </div>
                  <div>
                    <label className="text-xs text-text-muted uppercase font-bold mb-1.5 block">Email Address</label>
                    <input type="email" readOnly value={user?.email || ''} className="w-full px-3 py-2.5 bg-surface border border-border rounded-lg text-sm text-white focus:outline-none" />
                  </div>
                  <div>
                    <label className="text-xs text-text-muted uppercase font-bold mb-1.5 block">Role & Authority</label>
                    <input type="text" readOnly value={user?.role || 'analyst'} className="w-full px-3 py-2.5 bg-surface border border-border rounded-lg text-sm text-white uppercase focus:outline-none" />
                  </div>
                  <div>
                    <label className="text-xs text-text-muted uppercase font-bold mb-1.5 block">Badge Identifier</label>
                    <input type="text" readOnly value={user?.badge_number || 'OFFICER-001'} className="w-full px-3 py-2.5 bg-surface border border-border rounded-lg text-sm text-white focus:outline-none font-mono" />
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* SECTION 2: SECURITY & 2FA & ACTIVE SESSIONS */}
          {activeSection === 'security' && (
            <>
              {/* 2FA Card */}
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        <Smartphone className="w-5 h-5 text-primary" />
                        Two-Factor Authentication (2FA)
                      </CardTitle>
                      <p className="text-xs text-text-muted mt-1">
                        Protects official access using RFC 6238 Time-based One-Time Passwords (TOTP) and single-use emergency backup recovery codes.
                      </p>
                    </div>
                    {user?.is_2fa_enabled ? (
                      <span className="px-3 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-bold rounded-full flex items-center gap-1.5">
                        <ShieldCheck className="w-3.5 h-3.5" />
                        Active & Protected
                      </span>
                    ) : (
                      <span className="px-3 py-1 bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-bold rounded-full flex items-center gap-1.5">
                        <ShieldAlert className="w-3.5 h-3.5" />
                        Not Enabled
                      </span>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {user?.is_2fa_enabled ? (
                    <div className="p-4 rounded-xl bg-surface/50 border border-border flex items-center justify-between">
                      <div className="space-y-1">
                        <div className="text-sm font-semibold text-white">Authenticator App (TOTP) Active</div>
                        <div className="text-xs text-text-muted">
                          Your account requires a 6-digit TOTP code upon every sign in. 8 hashed backup recovery codes are stored at rest.
                        </div>
                      </div>
                      <button 
                        onClick={() => setIsDisableModalOpen(true)}
                        className="px-3.5 py-2 bg-red-950/40 hover:bg-red-900/60 border border-red-800/80 text-red-300 rounded-lg text-xs font-semibold transition-all cursor-pointer"
                      >
                        Disable 2FA
                      </button>
                    </div>
                  ) : (
                    <div className="p-4 rounded-xl bg-surface/50 border border-border flex items-center justify-between">
                      <div className="space-y-1">
                        <div className="text-sm font-semibold text-white">Activate Authenticator App</div>
                        <div className="text-xs text-text-muted">
                          Compatible with Google Authenticator, Microsoft Authenticator, Aegis, and 1Password.
                        </div>
                      </div>
                      <button 
                        onClick={handleStart2FASetup}
                        className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover font-semibold text-xs transition-all shadow-sm cursor-pointer"
                      >
                        Set Up 2FA
                      </button>
                    </div>
                  )}

                  {/* Field Encryption Notice */}
                  <div className="p-3.5 rounded-xl bg-cyan-950/20 border border-cyan-800/40 text-xs text-cyan-300 flex items-start gap-3">
                    <Lock className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold">Field-Level Encryption at Rest: </span>
                      All TOTP secrets, recovery codes, suspect profiling notes, and prior criminal history records are stored encrypted in the database using <strong>AES-256-GCM</strong> authenticated encryption. Prior records are strictly restricted by role under Section 54 IEA safeguards.
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Shorter Sessions & Active Session List */}
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        <Lock className="w-5 h-5 text-primary" />
                        Active Investigator Sessions & Auto-Revocation
                      </CardTitle>
                      <p className="text-xs text-text-muted mt-1">
                        Sessions automatically expire in 15 minutes of inactivity. Remote session revocation is enforced via cryptographic token revocation ledgers.
                      </p>
                    </div>
                    {sessions.length > 1 && (
                      <button 
                        onClick={handleRevokeOtherSessions}
                        className="px-3 py-1.5 bg-surface border border-red-800/60 text-red-400 hover:bg-red-950/40 rounded-lg text-xs font-semibold transition-all cursor-pointer"
                      >
                        Revoke All Other Sessions
                      </button>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {sessions.length === 0 ? (
                    <div className="text-xs text-text-muted text-center py-4">No active sessions found.</div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-border/80 text-text-muted">
                            <th className="py-2 px-3">Device / Platform</th>
                            <th className="py-2 px-3">IP Address</th>
                            <th className="py-2 px-3">Created</th>
                            <th className="py-2 px-3">Expires</th>
                            <th className="py-2 px-3 text-right">Action</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border/40">
                          {sessions.map((s, idx) => (
                            <tr key={s.id} className="hover:bg-surface/40 transition-colors">
                              <td className="py-3 px-3">
                                <div className="font-medium text-white flex items-center gap-2">
                                  <span>{s.device_info}</span>
                                  {idx === 0 && (
                                    <span className="px-1.5 py-0.5 bg-emerald-500/20 text-emerald-300 text-[10px] rounded font-bold">
                                      Current
                                    </span>
                                  )}
                                </div>
                                <div className="text-[10px] text-text-muted truncate max-w-xs">{s.user_agent}</div>
                              </td>
                              <td className="py-3 px-3 font-mono text-text-muted">{s.ip_address || '127.0.0.1'}</td>
                              <td className="py-3 px-3 text-text-muted">{new Date(s.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                              <td className="py-3 px-3 text-text-muted">{new Date(s.expires_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                              <td className="py-3 px-3 text-right">
                                <button
                                  onClick={() => handleRevokeSession(s.id)}
                                  className="text-red-400 hover:text-red-300 font-semibold text-xs px-2 py-1 rounded bg-red-950/30 hover:bg-red-900/50 transition-colors cursor-pointer"
                                >
                                  Revoke
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>
            </>
          )}

          {/* SECTION 3: AI & PRIVATE MODELS */}
          {activeSection === 'ai_models' && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Cpu className="w-5 h-5 text-primary" />
                      Private Model & Air-Gap Configuration
                    </CardTitle>
                    <p className="text-xs text-text-muted mt-1">
                      Choose between Cloud Gemini or locally hosted Ollama/vLLM inference engines. Total air-gap switches guarantee no data ever leaves the secure enclave.
                    </p>
                  </div>
                  {secConfig?.block_external_ai_globally ? (
                    <span className="px-3 py-1 bg-red-500/10 border border-red-500/40 text-red-400 text-xs font-bold rounded-full flex items-center gap-1.5">
                      <ShieldAlert className="w-3.5 h-3.5" />
                      AIR-GAP ENGAGED (Cloud Blocked)
                    </span>
                  ) : (
                    <span className="px-3 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-bold rounded-full flex items-center gap-1.5">
                      <Server className="w-3.5 h-3.5" />
                      Hybrid / Local Available
                    </span>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-5">
                {/* Global Air-Gap Kill Switch */}
                <div className="p-4 rounded-xl bg-surface/60 border border-border flex items-center justify-between">
                  <div className="space-y-1 max-w-xl">
                    <div className="text-sm font-bold text-white flex items-center gap-2">
                      <ShieldAlert className="w-4 h-4 text-red-400" />
                      Global Air-Gap Firewall Kill-Switch
                    </div>
                    <div className="text-xs text-text-muted leading-relaxed">
                      When enabled, all external cloud AI API calls are completely blocked across the entire platform. Every case will strictly run through locally hosted models or local deterministic heuristics.
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input 
                      type="checkbox"
                      checked={secConfig?.block_external_ai_globally || false}
                      onChange={(e) => handleUpdateSecConfig({ block_external_ai_globally: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-surface-hover peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-600"></div>
                  </label>
                </div>

                {/* AI Provider Selector */}
                <div className="space-y-2">
                  <label className="text-xs text-text-muted uppercase font-bold block">
                    Default AI Inference Engine
                  </label>
                  <select
                    value={secConfig?.default_ai_provider || 'cloud_gemini'}
                    onChange={(e) => handleUpdateSecConfig({ default_ai_provider: e.target.value as any })}
                    disabled={secConfig?.block_external_ai_globally}
                    className="w-full px-3 py-2.5 bg-surface border border-border rounded-lg text-sm text-white focus:outline-none focus:border-primary disabled:opacity-50"
                  >
                    <option value="cloud_gemini">Cloud Gemini API (Default Cloud Intelligence)</option>
                    <option value="local_ollama">Local Ollama (Self-Hosted On-Premises)</option>
                    <option value="local_vllm">Local vLLM (High-Throughput Offline Server)</option>
                    <option value="custom_local">Custom Local OpenAI-Compatible Server</option>
                  </select>
                </div>

                {/* Local Endpoint & Model */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-text-muted uppercase font-bold mb-1.5 block">
                      Local AI Endpoint URL
                    </label>
                    <input 
                      type="text"
                      defaultValue={secConfig?.local_ai_endpoint || 'http://localhost:11434/v1'}
                      onBlur={(e) => handleUpdateSecConfig({ local_ai_endpoint: e.target.value })}
                      placeholder="http://localhost:11434/v1"
                      className="w-full px-3 py-2.5 bg-surface border border-border rounded-lg text-sm text-white focus:outline-none focus:border-primary font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-text-muted uppercase font-bold mb-1.5 block">
                      Local AI Model Identifier
                    </label>
                    <input 
                      type="text"
                      defaultValue={secConfig?.local_ai_model || 'mistral'}
                      onBlur={(e) => handleUpdateSecConfig({ local_ai_model: e.target.value })}
                      placeholder="e.g. mistral, llama3, deepseek-r1"
                      className="w-full px-3 py-2.5 bg-surface border border-border rounded-lg text-sm text-white focus:outline-none focus:border-primary font-mono"
                    />
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-surface/40 border border-border text-xs text-text-muted space-y-1">
                  <div className="font-semibold text-white">Sensitive Case Air-Gap Switch:</div>
                  <div>
                    Individual cases can also be designated <strong>Air-Gapped</strong> independently from the Case Overview screen. When a case is toggled as sensitive, external AI calls for that case are permanently blocked, even if global cloud access is permitted.
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* SECTION 4: STORAGE, RETENTION & RESTORE TESTING */}
          {activeSection === 'storage' && (
            <>
              {/* Backups & Restore Tests */}
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        <HardDrive className="w-5 h-5 text-primary" />
                        Automated Backups & Sandbox Restore Tests
                      </CardTitle>
                      <p className="text-xs text-text-muted mt-1">
                        Generates SHA-256 verified forensic snapshots. Automated restore tests execute PRAGMA integrity_check and table sanity counts in isolated sandboxes.
                      </p>
                    </div>
                    {isAdmin && (
                      <button
                        onClick={handleCreateBackup}
                        className="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm cursor-pointer"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                        Create Snapshot Backup Now
                      </button>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {backups.length === 0 ? (
                    <div className="text-xs text-text-muted text-center py-6">
                      No automated snapshots created yet. Click "Create Snapshot Backup Now" above.
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-border/80 text-text-muted">
                            <th className="py-2 px-3">Snapshot File</th>
                            <th className="py-2 px-3">Size</th>
                            <th className="py-2 px-3">SHA-256 Digest</th>
                            <th className="py-2 px-3">Restore Test Status</th>
                            <th className="py-2 px-3 text-right">Sandbox Test</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border/40">
                          {backups.map(bk => (
                            <tr key={bk.id} className="hover:bg-surface/40 transition-colors">
                              <td className="py-3 px-3 font-medium text-white">
                                {bk.file_name}
                                <div className="text-[10px] text-text-muted">{new Date(bk.created_at).toLocaleString()}</div>
                              </td>
                              <td className="py-3 px-3 text-text-muted font-mono">
                                {(bk.file_size_bytes / 1024).toFixed(1)} KB
                              </td>
                              <td className="py-3 px-3 font-mono text-text-muted text-[11px]" title={bk.sha256_hash}>
                                {bk.sha256_hash.substring(0, 16)}...
                              </td>
                              <td className="py-3 px-3">
                                {bk.restore_test_status === 'passed' ? (
                                  <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded text-[11px] font-bold flex items-center gap-1 w-fit">
                                    <CheckCircle2 className="w-3 h-3" />
                                    Passed (PRAGMA OK)
                                  </span>
                                ) : bk.restore_test_status === 'in_progress' ? (
                                  <span className="px-2 py-0.5 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded text-[11px] font-bold flex items-center gap-1 w-fit">
                                    <RefreshCw className="w-3 h-3 animate-spin" />
                                    Verifying...
                                  </span>
                                ) : (
                                  <span className="px-2 py-0.5 bg-surface text-text-muted border border-border rounded text-[11px] font-bold w-fit block">
                                    Untested
                                  </span>
                                )}
                              </td>
                              <td className="py-3 px-3 text-right">
                                <button
                                  onClick={() => handleRunRestoreTest(bk.id)}
                                  className="px-2.5 py-1 bg-surface hover:bg-surface-hover border border-border rounded text-[11px] font-semibold text-white transition-colors cursor-pointer"
                                >
                                  Test Restore
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Retention & Legal-Hold Policies */}
              <Card>
                <CardHeader>
                  <CardTitle>Case Retention & Legal Hold Enforcement</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="p-4 rounded-xl bg-surface/50 border border-border space-y-2">
                    <div className="text-sm font-semibold text-white">Statutory Criminal Retention Period: 25 Years</div>
                    <div className="text-xs text-text-muted leading-relaxed">
                      By default under Indian criminal procedure rules, case records, digital forensic hashes, and chain of custody logs are scheduled for retention for 25 years from docket initiation.
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-800/40 text-xs text-amber-300 space-y-1.5">
                    <div className="font-bold flex items-center gap-1.5">
                      <Lock className="w-4 h-4 text-amber-400" />
                      Legal Hold Protection (HTTP 423 Locked)
                    </div>
                    <div>
                      When a case is placed under <strong>Legal Hold</strong>, all deletion and purging APIs are immediately disabled. Any attempt by investigators or administrators to delete the case or any attached exhibits is blocked with an immutable legal hold notification.
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          )}

          {/* SECTION 5: NOTIFICATIONS */}
          {activeSection === 'notifications' && (
            <Card>
              <CardHeader><CardTitle>Security & Alert Notifications</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {[
                  { label: 'Air-gap security breach attempts', desc: 'When external egress is blocked for a sensitive case', defaultOn: true },
                  { label: 'Two-Factor login alerts', desc: 'When your account logs in from a new device', defaultOn: true },
                  { label: 'Automated backup completion', desc: 'When scheduled database backup passes restore test', defaultOn: true },
                  { label: 'Legal hold placements', desc: 'When a supervisor places or releases a legal hold', defaultOn: true },
                ].map(pref => (
                  <div key={pref.label} className="flex items-center justify-between p-3 rounded-lg bg-surface/50 border border-border/50">
                    <div>
                      <div className="text-sm font-medium text-white">{pref.label}</div>
                      <div className="text-xs text-text-muted mt-0.5">{pref.desc}</div>
                    </div>
                    <div className="w-10 h-6 rounded-full relative cursor-pointer transition-colors bg-primary">
                      <div className="absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-all left-5" />
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* SECTION 6: SCORING CONFIGURATION (LEAD / ADMIN ONLY) */}
          {activeSection === 'scoring_config' && isLeadOrAdmin && (
            <div className="space-y-4">
              <div className="bg-[#faf7f2] border border-[#eae4d9] rounded-2xl p-4 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-serif font-bold text-[#191410]">Scoring Configuration & Forensic Likelihood Baselines</h2>
                  <p className="text-xs text-[#6e665d]">Adjust mathematical likelihood ratios, sensitivity bounds, and MMO prior weights.</p>
                </div>
                <span className="text-[10px] font-mono px-2.5 py-1 rounded-full font-bold uppercase bg-amber-50 text-amber-800 border border-amber-200">
                  Lead / Admin Authorized
                </span>
              </div>
              <ScoringConfiguration />
            </div>
          )}

          {/* SECTION 7: RESPONSIBLE USE & LEGAL LIMITS */}
          {activeSection === 'responsible_use' && isLeadOrAdmin && (
            <div className="space-y-4">
              <div className="bg-[#faf7f2] border border-[#eae4d9] rounded-2xl p-4 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-serif font-bold text-[#191410]">Responsible AI, Non-Verdict Disclaimers & Legal Limits</h2>
                  <p className="text-xs text-[#6e665d]">Section 54 IEA character evidence partitions and statutory non-verdict safeguards.</p>
                </div>
                <span className="text-[10px] font-mono px-2.5 py-1 rounded-full font-bold uppercase bg-blue-50 text-blue-800 border border-blue-200">
                  Statutory Rule
                </span>
              </div>
              <ResponsibleUse />
            </div>
          )}

          {/* SECTION 8: MODEL CARD */}
          {activeSection === 'model_card' && isLeadOrAdmin && (
            <div className="space-y-4">
              <div className="bg-[#faf7f2] border border-[#eae4d9] rounded-2xl p-4 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-serif font-bold text-[#191410]">Forensic AI Model Card & Architecture Specifications</h2>
                  <p className="text-xs text-[#6e665d]">Transparency documentation, intended use limits, latency profiles, and dataset provenance.</p>
                </div>
                <span className="text-[10px] font-mono px-2.5 py-1 rounded-full font-bold uppercase bg-purple-50 text-purple-800 border border-purple-200">
                  Model Card V2.4
                </span>
              </div>
              <ModelCard />
            </div>
          )}

          {/* SECTION 9: BENCHMARK EVALUATION */}
          {activeSection === 'evaluation' && isLeadOrAdmin && (
            <div className="space-y-4">
              <div className="bg-[#faf7f2] border border-[#eae4d9] rounded-2xl p-4 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-serif font-bold text-[#191410]">Algorithmic Benchmark Evaluation & Bias Audits</h2>
                  <p className="text-xs text-[#6e665d]">Empirical evaluation across 26 benchmark test cases, stress tests, and bias detection.</p>
                </div>
                <span className="text-[10px] font-mono px-2.5 py-1 rounded-full font-bold uppercase bg-emerald-50 text-emerald-800 border border-emerald-200">
                  Verification Suite
                </span>
              </div>
              <Evaluation />
            </div>
          )}

          {/* SECTION 10: SYSTEM HEALTH & TELEMETRY */}
          {activeSection === 'system_health' && isLeadOrAdmin && (
            <div className="space-y-4">
              <div className="bg-[#faf7f2] border border-[#eae4d9] rounded-2xl p-4 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-serif font-bold text-[#191410]">Live System Health, Workers & Disaster Recovery</h2>
                  <p className="text-xs text-[#6e665d]">Real-time queue congestion, AI latency diagnostics, and PRAGMA database snapshots.</p>
                </div>
                <span className="text-[10px] font-mono px-2.5 py-1 rounded-full font-bold uppercase bg-emerald-50 text-emerald-800 border border-emerald-200">
                  Operational
                </span>
              </div>
              <SystemHealth />
            </div>
          )}

        </div>
      </div>

      {/* 2FA SETUP MODAL */}
      {is2FAModalOpen && setup2FAData && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-[#eae4d9] rounded-2xl max-w-lg w-full p-6 space-y-5 text-[#191410] shadow-2xl animate-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-[#eae4d9] pb-3">
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-[#d93829]" />
                <h3 className="font-serif font-bold text-base text-[#191410]">Configure Two-Factor Authenticator</h3>
              </div>
              <button onClick={() => setIs2FAModalOpen(false)} className="text-[#6e665d] hover:text-[#191410] cursor-pointer">✕</button>
            </div>

            <div className="space-y-3 text-xs">
              <p className="text-[#6e665d]">
                Scan or enter this TOTP secret into Google Authenticator or 1Password:
              </p>
              
              <div className="p-3 bg-[#faf7f2] rounded-xl border border-[#eae4d9] font-mono text-center text-sm font-bold tracking-widest text-[#191410] select-all">
                {setup2FAData.secret}
              </div>

              {/* Recovery Backup Codes */}
              <div className="space-y-1.5 pt-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-[#191410]">Emergency Single-Use Backup Codes:</span>
                  <button 
                    onClick={() => {
                      navigator.clipboard.writeText(setup2FAData.backup_codes.join('\n'));
                      setCopiedCodes(true);
                      setTimeout(() => setCopiedCodes(false), 2000);
                    }}
                    className="text-[11px] text-[#d93829] hover:underline flex items-center gap-1 cursor-pointer font-semibold"
                  >
                    {copiedCodes ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedCodes ? 'Copied!' : 'Copy All'}</span>
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-1.5 p-2.5 bg-[#faf7f2] border border-[#eae4d9] rounded-xl font-mono text-[11px] text-[#191410]">
                  {setup2FAData.backup_codes.map((code, i) => (
                    <div key={i} className="text-center py-0.5 font-semibold">{code}</div>
                  ))}
                </div>
                <p className="text-[10px] text-[#8c8276]">
                  Keep these safe! Each backup code can be used once if you lose your phone.
                </p>
              </div>

              {/* Verification Code Input */}
              <div className="space-y-1.5 pt-2">
                <label className="font-bold text-[#191410] block">Enter 6-Digit Authenticator Code to Confirm:</label>
                <input
                  type="text"
                  autoFocus
                  maxLength={6}
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value.trim())}
                  placeholder="000000"
                  className="w-full px-3 py-2 bg-[#faf7f2] border border-[#eae4d9] rounded-xl text-center font-mono font-bold text-lg tracking-widest text-[#191410] focus:outline-none focus:border-[#d93829]"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-[#eae4d9]">
              <button
                onClick={() => setIs2FAModalOpen(false)}
                className="px-4 py-2 bg-white hover:bg-[#faf7f2] border border-[#eae4d9] rounded-xl text-xs font-semibold cursor-pointer text-[#6e665d]"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm2FA}
                disabled={verificationCode.length !== 6}
                className="px-5 py-2 bg-[#d93829] hover:bg-[#bf2b1d] disabled:opacity-50 text-white rounded-xl text-xs font-semibold cursor-pointer shadow-xs"
              >
                Verify & Activate 2FA
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 2FA DISABLE CONFIRM MODAL */}
      {isDisableModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-[#eae4d9] rounded-2xl max-w-sm w-full p-6 space-y-4 text-[#191410] shadow-2xl animate-in zoom-in-95">
            <h3 className="font-bold text-base text-red-700 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              Disable Two-Factor Authentication?
            </h3>
            <p className="text-xs text-[#6e665d]">
              Confirm your password to deactivate two-factor authentication and remove your TOTP secret.
            </p>
            <input
              type="password"
              placeholder="Confirm account password"
              value={disablePassword}
              onChange={(e) => setDisablePassword(e.target.value)}
              className="w-full px-3 py-2 bg-[#faf7f2] border border-[#eae4d9] rounded-xl text-xs text-[#191410] focus:outline-none focus:border-red-500"
            />
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setIsDisableModalOpen(false)}
                className="px-3 py-1.5 bg-white border border-[#eae4d9] text-[#6e665d] text-xs rounded-xl font-semibold cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleDisable2FA}
                className="px-4 py-1.5 bg-red-600 hover:bg-red-700 text-xs text-white rounded-xl font-semibold cursor-pointer shadow-xs"
              >
                Disable
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
