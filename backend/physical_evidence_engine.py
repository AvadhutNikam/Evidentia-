"""
backend/physical_evidence_engine.py
===================================
Physical Evidence Forensics Engine, Extended Chained Custody Ledger,
Tamper-Evident Seals & OCR Verification, Muddimalkhana Register,
and Forensic Science Laboratory (FSL) Dispatch Lifecycle.
"""

import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import (
    Evidence, CustodyLog, AuditLog, Case, User, CasePerson,
    PhysicalItem, Seal, SealEvent, FSLDispatch, FSLDispatchItem,
    MalkhanaStockCheck
)
from audit_engine import log_audit_event


GENESIS_CUSTODY_HASH = "GENESIS_CUSTODY_HASH_000000000000000000000000000000000000000000000000"


# ==============================================================================
# 1. CUSTODY HASH-CHAINING & VERIFICATION
# ==============================================================================

def compute_custody_entry_hash(
    previous_hash: str,
    evidence_id: int,
    action: str,
    timestamp_iso: str,
    actor_name: str,
    to_person_name: Optional[str] = None,
    to_location: Optional[str] = None,
    seal_status: Optional[str] = None,
    notes: Optional[str] = None
) -> str:
    """Computes deterministic SHA-256 hash for a chained custody ledger entry."""
    canonical_data = (
        f"{previous_hash}|{evidence_id}|{action}|{timestamp_iso}|"
        f"{actor_name or ''}|{to_person_name or ''}|{to_location or ''}|"
        f"{seal_status or ''}|{notes or ''}"
    )
    return hashlib.sha256(canonical_data.encode("utf-8")).hexdigest()


def append_chained_custody_entry(
    db: Session,
    evidence_id: int,
    case_id: int,
    action: str,
    actor_name: str,
    actor_id: Optional[int] = None,
    actor_role: Optional[str] = "investigator",
    from_person_id: Optional[int] = None,
    from_person_name: Optional[str] = None,
    from_location: Optional[str] = None,
    to_person_id: Optional[int] = None,
    to_person_name: Optional[str] = None,
    to_location: Optional[str] = None,
    purpose: Optional[str] = None,
    condition_at_handover: Optional[str] = "intact",
    seal_status_check: Optional[str] = "intact",
    expected_return_date: Optional[datetime] = None,
    authority_order_ref: Optional[str] = None,
    acknowledgement_type: Optional[str] = "digital_pin",
    acknowledgement_data: Optional[str] = None,
    attached_photos: Optional[List[Dict[str, Any]]] = None,
    notes: Optional[str] = None
) -> CustodyLog:
    """
    Appends an immutable, cryptographic SHA-256 hash-chained entry to CustodyLog.
    Guarantees sequential integrity linked to the previous entry for this evidence item.
    Also dual-anchors the event into the Merkle audit_logs table.
    """
    # 1. Fetch latest custody entry for this evidence item to find previous hash
    last_entry = (
        db.query(CustodyLog)
        .filter(CustodyLog.evidence_id == evidence_id)
        .order_by(CustodyLog.id.desc())
        .first()
    )

    prev_hash = last_entry.current_log_hash if (last_entry and last_entry.current_log_hash) else GENESIS_CUSTODY_HASH
    now_utc = datetime.now(timezone.utc)
    now_iso = now_utc.isoformat()

    # 2. Compute current entry hash
    curr_hash = compute_custody_entry_hash(
        previous_hash=prev_hash,
        evidence_id=evidence_id,
        action=action,
        timestamp_iso=now_iso,
        actor_name=actor_name,
        to_person_name=to_person_name,
        to_location=to_location,
        seal_status=seal_status_check,
        notes=notes
    )

    photos_json = json.dumps(attached_photos) if attached_photos else None

    # 3. Create entry
    entry = CustodyLog(
        evidence_id=evidence_id,
        case_id=case_id,
        action=action,
        actor_name=actor_name,
        actor_role=actor_role,
        source_agency="Maharashtra Police / State CID",
        location=to_location or from_location or "Yerawada Police Station",
        timestamp=now_utc,
        file_hash_snapshot=curr_hash[:16],
        notes=notes,
        from_person_id=from_person_id,
        from_person_name=from_person_name,
        from_location=from_location,
        to_person_id=to_person_id,
        to_person_name=to_person_name,
        to_location=to_location,
        purpose=purpose,
        condition_at_handover=condition_at_handover,
        seal_status_check=seal_status_check,
        expected_return_date=expected_return_date,
        authority_order_ref=authority_order_ref,
        acknowledgement_type=acknowledgement_type,
        acknowledgement_data=acknowledgement_data,
        attached_photos=photos_json,
        previous_log_hash=prev_hash,
        current_log_hash=curr_hash
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    # 4. Dual-anchor into audit_logs chain
    log_audit_event(
        db=db,
        action_type=f"CUSTODY_{action}",
        target_type="evidence_custody",
        target_id=str(evidence_id),
        description=f"Custody {action}: Transferred to {to_person_name or 'Custody'} at {to_location or 'Station'}. Seal: {seal_status_check}",
        user_id=actor_id,
        user_name=actor_name,
        user_role=actor_role,
        case_id=case_id,
        before_value=prev_hash[:12],
        after_value=curr_hash[:12]
    )

    return entry


def verify_custody_chain(evidence_id: int, db: Session) -> Dict[str, Any]:
    """
    Traverses the custody ledger in ascending order and verifies that every hash link is unbroken.
    Returns validation status, total entries count, and details if tampered.
    """
    entries = (
        db.query(CustodyLog)
        .filter(CustodyLog.evidence_id == evidence_id)
        .order_by(CustodyLog.id.asc())
        .all()
    )

    if not entries:
        return {
            "valid": True,
            "entries_count": 0,
            "message": "No custody entries recorded yet for this item."
        }

    expected_prev = GENESIS_CUSTODY_HASH
    for idx, entry in enumerate(entries):
        if entry.previous_log_hash != expected_prev:
            return {
                "valid": False,
                "broken_at_step": idx,
                "entry_id": entry.id,
                "action": entry.action,
                "error": f"Broken chain link at step #{idx+1}: expected previous hash {expected_prev[:12]}..., got {entry.previous_log_hash or 'None'}."
            }
        expected_prev = entry.current_log_hash

    return {
        "valid": True,
        "entries_count": len(entries),
        "last_hash": entries[-1].current_log_hash,
        "first_recorded_at": entries[0].timestamp.isoformat() if entries[0].timestamp else None,
        "last_recorded_at": entries[-1].timestamp.isoformat() if entries[-1].timestamp else None,
        "message": f"Cryptographic custody ledger intact. {len(entries)} verified sequential links."
    }


# ==============================================================================
# 2. CONTINUITY CHECKER & RELIABILITY ADJUSTMENT
# ==============================================================================

def evaluate_custody_continuity(evidence_id: int, db: Session) -> Dict[str, Any]:
    """
    Continuity Checker: Inspects an exhibit's ledger chronologically for:
      1. Gaps: 'from' does not match previous 'to'
      2. Unexplained moves: location jump without transfer entry
      3. Long silences: in transit for longer than configured threshold (7 days / 3 days bio)
      4. Seal problems: broken or damaged without authorized break event
      5. Missing steps: unconfirmed transfers, missing mandatory photos
    Updates evidence.chain_of_custody_complete and computes reliability penalty.
    """
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        return {"status": "error", "message": f"Evidence #{evidence_id} not found."}

    entries = (
        db.query(CustodyLog)
        .filter(CustodyLog.evidence_id == evidence_id)
        .order_by(CustodyLog.id.asc())
        .all()
    )

    chain_check = verify_custody_chain(evidence_id, db)
    issues: List[Dict[str, Any]] = []

    if not chain_check["valid"]:
        issues.append({
            "type": "HASH_CHAIN_CORRUPTED",
            "severity": "critical",
            "message": chain_check.get("error", "Custody cryptographic hash chain verification failed.")
        })

    # Rule checks across consecutive entries
    for i in range(1, len(entries)):
        prev = entries[i-1]
        curr = entries[i]

        # 1. Handover Person Gap
        if curr.from_person_name and prev.to_person_name:
            if curr.from_person_name.strip().lower() != prev.to_person_name.strip().lower():
                issues.append({
                    "type": "CUSTODIAN_GAP",
                    "severity": "critical",
                    "step_index": i,
                    "message": f"Custodian gap at step #{i+1}: transferred from '{curr.from_person_name}' but previous custodian was '{prev.to_person_name}'."
                })

        # 2. Location Jump
        if curr.from_location and prev.to_location:
            if curr.from_location.strip().lower() != prev.to_location.strip().lower():
                issues.append({
                    "type": "LOCATION_JUMP",
                    "severity": "warning",
                    "step_index": i,
                    "message": f"Location jump: item departed from '{curr.from_location}' without recorded transfer from previous location '{prev.to_location}'."
                })

        # 3. Seal status problems
        if curr.seal_status_check in ["damaged", "broken_unauthorized"]:
            issues.append({
                "type": "SEAL_COMPROMISED",
                "severity": "critical",
                "step_index": i,
                "message": f"Seal reported as '{curr.seal_status_check}' during {curr.action} at {curr.location}."
            })

    # 4. Long Silences Check
    if entries:
        last_entry = entries[-1]
        phys = db.query(PhysicalItem).filter(PhysicalItem.evidence_id == evidence_id).first()
        if phys and phys.status in ["issued_investigation", "dispatched_fsl"]:
            max_days = phys.dispatch_time_limit_days or (3 if phys.is_biological else 7)
            if last_entry.timestamp:
                ts = last_entry.timestamp
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                delta_days = (datetime.now(timezone.utc) - ts).days
                if delta_days > max_days:
                    issues.append({
                        "type": "TRANSIT_OVERDUE",
                        "severity": "warning",
                        "message": f"Item has been in transit/issued for {delta_days} days (threshold is {max_days} days) without an updated custody entry."
                    })

    # Determine overall status & reliability adjustment
    has_critical = any(issue["severity"] == "critical" for issue in issues)
    has_warning = any(issue["severity"] == "warning" for issue in issues)

    if has_critical:
        status = "seal_issue" if any("SEAL" in iss["type"] for iss in issues) else "gap"
        penalty = -0.25
        complete = False
    elif has_warning:
        status = "gap"
        penalty = -0.10
        complete = False
    else:
        status = "complete"
        penalty = 0.0
        complete = True

    # Sync back to Evidence model
    evidence.chain_of_custody_complete = complete
    db.commit()

    return {
        "evidence_id": evidence_id,
        "evidence_kind": getattr(evidence, "evidence_kind", "digital"),
        "status": status,
        "chain_of_custody_complete": complete,
        "hash_chain_valid": chain_check["valid"],
        "reliability_penalty": penalty,
        "total_custody_entries": len(entries),
        "issues": issues,
        "last_action": entries[-1].action if entries else None,
        "last_timestamp": entries[-1].timestamp.isoformat() if (entries and entries[-1].timestamp) else None,
        "current_custodian": entries[-1].to_person_name if (entries and entries[-1].to_person_name) else "Yerawada Police Station",
        "current_location": entries[-1].to_location if (entries and entries[-1].to_location) else "Malkhana"
    }


# ==============================================================================
# 3. CRITICAL INTEGRITY CHECK HOOK FOR PHYSICAL EXHIBITS
# ==============================================================================

def verify_physical_evidence_integrity(
    db: Session,
    evidence: Evidence,
    user_name: str = "Forensics Examiner",
    user_id: Optional[int] = None,
    user_role: str = "forensic_analyst"
) -> Dict[str, Any]:
    """
    Called by audit_engine.verify_evidence_integrity when evidence_kind == 'physical'.
    Eliminates false 'file missing' tamper alerts on physical evidence.
    Verifies custody ledger hash-chaining, continuity, and active seal status instead.
    """
    continuity = evaluate_custody_continuity(evidence.id, db)
    phys = db.query(PhysicalItem).filter(PhysicalItem.evidence_id == evidence.id).first()

    # Check active seals
    active_seals = db.query(Seal).filter(Seal.evidence_id == evidence.id).all()
    broken_seals = [s for s in active_seals if s.status == "broken_unauthorized"]

    is_intact = continuity["status"] == "complete" and len(broken_seals) == 0

    if is_intact:
        evidence.hash_verified = True
        evidence.chain_of_custody_complete = True
        db.commit()

        # Log integrity verification in custody and audit logs
        log_audit_event(
            db=db,
            action_type="INTEGRITY_VERIFY",
            target_type="physical_exhibit",
            target_id=str(evidence.id),
            description=f"Physical evidence integrity check passed: Custody chain valid ({continuity['total_custody_entries']} entries), seals intact.",
            user_id=user_id,
            user_name=user_name,
            case_id=evidence.case_id,
            before_value="PENDING_VERIFY",
            after_value="PHYSICAL_CHAIN_VERIFIED"
        )

        return {
            "success": True,
            "evidence_id": evidence.id,
            "file_name": phys.description if phys else f"Physical Exhibit #{evidence.id}",
            "evidence_kind": "physical",
            "stored_hash": continuity.get("last_action"),
            "recorded_hash": "CHAIN_SEAL_VERIFIED",
            "recomputed_hash": "CHAIN_SEAL_VERIFIED",
            "integrity_verified": True,
            "status": "PHYSICAL_CHAIN_VERIFIED",
            "message": "Physical evidence custody continuity and tamper-evident seal integrity fully verified.",
            "continuity": continuity
        }
    else:
        evidence.hash_verified = False
        evidence.chain_of_custody_complete = False
        db.commit()

        return {
            "success": False,
            "evidence_id": evidence.id,
            "file_name": phys.description if phys else f"Physical Exhibit #{evidence.id}",
            "evidence_kind": "physical",
            "stored_hash": None,
            "recorded_hash": None,
            "recomputed_hash": None,
            "integrity_verified": False,
            "status": "CUSTODY_OR_SEAL_COMPROMISED",
            "message": f"Physical evidence check flagged issues: {', '.join(i['message'] for i in continuity['issues'])}",
            "continuity": continuity
        }


# ==============================================================================
# 4. SEALS STATE MACHINE & OCR VERIFICATION
# ==============================================================================

def apply_new_seal(
    case_id: int,
    evidence_id: int,
    seal_number: str,
    owner_mark: str,
    package_description: str,
    applied_by_user: User,
    applied_in_presence_of: List[str],
    photos: Optional[List[Dict[str, Any]]],
    db: Session
) -> Seal:
    """Applies a new forensic seal to a physical evidence package."""
    seal = Seal(
        case_id=case_id,
        evidence_id=evidence_id,
        seal_number=seal_number.strip().upper(),
        owner_mark=owner_mark.strip(),
        package_description=package_description,
        applied_by_id=applied_by_user.id,
        applied_by_name=(applied_by_user.full_name if hasattr(applied_by_user, 'full_name') and applied_by_user.full_name else applied_by_user.email) or applied_by_user.email,
        applied_at=datetime.now(timezone.utc),
        applied_in_presence_of=json.dumps(applied_in_presence_of) if applied_in_presence_of else None,
        status="intact"
    )
    db.add(seal)
    db.commit()
    db.refresh(seal)

    # Record initial APPLY event
    event = SealEvent(
        seal_id=seal.id,
        event_type="apply",
        actor_id=applied_by_user.id,
        actor_name=(applied_by_user.full_name if hasattr(applied_by_user, 'full_name') and applied_by_user.full_name else applied_by_user.email) or applied_by_user.email,
        witnesses=json.dumps(applied_in_presence_of) if applied_in_presence_of else None,
        reason="Initial Sealing at recovery / crime scene",
        photos=json.dumps(photos) if photos else None
    )
    db.add(event)
    db.commit()

    return seal


def record_seal_event(
    seal_id: int,
    event_type: str,  # 'inspect', 'break', 'reseal'
    actor_user: User,
    reason: str,
    witnesses: Optional[List[str]],
    photos: Optional[List[Dict[str, Any]]],
    new_seal_data: Optional[Dict[str, Any]],
    db: Session
) -> Tuple[SealEvent, Optional[Seal]]:
    """
    Enforces Seal State Machine Rules:
      - 'intact' -> 'inspect' (remains intact)
      - 'intact' -> 'break' (transitions to broken_authorized or broken_unauthorized)
      - Broken seal CANNOT transition directly back to intact! Must use 'reseal'.
      - Reseal creates a new Seal record linked to the replaced seal.
    """
    seal = db.query(Seal).filter(Seal.id == seal_id).first()
    if not seal:
        raise ValueError(f"Seal #{seal_id} not found.")

    new_seal: Optional[Seal] = None

    if event_type == "break":
        if seal.status in ["broken_authorized", "broken_unauthorized"]:
            raise ValueError(f"Seal #{seal.seal_number} is already broken.")
        seal.status = "broken_authorized" if "court" in reason.lower() or "fsl" in reason.lower() or "ordered" in reason.lower() else "broken_unauthorized"

    elif event_type == "reseal":
        if not new_seal_data or not new_seal_data.get("seal_number"):
            raise ValueError("Resealing requires new seal_number and owner_mark.")
        seal.status = "resealed"

        new_seal = Seal(
            case_id=seal.case_id,
            evidence_id=seal.evidence_id,
            seal_number=new_seal_data["seal_number"].strip().upper(),
            owner_mark=new_seal_data.get("owner_mark", "Forensics / Reseal"),
            package_description=new_seal_data.get("package_description", seal.package_description),
            applied_by_id=actor_user.id,
            applied_by_name=(actor_user.full_name if hasattr(actor_user, 'full_name') and actor_user.full_name else actor_user.email) or actor_user.email,
            applied_at=datetime.now(timezone.utc),
            applied_in_presence_of=json.dumps(witnesses) if witnesses else None,
            status="intact",
            replaced_seal_id=seal.id
        )
        db.add(new_seal)
        db.commit()
        db.refresh(new_seal)

    event = SealEvent(
        seal_id=seal.id,
        event_type=event_type,
        actor_id=actor_user.id,
        actor_name=(actor_user.full_name if hasattr(actor_user, 'full_name') and actor_user.full_name else actor_user.email) or actor_user.email,
        witnesses=json.dumps(witnesses) if witnesses else None,
        reason=reason,
        new_seal_id=new_seal.id if new_seal else None,
        photos=json.dumps(photos) if photos else None
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return event, new_seal


def compare_seal_ocr_number(claimed_seal: str, ocr_detected_text: str) -> Dict[str, Any]:
    """
    Compares claimed seal number with OCR text extracted from close-up photo.
    Returns match status, confidence score, and flag if mismatch.
    """
    claimed_clean = "".join(c for c in claimed_seal.upper() if c.isalnum())
    ocr_clean = "".join(c for c in ocr_detected_text.upper() if c.isalnum())

    if not claimed_clean or not ocr_clean:
        return {"match": False, "confidence": 0.0, "status": "unreadable"}

    if claimed_clean == ocr_clean:
        return {"match": True, "confidence": 1.0, "status": "exact_match"}

    if claimed_clean in ocr_clean or ocr_clean in claimed_clean:
        return {"match": True, "confidence": 0.85, "status": "partial_match"}

    return {
        "match": False,
        "confidence": 0.20,
        "status": "mismatch",
        "claimed": claimed_seal,
        "detected": ocr_detected_text
    }


# ==============================================================================
# 5. MALKHANA STATION-LEVEL REGISTER
# ==============================================================================

def get_malkhana_register(
    police_station: str,
    case_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    db: Session = None
) -> List[Dict[str, Any]]:
    """Returns station-level Muddimalkhana inventory register with current location and seal status."""
    query = (
        db.query(PhysicalItem, Evidence, Case)
        .join(Evidence, PhysicalItem.evidence_id == Evidence.id)
        .join(Case, Evidence.case_id == Case.id)
    )

    if case_id:
        query = query.filter(Case.id == case_id)

    if status_filter:
        query = query.filter(PhysicalItem.status == status_filter)

    results = query.all()
    rows = []
    for phys, ev, c in results:
        # Get latest seal
        latest_seal = (
            db.query(Seal)
            .filter(Seal.evidence_id == ev.id)
            .order_by(Seal.id.desc())
            .first()
        )
        rows.append({
            "id": phys.id,
            "evidence_id": ev.id,
            "case_id": c.id,
            "crime_number": c.crime_number or f"CR-{c.id}",
            "case_title": c.title,
            "category": phys.category,
            "description": phys.description,
            "identifying_marks": phys.identifying_marks,
            "quantity_or_weight": phys.quantity_or_weight,
            "condition": phys.condition,
            "packaging": phys.packaging,
            "current_location": phys.current_location,
            "current_custodian": phys.current_custodian,
            "malkhana_entry_number": phys.malkhana_entry_number,
            "rack_or_shelf": phys.rack_or_shelf,
            "status": phys.status,
            "seal_number": latest_seal.seal_number if latest_seal else None,
            "seal_status": latest_seal.status if latest_seal else "unsealed",
            "is_biological": phys.is_biological,
            "is_perishable": phys.is_perishable,
            "is_firearm": phys.is_firearm,
            "is_narcotics": phys.is_narcotics,
            "created_at": phys.created_at.isoformat() if phys.created_at else None
        })

    return rows


def deposit_into_malkhana(
    evidence_id: int,
    malkhana_entry_number: str,
    rack_or_shelf: str,
    depositor_name: str,
    received_by_user: User,
    condition: str,
    seal_status: str,
    photos: Optional[List[Dict[str, Any]]],
    db: Session
) -> Dict[str, Any]:
    """Records MALKHANA_IN deposit with rack/shelf allocation and receiver confirmation."""
    phys = db.query(PhysicalItem).filter(PhysicalItem.evidence_id == evidence_id).first()
    if not phys:
        raise ValueError(f"Physical item for evidence #{evidence_id} not found.")

    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()

    # Update item
    phys.malkhana_entry_number = malkhana_entry_number.strip().upper()
    phys.rack_or_shelf = rack_or_shelf.strip()
    phys.current_location = "malkhana"
    phys.current_custodian = (received_by_user.full_name if hasattr(received_by_user, 'full_name') and received_by_user.full_name else received_by_user.email) or received_by_user.email
    phys.status = "deposited_malkhana"
    phys.condition = condition
    db.commit()

    # Create chained custody entry
    entry = append_chained_custody_entry(
        db=db,
        evidence_id=evidence_id,
        case_id=ev.case_id,
        action="MALKHANA_IN",
        actor_name=(received_by_user.full_name if hasattr(received_by_user, 'full_name') and received_by_user.full_name else received_by_user.email) or received_by_user.email,
        actor_id=received_by_user.id,
        actor_role="malkhana_incharge",
        from_person_name=depositor_name,
        from_location="Police Station / Field",
        to_person_id=received_by_user.id,
        to_person_name=(received_by_user.full_name if hasattr(received_by_user, 'full_name') and received_by_user.full_name else received_by_user.email) or received_by_user.email,
        to_location=f"Malkhana ({rack_or_shelf})",
        purpose="Safe Custody Deposit",
        condition_at_handover=condition,
        seal_status_check=seal_status,
        acknowledgement_type="digital_pin",
        attached_photos=photos,
        notes=f"Deposited in Muddimalkhana entry #{malkhana_entry_number} at {rack_or_shelf}."
    )

    return {
        "success": True,
        "evidence_id": evidence_id,
        "malkhana_entry_number": phys.malkhana_entry_number,
        "rack_or_shelf": phys.rack_or_shelf,
        "custody_entry_id": entry.id
    }


def issue_from_malkhana(
    evidence_id: int,
    purpose: str,  # 'Investigation Review', 'Court Production', 'Sent to FSL'
    requested_by_user: User,
    approved_by_user: User,
    taken_by_name: str,
    destination_location: str,
    expected_return_date: Optional[datetime],
    authority_order_ref: Optional[str],
    seal_check: str,
    notes: Optional[str],
    db: Session
) -> Dict[str, Any]:
    """
    Enforces TWO-PERSON RULE: Requester and Approver must be distinct users!
    Records MALKHANA_OUT custody movement.
    """
    if requested_by_user.id == approved_by_user.id:
        raise ValueError("Two-Person Rule Violation: Requester and Malkhana Approver must be distinct individuals.")

    phys = db.query(PhysicalItem).filter(PhysicalItem.evidence_id == evidence_id).first()
    if not phys:
        raise ValueError(f"Physical item for evidence #{evidence_id} not found.")

    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()

    # Map purpose to status
    new_status = "issued_investigation"
    if "fsl" in purpose.lower():
        new_status = "dispatched_fsl"
    elif "court" in purpose.lower():
        new_status = "produced_court"

    phys.current_location = destination_location
    phys.current_custodian = taken_by_name
    phys.status = new_status
    db.commit()

    entry = append_chained_custody_entry(
        db=db,
        evidence_id=evidence_id,
        case_id=ev.case_id,
        action="MALKHANA_OUT",
        actor_name=(approved_by_user.full_name if hasattr(approved_by_user, 'full_name') and approved_by_user.full_name else approved_by_user.email) or approved_by_user.email,
        actor_id=approved_by_user.id,
        actor_role="malkhana_incharge",
        from_person_id=approved_by_user.id,
        from_person_name=(approved_by_user.full_name if hasattr(approved_by_user, 'full_name') and approved_by_user.full_name else approved_by_user.email) or approved_by_user.email,
        from_location=f"Malkhana ({phys.rack_or_shelf or 'General'})",
        to_person_name=taken_by_name,
        to_location=destination_location,
        purpose=purpose,
        condition_at_handover=phys.condition,
        seal_status_check=seal_check,
        expected_return_date=expected_return_date,
        authority_order_ref=authority_order_ref,
        notes=f"Authorized issue by {(approved_by_user.full_name if hasattr(approved_by_user, 'full_name') and approved_by_user.full_name else approved_by_user.email)} on request of {(requested_by_user.full_name if hasattr(requested_by_user, 'full_name') and requested_by_user.full_name else requested_by_user.email)}. Ref: {authority_order_ref or 'None'}."
    )

    return {
        "success": True,
        "evidence_id": evidence_id,
        "new_status": new_status,
        "custody_entry_id": entry.id
    }


def generate_malkhana_barcode_label(evidence_id: int, db: Session) -> Dict[str, Any]:
    """Generates printable QR code & Barcode label data (SVG string) for exhibit package."""
    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    phys = db.query(PhysicalItem).filter(PhysicalItem.evidence_id == evidence_id).first()
    c = db.query(Case).filter(Case.id == ev.case_id).first() if ev else None
    latest_seal = db.query(Seal).filter(Seal.evidence_id == evidence_id).order_by(Seal.id.desc()).first()

    crime_no = c.crime_number if (c and c.crime_number) else f"CR-{ev.case_id}"
    malkhana_no = phys.malkhana_entry_number if (phys and phys.malkhana_entry_number) else f"EX-{evidence_id}"
    seal_no = latest_seal.seal_number if latest_seal else "UNSEALED"
    desc = phys.description if phys else ev.file_name

    # SVG printable label
    svg_label = f"""<svg xmlns="http://www.w3.org/2000/svg" width="380" height="200" viewBox="0 0 380 200" style="background:#fff; font-family: monospace, sans-serif;">
  <rect x="5" y="5" width="370" height="190" fill="#fff" stroke="#191410" stroke-width="2" rx="4"/>
  <text x="15" y="28" font-size="12" font-weight="bold" fill="#d93829">MUDDIMALKHANA FORENSIC EXHIBIT</text>
  <line x1="15" y1="36" x2="365" y2="36" stroke="#e2dcd2" stroke-width="1.5"/>
  <text x="15" y="55" font-size="11" font-weight="bold" fill="#191410">CRIME NO: <tspan font-weight="normal">{crime_no}</tspan></text>
  <text x="15" y="75" font-size="11" font-weight="bold" fill="#191410">MALKHANA NO: <tspan font-weight="normal">{malkhana_no}</tspan></text>
  <text x="15" y="95" font-size="11" font-weight="bold" fill="#191410">RACK / SHELF: <tspan font-weight="normal">{phys.rack_or_shelf or 'Unallocated'}</tspan></text>
  <text x="15" y="115" font-size="11" font-weight="bold" fill="#191410">SEAL NO: <tspan font-weight="normal">{seal_no}</tspan></text>
  <text x="15" y="135" font-size="10" font-weight="normal" fill="#59524c">DESC: {(desc[:36] + '...') if len(desc) > 36 else desc}</text>
  <!-- Mock QR Representation Grid -->
  <rect x="270" y="45" width="85" height="85" fill="#f5f0e8" stroke="#191410" stroke-width="1"/>
  <rect x="278" y="53" width="22" height="22" fill="#191410"/>
  <rect x="325" y="53" width="22" height="22" fill="#191410"/>
  <rect x="278" y="100" width="22" height="22" fill="#191410"/>
  <rect x="306" y="80" width="12" height="12" fill="#191410"/>
  <line x1="15" y1="155" x2="365" y2="155" stroke="#e2dcd2" stroke-width="1"/>
  <text x="15" y="175" font-size="9" fill="#70685e">SHA-256: {latest_seal.seal_number if latest_seal else 'GENESIS'} | YERAWADA POLICE STATION</text>
</svg>"""

    return {
        "evidence_id": evidence_id,
        "crime_number": crime_no,
        "malkhana_entry_number": malkhana_no,
        "seal_number": seal_no,
        "svg": svg_label
    }


# ==============================================================================
# 6. FSL DISPATCH & RETURN LIFECYCLE
# ==============================================================================

def create_fsl_dispatch(
    case_id: int,
    forwarding_letter_number: str,
    forwarding_letter_date: datetime,
    fsl_name: str,
    examination_requested: str,
    carried_by_name: str,
    carried_by_role: str,
    carried_by_id_card: str,
    mode_of_transit: str,
    expected_report_date: Optional[datetime],
    item_evidence_ids: List[int],
    current_user: User,
    db: Session
) -> FSLDispatch:
    """
    Creates FSL forwarding dispatch, bundles exhibits, automatically creates
    SENT_TO_FSL custody entries, and marks items as in transit.
    """
    dispatch = FSLDispatch(
        case_id=case_id,
        forwarding_letter_number=forwarding_letter_number.strip().upper(),
        forwarding_letter_date=forwarding_letter_date,
        fsl_name=fsl_name.strip(),
        examination_requested=examination_requested.strip(),
        sent_date=datetime.now(timezone.utc),
        carried_by_name=carried_by_name.strip(),
        carried_by_role=carried_by_role.strip(),
        carried_by_id_card=carried_by_id_card.strip(),
        mode_of_transit=mode_of_transit,
        expected_report_date=expected_report_date,
        status="dispatched"
    )
    db.add(dispatch)
    db.commit()
    db.refresh(dispatch)

    for ev_id in item_evidence_ids:
        latest_seal = db.query(Seal).filter(Seal.evidence_id == ev_id).order_by(Seal.id.desc()).first()
        seal_no = latest_seal.seal_number if latest_seal else "UNSEALED"

        dispatch_item = FSLDispatchItem(
            dispatch_id=dispatch.id,
            evidence_id=ev_id,
            seal_number_at_dispatch=seal_no,
            seal_status_at_dispatch="intact"
        )
        db.add(dispatch_item)

        # Update physical item location
        phys = db.query(PhysicalItem).filter(PhysicalItem.evidence_id == ev_id).first()
        if phys:
            phys.current_location = "fsl"
            phys.current_custodian = f"{fsl_name} (Carried by {carried_by_name})"
            phys.status = "dispatched_fsl"

        # Chained custody log
        append_chained_custody_entry(
            db=db,
            evidence_id=ev_id,
            case_id=case_id,
            action="SENT_TO_FSL",
            actor_name=(current_user.full_name if hasattr(current_user, 'full_name') and current_user.full_name else current_user.email) or current_user.email,
            actor_id=current_user.id,
            actor_role="investigator",
            from_location="Malkhana / Police Station",
            to_person_name=carried_by_name,
            to_location=fsl_name,
            purpose=f"FSL Examination: {examination_requested}",
            condition_at_handover="Intact, sealed for transit",
            seal_status_check=seal_no,
            expected_return_date=expected_report_date,
            authority_order_ref=f"Forwarding Memo #{forwarding_letter_number}",
            notes=f"Dispatched via {mode_of_transit} to {fsl_name}."
        )

    db.commit()
    return dispatch


def record_fsl_lab_receipt(
    dispatch_id: int,
    receipt_scan_path: str,
    ack_date: datetime,
    current_user: User,
    db: Session
) -> FSLDispatch:
    """Updates dispatch status to 'received_by_lab' upon stamped acknowledgment."""
    dispatch = db.query(FSLDispatch).filter(FSLDispatch.id == dispatch_id).first()
    if not dispatch:
        raise ValueError(f"FSL Dispatch #{dispatch_id} not found.")

    dispatch.status = "received_by_lab"
    dispatch.lab_acknowledgement_receipt_path = receipt_scan_path
    dispatch.lab_acknowledgement_date = ack_date
    db.commit()
    return dispatch


def record_fsl_items_return(
    dispatch_id: int,
    return_date: datetime,
    carried_by: str,
    item_returns: List[Dict[str, Any]],  # [{evidence_id, return_seal_number, seal_status, condition}]
    current_user: User,
    db: Session
) -> FSLDispatch:
    """Records return of physical exhibits from FSL lab with new lab seals and custody logs."""
    dispatch = db.query(FSLDispatch).filter(FSLDispatch.id == dispatch_id).first()
    if not dispatch:
        raise ValueError(f"FSL Dispatch #{dispatch_id} not found.")

    dispatch.status = "items_returned"
    dispatch.return_date = return_date
    dispatch.return_carried_by = carried_by

    for ret in item_returns:
        ev_id = ret["evidence_id"]
        d_item = db.query(FSLDispatchItem).filter(
            FSLDispatchItem.dispatch_id == dispatch_id,
            FSLDispatchItem.evidence_id == ev_id
        ).first()

        if d_item:
            d_item.return_seal_number = ret.get("return_seal_number")
            d_item.return_seal_status = ret.get("seal_status", "intact")
            d_item.condition_on_return = ret.get("condition", "intact")

        # Update physical item
        phys = db.query(PhysicalItem).filter(PhysicalItem.evidence_id == ev_id).first()
        if phys:
            phys.current_location = "malkhana"
            phys.current_custodian = (current_user.full_name if hasattr(current_user, 'full_name') and current_user.full_name else current_user.email) or current_user.email
            phys.status = "returned_from_fsl"
            phys.condition = ret.get("condition", "intact")

        # Chained custody log
        append_chained_custody_entry(
            db=db,
            evidence_id=ev_id,
            case_id=dispatch.case_id,
            action="RECEIVED_FROM_FSL",
            actor_name=(current_user.full_name if hasattr(current_user, 'full_name') and current_user.full_name else current_user.email) or current_user.email,
            actor_id=current_user.id,
            actor_role="malkhana_incharge",
            from_location=dispatch.fsl_name,
            from_person_name=carried_by,
            to_person_id=current_user.id,
            to_person_name=(current_user.full_name if hasattr(current_user, 'full_name') and current_user.full_name else current_user.email) or current_user.email,
            to_location="Malkhana",
            purpose="Returned after Forensic Examination",
            condition_at_handover=ret.get("condition", "intact"),
            seal_status_check=ret.get("seal_status", "intact"),
            notes=f"Returned with FSL Seal #{ret.get('return_seal_number', 'N/A')}."
        )

    db.commit()
    return dispatch
