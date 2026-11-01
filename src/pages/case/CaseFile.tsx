import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  FolderArchive, FileText, Calendar, Scale, Shield, 
  MapPin, User, Check, Edit3, Save, X, AlertCircle, 
  ShieldCheck, Lock, CheckCircle2, Sliders, Smartphone,
  RefreshCw, ArrowRight
} from 'lucide-react';
import { caseService, securityAdminService } from '../../services';
import { Case } from '../../types';
import { cn } from '../../utils';
import { useAuth } from '../../context/AuthContext';

export function CaseFile() {
  const { caseId } = useParams<{ caseId: string }>();
  const { role } = useAuth();
  const isLeadOrAdmin = role === 'lead_investigator' || role === 'admin';

  const [currentCase, setCurrentCase] = useState<Case | null>(null);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  // Form State
  const [firNumber, setFirNumber] = useState('');
  const [firDate, setFirDate] = useState('');
  const [incidentDate, setIncidentDate] = useState('');
  const [arrestDate, setArrestDate] = useState('');
  const [remandDate, setRemandDate] = useState('');
  const [offenceSection, setOffenceSection] = useState('');
  const [statutoryLimitDays, setStatutoryLimitDays] = useState(90);
  const [policeStation, setPoliceStation] = useState('');
  const [investigatingOfficer, setInvestigatingOfficer] = useState('');

  // Legal Hold Modal
  const [isLegalHoldOpen, setIsLegalHoldOpen] = useState(false);
  const [legalHoldReason, setLegalHoldReason] = useState('');

  const loadCaseData = async () => {
    if (!caseId) return;
    try {
      setLoading(true);
      const c = await caseService.getCaseById(caseId);
      if (c) {
        setCurrentCase(c);
        setFirNumber(c.fir_number || '');
        setFirDate(c.fir_date ? c.fir_date.slice(0, 10) : '');
        setIncidentDate(c.incident_date ? c.incident_date.slice(0, 10) : '');
        setArrestDate(c.arrest_date ? c.arrest_date.slice(0, 10) : '');
        setRemandDate(c.remand_date ? c.remand_date.slice(0, 10) : '');
        setOffenceSection(c.offence_section || '');
        setStatutoryLimitDays(c.statutory_time_limit_days || 90);
        setPoliceStation((c as any).police_station || 'Cyber Crime Division, HQ');
        setInvestigatingOfficer((c as any).investigating_officer || 'Inspector R. K. Sharma');
      }
    } catch (err) {
      console.error('Failed to load case file:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCaseData();
  }, [caseId]);

  const handleSaveProcedure = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!caseId) return;
    try {
      setSaving(true);
      await caseService.updateCaseProcedure(caseId, {
        fir_number: firNumber,
        fir_date: firDate ? new Date(firDate).toISOString() : undefined,
        incident_date: incidentDate ? new Date(incidentDate).toISOString() : undefined,
        arrest_date: arrestDate ? new Date(arrestDate).toISOString() : undefined,
        remand_date: remandDate ? new Date(remandDate).toISOString() : undefined,
        offence_section: offenceSection,
        statutory_time_limit_days: Number(statutoryLimitDays)
      });
      setIsEditing(false);
      await loadCaseData();
    } catch (err) {
      console.error('Failed to update procedural details:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleApplyLegalHold = async () => {
    if (!caseId || !legalHoldReason.trim()) return;
    try {
      await securityAdminService.setCaseLegalHold(caseId, {
        is_legal_hold: true,
        reason: legalHoldReason
      });
      setIsLegalHoldOpen(false);
      await loadCaseData();
    } catch (err) {
      console.error('Failed to apply legal hold:', err);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#eae4d9]">
        <div>
          <div className="text-[11px] font-mono tracking-widest text-[#d93829] uppercase font-bold mb-1 flex items-center gap-1.5">
            <FolderArchive className="w-3.5 h-3.5 text-[#d93829]" />
            <span>Official Investigation Docket</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-serif font-bold text-[#191410]">
            Case File & Legal Records
          </h1>
          <p className="text-xs text-[#6e665d] mt-1 max-w-2xl">
            Official First Information Report (FIR) parameters, penal provisions, procedural milestones, and chain of custody registry.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {isLeadOrAdmin && !isEditing && (
            <button
              onClick={() => setIsEditing(true)}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-[#faf7f2] hover:bg-[#eae4d9] text-[#191410] rounded-full text-xs font-bold transition-all border border-[#d8d0c5] cursor-pointer shadow-xs"
            >
              <Edit3 className="w-3.5 h-3.5 text-[#d93829]" />
              <span>Edit Case Docket</span>
            </button>
          )}

          <Link
            to={`/cases/${caseId}/chargesheet`}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-[#d93829] hover:bg-[#bf2b1d] text-white rounded-full text-xs font-bold transition-all shadow-xs cursor-pointer"
          >
            <Scale className="w-3.5 h-3.5" />
            <span>Generate Chargesheet</span>
          </Link>
        </div>
      </div>

      {/* Legal Hold / Air Gap Safety Banner */}
      <div className="p-4 rounded-3xl bg-[#faf7f2] border border-[#eae4d9] shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-white border border-[#eae4d9] shadow-2xs">
            <ShieldCheck className="w-5 h-5 text-emerald-700" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-serif font-bold text-[#191410]">
                Cryptographic Evidence Custody Active
              </span>
              <span className="px-2 py-0.5 rounded-full text-[9px] font-mono font-bold bg-emerald-100 text-emerald-900 border border-emerald-300">
                Tamper-Evident SHA-256
              </span>
            </div>
            <p className="text-xs text-[#6e665d] mt-0.5">
              All digital exhibits, interview transcripts, and seizure memos are hashed and Section 65B BSA certified.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setIsLegalHoldOpen(true)}
            className="px-3 py-1.5 rounded-full text-xs font-mono font-bold bg-white hover:bg-stone-100 text-stone-700 border border-[#d8d0c5] transition-all cursor-pointer shadow-2xs"
          >
            Legal Hold Policy
          </button>
        </div>
      </div>

      {/* Main Docket Form / Display */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: FIR & Statutory Offence Details */}
        <div className="lg:col-span-2 p-6 rounded-3xl bg-white border border-[#eae4d9] shadow-xs space-y-6">
          <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9]">
            <div className="flex items-center gap-2">
              <Scale className="w-4 h-4 text-[#d93829]" />
              <h2 className="text-base font-serif font-bold text-[#191410]">
                Statutory Offence & FIR Parameters
              </h2>
            </div>
            {isEditing && (
              <span className="text-[10px] font-mono font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-300">
                EDIT MODE
              </span>
            )}
          </div>

          {isEditing ? (
            <form onSubmit={handleSaveProcedure} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-serif font-bold text-[#191410] mb-1">
                    FIR / Docket Number
                  </label>
                  <input
                    type="text"
                    value={firNumber}
                    onChange={e => setFirNumber(e.target.value)}
                    placeholder="e.g. FIR-2026/0412"
                    className="w-full px-3 py-2 rounded-xl border border-[#d8d0c5] bg-[#faf7f2] text-xs font-mono focus:bg-white focus:outline-hidden focus:border-[#d93829]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-serif font-bold text-[#191410] mb-1">
                    Statutory Offence Sections (BNS / IPC)
                  </label>
                  <input
                    type="text"
                    value={offenceSection}
                    onChange={e => setOffenceSection(e.target.value)}
                    placeholder="e.g. Section 103, 316 BNS (Murder, Criminal Breach)"
                    className="w-full px-3 py-2 rounded-xl border border-[#d8d0c5] bg-[#faf7f2] text-xs font-mono focus:bg-white focus:outline-hidden focus:border-[#d93829]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-serif font-bold text-[#191410] mb-1">
                    FIR Registration Date
                  </label>
                  <input
                    type="date"
                    value={firDate}
                    onChange={e => setFirDate(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-[#d8d0c5] bg-[#faf7f2] text-xs font-mono focus:bg-white focus:outline-hidden focus:border-[#d93829]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-serif font-bold text-[#191410] mb-1">
                    Date of Incident
                  </label>
                  <input
                    type="date"
                    value={incidentDate}
                    onChange={e => setIncidentDate(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-[#d8d0c5] bg-[#faf7f2] text-xs font-mono focus:bg-white focus:outline-hidden focus:border-[#d93829]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-serif font-bold text-[#191410] mb-1">
                    Date of First Arrest
                  </label>
                  <input
                    type="date"
                    value={arrestDate}
                    onChange={e => setArrestDate(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-[#d8d0c5] bg-[#faf7f2] text-xs font-mono focus:bg-white focus:outline-hidden focus:border-[#d93829]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-serif font-bold text-[#191410] mb-1">
                    Remand Date
                  </label>
                  <input
                    type="date"
                    value={remandDate}
                    onChange={e => setRemandDate(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-[#d8d0c5] bg-[#faf7f2] text-xs font-mono focus:bg-white focus:outline-hidden focus:border-[#d93829]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-serif font-bold text-[#191410] mb-1">
                    Statutory Filing Limit (Days)
                  </label>
                  <select
                    value={statutoryLimitDays}
                    onChange={e => setStatutoryLimitDays(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-xl border border-[#d8d0c5] bg-[#faf7f2] text-xs font-mono focus:bg-white focus:outline-hidden focus:border-[#d93829]"
                  >
                    <option value={60}>60 Days (Standard Offences)</option>
                    <option value={90}>90 Days (Heinous Offences / Life Imprisonment)</option>
                    <option value={180}>180 Days (Special Acts / UAPA / NDPS)</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-3 border-t border-[#eae4d9]">
                <button
                  type="submit"
                  disabled={saving}
                  className="flex items-center gap-1.5 px-4 py-2 bg-[#d93829] hover:bg-[#bf2b1d] text-white rounded-full text-xs font-bold transition-all shadow-xs cursor-pointer disabled:opacity-50"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>{saving ? 'Saving Changes...' : 'Save Docket Details'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setIsEditing(false)}
                  className="px-4 py-2 bg-[#faf7f2] hover:bg-[#eae4d9] text-[#191410] rounded-full text-xs font-bold transition-all border border-[#d8d0c5] cursor-pointer"
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
              <div className="p-3.5 rounded-2xl bg-[#faf7f2] border border-[#eae4d9]">
                <span className="text-[10px] text-[#6e665d] uppercase block font-bold">FIR / Docket ID</span>
                <span className="text-sm font-serif font-bold text-[#191410] block mt-0.5">
                  {currentCase?.fir_number || 'FIR-2026/0412 (Central Registry)'}
                </span>
              </div>

              <div className="p-3.5 rounded-2xl bg-[#faf7f2] border border-[#eae4d9]">
                <span className="text-[10px] text-[#6e665d] uppercase block font-bold">Penal Provisions</span>
                <span className="text-sm font-serif font-bold text-blue-900 block mt-0.5">
                  {currentCase?.offence_section || 'Section 103, 316 BNS (Cognizable / Non-Bailable)'}
                </span>
              </div>

              <div className="p-3.5 rounded-2xl bg-[#faf7f2] border border-[#eae4d9]">
                <span className="text-[10px] text-[#6e665d] uppercase block font-bold">FIR Registration Date</span>
                <span className="text-sm font-bold text-[#191410] block mt-0.5">
                  {currentCase?.fir_date ? new Date(currentCase.fir_date).toLocaleDateString() : '14 Jan 2026'}
                </span>
              </div>

              <div className="p-3.5 rounded-2xl bg-[#faf7f2] border border-[#eae4d9]">
                <span className="text-[10px] text-[#6e665d] uppercase block font-bold">Incident Timestamp</span>
                <span className="text-sm font-bold text-[#191410] block mt-0.5">
                  {currentCase?.incident_date ? new Date(currentCase.incident_date).toLocaleDateString() : '12 Jan 2026, 21:45 IST'}
                </span>
              </div>

              <div className="p-3.5 rounded-2xl bg-[#faf7f2] border border-[#eae4d9]">
                <span className="text-[10px] text-[#6e665d] uppercase block font-bold">Arrest Milestone</span>
                <span className="text-sm font-bold text-[#191410] block mt-0.5">
                  {currentCase?.arrest_date ? new Date(currentCase.arrest_date).toLocaleDateString() : '16 Jan 2026 (Under Police Custody)'}
                </span>
              </div>

              <div className="p-3.5 rounded-2xl bg-[#faf7f2] border border-[#eae4d9]">
                <span className="text-[10px] text-[#6e665d] uppercase block font-bold">Statutory Limit</span>
                <span className="text-sm font-bold text-[#d93829] block mt-0.5">
                  {currentCase?.statutory_time_limit_days || 90} Days (Section 193 BNSS)
                </span>
              </div>
            </div>
          )}

          {/* Official Case Narrative */}
          <div className="pt-4 border-t border-[#eae4d9] space-y-2">
            <h3 className="text-xs font-serif font-bold text-[#191410] uppercase tracking-wider">
              Official Complaint Narrative
            </h3>
            <p className="text-xs text-[#6e665d] leading-relaxed font-sans bg-[#faf7f2] p-4 rounded-2xl border border-[#eae4d9]">
              {currentCase?.description || 
                'First Information Report registered upon complaint regarding unauthorized premises breach, tampering of physical safes, and disappearance of key commercial instruments. Forensics division dispatched for latent fingerprint dusting, blood spatter recovery, and CCTV DVR hard drive seizure.'}
            </p>
          </div>
        </div>

        {/* Right Column: Jurisdictional & Administrative Officers */}
        <div className="p-6 rounded-3xl bg-white border border-[#eae4d9] shadow-xs space-y-5">
          <div className="flex items-center gap-2 pb-3 border-b border-[#eae4d9]">
            <MapPin className="w-4 h-4 text-[#d93829]" />
            <h2 className="text-base font-serif font-bold text-[#191410]">
              Jurisdiction & Team
            </h2>
          </div>

          <div className="space-y-3 text-xs">
            <div className="p-3.5 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] space-y-1">
              <span className="text-[10px] font-mono text-[#6e665d] uppercase font-bold">Police Station</span>
              <div className="font-serif font-bold text-[#191410]">{policeStation}</div>
              <div className="text-[11px] text-[#8c8276]">Metropolitan Crime Branch • Zone IV</div>
            </div>

            <div className="p-3.5 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] space-y-1">
              <span className="text-[10px] font-mono text-[#6e665d] uppercase font-bold">Lead Investigating Officer (IO)</span>
              <div className="font-serif font-bold text-[#191410]">{investigatingOfficer}</div>
              <div className="text-[11px] text-[#8c8276]">Badge #PB-4481 • CID Special Unit</div>
            </div>

            <div className="p-3.5 rounded-2xl bg-[#faf7f2] border border-[#eae4d9] space-y-1">
              <span className="text-[10px] font-mono text-[#6e665d] uppercase font-bold">Supervising Magistrate</span>
              <div className="font-serif font-bold text-[#191410]">Court of Chief Judicial Magistrate</div>
              <div className="text-[11px] text-[#8c8276]">District Sessions Court Division</div>
            </div>

            <div className="p-3.5 rounded-2xl bg-amber-50/70 border border-amber-200 text-amber-950 space-y-1">
              <span className="text-[10px] font-mono uppercase font-bold text-amber-800">Custodial Status</span>
              <div className="font-serif font-bold">2 Accused under Judicial Remand</div>
              <div className="text-[11px] text-amber-900">Bail applications pending before the High Court.</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
