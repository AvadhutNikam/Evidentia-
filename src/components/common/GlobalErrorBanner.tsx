import React, { useState, useEffect, useRef } from 'react';
import { AlertTriangle, X, Play, RefreshCw, CheckCircle2 } from 'lucide-react';
import { ApiErrorEventDetail } from '../../services/apiClient';
import { API_BASE, isDemoMode, setDemoMode } from '../../config/api';

export function GlobalErrorBanner() {
  const [error, setError] = useState<ApiErrorEventDetail | null>(null);
  const [demoActive, setDemoActive] = useState<boolean>(isDemoMode());
  const [isRetrying, setIsRetrying] = useState<boolean>(false);
  const [reconnected, setReconnected] = useState<boolean>(false);
  const pollTimerRef = useRef<any>(null);

  const checkBackendHealth = async () => {
    setIsRetrying(true);
    try {
      const res = await fetch(`${API_BASE}/health?t=${Date.now()}`, { 
        method: 'GET',
        headers: { 'Cache-Control': 'no-cache' }
      });
      if (res.ok) {
        setReconnected(true);
        setTimeout(() => {
          setError(null);
          setReconnected(false);
        }, 1500);
        return true;
      }
    } catch {
      // Still offline
    } finally {
      setIsRetrying(false);
    }
    return false;
  };

  useEffect(() => {
    const handleApiError = (event: Event) => {
      const customEvent = event as CustomEvent<ApiErrorEventDetail>;
      setError(customEvent.detail);
    };

    const handleApiSuccess = () => {
      // Clear offline notice if any request successfully completed
      setError((prev) => (prev && prev.status === 0 ? null : prev));
    };

    const handleDemoChange = (event: Event) => {
      const customEvent = event as CustomEvent<{ enabled: boolean }>;
      setDemoActive(customEvent.detail.enabled);
      if (customEvent.detail.enabled) {
        setError(null);
      }
    };

    window.addEventListener('evidentia:api-error', handleApiError);
    window.addEventListener('evidentia:api-success', handleApiSuccess);
    window.addEventListener('evidentia:demo-mode-changed', handleDemoChange);

    return () => {
      window.removeEventListener('evidentia:api-error', handleApiError);
      window.removeEventListener('evidentia:api-success', handleApiSuccess);
      window.removeEventListener('evidentia:demo-mode-changed', handleDemoChange);
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, []);

  // When an offline error is active, poll /health every 3 seconds to auto-heal
  useEffect(() => {
    if (error && error.status === 0) {
      // Immediately run an initial check in case server just started
      checkBackendHealth().then((ok) => {
        if (ok && pollTimerRef.current) {
          clearInterval(pollTimerRef.current);
          pollTimerRef.current = null;
        }
      });

      pollTimerRef.current = setInterval(async () => {
        const ok = await checkBackendHealth();
        if (ok && pollTimerRef.current) {
          clearInterval(pollTimerRef.current);
          pollTimerRef.current = null;
        }
      }, 3000);
    } else {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    }

    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, [error]);

  if (reconnected) {
    return (
      <div
        role="status"
        className="bg-emerald-50 border-b border-emerald-200 px-4 py-2 text-emerald-800 flex items-center justify-between text-xs sticky top-0 z-50 shadow-xs animate-fadeIn"
      >
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span className="font-semibold">Backend Connection Restored</span>
          <span className="text-emerald-700">Server is online and responding at {API_BASE}.</span>
        </div>
      </div>
    );
  }

  if (!error) return null;

  return (
    <div
      role="alert"
      className="bg-[#fff4f2] border-b border-[#f5c6cb] px-4 py-2.5 text-[#721c24] flex flex-wrap items-center justify-between gap-3 shadow-xs sticky top-0 z-50 text-xs transition-all animate-fadeIn"
    >
      <div className="flex items-center gap-2.5 min-w-0">
        <div className="p-1 rounded-full bg-[#f8d7da] text-[#d93829] shrink-0">
          <AlertTriangle className="w-4 h-4" />
        </div>
        <div className="truncate">
          <span className="font-bold uppercase tracking-wider text-[10px] bg-[#d93829] text-white px-1.5 py-0.5 rounded-sm mr-2">
            {error.status ? `HTTP ${error.status}` : 'OFFLINE'}
          </span>
          <span className="font-semibold text-[#191410] mr-1.5">
            Backend Call Failed ({error.endpoint}):
          </span>
          <span className="text-[#59524c]">{error.message}</span>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0 ml-auto">
        <button
          onClick={() => checkBackendHealth()}
          disabled={isRetrying}
          className="flex items-center gap-1.5 px-2.5 py-1 bg-white hover:bg-[#faf7f2] border border-[#e2dcd2] text-[#3d3832] rounded-md text-[11px] font-semibold shadow-xs cursor-pointer transition-colors"
          title="Test backend connection"
        >
          <RefreshCw className={`w-3 h-3 ${isRetrying ? 'animate-spin text-[#d93829]' : 'text-[#70685e]'}`} />
          {isRetrying ? 'Checking...' : 'Retry Connection'}
        </button>

        {!demoActive && (
          <button
            onClick={() => {
              setDemoMode(true);
              setError(null);
            }}
            className="flex items-center gap-1.5 px-2.5 py-1 bg-amber-500 hover:bg-amber-600 text-white rounded-md text-[11px] font-bold shadow-xs cursor-pointer transition-colors"
          >
            <Play className="w-3 h-3 fill-current" />
            Enable Demo Mode
          </button>
        )}

        <button
          onClick={() => setError(null)}
          title="Dismiss Error Banner"
          className="p-1 rounded hover:bg-[#f5c6cb]/50 text-[#70685e] hover:text-[#191410] cursor-pointer transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
