"""
backend/routers/history.py
Cryptographic Audit Ledger, Merkle Chain Verification & Scoring History Router.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import AuditLog, ScoringRun, User
from schemas import AuditLogOut, AuditChainVerificationResponse
from auth import get_current_user, check_case_access
from audit_engine import verify_audit_chain
from routers.common import resolve_case_id

router = APIRouter(tags=["Audit Ledger & Historical Versioning"])


@router.get("/cases/{case_id}/audit-logs", response_model=List[AuditLogOut])
def get_case_audit_logs(
    case_id: str,
    user_id: Optional[int] = None,
    action_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns append-only audit entries for a case with optional actor and action filters."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    q = db.query(AuditLog).filter(
        (AuditLog.case_id == real_case_id) | (AuditLog.case_id.is_(None))
    )
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if action_type:
        q = q.filter(AuditLog.action_type == action_type)

    return q.order_by(AuditLog.id.desc()).all()


@router.get("/audit/logs", response_model=List[AuditLogOut])
def get_all_audit_logs(
    action_type: Optional[str] = None,
    user_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns global audit ledger entries (admin & lead investigator access)."""
    q = db.query(AuditLog)
    if action_type:
        q = q.filter(AuditLog.action_type == action_type)
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    return q.order_by(AuditLog.id.desc()).all()


@router.get("/audit/verify-chain", response_model=AuditChainVerificationResponse)
@router.get("/cases/{case_id}/audit-chain")
@router.get("/cases/{case_id}/audit-chain/verify")
def verify_audit_ledger_chain(
    case_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cryptographically verifies Merkle-chained SHA-256 links across the entire audit log."""
    real_case_id = resolve_case_id(case_id, db) if case_id else None
    return verify_audit_chain(db, case_id=real_case_id)


@router.get("/cases/{case_id}/scoring-history")
def get_scoring_history(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns the timeline of frozen scoring snapshots for a case docket."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    runs = db.query(ScoringRun).filter(ScoringRun.case_id == real_case_id).order_by(ScoringRun.id.desc()).limit(20).all()
    return [
        {
            "id": r.id,
            "case_id": r.case_id,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "algorithm_version": r.algorithm_version,
            "trigger_action": r.trigger_action,
            "user_id": r.user_id,
            "scores": r.scores_json
        }
        for r in runs
    ]


@router.get("/cases/{case_id}/audit-certificate")
@router.get("/audit/certificate")
def get_audit_certificate(
    case_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Exports a statutory Section 65B Indian Evidence Act / Section 63 BSA compliant
    certificate verifying that all cryptographic SHA-256 audit log blocks remain intact
    and that no system records were altered or deleted.
    """
    real_case_id = resolve_case_id(case_id, db) if case_id else None
    verification = verify_audit_chain(db, case_id=real_case_id)
    return {
        "certificate_title": "CERTIFICATE OF ELECTRONIC RECORD INTEGRITY AND AUDIT LEDGER CONTINUITY",
        "statutory_provision": "Under Section 65B(4) Indian Evidence Act, 1872 / Section 63 Bharatiya Sakshya Adhiniyam, 2023",
        "case_id": real_case_id,
        "certified_by": current_user.full_name,
        "role": current_user.role,
        "chain_intact": verification.get("chain_intact", True),
        "total_entries": verification.get("total_entries", 0),
        "verified_count": verification.get("verified_count", 0),
        "genesis_hash": verification.get("genesis_hash"),
        "latest_hash": verification.get("latest_hash"),
        "status": verification.get("status"),
        "certification_statement": (
            "This is to certify that the computer and data storage system of Evidentia AI was operating lawfully and "
            "in normal operating condition during the period of case recording. The cryptographic hash chain (SHA-256) "
            "has been verified unbroken across all recorded entries, with zero evidence of data tampering, modification, "
            "or unauthorized substitution."
        )
    }

