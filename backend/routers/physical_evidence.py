"""
backend/routers/physical_evidence.py
====================================
API Router for Physical Evidence Tracking, Extended Chained Custody,
Seals with OCR Verification, Muddimalkhana Station Register, and FSL Dispatches.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Case, Evidence, CustodyLog, User, CasePerson,
    PhysicalItem, Seal, SealEvent, FSLDispatch, FSLDispatchItem,
    MalkhanaStockCheck
)
from schemas import (
    PhysicalItemCreate, PhysicalItemOut, CustodyHandoverRequest,
    CustodyLogExtendedOut, ContinuityCheckOut, SealCreateRequest,
    SealOut, SealEventCreateRequest, SealEventOut, MalkhanaDepositRequest,
    MalkhanaIssueRequest, MalkhanaRegisterItemOut, MalkhanaStockCheckCreate,
    MalkhanaStockCheckOut, FSLDispatchCreateRequest, FSLDispatchOut,
    FSLReturnRequest, OCRSealCompareRequest, OCRSealCompareOut
)
from auth import get_current_user, check_case_access
from physical_evidence_engine import (
    append_chained_custody_entry, verify_custody_chain, evaluate_custody_continuity,
    apply_new_seal, record_seal_event, compare_seal_ocr_number,
    get_malkhana_register, deposit_into_malkhana, issue_from_malkhana,
    generate_malkhana_barcode_label, create_fsl_dispatch,
    record_fsl_lab_receipt, record_fsl_items_return
)
from audit_engine import log_audit_event


router = APIRouter(tags=["Physical Evidence & Forensics Custody"])


def resolve_case_id(case_identifier: str, db: Session) -> int:
    """Helper to resolve '1', 'C-1', or crime_number to internal integer case_id."""
    clean_id = str(case_identifier).replace("C-", "").strip()
    if clean_id.isdigit():
        c = db.query(Case).filter(Case.id == int(clean_id)).first()
        if c:
            return c.id
    c = db.query(Case).filter(Case.crime_number == case_identifier).first()
    if c:
        return c.id
    raise HTTPException(status_code=404, detail=f"Case docket '{case_identifier}' not found.")


# ==============================================================================
# 1. PHYSICAL EVIDENCE CRUD
# ==============================================================================

@router.post("/cases/{case_id}/physical-evidence", response_model=PhysicalItemOut)
def register_physical_evidence(
    case_id: str,
    payload: PhysicalItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Registers a physical forensic article (weapon, clothing, biological sample, vehicle, etc.)
    as a first-class exhibit without requiring a digital file on disk.
    Automatically logs initial SEIZED custody entry.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "write"):
        raise HTTPException(status_code=403, detail="Permission denied to register evidence in this case.")

    # 1. Create Exhibit row
    exhibit = Evidence(
        case_id=real_case_id,
        evidence_kind="physical",
        file_name=payload.description[:60],  # Summary title
        file_type="Physical Article",
        evidence_type=payload.category,
        uploaded_by=(current_user.full_name if hasattr(current_user, 'full_name') and current_user.full_name else current_user.email) or current_user.email,
        collected_by=payload.seized_by_name or (current_user.full_name if hasattr(current_user, 'full_name') and current_user.full_name else current_user.email),
        collection_date=datetime.now(timezone.utc),
        custody_notes=f"Physical Exhibit recovered from: {payload.seized_from or 'Scene'}. Packaging: {payload.packaging}",
        chain_of_custody_complete=True,
        hash_verified=True,
        quality_rating=4.5
    )
    db.add(exhibit)
    db.commit()
    db.refresh(exhibit)

    # 2. Create 1-to-1 PhysicalItem record
    phys = PhysicalItem(
        evidence_id=exhibit.id,
        category=payload.category,
        description=payload.description,
        identifying_marks=payload.identifying_marks,
        quantity_or_weight=payload.quantity_or_weight,
        condition=payload.condition,
        packaging=payload.packaging,
        seized_from=payload.seized_from,
        seized_at=payload.seized_at,
        seized_by_id=current_user.id,
        seized_by_name=payload.seized_by_name or (current_user.full_name if hasattr(current_user, 'full_name') and current_user.full_name else current_user.email),
        seizure_memo_id=payload.seizure_memo_id,
        panch_witness_1_id=payload.panch_witness_1_id,
        panch_witness_2_id=payload.panch_witness_2_id,
        current_location=payload.current_location,
        current_custodian=payload.current_custodian or (current_user.full_name if hasattr(current_user, 'full_name') and current_user.full_name else current_user.email),
        malkhana_entry_number=payload.malkhana_entry_number,
        rack_or_shelf=payload.rack_or_shelf,
        status="deposited_malkhana" if payload.current_location == "malkhana" else "seized",
        is_perishable=payload.is_perishable,
        is_biological=payload.is_biological,
        is_firearm=payload.is_firearm,
        is_narcotics=payload.is_narcotics,
        dispatch_time_limit_days=payload.dispatch_time_limit_days or (3 if payload.is_biological else None)
    )
    db.add(phys)
    db.commit()
    db.refresh(phys)

    # 3. Create Genesis Custody Entry
    append_chained_custody_entry(
        db=db,
        evidence_id=exhibit.id,
        case_id=real_case_id,
        action="SEIZED",
        actor_name=(current_user.full_name if hasattr(current_user, 'full_name') and current_user.full_name else current_user.email) or current_user.email,
        actor_id=current_user.id,
        actor_role="investigator",
        from_location=payload.seized_at or "Scene of Crime",
        to_person_id=current_user.id,
        to_person_name=(current_user.full_name if hasattr(current_user, 'full_name') and current_user.full_name else current_user.email) or current_user.email,
        to_location=payload.current_location,
        purpose="Recovery and Seizure under Panchnama",
        condition_at_handover=payload.condition,
        seal_status_check="intact",
        notes=f"Seized from {payload.seized_from or 'Scene'}. Packed in {payload.packaging}."
    )

    return PhysicalItemOut(
        id=phys.id,
        evidence_id=exhibit.id,
        case_id=real_case_id,
        category=phys.category,
        description=phys.description,
        identifying_marks=phys.identifying_marks,
        quantity_or_weight=phys.quantity_or_weight,
        condition=phys.condition,
        packaging=phys.packaging,
        seized_from=phys.seized_from,
        seized_at=phys.seized_at,
        seized_by_id=phys.seized_by_id,
        seized_by_name=phys.seized_by_name,
        seizure_memo_id=phys.seizure_memo_id,
        panch_witness_1_id=phys.panch_witness_1_id,
        panch_witness_2_id=phys.panch_witness_2_id,
        current_location=phys.current_location,
        current_custodian=phys.current_custodian,
        malkhana_entry_number=phys.malkhana_entry_number,
        rack_or_shelf=phys.rack_or_shelf,
        status=phys.status,
        is_perishable=phys.is_perishable,
        is_biological=phys.is_biological,
        is_firearm=phys.is_firearm,
        is_narcotics=phys.is_narcotics,
        dispatch_time_limit_days=phys.dispatch_time_limit_days,
        created_at=phys.created_at
    )


@router.get("/cases/{case_id}/physical-evidence", response_model=List[PhysicalItemOut])
def list_physical_evidence(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all physical forensic exhibits registered for a case docket."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied.")

    items = (
        db.query(PhysicalItem, Evidence)
        .join(Evidence, PhysicalItem.evidence_id == Evidence.id)
        .filter(Evidence.case_id == real_case_id)
        .order_by(PhysicalItem.id.desc())
        .all()
    )

    out = []
    for phys, ev in items:
        out.append(PhysicalItemOut(
            id=phys.id,
            evidence_id=ev.id,
            case_id=ev.case_id,
            category=phys.category,
            description=phys.description,
            identifying_marks=phys.identifying_marks,
            quantity_or_weight=phys.quantity_or_weight,
            condition=phys.condition,
            packaging=phys.packaging,
            seized_from=phys.seized_from,
            seized_at=phys.seized_at,
            seized_by_id=phys.seized_by_id,
            seized_by_name=phys.seized_by_name,
            seizure_memo_id=phys.seizure_memo_id,
            panch_witness_1_id=phys.panch_witness_1_id,
            panch_witness_2_id=phys.panch_witness_2_id,
            current_location=phys.current_location,
            current_custodian=phys.current_custodian,
            malkhana_entry_number=phys.malkhana_entry_number,
            rack_or_shelf=phys.rack_or_shelf,
            status=phys.status,
            is_perishable=phys.is_perishable,
            is_biological=phys.is_biological,
            is_firearm=phys.is_firearm,
            is_narcotics=phys.is_narcotics,
            dispatch_time_limit_days=phys.dispatch_time_limit_days,
            created_at=phys.created_at
        ))
    return out


@router.get("/physical-evidence/{evidence_id}", response_model=PhysicalItemOut)
def get_physical_evidence_details(
    evidence_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves full forensic details for a physical exhibit."""
    phys = db.query(PhysicalItem).filter(PhysicalItem.evidence_id == evidence_id).first()
    if not phys:
        raise HTTPException(status_code=404, detail=f"Physical item for exhibit #{evidence_id} not found.")

    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    return PhysicalItemOut(
        id=phys.id,
        evidence_id=ev.id,
        case_id=ev.case_id,
        category=phys.category,
        description=phys.description,
        identifying_marks=phys.identifying_marks,
        quantity_or_weight=phys.quantity_or_weight,
        condition=phys.condition,
        packaging=phys.packaging,
        seized_from=phys.seized_from,
        seized_at=phys.seized_at,
        seized_by_id=phys.seized_by_id,
        seized_by_name=phys.seized_by_name,
        seizure_memo_id=phys.seizure_memo_id,
        panch_witness_1_id=phys.panch_witness_1_id,
        panch_witness_2_id=phys.panch_witness_2_id,
        current_location=phys.current_location,
        current_custodian=phys.current_custodian,
        malkhana_entry_number=phys.malkhana_entry_number,
        rack_or_shelf=phys.rack_or_shelf,
        status=phys.status,
        is_perishable=phys.is_perishable,
        is_biological=phys.is_biological,
        is_firearm=phys.is_firearm,
        is_narcotics=phys.is_narcotics,
        dispatch_time_limit_days=phys.dispatch_time_limit_days,
        created_at=phys.created_at
    )


# ==============================================================================
# 2. EXTENDED CHAINED CUSTODY & CONTINUITY CHECKER
# ==============================================================================

@router.post("/physical-evidence/{evidence_id}/custody-handover", response_model=CustodyLogExtendedOut)
def record_custody_transfer(
    evidence_id: int,
    payload: CustodyHandoverRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Records an immutable, cryptographically chained custody transfer entry for an exhibit.
    """
    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found.")

    if not check_case_access(ev.case_id, current_user, db, "write"):
        raise HTTPException(status_code=403, detail="Permission denied.")

    entry = append_chained_custody_entry(
        db=db,
        evidence_id=evidence_id,
        case_id=ev.case_id,
        action=payload.action,
        actor_name=(current_user.full_name if hasattr(current_user, 'full_name') and current_user.full_name else current_user.email) or current_user.email,
        actor_id=current_user.id,
        actor_role=current_user.role or "investigator",
        from_person_id=payload.from_person_id or current_user.id,
        from_person_name=payload.from_person_name or (current_user.full_name if hasattr(current_user, 'full_name') and current_user.full_name else current_user.email),
        from_location=payload.from_location,
        to_person_id=payload.to_person_id,
        to_person_name=payload.to_person_name,
        to_location=payload.to_location,
        purpose=payload.purpose,
        condition_at_handover=payload.condition_at_handover,
        seal_status_check=payload.seal_status_check,
        expected_return_date=payload.expected_return_date,
        authority_order_ref=payload.authority_order_ref,
        acknowledgement_type=payload.acknowledgement_type,
        acknowledgement_data=payload.acknowledgement_data,
        attached_photos=payload.attached_photos,
        notes=payload.notes
    )

    # Sync physical item status if exists
    phys = db.query(PhysicalItem).filter(PhysicalItem.evidence_id == evidence_id).first()
    if phys:
        phys.current_location = payload.to_location
        phys.current_custodian = payload.to_person_name
        phys.condition = payload.condition_at_handover or phys.condition
        db.commit()

    return entry


@router.get("/physical-evidence/{evidence_id}/continuity", response_model=ContinuityCheckOut)
def check_evidence_continuity(
    evidence_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Runs the automated Continuity Checker on an exhibit's custody ledger.
    Detects gaps, unexplained location jumps, long transit silences, and seal problems.
    """
    res = evaluate_custody_continuity(evidence_id, db)
    if res.get("status") == "error":
        raise HTTPException(status_code=404, detail=res["message"])
    return res


@router.get("/evidence/{evidence_id}/custody-ledger", response_model=List[CustodyLogExtendedOut])
def get_custody_ledger(
    evidence_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns the complete chronological custody ledger for either digital or physical exhibits."""
    entries = (
        db.query(CustodyLog)
        .filter(CustodyLog.evidence_id == evidence_id)
        .order_by(CustodyLog.id.asc())
        .all()
    )
    return entries


# ==============================================================================
# 3. SEALS & SEAL EVENTS WITH OCR VERIFICATION
# ==============================================================================

@router.post("/physical-evidence/{evidence_id}/seals", response_model=SealOut)
def create_seal_for_evidence(
    evidence_id: int,
    payload: SealCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Applies a new forensic seal to a physical evidence package."""
    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found.")

    seal = apply_new_seal(
        case_id=ev.case_id,
        evidence_id=evidence_id,
        seal_number=payload.seal_number,
        owner_mark=payload.owner_mark,
        package_description=payload.package_description or "Forensic parcel",
        applied_by_user=current_user,
        applied_in_presence_of=payload.applied_in_presence_of or [],
        photos=payload.photos,
        db=db
    )
    return seal


@router.get("/physical-evidence/{evidence_id}/seals", response_model=List[SealOut])
def list_seals_for_evidence(
    evidence_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all seals (active and historical replaced seals) for an exhibit."""
    seals = db.query(Seal).filter(Seal.evidence_id == evidence_id).order_by(Seal.id.desc()).all()
    return seals


@router.post("/seals/{seal_id}/events", response_model=SealEventOut)
def record_event_on_seal(
    seal_id: int,
    payload: SealEventCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enforces the Seal State Machine (inspect, break, reseal).
    Broken seals can never jump back to intact directly; reseal creates a new chained seal.
    """
    try:
        event, _ = record_seal_event(
            seal_id=seal_id,
            event_type=payload.event_type,
            actor_user=current_user,
            reason=payload.reason,
            witnesses=payload.witnesses,
            photos=payload.photos,
            new_seal_data=payload.new_seal_data,
            db=db
        )
        return event
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/physical-evidence/ocr-compare", response_model=OCRSealCompareOut)
def check_ocr_seal(payload: OCRSealCompareRequest):
    """Compares claimed seal number with OCR text detected in photo."""
    return compare_seal_ocr_number(payload.claimed_seal, payload.ocr_detected_text)


# ==============================================================================
# 4. MALKHANA STATION-LEVEL REGISTER & MOVEMENTS
# ==============================================================================

@router.get("/malkhana/register", response_model=List[MalkhanaRegisterItemOut])
def get_station_malkhana_register(
    police_station: str = Query("Yerawada Police Station"),
    case_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns station-level Muddimalkhana inventory with rack allocations and seal status."""
    return get_malkhana_register(
        police_station=police_station,
        case_id=case_id,
        status_filter=status,
        db=db
    )


@router.post("/malkhana/deposit")
def deposit_evidence_into_malkhana(
    evidence_id: int,
    payload: MalkhanaDepositRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deposits an item into the Malkhana (MALKHANA_IN) with rack allocation."""
    try:
        return deposit_into_malkhana(
            evidence_id=evidence_id,
            malkhana_entry_number=payload.malkhana_entry_number,
            rack_or_shelf=payload.rack_or_shelf,
            depositor_name=payload.depositor_name,
            received_by_user=current_user,
            condition=payload.condition,
            seal_status=payload.seal_status,
            photos=payload.photos,
            db=db
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/malkhana/issue")
def issue_evidence_from_malkhana(
    evidence_id: int,
    payload: MalkhanaIssueRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Issues an item from the Malkhana (MALKHANA_OUT).
    Enforces TWO-PERSON RULE: Approver must be distinct from Requester!
    """
    approver = db.query(User).filter(User.id == payload.approver_id).first()
    if not approver:
        raise HTTPException(status_code=404, detail="Approving Officer not found.")

    try:
        return issue_from_malkhana(
            evidence_id=evidence_id,
            purpose=payload.purpose,
            requested_by_user=current_user,
            approved_by_user=approver,
            taken_by_name=payload.taken_by_name,
            destination_location=payload.destination_location,
            expected_return_date=payload.expected_return_date,
            authority_order_ref=payload.authority_order_ref,
            seal_check=payload.seal_check,
            notes=payload.notes,
            db=db
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/physical-evidence/{evidence_id}/barcode-label")
def get_barcode_label(
    evidence_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generates printable SVG barcode / QR label for physical evidence envelope."""
    return generate_malkhana_barcode_label(evidence_id, db)


@router.post("/malkhana/stock-checks", response_model=MalkhanaStockCheckOut)
def record_malkhana_stock_audit(
    payload: MalkhanaStockCheckCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Records a periodic station inventory audit for Muddimalkhana."""
    check = MalkhanaStockCheck(
        police_station=payload.police_station,
        conducted_by_id=current_user.id,
        conducted_by_name=(current_user.full_name if hasattr(current_user, 'full_name') and current_user.full_name else current_user.email) or current_user.email,
        total_items_expected=payload.total_items_expected,
        items_verified_present=payload.items_verified_present,
        discrepancies_count=payload.discrepancies_count,
        discrepancies_details=payload.discrepancies_details,
        status="discrepancy_reported" if payload.discrepancies_count > 0 else "completed",
        supervisor_notes=payload.supervisor_notes
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return check


@router.get("/malkhana/stock-checks", response_model=List[MalkhanaStockCheckOut])
def list_malkhana_stock_audits(
    police_station: str = Query("Yerawada Police Station"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists stock check history for station."""
    return (
        db.query(MalkhanaStockCheck)
        .filter(MalkhanaStockCheck.police_station == police_station)
        .order_by(MalkhanaStockCheck.id.desc())
        .all()
    )


# ==============================================================================
# 5. FSL DISPATCH & RETURN LIFECYCLE
# ==============================================================================

@router.post("/cases/{case_id}/fsl-dispatches", response_model=FSLDispatchOut)
def dispatch_to_fsl(
    case_id: str,
    payload: FSLDispatchCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates FSL forwarding letter dispatch, bundles items, and records SENT_TO_FSL."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "write"):
        raise HTTPException(status_code=403, detail="Permission denied.")

    dispatch = create_fsl_dispatch(
        case_id=real_case_id,
        forwarding_letter_number=payload.forwarding_letter_number,
        forwarding_letter_date=payload.forwarding_letter_date,
        fsl_name=payload.fsl_name,
        examination_requested=payload.examination_requested,
        carried_by_name=payload.carried_by_name,
        carried_by_role=payload.carried_by_role or "Police Constable",
        carried_by_id_card=payload.carried_by_id_card or "PC-4412",
        mode_of_transit=payload.mode_of_transit,
        expected_report_date=payload.expected_report_date,
        item_evidence_ids=payload.item_evidence_ids,
        current_user=current_user,
        db=db
    )
    return dispatch


@router.get("/cases/{case_id}/fsl-dispatches", response_model=List[FSLDispatchOut])
def list_fsl_dispatches_for_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all FSL dispatches for a case docket."""
    real_case_id = resolve_case_id(case_id, db)
    return (
        db.query(FSLDispatch)
        .filter(FSLDispatch.case_id == real_case_id)
        .order_by(FSLDispatch.id.desc())
        .all()
    )


@router.post("/fsl-dispatches/{dispatch_id}/acknowledge")
def acknowledge_fsl_lab_receipt(
    dispatch_id: int,
    receipt_scan_path: str = Query(...),
    ack_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Records lab acknowledgment receipt, moving dispatch to 'received_by_lab'."""
    try:
        return record_fsl_lab_receipt(
            dispatch_id=dispatch_id,
            receipt_scan_path=receipt_scan_path,
            ack_date=ack_date or datetime.now(timezone.utc),
            current_user=current_user,
            db=db
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/fsl-dispatches/{dispatch_id}/return")
def return_fsl_items(
    dispatch_id: int,
    payload: FSLReturnRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Records items returned from FSL with new lab seals and custody logs."""
    try:
        return record_fsl_items_return(
            dispatch_id=dispatch_id,
            return_date=payload.return_date,
            carried_by=payload.carried_by,
            item_returns=payload.item_returns,
            current_user=current_user,
            db=db
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==============================================================================
# 6. COURT CUSTODY CERTIFICATE GENERATION
# ==============================================================================

@router.get("/physical-evidence/{evidence_id}/court-certificate")
def get_court_custody_certificate(
    evidence_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generates official Court-Admissible Chain of Custody Certificate
    under Section 192/193 BNSS / Section 172 CrPC.
    """
    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found.")

    c = db.query(Case).filter(Case.id == ev.case_id).first()
    phys = db.query(PhysicalItem).filter(PhysicalItem.evidence_id == evidence_id).first()
    continuity = evaluate_custody_continuity(evidence_id, db)
    entries = db.query(CustodyLog).filter(CustodyLog.evidence_id == evidence_id).order_by(CustodyLog.id.asc()).all()

    ledger_rows = []
    for idx, log in enumerate(entries):
        ledger_rows.append({
            "step": idx + 1,
            "action": log.action,
            "timestamp": log.timestamp.strftime("%d-%b-%Y %H:%M:%S IST") if log.timestamp else "N/A",
            "actor": f"{log.actor_name} ({log.actor_role or 'Officer'})",
            "from_location": log.from_location or "N/A",
            "to_location": log.to_location or "N/A",
            "to_person": log.to_person_name or "N/A",
            "seal_status": log.seal_status_check or "N/A",
            "hash": log.current_log_hash[:16] + "..." if log.current_log_hash else "GENESIS"
        })

    certificate = {
        "certificate_title": "CERTIFICATE OF UNBROKEN CHAIN OF CUSTODY",
        "legal_provision": "Under Section 192/193 Bharatiya Nagarik Suraksha Sanhita (BNSS 2023) / Section 172 CrPC",
        "crime_number": c.crime_number or f"CR-{c.id}",
        "police_station": c.police_station or "Yerawada Police Station",
        "court_name": c.court_name or "Sessions Court, Pune",
        "evidence_id": evidence_id,
        "exhibit_kind": "Physical Forensic Article",
        "category": phys.category if phys else "Forensic Item",
        "description": phys.description if phys else ev.file_name,
        "identifying_marks": phys.identifying_marks if phys else "None",
        "malkhana_entry_number": phys.malkhana_entry_number if phys else "N/A",
        "continuity_status": continuity["status"].upper(),
        "hash_chain_verified": continuity["hash_chain_valid"],
        "total_transfers": len(entries),
        "certifying_officer": (current_user.full_name if hasattr(current_user, 'full_name') and current_user.full_name else current_user.email) or current_user.email,
        "generation_timestamp": datetime.now(timezone.utc).strftime("%d-%b-%Y %H:%M:%S UTC"),
        "ledger": ledger_rows
    }

    return certificate
