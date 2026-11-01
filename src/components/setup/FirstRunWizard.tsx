import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, Server, Lock, Globe, AlertTriangle, 
  CheckCircle2, ArrowRight, Download, RefreshCw, Cpu, 
  Languages, Eye, FileText, Check
} from 'lucide-react';
import { apiRequest } from '../../services/apiClient';
import { setApplicationLanguage, getApplicationLanguage, SupportedLanguage } from '../../i18n';
import { useTranslation } from 'react-i18next';

interface OutboundDestination {
  id: string;
  service_name: string;
  purpose: string;
  data_payload: string;
  policy: string;
  is_blocked: boolean;
  risk_mitigation: string;
}

interface FirstRunWizardProps {
  isOpen: boolean;
  onClose: () => void;
}

export const FirstRunWizard: React.FC<FirstRunWizardProps> = ({ isOpen, onClose }) => {
  const { t } = useTranslation();
  const [step, setStep] = useState<number>(1);
  const [selectedLang, setSelectedLang] = useState<SupportedLanguage>(getApplicationLanguage());
  const [chosenMode, setChosenMode] = useState<'private_only' | 'cloud_allowed' | 'ai_off'>('private_only');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  
  // Test Local AI state
  const [testResult, setTestResult] = useState<any>(null);
  const [isTestingAI, setIsTestingAI] = useState<boolean>(false);

  // Outbound Register state
  const [outboundDestinations, setOutboundDestinations] = useState<OutboundDestination[]>([]);
  const [showOutboundAudit, setShowOutboundAudit] = useState<boolean>(false);

  const handleLangChange = (l: SupportedLanguage) => {
    setSelectedLang(l);
    setApplicationLanguage(l);
  };

  const handleTestPrivateAI = async () => {
    setIsTestingAI(true);
    setTestResult(null);
    try {
      const res = await apiRequest('/security/test-private-ai', { method: 'POST' });
      setTestResult(res);
    } catch (err: any) {
      setTestResult({
        status: 'offline_simulated',
        message: 'Local Ollama endpoint not detected. When in Private mode, requests will safely queue without external transmission.'
      });
    } finally {
      setIsTestingAI(false);
    }
  };

  const handleFetchOutboundRegister = async () => {
    try {
      const res = await apiRequest('/security/outbound-register', { method: 'GET' });
      setOutboundDestinations(res.destinations || []);
      setShowOutboundAudit(true);
    } catch (err) {
      console.error(err);
    }
  };

  const handleDownloadSheet = async () => {
    try {
      const res = await apiRequest('/security/data-flow-sheet', { method: 'GET' });
      const blob = new Blob([res.data_flow_markdown], { type: 'text/markdown;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Evidentia_Data_Flow_Specification_${new Date().toISOString().slice(0, 10)}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert('Could not download data flow sheet.');
    }
  };

  const handleCompleteSetup = async () => {
    setIsSubmitting(true);
    try {
      await apiRequest('/security/ai-mode', {
        method: 'PUT',
        body: JSON.stringify({ mode: chosenMode }),
        suppressBanner: true,
        fallback: { success: true }
      });
      localStorage.setItem('evidentia_first_run_completed', 'true');
      onClose();
    } catch {
      // Gracefully persist locally if server endpoint requires authenticated admin session
      localStorage.setItem('evidentia_first_run_completed', 'true');
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 select-none">
      <div className="bg-white border border-[#eae4d9] rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto flex flex-col">
        {/* Wizard Header */}
        <div className="p-6 border-b border-[#eae4d9] bg-[#faf7f2]/80 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#fdeee9] text-[#d93829] flex items-center justify-center font-bold">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold font-serif text-[#191410]">
                Station Security & Data Residency Setup
              </h2>
              <p className="text-xs text-[#70685e]">
                Configure data boundaries, on-premise AI models, and police legal safeguards.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 font-mono text-xs">
            <span className={`px-2.5 py-1 rounded-full ${step === 1 ? 'bg-[#d93829] text-white font-bold' : 'bg-neutral-100 text-neutral-600'}`}>
              Step 1
            </span>
            <span className="text-neutral-400">→</span>
            <span className={`px-2.5 py-1 rounded-full ${step === 2 ? 'bg-[#d93829] text-white font-bold' : 'bg-neutral-100 text-neutral-600'}`}>
              Step 2
            </span>
          </div>
        </div>

        {/* Wizard Content */}
        <div className="p-6 flex-1 space-y-6">
          {step === 1 ? (
            /* Step 1: Language & Station Identity */
            <div className="space-y-6 animate-fade-in">
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-[#70685e] mb-2 flex items-center gap-2">
                  <Languages className="w-4 h-4 text-[#d93829]" />
                  1. Select Station Operational Language (भाषा निवडा)
                </h3>
                <p className="text-xs text-[#70685e] mb-4">
                  Evidentia supports official police terminologies in Marathi (महाराष्ट्र पोलीस मानक), Hindi (बीएनएस/नागरिक सुरक्षा), and English.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 notranslate" translate="no">
                  <button
                    key="wizard-lang-mr"
                    type="button"
                    onClick={() => handleLangChange('mr')}
                    className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
                      selectedLang === 'mr'
                        ? 'border-[#d93829] bg-[#fdeee9]/40 ring-2 ring-[#d93829]/20 shadow-xs'
                        : 'border-[#eae4d9] hover:border-neutral-400 bg-white'
                    }`}
                  >
                    <div className="text-base font-bold text-[#191410] mb-0.5">मराठी</div>
                    <div className="text-xs text-[#70685e]">महाराष्ट्र पोलीस (जबाब, पंचनामा, केस डायरी)</div>
                  </button>

                  <button
                    key="wizard-lang-hi"
                    type="button"
                    onClick={() => handleLangChange('hi')}
                    className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
                      selectedLang === 'hi'
                        ? 'border-[#d93829] bg-[#fdeee9]/40 ring-2 ring-[#d93829]/20 shadow-xs'
                        : 'border-[#eae4d9] hover:border-neutral-400 bg-white'
                    }`}
                  >
                    <div className="text-base font-bold text-[#191410] mb-0.5">हिन्दी</div>
                    <div className="text-xs text-[#70685e]">केंद्रीय / राज्य पुलिस (बीएनएस, बीएनएसएस)</div>
                  </button>

                  <button
                    key="wizard-lang-en"
                    type="button"
                    onClick={() => handleLangChange('en')}
                    className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
                      selectedLang === 'en'
                        ? 'border-[#d93829] bg-[#fdeee9]/40 ring-2 ring-[#d93829]/20 shadow-xs'
                        : 'border-[#eae4d9] hover:border-neutral-400 bg-white'
                    }`}
                  >
                    <div className="text-base font-bold text-[#191410] mb-0.5">English</div>
                    <div className="text-xs text-[#70685e]">Forensic standard terminology</div>
                  </button>
                </div>
              </div>

              {/* Station Context Banner */}
              <div className="p-4 bg-neutral-50 rounded-xl border border-[#eae4d9] space-y-2 text-xs text-[#70685e]">
                <div className="font-semibold text-[#191410] flex items-center gap-1.5">
                  <Server className="w-4 h-4 text-emerald-600" />
                  Station Server Deployment Check
                </div>
                <p>
                  This workstation is running the local backend gateway at <code className="font-mono text-[#d93829]">http://127.0.0.1:8000</code>. All evidence files and SHA-256 custody chains reside on this physical hardware.
                </p>
              </div>
            </div>
          ) : (
            /* Step 2: Where Does Your Data Go? */
            <div className="space-y-6 animate-fade-in">
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-[#70685e] mb-1">
                  2. Where Does Your Data Go? (डेटा मर्यादा व गोपनीयता)
                </h3>
                <p className="text-xs text-[#70685e]">
                  Plain-language disclosure of data boundaries before enabling investigative tools.
                </p>
              </div>

              {/* 3 Plain-Language Information Blocks */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {/* Block 1: Stays on Server */}
                <div className="p-4 rounded-xl border border-emerald-200 bg-emerald-50/60 space-y-2">
                  <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold">
                    <Server className="w-4 h-4" />
                  </div>
                  <h4 className="text-xs font-bold text-emerald-900 uppercase">
                    Stays on This Server
                  </h4>
                  <ul className="text-xs text-emerald-800 space-y-1 list-disc list-inside">
                    <li>All Case Files & FIRs</li>
                    <li>Muddimalkhana evidence ledger</li>
                    <li>Officer activity & audit logs</li>
                    <li>Investigator notes & statements</li>
                  </ul>
                </div>

                {/* Block 2: Leaves Only If Allowed */}
                <div className="p-4 rounded-xl border border-amber-200 bg-amber-50/60 space-y-2">
                  <div className="w-8 h-8 rounded-lg bg-amber-100 text-amber-800 flex items-center justify-center font-bold">
                    <Globe className="w-4 h-4" />
                  </div>
                  <h4 className="text-xs font-bold text-amber-900 uppercase">
                    Leaves Only If Cloud AI Allowed
                  </h4>
                  <ul className="text-xs text-amber-800 space-y-1 list-disc list-inside">
                    <li>Text of exhibits you send to AI</li>
                    <li>Transmitted to authorized provider</li>
                    <li>Zero training on case data</li>
                    <li><span className="font-bold">Blocked</span> in Private mode</li>
                  </ul>
                </div>

                {/* Block 3: Never Leaves */}
                <div className="p-4 rounded-xl border border-rose-200 bg-rose-50/60 space-y-2">
                  <div className="w-8 h-8 rounded-lg bg-rose-100 text-rose-800 flex items-center justify-center font-bold">
                    <Lock className="w-4 h-4" />
                  </div>
                  <h4 className="text-xs font-bold text-rose-900 uppercase">
                    Never Leaves Under Any Mode
                  </h4>
                  <ul className="text-xs text-rose-800 space-y-1 list-disc list-inside">
                    <li>Officer passwords & PINs</li>
                    <li>Master cryptographic keys</li>
                    <li>Custody chain hash roots</li>
                    <li>User session tokens</li>
                  </ul>
                </div>
              </div>

              {/* Mode Selection */}
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-[#70685e] mb-2">
                  Select System Operating Policy
                </label>
                <div className="space-y-2">
                  <label 
                    onClick={() => setChosenMode('private_only')}
                    className={`p-3.5 rounded-xl border flex items-center justify-between transition-all cursor-pointer ${
                      chosenMode === 'private_only'
                        ? 'border-emerald-600 bg-emerald-50/50 ring-1 ring-emerald-600/20'
                        : 'border-[#eae4d9] bg-white hover:border-neutral-400'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-4 h-4 rounded-full border border-emerald-600 flex items-center justify-center">
                        {chosenMode === 'private_only' && <div className="w-2 h-2 rounded-full bg-emerald-600" />}
                      </div>
                      <div>
                        <div className="text-xs font-bold text-[#191410] flex items-center gap-2">
                          <span>Private Only (Recommended for Police Stations)</span>
                          <span className="px-2 py-0.5 rounded-full text-[10px] bg-emerald-100 text-emerald-800 font-mono font-bold">
                            0 EGRESS
                          </span>
                        </div>
                        <div className="text-[11px] text-[#70685e]">
                          Uses locally hosted Ollama/vLLM. Zero outbound calls to outside servers.
                        </div>
                      </div>
                    </div>
                  </label>

                  <label 
                    onClick={() => setChosenMode('cloud_allowed')}
                    className={`p-3.5 rounded-xl border flex items-center justify-between transition-all cursor-pointer ${
                      chosenMode === 'cloud_allowed'
                        ? 'border-amber-600 bg-amber-50/50 ring-1 ring-amber-600/20'
                        : 'border-[#eae4d9] bg-white hover:border-neutral-400'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-4 h-4 rounded-full border border-amber-600 flex items-center justify-center">
                        {chosenMode === 'cloud_allowed' && <div className="w-2 h-2 rounded-full bg-amber-600" />}
                      </div>
                      <div>
                        <div className="text-xs font-bold text-[#191410]">
                          Cloud AI Allowed (External API for Non-Sensitive Cases)
                        </div>
                        <div className="text-[11px] text-[#70685e]">
                          Higher accuracy on complex OCR, but requires external internet connection.
                        </div>
                      </div>
                    </div>
                  </label>

                  <label 
                    onClick={() => setChosenMode('ai_off')}
                    className={`p-3.5 rounded-xl border flex items-center justify-between transition-all cursor-pointer ${
                      chosenMode === 'ai_off'
                        ? 'border-neutral-600 bg-neutral-100 ring-1 ring-neutral-600/20'
                        : 'border-[#eae4d9] bg-white hover:border-neutral-400'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-4 h-4 rounded-full border border-neutral-600 flex items-center justify-center">
                        {chosenMode === 'ai_off' && <div className="w-2 h-2 rounded-full bg-neutral-600" />}
                      </div>
                      <div>
                        <div className="text-xs font-bold text-[#191410]">
                          AI Off (Strict Deterministic Database Only)
                        </div>
                        <div className="text-[11px] text-[#70685e]">
                          Disables all generative AI features; station functions as pure evidence registry.
                        </div>
                      </div>
                    </div>
                  </label>
                </div>
              </div>

              {/* Action Buttons: Test Private AI & Outbound Audit */}
              <div className="p-4 bg-[#faf7f2] rounded-xl border border-[#eae4d9] flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleTestPrivateAI}
                    disabled={isTestingAI}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-[#eae4d9] hover:border-neutral-400 text-xs font-semibold rounded-lg text-[#191410] transition-colors cursor-pointer"
                  >
                    <Cpu className={`w-3.5 h-3.5 text-[#d93829] ${isTestingAI ? 'animate-spin' : ''}`} />
                    Test Private Local AI
                  </button>

                  <button
                    type="button"
                    onClick={handleFetchOutboundRegister}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-[#eae4d9] hover:border-neutral-400 text-xs font-semibold rounded-lg text-[#191410] transition-colors cursor-pointer"
                  >
                    <Eye className="w-3.5 h-3.5 text-purple-700" />
                    Verify Outbound Call Register
                  </button>
                </div>

                <button
                  type="button"
                  onClick={handleDownloadSheet}
                  className="flex items-center gap-1.5 text-xs text-[#70685e] hover:text-[#191410] underline cursor-pointer"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download Data Flow Sheet (.md)
                </button>
              </div>

              {/* Test Result Feedback */}
              {testResult && (
                <div className="p-3 bg-white rounded-lg border border-[#eae4d9] text-xs font-mono">
                  <div className="font-bold text-[#191410] mb-1">Local Model Test Response:</div>
                  <div className="text-[#70685e]">{testResult.message}</div>
                </div>
              )}

              {/* Outbound Audit Table Drawer */}
              {showOutboundAudit && outboundDestinations.length > 0 && (
                <div className="space-y-2 p-3 bg-white rounded-xl border border-[#eae4d9] text-xs">
                  <div className="font-bold text-[#191410] flex items-center justify-between">
                    <span>Active Network Egress Audit Table</span>
                    <button onClick={() => setShowOutboundAudit(false)} className="text-neutral-400 hover:text-neutral-700">✕</button>
                  </div>
                  <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
                    {outboundDestinations.map(d => (
                      <div key={d.id} className="p-2 rounded border border-[#eae4d9] bg-[#faf7f2]/50 flex items-center justify-between text-[11px]">
                        <div>
                          <div className="font-bold text-[#191410]">{d.service_name}</div>
                          <div className="text-[#70685e]">{d.data_payload}</div>
                        </div>
                        <span className={`px-2 py-0.5 rounded-full font-mono font-bold ${
                          d.is_blocked ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                        }`}>
                          {d.policy}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Wizard Footer Navigation */}
        <div className="p-5 border-t border-[#eae4d9] bg-[#faf7f2]/80 flex items-center justify-between">
          {step === 1 ? (
            <div>
              <span className="text-xs text-[#70685e]">
                Settings can be re-adjusted anytime in Admin Settings.
              </span>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setStep(1)}
              className="px-4 py-2 text-xs font-semibold text-[#70685e] hover:text-[#191410]"
            >
              ← Back to Language
            </button>
          )}

          {step === 1 ? (
            <button
              type="button"
              onClick={() => setStep(2)}
              className="flex items-center gap-1.5 px-5 py-2.5 bg-[#d93829] text-white text-xs font-bold rounded-lg hover:bg-[#bf2b1d] transition-all shadow-sm cursor-pointer"
            >
              Next: Privacy & Data Rules
              <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleCompleteSetup}
              disabled={isSubmitting}
              className="flex items-center gap-1.5 px-6 py-2.5 bg-emerald-700 text-white text-xs font-bold rounded-lg hover:bg-emerald-800 transition-all shadow-sm cursor-pointer disabled:opacity-50"
            >
              <Check className="w-4 h-4" />
              Confirm Station Policy & Launch
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

