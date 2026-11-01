# backend/audit_engine.py
"""
Central Audit Ledger and Chain of Custody Engine for Evidentia AI.
Implements:
1. Cryptographic Merkle-hash chaining across audit log entries (append-only ledger).
2. SHA-256 raw byte fingerprinting for forensic evidence intake and verification.
3. Tamper detection and continuous integrity validation.
4. Chain of custody lifecycle tracking for exhibits (Seizure -> Intake -> Certification -> Analysis -> Verification).
5. Soft-deletion preserving permanent evidence history.
"""

import hashlib
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models import AuditLog, CustodyLog, Evidence, User

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"
_audit_lock = threading.Lock()


def compute_sha256_bytes(data: bytes) -> str:
    """Computes fixed-length 256-bit cryptographic digest over raw binary payload."""
    return hashlib.sha256(data).hexdigest()


def normalize_timestamp_str(ts) -> str:
    """Canonical timestamp formatting across SQLite and Python datetimes."""
    if not ts:
        return ""
    if isinstance(ts, str):
        clean = ts.replace("Z", "").replace("+00:00", "").replace(" ", "T")
        if "." in clean:
            clean = clean.split(".")[0]
        return clean
    elif hasattr(ts, "strftime"):
        return ts.strftime("%Y-%m-%dT%H:%M:%S")
    return str(ts)


def calculate_audit_payload_hash(
    previous_hash: str,
    timestamp_iso: Any,
    user_name: str,
    action_type: str,
    target_type: str,
    target_id: str,
    description: str,
    before_value: str = "",
    after_value: str = ""
) -> str:
    """
    Computes deterministic SHA-256 hash for an audit ledger block:
    current_hash = SHA256(previous_hash | canonical_timestamp | user_name | action_type | target_type | target_id | description | before_value | after_value)
    """
    norm_ts = normalize_timestamp_str(timestamp_iso)
    canonical_repr = (
        f"{previous_hash}|"
        f"{norm_ts}|"
        f"{user_name or 'System'}|"
        f"{action_type}|"
        f"{target_type}|"
        f"{target_id or ''}|"
        f"{description or ''}|"
        f"{before_value or ''}|"
        f"{after_value or ''}"
    )
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()


def log_audit_event(
    db: Session,
    action_type: str,
    target_type: str,
    target_id: Optional[str],
    description: str,
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
    user_role: Optional[str] = None,
    case_id: Optional[int] = None,
    before_value: Optional[str] = None,
    after_value: Optional[str] = None,
    ip_address: Optional[str] = None,
    commit: bool = True
) -> AuditLog:
    """
    Central helper for writing an append-only, Merkle-chained audit entry.
    """
    with _audit_lock:
        last_log = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        prev_hash = last_log.current_hash if last_log else GENESIS_HASH

        now = datetime.now(timezone.utc)

        effective_user_name = user_name or "System"
        curr_hash = calculate_audit_payload_hash(
            previous_hash=prev_hash,
            timestamp_iso=now,
            user_name=effective_user_name,
            action_type=action_type,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else "",
            description=description,
            before_value=str(before_value) if before_value is not None else "",
            after_value=str(after_value) if after_value is not None else ""
        )

        audit_entry = AuditLog(
            case_id=case_id,
            user_id=user_id,
            user_name=effective_user_name,
            user_role=user_role or "analyst",
            action_type=action_type,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            description=description,
            before_value=str(before_value) if before_value is not None else None,
            after_value=str(after_value) if after_value is not None else None,
            ip_address=ip_address,
            timestamp=now,
            previous_hash=prev_hash,
            current_hash=curr_hash
        )
        db.add(audit_entry)
        if commit:
            db.commit()
            db.refresh(audit_entry)
        else:
            db.flush()
        return audit_entry


def verify_audit_chain(db: Session, case_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Verifies the integrity of the cryptographic Merkle chain.
    """
    logs = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
    if not logs:
        return {
            "chain_intact": True,
            "total_entries": 0,
            "verified_count": 0,
            "genesis_hash": GENESIS_HASH,
            "latest_hash": GENESIS_HASH,
            "status": "VALID",
            "message": "Audit ledger is initialized and empty. Genesis state valid."
        }

    expected_prev = GENESIS_HASH
    for i, log in enumerate(logs):
        if log.previous_hash != expected_prev:
            return {
                "chain_intact": False,
                "total_entries": len(logs),
                "verified_count": i,
                "genesis_hash": GENESIS_HASH,
                "latest_hash": expected_prev,
                "tampered_at_index": i,
                "tampered_entry_id": log.id,
                "tampered_action": log.action_type,
                "status": "TAMPER_DETECTED",
                "message": f"Cryptographic Merkle link broken at block #{log.id}.",
                "error": f"Chain link broken at entry #{log.id} ({log.action_type}): previous_hash does not match."
            }

        recomputed = calculate_audit_payload_hash(
            previous_hash=log.previous_hash,
            timestamp_iso=log.timestamp,
            user_name=log.user_name,
            action_type=log.action_type,
            target_type=log.target_type,
            target_id=log.target_id or "",
            description=log.description,
            before_value=log.before_value or "",
            after_value=log.after_value or ""
        )

        if log.current_hash != recomputed:
            return {
                "chain_intact": False,
                "total_entries": len(logs),
                "verified_count": i,
                "genesis_hash": GENESIS_HASH,
                "latest_hash": expected_prev,
                "tampered_at_index": i,
                "tampered_entry_id": log.id,
                "tampered_action": log.action_type,
                "status": "TAMPER_DETECTED",
                "message": f"Data alteration detected at block #{log.id}.",
                "error": f"Row modification detected at entry #{log.id}: data content was altered after creation."
            }

        expected_prev = log.current_hash


    return {
        "chain_intact": True,
        "total_entries": len(logs),
        "verified_count": len(logs),
        "genesis_hash": GENESIS_HASH,
        "latest_hash": logs[-1].current_hash,
        "last_timestamp": logs[-1].timestamp.isoformat() if logs[-1].timestamp else None,
        "status": "VALID",
        "message": f"Cryptographic Merkle audit chain intact. All {len(logs)} entries verified without tamper."
    }


def log_custody_event(
    db: Session,
    evidence_id: int,
    case_id: int,
    action: str,
    actor_name: str,
    actor_role: Optional[str] = "Lead SIT Investigator",
    source_agency: Optional[str] = None,
    location: Optional[str] = None,
    notes: Optional[str] = None,
    file_hash_snapshot: Optional[str] = None
) -> CustodyLog:
    """Records an immutable milestone in the exhibit chain of custody."""
    entry = CustodyLog(
        evidence_id=evidence_id,
        case_id=case_id,
        action=action,
        actor_name=actor_name,
        actor_role=actor_role,
        source_agency=source_agency,
        location=location,
        timestamp=datetime.now(timezone.utc),
        file_hash_snapshot=file_hash_snapshot,
        notes=notes
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def verify_evidence_integrity(
    db: Session,
    evidence_id: int,
    user_name: str = "Forensics Examiner",
    user_id: Optional[int] = None,
    user_role: str = "forensic_analyst",
    **kwargs
) -> Dict[str, Any]:
    """
    Recomputes SHA-256 of the stored physical file on disk/storage and compares it to the original recorded file_hash.
    If the file is missing or replaced, it strictly FAILS with 'file missing, cannot verify' (or tamper mismatch),
    never falls back to synthetic or recorded hashes, writes a critical tamper alert, and flags the custody/audit logs.
    """
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        return {
            "success": False,
            "error": f"Evidence #{evidence_id} not found."
        }

    # CRITICAL FIX: Physical forensic exhibits DO NOT have a digital file on disk.
    # Route them to physical custody continuity & seal verification to avoid false tamper alerts.
    if getattr(evidence, "evidence_kind", "digital") == "physical":
        from physical_evidence_engine import verify_physical_evidence_integrity
        return verify_physical_evidence_integrity(
            db=db,
            evidence=evidence,
            user_name=user_name,
            user_id=user_id,
            user_role=user_role
        )

    backend_dir = Path(__file__).resolve().parent
    file_path = None

    if evidence.storage_path:
        p = Path(evidence.storage_path)
        if not p.is_absolute():
            p = backend_dir / p
        if p.exists() and p.is_file():
            file_path = p

    if not file_path:
        # Check fallback uploads directory
        candidate = backend_dir / "uploads" / evidence.file_name
        if candidate.exists() and candidate.is_file():
            file_path = candidate

    # Strict check: If physical file is missing, FAIL immediately with tamper alert.
    # NEVER fall back to recorded hash or synthetic hash.
    if not file_path or not file_path.exists():
        evidence.hash_verified = False
        if hasattr(evidence, "quality_rating") and evidence.quality_rating is not None:
            evidence.quality_rating = min(evidence.quality_rating, 1.0)
        db.commit()

        log_custody_event(
            db=db,
            evidence_id=evidence.id,
            case_id=evidence.case_id,
            action="FILE_MISSING_TAMPER",
            actor_name=user_name,
            actor_role=user_role,
            location="Digital Forensics Laboratory",
            notes="CRITICAL ERROR: file missing, cannot verify. Physical file unreadable on disk.",
            file_hash_snapshot=None
        )

        log_audit_event(
            db=db,
            action_type="TAMPER_OR_MISSING",
            target_type="exhibit",
            target_id=str(evidence.id),
            description=f"Evidence '{evidence.file_name}' check failed: file missing, cannot verify.",
            user_id=user_id,
            user_name=user_name,
            case_id=evidence.case_id,
            before_value=evidence.file_hash,
            after_value=None
        )

        try:
            from alerts_engine import check_integrity_failure_rule
            check_integrity_failure_rule(
                case_id=evidence.case_id,
                db=db,
                exhibit_id=evidence.id,
                error_detail="file missing, cannot verify"
            )
        except Exception as e:
            print(f"[!] Could not process missing file alert: {e}")

        return {
            "success": False,
            "evidence_id": evidence.id,
            "file_name": evidence.file_name,
            "stored_hash": evidence.file_hash,
            "recorded_hash": evidence.file_hash,
            "recomputed_hash": None,
            "integrity_verified": False,
            "status": "FILE_MISSING_TAMPER",
            "message": "file missing, cannot verify",
            "error": "file missing, cannot verify",
            "is_match": False
        }

    # Recompute SHA-256 directly from raw file bytes
    raw_bytes = file_path.read_bytes()
    recomputed_hash = compute_sha256_bytes(raw_bytes)

    # Compare
    is_match = (recomputed_hash == evidence.file_hash)
    evidence.hash_verified = is_match
    if not is_match and hasattr(evidence, "quality_rating") and evidence.quality_rating is not None:
        evidence.quality_rating = min(evidence.quality_rating, 1.0)
    db.commit()

    # Record custody verification milestone
    custody_action = "INTEGRITY_VERIFY" if is_match else "TAMPER_WARNING"
    notes = (
        f"Automated SHA-256 re-computation verified match against recorded fingerprint ({evidence.file_hash[:16]}...)."
        if is_match else
        f"CRITICAL TAMPER WARNING: Computed hash ({recomputed_hash[:16]}...) does not match custody record ({evidence.file_hash[:16]}...). File modified or replaced."
    )
    log_custody_event(
        db=db,
        evidence_id=evidence.id,
        case_id=evidence.case_id,
        action=custody_action,
        actor_name=user_name,
        actor_role=user_role,
        location="Digital Forensics Laboratory",
        notes=notes,
        file_hash_snapshot=recomputed_hash
    )

    # Log to append-only audit ledger
    log_audit_event(
        db=db,
        action_type="INTEGRITY_VERIFY" if is_match else "TAMPER_DETECTED",
        target_type="exhibit",
        target_id=str(evidence.id),
        description=f"Evidence '{evidence.file_name}' integrity check: {'PASSED' if is_match else 'FAILED (TAMPER DETECTED: file replaced or modified)'}.",
        user_id=user_id,
        user_name=user_name,
        case_id=evidence.case_id,
        before_value=evidence.file_hash,
        after_value=recomputed_hash
    )

    # Trigger or auto-resolve critical integrity alert
    try:
        from alerts_engine import check_integrity_failure_rule, auto_resolve_alert
        if not is_match:
            check_integrity_failure_rule(
                case_id=evidence.case_id,
                db=db,
                exhibit_id=evidence.id,
                error_detail=f"Recomputed SHA-256 ({recomputed_hash[:16]}...) differs from original intake fingerprint ({evidence.file_hash[:16]}...). File modified or replaced."
            )
        else:
            auto_resolve_alert(
                case_id=evidence.case_id,
                dedup_key=f"integrity_failure_{evidence.case_id}_{evidence.id}",
                resolution_reason="Integrity re-verified: SHA-256 matches judicial custody fingerprint.",
                db=db
            )
    except Exception as e:
        print(f"[!] Could not process integrity alert: {e}")

    return {
        "success": is_match,
        "evidence_id": evidence.id,
        "file_name": evidence.file_name,
        "stored_hash": evidence.file_hash,
        "recorded_hash": evidence.file_hash,
        "recomputed_hash": recomputed_hash,
        "integrity_verified": is_match,
        "status": "VALID_INTACT" if is_match else "TAMPER_WARNING",
        "message": "File integrity intact. SHA-256 matches judicial custody record." if is_match else "CRITICAL TAMPER WARNING: Recomputed SHA-256 differs from original intake hash! File replaced or modified.",
        "error": None if is_match else "Integrity mismatch: file replaced or modified",
        "is_match": is_match
    }


def soft_delete_evidence(
    db: Session,
    evidence_id: int,
    user_name: str,
    user_id: Optional[int] = None,
    user_role: Optional[str] = None
) -> Dict[str, Any]:
    """
    Soft-deletes an evidence exhibit (marks is_deleted=True).
    The file record and custody history remain permanently preserved for legal defensibility.
    """
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        return {"success": False, "error": f"Evidence #{evidence_id} not found."}

    now = datetime.now(timezone.utc)
    evidence.is_deleted = True
    evidence.deleted_at = now
    evidence.deleted_by = user_name
    db.commit()

    # Custody log
    log_custody_event(
        db=db,
        evidence_id=evidence.id,
        case_id=evidence.case_id,
        action="SOFT_DELETE",
        actor_name=user_name,
        actor_role=user_role or "lead_investigator",
        notes=f"Exhibit retired from active trial analysis by {user_name}. Historical custody preserved.",
        file_hash_snapshot=evidence.file_hash
    )

    # Audit log
    log_audit_event(
        db=db,
        action_type="EVIDENCE_SOFT_DELETE",
        target_type="exhibit",
        target_id=str(evidence.id),
        description=f"Exhibit '{evidence.file_name}' soft-deleted from active case #{evidence.case_id} by {user_name}. Custody ledger preserved.",
        user_id=user_id,
        user_name=user_name,
        user_role=user_role,
        case_id=evidence.case_id,
        before_value="active",
        after_value="deleted"
    )

    return {"success": True, "message": f"Exhibit '{evidence.file_name}' soft-deleted successfully."}
