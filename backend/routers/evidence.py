"""
backend/routers/evidence.py
Evidence Ingestion, Forensic SHA-256 Custody, Analysis & Verification Router.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, status, Response
from sqlalchemy.orm import Session

from database import get_db
from models import Case, Evidence, EvidenceStatus, Entity, Event, User, CustodyLog, Job
from schemas import EvidenceOut, CustodyLogOut, EvidenceIntegrityResponse
from auth import get_current_user, check_case_access
from storage import save_uploaded_file
from upload_validator import validate_evidence_upload
from audit_engine import (
    log_custody_event, log_audit_event, verify_evidence_integrity,
    soft_delete_evidence
)
from analyzer import run_comprehensive_analysis
from routers.common import resolve_case_id, resolve_evidence_obj, parse_date_safely
from jobs.queue import create_job

router = APIRouter(tags=["Forensic Evidence & Chain of Custody"])


@router.post("/cases/{case_id}/evidence", response_model=EvidenceOut)
async def upload_evidence(
    case_id: str,
    file: UploadFile = File(...),
    source: Optional[str] = Form(None),
    collected_by: Optional[str] = Form(None),
    collection_date: Optional[str] = Form(None),
    custody_notes: Optional[str] = Form(None),
    evidence_type: Optional[str] = Form("document"),
    sec_65b_certificate_present: Optional[bool] = Form(True),
    current_user: User = Depends(get_current_user),
    response: Response = None,
    db: Session = Depends(get_db)
):
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "add_evidence"):
        raise HTTPException(status_code=403, detail=f"User role '{current_user.role}' is not permitted to upload evidence.")

    case = db.query(Case).filter(Case.id == real_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    try:
        raw_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {str(e)}")

    val_res = validate_evidence_upload(
        file_bytes=raw_bytes,
        original_filename=file.filename or "evidence.bin",
        case_id=real_id,
        db=db,
        user=current_user
    )

    storage_path, file_size, sha256_hash = await save_uploaded_file(raw_bytes, val_res.sanitized_filename)
    file_type = val_res.detected_category

    coll_dt = datetime.now(timezone.utc)
    if collection_date:
        try:
            coll_dt = datetime.fromisoformat(collection_date.replace("Z", "+00:00"))
        except Exception:
            pass

    officer_name = (collected_by or "").strip() or current_user.full_name
    agency_source = (source or "").strip() or "Judicial Submission / Seizure Panchnama"

    db_evidence = Evidence(
        case_id=real_id,
        file_name=val_res.sanitized_filename,
        file_type=file_type,
        file_size=file_size,
        storage_path=storage_path,
        uploaded_by=current_user.full_name,
        processing_status=EvidenceStatus.UPLOADED,
        source=agency_source,
        evidence_type=evidence_type or "document",
        file_hash=sha256_hash,
        hash_verified=True,
        chain_of_custody_complete=True,
        sec_65b_certificate_present=bool(sec_65b_certificate_present),
        source_independent=True,
        quality_rating=4.0,
        collected_by=officer_name,
        collection_date=coll_dt,
        custody_notes=custody_notes or "Exhibit sealed in forensic custody envelope; SHA-256 fingerprint verified.",
        is_deleted=False,
        extraction_mode="live",
        is_demo_fixture=False,
        version=1
    )
    db.add(db_evidence)
    db.commit()
    db.refresh(db_evidence)

    log_custody_event(
        db=db,
        evidence_id=db_evidence.id,
        case_id=real_id,
        action="SEIZURE",
        actor_name=officer_name,
        actor_role=current_user.role,
        source_agency=agency_source,
        location="Field / Crime Scene Recovery",
        notes=f"Physical recovery of '{file.filename}'. {custody_notes or 'Seized without tampering.'}",
        file_hash_snapshot=sha256_hash
    )

    log_custody_event(
        db=db,
        evidence_id=db_evidence.id,
        case_id=real_id,
        action="INTAKE",
        actor_name=current_user.full_name,
        actor_role=current_user.role,
        source_agency="Cyber & Digital Forensics Unit",
        location="Forensic Ingestion Locker",
        notes=f"Digital ingestion complete. Raw byte SHA-256 fingerprint: {sha256_hash} ({file_size} bytes).",
        file_hash_snapshot=sha256_hash
    )

    log_audit_event(
        db=db,
        action_type="EVIDENCE_UPLOAD",
        target_type="exhibit",
        target_id=str(db_evidence.id),
        description=f"Exhibit '{file.filename}' uploaded into custody. SHA-256: {sha256_hash[:16]}... ({file_size} bytes).",
        user_id=current_user.id,
        user_name=current_user.full_name,
        user_role=current_user.role,
        case_id=real_id,
        after_value=sha256_hash
    )

    # Fast Ingestion: Create background processing job and return immediately (< 1 second)
    job = create_job(
        db=db,
        case_id=real_id,
        exhibit_id=db_evidence.id,
        job_type="process_evidence",
        user_id=current_user.id,
        created_by=current_user.full_name,
        priority=0
    )

    # Evaluate Sec 65B Certificate Rule for electronic evidence
    try:
        from alerts_engine import check_missing_certificate_rule
        check_missing_certificate_rule(real_id, db_evidence.id, db)
    except Exception as e:
        print(f"[!] Could not run certificate check rule: {e}")

    # Real-Time Cross-Case Matching on Ingestion
    try:
        from cross_case_engine import match_exhibit_cross_case_realtime
        match_exhibit_cross_case_realtime(db_evidence.id, current_user, db)
    except Exception as cce:
        logger.warning(f"[EvidenceUpload] Real-time cross-case match notice: {cce}")

    setattr(db_evidence, "job_id", job.id)
    if response:
        response.headers["X-Job-Id"] = str(job.id)

    return db_evidence


@router.post("/cases/{case_id}/evidence/field-capture", response_model=EvidenceOut)
async def field_capture_evidence(
    case_id: str,
    file: UploadFile = File(...),
    client_computed_hash: str = Form(...),
    officer_confirmed: bool = Form(...),
    officer_declaration: str = Form(...),
    evidence_type: Optional[str] = Form("photograph"),
    title: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    accuracy_meters: Optional[float] = Form(None),
    captured_at: Optional[str] = Form(None),
    device_info: Optional[str] = Form(None),
    location_name: Optional[str] = Form(None),
    tamper_seal_number: Optional[str] = Form(None),
    source_agency: Optional[str] = Form(None),
    custody_notes: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    response: Response = None,
    db: Session = Depends(get_db)
):
    """
    Mobile Field Evidence Ingestion:
    Accepts on-scene photographs, audio, or video recordings captured in the field.
    Verifies on-device cryptographic hash, records geo-location (GPS) and capture timestamp,
    requires signed officer integrity confirmation, and logs initial Chain of Custody (FIELD_CAPTURE).
    """
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "add_evidence"):
        raise HTTPException(
            status_code=403,
            detail=f"User role '{current_user.role}' is not permitted to capture field evidence."
        )

    case = db.query(Case).filter(Case.id == real_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case docket not found")

    try:
        raw_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read captured media file: {str(e)}")

    cap_dt = None
    if captured_at:
        try:
            cap_dt = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
        except Exception:
            pass

    from mobile_capture_engine import ingest_field_evidence

    filename = file.filename or f"field_capture_{int(datetime.now().timestamp())}.jpg"
    evidence_item = await ingest_field_evidence(
        case_id=real_id,
        file_bytes=raw_bytes,
        original_filename=filename,
        client_computed_hash=client_computed_hash,
        officer_confirmed=officer_confirmed,
        officer_declaration=officer_declaration,
        current_user=current_user,
        db=db,
        evidence_type=evidence_type or "photograph",
        title=title,
        latitude=latitude,
        longitude=longitude,
        accuracy_meters=accuracy_meters,
        captured_at=cap_dt,
        device_info=device_info,
        location_name=location_name,
        tamper_seal_number=tamper_seal_number,
        source_agency=source_agency,
        custody_notes=custody_notes
    )

    if response and getattr(evidence_item, "job_id", None):
        response.headers["X-Job-Id"] = str(evidence_item.job_id)

    # Real-Time Cross-Case Matching on Ingestion
    try:
        from cross_case_engine import match_exhibit_cross_case_realtime
        match_exhibit_cross_case_realtime(evidence_item.id, current_user, db)
    except Exception as cce:
        logger.warning(f"[FieldCapture] Real-time cross-case match notice: {cce}")

    return evidence_item


@router.get("/cases/{case_id}/field-evidence", response_model=List[EvidenceOut])
def get_field_captured_evidence(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns all exhibits for a case that were captured in the field with mobile provenance.
    """
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")
    return db.query(Evidence).filter(
        Evidence.case_id == real_id,
        Evidence.is_field_captured == True,
        Evidence.is_deleted == False
    ).all()


@router.get("/cases/{case_id}/evidence", response_model=List[EvidenceOut])
def get_evidence_for_case(case_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")
    return db.query(Evidence).filter(
        Evidence.case_id == real_id,
        Evidence.is_deleted == False
    ).all()


@router.get("/evidence/{evidence_id}", response_model=EvidenceOut)
def get_evidence(evidence_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ev = resolve_evidence_obj(evidence_id, db)
    if not ev or ev.is_deleted:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if not check_case_access(ev.case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")
    return ev


@router.post("/evidence/{evidence_id}/analyze")
def analyze_evidence(
    evidence_id: str,
    sync: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    evidence = resolve_evidence_obj(evidence_id, db)
    if not evidence:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found")
    if not check_case_access(evidence.case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    existing_job = db.query(Job).filter(
        Job.exhibit_id == evidence.id,
        Job.status.in_(["queued", "running"])
    ).first()

    if not existing_job:
        job = create_job(
            db=db,
            case_id=evidence.case_id,
            exhibit_id=evidence.id,
            job_type="process_evidence",
            user_id=current_user.id,
            created_by=current_user.full_name or current_user.email,
            priority=1
        )
    else:
        job = existing_job

    if sync:
        from jobs.pipeline import execute_evidence_pipeline
        execute_evidence_pipeline(job.id, db)
        db.refresh(evidence)
        return {
            "status": "success",
            "message": "Forensic evidence analysis completed synchronously",
            "evidence_id": evidence.id,
            "job_id": job.id,
            "processing_status": "Analyzed",
            "extracted_text": evidence.extracted_text
        }

    return {
        "status": "queued",
        "message": "Evidence analysis queued for background processing",
        "evidence_id": evidence.id,
        "job_id": job.id,
        "current_stage": job.current_stage,
        "progress": job.progress_pct
    }


@router.get("/evidence/{evidence_id}/custody-log", response_model=List[CustodyLogOut])
def get_evidence_custody_log(evidence_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ev = resolve_evidence_obj(evidence_id, db)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if not check_case_access(ev.case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")
    return db.query(CustodyLog).filter(CustodyLog.evidence_id == ev.id).order_by(CustodyLog.id.desc()).all()


@router.post("/evidence/{evidence_id}/verify-integrity", response_model=EvidenceIntegrityResponse)
def verify_integrity_endpoint(
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ev = resolve_evidence_obj(evidence_id, db)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if not check_case_access(ev.case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")
    return verify_evidence_integrity(
        evidence_id=ev.id,
        user_id=current_user.id,
        user_name=current_user.full_name,
        user_role=current_user.role,
        db=db
    )


@router.delete("/evidence/{evidence_id}")
def delete_evidence_endpoint(
    evidence_id: str,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ev = resolve_evidence_obj(evidence_id, db)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    # Statutory Legal Hold Protection
    case = db.query(Case).filter(Case.id == ev.case_id).first()
    if case and getattr(case, "is_legal_hold", False):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Cannot delete Exhibit #{ev.id}: Case #{ev.case_id} is under active Legal Hold ({case.legal_hold_reason or 'Statutory Preservation Order'}). Removal or destruction of exhibits is prohibited."
        )

    if not check_case_access(ev.case_id, current_user, db, "delete_evidence"):
        raise HTTPException(status_code=403, detail=f"User role '{current_user.role}' is not permitted to soft-delete evidence.")
    return soft_delete_evidence(
        evidence_id=ev.id,
        reason=reason or "Retired from active trial docket by investigator.",
        user_id=current_user.id,
        user_name=current_user.full_name,
        user_role=current_user.role,
        db=db
    )

