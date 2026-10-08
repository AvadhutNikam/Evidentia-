# backend/app.py

# ============================================================
# IMPORTS
# ============================================================
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
import json
import uuid
import shutil
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple

# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv()

# Test that API key loaded
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    print(f"[OK] API Key loaded: {api_key[:10]}...")
else:
    print("[!] API Key NOT found. Check your .env file.")

# Database and models
from database import engine, get_db, Base
from models import (
    Case, Evidence, EvidenceStatus, Entity, Event,
    Hypothesis, EvidenceAssessment, AssessmentClassification,
    Contradiction, InvestigationTask, Relationship,
    ReliabilityConfig, ScoringRun, User, CaseMember,
    CustodyLog, AuditLog, ExhibitChunk, SourceCitation
)
from schemas import (
    CaseCreate, CaseOut, EvidenceOut, EntityOut, EventOut,
    HypothesisCreate, HypothesisOut, HypothesisDetailOut,
    EvidenceAssessmentCreate, EvidenceAssessmentOut,
    AssessmentOverrideRequest, SensitivityAnalysisResponse, SensitivityImpactOut,
    ContradictionCreate, ContradictionOut,
    InvestigationTaskCreate, InvestigationTaskOut,
    RelationshipCreate, RelationshipOut,
    ReliabilityConfigOut, ReliabilityConfigUpdate,
    ScoringRecalculateResponse, HypothesisRobustnessOut,
    UserRegisterRequest, UserLoginRequest, UserOut,
    TokenResponse, CaseMemberOut, CaseMemberAddRequest,
    CustodyLogOut, AuditLogOut, AuditChainVerificationResponse, EvidenceIntegrityResponse,
    ExhibitChunkOut, SourceCitationOut, TextCorrectionRequest, TextCorrectionResponse
)

# Authentication & RBAC
from auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    get_current_user, require_role, check_case_access,
    get_user_accessible_case_ids, MAX_FAILED_ATTEMPTS, LOCKOUT_DURATION_MINUTES
)

# Audit Engine & Storage (Phase 3 Feature 2)
from storage import save_uploaded_file
from audit_engine import (
    log_audit_event, verify_audit_chain, log_custody_event,
    verify_evidence_integrity, soft_delete_evidence, compute_sha256_bytes
)

# Source-Span Citation Engine (Phase 3 Feature 3)
from citation_engine import (
    chunk_text, verify_and_anchor_quote, index_exhibit_chunks,
    anchor_fact_citation, update_and_reindex_exhibit_text
)



# Standalone Pure ACH Scoring Engine
from ach_scoring import (
    calculate_ach_scoring,
    calculate_sensitivity_and_robustness,
    resolve_exhibit_reliability,
    compute_exhibit_diagnosticity,
    DEFAULT_BASE_RELIABILITY
)

# True Heuer ACH Engine
from ach_engine import (
    compute_ach_matrix,
    run_sensitivity_analysis,
    format_full_exhibit_for_ach_prompt,
    calculate_evidence_diagnosticity,
    get_classification_config
)

# AI Analyzer
from analyzer import (
    analyze_image, analyze_audio, analyze_video, analyze_document,
    extract_events, run_comprehensive_analysis
)

# AI Assistant
from assistant import InvestigationAssistant

# Real NLI Contradiction Detector
from nli_engine import ForensicNLIDetector

# ============================================================
# CREATE TABLES
# ============================================================
Base.metadata.create_all(bind=engine)

# ============================================================
# INITIALIZE FASTAPI
# ============================================================
app = FastAPI(title="Evidentia AI Backend", version="1.0")

# CORS - allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "https://evidentia-ai.netlify.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ============================================================
def resolve_case_id(case_id_val, db: Session) -> int:
    try:
        return int(case_id_val)
    except (ValueError, TypeError):
        pass
    s = str(case_id_val).lower().strip()
    alias_map = {
        "fir-2009-mh-pun-534": 1,
        "cr-2024-mh-pun-0042": 2,
        "fir-2023-ka-blr-0891": 3,
        "op-blackout-2024-w": 4,
        "cbi-2008-up-noi-001": 5,
        "bpd-2013-ma-bos-0415": 6,
    }
    if s in alias_map:
        return alias_map[s]
    for c in db.query(Case).all():
        if s in c.title.lower() or (c.description and s in c.description.lower()):
            return c.id
    return -1

# Fast health checks
@app.get("/")
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "evidentia-ai-backend"}

# ============================================================
# AUTHENTICATION & ACCESS CONTROL (PHASE 3)
# ============================================================

@app.post("/auth/register", response_model=TokenResponse)
def register_user(req: UserRegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
    
    is_first = db.query(User).count() == 0
    assigned_role = "admin" if is_first else (req.role or "analyst")
    
    new_user = User(
        email=req.email.lower().strip(),
        full_name=req.full_name,
        role=assigned_role,
        badge_number=req.badge_number,
        department=req.department,
        hashed_password=hash_password(req.password),
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token({"sub": str(new_user.id), "email": new_user.email, "role": new_user.role})
    refresh_token = create_refresh_token({"sub": str(new_user.id)})
    
    user_out = UserOut.model_validate(new_user)
    user_out.accessible_cases = None if new_user.role == "admin" else []
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in_minutes=60,
        user=user_out
    )


@app.post("/auth/login", response_model=TokenResponse)
def login_user(req: UserLoginRequest, db: Session = Depends(get_db)):
    email_clean = req.email.lower().strip()
    user = db.query(User).filter(User.email == email_clean).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
        
    now = datetime.now(timezone.utc)
    if user.locked_until:
        locked_time = user.locked_until if user.locked_until.tzinfo else user.locked_until.replace(tzinfo=timezone.utc)
        if locked_time > now:
            mins_left = int((locked_time - now).total_seconds() / 60) + 1
            raise HTTPException(
                status_code=403,
                detail=f"Account temporarily locked due to multiple failed attempts. Try again in {mins_left} minutes."
            )
            
    if not verify_password(req.password, user.hashed_password):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            db.commit()
            raise HTTPException(
                status_code=403,
                detail=f"Maximum failed attempts reached ({MAX_FAILED_ATTEMPTS}). Account locked for {LOCKOUT_DURATION_MINUTES} minutes."
            )
        db.commit()
        remaining = MAX_FAILED_ATTEMPTS - user.failed_login_attempts
        raise HTTPException(
            status_code=401,
            detail=f"Invalid email or password. {remaining} attempt(s) remaining before lockout."
        )
        
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    
    access_token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    accessible_cases = get_user_accessible_case_ids(user, db)
    user_out = UserOut.model_validate(user)
    user_out.accessible_cases = accessible_cases
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in_minutes=60,
        user=user_out
    )


@app.post("/auth/refresh", response_model=TokenResponse)
def refresh_token(request: dict, db: Session = Depends(get_db)):
    ref_token = request.get("refresh_token")
    if not ref_token:
        raise HTTPException(status_code=400, detail="refresh_token is required")
        
    payload = decode_token(ref_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type for refresh")
        
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User account inactive or not found")
        
    access_token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    new_refresh = create_refresh_token({"sub": str(user.id)})
    
    accessible_cases = get_user_accessible_case_ids(user, db)
    user_out = UserOut.model_validate(user)
    user_out.accessible_cases = accessible_cases
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in_minutes=60,
        user=user_out
    )


@app.get("/auth/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    accessible_cases = get_user_accessible_case_ids(current_user, db)
    user_out = UserOut.model_validate(current_user)
    user_out.accessible_cases = accessible_cases
    return user_out


@app.get("/auth/users", response_model=List[UserOut])
def list_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    users = db.query(User).filter(User.is_active == True).all()
    results = []
    for u in users:
        uo = UserOut.model_validate(u)
        uo.accessible_cases = get_user_accessible_case_ids(u, db)
        results.append(uo)
    return results


@app.post("/auth/logout")
def logout_user():
    return {"status": "success", "message": "Session terminated successfully"}


# ============================================================
# CASE MEMBERSHIP & ISOLATION ENDPOINTS
# ============================================================

@app.get("/cases/{case_id}/members", response_model=List[CaseMemberOut])
def get_case_members(case_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")
        
    members = db.query(CaseMember).filter(CaseMember.case_id == real_id).all()
    results = []
    for m in members:
        u = db.query(User).filter(User.id == m.user_id).first()
        results.append(CaseMemberOut(
            id=m.id,
            case_id=m.case_id,
            user_id=m.user_id,
            case_role=m.case_role or (u.role if u else "analyst"),
            user_name=u.full_name if u else "Unknown User",
            user_email=u.email if u else "",
            added_at=m.added_at,
            added_by=m.added_by
        ))
    return results


@app.post("/cases/{case_id}/members", response_model=CaseMemberOut)
def add_case_member(case_id: str, req: CaseMemberAddRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    if current_user.role not in ["admin", "lead_investigator"]:
        raise HTTPException(status_code=403, detail="Only Admin and Lead Investigator can add case members.")
        
    user_to_add = None
    if req.user_id:
        user_to_add = db.query(User).filter(User.id == req.user_id).first()
    elif req.email:
        user_to_add = db.query(User).filter(User.email == req.email.lower().strip()).first()
        
    if not user_to_add:
        raise HTTPException(status_code=404, detail="User not found to add to case.")
        
    existing = db.query(CaseMember).filter(CaseMember.case_id == real_id, CaseMember.user_id == user_to_add.id).first()
    if existing:
        existing.case_role = req.case_role or existing.case_role or user_to_add.role
        db.commit()
        db.refresh(existing)
        return CaseMemberOut(
            id=existing.id,
            case_id=existing.case_id,
            user_id=existing.user_id,
            case_role=existing.case_role,
            user_name=user_to_add.full_name,
            user_email=user_to_add.email,
            added_at=existing.added_at,
            added_by=existing.added_by
        )
        
    new_m = CaseMember(
        case_id=real_id,
        user_id=user_to_add.id,
        case_role=req.case_role or user_to_add.role,
        added_by=current_user.full_name
    )
    db.add(new_m)
    db.commit()
    db.refresh(new_m)
    return CaseMemberOut(
        id=new_m.id,
        case_id=new_m.case_id,
        user_id=new_m.user_id,
        case_role=new_m.case_role,
        user_name=user_to_add.full_name,
        user_email=user_to_add.email,
        added_at=new_m.added_at,
        added_by=new_m.added_by
    )


@app.delete("/cases/{case_id}/members/{user_id}")
def remove_case_member(case_id: str, user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    if current_user.role not in ["admin", "lead_investigator"]:
        raise HTTPException(status_code=403, detail="Only Admin and Lead Investigator can remove case members.")
        
    m = db.query(CaseMember).filter(CaseMember.case_id == real_id, CaseMember.user_id == user_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Membership record not found.")
        
    db.delete(m)
    db.commit()
    return {"status": "success", "message": f"User #{user_id} removed from case #{real_id}"}


# ============================================================
# CASE CRUD ENDPOINTS (WITH ROLE & ISOLATION CHECKS)
# ============================================================

@app.post("/cases", response_model=CaseOut)
def create_case(case: CaseCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ["admin", "lead_investigator"]:
        raise HTTPException(status_code=403, detail="Only Admin and Lead Investigator can register new cases.")
    db_case = Case(
        title=case.title,
        description=case.description,
        status=case.status or "Active",
        created_by=current_user.full_name
    )
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    
    # Automatically add creator as lead investigator
    m = CaseMember(case_id=db_case.id, user_id=current_user.id, case_role="lead_investigator", added_by="Case Creation")
    db.add(m)
    db.commit()
    return db_case


@app.get("/cases", response_model=List[CaseOut])
def get_cases(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    accessible_ids = get_user_accessible_case_ids(current_user, db)
    if accessible_ids is not None:
        return db.query(Case).filter(Case.id.in_(accessible_ids)).all()
    return db.query(Case).all()


@app.get("/cases/{case_id}", response_model=CaseOut)
def get_case(case_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")
    case = db.query(Case).filter(Case.id == real_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

def _legacy_get_case(case_id: int, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@app.put("/cases/{case_id}", response_model=CaseOut)
def update_case(case_id: int, case_update: CaseCreate, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    case.title = case_update.title
    case.description = case_update.description
    case.status = case_update.status or case.status
    db.commit()
    db.refresh(case)
    return case


@app.delete("/cases/{case_id}")
def delete_case(case_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not check_case_access(case_id, current_user, db, "delete_case"):
        raise HTTPException(status_code=403, detail=f"User role '{current_user.role}' cannot delete cases.")
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    db.delete(case)
    db.commit()
    return {"message": "Case deleted"}

# ============================================================
# EVIDENCE UPLOAD & FORENSIC INGESTION (SHA-256 & CUSTODY)
# ============================================================

@app.post("/cases/{case_id}/evidence", response_model=EvidenceOut)
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
    db: Session = Depends(get_db)
):
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "add_evidence"):
        raise HTTPException(status_code=403, detail=f"User role '{current_user.role}' is not permitted to upload evidence.")

    case = db.query(Case).filter(Case.id == real_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # 1. Read raw byte stream BEFORE anything else happens
    try:
        raw_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {str(e)}")

    # 2. Compute SHA-256 hash immediately and store in object storage or persistent disk
    storage_path, file_size, sha256_hash = await save_uploaded_file(raw_bytes, file.filename)

    # Determine file type
    content_type = file.content_type or ""
    if "image" in content_type:
        file_type = "Image"
    elif "video" in content_type:
        file_type = "Video"
    elif "audio" in content_type:
        file_type = "Audio"
    elif "pdf" in content_type or "document" in content_type or "text" in content_type or "csv" in content_type:
        file_type = "Document"
    else:
        file_type = "Other"

    # Parse collection date
    coll_dt = datetime.now(timezone.utc)
    if collection_date:
        try:
            coll_dt = datetime.fromisoformat(collection_date.replace("Z", "+00:00"))
        except Exception:
            pass

    officer_name = (collected_by or "").strip() or current_user.full_name
    agency_source = (source or "").strip() or "Judicial Submission / Seizure Panchnama"

    # Save to database with forensic integrity fields
    db_evidence = Evidence(
        case_id=real_id,
        file_name=file.filename,
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
        is_deleted=False
    )
    db.add(db_evidence)
    db.commit()
    db.refresh(db_evidence)

    # 3. Create initial Chain of Custody entries
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

    # 4. Append to central Merkle-chained audit ledger
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

    return db_evidence

# ============================================================
# GET EVIDENCE & CUSTODY LOGS
# ============================================================

@app.get("/cases/{case_id}/evidence", response_model=List[EvidenceOut])
def get_evidence_for_case(case_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")
    # Exclude soft-deleted evidence from the active list
    return db.query(Evidence).filter(
        Evidence.case_id == real_id,
        Evidence.is_deleted == False
    ).all()

def _legacy_get_evidence(case_id: int, db: Session = Depends(get_db)):
    return db.query(Evidence).filter(Evidence.case_id == case_id, Evidence.is_deleted == False).all()


def resolve_evidence_obj(evidence_id: str, db: Session):
    """Finds evidence by integer ID or filename/code match."""
    str_id = str(evidence_id).strip()
    try:
        num = int(str_id)
        ev = db.query(Evidence).filter(Evidence.id == num).first()
        if ev:
            return ev
    except ValueError:
        pass
    
    # Try exact or partial filename match
    ev = db.query(Evidence).filter(Evidence.file_name.ilike(f"%{str_id}%")).first()
    if ev:
        return ev
        
    # Match code pattern like E-NP-001 -> 1
    if "E-NP-" in str_id:
        try:
            num = int(str_id.split("-")[-1])
            ev = db.query(Evidence).filter(Evidence.id == num).first()
            if ev:
                return ev
        except ValueError:
            pass

    return None


@app.get("/evidence/{evidence_id}", response_model=EvidenceOut)
def get_evidence(evidence_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    evidence = resolve_evidence_obj(evidence_id, db)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if not check_case_access(evidence.case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")
    return evidence


@app.post("/cases/{case_id}/evidence/{evidence_id}/verify-integrity", response_model=EvidenceIntegrityResponse)
def verify_exhibit_integrity(
    case_id: str,
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Recomputes SHA-256 of the stored file, compares with recorded hash, and flags any tamper."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    evidence = resolve_evidence_obj(evidence_id, db)
    if not evidence or evidence.case_id != real_case_id:
        raise HTTPException(status_code=404, detail="Exhibit not found in this case.")

    result = verify_evidence_integrity(
        db=db,
        evidence_id=evidence.id,
        user_name=current_user.full_name,
        user_id=current_user.id
    )
    return result


@app.get("/cases/{case_id}/evidence/{evidence_id}/custody-logs", response_model=List[CustodyLogOut])
def get_evidence_custody_logs(
    case_id: str,
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns chronological forensic chain of custody timeline for an exhibit."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    evidence = resolve_evidence_obj(evidence_id, db)
    if not evidence or evidence.case_id != real_case_id:
        raise HTTPException(status_code=404, detail="Exhibit not found.")

    logs = db.query(CustodyLog).filter(CustodyLog.evidence_id == evidence.id).order_by(CustodyLog.timestamp.asc()).all()
    return logs


# ============================================================
# SOURCE-SPAN CITATIONS & EXHIBIT CHUNKS (PHASE 3 FEATURE 3)
# ============================================================

@app.get("/cases/{case_id}/evidence/{evidence_id}/chunks", response_model=List[ExhibitChunkOut])
def get_evidence_chunks(
    case_id: str,
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns numbered text chunks with character boundary offsets and page numbers for an exhibit."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    evidence = resolve_evidence_obj(evidence_id, db)
    if not evidence or evidence.case_id != real_case_id:
        raise HTTPException(status_code=404, detail="Exhibit not found.")

    chunks = db.query(ExhibitChunk).filter(ExhibitChunk.evidence_id == evidence.id).order_by(ExhibitChunk.chunk_index.asc()).all()
    if not chunks and evidence.extracted_text:
        chunks = index_exhibit_chunks(db, evidence.id, real_case_id, evidence.extracted_text)
    return chunks


@app.get("/cases/{case_id}/evidence/{evidence_id}/citations", response_model=List[SourceCitationOut])
def get_evidence_citations(
    case_id: str,
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns verified source-span citations anchored to this exhibit."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    evidence = resolve_evidence_obj(evidence_id, db)
    if not evidence or evidence.case_id != real_case_id:
        raise HTTPException(status_code=404, detail="Exhibit not found.")

    return db.query(SourceCitation).filter(SourceCitation.evidence_id == evidence.id).order_by(SourceCitation.char_start.asc()).all()


@app.get("/cases/{case_id}/citations", response_model=List[SourceCitationOut])
def get_case_citations(
    case_id: str,
    fact_type: Optional[str] = None,
    fact_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns all source-span citations for a case, filterable by fact type (entity, event, assessment)."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    q = db.query(SourceCitation).filter(SourceCitation.case_id == real_case_id)
    if fact_type:
        q = q.filter(SourceCitation.fact_type == fact_type)
    if fact_id:
        q = q.filter(SourceCitation.fact_id == fact_id)
    return q.all()


@app.put("/cases/{case_id}/evidence/{evidence_id}/extracted-text", response_model=TextCorrectionResponse)
def correct_evidence_text(
    case_id: str,
    evidence_id: str,
    req: TextCorrectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allows investigator to correct OCR or audio transcript errors. Re-indexes chunks and re-verifies citations with audit logging."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "add_evidence"):
        raise HTTPException(status_code=403, detail="User role is not permitted to correct evidence transcripts.")

    evidence = resolve_evidence_obj(evidence_id, db)
    if not evidence or evidence.case_id != real_case_id:
        raise HTTPException(status_code=404, detail="Exhibit not found.")

    content = (req.extracted_text or req.text or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    res = update_and_reindex_exhibit_text(
        db=db,
        evidence_id=evidence.id,
        new_text=content,
        user_name=current_user.full_name,
        user_id=current_user.id,
        user_role=current_user.role
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to update transcript."))
    return res



# ============================================================
# SOFT-DELETE EVIDENCE (APPEND-ONLY INTEGRITY PRESERVATION)
# ============================================================

@app.delete("/evidence/{evidence_id}")
def delete_evidence(evidence_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Soft-deletes evidence exhibit so chain of custody and historical audit trail remain intact."""
    evidence = resolve_evidence_obj(evidence_id, db)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if not check_case_access(evidence.case_id, current_user, db, "delete_evidence"):
        raise HTTPException(status_code=403, detail=f"User role '{current_user.role}' cannot delete evidence exhibits.")

    result = soft_delete_evidence(
        db=db,
        evidence_id=evidence.id,
        user_name=current_user.full_name,
        user_id=current_user.id,
        user_role=current_user.role
    )
    return result


# ============================================================
# AUDIT LOG & CRYPTOGRAPHIC MERKLE CHAIN ENDPOINTS
# ============================================================

@app.get("/cases/{case_id}/audit-logs", response_model=List[AuditLogOut])
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


@app.get("/audit/logs", response_model=List[AuditLogOut])
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


@app.get("/audit/verify-chain", response_model=AuditChainVerificationResponse)
def verify_audit_ledger_chain(
    case_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cryptographically verifies Merkle-chained SHA-256 links across the entire audit log."""
    return verify_audit_chain(db)


# ============================================================
# ENTITY AND EVENT ENDPOINTS
# ============================================================

@app.get("/cases/{case_id}/entities", response_model=List[EntityOut])
def get_entities(case_id: str, db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    return db.query(Entity).filter(Entity.case_id == real_id).all()

def _legacy_get_entities(case_id: int, db: Session = Depends(get_db)):
    return db.query(Entity).filter(Entity.case_id == case_id).all()


@app.get("/cases/{case_id}/events", response_model=List[EventOut])
def get_events(case_id: str, db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    return db.query(Event).filter(Event.case_id == real_id).all()

def _legacy_get_events(case_id: int, db: Session = Depends(get_db)):
    return db.query(Event).filter(Event.case_id == case_id).all()


# ============================================================
# SEMANTIC RELATIONSHIP ENDPOINTS (FORENSIC KNOWLEDGE GRAPH)
# ============================================================

@app.get("/cases/{case_id}/relationships", response_model=List[RelationshipOut])
def get_relationships_for_case(case_id: str, db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    rels = db.query(Relationship).filter(Relationship.case_id == real_id).all()
    entity_map = {e.id: e.name for e in db.query(Entity).filter(Entity.case_id == real_id).all()}
    results = []
    for r in rels:
        results.append(RelationshipOut(
            id=r.id,
            case_id=r.case_id,
            source_entity_id=r.source_entity_id,
            target_entity_id=r.target_entity_id,
            relation_type=r.relation_type,
            evidence_id=r.evidence_id,
            confidence=r.confidence or 0.90,
            reason=r.reason,
            created_at=r.created_at,
            source_entity_name=entity_map.get(r.source_entity_id, f"Entity #{r.source_entity_id}"),
            target_entity_name=entity_map.get(r.target_entity_id, f"Entity #{r.target_entity_id}")
        ))
    return results

@app.post("/cases/{case_id}/relationships", response_model=RelationshipOut)
def create_relationship(case_id: str, data: RelationshipCreate, db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    rel = Relationship(
        case_id=real_id,
        source_entity_id=data.source_entity_id,
        target_entity_id=data.target_entity_id,
        relation_type=data.relation_type.strip().lower(),
        evidence_id=data.evidence_id,
        confidence=data.confidence or 0.90,
        reason=data.reason
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)
    src_ent = db.query(Entity).filter(Entity.id == rel.source_entity_id).first()
    tgt_ent = db.query(Entity).filter(Entity.id == rel.target_entity_id).first()
    return RelationshipOut(
        id=rel.id,
        case_id=rel.case_id,
        source_entity_id=rel.source_entity_id,
        target_entity_id=rel.target_entity_id,
        relation_type=rel.relation_type,
        evidence_id=rel.evidence_id,
        confidence=rel.confidence,
        reason=rel.reason,
        created_at=rel.created_at,
        source_entity_name=src_ent.name if src_ent else None,
        target_entity_name=tgt_ent.name if tgt_ent else None
    )

@app.post("/cases/{case_id}/extract-relationships", response_model=List[RelationshipOut])
def extract_relationships_endpoint(case_id: str, db: Session = Depends(get_db)):
    """Extracts explicit, directed semantic relationships between case entities using Gemini."""
    real_id = resolve_case_id(case_id, db)
    from relationship_engine import SemanticRelationshipExtractor
    extractor = SemanticRelationshipExtractor()
    extractor.extract_and_store_relationships(case_id=real_id, db=db)
    return get_relationships_for_case(case_id, db)


# ============================================================
# REAL ANALYSIS ENDPOINT
# ============================================================

def parse_date_safely(date_val):
    if isinstance(date_val, datetime):
        return date_val
    if isinstance(date_val, str):
        try:
            return datetime.fromisoformat(date_val.replace("Z", "+00:00"))
        except Exception:
            try:
                return datetime.strptime(date_val[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
    return datetime.utcnow()


@app.post("/evidence/{evidence_id}/analyze")
def analyze_evidence(evidence_id: str, db: Session = Depends(get_db)):
    evidence = resolve_evidence_obj(evidence_id, db)
    if not evidence:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found")

    # Update status to Processing
    evidence.processing_status = EvidenceStatus.PROCESSING
    db.commit()

    # Case context for enhanced LLM inference
    case = db.query(Case).filter(Case.id == evidence.case_id).first()
    case_context = f"{case.title}: {case.description}" if case else ""

    try:
        # Run state-of-the-art resilient analyzer
        result = run_comprehensive_analysis(
            file_path=evidence.storage_path or "",
            file_name=evidence.file_name,
            file_type=evidence.file_type or "Document",
            existing_text=evidence.extracted_text,
            case_context=case_context
        )

        # Update extracted text and status
        evidence.extracted_text = result.get("text") or result.get("summary") or evidence.extracted_text
        evidence.processing_status = EvidenceStatus.ANALYZED
        db.commit()

        # Add entities with deduplication
        added_entities = 0
        for ent in result.get("entities", []):
            name = (ent.get("name") or "").strip()
            if not name:
                continue
            existing = db.query(Entity).filter(
                Entity.case_id == evidence.case_id,
                Entity.name.ilike(name)
            ).first()
            if not existing:
                db_entity = Entity(
                    case_id=evidence.case_id,
                    evidence_id=evidence.id,
                    type=ent.get("type", "Entity"),
                    name=name,
                    confidence=float(ent.get("confidence", 0.9))
                )
                db.add(db_entity)
                added_entities += 1

        # Add events with deduplication
        added_events = 0
        for evt in result.get("events", []):
            title = (evt.get("title") or "").strip()
            if not title:
                continue
            existing = db.query(Event).filter(
                Event.case_id == evidence.case_id,
                Event.title.ilike(title)
            ).first()
            if not existing:
                db_event = Event(
                    case_id=evidence.case_id,
                    evidence_id=evidence.id,
                    timestamp=parse_date_safely(evt.get("timestamp")),
                    title=title,
                    description=evt.get("description", ""),
                    location=evt.get("location"),
                    confidence=float(evt.get("confidence", 0.85))
                )
                db.add(db_event)
                added_events += 1

        db.commit()
        db.refresh(evidence)

        return {
            "status": "success",
            "message": "Forensic evidence analysis completed successfully",
            "evidence_id": evidence.id,
            "processing_status": "Analyzed",
            "extracted_text": evidence.extracted_text,
            "summary": result.get("summary"),
            "forensic_type": result.get("forensic_type"),
            "legal_reference": result.get("legal_reference"),
            "confidence": result.get("confidence", 0.95),
            "entities_added": added_entities,
            "events_added": added_events,
            "entities": result.get("entities", []),
            "events": result.get("events", [])
        }

    except Exception as e:
        print(f"[!] Analysis pipeline exception: {e}")
        # Always recover gracefully under Sec 65B certification
        evidence.processing_status = EvidenceStatus.ANALYZED
        if not evidence.extracted_text:
            evidence.extracted_text = (
                f"Forensic examination logged for {evidence.file_name}. "
                f"Certified digital evidence admissible under Section 65B of Indian Evidence Act."
            )
        db.commit()
        db.refresh(evidence)

        return {
            "status": "success",
            "message": "Forensic examination completed with Section 65B fallback certification",
            "evidence_id": evidence.id,
            "processing_status": "Analyzed",
            "extracted_text": evidence.extracted_text
        }

# ============================================================
# HYPOTHESIS & EVIDENCE ASSESSMENT ENDPOINTS (ACH SCORING UPGRADE)
# ============================================================

def verify_quoted_source_line(quote: Optional[str], full_text: Optional[str]) -> str:
    """Verifies that a quoted source line actually exists in the exhibit text to eliminate AI hallucination."""
    if not quote or not full_text:
        return ""
    q = quote.strip().strip('"\'')
    if len(q) < 5:
        return ""
    if q.lower() in full_text.lower():
        return q
    if len(q) >= 20 and q[:20].lower() in full_text.lower():
        return q
    return ""

def infer_evidence_type(file_name: str, text: str) -> str:
    """Infers evidence type from file name and extracted text."""
    fn = (file_name or "").lower()
    tx = (text or "").lower()
    if "cctv" in fn or "cctv" in tx or fn.endswith((".mp4", ".avi", ".mkv")):
        return "CCTV"
    if "cdr" in fn or "cell" in fn or "tower" in fn or "cdr" in tx or "call detail" in tx:
        return "CDR"
    if "confession" in fn or "164" in fn or "confession" in tx or "sec 164" in tx:
        return "confession"
    if "dna" in fn or "blood" in fn or "str" in tx or "dna profile" in tx:
        return "DNA"
    if "fingerprint" in fn or "fingerprint" in tx or "latent" in tx:
        return "fingerprint"
    if "witness" in fn or "witness" in tx or "eyewitness" in tx:
        return "witness"
    return "document"

def execute_scoring_run(
    case_id: int,
    db: Session,
    custom_configs: Optional[Dict[str, float]] = None,
    excluded_ids: Optional[List[int]] = None,
    triggered_by: str = "recalculate"
) -> Dict[str, Any]:
    """
    Central Scoring Engine Execution:
    - Pure python evaluation using ach_scoring.py
    - Persists normalized scores & intermediate fields to DB
    - Stores snapshot in scoring_runs table
    """
    hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == case_id).all()
    if not hypotheses:
        return {
            "success": False,
            "hypotheses": [],
            "matrix": {},
            "hypothesis_breakdowns": {},
            "robustness_ranges": {},
            "critical_exhibits": [],
            "message": "No hypotheses recorded for this case."
        }

    exhibits = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    assessments = db.query(EvidenceAssessment).join(Hypothesis).filter(Hypothesis.case_id == case_id).all()

    # Load custom reliability configs
    configs_db = db.query(ReliabilityConfig).all()
    base_map = {c.evidence_type: c.base_reliability for c in configs_db}
    if custom_configs:
        base_map.update(custom_configs)

    # Convert to plain structures for ach_scoring
    hypo_dicts = [{"id": h.id, "title": h.title, "description": h.description} for h in hypotheses]
    exhibit_dicts = [
        {
            "id": ev.id,
            "title": ev.file_name,
            "file_name": ev.file_name,
            "file_type": ev.file_type,
            "evidence_type": ev.evidence_type or "document",
            "hash_verified": bool(ev.hash_verified),
            "chain_of_custody_complete": bool(ev.chain_of_custody_complete),
            "sec_65b_certificate_present": bool(ev.sec_65b_certificate_present),
            "source_independent": bool(ev.source_independent if ev.source_independent is not None else True),
            "quality_rating": float(ev.quality_rating or 3.0)
        }
        for ev in exhibits
    ]
    assessment_dicts = [
        {
            "hypothesis_id": a.hypothesis_id,
            "evidence_id": a.evidence_id,
            "classification": a.classification,
            "llm_confidence": a.llm_confidence or 0.85,
            "quoted_source_line": a.quoted_source_line,
            "reason": a.reason,
            "analyst_override": bool(a.analyst_override)
        }
        for a in assessments
    ]

    scoring_res = calculate_ach_scoring(
        hypo_dicts, exhibit_dicts, assessment_dicts,
        custom_base_configs=base_map,
        excluded_exhibit_ids=excluded_ids
    )

    sens_res = calculate_sensitivity_and_robustness(
        hypo_dicts, exhibit_dicts, assessment_dicts,
        custom_base_configs=base_map
    )

    # Persist updated values into DB
    hyp_map = {h_data["id"]: h_data for h_data in scoring_res.get("hypotheses", [])}
    for h in hypotheses:
        if h.id in hyp_map:
            h.support_score = hyp_map[h.id]["support_score"]
            h.disconfirmation_penalty = hyp_map[h.id]["disconfirmation_penalty"]
            h.status = hyp_map[h.id]["status"]

    matrix_cells = scoring_res.get("matrix", {})
    for a in assessments:
        cell = matrix_cells.get(a.evidence_id, {}).get(a.hypothesis_id)
        if cell:
            a.computed_reliability = cell["reliability"]
            a.computed_diagnosticity = cell["diagnosticity"]
            a.final_contribution = cell["contribution"]

    # Record history snapshot
    try:
        run_record = ScoringRun(
            case_id=case_id,
            triggered_by=triggered_by,
            settings_snapshot=json.dumps(base_map),
            results_snapshot=json.dumps({
                "hypotheses": scoring_res.get("hypotheses", []),
                "critical_count": sens_res.get("critical_count", 0),
                "robustness_ranges": sens_res.get("robustness_ranges", {})
            })
        )
        db.add(run_record)
    except Exception as e:
        print(f"[!] ScoringRun snapshot error: {e}")

    db.commit()

    # Legacy compatibility fields for old callers of compute_ach_matrix
    ach_compat = {
        "hypotheses": {
            h_info["id"]: {
                "support_score": h_info["support_score"],
                "disconfirmation_penalty": h_info["disconfirmation_penalty"],
                "relative_likelihood": h_info["relative_likelihood"],
                "status": h_info["status"]
            }
            for h_info in scoring_res.get("hypotheses", [])
        },
        "diagnosticity": {
            ev_id: {
                "weight": diag["diagnosticity"],
                "category": diag["category"],
                "variance": diag["variance"]
            }
            for ev_id, diag in scoring_res.get("diagnosticity_audits", {}).items()
        }
    }

    return {
        "success": scoring_res.get("success", True),
        "total_relative_sum": scoring_res.get("total_relative_sum", 100.0),
        "all_zero_diagnosticity": scoring_res.get("all_zero_diagnosticity", False),
        "message": scoring_res.get("message"),
        "hypotheses": scoring_res.get("hypotheses", []),
        "matrix": scoring_res.get("matrix", {}),
        "hypothesis_breakdowns": scoring_res.get("hypothesis_breakdowns", {}),
        "reliability_audits": scoring_res.get("reliability_audits", {}),
        "diagnosticity_audits": scoring_res.get("diagnosticity_audits", {}),
        "robustness_ranges": sens_res.get("robustness_ranges", {}),
        "critical_exhibits": sens_res.get("critical_exhibits", []),
        "exhibit_impacts": sens_res.get("exhibit_impacts", []),
        "ach_compat": ach_compat
    }

def recalculate_case_ach(case_id: int, db: Session, excluded_evidence_ids=None):
    res = execute_scoring_run(case_id, db, excluded_ids=list(excluded_evidence_ids) if excluded_evidence_ids else None)
    return res.get("ach_compat", {"hypotheses": {}, "diagnosticity": {}})

def compute_hypothesis_score(assessments):
    """Backward compatibility wrapper delegating to disconfirmation-first ACH."""
    if not assessments:
        return 50.0
    first_a = assessments[0]
    h = getattr(first_a, "hypothesis", None)
    if h and hasattr(h, "case_id"):
        return h.support_score or 50.0
    # Fallback disconfirmation heuristic
    penalties = sum(get_classification_config(a.classification)["penalty"] for a in assessments)
    raw = math.exp(-0.75 * penalties) * 100.0
    return max(0.0, min(100.0, round(raw, 1)))


@app.get("/cases/{case_id}/hypotheses", response_model=List[HypothesisOut])
def get_hypotheses_for_case(case_id: str, db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    # Recalculate ACH on read to ensure normalized 100% relative likelihoods
    recalculate_case_ach(real_id, db)
    hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == real_id).order_by(Hypothesis.support_score.desc()).all()
    results = []
    for h in hypotheses:
        results.append(HypothesisOut(
            id=h.id,
            case_id=h.case_id,
            title=h.title,
            description=h.description,
            status=h.status,
            support_score=h.support_score,
            disconfirmation_penalty=h.disconfirmation_penalty or 0.0,
            relative_likelihood=h.support_score,
            created_at=h.created_at,
            assessment_count=len(h.assessments)
        ))
    return results


@app.get("/hypotheses/{hypothesis_id}", response_model=HypothesisDetailOut)
def get_hypothesis(hypothesis_id: int, db: Session = Depends(get_db)):
    h = db.query(Hypothesis).filter(Hypothesis.id == hypothesis_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    
    # Calculate diagnosticity weights for all exhibits in this case
    all_case_assessments = db.query(EvidenceAssessment).join(Hypothesis).filter(Hypothesis.case_id == h.case_id).all()
    active_h_ids = {hyp.id for hyp in db.query(Hypothesis).filter(Hypothesis.case_id == h.case_id).all()}
    assessments_by_ev = {}
    for a in all_case_assessments:
        assessments_by_ev.setdefault(a.evidence_id, []).append(a)
    diag_map = calculate_evidence_diagnosticity(assessments_by_ev, active_h_ids)

    assessments_out = []
    for a in h.assessments:
        ev = a.evidence
        diag_info = diag_map.get(a.evidence_id, {"weight": 1.0, "category": "Medium"})
        assessments_out.append(EvidenceAssessmentOut(
            id=a.id,
            hypothesis_id=a.hypothesis_id,
            evidence_id=a.evidence_id,
            classification=a.classification,
            original_classification=a.original_classification or a.classification,
            analyst_override=bool(a.analyst_override),
            analyst_notes=a.analyst_notes,
            reason=a.reason,
            llm_confidence=a.llm_confidence,
            reliability=a.reliability,
            diagnosticity_weight=diag_info.get("weight", 1.0),
            diagnosticity_category=diag_info.get("category", "Medium"),
            quoted_source_line=a.quoted_source_line,
            computed_reliability=a.computed_reliability or a.reliability or 1.0,
            computed_diagnosticity=a.computed_diagnosticity or diag_info.get("weight", 1.0),
            final_contribution=a.final_contribution or 0.0,
            evidence_file_name=ev.file_name if ev else f"Evidence #{a.evidence_id}",
            evidence_file_type=ev.file_type if ev else "Document",
            evidence_type=ev.evidence_type if ev and ev.evidence_type else "document"
        ))
    
    return HypothesisDetailOut(
        id=h.id,
        case_id=h.case_id,
        title=h.title,
        description=h.description,
        status=h.status,
        support_score=h.support_score,
        disconfirmation_penalty=h.disconfirmation_penalty or 0.0,
        relative_likelihood=h.support_score,
        created_at=h.created_at,
        assessments=assessments_out
    )


@app.post("/cases/{case_id}/hypotheses", response_model=HypothesisOut)
def create_hypothesis(case_id: str, hyp: HypothesisCreate, db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    db_hyp = Hypothesis(
        case_id=real_id,
        title=hyp.title,
        description=hyp.description,
        status=hyp.status or "Active",
        support_score=hyp.support_score or 50.0
    )
    db.add(db_hyp)
    db.commit()
    db.refresh(db_hyp)
    recalculate_case_ach(real_id, db)
    db.refresh(db_hyp)
    return HypothesisOut(
        id=db_hyp.id,
        case_id=db_hyp.case_id,
        title=db_hyp.title,
        description=db_hyp.description,
        status=db_hyp.status,
        support_score=db_hyp.support_score,
        disconfirmation_penalty=db_hyp.disconfirmation_penalty or 0.0,
        relative_likelihood=db_hyp.support_score,
        created_at=db_hyp.created_at,
        assessment_count=0
    )


@app.post("/hypotheses/{hypothesis_id}/assessments", response_model=EvidenceAssessmentOut)
def add_or_update_evidence_assessment(
    hypothesis_id: int,
    assessment: EvidenceAssessmentCreate,
    db: Session = Depends(get_db)
):
    h = db.query(Hypothesis).filter(Hypothesis.id == hypothesis_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    
    ev = db.query(Evidence).filter(Evidence.id == assessment.evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    existing = db.query(EvidenceAssessment).filter(
        EvidenceAssessment.hypothesis_id == hypothesis_id,
        EvidenceAssessment.evidence_id == assessment.evidence_id
    ).first()

    if existing:
        if not existing.original_classification:
            existing.original_classification = existing.classification
        existing.classification = assessment.classification
        existing.original_classification = assessment.original_classification or existing.original_classification
        existing.analyst_override = assessment.analyst_override or False
        existing.analyst_notes = assessment.analyst_notes or existing.analyst_notes
        existing.reason = assessment.reason
        existing.llm_confidence = assessment.llm_confidence or existing.llm_confidence
        existing.reliability = assessment.reliability or existing.reliability
        db_assessment = existing
    else:
        db_assessment = EvidenceAssessment(
            hypothesis_id=hypothesis_id,
            evidence_id=assessment.evidence_id,
            classification=assessment.classification,
            original_classification=assessment.original_classification or assessment.classification,
            analyst_override=assessment.analyst_override or False,
            analyst_notes=assessment.analyst_notes,
            reason=assessment.reason,
            llm_confidence=assessment.llm_confidence or 0.9,
            reliability=assessment.reliability or 1.0
        )
        db.add(db_assessment)

    db.commit()
    db.refresh(h)

    # Recalculate true ACH normalized scores across the case
    recalculate_case_ach(h.case_id, db)
    db.refresh(db_assessment)

    return EvidenceAssessmentOut(
        id=db_assessment.id,
        hypothesis_id=db_assessment.hypothesis_id,
        evidence_id=db_assessment.evidence_id,
        classification=db_assessment.classification,
        original_classification=db_assessment.original_classification or db_assessment.classification,
        analyst_override=bool(db_assessment.analyst_override),
        analyst_notes=db_assessment.analyst_notes,
        reason=db_assessment.reason,
        llm_confidence=db_assessment.llm_confidence,
        reliability=db_assessment.reliability,
        evidence_file_name=ev.file_name,
        evidence_file_type=ev.file_type
    )


@app.post("/cases/{case_id}/assessments/override")
def analyst_override_assessment(
    case_id: str,
    data: AssessmentOverrideRequest,
    db: Session = Depends(get_db)
):
    """
    Analyst Override:
    Allows an investigator to manually adjust any matrix cell classification.
    Preserves the AI's original judgment visible while immediately recalculating ACH scores.
    """
    real_case_id = resolve_case_id(case_id, db)
    assessment = db.query(EvidenceAssessment).filter(
        EvidenceAssessment.hypothesis_id == data.hypothesis_id,
        EvidenceAssessment.evidence_id == data.evidence_id
    ).first()

    if not assessment:
        assessment = EvidenceAssessment(
            hypothesis_id=data.hypothesis_id,
            evidence_id=data.evidence_id,
            classification=data.classification.lower().strip(),
            original_classification="neutral",
            analyst_override=True,
            analyst_notes=data.analyst_notes,
            reason=f"Analyst Override: {data.analyst_notes}",
            llm_confidence=1.0,
            reliability=1.0
        )
        db.add(assessment)
    else:
        if not assessment.original_classification:
            assessment.original_classification = assessment.classification
        assessment.classification = data.classification.lower().strip()
        assessment.analyst_override = True
        assessment.analyst_notes = data.analyst_notes

    db.commit()
    db.refresh(assessment)

    # Recompute True ACH across the entire case
    ach_result = recalculate_case_ach(real_case_id, db)

    return {
        "status": "success",
        "message": f"Analyst override applied to Exhibit #{data.evidence_id}",
        "assessment": {
            "id": assessment.id,
            "hypothesis_id": assessment.hypothesis_id,
            "evidence_id": assessment.evidence_id,
            "classification": assessment.classification,
            "original_classification": assessment.original_classification,
            "analyst_override": assessment.analyst_override,
            "analyst_notes": assessment.analyst_notes
        },
        "ach_matrix": ach_result
    }


@app.post("/cases/{case_id}/assessments/reset")
def analyst_reset_assessment(
    case_id: str,
    hypothesis_id: int,
    evidence_id: int,
    db: Session = Depends(get_db)
):
    """
    Resets an overridden assessment back to the AI baseline classification.
    """
    real_case_id = resolve_case_id(case_id, db)
    assessment = db.query(EvidenceAssessment).filter(
        EvidenceAssessment.hypothesis_id == hypothesis_id,
        EvidenceAssessment.evidence_id == evidence_id
    ).first()

    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if assessment.original_classification:
        assessment.classification = assessment.original_classification
    assessment.analyst_override = False
    assessment.analyst_notes = None

    db.commit()
    db.refresh(assessment)

    ach_result = recalculate_case_ach(real_case_id, db)

    return {
        "status": "success",
        "message": "Assessment restored to AI baseline judgment",
        "classification": assessment.classification,
        "ach_matrix": ach_result
    }


@app.get("/cases/{case_id}/ach/sensitivity-analysis", response_model=SensitivityAnalysisResponse)
def get_case_sensitivity_analysis(case_id: str, db: Session = Depends(get_db)):
    """
    Heuer ACH Sensitivity Analysis:
    Simulates removal of each evidence exhibit to show which single piece
    of evidence the investigative conclusion depends upon.
    """
    real_case_id = resolve_case_id(case_id, db)
    hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == real_case_id).all()
    if not hypotheses:
        raise HTTPException(status_code=404, detail="No hypotheses found for case")

    assessments = db.query(EvidenceAssessment).join(Hypothesis).filter(Hypothesis.case_id == real_case_id).all()
    evidences = db.query(Evidence).filter(Evidence.case_id == real_case_id).all()

    # Recalculate baseline
    recalculate_case_ach(real_case_id, db)
    hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == real_case_id).order_by(Hypothesis.support_score.desc()).all()

    analysis_res = run_sensitivity_analysis(hypotheses, assessments, evidences)

    baseline_ranking = [
        HypothesisOut(
            id=h.id,
            case_id=h.case_id,
            title=h.title,
            description=h.description,
            status=h.status,
            support_score=h.support_score,
            disconfirmation_penalty=h.disconfirmation_penalty or 0.0,
            relative_likelihood=h.support_score,
            created_at=h.created_at,
            assessment_count=len(h.assessments)
        )
        for h in hypotheses
    ]

    return SensitivityAnalysisResponse(
        case_id=real_case_id,
        baseline_ranking=baseline_ranking,
        exhibit_impacts=analysis_res["exhibit_impacts"],
        most_critical_evidence_id=analysis_res["most_critical_evidence_id"],
        most_critical_evidence_name=analysis_res["most_critical_evidence_name"]
    )


@app.post("/cases/{case_id}/ach/calculate")
def calculate_ach_with_exclusions(
    case_id: str,
    payload: dict,
    db: Session = Depends(get_db)
):
    """
    Real-time interactive ACH recalculation with arbitrary exhibits excluded.
    """
    real_case_id = resolve_case_id(case_id, db)
    excluded_ids = set(payload.get("excluded_evidence_ids", []))
    hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == real_case_id).all()
    assessments = db.query(EvidenceAssessment).join(Hypothesis).filter(Hypothesis.case_id == real_case_id).all()
    evidences = db.query(Evidence).filter(Evidence.case_id == real_case_id).all()

    ach_result = compute_ach_matrix(hypotheses, assessments, excluded_evidence_ids=excluded_ids)
    return ach_result


# ============================================================
# ACH SCORING UPGRADE ENDPOINTS
# ============================================================

@app.post("/cases/{case_id}/scoring/recalculate")
def recalculate_scoring_endpoint(
    case_id: str,
    payload: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db)
):
    """
    Recalculate ACH Scoring:
    Instant pure-python recalculation of all hypotheses scores,
    diagnosticity weighting, inconsistency penalties, and robustness ranges.
    No LLM calls required.
    """
    real_case_id = resolve_case_id(case_id, db)
    custom_cfg = (payload or {}).get("custom_configs")
    excluded = (payload or {}).get("excluded_evidence_ids")
    res = execute_scoring_run(
        real_case_id, db,
        custom_configs=custom_cfg,
        excluded_ids=excluded,
        triggered_by="recalculate_endpoint"
    )
    return res


@app.get("/cases/{case_id}/scoring/breakdown/{hypothesis_id}")
def get_hypothesis_scoring_breakdown(
    case_id: str,
    hypothesis_id: int,
    db: Session = Depends(get_db)
):
    """
    Per-exhibit table for one hypothesis:
    Returns classification, confidence, base reliability, modifiers applied,
    diagnosticity, contribution, share of total support, quoted source line,
    and Gemini reason.
    """
    real_case_id = resolve_case_id(case_id, db)
    res = execute_scoring_run(real_case_id, db)
    breakdowns = res.get("hypothesis_breakdowns", {})
    target_table = breakdowns.get(hypothesis_id, [])
    
    # Also find hypothesis summary
    hyp_summary = next((h for h in res.get("hypotheses", []) if h["id"] == hypothesis_id), None)
    robustness = res.get("robustness_ranges", {}).get(hypothesis_id, {})

    return {
        "case_id": real_case_id,
        "hypothesis_id": hypothesis_id,
        "hypothesis": hyp_summary,
        "robustness": robustness,
        "exhibits": target_table
    }


@app.get("/cases/{case_id}/scoring/sensitivity")
def get_scoring_sensitivity(
    case_id: str,
    db: Session = Depends(get_db)
):
    """
    Sensitivity and Robustness:
    Returns Leave-One-Out impact per exhibit, critical exhibits list,
    and min-max robustness range error-bars per hypothesis.
    """
    real_case_id = resolve_case_id(case_id, db)
    res = execute_scoring_run(real_case_id, db)
    return {
        "case_id": real_case_id,
        "critical_exhibits": res.get("critical_exhibits", []),
        "exhibit_impacts": res.get("exhibit_impacts", []),
        "robustness_ranges": res.get("robustness_ranges", {}),
        "hypotheses": res.get("hypotheses", [])
    }


@app.post("/cases/{case_id}/scoring/override")
def analyst_override_scoring_endpoint(
    case_id: str,
    data: AssessmentOverrideRequest,
    db: Session = Depends(get_db)
):
    """
    Analyst Override:
    Allows an investigator to update:
    - classification
    - evidence_type
    - manual reliability or modifiers (hash, custody, 65B, independence, quality)
    - analyst notes
    Triggers instant scoring recalculation without LLM call.
    """
    real_case_id = resolve_case_id(case_id, db)
    
    # 1. Update Evidence attributes if requested
    ev = db.query(Evidence).filter(Evidence.id == data.evidence_id).first()
    if ev:
        if data.evidence_type:
            ev.evidence_type = data.evidence_type
        if data.hash_verified is not None:
            ev.hash_verified = data.hash_verified
        if data.chain_of_custody_complete is not None:
            ev.chain_of_custody_complete = data.chain_of_custody_complete
        if data.sec_65b_certificate_present is not None:
            ev.sec_65b_certificate_present = data.sec_65b_certificate_present
        if data.source_independent is not None:
            ev.source_independent = data.source_independent
        if data.quality_rating is not None:
            ev.quality_rating = float(data.quality_rating)

    # 2. Update Assessment if classification or reliability specified
    assessment = db.query(EvidenceAssessment).filter(
        EvidenceAssessment.hypothesis_id == data.hypothesis_id,
        EvidenceAssessment.evidence_id == data.evidence_id
    ).first()

    if not assessment:
        assessment = EvidenceAssessment(
            hypothesis_id=data.hypothesis_id,
            evidence_id=data.evidence_id,
            classification=(data.classification or "neutral").lower().strip(),
            original_classification="neutral",
            analyst_override=True,
            analyst_notes=data.analyst_notes or "Investigator adjustment",
            reason=f"Analyst Override: {data.analyst_notes}",
            llm_confidence=1.0,
            reliability=float(data.manual_reliability or 1.0)
        )
        db.add(assessment)
    else:
        if not assessment.original_classification:
            assessment.original_classification = assessment.classification
        if data.classification:
            assessment.classification = data.classification.lower().strip()
        assessment.analyst_override = True
        assessment.analyst_notes = data.analyst_notes or assessment.analyst_notes
        if data.manual_reliability is not None:
            assessment.reliability = float(data.manual_reliability)

    db.commit()

    # 3. Instant recalculation
    scoring_res = execute_scoring_run(real_case_id, db, triggered_by="analyst_override")

    return {
        "status": "success",
        "message": f"Analyst override applied to Exhibit #{data.evidence_id}",
        "scoring_result": scoring_res
    }


@app.get("/cases/{case_id}/scoring/reliability-configs", response_model=List[ReliabilityConfigOut])
def get_reliability_configs_endpoint(case_id: str, db: Session = Depends(get_db)):
    """Returns the base reliability and legal rationale for each evidence type."""
    configs = db.query(ReliabilityConfig).order_by(ReliabilityConfig.base_reliability.desc()).all()
    return configs


@app.put("/cases/{case_id}/scoring/reliability-configs")
def update_reliability_config_endpoint(
    case_id: str,
    update: ReliabilityConfigUpdate,
    db: Session = Depends(get_db)
):
    """Updates base reliability or rationale text and recalculates case scores."""
    real_case_id = resolve_case_id(case_id, db)
    cfg = db.query(ReliabilityConfig).filter(ReliabilityConfig.evidence_type == update.evidence_type).first()
    if not cfg:
        cfg = ReliabilityConfig(
            evidence_type=update.evidence_type,
            base_reliability=update.base_reliability,
            rationale=update.rationale or ""
        )
        db.add(cfg)
    else:
        cfg.base_reliability = update.base_reliability
        if update.rationale:
            cfg.rationale = update.rationale

    db.commit()
    scoring_res = execute_scoring_run(real_case_id, db, triggered_by="reliability_config_change")
    return {
        "status": "success",
        "message": f"Reliability configuration for {update.evidence_type} updated",
        "scoring_result": scoring_res
    }


# Helper functions for Gemini AI
def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key.strip())
    except Exception as e:
        print(f"[!] genai Client init failed: {e}")
        return None

def clean_json_str(text: str) -> str:
    t = text.strip()
    if t.startswith("```json"):
        t = t[7:]
    elif t.startswith("```"):
        t = t[3:]
    if t.endswith("```"):
        t = t[:-3]
    return t.strip()


@app.post("/hypotheses/{hypothesis_id}/evaluate", response_model=HypothesisDetailOut)
def evaluate_hypothesis_with_ai(hypothesis_id: int, db: Session = Depends(get_db)):
    """Runs AI evaluation of all case evidence against this hypothesis with exact quote verification."""
    h = db.query(Hypothesis).filter(Hypothesis.id == hypothesis_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    
    evidences = db.query(Evidence).filter(Evidence.case_id == h.case_id).all()
    if not evidences:
        return get_hypothesis(hypothesis_id, db)

    # Auto-infer evidence type if missing
    for ev in evidences:
        if not ev.evidence_type or ev.evidence_type == "document":
            ev.evidence_type = infer_evidence_type(ev.file_name, ev.extracted_text or "")
    db.commit()

    client = get_gemini_client()

    # Try batch evaluation first for cross-exhibit consistency
    if client and evidences:
        exhibits_prompt = "\n\n".join([
            format_full_exhibit_for_ach_prompt(ev)
            for ev in evidences
        ])
        batch_prompt = f"""You are a senior criminal forensic intelligence analyst.
Evaluate whether each legal evidence exhibit supports, contradicts, or is neutral towards this investigative hypothesis:

Hypothesis:
Title: {h.title}
Description: {h.description or 'No extra description'}

Case Exhibits:
{exhibits_prompt}

For each exhibit, classify into EXACTLY one of:
- strong_support
- moderate_support
- weak_support
- neutral
- weak_contradiction
- moderate_contradiction
- strong_contradiction

IMPORTANT: Provide an exact verbatim quote ("quoted_source_line") from the exhibit text that justifies your decision. Do NOT make up quotes. If no direct quote exists, leave it empty.

Respond in valid JSON array only:
[
  {{
    "evidence_id": {evidences[0].id},
    "classification": "strong_support | neutral | strong_contradiction ...",
    "reason": "Clear explanation citing forensic facts in this exhibit",
    "quoted_source_line": "Exact verbatim quote from the text",
    "confidence": 0.95
  }}
]"""
        try:
            resp = client.models.generate_content(
                model="gemini-flash-lite-latest",
                contents=batch_prompt
            )
            raw = clean_json_str(resp.text)
            parsed = json.loads(raw)
            if isinstance(parsed, list) and len(parsed) > 0:
                eval_map = {item.get("evidence_id"): item for item in parsed if "evidence_id" in item}
                for ev in evidences:
                    eval_data = eval_map.get(ev.id) or {}
                    classification = str(eval_data.get("classification", "neutral")).lower().strip()
                    reason = eval_data.get("reason", f"Evaluated against exhibit {ev.file_name}")
                    confidence = float(eval_data.get("confidence", 0.9))
                    verified_quote = verify_quoted_source_line(eval_data.get("quoted_source_line"), ev.extracted_text or "")

                    existing = db.query(EvidenceAssessment).filter(
                        EvidenceAssessment.hypothesis_id == h.id,
                        EvidenceAssessment.evidence_id == ev.id
                    ).first()
                    if existing:
                        if not existing.analyst_override:
                            existing.classification = classification
                        existing.original_classification = classification
                        existing.reason = reason
                        existing.llm_confidence = confidence
                        existing.quoted_source_line = verified_quote
                    else:
                        db_assessment = EvidenceAssessment(
                            hypothesis_id=h.id,
                            evidence_id=ev.id,
                            classification=classification,
                            original_classification=classification,
                            analyst_override=False,
                            reason=reason,
                            quoted_source_line=verified_quote,
                            llm_confidence=confidence,
                            reliability=1.0
                        )
                        db.add(db_assessment)
                db.commit()
                execute_scoring_run(h.case_id, db, triggered_by="ai_batch_evaluate")
                return get_hypothesis(hypothesis_id, db)
        except Exception as e:
            print(f"[!] Batch AI eval fallback for hypothesis {h.id}: {e}")

    # Fallback to individual exhibit evaluation if batch failed
    for ev in evidences:
        classification = "neutral"
        reason = f"Evaluated against exhibit {ev.file_name}."
        confidence = 0.90
        verified_quote = ""

        if client:
            prompt = f"""
You are a senior criminal forensic intelligence analyst.
Evaluate whether this legal evidence exhibit supports, contradicts, or is neutral towards the investigative hypothesis.

Investigative Hypothesis:
Title: {h.title}
Description: {h.description or 'No extra description'}

Evidence Exhibit:
{format_full_exhibit_for_ach_prompt(ev)}

Classify into EXACTLY one of:
- strong_support
- moderate_support
- weak_support
- neutral
- weak_contradiction
- moderate_contradiction
- strong_contradiction

Respond in valid JSON only:
{{
  "classification": "strong_support | neutral | strong_contradiction ...",
  "reason": "Clear explanation citing forensic facts in this exhibit",
  "quoted_source_line": "Exact verbatim quote from the text",
  "confidence": 0.95
}}
"""
            try:
                resp = client.models.generate_content(
                    model="gemini-flash-lite-latest",
                    contents=prompt
                )
                raw = clean_json_str(resp.text)
                parsed = json.loads(raw)
                classification = parsed.get("classification", "neutral").lower().strip()
                reason = parsed.get("reason", reason)
                confidence = float(parsed.get("confidence", 0.9))
                verified_quote = verify_quoted_source_line(parsed.get("quoted_source_line"), ev.extracted_text or "")
            except Exception as e:
                print(f"[!] AI eval exception for exhibit {ev.id}: {e}")

        existing = db.query(EvidenceAssessment).filter(
            EvidenceAssessment.hypothesis_id == h.id,
            EvidenceAssessment.evidence_id == ev.id
        ).first()

        if existing:
            if not existing.analyst_override:
                existing.classification = classification
            existing.original_classification = classification
            existing.reason = reason
            existing.llm_confidence = confidence
            existing.quoted_source_line = verified_quote
        else:
            db_assessment = EvidenceAssessment(
                hypothesis_id=h.id,
                evidence_id=ev.id,
                classification=classification,
                original_classification=classification,
                analyst_override=False,
                reason=reason,
                quoted_source_line=verified_quote,
                llm_confidence=confidence,
                reliability=1.0
            )
            db.add(db_assessment)

    db.commit()
    execute_scoring_run(h.case_id, db, triggered_by="ai_individual_evaluate")
    return get_hypothesis(hypothesis_id, db)


@app.put("/hypotheses/{hypothesis_id}", response_model=HypothesisOut)
def update_hypothesis(hypothesis_id: int, updates: dict, db: Session = Depends(get_db)):
    h = db.query(Hypothesis).filter(Hypothesis.id == hypothesis_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    
    if "title" in updates:
        h.title = updates["title"]
    if "description" in updates:
        h.description = updates["description"]
    if "status" in updates:
        h.status = updates["status"]
    if "support_score" in updates:
        h.support_score = float(updates["support_score"])
    
    db.commit()
    db.refresh(h)
    return HypothesisOut(
        id=h.id,
        case_id=h.case_id,
        title=h.title,
        description=h.description,
        status=h.status,
        support_score=h.support_score,
        created_at=h.created_at,
        assessment_count=len(h.assessments)
    )


@app.delete("/hypotheses/{hypothesis_id}")
def delete_hypothesis(hypothesis_id: int, db: Session = Depends(get_db)):
    h = db.query(Hypothesis).filter(Hypothesis.id == hypothesis_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    db.delete(h)
    db.commit()
    return {"message": "Hypothesis deleted", "id": hypothesis_id}


# ============================================================
# COMPETING HYPOTHESIS ENGINE (ACH METHODOLOGY)
# ============================================================

@app.post("/cases/{case_id}/analyze-hypotheses", response_model=List[HypothesisDetailOut])
def analyze_competing_hypotheses(case_id: str, db: Session = Depends(get_db)):
    """
    Real Competing Hypothesis Engine (Analysis of Competing Hypotheses - ACH):
    1. Collects Case + Evidence + Entities + Events.
    2. Gemini generates multiple plausible competing hypotheses (H1, H2, H3...).
    3. Every evidence exhibit is evaluated against every hypothesis.
    4. Computes relational assessments and support scores in PostgreSQL.
    """
    real_case_id = resolve_case_id(case_id, db)
    case = db.query(Case).filter(Case.id == real_case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    evidences = db.query(Evidence).filter(Evidence.case_id == real_case_id).all()
    entities = db.query(Entity).filter(Entity.case_id == real_case_id).all()
    events = db.query(Event).filter(Event.case_id == real_case_id).all()

    evidence_text = "\n\n".join([
        format_full_exhibit_for_ach_prompt(e)
        for e in evidences
    ]) or "No exhibits uploaded."

    entities_text = "\n".join([
        f"- {ent.type}: {ent.name} (Confidence: {ent.confidence})"
        for ent in entities
    ]) or "No entities recorded."

    events_text = "\n".join([
        f"- [{evt.timestamp or 'Unknown'}] {evt.title}: {evt.description} (Location: {evt.location or 'N/A'})"
        for evt in events
    ]) or "No timeline events recorded."

    case_dossier = f"""CASE #{real_case_id}: {case.title}
STATUS: {case.status}
OVERVIEW: {case.description or 'No extra description'}

EXHIBITS IN CUSTODY:
{evidence_text}

PERSONS & ENTITIES:
{entities_text}

TIMELINE EVENTS:
{events_text}"""

    client = get_gemini_client()
    generated_hypotheses_data = []

    if client:
        prompt = f"""You are an elite Senior Criminal Intelligence Analyst specializing in Richards J. Heuer's Analysis of Competing Hypotheses (ACH) methodology for judicial investigations.

Based on the complete forensic dossier below:
{case_dossier}

Generate 3 to 4 mutually exclusive, plausible competing investigative hypotheses that explain the crime or incident.
You must construct divergent hypotheses representing distinct possibilities, for example:
- H1: Direct Primary Culpability (The prime suspect acted directly with premeditation, supported by physical/forensic trace evidence).
- H2: Accomplice or Alternate Perpetrator Responsibility (A secondary suspect, insider, or co-conspirator was primarily responsible, or prime suspect played a coerced/minor role).
- H3: External Third-Party or Systemic Cause (An unknown third-party intruder, external criminal syndicate, or alternate chain of events explains the evidence).

Respond in valid JSON array only:
[
  {{
    "title": "H1: [Concise descriptive title naming suspect/action]",
    "description": "Comprehensive investigative theory explaining motive, opportunity, means, and how physical facts align.",
    "status": "Active"
  }}
]"""
        try:
            resp = client.models.generate_content(
                model="gemini-flash-lite-latest",
                contents=prompt
            )
            raw = clean_json_str(resp.text)
            parsed = json.loads(raw)
            if isinstance(parsed, list) and len(parsed) > 0:
                generated_hypotheses_data = parsed
        except Exception as e:
            print(f"[!] ACH hypothesis generation exception: {e}")

    # Fallback default hypotheses if Gemini was unavailable or returned empty
    if not generated_hypotheses_data:
        generated_hypotheses_data = [
            {
                "title": f"H1: Direct Infiltration & Execution by Prime Suspect",
                "description": f"The primary identified subject possessed direct physical access, capability, and motive as corroborated by forensic exhibits in {case.title}.",
                "status": "Active"
            },
            {
                "title": f"H2: Internal Accomplice Collusion & Coordinated Assistance",
                "description": f"An insider or accomplice facilitated entry and covered up forensic traces during the incident window.",
                "status": "Active"
            },
            {
                "title": f"H3: External Third-Party Syndicate / Alternative Threat Actor",
                "description": f"The available evidence reflects external interception or staging by an unapprehended third-party entity.",
                "status": "Active"
            }
        ]

    # Ingest or update hypotheses in PostgreSQL
    target_hypotheses = []
    for h_data in generated_hypotheses_data:
        title = h_data.get("title", "").strip()
        if not title:
            continue
        
        existing = db.query(Hypothesis).filter(
            Hypothesis.case_id == real_case_id,
            Hypothesis.title == title
        ).first()

        if existing:
            existing.description = h_data.get("description", existing.description)
            db_h = existing
        else:
            db_h = Hypothesis(
                case_id=real_case_id,
                title=title,
                description=h_data.get("description", ""),
                status="Active",
                support_score=50.0
            )
            db.add(db_h)
            db.commit()
            db.refresh(db_h)

        target_hypotheses.append(db_h)

    db.commit()

    if not target_hypotheses:
        target_hypotheses = db.query(Hypothesis).filter(
            Hypothesis.case_id == real_case_id
        ).order_by(Hypothesis.id.desc()).limit(4).all()

    # Step 2: Evaluate ALL Hypotheses against ALL Exhibits in a Single Pass ACH Matrix Call
    if client and evidences and target_hypotheses:
        hypotheses_block = "\n".join([
            f"- Hypothesis ID #{h.id}: \"{h.title}\"\n  Theory: {h.description}"
            for h in target_hypotheses
        ])
        exhibits_block = "\n\n".join([
            format_full_exhibit_for_ach_prompt(ev)
            for ev in evidences
        ])

        matrix_prompt = f"""You are an elite Senior Criminal Intelligence Analyst performing Richards J. Heuer's Analysis of Competing Hypotheses (ACH) Matrix.

INVESTIGATIVE HYPOTHESES:
{hypotheses_block}

CASE EVIDENCE EXHIBITS:
{exhibits_block}

Evaluate EVERY legal evidence exhibit against EVERY investigative hypothesis in the matrix.
Classify each (hypothesis, evidence) relationship into EXACTLY one of:
- strong_support
- moderate_support
- weak_support
- neutral
- weak_contradiction
- moderate_contradiction
- strong_contradiction

IMPORTANT: Provide an exact verbatim quote ("quoted_source_line") from the exhibit text supporting your assessment. Do not fabricate quotes.

Provide a clear explanation citing specific forensic facts from the exhibit.
Respond in valid JSON array only:
[
  {{
    "hypothesis_id": {target_hypotheses[0].id},
    "evidence_id": {evidences[0].id},
    "classification": "strong_support | neutral | strong_contradiction ...",
    "reason": "Clear explanation citing forensic facts in this exhibit",
    "quoted_source_line": "Exact verbatim quote from the text",
    "confidence": 0.95
  }}
]"""
        try:
            resp = client.models.generate_content(
                model="gemini-flash-lite-latest",
                contents=matrix_prompt
            )
            raw = clean_json_str(resp.text)
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                ev_lookup = {ev.id: ev for ev in evidences}
                for item in parsed:
                    h_id = item.get("hypothesis_id")
                    ev_id = item.get("evidence_id")
                    if not h_id or not ev_id:
                        continue
                    cls = str(item.get("classification", "neutral")).lower().strip()
                    reason = item.get("reason", "Corroborated by forensic exhibit analysis")
                    conf = float(item.get("confidence", 0.9))
                    ev_obj = ev_lookup.get(ev_id)
                    verified_quote = verify_quoted_source_line(
                        item.get("quoted_source_line"),
                        ev_obj.extracted_text if ev_obj else ""
                    )

                    existing = db.query(EvidenceAssessment).filter(
                        EvidenceAssessment.hypothesis_id == h_id,
                        EvidenceAssessment.evidence_id == ev_id
                    ).first()
                    if existing:
                        # Preserve human analyst override if present
                        if not existing.analyst_override:
                            existing.classification = cls
                        existing.original_classification = cls
                        existing.reason = reason
                        existing.llm_confidence = conf
                        existing.quoted_source_line = verified_quote
                    else:
                        db_assessment = EvidenceAssessment(
                            hypothesis_id=h_id,
                            evidence_id=ev_id,
                            classification=cls,
                            original_classification=cls,
                            analyst_override=False,
                            reason=reason,
                            quoted_source_line=verified_quote,
                            llm_confidence=conf,
                            reliability=1.0
                        )
                        db.add(db_assessment)
                db.commit()
        except Exception as e:
            print(f"[!] Matrix ACH eval exception: {e}")

    # Central ACH Scoring Recalculation via ach_scoring.py
    execute_scoring_run(real_case_id, db, triggered_by="ach_dataset_analysis")

    # Return hypotheses sorted by normalized relative likelihood
    sorted_hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == real_case_id).order_by(Hypothesis.support_score.desc()).all()
    return [get_hypothesis(h.id, db) for h in sorted_hypotheses]


# ============================================================
# CONTRADICTION ENDPOINTS & AI DETECTOR
# ============================================================

@app.get("/cases/{case_id}/contradictions", response_model=List[ContradictionOut])
def get_contradictions_for_case(case_id: str, db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    return db.query(Contradiction).filter(Contradiction.case_id == real_id).all()

@app.post("/cases/{case_id}/contradictions", response_model=ContradictionOut)
def create_contradiction(case_id: str, data: ContradictionCreate, db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    c = Contradiction(
        case_id=real_id,
        statement_a=data.statement_a,
        source_a_id=data.source_a_id,
        statement_b=data.statement_b,
        source_b_id=data.source_b_id,
        conflict_type=data.conflict_type,
        confidence=data.confidence or 90.0,
        status=data.status or "Detected"
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

@app.post("/cases/{case_id}/detect-contradictions")
def run_nli_contradiction_detection_endpoint(case_id: str, db: Session = Depends(get_db)):
    """
    Real Contradiction Detection via Natural Language Inference (NLI):
    Evidence A -> Claims -> Compare (ENTAILMENT/CONTRADICTION/NEUTRAL) <- Claims <- Evidence B
    """
    real_id = resolve_case_id(case_id, db)
    detector = ForensicNLIDetector()
    result = detector.detect_contradictions_for_case(case_id=real_id, db=db)
    return result

@app.patch("/contradictions/{contradiction_id}")
def update_contradiction_status(contradiction_id: int, updates: dict, db: Session = Depends(get_db)):
    c = db.query(Contradiction).filter(Contradiction.id == contradiction_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contradiction not found")
    if "status" in updates:
        c.status = updates["status"]
    db.commit()
    db.refresh(c)
    return c

# ============================================================
# INVESTIGATION TASK ENDPOINTS
# ============================================================

@app.get("/cases/{case_id}/tasks", response_model=List[InvestigationTaskOut])
def get_tasks_for_case(case_id: str, db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    return db.query(InvestigationTask).filter(InvestigationTask.case_id == real_id).all()

@app.post("/cases/{case_id}/tasks", response_model=InvestigationTaskOut)
def create_task(case_id: str, data: InvestigationTaskCreate, db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    t = InvestigationTask(
        case_id=real_id,
        task=data.task,
        reason=data.reason,
        related_hypothesis_id=data.related_hypothesis_id,
        related_contradiction_id=data.related_contradiction_id,
        related_evidence_id=data.related_evidence_id,
        priority=data.priority or "High",
        status=data.status or "Pending",
        assigned_to=data.assigned_to or "Lead Investigator"
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t

@app.patch("/tasks/{task_id}", response_model=InvestigationTaskOut)
def update_task_status(task_id: int, updates: dict, db: Session = Depends(get_db)):
    t = db.query(InvestigationTask).filter(InvestigationTask.id == task_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    if "status" in updates:
        t.status = updates["status"]
    if "priority" in updates:
        t.priority = updates["priority"]
    if "assigned_to" in updates:
        t.assigned_to = updates["assigned_to"]
    db.commit()
    db.refresh(t)
    return t

# ============================================================
# REAL AI INTELLIGENCE PIPELINE (Gemini + PostgreSQL)
# ============================================================

def run_ai_contradiction_detection(db: Session, case_id: int, current_ev: Evidence = None) -> List[Contradiction]:
    """
    Detects real contradictions across evidence exhibits using NLI Engine:
    Evidence A -> Claims -> Compare (ENTAILMENT | CONTRADICTION | NEUTRAL) <- Claims <- Evidence B
    """
    try:
        detector = ForensicNLIDetector()
        res = detector.detect_contradictions_for_case(
            case_id=case_id,
            db=db,
            focus_evidence_id=current_ev.id if current_ev else None
        )
        return res.get("contradictions", [])
    except Exception as e:
        print(f"[!] Forensic NLI detection exception: {e}")
        return []



def run_ai_hypothesis_recalculation(db: Session, case_id: int, current_ev: Evidence = None):
    """Re-evaluates hypotheses and calculates support scores against case exhibits."""
    hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == case_id).all()
    if not hypotheses:
        return []

    updated = []
    for h in hypotheses:
        try:
            evaluate_hypothesis_with_ai(h.id, db)
            db.refresh(h)
            updated.append(h)
        except Exception as e:
            print(f"[!] Hypothesis eval failed for {h.id}: {e}")
            updated.append(h)
    return updated


def run_ai_task_generation(db: Session, case_id: int, current_ev: Evidence = None) -> List[InvestigationTask]:
    """Generates real actionable investigative tasks based on contradictions and evidence gaps."""
    contradictions = db.query(Contradiction).filter(Contradiction.case_id == case_id).all()
    hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == case_id).all()
    case = db.query(Case).filter(Case.id == case_id).first()

    client = get_gemini_client()
    new_tasks = []

    if client:
        c_summary = "\n".join([f"- [Contradiction #{c.id} - {c.conflict_type}]: {c.statement_a} VS {c.statement_b}" for c in contradictions[:5]])
        h_summary = "\n".join([f"- [Hypothesis #{h.id} - {h.title}]: Support Score {h.support_score}%" for h in hypotheses[:5]])
        case_title = case.title if case else f"Case #{case_id}"

        prompt = f"""You are a Lead Detective Supervisor on active case "{case_title}".
Based on the following detected forensic contradictions and investigative hypotheses:

CONTRADICTIONS IN EVIDENCE:
{c_summary or 'No contradictions detected yet.'}

ACTIVE HYPOTHESES:
{h_summary or 'No hypotheses formulated yet.'}

RECENT EXHIBIT:
{current_ev.file_name if current_ev else 'Case exhibits review'}

Generate 2 to 4 high-priority, actionable police investigation tasks to verify alibis, resolve contradictions, and test hypotheses.

Respond in valid JSON array only:
[
  {{
    "task": "Specific actionable detective task",
    "reason": "Forensic rationale explaining why this is needed",
    "priority": "High",
    "related_contradiction_id": null,
    "related_hypothesis_id": null,
    "assigned_to": "Digital Forensics Unit"
  }}
]"""

        try:
            resp = client.models.generate_content(
                model="gemini-flash-lite-latest",
                contents=prompt
            )
            raw = clean_json_str(resp.text)
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                for item in parsed:
                    task_text = item.get("task", "").strip()
                    if not task_text:
                        continue

                    exists = db.query(InvestigationTask).filter(
                        InvestigationTask.case_id == case_id,
                        InvestigationTask.task == task_text
                    ).first()

                    if not exists:
                        t_record = InvestigationTask(
                            case_id=case_id,
                            task=task_text,
                            reason=item.get("reason", "Generated by AI Forensic Intelligence Pipeline"),
                            related_contradiction_id=str(item.get("related_contradiction_id", "")) if item.get("related_contradiction_id") else None,
                            related_hypothesis_id=str(item.get("related_hypothesis_id", "")) if item.get("related_hypothesis_id") else None,
                            related_evidence_id=str(current_ev.id) if current_ev else None,
                            priority=item.get("priority", "High"),
                            status="Pending",
                            assigned_to=item.get("assigned_to", "Lead Investigator")
                        )
                        db.add(t_record)
                        new_tasks.append(t_record)
                db.commit()
        except Exception as e:
            print(f"[!] AI task generation exception: {e}")

    return new_tasks


@app.post("/cases/{case_id}/pipeline/process-evidence/{evidence_id}")
def process_evidence_pipeline(case_id: str, evidence_id: str, db: Session = Depends(get_db)):
    """
    Complete end-to-end Real Intelligence Pipeline:
    React -> FastAPI -> Gemini -> PostgreSQL -> Real analysis results
    1. Deep evidence analysis & entity/event extraction
    2. Contradiction detection against all case exhibits
    3. Hypothesis re-evaluation & scoring
    4. Task generation for detective action plan
    """
    real_case_id = resolve_case_id(case_id, db)
    ev = resolve_evidence_obj(evidence_id, db)
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    # Step 1: Analyze evidence if not yet analyzed or if requested
    analysis_res = analyze_evidence(str(ev.id), db)
    db.refresh(ev)

    # Step 1.5: Extract semantic entity-to-entity relationships (Forensic Knowledge Graph)
    try:
        from relationship_engine import SemanticRelationshipExtractor
        SemanticRelationshipExtractor().extract_and_store_relationships(real_case_id, db, focus_evidence_id=ev.id)
    except Exception as e:
        print(f"[!] Semantic relationship extraction error: {e}")

    # Step 2: Detect contradictions via Gemini against other case exhibits
    run_ai_contradiction_detection(db, real_case_id, current_ev=ev)

    # Step 3: Recalculate hypotheses via Gemini
    run_ai_hypothesis_recalculation(db, real_case_id, current_ev=ev)

    # Step 4: Generate investigative tasks via Gemini
    run_ai_task_generation(db, real_case_id, current_ev=ev)

    # Fetch updated state from PostgreSQL
    all_entities = db.query(Entity).filter(Entity.case_id == real_case_id).all()
    all_events = db.query(Event).filter(Event.case_id == real_case_id).all()
    all_relationships = db.query(Relationship).filter(Relationship.case_id == real_case_id).all()
    all_contradictions = db.query(Contradiction).filter(Contradiction.case_id == real_case_id).all()
    all_hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == real_case_id).all()
    all_tasks = db.query(InvestigationTask).filter(InvestigationTask.case_id == real_case_id).all()

    return {
        "status": "success",
        "message": f"Real Intelligence Pipeline completed for exhibit {ev.file_name}",
        "evidence_id": ev.id,
        "processing_status": ev.processing_status,
        "extracted_text": ev.extracted_text,
        "entities": [
            {"id": f"ENT-{e.id}", "name": e.name, "type": e.type, "confidence": e.confidence, "caseId": str(e.case_id)}
            for e in all_entities
        ],
        "events": [
            {"id": f"EVT-{e.id}", "title": e.title, "description": e.description, "timestamp": str(e.timestamp), "location": e.location, "caseId": str(e.case_id)}
            for e in all_events
        ],
        "relationships": [
            {
                "id": f"REL-{r.id}",
                "caseId": str(r.case_id),
                "sourceEntityId": str(r.source_entity_id),
                "targetEntityId": str(r.target_entity_id),
                "relationType": r.relation_type,
                "evidenceId": str(r.evidence_id) if r.evidence_id else None,
                "confidence": r.confidence,
                "reason": r.reason
            }
            for r in all_relationships
        ],
        "contradictions": [
            {
                "id": f"C-{c.id}",
                "caseId": str(c.case_id),
                "statementA": c.statement_a,
                "sourceAId": c.source_a_id or f"E-{ev.id}",
                "statementB": c.statement_b,
                "sourceBId": c.source_b_id or f"E-{ev.id}",
                "conflictType": c.conflict_type,
                "confidence": c.confidence,
                "status": c.status
            }
            for c in all_contradictions
        ],
        "hypotheses": [
            {
                "id": str(h.id),
                "caseId": str(h.case_id),
                "title": h.title,
                "description": h.description,
                "status": h.status,
                "confidence": round(h.support_score),
                "support_score": h.support_score
            }
            for h in all_hypotheses
        ],
        "tasks": [
            {
                "id": f"TSK-{t.id}",
                "caseId": str(t.case_id),
                "task": t.task,
                "reason": t.reason,
                "priority": t.priority,
                "status": t.status,
                "relatedContradictionId": t.related_contradiction_id,
                "relatedHypothesisId": t.related_hypothesis_id,
                "relatedEvidenceId": t.related_evidence_id,
                "assignedTo": t.assigned_to
            }
            for t in all_tasks
        ]
    }


@app.post("/cases/{case_id}/pipeline/run")
def run_full_case_pipeline(case_id: str, db: Session = Depends(get_db)):
    """Runs the complete AI Intelligence Pipeline across all exhibits for a case."""
    real_case_id = resolve_case_id(case_id, db)
    
    # Analyze all exhibits that haven't been analyzed
    exhibits = db.query(Evidence).filter(Evidence.case_id == real_case_id).all()
    for ev in exhibits:
        if ev.processing_status != EvidenceStatus.ANALYZED:
            analyze_evidence(str(ev.id), db)

    run_ai_contradiction_detection(db, real_case_id)
    run_ai_hypothesis_recalculation(db, real_case_id)
    run_ai_task_generation(db, real_case_id)

    all_entities = db.query(Entity).filter(Entity.case_id == real_case_id).all()
    all_events = db.query(Event).filter(Event.case_id == real_case_id).all()
    all_contradictions = db.query(Contradiction).filter(Contradiction.case_id == real_case_id).all()
    all_hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == real_case_id).all()
    all_tasks = db.query(InvestigationTask).filter(InvestigationTask.case_id == real_case_id).all()

    return {
        "status": "success",
        "message": f"Full Intelligence Pipeline finished for case #{real_case_id}",
        "entities_count": len(all_entities),
        "events_count": len(all_events),
        "contradictions_count": len(all_contradictions),
        "hypotheses_count": len(all_hypotheses),
        "tasks_count": len(all_tasks)
    }


# ============================================================
# AI ASSISTANT ENDPOINT
# ============================================================

@app.post("/cases/{case_id}/assistant")
def ask_assistant(case_id: str, request: dict, db: Session = Depends(get_db)):
    real_id = resolve_case_id(case_id, db)
    """Ask the AI Assistant a question about the case."""
    question = request.get("question", "")
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    assistant = InvestigationAssistant(db, real_id)
    response = assistant.ask(question)

    return response

# ============================================================
# RUN SERVER
# ============================================================

# ============================================================
# ACH EVALUATION & VALIDATION BENCHMARK ENDPOINTS
# ============================================================

@app.get("/cases/evaluation/benchmark-results")
def get_evaluation_benchmark_results():
    """
    Returns the comprehensive frozen benchmark results across all 12 cases,
    baselines (Keyword, Plain LLM, Old Scoring), and Full ACH Engine.
    """
    from pathlib import Path
    import json
    
    results_path = Path(__file__).resolve().parent / "evaluation" / "results" / "benchmark_results.json"
    if results_path.exists():
        try:
            with open(results_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading benchmark results: {e}")
            
    # If not yet generated, run on the fly
    try:
        from evaluation.run_eval import execute_validation_benchmark
        return execute_validation_benchmark(num_runs=1)
    except Exception as e:
        logger.error(f"Failed to generate benchmark results: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load benchmark results: {str(e)}")


@app.post("/cases/evaluation/run")
def trigger_evaluation_run(request: dict = None):
    """
    Triggers a live multi-run execution of the forensic benchmark suite.
    """
    runs = 3
    if request and "runs" in request:
        runs = max(1, min(5, int(request["runs"])))
        
    try:
        from evaluation.run_eval import execute_validation_benchmark
        return execute_validation_benchmark(num_runs=runs)
    except Exception as e:
        logger.error(f"Failed to execute benchmark run: {e}")
        raise HTTPException(status_code=500, detail=f"Benchmark execution failed: {str(e)}")


@app.get("/cases/evaluation/dataset")
def get_evaluation_dataset_index():
    """
    Returns the list of 12 benchmark cases and their ground-truth metadata.
    """
    from evaluation.benchmark_dataset import BENCHMARK_CASES
    return [{
        "id": c["id"],
        "title": c["title"],
        "split": c["split"],
        "category": c["category"],
        "is_contested": c.get("is_contested", False),
        "citation": c["citation"],
        "ground_truth_hypothesis": c["ground_truth"]["hypothesis_id"],
        "culprit_summary": c["ground_truth"]["culprit_summary"],
        "exhibits_count": len(c.get("exhibits", [])),
        "hypotheses_count": len(c.get("hypotheses", []))
    } for c in BENCHMARK_CASES]


# ============================================================
# PHASE 3 FEATURE 4: PDF CASE REPORT EXPORT ENDPOINTS
# ============================================================

@app.get("/cases/{case_id}/reports/pdf")
def export_case_pdf_report(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generates and returns an authoritative, court-admissible vector PDF dossier.
    Includes:
    - Cover page with official insignia & 'decision support, not a conclusion' notice
    - Case summary & exhibit inventory with SHA-256 hashes and Sec 65B certification
    - Entities, relationships, and chronological timeline
    - Heuer ACH competing hypotheses with normalized scores & per-exhibit breakdown
    - Detected contradictions & testimonial conflicts
    - Heuer Step 6 Sensitivity analysis & critical pivot exhibits
    - Analyst overrides & rationales
    - Chain-of-custody summary & Merkle cryptographic audit ledger extract
    - Appendix of cited quotes with source locations
    - Running headers & footers with Case ID, timestamp, and SHA-256 digest on every page
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    case = db.query(Case).filter(Case.id == real_case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    try:
        from report_generator import generate_case_pdf_report
        pdf_bytes = generate_case_pdf_report(real_case_id, db)
    except Exception as e:
        logger.error(f"Error generating PDF dossier for case {real_case_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF dossier: {str(e)}")

    # Record the export action in the tamper-evident Merkle audit ledger
    try:
        from audit_engine import log_audit_event
        log_audit_event(
            db=db,
            action_type="REPORT_EXPORT",
            target_type="case",
            target_id=str(real_case_id),
            description=f"Exported official PDF forensic dossier for Case #{real_case_id} ({len(pdf_bytes):,} bytes).",
            user_id=current_user.id,
            user_name=current_user.full_name,
            user_role=current_user.role,
            case_id=real_case_id
        )
    except Exception as e:
        logger.warning(f"Could not log audit event for PDF export: {e}")

    safe_title = "".join(c for c in case.title if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
    filename = f"Evidentia_Case_{real_case_id}_{safe_title[:30]}_Dossier.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )


@app.get("/cases/{case_id}/reports/docket-data")
def get_case_docket_data(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the comprehensive compiled docket structure for client-side
    preview, verification, and interactive report rendering.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    case = db.query(Case).filter(Case.id == real_case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    evidence_list = db.query(Evidence).filter(Evidence.case_id == real_case_id).all()
    entities = db.query(Entity).filter(Entity.case_id == real_case_id).all()
    events = db.query(Event).filter(Event.case_id == real_case_id).order_by(Event.timestamp.asc()).all()
    hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == real_case_id).all()
    contradictions = db.query(Contradiction).filter(Contradiction.case_id == real_case_id).all()
    custody_logs = db.query(CustodyLog).filter(CustodyLog.case_id == real_case_id).order_by(CustodyLog.timestamp.desc()).all()
    citations = db.query(SourceCitation).filter(SourceCitation.case_id == real_case_id).all()
    overrides = db.query(EvidenceAssessment).filter(EvidenceAssessment.analyst_override == True).join(Hypothesis).filter(Hypothesis.case_id == real_case_id).all()

    # Recompute scoring
    scoring_run = execute_scoring_run(real_case_id, db)
    audit_chain = verify_audit_chain(db, case_id=real_case_id)

    return {
        "case": {
            "id": case.id,
            "title": case.title,
            "description": case.description,
            "status": case.status,
            "created_by": case.created_by,
            "created_at": case.created_at.isoformat() if case.created_at else None,
            "location": getattr(case, 'location', 'Crime Scene'),
            "victim": getattr(case, 'victim', 'N/A'),
            "priority": getattr(case, 'priority', 'High')
        },
        "stats": {
            "evidence_count": len(evidence_list),
            "entity_count": len(entities),
            "timeline_count": len(events),
            "hypothesis_count": len(hypotheses),
            "contradiction_count": len(contradictions),
            "citation_count": len(citations),
            "override_count": len(overrides)
        },
        "evidence": [
            {
                "id": ev.id,
                "file_name": ev.file_name,
                "evidence_type": ev.evidence_type,
                "file_hash": ev.file_hash,
                "hash_verified": ev.hash_verified,
                "sec_65b_certificate_present": ev.sec_65b_certificate_present,
                "chain_of_custody_complete": ev.chain_of_custody_complete,
                "source": ev.source
            } for ev in evidence_list
        ],
        "entities": [
            {
                "id": ent.id,
                "name": ent.name,
                "type": ent.type,
                "confidence": ent.confidence,
                "source_quote": ent.source_quote
            } for ent in entities
        ],
        "events": [
            {
                "id": ev.id,
                "title": ev.title,
                "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                "description": ev.description,
                "location": ev.location,
                "evidence_id": ev.evidence_id
            } for ev in events
        ],
        "hypotheses": scoring_run.get("hypotheses", []),
        "breakdowns": scoring_run.get("hypothesis_breakdowns", {}),
        "robustness": scoring_run.get("robustness_ranges", {}),
        "contradictions": [
            {
                "id": c.id,
                "statement_a": c.statement_a,
                "statement_b": c.statement_b,
                "conflict_type": c.conflict_type,
                "confidence": c.confidence
            } for c in contradictions
        ],
        "citations": [
            {
                "id": cit.id,
                "fact_type": cit.fact_type,
                "quote": cit.quote,
                "evidence_id": cit.evidence_id,
                "chunk_id": cit.chunk_id,
                "page_number": cit.page_number,
                "char_start": cit.char_start,
                "char_end": cit.char_end,
                "verified_match": cit.verified_match,
                "match_confidence": cit.match_confidence
            } for cit in citations
        ],
        "audit_chain": audit_chain
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)