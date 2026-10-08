import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, KeyRound, Lock, User, CheckCircle2, AlertCircle, ArrowRight, Sparkles } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export function Login() {
  const navigate = useNavigate();
  const { login, loginAsDemoRole, isLoading } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!email || !password) {
      setError('Please provide both official email and password.');
      return;
    }

    const success = await login(email, password);
    if (success) {
      navigate('/dashboard');
    } else {
      setError('Authentication failed. Check your credentials or lockout status.');
    }
  };

  const handleDemoSelect = async (role: 'admin' | 'lead_investigator' | 'analyst' | 'reviewer') => {
    setError(null);
    const success = await loginAsDemoRole(role);
    if (success) {
      navigate('/dashboard');
    }
  };

  return (
    <div className="min-h-screen bg-[#fcfaf7] flex flex-col justify-center py-12 sm:px-6 lg:px-8 selection:bg-[#d93829] selection:text-white">
      {/* Background Decor */}
      <div className="absolute inset-0 bg-[radial-gradient(#e5ddd0_1px,transparent_1px)] [background-size:24px_24px] opacity-40 pointer-events-none" />

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10 text-center space-y-3">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-[#d93829] to-[#eb5a4b] text-white shadow-lg shadow-[#d93829]/25">
          <Shield className="w-8 h-8 stroke-[2.2]" />
        </div>
        <div>
          <h2 className="text-2xl sm:text-3xl font-serif font-extrabold text-[#191410] tracking-tight">
            Evidentia AI
          </h2>
          <p className="text-xs uppercase tracking-widest text-[#d93829] font-bold font-sans mt-0.5">
            Forensic Intelligence & Access Control
          </p>
        </div>
        <p className="text-xs text-[#70685e] max-w-sm mx-auto">
          Sign in with official credentials or select a verified forensic role below to evaluate access isolation and RBAC.
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-xl relative z-10 px-4">
        <div className="bg-white py-8 px-6 sm:px-10 shadow-sm border border-[#eae4d9] rounded-3xl space-y-6">
          {/* Quick Demo Role Selector */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-[#999084] uppercase tracking-wider font-mono flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-[#d93829]" />
                Demo Role Fast Switcher (1-Click)
              </span>
              <span className="text-[10px] text-[#70685e]">Evaluation Mode</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {/* Admin Card */}
              <button
                type="button"
                onClick={() => handleDemoSelect('admin')}
                disabled={isLoading}
                className="p-3 rounded-xl border border-[#eae4d9] hover:border-[#d93829] hover:bg-[#fef8f6] transition-all text-left flex items-start gap-2.5 group cursor-pointer"
              >
                <div className="w-7 h-7 rounded-lg bg-[#fdeee9] text-[#d93829] flex items-center justify-center shrink-0 mt-0.5 group-hover:scale-110 transition-transform">
                  <Shield className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-bold text-[#191410] group-hover:text-[#d93829]">
                    Admin (All Cases)
                  </div>
                  <div className="text-[10px] text-[#70685e] line-clamp-1">
                    Superintendent S. Roy • IPS-9041
                  </div>
                  <div className="text-[9px] text-[#999084] font-mono mt-0.5">
                    Full user & case control
                  </div>
                </div>
              </button>

              {/* Lead Investigator Card */}
              <button
                type="button"
                onClick={() => handleDemoSelect('lead_investigator')}
                disabled={isLoading}
                className="p-3 rounded-xl border border-[#eae4d9] hover:border-[#1b64b8] hover:bg-[#f2f7fd] transition-all text-left flex items-start gap-2.5 group cursor-pointer"
              >
                <div className="w-7 h-7 rounded-lg bg-[#ebf4fd] text-[#1b64b8] flex items-center justify-center shrink-0 mt-0.5 group-hover:scale-110 transition-transform">
                  <User className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-bold text-[#191410] group-hover:text-[#1b64b8]">
                    Lead Investigator
                  </div>
                  <div className="text-[10px] text-[#70685e] line-clamp-1">
                    PI Vikram Salunkhe • CID-441
                  </div>
                  <div className="text-[9px] text-[#999084] font-mono mt-0.5">
                    Assigned cases authority
                  </div>
                </div>
              </button>

              {/* Forensic Analyst Card */}
              <button
                type="button"
                onClick={() => handleDemoSelect('analyst')}
                disabled={isLoading}
                className="p-3 rounded-xl border border-[#eae4d9] hover:border-[#6b38fb] hover:bg-[#f6f2ff] transition-all text-left flex items-start gap-2.5 group cursor-pointer"
              >
                <div className="w-7 h-7 rounded-lg bg-[#f0eaff] text-[#6b38fb] flex items-center justify-center shrink-0 mt-0.5 group-hover:scale-110 transition-transform">
                  <KeyRound className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-bold text-[#191410] group-hover:text-[#6b38fb]">
                    Forensic Analyst
                  </div>
                  <div className="text-[10px] text-[#70685e] line-clamp-1">
                    Dr. Ananya Sen • FSL-108
                  </div>
                  <div className="text-[9px] text-[#999084] font-mono mt-0.5">
                    Evidence upload & ACH run
                  </div>
                </div>
              </button>

              {/* Reviewer Card */}
              <button
                type="button"
                onClick={() => handleDemoSelect('reviewer')}
                disabled={isLoading}
                className="p-3 rounded-xl border border-[#eae4d9] hover:border-[#1b7a37] hover:bg-[#f2f9f4] transition-all text-left flex items-start gap-2.5 group cursor-pointer"
              >
                <div className="w-7 h-7 rounded-lg bg-[#ebf7ee] text-[#1b7a37] flex items-center justify-center shrink-0 mt-0.5 group-hover:scale-110 transition-transform">
                  <Lock className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-bold text-[#191410] group-hover:text-[#1b7a37]">
                    Judicial Reviewer
                  </div>
                  <div className="text-[10px] text-[#70685e] line-clamp-1">
                    Adv. Ramesh Sharma • Prosecutor
                  </div>
                  <div className="text-[9px] text-[#999084] font-mono mt-0.5">
                    Read-only (No edit/delete)
                  </div>
                </div>
              </button>
            </div>
          </div>

          <div className="relative flex py-1 items-center">
            <div className="flex-grow border-t border-[#eae4d9]" />
            <span className="flex-shrink mx-3 text-[10px] uppercase font-bold tracking-wider text-[#999084] font-mono">
              or sign in manually
            </span>
            <div className="flex-grow border-t border-[#eae4d9]" />
          </div>

          {error && (
            <div className="p-3.5 rounded-xl bg-[#fdeee9] border border-[#fbdcd5] text-xs text-[#d93829] flex items-center gap-2.5 animate-shake">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Standard Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-[#191410] mb-1.5">
                Official Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="e.g. analyst@evidentia.gov.in"
                className="w-full px-3.5 py-2.5 rounded-xl border border-[#eae4d9] bg-[#faf7f2]/50 text-xs text-[#191410] placeholder:text-[#999084] focus:outline-none focus:border-[#d93829] focus:bg-white transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-[#191410] mb-1.5">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-3.5 py-2.5 rounded-xl border border-[#eae4d9] bg-[#faf7f2]/50 text-xs text-[#191410] placeholder:text-[#999084] focus:outline-none focus:border-[#d93829] focus:bg-white transition-all font-mono"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 px-4 rounded-xl bg-[#d93829] hover:bg-[#c22e20] text-white text-xs font-semibold shadow-sm shadow-[#d93829]/25 flex items-center justify-center gap-2 transition-all disabled:opacity-50 cursor-pointer"
            >
              <span>{isLoading ? 'Verifying Credentials...' : 'Sign In to Investigation Suite'}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </form>

          {/* Security Notice */}
          <div className="pt-2 border-t border-[#eae4d9] text-center">
            <p className="text-[10px] text-[#999084] leading-relaxed">
              Protected by NIST SHA-256 Hashing, Bcrypt Salts & JWT Access Tokens.
              All actions logged under Section 65B Indian Evidence Act audit trails.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
export default Login;
