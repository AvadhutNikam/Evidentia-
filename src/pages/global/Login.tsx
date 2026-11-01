import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Shield,
  KeyRound,
  Lock,
  User,
  AlertCircle,
  ArrowRight,
  Sparkles,
  Eye,
  EyeOff,
  Mail,
  CheckCircle2,
  LockKeyhole
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface DemoRoleConfig {
  role: 'admin' | 'lead_investigator' | 'analyst' | 'reviewer';
  label: string;
  badge: string;
  badgeColor: string;
  name: string;
  desc: string;
  borderColor: string;
  hoverBorder: string;
  iconBg: string;
  iconColor: string;
  icon: React.ComponentType<{ className?: string }>;
}

const DEMO_ROLES: DemoRoleConfig[] = [
  {
    role: 'admin',
    label: 'Admin (All Cases)',
    badge: 'SUPERUSER',
    badgeColor: 'bg-red-100 text-red-800 border-red-200',
    name: 'Superintendent S. Roy • IPS-9041',
    desc: 'Full user, case, and system control',
    borderColor: 'border-stone-200',
    hoverBorder: 'hover:border-red-500 hover:bg-red-50/40',
    iconBg: 'bg-red-100 text-red-600',
    iconColor: 'text-red-600',
    icon: Shield,
  },
  {
    role: 'lead_investigator',
    label: 'Lead Investigator',
    badge: 'CASE LEAD',
    badgeColor: 'bg-blue-100 text-blue-800 border-blue-200',
    name: 'PI Vikram Salunkhe • CID-441',
    desc: 'Assigned cases authority & case finalization',
    borderColor: 'border-stone-200',
    hoverBorder: 'hover:border-blue-500 hover:bg-blue-50/40',
    iconBg: 'bg-blue-100 text-blue-600',
    iconColor: 'text-blue-600',
    icon: User,
  },
  {
    role: 'analyst',
    label: 'Forensic Analyst',
    badge: 'ACH & EXHIBITS',
    badgeColor: 'bg-purple-100 text-purple-800 border-purple-200',
    name: 'Dr. Ananya Sen • FSL-108',
    desc: 'Evidence upload, NLI & Bayesian ACH run',
    borderColor: 'border-stone-200',
    hoverBorder: 'hover:border-purple-500 hover:bg-purple-50/40',
    iconBg: 'bg-purple-100 text-purple-600',
    iconColor: 'text-purple-600',
    icon: KeyRound,
  },
  {
    role: 'reviewer',
    label: 'Judicial Reviewer',
    badge: 'READ-ONLY',
    badgeColor: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    name: 'Adv. Ramesh Sharma • Prosecutor',
    desc: 'Read-only docket inspection (No edits/deletes)',
    borderColor: 'border-stone-200',
    hoverBorder: 'hover:border-emerald-500 hover:bg-emerald-50/40',
    iconBg: 'bg-emerald-100 text-emerald-600',
    iconColor: 'text-emerald-600',
    icon: Lock,
  },
];

export function Login() {
  const navigate = useNavigate();
  const { login, complete2FA, loginAsDemoRole, isLoading } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeDemoRole, setActiveDemoRole] = useState<string | null>(null);

  // 2FA state
  const [requires2FA, setRequires2FA] = useState(false);
  const [tempToken, setTempToken] = useState('');
  const [twoFactorCode, setTwoFactorCode] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!email.trim() || !password) {
      setError('Please provide both official email address and password.');
      return;
    }

    const res = await login(email.trim(), password);
    if (res.success) {
      navigate('/dashboard');
    } else if (res.requires2FA && res.tempToken) {
      setRequires2FA(true);
      setTempToken(res.tempToken);
      setError(null);
    } else {
      setError(res.error || 'Authentication failed. Please verify credentials or account status.');
    }
  };

  const handle2FASubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!twoFactorCode.trim()) {
      setError('Please enter your 6-digit TOTP code or emergency backup recovery code.');
      return;
    }

    const res = await complete2FA(tempToken, twoFactorCode.trim());
    if (res.success) {
      navigate('/dashboard');
    } else {
      setError(res.error || 'Invalid 2FA code. Please verify and try again.');
    }
  };

  const handleDemoSelect = async (role: 'admin' | 'lead_investigator' | 'analyst' | 'reviewer') => {
    setError(null);
    setRequires2FA(false);
    setActiveDemoRole(role);
    try {
      const success = await loginAsDemoRole(role);
      if (success) {
        navigate('/dashboard');
      }
    } finally {
      setActiveDemoRole(null);
    }
  };

  const prefillAccount = (fillEmail: string, fillPass: string) => {
    setEmail(fillEmail);
    setPassword(fillPass);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-[#faf7f2] flex flex-col justify-center py-10 sm:py-16 px-4 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Background Subtle Forensic Pattern */}
      <div
        className="absolute inset-0 bg-[radial-gradient(#ded7cb_1px,transparent_1px)] [background-size:24px_24px] opacity-60 pointer-events-none"
        aria-hidden="true"
      />

      {/* Header / Brand */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10 text-center space-y-3 mb-6">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-[#d93829] to-[#eb5a4b] text-white shadow-lg shadow-red-900/20">
          <Shield className="w-8 h-8 stroke-[2.2] text-white" />
        </div>

        <div>
          <h1 className="text-3xl font-serif font-extrabold text-stone-900 tracking-tight">
            Evidentia AI
          </h1>
          <p className="text-[11px] uppercase tracking-widest text-red-700 font-bold font-mono mt-1">
            Forensic Intelligence & Access Control
          </p>
        </div>

        <p className="text-xs text-stone-600 max-w-sm mx-auto leading-relaxed">
          Sign in with official credentials or select a verified test role below to evaluate access isolation and RBAC.
        </p>
      </div>

      {/* Main Authentication Card */}
      <div className="sm:mx-auto sm:w-full sm:max-w-xl relative z-10">
        <div className="bg-white py-8 px-6 sm:px-10 shadow-md shadow-stone-200/50 border border-stone-200/90 rounded-2xl space-y-6">
          {/* Quick Demo Role Selector */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-stone-800 uppercase tracking-wider font-mono flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-red-600" />
                Demo Role Fast Switcher (1-Click)
              </span>
              <span className="text-[11px] font-medium text-stone-500 bg-stone-100 px-2 py-0.5 rounded-full border border-stone-200">
                Evaluation Mode
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {DEMO_ROLES.map((d) => {
                const IconComponent = d.icon;
                const isCurrentLoading = isLoading && activeDemoRole === d.role;

                return (
                  <button
                    key={d.role}
                    type="button"
                    onClick={() => handleDemoSelect(d.role)}
                    disabled={isLoading}
                    className={`p-3.5 rounded-xl border ${d.borderColor} ${d.hoverBorder} transition-all text-left flex items-start gap-3 group cursor-pointer bg-white hover:shadow-xs relative`}
                  >
                    <div
                      className={`w-8 h-8 rounded-lg ${d.iconBg} flex items-center justify-center shrink-0 mt-0.5 group-hover:scale-105 transition-transform`}
                    >
                      <IconComponent className={`w-4 h-4 ${d.iconColor}`} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-1">
                        <span className="text-xs font-bold text-stone-900 group-hover:text-red-700 transition-colors">
                          {d.label}
                        </span>
                        <span
                          className={`text-[9px] font-mono font-bold uppercase px-1.5 py-0.2 rounded border ${d.badgeColor}`}
                        >
                          {d.badge}
                        </span>
                      </div>
                      <div className="text-[11px] text-stone-600 font-medium line-clamp-1 mt-0.5">
                        {d.name}
                      </div>
                      <div className="text-[10px] text-stone-500 line-clamp-1 mt-0.5">
                        {d.desc}
                      </div>
                    </div>

                    {isCurrentLoading && (
                      <div className="absolute inset-0 bg-white/70 backdrop-blur-xs rounded-xl flex items-center justify-center">
                        <div className="w-4 h-4 border-2 border-red-600 border-t-transparent rounded-full animate-spin" />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Divider */}
          <div className="relative flex py-1 items-center">
            <div className="flex-grow border-t border-stone-200" />
            <span className="flex-shrink mx-3 text-[11px] uppercase font-bold tracking-wider text-stone-600 font-mono">
              or sign in manually
            </span>
            <div className="flex-grow border-t border-stone-200" />
          </div>

          {/* Error Banner */}
          {error && (
            <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 flex items-start gap-2.5 animate-shake">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-600 mt-0.5" />
              <span className="font-medium">{error}</span>
            </div>
          )}

          {requires2FA ? (
            /* 2FA Challenge Form */
            <form onSubmit={handle2FASubmit} className="space-y-4">
              <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-xs flex items-start gap-3">
                <LockKeyhole className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold text-amber-900">
                    Two-Factor Authentication Required
                  </div>
                  <div className="text-[11px] text-amber-800 mt-0.5 leading-relaxed">
                    Enter the 6-digit TOTP verification code from your authenticator app (Google Authenticator, Microsoft Authenticator) or an 8-character emergency backup recovery code.
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-stone-800 mb-1.5">
                  Verification Code or Emergency Recovery Code
                </label>
                <input
                  type="text"
                  autoFocus
                  value={twoFactorCode}
                  onChange={(e) => setTwoFactorCode(e.target.value.trim())}
                  placeholder="e.g. 123456 or a1b2c3d4"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-stone-300 bg-stone-50 text-stone-900 text-base text-center tracking-widest font-mono placeholder:tracking-normal placeholder:text-xs placeholder:text-stone-400 focus:outline-none focus:border-red-600 focus:bg-white focus:ring-2 focus:ring-red-600/10 transition-all font-bold"
                />
              </div>

              <div className="flex gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => {
                    setRequires2FA(false);
                    setTempToken('');
                    setTwoFactorCode('');
                    setError(null);
                  }}
                  className="w-1/3 py-2.5 px-3 rounded-xl border border-stone-300 text-stone-700 hover:bg-stone-50 text-xs font-semibold transition-all cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-2/3 py-2.5 px-4 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-semibold shadow-xs flex items-center justify-center gap-2 transition-all disabled:opacity-50 cursor-pointer"
                >
                  <span>{isLoading ? 'Verifying...' : 'Verify & Continue'}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </form>
          ) : (
            /* Standard Manual Login Form */
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-bold text-stone-800">
                    Official Email Address
                  </label>
                  <button
                    type="button"
                    onClick={() => prefillAccount('admin@evidentia.gov.in', 'Password123!')}
                    className="text-[11px] text-red-700 hover:text-red-800 font-semibold cursor-pointer hover:underline"
                  >
                    Use Admin Login
                  </button>
                </div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-stone-500">
                    <Mail className="w-4 h-4" />
                  </div>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="e.g. admin@evidentia.gov.in"
                    className="w-full pl-9 pr-3.5 py-2.5 rounded-xl border border-stone-300 bg-stone-50 text-xs text-stone-900 placeholder:text-stone-500 focus:outline-none focus:border-red-600 focus:bg-white focus:ring-2 focus:ring-red-600/10 transition-all font-medium"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-bold text-stone-800">
                    Password
                  </label>
                  <span className="text-[10px] text-stone-500 font-mono">
                    Default: Password123!
                  </span>
                </div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-stone-500">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-9 pr-10 py-2.5 rounded-xl border border-stone-300 bg-stone-50 text-xs text-stone-900 placeholder:text-stone-500 focus:outline-none focus:border-red-600 focus:bg-white focus:ring-2 focus:ring-red-600/10 transition-all font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-stone-500 hover:text-stone-800 transition-colors cursor-pointer"
                    title={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2.5 px-4 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-semibold shadow-sm flex items-center justify-center gap-2 transition-all disabled:opacity-50 cursor-pointer mt-2"
              >
                {isLoading ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Verifying Credentials...</span>
                  </>
                ) : (
                  <>
                    <span>Sign In to Investigation Suite</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            </form>
          )}

          {/* Security & Statutory Notice */}
          <div className="pt-3 border-t border-stone-200 text-center space-y-1">
            <div className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-stone-700">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              <span>NIST SHA-256 Hashed • Bcrypt Protected • JWT Signed</span>
            </div>
            <p className="text-[10px] text-stone-500 leading-relaxed max-w-sm mx-auto">
              All logins and actions logged in an unbroken Merkle audit ledger under Section 65B Indian Evidence Act / Section 63 BSA 2023.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Login;
