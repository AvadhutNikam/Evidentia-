import React, { useState, useEffect } from 'react';
import {
  ShieldCheck, AlertTriangle, Clock, ArrowRight, UserCheck, MapPin,
  FileCheck2, QrCode, Lock, KeyRound, CheckCircle2, ChevronRight,
  Download, Printer, Plus, AlertCircle, RefreshCw, X, Eye
} from 'lucide-react';
import {
  physicalEvidenceService,
  CustodyLogExtended,
  ContinuityCheck,
  Seal,
  CourtCertificate
} from '../../services';

interface UnifiedCustodyTimelineProps {
  evidenceId: number;
  caseId: string | number;
  evidenceTitle: string;
  evidenceKind?: 'digital' | 'physical';
  onUpdated?: () => void;
}

export function UnifiedCustodyTimeline({
  evidenceId,
  caseId,
  evidenceTitle,
  evidenceKind = 'physical',
  onUpdated
}: UnifiedCustodyTimelineProps) {
  const [loading, setLoading] = useState<boolean>(true);
  const [ledger, setLedger] = useState<CustodyLogExtended[]>([]);
  const [continuity, setContinuity] = useState<ContinuityCheck | null>(null);
  const [seals, setSeals] = useState<Seal[]>([]);
  const [selectedPhoto, setSelectedPhoto] = useState<string | null>(null);

  // Modals
  const [showHandoverModal, setShowHandoverModal] = useState<boolean>(false);
  const [showCertificateModal, setShowCertificateModal] = useState<boolean>(false);
  const [certificateData, setCertificateData] = useState<CourtCertificate | null>(null);
  const [showSealModal, setShowSealModal] = useState<boolean>(false);

  // Form states for Handover
  const [handoverAction, setHandoverAction] = useState<string>('TRANSFER');
  const [toPersonName, setToPersonName] = useState<string>('');
  const [toLocation, setToLocation] = useState<string>('');
  const [fromLocation, setFromLocation] = useState<string>('');
  const [purpose, setPurpose] = useState<string>('Investigation Handover');
  const [sealCheck, setSealCheck] = useState<string>('intact');
  const [notes, setNotes] = useState<string>('');
  const [submittingHandover, setSubmittingHandover] = useState<boolean>(false);

  // Form states for Seal
  const [newSealNumber, setNewSealNumber] = useState<string>('');
  const [newOwnerMark, setNewOwnerMark] = useState<string>('Crime Branch Pune IO Seal');
  const [packageDesc, setPackageDesc] = useState<string>('Cloth parcel sealed with red wax');
  const [witnessesInput, setWitnessesInput] = useState<string>('Panch Witness 1, Panch Witness 2');
  const [submittingSeal, setSubmittingSeal] = useState<boolean>(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [ledgerData, contData, sealsData] = await Promise.all([
        physicalEvidenceService.getCustodyLedger(evidenceId).catch(() => []),
        physicalEvidenceService.checkContinuity(evidenceId).catch(() => null),
        physicalEvidenceService.getSeals(evidenceId).catch(() => [])
      ]);
      setLedger(ledgerData);
      setContinuity(contData);
      setSeals(sealsData);
    } catch (err) {
      console.error('Failed to load custody timeline:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [evidenceId]);

  const handleOpenCertificate = async () => {
    try {
      const cert = await physicalEvidenceService.getCourtCustodyCertificate(evidenceId);
      setCertificateData(cert);
      setShowCertificateModal(true);
    } catch (err) {
      alert('Could not generate court certificate. Check connection.');
    }
  };

  const handleCreateHandover = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!toPersonName.trim() || !toLocation.trim()) {
      alert('Please fill recipient name and destination location.');
      return;
    }
    setSubmittingHandover(true);
    try {
      await physicalEvidenceService.recordCustodyTransfer(evidenceId, {
        action: handoverAction,
        to_person_name: toPersonName.trim(),
        to_location: toLocation.trim(),
        from_location: fromLocation.trim() || undefined,
        purpose: purpose.trim(),
        seal_status_check: sealCheck,
        notes: notes.trim() || undefined
      });
      setShowHandoverModal(false);
      resetHandoverForm();
      await loadData();
      if (onUpdated) onUpdated();
    } catch (err: any) {
      alert(err?.message || 'Failed to record custody handover.');
    } finally {
      setSubmittingHandover(false);
    }
  };

  const resetHandoverForm = () => {
    setToPersonName('');
    setToLocation('');
    setFromLocation('');
    setNotes('');
  };

  const handleCreateSeal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSealNumber.trim()) {
      alert('Please specify seal number.');
      return;
    }
    setSubmittingSeal(true);
    try {
      const witnessList = witnessesInput.split(',').map(s => s.trim()).filter(Boolean);
      await physicalEvidenceService.createSeal(evidenceId, {
        seal_number: newSealNumber.trim().toUpperCase(),
        owner_mark: newOwnerMark.trim(),
        package_description: packageDesc.trim(),
        applied_in_presence_of: witnessList
      });
      setShowSealModal(false);
      setNewSealNumber('');
      await loadData();
      if (onUpdated) onUpdated();
    } catch (err: any) {
      alert(err?.message || 'Failed to apply new seal.');
    } finally {
      setSubmittingSeal(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center bg-white rounded-lg border border-[#e2dcd2] shadow-xs">
        <RefreshCw className="w-5 h-5 text-[#8c827a] animate-spin mx-auto mb-2" />
        <p className="text-xs text-[#70685e] font-serif">Verifying cryptographic hash chain & forensic custody ledger...</p>
      </div>
    );
  }

  const isComplete = continuity?.status === 'complete' && continuity?.hash_chain_valid;
  const isGap = continuity?.status === 'gap';
  const isSealIssue = continuity?.status === 'seal_issue';

  return (
    <div className="space-y-4">
      {/* 1. Continuity Header Card */}
      <div className={`p-4 rounded-lg border shadow-xs transition-all ${
        isComplete
          ? 'bg-emerald-50/70 border-emerald-200 text-emerald-950'
          : isGap
          ? 'bg-amber-50/70 border-amber-200 text-amber-950'
          : 'bg-rose-50/70 border-rose-200 text-rose-950'
      }`}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-full ${
              isComplete ? 'bg-emerald-100 text-emerald-700' : isGap ? 'bg-amber-100 text-amber-700' : 'bg-rose-100 text-rose-700'
            }`}>
              {isComplete ? <ShieldCheck className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm">
                  {isComplete
                    ? 'Unbroken Chain of Custody (Cryptographically Verified)'
                    : isGap
                    ? 'Custody Continuity Warning (Discrepancy Detected)'
                    : 'Critical Seal / Custody Breach Flagged'}
                </span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-white border border-current shadow-xs">
                  {evidenceKind.toUpperCase()} EXHIBIT
                </span>
              </div>
              <p className="text-xs opacity-90 mt-0.5">
                {isComplete
                  ? `All ${continuity?.total_custody_entries || ledger.length} custody entries verified against sequential SHA-256 Merkle chain. Current custodian: ${continuity?.current_custodian || 'Malkhana'}.`
                  : continuity?.issues?.map(i => i.message).join(' | ') || 'Handover discontinuity flagged by automated checker.'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowHandoverModal(true)}
              className="px-3 py-1.5 bg-[#d93829] hover:bg-[#b82d20] text-white text-xs font-semibold rounded-md shadow-xs flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              Record Handover
            </button>
            <button
              onClick={() => setShowSealModal(true)}
              className="px-3 py-1.5 bg-white hover:bg-[#faf7f2] border border-[#e2dcd2] text-[#191410] text-xs font-semibold rounded-md shadow-xs flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Lock className="w-3.5 h-3.5 text-[#70685e]" />
              Apply Seal
            </button>
            <button
              onClick={handleOpenCertificate}
              className="px-3 py-1.5 bg-white hover:bg-[#faf7f2] border border-[#e2dcd2] text-[#191410] text-xs font-semibold rounded-md shadow-xs flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <FileCheck2 className="w-3.5 h-3.5 text-emerald-600" />
              Court Certificate
            </button>
          </div>
        </div>

        {/* Issues alert list if any */}
        {continuity?.issues && continuity.issues.length > 0 && (
          <div className="mt-3 pt-3 border-t border-current/20 space-y-1">
            {continuity.issues.map((iss, idx) => (
              <div key={idx} className="flex items-start gap-2 text-xs">
                <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                <span><strong className="font-semibold">{iss.type}:</strong> {iss.message}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 2. Active Seals Strip */}
      {seals.length > 0 && (
        <div className="p-3 bg-white rounded-lg border border-[#e2dcd2] shadow-xs">
          <div className="text-xs font-bold text-[#191410] uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-[#d93829]" />
            Tamper-Evident Seals ({seals.length})
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
            {seals.map((seal) => (
              <div key={seal.id} className="p-2.5 rounded-md border border-[#eae4d9] bg-[#faf7f2]/60 text-xs">
                <div className="flex items-center justify-between font-mono font-bold text-[#191410]">
                  <span>{seal.seal_number}</span>
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-sans font-bold uppercase ${
                    seal.status === 'intact'
                      ? 'bg-emerald-100 text-emerald-800'
                      : seal.status === 'resealed'
                      ? 'bg-blue-100 text-blue-800'
                      : 'bg-rose-100 text-rose-800'
                  }`}>
                    {seal.status}
                  </span>
                </div>
                <p className="text-[#59524c] mt-1 text-[11px] truncate">{seal.owner_mark}</p>
                <p className="text-[#8c827a] text-[10px] mt-0.5">Applied by: {seal.applied_by_name}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. Chronological Chained Ledger Timeline */}
      <div className="bg-white rounded-lg border border-[#e2dcd2] p-4 shadow-xs">
        <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9] mb-4">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-[#d93829]" />
            <h4 className="font-serif font-bold text-sm text-[#191410]">
              Sequential Custody Trail ({ledger.length} Recorded Movements)
            </h4>
          </div>
          <span className="text-[11px] text-[#70685e]">
            Cryptographic SHA-256 Ledger • Sec 192/193 BNSS Compliant
          </span>
        </div>

        {ledger.length === 0 ? (
          <div className="p-8 text-center text-[#70685e] text-xs italic">
            No custody entries recorded yet for this exhibit.
          </div>
        ) : (
          <div className="relative pl-6 space-y-6 before:content-[''] before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-[#eae4d9]">
            {ledger.map((entry, idx) => {
              const isFirst = idx === 0;
              const isLast = idx === ledger.length - 1;

              return (
                <div key={entry.id} className="relative group">
                  {/* Step dot */}
                  <div className={`absolute -left-6 top-1 w-4 h-4 rounded-full border-2 bg-white flex items-center justify-center ${
                    isLast ? 'border-[#d93829] ring-2 ring-red-100' : 'border-[#8c827a]'
                  }`}>
                    <div className={`w-1.5 h-1.5 rounded-full ${isLast ? 'bg-[#d93829]' : 'bg-[#8c827a]'}`} />
                  </div>

                  <div className="p-3.5 rounded-lg border border-[#eae4d9] bg-[#faf7f2]/40 hover:bg-[#faf7f2] transition-colors">
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 bg-[#191410] text-white rounded text-[10px] font-bold tracking-wider">
                          {entry.action}
                        </span>
                        <span className="text-xs font-semibold text-[#191410]">
                          {entry.purpose || 'Custody Handover'}
                        </span>
                      </div>
                      <span className="text-[11px] text-[#70685e]">
                        {new Date(entry.timestamp).toLocaleString('en-IN', {
                          day: '2-digit', month: 'short', year: 'numeric',
                          hour: '2-digit', minute: '2-digit', second: '2-digit'
                        })}
                      </span>
                    </div>

                    {/* From / To Route */}
                    <div className="flex flex-wrap items-center gap-3 text-xs text-[#3d3832] my-2">
                      <div className="flex items-center gap-1.5">
                        <MapPin className="w-3.5 h-3.5 text-[#8c827a]" />
                        <span>From: <strong>{entry.from_location || 'Scene / Prior Location'}</strong></span>
                        {entry.from_person_name && <span className="text-[#70685e]">({entry.from_person_name})</span>}
                      </div>
                      <ArrowRight className="w-3.5 h-3.5 text-[#d93829]" />
                      <div className="flex items-center gap-1.5">
                        <MapPin className="w-3.5 h-3.5 text-[#8c827a]" />
                        <span>To: <strong>{entry.to_location || entry.location}</strong></span>
                        {entry.to_person_name && <span className="text-[#70685e]">({entry.to_person_name})</span>}
                      </div>
                    </div>

                    {/* Condition & Seal Status */}
                    <div className="flex flex-wrap items-center gap-4 text-[11px] text-[#59524c] pt-2 border-t border-[#eae4d9]/70">
                      <div>
                        Condition: <span className="font-semibold capitalize text-[#191410]">{entry.condition_at_handover || 'Intact'}</span>
                      </div>
                      <div>
                        Seal Check: <span className="font-semibold text-[#191410]">{entry.seal_status_check || 'Verified'}</span>
                      </div>
                      <div>
                        Logged by: <span className="text-[#191410] font-medium">{entry.actor_name}</span>
                      </div>
                    </div>

                    {/* Notes */}
                    {entry.notes && (
                      <p className="text-xs text-[#59524c] italic mt-2 bg-white/70 p-2 rounded border border-[#eae4d9]">
                        &ldquo;{entry.notes}&rdquo;
                      </p>
                    )}

                    {/* Cryptographic SHA-256 Hash Link */}
                    <div className="mt-2.5 pt-2 border-t border-[#eae4d9]/50 flex items-center justify-between text-[10px] font-mono text-[#8c827a]">
                      <span title={entry.previous_log_hash || ''}>
                        PREV: {entry.previous_log_hash ? entry.previous_log_hash.slice(0, 14) + '...' : 'GENESIS'}
                      </span>
                      <span className="text-[#d93829] font-bold" title={entry.current_log_hash || ''}>
                        HASH: {entry.current_log_hash ? entry.current_log_hash.slice(0, 16) + '...' : 'PENDING'}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 4. MODAL: Record Handover */}
      {showHandoverModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-lg border border-[#e2dcd2] shadow-xl w-full max-w-lg p-5 animate-scaleUp">
            <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9] mb-4">
              <h3 className="font-serif font-bold text-base text-[#191410] flex items-center gap-2">
                <Plus className="w-4 h-4 text-[#d93829]" />
                Record Chained Custody Handover
              </h3>
              <button
                onClick={() => setShowHandoverModal(false)}
                className="text-[#8c827a] hover:text-[#191410] cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateHandover} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-[#59524c] font-semibold mb-1">Custody Action</label>
                <select
                  value={handoverAction}
                  onChange={(e) => setHandoverAction(e.target.value)}
                  className="w-full px-3 py-1.5 border border-[#d6cfc5] rounded bg-[#faf7f2] text-[#191410]"
                >
                  <option value="TRANSFER">TRANSFER (Investigator / Officer Handover)</option>
                  <option value="MALKHANA_IN">MALKHANA_IN (Station Vault Deposit)</option>
                  <option value="MALKHANA_OUT">MALKHANA_OUT (Vault Issue for Review/Court)</option>
                  <option value="SENT_TO_FSL">SENT_TO_FSL (Dispatched to Forensic Lab)</option>
                  <option value="RECEIVED_FROM_FSL">RECEIVED_FROM_FSL (Lab Return)</option>
                  <option value="PRODUCED_IN_COURT">PRODUCED_IN_COURT (Trial Evidence Production)</option>
                  <option value="RETURNED">RETURNED (Released to Owner by Court Order)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#59524c] font-semibold mb-1">To Person Name *</label>
                  <input
                    type="text"
                    required
                    value={toPersonName}
                    onChange={(e) => setToPersonName(e.target.value)}
                    placeholder="e.g. ASI Malkhana / Court Registrar"
                    className="w-full px-3 py-1.5 border border-[#d6cfc5] rounded bg-white text-[#191410]"
                  />
                </div>
                <div>
                  <label className="block text-[#59524c] font-semibold mb-1">Destination Location *</label>
                  <input
                    type="text"
                    required
                    value={toLocation}
                    onChange={(e) => setToLocation(e.target.value)}
                    placeholder="e.g. Malkhana Rack 2 / Sessions Court"
                    className="w-full px-3 py-1.5 border border-[#d6cfc5] rounded bg-white text-[#191410]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#59524c] font-semibold mb-1">Departing Location</label>
                  <input
                    type="text"
                    value={fromLocation}
                    onChange={(e) => setFromLocation(e.target.value)}
                    placeholder="e.g. Yerawada Police Station"
                    className="w-full px-3 py-1.5 border border-[#d6cfc5] rounded bg-white text-[#191410]"
                  />
                </div>
                <div>
                  <label className="block text-[#59524c] font-semibold mb-1">Seal Check</label>
                  <select
                    value={sealCheck}
                    onChange={(e) => setSealCheck(e.target.value)}
                    className="w-full px-3 py-1.5 border border-[#d6cfc5] rounded bg-[#faf7f2] text-[#191410]"
                  >
                    <option value="intact">Intact & Undisturbed</option>
                    <option value="damaged">Damaged / Seal Broken</option>
                    <option value="resealed">Resealed with New Wax</option>
                    <option value="unsealed">Unsealed (Raw Exhibit)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[#59524c] font-semibold mb-1">Handover Purpose</label>
                <input
                  type="text"
                  value={purpose}
                  onChange={(e) => setPurpose(e.target.value)}
                  placeholder="e.g. Safe deposit, Trial exhibit production"
                  className="w-full px-3 py-1.5 border border-[#d6cfc5] rounded bg-white text-[#191410]"
                />
              </div>

              <div>
                <label className="block text-[#59524c] font-semibold mb-1">Handover Notes / Remarks</label>
                <textarea
                  rows={2}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Notes on packaging, condition, witness signatures..."
                  className="w-full px-3 py-1.5 border border-[#d6cfc5] rounded bg-white text-[#191410]"
                />
              </div>

              <div className="pt-3 border-t border-[#eae4d9] flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowHandoverModal(false)}
                  className="px-3 py-1.5 border border-[#d6cfc5] rounded text-[#59524c] hover:bg-[#faf7f2] font-semibold cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingHandover}
                  className="px-4 py-1.5 bg-[#d93829] hover:bg-[#b82d20] text-white font-semibold rounded shadow-xs cursor-pointer disabled:opacity-50"
                >
                  {submittingHandover ? 'Writing to Hash Chain...' : 'Record Chained Transfer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 5. MODAL: Apply Seal */}
      {showSealModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-lg border border-[#e2dcd2] shadow-xl w-full max-w-md p-5 animate-scaleUp">
            <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9] mb-4">
              <h3 className="font-serif font-bold text-base text-[#191410] flex items-center gap-2">
                <Lock className="w-4 h-4 text-[#d93829]" />
                Apply Tamper-Evident Seal
              </h3>
              <button
                onClick={() => setShowSealModal(false)}
                className="text-[#8c827a] hover:text-[#191410] cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateSeal} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-[#59524c] font-semibold mb-1">Seal Number *</label>
                <input
                  type="text"
                  required
                  value={newSealNumber}
                  onChange={(e) => setNewSealNumber(e.target.value)}
                  placeholder="e.g. MH-PUN-09-W02"
                  className="w-full px-3 py-1.5 border border-[#d6cfc5] rounded bg-white font-mono uppercase text-[#191410]"
                />
              </div>

              <div>
                <label className="block text-[#59524c] font-semibold mb-1">Owner / Office Mark</label>
                <input
                  type="text"
                  value={newOwnerMark}
                  onChange={(e) => setNewOwnerMark(e.target.value)}
                  placeholder="e.g. Crime Branch Unit 1 IO Mark"
                  className="w-full px-3 py-1.5 border border-[#d6cfc5] rounded bg-white text-[#191410]"
                />
              </div>

              <div>
                <label className="block text-[#59524c] font-semibold mb-1">Packaging Description</label>
                <input
                  type="text"
                  value={packageDesc}
                  onChange={(e) => setPackageDesc(e.target.value)}
                  placeholder="e.g. Sealed wooden box with lac seal"
                  className="w-full px-3 py-1.5 border border-[#d6cfc5] rounded bg-white text-[#191410]"
                />
              </div>

              <div>
                <label className="block text-[#59524c] font-semibold mb-1">Applied in Presence of (Panchas / Witnesses)</label>
                <input
                  type="text"
                  value={witnessesInput}
                  onChange={(e) => setWitnessesInput(e.target.value)}
                  placeholder="Comma separated witness names"
                  className="w-full px-3 py-1.5 border border-[#d6cfc5] rounded bg-white text-[#191410]"
                />
              </div>

              <div className="pt-3 border-t border-[#eae4d9] flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowSealModal(false)}
                  className="px-3 py-1.5 border border-[#d6cfc5] rounded text-[#59524c] hover:bg-[#faf7f2] font-semibold cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingSeal}
                  className="px-4 py-1.5 bg-[#d93829] hover:bg-[#b82d20] text-white font-semibold rounded shadow-xs cursor-pointer disabled:opacity-50"
                >
                  {submittingSeal ? 'Applying...' : 'Apply & Register Seal'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 6. MODAL: Court Custody Certificate */}
      {showCertificateModal && certificateData && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-lg border border-[#e2dcd2] shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 animate-scaleUp text-[#191410]">
            <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9] mb-4">
              <div className="flex items-center gap-2">
                <FileCheck2 className="w-5 h-5 text-emerald-700" />
                <h3 className="font-serif font-bold text-lg text-[#191410]">
                  Official Court Custody Certificate
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => window.print()}
                  className="px-2.5 py-1 text-xs border border-[#d6cfc5] rounded hover:bg-[#faf7f2] flex items-center gap-1 font-semibold cursor-pointer"
                >
                  <Printer className="w-3.5 h-3.5" />
                  Print
                </button>
                <button
                  onClick={() => setShowCertificateModal(false)}
                  className="text-[#8c827a] hover:text-[#191410] cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Certificate Body (Judicial Format) */}
            <div className="border-2 border-[#191410] p-6 bg-[#faf7f2]/50 font-serif space-y-4 text-xs">
              <div className="text-center space-y-1">
                <p className="font-bold tracking-widest text-sm uppercase">MAHARASHTRA POLICE DEPARTMENT</p>
                <p className="font-bold text-base uppercase text-[#d93829]">{certificateData.certificate_title}</p>
                <p className="italic text-[11px] text-[#59524c]">{certificateData.legal_provision}</p>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[#191410] text-[11px] font-sans">
                <div>CRIME NO: <strong>{certificateData.crime_number}</strong></div>
                <div>POLICE STATION: <strong>{certificateData.police_station}</strong></div>
                <div>COURT: <strong>{certificateData.court_name}</strong></div>
                <div>EXHIBIT ID: <strong>#{certificateData.evidence_id}</strong></div>
                <div>CATEGORY: <strong className="capitalize">{certificateData.category}</strong></div>
                <div>MALKHANA NO: <strong>{certificateData.malkhana_entry_number}</strong></div>
              </div>

              <div className="p-2.5 bg-white border border-[#eae4d9] rounded text-[11px] font-sans">
                <strong>EXHIBIT DESCRIPTION:</strong> {certificateData.description}
                {certificateData.identifying_marks && (
                  <div><strong>IDENTIFYING MARKS:</strong> {certificateData.identifying_marks}</div>
                )}
              </div>

              <div>
                <p className="font-bold uppercase tracking-wider text-[11px] mb-1.5 font-sans">
                  CHRONOLOGICAL CUSTODY LEDGER ({certificateData.total_transfers} TRANSFERS)
                </p>
                <table className="w-full text-[10px] font-sans border-collapse border border-[#d6cfc5]">
                  <thead>
                    <tr className="bg-[#f0ebe1] text-[#191410]">
                      <th className="border border-[#d6cfc5] p-1 text-center">#</th>
                      <th className="border border-[#d6cfc5] p-1 text-left">Action</th>
                      <th className="border border-[#d6cfc5] p-1 text-left">Timestamp (IST)</th>
                      <th className="border border-[#d6cfc5] p-1 text-left">Custodian / Route</th>
                      <th className="border border-[#d6cfc5] p-1 text-center">Seal Status</th>
                      <th className="border border-[#d6cfc5] p-1 text-left">Hash Seal</th>
                    </tr>
                  </thead>
                  <tbody>
                    {certificateData.ledger.map((row) => (
                      <tr key={row.step} className="border-b border-[#eae4d9]">
                        <td className="border border-[#d6cfc5] p-1 text-center font-bold">{row.step}</td>
                        <td className="border border-[#d6cfc5] p-1 font-semibold">{row.action}</td>
                        <td className="border border-[#d6cfc5] p-1">{row.timestamp}</td>
                        <td className="border border-[#d6cfc5] p-1">{row.from_location} &rarr; {row.to_location}</td>
                        <td className="border border-[#d6cfc5] p-1 text-center font-medium">{row.seal_status}</td>
                        <td className="border border-[#d6cfc5] p-1 font-mono text-[9px] text-[#70685e]">{row.hash}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="pt-4 border-t border-[#191410] flex justify-between items-end font-sans text-[11px]">
                <div>
                  <p>CONTINUITY STATUS: <strong className="text-emerald-700">{certificateData.continuity_status}</strong></p>
                  <p>HASH CHAIN VERIFIED: <strong>{certificateData.hash_chain_verified ? 'YES (SHA-256)' : 'NO'}</strong></p>
                  <p className="text-[10px] text-[#70685e]">Certified at: {certificateData.generation_timestamp}</p>
                </div>
                <div className="text-right">
                  <div className="w-40 border-b border-[#191410] pb-1 mb-1 font-bold">
                    {certificateData.certifying_officer}
                  </div>
                  <p className="text-[10px] text-[#59524c]">Investigating Officer / Malkhana In-Charge</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

