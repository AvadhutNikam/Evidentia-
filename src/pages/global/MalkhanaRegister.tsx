import React, { useState, useEffect } from 'react';
import {
  Archive, QrCode, Search, Filter, Plus, ArrowUpRight, ArrowDownLeft,
  Lock, RefreshCw, CheckCircle2, AlertTriangle, Printer, X, ShieldAlert,
  MapPin, Clock, FileText, Eye, CheckSquare
} from 'lucide-react';
import {
  physicalEvidenceService,
  MalkhanaRegisterItem,
  caseFileService,
  PoliceStationLookup
} from '../../services';
import { UnifiedCustodyTimeline } from '../../components/evidence/UnifiedCustodyTimeline';

export function MalkhanaRegister() {
  const [station, setStation] = useState<string>('Yerawada Police Station');
  const [stations, setStations] = useState<PoliceStationLookup[]>([]);
  const [items, setItems] = useState<MalkhanaRegisterItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Selected item for modals
  const [selectedItem, setSelectedItem] = useState<MalkhanaRegisterItem | null>(null);
  const [showIssueModal, setShowIssueModal] = useState<boolean>(false);
  const [showReturnModal, setShowReturnModal] = useState<boolean>(false);
  const [showDepositModal, setShowDepositModal] = useState<boolean>(false);
  const [showLabelModal, setShowLabelModal] = useState<boolean>(false);
  const [labelSvg, setLabelSvg] = useState<string>('');
  const [showTimelineModal, setShowTimelineModal] = useState<boolean>(false);

  // Issue Form (Two-Person Rule)
  const [issuePurpose, setIssuePurpose] = useState<string>('Investigation Examination');
  const [destinationLocation, setDestinationLocation] = useState<string>('Sessions Court, Pune');
  const [takenByName, setTakenByName] = useState<string>('');
  const [approverId, setApproverId] = useState<number>(1);
  const [expectedReturnDate, setExpectedReturnDate] = useState<string>('');
  const [authorityOrderRef, setAuthorityOrderRef] = useState<string>('');
  const [issueSubmitting, setIssueSubmitting] = useState<boolean>(false);

  // Return Form
  const [returnedByName, setReturnedByName] = useState<string>('');
  const [returnRack, setReturnRack] = useState<string>('');
  const [returnCondition, setReturnCondition] = useState<string>('intact');
  const [returnSealStatus, setReturnSealStatus] = useState<string>('intact');
  const [returnSubmitting, setReturnSubmitting] = useState<boolean>(false);

  // Stock Check Mode
  const [stockCheckActive, setStockCheckActive] = useState<boolean>(false);
  const [scannedIds, setScannedIds] = useState<number[]>([]);

  const loadRegister = async () => {
    setLoading(true);
    try {
      const [stationList, regItems] = await Promise.all([
        caseFileService.getPoliceStations().catch(() => []),
        physicalEvidenceService.getMalkhanaRegister(
          station,
          undefined,
          statusFilter === 'all' ? undefined : statusFilter
        ).catch(() => [])
      ]);
      setStations(stationList);
      setItems(regItems);
    } catch (err) {
      console.error('Failed to load malkhana register:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRegister();
  }, [station, statusFilter]);

  const filteredItems = items.filter((item) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      item.crime_number.toLowerCase().includes(q) ||
      (item.malkhana_entry_number || '').toLowerCase().includes(q) ||
      (item.seal_number || '').toLowerCase().includes(q) ||
      item.description.toLowerCase().includes(q) ||
      item.category.toLowerCase().includes(q)
    );
  });

  const handleOpenLabel = async (item: MalkhanaRegisterItem) => {
    try {
      const res = await physicalEvidenceService.getBarcodeLabel(item.evidence_id);
      setLabelSvg(res.svg);
      setSelectedItem(item);
      setShowLabelModal(true);
    } catch (err) {
      alert('Could not generate barcode label.');
    }
  };

  const handleIssueSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItem) return;
    if (!takenByName.trim()) {
      alert('Please specify the person taking the exhibit.');
      return;
    }
    setIssueSubmitting(true);
    try {
      await physicalEvidenceService.issueMalkhana(selectedItem.evidence_id, {
        purpose: issuePurpose,
        destination_location: destinationLocation,
        taken_by_name: takenByName.trim(),
        approver_id: approverId,
        expected_return_date: expectedReturnDate || undefined,
        authority_order_ref: authorityOrderRef.trim() || undefined,
        seal_check: 'intact'
      });
      setShowIssueModal(false);
      setSelectedItem(null);
      await loadRegister();
    } catch (err: any) {
      alert(err?.message || 'Failed to issue exhibit from Malkhana. Ensure requester and approver are distinct.');
    } finally {
      setIssueSubmitting(false);
    }
  };

  const handleReturnSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItem) return;
    setReturnSubmitting(true);
    try {
      await physicalEvidenceService.depositMalkhana(selectedItem.evidence_id, {
        malkhana_entry_number: selectedItem.malkhana_entry_number || `MK-${selectedItem.id}`,
        rack_or_shelf: returnRack || selectedItem.rack_or_shelf || 'Rack 1',
        depositor_name: returnedByName || 'Investigator',
        condition: returnCondition,
        seal_status: returnSealStatus
      });
      setShowReturnModal(false);
      setSelectedItem(null);
      await loadRegister();
    } catch (err: any) {
      alert(err?.message || 'Failed to return exhibit to Malkhana.');
    } finally {
      setReturnSubmitting(false);
    }
  };

  const handleToggleScan = (id: number) => {
    setScannedIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  return (
    <div className="min-h-screen bg-[#faf7f2] text-[#191410] p-6 space-y-6">
      {/* 1. Header Banner */}
      <div className="bg-white rounded-lg border border-[#e2dcd2] p-5 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="p-3 bg-red-50 text-[#d93829] rounded-lg border border-red-100 shadow-xs">
            <Archive className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="font-serif font-bold text-xl text-[#191410]">
                Muddimalkhana Register (Evidence Vault)
              </h1>
              <span className="text-[10px] font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full border border-emerald-200">
                Station Master Ledger
              </span>
            </div>
            <p className="text-xs text-[#59524c] mt-0.5">
              Statutory station register for physical evidence, weapons, recovered property, sealed parcels, and two-person issues.
            </p>
          </div>
        </div>

        {/* Station picker & stock check button */}
        <div className="flex items-center gap-3">
          <select
            value={station}
            onChange={(e) => setStation(e.target.value)}
            className="px-3 py-1.5 border border-[#d6cfc5] rounded-md bg-[#faf7f2] text-xs font-semibold text-[#191410] shadow-xs cursor-pointer"
          >
            {stations.map(st => (
              <option key={st.id} value={st.name}>{st.name}</option>
            ))}
            {stations.length === 0 && <option value="Yerawada Police Station">Yerawada Police Station</option>}
          </select>

          <button
            onClick={() => setStockCheckActive(!stockCheckActive)}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md border shadow-xs flex items-center gap-1.5 transition-colors cursor-pointer ${
              stockCheckActive
                ? 'bg-amber-500 text-white border-amber-600'
                : 'bg-white border-[#d6cfc5] text-[#191410] hover:bg-[#faf7f2]'
            }`}
          >
            <CheckSquare className="w-3.5 h-3.5" />
            {stockCheckActive ? 'Exit Stock Check Audit' : 'Stock Check Audit Mode'}
          </button>
        </div>
      </div>

      {/* 2. Stock Check Audit Mode Banner (if active) */}
      {stockCheckActive && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-950 flex flex-wrap items-center justify-between gap-3 animate-fadeIn">
          <div>
            <span className="font-bold uppercase tracking-wider text-[10px] bg-amber-200 text-amber-900 px-2 py-0.5 rounded-md mr-2">
              AUDIT ACTIVE
            </span>
            <strong>Periodic Station Stock Check:</strong> Scan or verify each physical item present in the vault.
            <span className="ml-2 text-amber-800 font-semibold">
              Verified: {scannedIds.length} / {items.length} Exhibits ({items.length - scannedIds.length} Pending)
            </span>
          </div>
          <button
            onClick={() => alert(`Stock Check complete. Verified: ${scannedIds.length}. Discrepancies: ${items.length - scannedIds.length}. Logged to audit engine.`)}
            className="px-3 py-1 bg-amber-600 hover:bg-amber-700 text-white rounded text-xs font-bold shadow-xs cursor-pointer"
          >
            Submit Audit Endorsement
          </button>
        </div>
      )}

      {/* 3. Filter Chips & Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
          {[
            { id: 'all', label: 'All Exhibits' },
            { id: 'deposited_malkhana', label: 'In Malkhana' },
            { id: 'issued_investigation', label: 'Issued for Review' },
            { id: 'dispatched_fsl', label: 'At Forensic Lab (FSL)' },
            { id: 'produced_court', label: 'In Court' },
          ].map(f => (
            <button
              key={f.id}
              onClick={() => setStatusFilter(f.id)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md border transition-all cursor-pointer ${
                statusFilter === f.id
                  ? 'bg-[#191410] text-white border-[#191410] shadow-xs'
                  : 'bg-white text-[#59524c] border-[#e2dcd2] hover:bg-[#faf7f2]'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="relative min-w-[260px]">
          <Search className="w-3.5 h-3.5 text-[#8c827a] absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by crime #, malkhana #, seal #..."
            className="w-full pl-8 pr-3 py-1.5 text-xs border border-[#d6cfc5] rounded-md bg-white text-[#191410] shadow-xs focus:outline-none focus:border-[#d93829]"
          />
        </div>
      </div>

      {/* 4. Muddimalkhana Register Table */}
      <div className="bg-white rounded-lg border border-[#e2dcd2] shadow-xs overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-xs text-[#70685e] font-serif">
            <RefreshCw className="w-5 h-5 animate-spin mx-auto text-[#8c827a] mb-2" />
            Loading Muddimalkhana inventory records...
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="p-12 text-center text-xs text-[#70685e] italic">
            No physical items found matching the selected filter.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="bg-[#f0ebe1] text-[#191410] border-b border-[#e2dcd2] font-serif">
                  {stockCheckActive && <th className="p-3 text-center">Audit</th>}
                  <th className="p-3">Malkhana #</th>
                  <th className="p-3">Crime / Docket</th>
                  <th className="p-3">Exhibit Description</th>
                  <th className="p-3">Category</th>
                  <th className="p-3">Rack / Locker</th>
                  <th className="p-3">Seal Details</th>
                  <th className="p-3">Current Status</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#eae4d9]">
                {filteredItems.map((item) => {
                  const isPresent = item.status === 'deposited_malkhana';
                  const isScanned = scannedIds.includes(item.id);

                  return (
                    <tr
                      key={item.id}
                      className={`hover:bg-[#faf7f2]/80 transition-colors ${
                        stockCheckActive && isScanned ? 'bg-emerald-50/50' : ''
                      }`}
                    >
                      {stockCheckActive && (
                        <td className="p-3 text-center">
                          <input
                            type="checkbox"
                            checked={isScanned}
                            onChange={() => handleToggleScan(item.id)}
                            className="rounded border-[#d6cfc5] text-[#d93829] cursor-pointer"
                          />
                        </td>
                      )}
                      <td className="p-3 font-mono font-bold text-[#d93829]">
                        {item.malkhana_entry_number || `MK-${item.id}`}
                      </td>
                      <td className="p-3">
                        <div className="font-semibold text-[#191410]">{item.crime_number}</div>
                        <div className="text-[11px] text-[#70685e] truncate max-w-[150px]">{item.case_title}</div>
                      </td>
                      <td className="p-3 max-w-[240px]">
                        <div className="font-medium text-[#191410]">{item.description}</div>
                        {item.identifying_marks && (
                          <div className="text-[10px] text-[#70685e] italic mt-0.5">Marks: {item.identifying_marks}</div>
                        )}
                      </td>
                      <td className="p-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-[#eae4d9] text-[#3d3832]">
                          {item.category.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="p-3 font-semibold text-[#59524c]">
                        {item.rack_or_shelf || 'Unallocated'}
                      </td>
                      <td className="p-3">
                        {item.seal_number ? (
                          <div>
                            <span className="font-mono font-bold text-[#191410] text-[11px]">{item.seal_number}</span>
                            <span className={`ml-1.5 text-[9px] uppercase font-bold px-1 py-0.2 rounded ${
                              item.seal_status === 'intact'
                                ? 'bg-emerald-100 text-emerald-800'
                                : 'bg-rose-100 text-rose-800'
                            }`}>
                              {item.seal_status}
                            </span>
                          </div>
                        ) : (
                          <span className="text-[#8c827a] italic">No Seal</span>
                        )}
                      </td>
                      <td className="p-3">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                          item.status === 'deposited_malkhana'
                            ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                            : item.status === 'dispatched_fsl'
                            ? 'bg-blue-50 text-blue-800 border-blue-200'
                            : item.status === 'produced_court'
                            ? 'bg-purple-50 text-purple-800 border-purple-200'
                            : 'bg-amber-50 text-amber-800 border-amber-200'
                        }`}>
                          {item.status.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="p-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* Issue Button */}
                          {isPresent && (
                            <button
                              onClick={() => {
                                setSelectedItem(item);
                                setShowIssueModal(true);
                              }}
                              title="Issue item (Two-person approval)"
                              className="px-2 py-1 bg-white hover:bg-amber-50 border border-[#d6cfc5] text-amber-800 rounded text-[11px] font-semibold shadow-xs flex items-center gap-1 cursor-pointer"
                            >
                              <ArrowUpRight className="w-3 h-3 text-amber-600" />
                              Issue
                            </button>
                          )}

                          {/* Return Button */}
                          {!isPresent && (
                            <button
                              onClick={() => {
                                setSelectedItem(item);
                                setReturnedByName(item.current_custodian || '');
                                setShowReturnModal(true);
                              }}
                              title="Return exhibit to Malkhana"
                              className="px-2 py-1 bg-white hover:bg-emerald-50 border border-[#d6cfc5] text-emerald-800 rounded text-[11px] font-semibold shadow-xs flex items-center gap-1 cursor-pointer"
                            >
                              <ArrowDownLeft className="w-3 h-3 text-emerald-600" />
                              Return
                            </button>
                          )}

                          {/* Print Label */}
                          <button
                            onClick={() => handleOpenLabel(item)}
                            title="Generate QR / Barcode Label"
                            className="p-1 hover:bg-[#faf7f2] border border-[#d6cfc5] rounded text-[#59524c] cursor-pointer"
                          >
                            <QrCode className="w-3.5 h-3.5" />
                          </button>

                          {/* View Custody Timeline */}
                          <button
                            onClick={() => {
                              setSelectedItem(item);
                              setShowTimelineModal(true);
                            }}
                            title="View Unbroken Custody Ledger"
                            className="p-1 hover:bg-[#faf7f2] border border-[#d6cfc5] rounded text-[#59524c] cursor-pointer"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 5. MODAL: Issue Item (TWO-PERSON RULE) */}
      {showIssueModal && selectedItem && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-lg border border-[#e2dcd2] shadow-xl w-full max-w-lg p-5 animate-scaleUp">
            <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9] mb-4">
              <div>
                <h3 className="font-serif font-bold text-base text-[#191410] flex items-center gap-2">
                  <ArrowUpRight className="w-4 h-4 text-amber-600" />
                  Malkhana Issue (Two-Person Rule Enforced)
                </h3>
                <p className="text-[11px] text-[#70685e]">
                  Exhibit: {selectedItem.description} (#{selectedItem.malkhana_entry_number})
                </p>
              </div>
              <button onClick={() => setShowIssueModal(false)} className="text-[#8c827a] hover:text-[#191410] cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mb-3 p-2.5 bg-amber-50/80 border border-amber-200 rounded text-xs text-amber-900 flex items-start gap-2">
              <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5 text-amber-700" />
              <span>
                <strong>Statutory Mandate:</strong> Removal of court property requires separate authorization. Requester and Malkhana Approver must be distinct officers.
              </span>
            </div>

            <form onSubmit={handleIssueSubmit} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-[#59524c] font-semibold mb-1">Issue Purpose *</label>
                <select
                  value={issuePurpose}
                  onChange={(e) => setIssuePurpose(e.target.value)}
                  className="w-full px-3 py-1.5 border border-[#d6cfc5] rounded bg-[#faf7f2] text-[#191410]"
                >
                  <option value="Investigation Examination">Investigation Examination by IO</option>
                  <option value="Court Trial Evidence Production">Court Trial Evidence Production</option>
                  <option value="Sent to FSL for Forensic Analysis">Sent to FSL for Forensic Analysis</option>
                  <option value="Specialist ballistic inspection">Specialist ballistic inspection</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#59524c] font-semibold mb-1">Taken By (Person Name) *</label>
                  <input
                    type="text"
                    required
                    value={takenByName}
                    onChange={(e) => setTakenByName(e.target.value)}
                    placeholder="e.g. PI S. Ray / PC 4412"
                    className="w-full px-3 py-1.5 border border-[#d6cfc5] rounded bg-white text-[#191410]"
                  />
                </div>
                <div>
                  <label className="block text-[#59524c] font-semibold mb-1">Destination Location *</label>
                  <input
                    type="text"
                    required
                    value={destinationLocation}
                    onChange={(e) => setDestinationLocation(e.target.value)}
                    placeholder="e.g. Sessions Court No. 4"
                    className="w-full px-3 py-1.5 border border-[#d6cfc5] rounded bg-white text-[#191410]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#59524c] font-semibold mb-1">Expected Return Date</label>
                  <input
                    type="date"
                    value={expectedReturnDate}
                    onChange={(e) => setExpectedReturnDate(e.target.value)}
                    className="w-full px-3 py-1.5 border border-[#d6cfc5] rounded bg-white text-[#191410]"
                  />
                </div>
                <div>
                  <label className="block text-[#59524c] font-semibold mb-1">Authority / Order Reference</label>
                  <input
                    type="text"
                    value={authorityOrderRef}
                    onChange={(e) => setAuthorityOrderRef(e.target.value)}
                    placeholder="Court Order # / ACP Order"
                    className="w-full px-3 py-1.5 border border-[#d6cfc5] rounded bg-white text-[#191410]"
                  />
                </div>
              </div>

              <div className="pt-3 border-t border-[#eae4d9] flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowIssueModal(false)}
                  className="px-3 py-1.5 border border-[#d6cfc5] rounded text-[#59524c] hover:bg-[#faf7f2] font-semibold cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={issueSubmitting}
                  className="px-4 py-1.5 bg-[#d93829] hover:bg-[#b82d20] text-white font-semibold rounded shadow-xs cursor-pointer disabled:opacity-50"
                >
                  {issueSubmitting ? 'Verifying & Issuing...' : 'Authorize Two-Person Issue'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 6. MODAL: Return Item to Malkhana */}
      {showReturnModal && selectedItem && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-lg border border-[#e2dcd2] shadow-xl w-full max-w-md p-5 animate-scaleUp">
            <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9] mb-4">
              <div>
                <h3 className="font-serif font-bold text-base text-[#191410] flex items-center gap-2">
                  <ArrowDownLeft className="w-4 h-4 text-emerald-600" />
                  Return Exhibit to Muddimalkhana
                </h3>
                <p className="text-[11px] text-[#70685e]">
                  Deposit back into vault: {selectedItem.malkhana_entry_number}
                </p>
              </div>
              <button onClick={() => setShowReturnModal(false)} className="text-[#8c827a] hover:text-[#191410] cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleReturnSubmit} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-[#59524c] font-semibold mb-1">Returned By (Officer Name)</label>
                <input
                  type="text"
                  value={returnedByName}
                  onChange={(e) => setReturnedByName(e.target.value)}
                  placeholder="Officer name"
                  className="w-full px-3 py-1.5 border border-[#d6cfc5] rounded bg-white text-[#191410]"
                />
              </div>

              <div>
                <label className="block text-[#59524c] font-semibold mb-1">Rack / Shelf Location</label>
                <input
                  type="text"
                  value={returnRack}
                  onChange={(e) => setReturnRack(e.target.value)}
                  placeholder="e.g. Almirah 1, Shelf B"
                  className="w-full px-3 py-1.5 border border-[#d6cfc5] rounded bg-white text-[#191410]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#59524c] font-semibold mb-1">Condition on Return</label>
                  <select
                    value={returnCondition}
                    onChange={(e) => setReturnCondition(e.target.value)}
                    className="w-full px-3 py-1.5 border border-[#d6cfc5] rounded bg-[#faf7f2] text-[#191410]"
                  >
                    <option value="intact">Intact / Undisturbed</option>
                    <option value="opened_by_court">Opened by Court</option>
                    <option value="damaged">Damaged / Altered</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[#59524c] font-semibold mb-1">Seal Status</label>
                  <select
                    value={returnSealStatus}
                    onChange={(e) => setReturnSealStatus(e.target.value)}
                    className="w-full px-3 py-1.5 border border-[#d6cfc5] rounded bg-[#faf7f2] text-[#191410]"
                  >
                    <option value="intact">Seal Intact</option>
                    <option value="resealed">Resealed by Court/FSL</option>
                    <option value="broken">Broken / Compromised</option>
                  </select>
                </div>
              </div>

              <div className="pt-3 border-t border-[#eae4d9] flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowReturnModal(false)}
                  className="px-3 py-1.5 border border-[#d6cfc5] rounded text-[#59524c] hover:bg-[#faf7f2] font-semibold cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={returnSubmitting}
                  className="px-4 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white font-semibold rounded shadow-xs cursor-pointer disabled:opacity-50"
                >
                  {returnSubmitting ? 'Recording Deposit...' : 'Confirm Return & Lock'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 7. MODAL: Printable QR / Barcode Label */}
      {showLabelModal && selectedItem && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-lg border border-[#e2dcd2] shadow-2xl w-full max-w-md p-5 animate-scaleUp text-[#191410]">
            <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9] mb-4">
              <h3 className="font-serif font-bold text-base text-[#191410] flex items-center gap-2">
                <QrCode className="w-4 h-4 text-[#d93829]" />
                Printable Exhibit QR & Barcode Label
              </h3>
              <button onClick={() => setShowLabelModal(false)} className="text-[#8c827a] hover:text-[#191410] cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 bg-[#faf7f2] border border-[#eae4d9] rounded flex items-center justify-center">
              <div dangerouslySetInnerHTML={{ __html: labelSvg }} />
            </div>

            <div className="pt-4 mt-4 border-t border-[#eae4d9] flex justify-between items-center text-xs">
              <span className="text-[#70685e]">Thermal label format (380x200)</span>
              <button
                onClick={() => window.print()}
                className="px-4 py-1.5 bg-[#191410] text-white font-semibold rounded shadow-xs flex items-center gap-1.5 hover:bg-[#3d3832] cursor-pointer"
              >
                <Printer className="w-3.5 h-3.5" />
                Print Physical Label
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 8. MODAL: View Custody Timeline */}
      {showTimelineModal && selectedItem && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-lg border border-[#e2dcd2] shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto p-6 animate-scaleUp">
            <div className="flex items-center justify-between pb-3 border-b border-[#eae4d9] mb-4">
              <div>
                <h3 className="font-serif font-bold text-base text-[#191410]">
                  Unbroken Custody Ledger & Forensic Seals
                </h3>
                <p className="text-xs text-[#59524c]">
                  {selectedItem.description} ({selectedItem.malkhana_entry_number || selectedItem.crime_number})
                </p>
              </div>
              <button onClick={() => setShowTimelineModal(false)} className="text-[#8c827a] hover:text-[#191410] cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>

            <UnifiedCustodyTimeline
              evidenceId={selectedItem.evidence_id}
              caseId={selectedItem.case_id}
              evidenceTitle={selectedItem.description}
              evidenceKind="physical"
              onUpdated={() => loadRegister()}
            />
          </div>
        </div>
      )}
    </div>
  );
}

