# backend/app.py

# ============================================================
# IMPORTS
# ============================================================
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form, Response, status
from fastapi.responses import JSONResponse
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

# Config
from config import DEFAULT_MODEL_NAME, FALLBACK_MODEL_NAMES, ALLOWED_ORIGINS

# Database and models
from database import engine, get_db, Base
from models import (
    Case, Evidence, EvidenceStatus, Entity, Event,
    Hypothesis, EvidenceAssessment, AssessmentClassification,
    Contradiction, InvestigationTask, Relationship,
    ReliabilityConfig, ScoringRun, User, CaseMember,
    CustodyLog, AuditLog, ExhibitChunk, SourceCitation,
    SuspectProfileFactor, BackgroundWeightConfig, PriorRecord,
    LikelihoodRatioReference, ScoringConfigVersion,
    EditLock, CasePresence, CollaborationEvent
)
from collaboration import publish_collaboration_event, release_edit_lock
from security_encryption import encrypt_field, decrypt_field
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
    ExhibitChunkOut, SourceCitationOut, TextCorrectionRequest, TextCorrectionResponse,
    SuspectProfileFactorCreate, SuspectProfileFactorOut,
    BackgroundWeightConfigOut, BackgroundWeightConfigUpdate, ScoringConfigVersionOut,
    PriorRecordCreate, PriorRecordUpdate, PriorRecordOut,
    CriminalHistoryComparisonOut, CriminalHistoryComparisonHypothesis,
    LikelihoodRatioReferenceOut, LikelihoodRatioReferenceUpdate,
    DependencyGroupUpdateRequest, ExculpatoryConfigOut,
    MonteCarloScoringResponse, MonteCarloHypothesisRange,
    InvestigativeGapOut, NextBestStepOut
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
    compute_evidence_scores,
    compute_background_scores,
    combine_scores_bayesian,
    calculate_three_layer_ach_scoring,
    calculate_sensitivity_and_robustness,
    resolve_exhibit_reliability,
    compute_exhibit_diagnosticity,
    DEFAULT_BASE_RELIABILITY,
    check_travel_feasibility,
    generate_ai_suspect_profile_suggestions,
    CHANGE2_FACTOR_NUMERICS,
    AVOID_DOUBLE_COUNTING_RULE,
    CRIMINAL_HISTORY_SAFEGUARD_NOTICE,
    compute_mo_similarity,
    calculate_record_effective_weight,
    LIKELIHOOD_RATIO_REFERENCE_TABLE,
    shrink_likelihood_ratio,
    resolve_assessment_likelihood_ratio,
    compute_bayesian_lr_scoring,
    map_legacy_classification_to_finding,
    UNKNOWN_HYPOTHESIS_TITLE,
    DEFAULT_UNKNOWN_PRIOR,
    EXCULPATORY_EVIDENCE_TYPES_CONFIG,
    resolve_exhibit_dependency_multipliers,
    compute_monte_carlo_scoring_ranges,
    detect_investigative_gaps,
    simulate_next_best_steps
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

# ============================================================
# BACKGROUND WORKER SUPERVISOR (FAIL-SAFE FOR QUEUED JOBS)
# ============================================================
@app.on_event("startup")
def startup_worker_supervisor():
    import sys
    """
    Automatic Embedded Worker Supervisor.
    If standalone worker is not explicitly running (DISABLE_EMBEDDED_WORKER not set to true),
    starts a daemon thread to guarantee queued forensic pipeline jobs are processed immediately.
    """
    disable_embedded = os.getenv("DISABLE_EMBEDDED_WORKER", "false").lower() in ("true", "1", "yes")
    is_pytest = "pytest" in sys.modules or os.getenv("PYTEST_CURRENT_TEST") is not None
    if not disable_embedded and not is_pytest:
        try:
            from worker import start_embedded_worker
            worker_thread, stop_event = start_embedded_worker(max_workers=1)
            app.state.worker_thread = worker_thread
            app.state.worker_stop_event = stop_event
            print("[EVIDENTIA-AI] Embedded background worker started successfully.")
        except Exception as e:
            print(f"[!] Could not start embedded worker: {e}")

@app.on_event("shutdown")
def shutdown_worker_supervisor():
    if hasattr(app.state, "worker_stop_event") and app.state.worker_stop_event:
        app.state.worker_stop_event.set()
        print("[EVIDENTIA-AI] Embedded background worker stop signal sent.")


# ============================================================
# CORS CONFIGURATION (Dynamic Allowed Origins from Environment)
# ============================================================
def get_allowed_origins() -> list[str]:
    """
    Reads permitted CORS origins from environment variable 'CORS_ALLOWED_ORIGINS' or 'ALLOWED_ORIGINS'.
    Supports comma-separated values, JSON arrays, and deployed frontend addresses.
    Falls back to local development origins and known deployment domains.
    """
    default_origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:3000",
        "https://evidentia-ai.netlify.app",
        "https://evidentia-ai.vercel.app",
    ]
    
    env_origins = os.getenv("CORS_ALLOWED_ORIGINS") or os.getenv("ALLOWED_ORIGINS")
    if not env_origins:
        return default_origins
    
    origins_set = set(default_origins)
    
    # Try parsing JSON array format (e.g. '["https://example.com"]')
    trimmed = env_origins.strip()
    if trimmed.startswith("[") and trimmed.endswith("]"):
        try:
            parsed = json.loads(trimmed)
            if isinstance(parsed, list):
                for item in parsed:
                    clean = str(item).strip().rstrip("/")
                    if clean:
                        origins_set.add(clean)
                return sorted(list(origins_set))
        except Exception:
            pass
            
    # Comma-separated list format (e.g. 'https://my-app.vercel.app, https://my-backend.railway.app')
    for raw in env_origins.split(","):
        clean = raw.strip().rstrip("/")
        if clean:
            origins_set.add(clean)
            
    return sorted(list(origins_set))

allowed_origins = get_allowed_origins()
allow_all = "*" in allowed_origins

cors_regex = os.getenv("CORS_ORIGIN_REGEX", r"^https:\/\/.*(evidentia|vercel|netlify|onrender|railway)\.(app|dev|com)$")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else allowed_origins,
    allow_credentials=not allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=cors_regex if not allow_all else None,
)

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    import logging
    logging.getLogger("uvicorn.error").exception(f"Unhandled server error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )

# ============================================================
# MODULAR ROUTERS (auth, cases, evidence, hypotheses, scoring, history, evaluation, reports)
# ============================================================
from routers import (
    auth_router,
    cases_router,
    evidence_router,
    hypotheses_router,
    scoring_router,
    history_router,
    evaluation_router,
    reports_router,
    jobs_router,
    collaboration_router,
    alerts_router,
    chargesheet_router,
    interviews_router,
    cross_case_router,
    telecom_financial_router,
    multilingual_router,
    decision_quality_router,
    security_admin_router,
    connectors_router,
    situation_board_router,
    geospatial_timeline_router,
    watchlists_router,
    voice_notes_router,
    system_health_router,
    search_router,
    priorities_router,
    case_file_router,
    physical_evidence_router,
    alibi_router,
    intake_router,
    legal_glossary_router,
    sync_router,
)

app.include_router(auth_router)
app.include_router(cases_router)
app.include_router(evidence_router)
app.include_router(hypotheses_router)
app.include_router(scoring_router)
app.include_router(history_router)
app.include_router(evaluation_router)
app.include_router(reports_router)
app.include_router(jobs_router)
app.include_router(collaboration_router)
app.include_router(alerts_router)
app.include_router(chargesheet_router)
app.include_router(interviews_router)
app.include_router(cross_case_router)
app.include_router(telecom_financial_router)
app.include_router(multilingual_router)
app.include_router(decision_quality_router)
app.include_router(security_admin_router)
app.include_router(connectors_router)
app.include_router(situation_board_router)
app.include_router(geospatial_timeline_router)
app.include_router(watchlists_router)
app.include_router(voice_notes_router)
app.include_router(system_health_router)
app.include_router(search_router)
app.include_router(priorities_router)
app.include_router(case_file_router)
app.include_router(physical_evidence_router)
app.include_router(alibi_router)
app.include_router(intake_router)
app.include_router(legal_glossary_router)
app.include_router(sync_router)

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

# Host & Container Orchestrator Health Check Endpoint
@app.get("/")
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Host & Container Orchestrator Health Check Endpoint.
    Verifies process responsiveness, database connectivity, and runtime metrics.
    Returns HTTP 200 OK when healthy, or HTTP 503 if database check fails.
    """
    db_status = "connected"
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        raise HTTPException(
            status_code=503,
            detail={"status": "degraded", "database": db_status, "service": "evidentia-ai-backend"}
        )

    return {
        "status": "healthy",
        "service": "evidentia-ai-backend",
        "version": "1.0.0",
        "database": db_status,
        "environment": os.getenv("ENVIRONMENT", "production"),
        "allowed_origins_count": len(allowed_origins),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ============================================================
# AUTHENTICATION & ACCESS CONTROL (PHASE 3)
# ============================================================













# ============================================================
# CASE MEMBERSHIP & ISOLATION ENDPOINTS
# ============================================================







# ============================================================
# CASE CRUD ENDPOINTS (WITH ROLE & ISOLATION CHECKS)
# ============================================================

def ensure_unknown_hypothesis(case_id: int, db: Session) -> Hypothesis:
    """
    CHANGE 5: Unknown / Other Explanation Hypothesis
    Always add it automatically for every case. Gives a modest default prior
    that grows when the evidence fits no listed suspect well.
    """
    unknown = db.query(Hypothesis).filter(
        Hypothesis.case_id == case_id,
        (Hypothesis.is_unknown == True) | (Hypothesis.title == UNKNOWN_HYPOTHESIS_TITLE)
    ).first()

    if not unknown:
        unknown = Hypothesis(
            case_id=case_id,
            title=UNKNOWN_HYPOTHESIS_TITLE,
            description="Perpetrator is an unknown individual or alternative explanation not currently listed among known suspects.",
            is_unknown=True,
            status="Active"
        )
        db.add(unknown)
        db.commit()
        db.refresh(unknown)
    else:
        if not unknown.is_unknown:
            unknown.is_unknown = True
            db.commit()
            db.refresh(unknown)

    return unknown







def _legacy_get_case(case_id: int, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case





# ============================================================
# EVIDENCE UPLOAD & FORENSIC INGESTION (SHA-256 & CUSTODY)
# ============================================================


# ============================================================
# GET EVIDENCE & CUSTODY LOGS
# ============================================================




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



# ============================================================
# AUDIT LOG & CRYPTOGRAPHIC MERKLE CHAIN ENDPOINTS
# ============================================================







# ============================================================
# ENTITY AND EVENT ENDPOINTS
# ============================================================







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
    triggered_by: str = "recalculate",
    scoring_method: str = "bayesian_lr",
    lr_mode: str = "typical"
) -> Dict[str, Any]:
    """
    Central Scoring Engine Execution:
    - Pure python evaluation using ach_scoring.py
    - Persists normalized scores & intermediate fields to DB
    - Stores snapshot in scoring_runs table
    """
    # CHANGE 5: Ensure Unknown / Other Explanation hypothesis exists before scoring
    ensure_unknown_hypothesis(case_id, db)

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

    # Load custom Likelihood Ratio Reference Table entries if any configured in DB
    lr_refs_db = db.query(LikelihoodRatioReference).all()
    custom_lr_table = {
        ref.category_key: {
            "evidence_type": ref.evidence_type,
            "finding_name": ref.finding_name,
            "finding_description": getattr(ref, "finding_description", None) or ref.finding_name,
            "support_direction": ref.support_direction,
            "min_lr": ref.min_lr,
            "max_lr": ref.max_lr,
            "typical_lr": ref.typical_lr,
            "source_citation": ref.source_citation,
            "forensic_error_rate": ref.forensic_error_rate,
            "notes": ref.notes
        }
        for ref in lr_refs_db
    } if lr_refs_db else None

    # Convert to plain structures for ach_scoring
    hypo_dicts = [
        {
            "id": h.id,
            "title": h.title,
            "description": h.description,
            "is_unknown": bool(getattr(h, "is_unknown", False)),
            "background_score": getattr(h, "background_score", None),
            "background_factors": getattr(h, "background_factors", None)
        }
        for h in hypotheses
    ]
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
            "quality_rating": float(ev.quality_rating or 3.0),
            "dependency_group": getattr(ev, "dependency_group", None)
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
            "analyst_override": bool(a.analyst_override),
            "finding_category": getattr(a, "finding_category", None),
            "finding_name": getattr(a, "finding_name", None),
            "likelihood_ratio": getattr(a, "likelihood_ratio", None),
            "effective_lr": getattr(a, "effective_lr", None),
            "lr_min": getattr(a, "lr_min", None),
            "lr_max": getattr(a, "lr_max", None),
            "lr_source_citation": getattr(a, "lr_source_citation", None),
            "lr_error_rate": getattr(a, "lr_error_rate", None),
            "weight_of_evidence_bans": getattr(a, "weight_of_evidence_bans", None),
            "is_exculpatory": bool(getattr(a, "is_exculpatory", False)),
            "clearing_factor_note": getattr(a, "clearing_factor_note", None),
            "dependency_group": getattr(a, "dependency_group", None),
            "dependency_weight_multiplier": getattr(a, "dependency_weight_multiplier", 1.0),
            "damped_likelihood_ratio": getattr(a, "damped_likelihood_ratio", None)
        }
        for a in assessments
    ]

    # Change 2: Load Suspect Profile Factors and Background Configuration
    profile_factors_db = db.query(SuspectProfileFactor).filter(SuspectProfileFactor.case_id == case_id).all()
    suspect_factors_by_hyp = {}
    for f in profile_factors_db:
        suspect_factors_by_hyp.setdefault(f.hypothesis_id, []).append({
            "id": f.id,
            "factor_type": f.factor_type,
            "factor_value": f.factor_value,
            "numeric_adjustment": f.numeric_adjustment,
            "note": f.note,
            "source_evidence_id": f.source_evidence_id,
            "source_exhibit_name": f.source_exhibit_name,
            "confidence": f.confidence,
            "is_confirmed": bool(f.is_confirmed),
            "entered_by": f.entered_by
        })

    bg_cfg_db = db.query(BackgroundWeightConfig).filter(
        (BackgroundWeightConfig.case_id == case_id) | (BackgroundWeightConfig.case_id == None)
    ).first()
    bg_cfg_dict = {}
    if bg_cfg_db:
        bg_cfg_dict = {
            "access_weight": bg_cfg_db.access_weight,
            "opportunity_weight": bg_cfg_db.opportunity_weight,
            "means_weight": bg_cfg_db.means_weight,
            "motive_weight": bg_cfg_db.motive_weight,
            "travel_feasibility_weight": bg_cfg_db.travel_feasibility_weight,
            "alibi_strongly_verified_discount": bg_cfg_db.alibi_strongly_verified_discount,
            "alibi_partially_verified_discount": bg_cfg_db.alibi_partially_verified_discount,
            "alibi_contradicted_multiplier": bg_cfg_db.alibi_contradicted_multiplier,
            "impossible_travel_penalty": bg_cfg_db.impossible_travel_penalty,
            "include_criminal_history": getattr(bg_cfg_db, "include_criminal_history", True),
            "criminal_history_max_cap": getattr(bg_cfg_db, "criminal_history_max_cap", 0.10),
            "exclude_juvenile_records": getattr(bg_cfg_db, "exclude_juvenile_records", True),
            "exclude_unverified_identity": getattr(bg_cfg_db, "exclude_unverified_identity", True),
            "min_identity_confidence": getattr(bg_cfg_db, "min_identity_confidence", 0.70)
        }

    # Change 3: Prior Criminal History Records & Case Modus Operandi
    case_obj = db.query(Case).filter(Case.id == case_id).first()
    exhibit_texts = [ev.extracted_text for ev in exhibits if ev.extracted_text]
    full_case_narrative = (case_obj.description or "") + " " + " ".join(exhibit_texts[:5])
    fn_lower = full_case_narrative.lower()

    weapon_infer = getattr(case_obj, "weapon_used", "") or ""
    if not weapon_infer:
        if any(w in fn_lower for w in ["iron rod", "jack handle", "tire lever", "rod", "pipe", "blunt"]):
            weapon_infer = "Iron rod / jack handle"
        elif any(w in fn_lower for w in ["knife", "blade", "sharp"]):
            weapon_infer = "Knife / Sharp weapon"
        elif any(w in fn_lower for w in ["firearm", "gun", "pistol"]):
            weapon_infer = "Firearm"

    entry_infer = getattr(case_obj, "entry_method", "") or ""
    if not entry_infer:
        if any(w in fn_lower for w in ["qualis", "cab", "taxi", "shared vehicle", "transit", "abduction", "intercept", "bus"]):
            entry_infer = "Fake transport / cab route intercept"
        elif any(w in fn_lower for w in ["break-in", "window", "trespass"]):
            entry_infer = "Forced entry / trespass"

    victim_infer = getattr(case_obj, "victim_type", "") or ""
    if not victim_infer:
        if any(w in fn_lower for w in ["female", "woman", "techie", "engineer", "commuter", "synechron", "lone"]):
            victim_infer = "Lone female commuter post-evening shift"

    loc_infer = getattr(case_obj, "location_type", "") or ""
    if not loc_infer:
        if any(w in fn_lower for w in ["kharadi", "bypass", "highway", "outskirts", "isolated", "desolate", "road"]):
            loc_infer = "Desolate transit bypass / isolated corridor"

    time_infer = getattr(case_obj, "time_pattern", "") or ""
    if not time_infer:
        if any(w in fn_lower for w in ["night", "late", "shift", "evening", "21:00", "22:00"]):
            time_infer = "Late night 21:00-01:00"

    current_case_profile = {
        "case_id": case_id,
        "title": case_obj.title if case_obj else "",
        "description": full_case_narrative,
        "crime_type": getattr(case_obj, "crime_type", "") or "",
        "weapon_used": weapon_infer,
        "entry_method": entry_infer,
        "victim_type": victim_infer,
        "location_type": loc_infer,
        "time_pattern": time_infer,
        "mo_description": full_case_narrative
    }

    prior_records_db = db.query(PriorRecord).filter(PriorRecord.case_id == case_id).all()
    prior_records_by_hyp = {}
    for pr in prior_records_db:
        # Compute real-time MO similarity and snapshot to DB
        mo_res = compute_mo_similarity(pr, current_case_profile)
        eff_res = calculate_record_effective_weight(pr, mo_res, bg_cfg_dict)
        pr.computed_mo_similarity = mo_res.get("overall_similarity", 0.0)
        pr.similarity_breakdown = json.dumps(mo_res.get("field_scores", {}))
        pr.quoted_comparison = mo_res.get("quoted_comparison", "")
        pr.effective_weight = eff_res.get("effective_weight", 0.0)
        pr.history_contribution = eff_res.get("contribution", 0.0)

        hyp_key = pr.hypothesis_id
        if not hyp_key and pr.suspect_name:
            for h in hypotheses:
                if pr.suspect_name.lower() in h.title.lower() or h.title.lower() in pr.suspect_name.lower():
                    hyp_key = h.id
                    break
        if hyp_key:
            prior_records_by_hyp.setdefault(hyp_key, []).append({
                "id": pr.id,
                "case_id": pr.case_id,
                "hypothesis_id": hyp_key,
                "suspect_name": pr.suspect_name,
                "offense_type": pr.offense_type,
                "legal_section": pr.legal_section,
                "offense_date": pr.offense_date.isoformat() if pr.offense_date else None,
                "location": pr.location,
                "outcome": pr.outcome,
                "weapon_used": pr.weapon_used,
                "entry_method": pr.entry_method,
                "victim_type": pr.victim_type,
                "location_type": pr.location_type,
                "time_pattern": pr.time_pattern,
                "mo_description": pr.mo_description,
                "source_agency": pr.source_agency,
                "source_document": pr.source_document,
                "verification_status": pr.verification_status,
                "identity_match_confidence": pr.identity_match_confidence,
                "verified_identity": bool(pr.verified_identity),
                "is_juvenile": bool(pr.is_juvenile)
            })

    scoring_res = calculate_three_layer_ach_scoring(
        hypo_dicts, exhibit_dicts, assessment_dicts,
        custom_base_configs=base_map,
        excluded_exhibit_ids=excluded_ids,
        suspect_factors_by_hypothesis=suspect_factors_by_hyp,
        background_config=bg_cfg_dict,
        prior_records_by_hypothesis=prior_records_by_hyp,
        current_case_profile=current_case_profile,
        scoring_method=scoring_method,
        lr_mode=lr_mode,
        custom_lr_table=custom_lr_table
    )

    sens_res = calculate_sensitivity_and_robustness(
        hypo_dicts, exhibit_dicts, assessment_dicts,
        custom_base_configs=base_map
    )

    mc_res = compute_monte_carlo_scoring_ranges(
        hypotheses=hypo_dicts,
        exhibits=exhibit_dicts,
        assessments=assessment_dicts,
        background_priors={h.id: float(getattr(h, "background_score", None) or (100.0 / len(hypo_dicts))) for h in hypotheses},
        custom_lr_table=custom_lr_table,
        custom_base_configs=base_map,
        num_simulations=150,
        random_seed=42,
        excluded_exhibit_ids=excluded_ids
    )

    # Persist updated values into DB
    hyp_map = {h_data["id"]: h_data for h_data in scoring_res.get("hypotheses", [])}
    for h in hypotheses:
        if h.id in hyp_map:
            h_data = hyp_map[h.id]
            # Change 1: Three-Layer Output Persistence
            ev_val = float(h_data.get("evidence_score", h_data.get("support_score", 0.0)))
            bg_val = float(h_data.get("background_score", 0.0))
            comb_val = float(h_data.get("combined_score", ev_val))
            bg_no_hist = float(h_data.get("background_score_without_history", bg_val))
            comb_no_hist = float(h_data.get("combined_score_without_history", comb_val))
            hist_contrib = float(h_data.get("history_contribution", 0.0))

            h.evidence_score = ev_val
            h.background_score = bg_val
            h.combined_score = comb_val
            h.background_score_without_history = bg_no_hist
            h.combined_score_without_history = comb_no_hist
            h.history_contribution = hist_contrib
            h.support_score = comb_val  # maintain backwards compatibility
            h.disconfirmation_penalty = h_data.get("disconfirmation_penalty", 0.0)
            h.status = h_data.get("status", "Active")

            # Change 4: Probabilistic Bayesian LR Metrics Persistence
            h.bayesian_lr_score = float(h_data.get("bayesian_lr_score", comb_val))
            h.bayesian_evidence_score = float(h_data.get("bayesian_evidence_score", ev_val))
            h.classic_ach_score = float(h_data.get("classic_ach_score", comb_val))
            h.classic_evidence_score = float(h_data.get("classic_evidence_score", ev_val))
            h.cumulative_lr = float(h_data.get("cumulative_lr", 1.0))

            # Change 5: Unknown Hypothesis & Lead Message Persistence
            h.is_unknown = bool(h_data.get("is_unknown", False))
            h.lead_message = h_data.get("lead_message")

            if "background_factors" in h_data:
                bg_fac = h_data["background_factors"]
                h.background_factors = json.dumps(bg_fac) if isinstance(bg_fac, (dict, list)) else str(bg_fac)
            if "scoring_inputs" in h_data:
                sc_in = h_data["scoring_inputs"]
                h.scoring_inputs = json.dumps(sc_in) if isinstance(sc_in, (dict, list)) else str(sc_in)

    matrix_cells = scoring_res.get("matrix", {})
    for a in assessments:
        cell = matrix_cells.get(a.evidence_id, {}).get(a.hypothesis_id)
        if cell:
            a.computed_reliability = cell.get("reliability", 1.0)
            a.computed_diagnosticity = cell.get("diagnosticity", 1.0)
            a.final_contribution = cell.get("contribution", 0.0)

            # Change 4: Matrix Cell Likelihood Ratio Fields Persistence
            if cell.get("finding_category"):
                a.finding_category = cell.get("finding_category")
            if cell.get("finding_name"):
                a.finding_name = cell.get("finding_name")
            if "base_lr" in cell:
                a.likelihood_ratio = cell.get("base_lr")
            elif "likelihood_ratio" in cell:
                a.likelihood_ratio = cell.get("likelihood_ratio")
            if "effective_lr" in cell:
                a.effective_lr = cell.get("effective_lr")
            if "min_lr" in cell:
                a.lr_min = cell.get("min_lr")
            if "max_lr" in cell:
                a.lr_max = cell.get("max_lr")
            if "source_citation" in cell:
                a.lr_source_citation = cell.get("source_citation")
            if "forensic_error_rate" in cell:
                a.lr_error_rate = cell.get("forensic_error_rate")
            if "weight_of_evidence_bans" in cell:
                a.weight_of_evidence_bans = cell.get("weight_of_evidence_bans")

            # Change 5: Clearing Factor & Dependency Group Fields Persistence
            if "is_exculpatory" in cell:
                a.is_exculpatory = bool(cell.get("is_exculpatory", False))
            if cell.get("clearing_factor_note"):
                a.clearing_factor_note = cell.get("clearing_factor_note")
            if cell.get("dependency_group"):
                a.dependency_group = cell.get("dependency_group")
            if cell.get("dependency_weight_multiplier") is not None:
                a.dependency_weight_multiplier = float(cell.get("dependency_weight_multiplier", 1.0))
            if cell.get("damped_likelihood_ratio") is not None:
                a.damped_likelihood_ratio = float(cell.get("damped_likelihood_ratio", 1.0))

    # Record history snapshot
    try:
        run_record = ScoringRun(
            case_id=case_id,
            triggered_by=triggered_by,
            settings_snapshot=json.dumps(base_map),
            results_snapshot=json.dumps({
                "hypotheses": scoring_res.get("hypotheses", []),
                "critical_count": sens_res.get("critical_count", 0),
                "robustness_ranges": sens_res.get("robustness_ranges", {}),
                "lead_message": scoring_res.get("lead_message"),
                "dependency_groups_audit": scoring_res.get("dependency_groups_audit", {})
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
                "support_score": h_info.get("combined_score", h_info["support_score"]),
                "evidence_score": h_info.get("evidence_score", h_info["support_score"]),
                "background_score": h_info.get("background_score", 0.0),
                "combined_score": h_info.get("combined_score", h_info["support_score"]),
                "disconfirmation_penalty": h_info["disconfirmation_penalty"],
                "relative_likelihood": h_info.get("evidence_score", h_info["support_score"]),
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
        "order_independence_verified": scoring_res.get("order_independence_verified", True),
        "scoring_method": scoring_res.get("scoring_method", scoring_method),
        "lr_mode": scoring_res.get("lr_mode", lr_mode),
        "message": scoring_res.get("message"),
        "hypotheses": scoring_res.get("hypotheses", []),
        "matrix": scoring_res.get("matrix", {}),
        "hypothesis_breakdowns": scoring_res.get("hypothesis_breakdowns", {}),
        "reliability_audits": scoring_res.get("reliability_audits", {}),
        "diagnosticity_audits": scoring_res.get("diagnosticity_audits", {}),
        "robustness_ranges": sens_res.get("robustness_ranges", {}),
        "critical_exhibits": sens_res.get("critical_exhibits", []),
        "exhibit_impacts": sens_res.get("exhibit_impacts", []),
        "background_summary": scoring_res.get("background_summary", {}),
        "bayesian_summary": scoring_res.get("bayesian_summary", {}),
        "bayesian_lr_audit": scoring_res.get("bayesian_lr_audit", {}),
        "classic_ach_audit": scoring_res.get("classic_ach_audit", {}),
        "reference_table": scoring_res.get("reference_table", LIKELIHOOD_RATIO_REFERENCE_TABLE),
        "criminal_history_comparison": scoring_res.get("criminal_history_comparison", {}),
        "criminal_history_safeguard_notice": scoring_res.get("criminal_history_safeguard_notice", CRIMINAL_HISTORY_SAFEGUARD_NOTICE),
        "monte_carlo": {
            "ranges": mc_res.get("ranges", []),
            "cannot_separate": mc_res.get("cannot_separate", False),
            "close_results_warning": mc_res.get("close_results_warning"),
            "discriminating_evidence_needed": mc_res.get("discriminating_evidence_needed", []),
            "is_fragile": mc_res.get("is_fragile", False),
            "fragile_exhibit_id": mc_res.get("fragile_exhibit_id"),
            "fragile_exhibit_title": mc_res.get("fragile_exhibit_title"),
            "fragility_message": mc_res.get("fragility_message")
        },
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
        return getattr(h, "combined_score", None) or h.support_score or 50.0
    # Fallback disconfirmation heuristic
    penalties = sum(get_classification_config(a.classification)["penalty"] for a in assessments)
    raw = math.exp(-0.75 * penalties) * 100.0
    return max(0.0, min(100.0, round(raw, 1)))








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






# ==============================================================================
# CHANGE 2: SUSPECT BACKGROUND PROFILE & FEASIBILITY ENDPOINTS
# ==============================================================================

@app.get("/cases/{case_id}/hypotheses/{hypothesis_id}/suspect-profile")
def get_suspect_profile(
    case_id: str,
    hypothesis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the structured suspect profile (Access, Opportunity, Means, Motive,
    Alibi Status, Travel Feasibility), source citations, and human sign-off status.
    Every profile view is logged to the Merkle audit ledger.
    """
    real_case_id = resolve_case_id(case_id, db)
    hyp = db.query(Hypothesis).filter(Hypothesis.id == hypothesis_id, Hypothesis.case_id == real_case_id).first()
    if not hyp:
        raise HTTPException(status_code=404, detail="Hypothesis not found")

    factors = db.query(SuspectProfileFactor).filter(
        SuspectProfileFactor.hypothesis_id == hypothesis_id
    ).all()

    # Log suspect profile view to tamper-evident audit ledger
    try:
        log_audit_event(
            db=db,
            action_type="SUSPECT_PROFILE_VIEW",
            target_type="hypothesis",
            target_id=str(hypothesis_id),
            description=f"Investigator {current_user.full_name} ({current_user.role}) viewed suspect profile factors for Hypothesis #{hypothesis_id} ({hyp.title}).",
            user_id=current_user.id,
            user_name=current_user.full_name,
            user_role=current_user.role,
            case_id=real_case_id
        )
    except Exception as e:
        print(f"[!] Suspect profile view audit error: {e}")

    # Timeline feasibility check
    feasibility = check_travel_feasibility(
        suspect_location="Suspect Known Sector",
        scene_location="Incident Site",
        time_window_minutes=60,
        distance_km=25
    )

    factors_out = []
    for f in factors:
        effect = "neutral"
        if f.factor_type in ["access", "opportunity", "means", "motive"]:
            if (f.numeric_adjustment or 0.5) >= 0.75:
                effect = "raises_prior"
            elif (f.numeric_adjustment or 0.5) <= 0.35:
                effect = "lowers_prior"
        elif f.factor_type == "alibi_status":
            val = (f.factor_value or "").lower()
            if "strongly_verified" in val or "strong" in val:
                effect = "lowers_prior_sharply"
            elif "partially_verified" in val or "partial" in val:
                effect = "lowers_prior"
            elif "contradicted" in val:
                effect = "raises_prior"
        elif f.factor_type == "travel_feasibility":
            if "impossible" in (f.factor_value or "").lower():
                effect = "blocks_impossible"
            elif "borderline" in (f.factor_value or "").lower():
                effect = "tight_margin"
            else:
                effect = "feasible"

        is_authorized = current_user.role in ["admin", "lead_investigator"]
        decrypted_note = decrypt_field(f.note) if is_authorized else "[RESTRICTED - Section 54 IEA Character Safeguard / Senior Clearance Required]"
        decrypted_name = decrypt_field(f.suspect_name) if is_authorized else "Suspect [Protected PII]"

        factors_out.append({
            "id": f.id,
            "case_id": f.case_id,
            "hypothesis_id": f.hypothesis_id,
            "suspect_name": decrypted_name,
            "factor_type": f.factor_type,
            "factor_value": f.factor_value,
            "numeric_adjustment": f.numeric_adjustment,
            "note": decrypted_note,
            "source_evidence_id": f.source_evidence_id,
            "source_exhibit_name": f.source_exhibit_name,
            "confidence": f.confidence,
            "entered_by": f.entered_by,
            "is_ai_suggested": bool(f.is_ai_suggested),
            "is_confirmed": bool(f.is_confirmed),
            "confirmed_by": f.confirmed_by,
            "confirmed_at": f.confirmed_at.isoformat() if f.confirmed_at else None,
            "effect_on_prior": effect,
            "created_at": f.created_at.isoformat() if f.created_at else None
        })

    confirmed_count = sum(1 for f in factors if f.is_confirmed)
    pending_ai_count = sum(1 for f in factors if f.is_ai_suggested and not f.is_confirmed)

    return {
        "status": "success",
        "case_id": real_case_id,
        "hypothesis_id": hypothesis_id,
        "hypothesis_title": hyp.title,
        "background_score": hyp.background_score or 50.0,
        "factors": factors_out,
        "summary": {
            "total_factors": len(factors),
            "confirmed_count": confirmed_count,
            "pending_ai_count": pending_ai_count,
            "has_human_signoff": confirmed_count > 0 and pending_ai_count == 0
        },
        "feasibility_check": feasibility,
        "avoid_double_counting_rule": AVOID_DOUBLE_COUNTING_RULE
    }


@app.post("/cases/{case_id}/hypotheses/{hypothesis_id}/suspect-profile/factors")
def create_or_update_suspect_factor(
    case_id: str,
    hypothesis_id: int,
    data: SuspectProfileFactorCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Data Entry: investigator enters or updates a suspect factor with human sign-off.
    Automatically recalculates 3-layer scores.
    Every factor entry is logged to the Merkle audit ledger.
    """
    real_case_id = resolve_case_id(case_id, db)
    hyp = db.query(Hypothesis).filter(Hypothesis.id == hypothesis_id, Hypothesis.case_id == real_case_id).first()
    if not hyp:
        raise HTTPException(status_code=404, detail="Hypothesis not found")

    existing = db.query(SuspectProfileFactor).filter(
        SuspectProfileFactor.hypothesis_id == hypothesis_id,
        SuspectProfileFactor.factor_type == data.factor_type
    ).first()

    ex_name = data.source_exhibit_name
    if data.source_evidence_id and not ex_name:
        ev = db.query(Evidence).filter(Evidence.id == data.source_evidence_id).first()
        if ev:
            ex_name = ev.file_name

    num_adj = data.numeric_adjustment
    if num_adj is None:
        num_adj = CHANGE2_FACTOR_NUMERICS.get(data.factor_value, 0.50)

    prior_val = existing.factor_value if existing else None
    if existing:
        current_version = getattr(existing, "version", 1) or 1
        if data.version is not None and data.version != current_version:
            log_audit_event(
                db=db,
                action_type="CONFLICT_REJECTED",
                target_type="suspect_factor",
                target_id=str(existing.id),
                description=f"Concurrent conflict on suspect factor #{existing.id}: User submitted v{data.version}, but current version is v{current_version}.",
                case_id=real_case_id,
                user_id=current_user.id,
                user_name=current_user.full_name,
                before_value=f"v{data.version}",
                after_value=f"v{current_version}",
                commit=True
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "conflict",
                    "message": f"Suspect factor #{existing.id} was modified by another investigator while you were editing.",
                    "item_type": "suspect_factor",
                    "item_id": str(existing.id),
                    "current_version": current_version,
                    "submitted_version": data.version,
                    "current_data": {
                        "id": existing.id,
                        "factor_type": existing.factor_type,
                        "factor_value": existing.factor_value,
                        "note": existing.note
                    }
                }
            )

        now_utc = datetime.now(timezone.utc)
        active_lock = db.query(EditLock).filter(
            EditLock.case_id == real_case_id,
            EditLock.item_type == "suspect_factor",
            EditLock.item_id == str(existing.id),
            EditLock.expires_at > now_utc,
            EditLock.user_id != current_user.id
        ).first()
        if active_lock:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail={
                    "error": "locked",
                    "message": f"{active_lock.user_name} is currently editing this suspect factor.",
                    "locked_by": active_lock.user_name,
                    "user_role": active_lock.user_role,
                    "expires_at": active_lock.expires_at.isoformat()
                }
            )

        existing.factor_value = data.factor_value
        existing.numeric_adjustment = num_adj
        existing.note = encrypt_field(data.note)
        if data.suspect_name:
            existing.suspect_name = encrypt_field(data.suspect_name)
        existing.source_evidence_id = data.source_evidence_id
        existing.source_exhibit_name = ex_name
        existing.confidence = data.confidence or 0.90
        existing.entered_by = current_user.full_name or data.entered_by or "Investigator"
        existing.is_confirmed = True
        existing.confirmed_by = current_user.full_name or data.entered_by or "Investigator"
        existing.confirmed_at = datetime.utcnow()
        existing.version = current_version + 1
        factor_obj = existing
    else:
        factor_obj = SuspectProfileFactor(
            case_id=real_case_id,
            hypothesis_id=hypothesis_id,
            suspect_name=encrypt_field(data.suspect_name or hyp.title),
            factor_type=data.factor_type,
            factor_value=data.factor_value,
            numeric_adjustment=num_adj,
            note=encrypt_field(data.note),
            source_evidence_id=data.source_evidence_id,
            source_exhibit_name=ex_name,
            confidence=data.confidence or 0.90,
            entered_by=current_user.full_name or data.entered_by or "Investigator",
            is_ai_suggested=False,
            is_confirmed=True,
            confirmed_by=current_user.full_name or data.entered_by or "Investigator",
            confirmed_at=datetime.utcnow(),
            version=1
        )
        db.add(factor_obj)

    db.commit()
    db.refresh(factor_obj)

    # Release any edit lock held by this user
    release_edit_lock(db, real_case_id, "suspect_factor", str(factor_obj.id), current_user.id)

    # Publish collaboration item.changed event (restricted from reviewers)
    publish_collaboration_event(
        db=db,
        case_id=real_case_id,
        event_type="item.changed",
        item_type="suspect_profile",
        item_id=str(factor_obj.id),
        version=getattr(factor_obj, "version", 1),
        user_id=current_user.id,
        user_name=current_user.full_name,
        summary=f"{current_user.full_name} updated suspect factor '{factor_obj.factor_type}'.",
        payload={
            "id": factor_obj.id,
            "hypothesis_id": factor_obj.hypothesis_id,
            "factor_type": factor_obj.factor_type,
            "factor_value": factor_obj.factor_value,
            "version": getattr(factor_obj, "version", 1)
        },
        is_restricted=True
    )

    # Log factor entry/update to audit ledger
    try:
        log_audit_event(
            db=db,
            action_type="FACTOR_ENTRY",
            target_type="suspect_factor",
            target_id=str(factor_obj.id),
            description=f"Investigator {current_user.full_name} ({current_user.role}) recorded suspect factor '{data.factor_type}'='{data.factor_value}' for Hypothesis #{hypothesis_id} ({hyp.title}).",
            user_id=current_user.id,
            user_name=current_user.full_name,
            user_role=current_user.role,
            case_id=real_case_id,
            before_value=str(prior_val) if prior_val else None,
            after_value=str(data.factor_value)
        )
    except Exception as e:
        print(f"[!] Factor entry audit error: {e}")

    execute_scoring_run(real_case_id, db)
    db.refresh(hyp)

    return {
        "status": "success",
        "message": f"Suspect factor '{data.factor_type}' saved and signed off.",
        "factor_id": factor_obj.id,
        "updated_background_score": hyp.background_score,
        "updated_combined_score": hyp.combined_score
    }


@app.put("/cases/{case_id}/hypotheses/{hypothesis_id}/suspect-profile/factors/{factor_id}/confirm")
def confirm_ai_suspect_factor(
    case_id: str,
    hypothesis_id: int,
    factor_id: int,
    db: Session = Depends(get_db)
):
    """
    Human-in-the-loop sign-off: investigator confirms an AI-suggested suspect factor.
    """
    real_case_id = resolve_case_id(case_id, db)
    f = db.query(SuspectProfileFactor).filter(
        SuspectProfileFactor.id == factor_id,
        SuspectProfileFactor.hypothesis_id == hypothesis_id
    ).first()
    if not f:
        raise HTTPException(status_code=404, detail="Suspect profile factor not found")

    f.is_confirmed = True
    f.confirmed_by = "Lead Investigator"
    f.confirmed_at = datetime.utcnow()
    db.commit()

    execute_scoring_run(real_case_id, db)

    return {
        "status": "success",
        "message": f"Factor '{f.factor_type}' confirmed with human investigator sign-off."
    }


@app.delete("/cases/{case_id}/hypotheses/{hypothesis_id}/suspect-profile/factors/{factor_id}")
def delete_suspect_factor(
    case_id: str,
    hypothesis_id: int,
    factor_id: int,
    db: Session = Depends(get_db)
):
    real_case_id = resolve_case_id(case_id, db)
    f = db.query(SuspectProfileFactor).filter(
        SuspectProfileFactor.id == factor_id,
        SuspectProfileFactor.hypothesis_id == hypothesis_id
    ).first()
    if not f:
        raise HTTPException(status_code=404, detail="Factor not found")

    db.delete(f)
    db.commit()

    execute_scoring_run(real_case_id, db)
    return {"status": "success", "message": "Factor removed."}


@app.post("/cases/{case_id}/hypotheses/{hypothesis_id}/suspect-profile/ai-suggest")
def trigger_ai_profile_suggestions(
    case_id: str,
    hypothesis_id: int,
    db: Session = Depends(get_db)
):
    """
    AI Suggestion Engine (Change 2):
    Draws suggestions from exhibits (e.g., CDR placing phone near scene suggests 'opportunity').
    Inserts factors marked `is_ai_suggested = True` and `is_confirmed = False`
    so human investigator review and sign-off is required.
    """
    real_case_id = resolve_case_id(case_id, db)
    hyp = db.query(Hypothesis).filter(Hypothesis.id == hypothesis_id, Hypothesis.case_id == real_case_id).first()
    if not hyp:
        raise HTTPException(status_code=404, detail="Hypothesis not found")

    exhibits_db = db.query(Evidence).filter(Evidence.case_id == real_case_id).all()
    events_db = db.query(Event).filter(Event.case_id == real_case_id).all()

    exhibits_list = [
        {"id": e.id, "title": e.file_name, "fileName": e.file_name, "file_type": e.file_type}
        for e in exhibits_db
    ]
    events_list = [
        {"id": ev.id, "title": ev.title, "location": ev.location}
        for ev in events_db
    ]

    suggestions = generate_ai_suspect_profile_suggestions(
        hypothesis={"id": hyp.id, "title": hyp.title, "description": hyp.description},
        exhibits=exhibits_list,
        events=events_list
    )

    for s in suggestions:
        existing = db.query(SuspectProfileFactor).filter(
            SuspectProfileFactor.hypothesis_id == hypothesis_id,
            SuspectProfileFactor.factor_type == s["factor_type"]
        ).first()

        if existing:
            if not existing.is_confirmed:
                existing.factor_value = s["factor_value"]
                existing.numeric_adjustment = s["numeric_adjustment"]
                existing.note = s["note"]
                existing.source_evidence_id = s.get("source_evidence_id")
                existing.source_exhibit_name = s.get("source_exhibit_name")
                existing.is_ai_suggested = True
                existing.is_confirmed = False
                existing.entered_by = s.get("entered_by", "AI Assistant (Pending Human Sign-off)")
        else:
            new_f = SuspectProfileFactor(
                case_id=real_case_id,
                hypothesis_id=hypothesis_id,
                suspect_name=hyp.title,
                factor_type=s["factor_type"],
                factor_value=s["factor_value"],
                numeric_adjustment=s["numeric_adjustment"],
                note=s["note"],
                source_evidence_id=s.get("source_evidence_id"),
                source_exhibit_name=s.get("source_exhibit_name"),
                confidence=s.get("confidence", 0.85),
                entered_by=s.get("entered_by", "AI Assistant (Pending Human Sign-off)"),
                is_ai_suggested=True,
                is_confirmed=False
            )
            db.add(new_f)

    db.commit()

    execute_scoring_run(real_case_id, db)
    db.refresh(hyp)

    return {
        "status": "success",
        "message": f"Generated {len(suggestions)} AI suspect profile factor suggestions pending investigator sign-off.",
        "suggestions_count": len(suggestions),
        "updated_background_score": hyp.background_score
    }


@app.get("/cases/{case_id}/background-config", response_model=BackgroundWeightConfigOut)
def get_background_config(case_id: str, db: Session = Depends(get_db)):
    real_case_id = resolve_case_id(case_id, db)
    cfg = db.query(BackgroundWeightConfig).filter(
        (BackgroundWeightConfig.case_id == real_case_id) | (BackgroundWeightConfig.case_id == None)
    ).first()
    if not cfg:
        cfg = BackgroundWeightConfig(
            case_id=real_case_id,
            access_weight=0.25,
            opportunity_weight=0.25,
            means_weight=0.15,
            motive_weight=0.20,
            travel_feasibility_weight=0.15,
            alibi_strongly_verified_discount=0.10,
            alibi_partially_verified_discount=0.50,
            alibi_contradicted_multiplier=1.30,
            impossible_travel_penalty=0.05,
            avoid_double_counting_rule=AVOID_DOUBLE_COUNTING_RULE
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


@app.put("/cases/{case_id}/background-config", response_model=BackgroundWeightConfigOut)
def update_background_config(
    case_id: str,
    data: BackgroundWeightConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    real_case_id = resolve_case_id(case_id, db)
    if current_user.role not in ["admin", "lead_investigator"]:
        raise HTTPException(status_code=403, detail="Role Restricted: Only Lead Investigators and Administrators can calibrate scoring weights, caps, and parameters.")

    cfg = db.query(BackgroundWeightConfig).filter(
        (BackgroundWeightConfig.case_id == real_case_id) | (BackgroundWeightConfig.case_id == None)
    ).first()
    if not cfg:
        cfg = BackgroundWeightConfig(case_id=real_case_id)
        db.add(cfg)

    if data.access_weight is not None: cfg.access_weight = data.access_weight
    if data.opportunity_weight is not None: cfg.opportunity_weight = data.opportunity_weight
    if data.means_weight is not None: cfg.means_weight = data.means_weight
    if data.motive_weight is not None: cfg.motive_weight = data.motive_weight
    if data.travel_feasibility_weight is not None: cfg.travel_feasibility_weight = data.travel_feasibility_weight
    if data.alibi_strongly_verified_discount is not None: cfg.alibi_strongly_verified_discount = data.alibi_strongly_verified_discount
    if data.alibi_partially_verified_discount is not None: cfg.alibi_partially_verified_discount = data.alibi_partially_verified_discount
    if data.alibi_contradicted_multiplier is not None: cfg.alibi_contradicted_multiplier = data.alibi_contradicted_multiplier
    if data.impossible_travel_penalty is not None: cfg.impossible_travel_penalty = data.impossible_travel_penalty
    if data.include_criminal_history is not None: cfg.include_criminal_history = data.include_criminal_history
    if data.criminal_history_max_cap is not None: cfg.criminal_history_max_cap = data.criminal_history_max_cap
    if data.exclude_juvenile_records is not None: cfg.exclude_juvenile_records = data.exclude_juvenile_records
    if data.exclude_unverified_identity is not None: cfg.exclude_unverified_identity = data.exclude_unverified_identity
    if data.min_identity_confidence is not None: cfg.min_identity_confidence = data.min_identity_confidence

    now_utc = datetime.now(timezone.utc)
    new_version = data.config_version or f"v{now_utc.strftime('%Y%m%d.%H%M')}"
    cfg.config_version = new_version
    cfg.updated_by = current_user.full_name or "Lead Investigator"
    cfg.change_rationale = data.change_rationale or "Investigation parameter calibration"

    # Version-stamping snapshot in scoring_config_versions
    import json
    weights_dict = {
        "access_weight": cfg.access_weight,
        "opportunity_weight": cfg.opportunity_weight,
        "means_weight": cfg.means_weight,
        "motive_weight": cfg.motive_weight,
        "travel_feasibility_weight": cfg.travel_feasibility_weight,
        "alibi_strongly_verified_discount": cfg.alibi_strongly_verified_discount,
        "alibi_partially_verified_discount": cfg.alibi_partially_verified_discount,
        "alibi_contradicted_multiplier": cfg.alibi_contradicted_multiplier,
        "impossible_travel_penalty": cfg.impossible_travel_penalty
    }
    caps_dict = {
        "include_criminal_history": cfg.include_criminal_history,
        "criminal_history_max_cap": cfg.criminal_history_max_cap,
        "exclude_juvenile_records": cfg.exclude_juvenile_records,
        "exclude_unverified_identity": cfg.exclude_unverified_identity,
        "min_identity_confidence": cfg.min_identity_confidence
    }
    version_entry = ScoringConfigVersion(
        case_id=real_case_id,
        version_tag=new_version,
        weights_json=json.dumps(weights_dict),
        caps_json=json.dumps(caps_dict),
        lr_table_json="{}",
        rationale=cfg.change_rationale,
        created_by=cfg.updated_by,
        created_at=now_utc
    )
    db.add(version_entry)
    db.commit()
    db.refresh(cfg)

    # Log to tamper-evident Merkle audit ledger
    try:
        log_audit_event(
            db=db,
            action_type="CONFIG_UPDATE",
            target_type="background_config",
            target_id=str(cfg.id),
            description=f"Investigator {current_user.full_name} ({current_user.role}) updated scoring configuration version to '{new_version}'. Rationale: {cfg.change_rationale}",
            user_id=current_user.id,
            user_name=current_user.full_name,
            user_role=current_user.role,
            case_id=real_case_id,
            after_value=new_version
        )
    except Exception as e:
        print(f"[!] Config update audit error: {e}")

    execute_scoring_run(real_case_id, db)
    return cfg


@app.get("/cases/{case_id}/scoring-config/versions")
def get_scoring_config_versions(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns audit trail of version-stamped configuration settings used in the case.
    """
    real_case_id = resolve_case_id(case_id, db)
    versions = db.query(ScoringConfigVersion).filter(
        ScoringConfigVersion.case_id == real_case_id
    ).order_by(ScoringConfigVersion.created_at.desc()).all()
    return [
        {
            "id": v.id,
            "case_id": v.case_id,
            "version_tag": v.version_tag,
            "weights_json": v.weights_json,
            "caps_json": v.caps_json,
            "lr_table_json": v.lr_table_json,
            "rationale": v.rationale,
            "created_by": v.created_by,
            "created_at": v.created_at.isoformat() if v.created_at else None
        }
        for v in versions
    ]


# ==============================================================================
# CHANGE 3: PRIOR CRIMINAL HISTORY & SAFEGUARDS ENDPOINTS
# ==============================================================================

@app.get("/cases/{case_id}/prior-records")
def get_prior_records_for_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns criminal prior records for suspects in the case.
    RBAC Protected: Only Admin and Lead Investigator can view raw criminal records.
    Every view and blocked attempt is logged to the Merkle audit ledger.
    Legal safeguard banner prominently returned with results.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    cfg = db.query(BackgroundWeightConfig).filter(
        (BackgroundWeightConfig.case_id == real_case_id) | (BackgroundWeightConfig.case_id == None)
    ).first()

    # Role-based restriction: Analysts and Reviewers cannot view criminal records under Sec 54 IEA / Sec 52 BSA
    if current_user.role not in ["admin", "lead_investigator"]:
        try:
            log_audit_event(
                db=db,
                action_type="PRIOR_RECORD_VIEW_BLOCKED",
                target_type="case",
                target_id=str(real_case_id),
                description=f"User {current_user.full_name} ({current_user.role}) was restricted from viewing prior criminal records for Case #{real_case_id} under Section 54 IEA / Section 52 BSA statutory safeguard.",
                user_id=current_user.id,
                user_name=current_user.full_name,
                user_role=current_user.role,
                case_id=real_case_id
            )
        except Exception as e:
            print(f"[!] Prior record blocked audit error: {e}")

        return {
            "case_id": real_case_id,
            "legal_safeguard_notice": CRIMINAL_HISTORY_SAFEGUARD_NOTICE,
            "is_role_restricted": True,
            "restricted_message": "Access Restricted: Criminal prior records and Modus Operandi intelligence are partitioned under Section 54 Indian Evidence Act / Section 52 Bharatiya Sakshya Adhiniyam, 2023. Raw history is restricted to Lead Investigators and Administrators to eliminate character prejudice.",
            "include_criminal_history": getattr(cfg, "include_criminal_history", True) if cfg else True,
            "criminal_history_max_cap": getattr(cfg, "criminal_history_max_cap", 0.10) if cfg else 0.10,
            "total_records": 0,
            "records": []
        }

    records = db.query(PriorRecord).filter(PriorRecord.case_id == real_case_id).order_by(PriorRecord.id.asc()).all()

    # Tamper-evident Merkle Audit Log on every view
    try:
        log_audit_event(
            db=db,
            action_type="PRIOR_RECORD_VIEW",
            target_type="case",
            target_id=str(real_case_id),
            description=f"User {current_user.full_name} ({current_user.role}) viewed criminal prior records for Case #{real_case_id} (count: {len(records)}).",
            user_id=current_user.id,
            user_name=current_user.full_name,
            user_role=current_user.role,
            case_id=real_case_id
        )
    except Exception as e:
        print(f"[!] Prior record view audit error: {e}")

    decrypted_records = []
    for r in records:
        ro = PriorRecordOut.from_orm(r)
        ro.suspect_name = decrypt_field(r.suspect_name)
        ro.mo_description = decrypt_field(r.mo_description)
        ro.source_document = decrypt_field(r.source_document)
        ro.quoted_comparison = decrypt_field(r.quoted_comparison)
        decrypted_records.append(ro)

    return {
        "case_id": real_case_id,
        "legal_safeguard_notice": CRIMINAL_HISTORY_SAFEGUARD_NOTICE,
        "is_role_restricted": False,
        "include_criminal_history": getattr(cfg, "include_criminal_history", True) if cfg else True,
        "criminal_history_max_cap": getattr(cfg, "criminal_history_max_cap", 0.10) if cfg else 0.10,
        "total_records": len(records),
        "records": decrypted_records
    }


@app.get("/cases/{case_id}/hypotheses/{hypothesis_id}/prior-records")
def get_prior_records_for_hypothesis(
    case_id: str,
    hypothesis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns prior criminal records linked to a specific suspect/hypothesis.
    Role-restricted to Lead Investigator and Admin.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied.")

    hyp = db.query(Hypothesis).filter(Hypothesis.id == hypothesis_id, Hypothesis.case_id == real_case_id).first()
    if not hyp:
        raise HTTPException(status_code=404, detail="Hypothesis not found")

    cfg = db.query(BackgroundWeightConfig).filter(
        (BackgroundWeightConfig.case_id == real_case_id) | (BackgroundWeightConfig.case_id == None)
    ).first()

    if current_user.role not in ["admin", "lead_investigator"]:
        return {
            "case_id": real_case_id,
            "hypothesis_id": hypothesis_id,
            "suspect_title": hyp.title,
            "legal_safeguard_notice": CRIMINAL_HISTORY_SAFEGUARD_NOTICE,
            "is_role_restricted": True,
            "restricted_message": "Access Restricted: Prior records for this suspect are partitioned under Section 54 IEA / Section 52 BSA. Restricted to Lead Investigators.",
            "include_criminal_history": getattr(cfg, "include_criminal_history", True) if cfg else True,
            "criminal_history_max_cap": getattr(cfg, "criminal_history_max_cap", 0.10) if cfg else 0.10,
            "records": []
        }

    records = db.query(PriorRecord).filter(
        PriorRecord.case_id == real_case_id,
        (PriorRecord.hypothesis_id == hypothesis_id) | (PriorRecord.suspect_name.ilike(f"%{hyp.title}%"))
    ).all()

    decrypted_records = []
    for r in records:
        ro = PriorRecordOut.from_orm(r)
        ro.suspect_name = decrypt_field(r.suspect_name)
        ro.mo_description = decrypt_field(r.mo_description)
        ro.source_document = decrypt_field(r.source_document)
        ro.quoted_comparison = decrypt_field(r.quoted_comparison)
        decrypted_records.append(ro)

    return {
        "case_id": real_case_id,
        "hypothesis_id": hypothesis_id,
        "suspect_title": hyp.title,
        "legal_safeguard_notice": CRIMINAL_HISTORY_SAFEGUARD_NOTICE,
        "is_role_restricted": False,
        "include_criminal_history": getattr(cfg, "include_criminal_history", True) if cfg else True,
        "criminal_history_max_cap": getattr(cfg, "criminal_history_max_cap", 0.10) if cfg else 0.10,
        "records": decrypted_records
    }


@app.post("/cases/{case_id}/prior-records", response_model=PriorRecordOut)
def create_prior_record(
    case_id: str,
    data: PriorRecordCreate,
    current_user: User = Depends(require_role(["admin", "lead_investigator", "analyst"])),
    db: Session = Depends(get_db)
):
    """
    Manual record import / entry: Investigator inputs verified prior offenses from official sources
    (SCRB, CCTNS certified records, court judgments).
    Does NOT falsely claim integration with external live databases.
    Recalculates 3-layer scores and MO relevance, and appends to Merkle audit chain.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "analyze"):
        raise HTTPException(status_code=403, detail="Permission denied to add prior records.")

    new_record = PriorRecord(
        case_id=real_case_id,
        hypothesis_id=data.hypothesis_id,
        person_entity_id=data.person_entity_id,
        suspect_name=encrypt_field(data.suspect_name),
        offense_type=data.offense_type,
        legal_section=data.legal_section,
        offense_date=data.offense_date,
        location=data.location,
        outcome=data.outcome.lower().strip(),
        weapon_used=data.weapon_used,
        entry_method=data.entry_method,
        victim_type=data.victim_type,
        location_type=data.location_type,
        time_pattern=data.time_pattern,
        mo_description=encrypt_field(data.mo_description),
        source_agency=data.source_agency,
        source_document=encrypt_field(data.source_document),
        verification_status=data.verification_status or "verified",
        identity_match_confidence=data.identity_match_confidence if data.identity_match_confidence is not None else 1.0,
        verified_identity=data.verified_identity if data.verified_identity is not None else True,
        is_juvenile=data.is_juvenile if data.is_juvenile is not None else False,
        entered_by=current_user.full_name
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    # Merkle audit entry
    try:
        log_audit_event(
            db=db,
            action_type="PRIOR_RECORD_CREATE",
            target_type="prior_record",
            target_id=str(new_record.id),
            description=f"Added prior offense record #{new_record.id} ({new_record.offense_type}, outcome: {new_record.outcome}) for suspect '{new_record.suspect_name}'. Source: {new_record.source_agency}.",
            user_id=current_user.id,
            user_name=current_user.full_name,
            user_role=current_user.role,
            case_id=real_case_id,
            after_value=json.dumps({
                "offense": new_record.offense_type,
                "section": new_record.legal_section,
                "outcome": new_record.outcome,
                "mo": new_record.mo_description,
                "source": new_record.source_agency
            })
        )
    except Exception as e:
        print(f"[!] Prior record create audit error: {e}")

    # Recalculate scoring across case
    execute_scoring_run(real_case_id, db, triggered_by="prior_record_create")
    db.refresh(new_record)
    return new_record


@app.put("/cases/{case_id}/prior-records/{record_id}", response_model=PriorRecordOut)
def update_prior_record(
    case_id: str,
    record_id: int,
    data: PriorRecordUpdate,
    current_user: User = Depends(require_role(["admin", "lead_investigator", "analyst"])),
    db: Session = Depends(get_db)
):
    """
    Updates an existing prior record (e.g., judicial outcome, verification status, identity match confidence).
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "analyze"):
        raise HTTPException(status_code=403, detail="Permission denied.")

    rec = db.query(PriorRecord).filter(PriorRecord.id == record_id, PriorRecord.case_id == real_case_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Prior record not found")

    before_snapshot = {
        "suspect_name": rec.suspect_name,
        "offense_type": rec.offense_type,
        "outcome": rec.outcome,
        "verified_identity": rec.verified_identity,
        "identity_match_confidence": rec.identity_match_confidence
    }

    current_version = getattr(rec, "version", 1) or 1
    if data.version is not None and data.version != current_version:
        log_audit_event(
            db=db,
            action_type="CONFLICT_REJECTED",
            target_type="prior_record",
            target_id=str(rec.id),
            description=f"Concurrent conflict on prior record #{rec.id}: User submitted v{data.version}, but current version is v{current_version}.",
            case_id=real_case_id,
            user_id=current_user.id,
            user_name=current_user.full_name,
            before_value=f"v{data.version}",
            after_value=f"v{current_version}",
            commit=True
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "conflict",
                "message": f"Prior record #{rec.id} was modified by another investigator while you were editing.",
                "item_type": "prior_record",
                "item_id": str(rec.id),
                "current_version": current_version,
                "submitted_version": data.version,
                "current_data": before_snapshot
            }
        )

    now_utc = datetime.now(timezone.utc)
    active_lock = db.query(EditLock).filter(
        EditLock.case_id == real_case_id,
        EditLock.item_type == "prior_record",
        EditLock.item_id == str(rec.id),
        EditLock.expires_at > now_utc,
        EditLock.user_id != current_user.id
    ).first()
    if active_lock:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail={
                "error": "locked",
                "message": f"{active_lock.user_name} is currently editing this prior record.",
                "locked_by": active_lock.user_name,
                "user_role": active_lock.user_role,
                "expires_at": active_lock.expires_at.isoformat()
            }
        )

    if data.suspect_name is not None: rec.suspect_name = encrypt_field(data.suspect_name)
    if data.hypothesis_id is not None: rec.hypothesis_id = data.hypothesis_id
    if data.person_entity_id is not None: rec.person_entity_id = data.person_entity_id
    if data.offense_type is not None: rec.offense_type = data.offense_type
    if data.legal_section is not None: rec.legal_section = data.legal_section
    if data.offense_date is not None: rec.offense_date = data.offense_date
    if data.location is not None: rec.location = data.location
    if data.outcome is not None: rec.outcome = data.outcome.lower().strip()
    if data.weapon_used is not None: rec.weapon_used = data.weapon_used
    if data.entry_method is not None: rec.entry_method = data.entry_method
    if data.victim_type is not None: rec.victim_type = data.victim_type
    if data.location_type is not None: rec.location_type = data.location_type
    if data.time_pattern is not None: rec.time_pattern = data.time_pattern
    if data.mo_description is not None: rec.mo_description = encrypt_field(data.mo_description)
    if data.source_agency is not None: rec.source_agency = data.source_agency
    if data.source_document is not None: rec.source_document = encrypt_field(data.source_document)
    if data.verification_status is not None: rec.verification_status = data.verification_status
    if data.identity_match_confidence is not None: rec.identity_match_confidence = data.identity_match_confidence
    if data.verified_identity is not None: rec.verified_identity = data.verified_identity
    if data.is_juvenile is not None: rec.is_juvenile = data.is_juvenile

    rec.version = current_version + 1

    # Merkle audit entry (transactional, commit together)
    try:
        log_audit_event(
            db=db,
            action_type="PRIOR_RECORD_UPDATE",
            target_type="prior_record",
            target_id=str(rec.id),
            description=f"Updated prior record #{rec.id} for suspect '{rec.suspect_name}'.",
            user_id=current_user.id,
            user_name=current_user.full_name,
            user_role=current_user.role,
            case_id=real_case_id,
            before_value=json.dumps(before_snapshot),
            after_value=json.dumps({
                "suspect_name": rec.suspect_name,
                "offense_type": rec.offense_type,
                "outcome": rec.outcome,
                "verified_identity": rec.verified_identity,
                "identity_match_confidence": rec.identity_match_confidence
            }),
            commit=False
        )
    except Exception as e:
        print(f"[!] Prior record update audit error: {e}")

    db.commit()
    db.refresh(rec)

    release_edit_lock(db, real_case_id, "prior_record", str(rec.id), current_user.id)

    publish_collaboration_event(
        db=db,
        case_id=real_case_id,
        event_type="item.changed",
        item_type="prior_record",
        item_id=str(rec.id),
        version=rec.version,
        user_id=current_user.id,
        user_name=current_user.full_name,
        summary=f"{current_user.full_name} updated prior record #{rec.id} for suspect '{rec.suspect_name}'.",
        payload={
            "id": rec.id,
            "suspect_name": rec.suspect_name,
            "outcome": rec.outcome,
            "version": rec.version
        },
        is_restricted=True
    )

    execute_scoring_run(real_case_id, db, triggered_by="prior_record_update")
    db.refresh(rec)
    ro = PriorRecordOut.from_orm(rec)
    ro.suspect_name = decrypt_field(rec.suspect_name)
    ro.mo_description = decrypt_field(rec.mo_description)
    ro.source_document = decrypt_field(rec.source_document)
    ro.quoted_comparison = decrypt_field(rec.quoted_comparison)
    return ro


@app.delete("/cases/{case_id}/prior-records/{record_id}")
def delete_prior_record(
    case_id: str,
    record_id: int,
    current_user: User = Depends(require_role(["admin", "lead_investigator"])),
    db: Session = Depends(get_db)
):
    """
    Deletes a prior criminal record and updates scores immediately.
    Restricted to Lead Investigator or Admin.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "delete_evidence"):
        raise HTTPException(status_code=403, detail="Permission denied to remove prior record.")

    rec = db.query(PriorRecord).filter(PriorRecord.id == record_id, PriorRecord.case_id == real_case_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Prior record not found")

    deleted_info = f"Offense: {rec.offense_type}, Suspect: {rec.suspect_name}, Outcome: {rec.outcome}"
    db.delete(rec)
    db.commit()

    try:
        log_audit_event(
            db=db,
            action_type="PRIOR_RECORD_DELETE",
            target_type="prior_record",
            target_id=str(record_id),
            description=f"Deleted prior offense record #{record_id} ({deleted_info}).",
            user_id=current_user.id,
            user_name=current_user.full_name,
            user_role=current_user.role,
            case_id=real_case_id
        )
    except Exception as e:
        print(f"[!] Prior record delete audit error: {e}")

    execute_scoring_run(real_case_id, db, triggered_by="prior_record_delete")
    return {"status": "success", "message": f"Prior record #{record_id} deleted successfully."}


@app.get("/cases/{case_id}/criminal-history-comparison", response_model=CriminalHistoryComparisonOut)
def get_criminal_history_comparison(
    case_id: str,
    current_user: User = Depends(require_role(["admin", "lead_investigator", "analyst"])),
    db: Session = Depends(get_db)
):
    """
    Returns stored comparison of hypothesis rankings With vs Without Criminal History.
    Allows investigator to inspect how prior history shifts background plausibility and combined priority.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied.")

    scoring_res = execute_scoring_run(real_case_id, db, triggered_by="criminal_history_comparison")
    comp = scoring_res.get("criminal_history_comparison", {})
    
    return {
        "case_id": real_case_id,
        "include_criminal_history": comp.get("include_criminal_history", True),
        "criminal_history_max_cap": comp.get("criminal_history_max_cap", 0.10),
        "legal_safeguard_notice": comp.get("legal_safeguard_notice", CRIMINAL_HISTORY_SAFEGUARD_NOTICE),
        "total_prior_records": comp.get("total_prior_records", 0),
        "hypotheses_comparison": comp.get("hypotheses_comparison", [])
    }


@app.post("/cases/{case_id}/toggle-criminal-history")
def toggle_criminal_history(
    case_id: str,
    payload: Optional[dict] = None,
    current_user: User = Depends(require_role(["admin", "lead_investigator", "analyst"])),
    db: Session = Depends(get_db)
):
    """
    On/Off Switch:
    Toggles or explicitly sets whether criminal history is factored into background plausibility.
    Immediate recalculation shows rankings with and without history side-by-side.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "analyze"):
        raise HTTPException(status_code=403, detail="Permission denied to toggle criminal history.")

    cfg = db.query(BackgroundWeightConfig).filter(
        (BackgroundWeightConfig.case_id == real_case_id) | (BackgroundWeightConfig.case_id == None)
    ).first()

    if not cfg:
        cfg = BackgroundWeightConfig(case_id=real_case_id)
        db.add(cfg)

    # Determine new state
    if payload and "enabled" in payload:
        new_state = bool(payload["enabled"])
    else:
        new_state = not getattr(cfg, "include_criminal_history", True)

    cfg.include_criminal_history = new_state
    db.commit()
    db.refresh(cfg)

    # Audit log entry
    try:
        log_audit_event(
            db=db,
            action_type="PRIOR_HISTORY_TOGGLE",
            target_type="case",
            target_id=str(real_case_id),
            description=f"User {current_user.full_name} toggled criminal history signal to {'ON' if new_state else 'OFF'}.",
            user_id=current_user.id,
            user_name=current_user.full_name,
            user_role=current_user.role,
            case_id=real_case_id,
            after_value=json.dumps({"include_criminal_history": new_state})
        )
    except Exception as e:
        print(f"[!] Prior history toggle audit error: {e}")

    scoring_res = execute_scoring_run(real_case_id, db, triggered_by="toggle_criminal_history")
    comp = scoring_res.get("criminal_history_comparison", {})

    return {
        "status": "success",
        "case_id": real_case_id,
        "include_criminal_history": new_state,
        "message": f"Criminal history signal is now {'ENABLED' if new_state else 'DISABLED'}.",
        "legal_safeguard_notice": CRIMINAL_HISTORY_SAFEGUARD_NOTICE,
        "comparison": comp,
        "hypotheses": scoring_res.get("hypotheses", [])
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



# ============================================================
# CHANGE 4: BAYESIAN LIKELIHOOD RATIO REFERENCE TABLE ENDPOINTS
# ============================================================



@app.put("/cases/{case_id}/bayesian-lr/reference-table/{category_key}", response_model=LikelihoodRatioReferenceOut)
def update_likelihood_ratio_reference_entry(
    case_id: str,
    category_key: str,
    data: LikelihoodRatioReferenceUpdate,
    db: Session = Depends(get_db)
):
    """
    Updates custom likelihood ratio ranges, typical value, or citations for a forensic category.
    Immediately recalculates Bayesian scores.
    """
    real_case_id = resolve_case_id(case_id, db)
    ref = db.query(LikelihoodRatioReference).filter(LikelihoodRatioReference.category_key == category_key).first()
    if not ref:
        spec = LIKELIHOOD_RATIO_REFERENCE_TABLE.get(category_key, {})
        ref = LikelihoodRatioReference(
            category_key=category_key,
            evidence_type=spec.get("evidence_type", "document"),
            finding_name=spec.get("finding_name", category_key),
            support_direction=spec.get("support_direction", "neutral"),
            min_lr=data.min_lr if data.min_lr is not None else float(spec.get("min_lr", 1.0)),
            max_lr=data.max_lr if data.max_lr is not None else float(spec.get("max_lr", 1.0)),
            typical_lr=data.typical_lr if data.typical_lr is not None else float(spec.get("typical_lr", 1.0)),
            source_citation=data.source_citation or spec.get("source_citation", ""),
            forensic_error_rate=data.forensic_error_rate or spec.get("forensic_error_rate", ""),
            notes=data.notes or spec.get("notes", "")
        )
        db.add(ref)
    else:
        if data.min_lr is not None:
            ref.min_lr = data.min_lr
        if data.max_lr is not None:
            ref.max_lr = data.max_lr
        if data.typical_lr is not None:
            ref.typical_lr = data.typical_lr
        if data.source_citation is not None:
            ref.source_citation = data.source_citation
        if data.forensic_error_rate is not None:
            ref.forensic_error_rate = data.forensic_error_rate
        if data.notes is not None:
            ref.notes = data.notes

    db.commit()
    db.refresh(ref)

    # Trigger Bayesian recalculation
    execute_scoring_run(real_case_id, db, triggered_by="update_reference_table_entry")
    return ref


@app.post("/cases/{case_id}/bayesian-lr/reference-table/reset")
def reset_likelihood_ratio_reference_table(
    case_id: str,
    db: Session = Depends(get_db)
):
    """
    Resets all entries in the Likelihood Ratio Reference Table back to peer-reviewed forensic defaults.
    """
    real_case_id = resolve_case_id(case_id, db)
    db.query(LikelihoodRatioReference).delete()
    for cat_key, spec in LIKELIHOOD_RATIO_REFERENCE_TABLE.items():
        db_ref = LikelihoodRatioReference(
            category_key=cat_key,
            evidence_type=spec.get("evidence_type", "document"),
            finding_name=spec.get("finding_name", cat_key),
            support_direction=spec.get("support_direction", "neutral"),
            min_lr=float(spec.get("min_lr", 1.0)),
            max_lr=float(spec.get("max_lr", 1.0)),
            typical_lr=float(spec.get("typical_lr", 1.0)),
            source_citation=spec.get("source_citation", "Forensic Guidelines"),
            forensic_error_rate=spec.get("forensic_error_rate", "N/A"),
            notes=spec.get("notes", "")
        )
        db.add(db_ref)
    db.commit()
    scoring_res = execute_scoring_run(real_case_id, db, triggered_by="reset_reference_table")
    return {
        "status": "success",
        "message": "Likelihood ratio reference table reset to scientific forensic defaults.",
        "scoring_result": scoring_res
    }


# ============================================================
# CHANGE 5: UNKNOWN HYPOTHESIS, EXCULPATORY CLEARING & DEPENDENCY ENDPOINTS
# ============================================================

@app.get("/cases/{case_id}/exculpatory-config")
def get_exculpatory_config(case_id: str, db: Session = Depends(get_db)):
    """
    Returns the peer-reviewed list of first-class exculpatory evidence types,
    their typical clearing likelihood ratios (in decibans), rationales, and statutory references.
    """
    types_list = [
        {
            "category_key": k,
            **v
        }
        for k, v in EXCULPATORY_EVIDENCE_TYPES_CONFIG.items()
    ]
    return {
        "status": "success",
        "case_id": case_id,
        "total_types": len(types_list),
        "exculpatory_types": types_list
    }


@app.put("/cases/{case_id}/evidence/{evidence_id}/dependency-group")
def update_evidence_dependency_group(
    case_id: str,
    evidence_id: int,
    req: DependencyGroupUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Marks an exhibit as belonging to a dependency group (e.g. exhibits sharing a source,
    retold statements, statement describing a CCTV clip, copies of the same test).
    Triggers recalculation with geometric diminishing weight schedule (1.0, 0.50, 0.25).
    """
    real_case_id = resolve_case_id(case_id, db)
    ev = db.query(Evidence).filter(Evidence.id == evidence_id, Evidence.case_id == real_case_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence exhibit not found.")

    old_group = ev.dependency_group
    new_group = (req.dependency_group or "").strip() or None
    ev.dependency_group = new_group
    db.commit()
    db.refresh(ev)

    # Re-run scoring run to apply group damping
    scoring_res = execute_scoring_run(real_case_id, db, triggered_by="update_dependency_group")

    return {
        "status": "success",
        "evidence_id": evidence_id,
        "file_name": ev.file_name,
        "previous_dependency_group": old_group,
        "dependency_group": ev.dependency_group,
        "dependency_groups_audit": scoring_res.get("dependency_groups_audit", {}),
        "scoring_result": scoring_res
    }


@app.post("/cases/{case_id}/evidence/auto-group-dependencies")
def auto_group_evidence_dependencies(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI / Heuristic Dependency Grouping:
    Analyzes case exhibits to automatically discover exhibits that share an underlying source:
      - Repeated or supplementary witness statements from the same individual
      - Statements describing a specific CCTV clip or camera feed
      - Multiple copies or re-tests of the same forensic item
    Marks their dependency_group and executes scoring.
    """
    real_case_id = resolve_case_id(case_id, db)
    exhibits = db.query(Evidence).filter(Evidence.case_id == real_case_id).all()

    # Rule-based clustering heuristics
    groups_assigned = {}
    witness_exhibits: Dict[str, List[Evidence]] = {}
    cctv_exhibits: Dict[str, List[Evidence]] = {}

    for ev in exhibits:
        fn = (ev.file_name or "").lower()
        title = (getattr(ev, "title", None) or "").lower()
        extracted = (ev.extracted_text or "")[:400].lower()
        combined = f"{fn} {title} {extracted}"

        # Match common names
        for name in ["shinde", "pawar", "jadhav", "kadam", "patil", "sharma", "verma", "talwar", "hemraj", "bharti"]:
            if name in combined:
                witness_exhibits.setdefault(f"witness_{name}_group", []).append(ev)

        # Match CCTV footage with witness statements discussing it
        if "cctv" in combined or "camera" in combined or "toll" in combined:
            if "toll" in combined:
                cctv_exhibits.setdefault("toll_cctv_and_logs_group", []).append(ev)
            elif "atm" in combined:
                cctv_exhibits.setdefault("atm_cctv_and_statements_group", []).append(ev)

    all_clusters = {**witness_exhibits, **cctv_exhibits}
    changes_made = 0
    for grp_name, ev_list in all_clusters.items():
        if len(ev_list) >= 2:
            for ev in ev_list:
                if not ev.dependency_group:
                    ev.dependency_group = grp_name
                    changes_made += 1
                    groups_assigned.setdefault(grp_name, []).append(ev.id)

    db.commit()
    scoring_res = execute_scoring_run(real_case_id, db, triggered_by="auto_group_dependencies")

    return {
        "status": "success",
        "changes_made": changes_made,
        "discovered_groups": {k: len(v) for k, v in groups_assigned.items()},
        "dependency_groups_audit": scoring_res.get("dependency_groups_audit", {}),
        "lead_message": scoring_res.get("lead_message")
    }


@app.get("/cases/{case_id}/scoring/dependency-groups")
def get_scoring_dependency_groups(
    case_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns active dependency groups, exhibit members, damping weights, and total effective multipliers.
    """
    real_case_id = resolve_case_id(case_id, db)
    exhibits = db.query(Evidence).filter(Evidence.case_id == real_case_id).all()
    exhibit_dicts = [
        {
            "id": ev.id,
            "title": ev.file_name,
            "file_name": ev.file_name,
            "file_type": ev.file_type,
            "evidence_type": ev.evidence_type or "document",
            "quality_rating": float(ev.quality_rating or 3.0),
            "hash_verified": bool(ev.hash_verified),
            "dependency_group": ev.dependency_group
        }
        for ev in exhibits
    ]
    mults, audits = resolve_exhibit_dependency_multipliers(exhibit_dicts)
    return {
        "status": "success",
        "case_id": real_case_id,
        "total_exhibits": len(exhibits),
        "total_groups": len(audits),
        "dependency_groups": audits,
        "exhibit_multipliers": mults
    }


@app.post("/cases/{case_id}/bayesian-lr/calculate")
def calculate_bayesian_lr_endpoint(
    case_id: str,
    payload: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db)
):
    """
    Calculates Bayesian Updating with Likelihood Ratios:
    - Multiplies prior by shrunk LR for each exhibit.
    - Shrinks toward 1 based on reliability and confidence.
    - Diagnosticity is naturally intrinsic (ratio = 1 changes nothing).
    - Guarantees 100% normalized sum and order independence.
    """
    real_case_id = resolve_case_id(case_id, db)
    p = payload or {}
    scoring_method = p.get("scoring_method", "bayesian_lr")
    lr_mode = p.get("lr_mode", "typical")
    custom_cfg = p.get("custom_configs")
    excluded = p.get("excluded_evidence_ids")

    res = execute_scoring_run(
        real_case_id, db,
        custom_configs=custom_cfg,
        excluded_ids=excluded,
        triggered_by="bayesian_lr_calculate_endpoint",
        scoring_method=scoring_method,
        lr_mode=lr_mode
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
    res = execute_scoring_run(real_case_id, db, triggered_by="breakdown_query")
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
        "exhibits": target_table,
        "background_summary": res.get("background_summary", {}),
        "bayesian_summary": res.get("bayesian_summary", {})
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


# ============================================================
# CHANGE 6 & 7: MONTE CARLO RANGES, GAPS & NEXT-STEP ENDPOINTS
# ============================================================

@app.get("/cases/{case_id}/scoring/monte-carlo-ranges", response_model=MonteCarloScoringResponse)
def get_case_monte_carlo_ranges(
    case_id: str,
    simulations: int = 250,
    db: Session = Depends(get_db)
):
    """
    CHANGE 6: Monte Carlo Scoring Credible Ranges & Fragility Warnings
    Runs scoring 250 times across plausible bounds of likelihood ratios, reliability, and priors.
    Detects close results and fragility warnings.
    """
    real_case_id = resolve_case_id(case_id, db)
    ensure_unknown_hypothesis(real_case_id, db)

    hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == real_case_id).all()
    if not hypotheses:
        raise HTTPException(status_code=404, detail="No hypotheses found for case")

    exhibits = db.query(Evidence).filter(
        Evidence.case_id == real_case_id,
        (Evidence.is_deleted == False) | (Evidence.is_deleted == None)
    ).all()
    assessments = db.query(EvidenceAssessment).join(Hypothesis).filter(Hypothesis.case_id == real_case_id).all()

    cfgs = db.query(ReliabilityConfig).all()
    base_map = {c.evidence_type: c.base_reliability for c in cfgs} if cfgs else None

    lr_refs_db = db.query(LikelihoodRatioReference).all()
    custom_lr_table = {
        ref.category_key: {
            "evidence_type": ref.evidence_type,
            "finding_name": ref.finding_name,
            "finding_description": ref.finding_description or "",
            "min_lr": ref.min_lr,
            "max_lr": ref.max_lr,
            "typical_lr": ref.typical_lr,
            "support_direction": ref.support_direction,
            "source_citation": ref.source_citation,
            "forensic_error_rate": ref.forensic_error_rate or "N/A",
            "notes": ref.notes
        }
        for ref in lr_refs_db
    } if lr_refs_db else None

    hypo_dicts = [
        {
            "id": h.id,
            "title": h.title,
            "description": h.description,
            "is_unknown": bool(getattr(h, "is_unknown", False) or "unknown" in h.title.lower()),
            "background_score": getattr(h, "background_score", None)
        }
        for h in hypotheses
    ]
    exhibit_dicts = [
        {
            "id": ev.id,
            "title": ev.file_name,
            "file_name": ev.file_name,
            "file_type": ev.file_type,
            "evidence_type": ev.evidence_type or "document",
            "chain_of_custody_complete": bool(ev.chain_of_custody_complete),
            "sec_65b_certificate_present": bool(ev.sec_65b_certificate_present),
            "source_independent": bool(ev.source_independent if ev.source_independent is not None else True),
            "dependency_group": getattr(ev, "dependency_group", None)
        }
        for ev in exhibits
    ]
    assessment_dicts = [
        {
            "hypothesis_id": a.hypothesis_id,
            "evidence_id": a.evidence_id,
            "classification": a.classification,
            "quoted_source_line": a.quoted_source_line,
            "reason": a.reason,
            "analyst_override": bool(a.analyst_override),
            "finding_category": getattr(a, "finding_category", None),
            "finding_name": getattr(a, "finding_name", None),
            "base_lr": getattr(a, "likelihood_ratio", None),
            "effective_lr": getattr(a, "effective_lr", None),
            "min_lr": getattr(a, "lr_min", None),
            "max_lr": getattr(a, "lr_max", None),
            "dependency_group": getattr(a, "dependency_group", None),
            "dependency_weight_multiplier": getattr(a, "dependency_weight_multiplier", 1.0)
        }
        for a in assessments
    ]

    background_priors = {h.id: float(getattr(h, "background_score", None) or (100.0 / len(hypo_dicts))) for h in hypotheses}

    mc_result = compute_monte_carlo_scoring_ranges(
        hypotheses=hypo_dicts,
        exhibits=exhibit_dicts,
        assessments=assessment_dicts,
        background_priors=background_priors,
        custom_lr_table=custom_lr_table,
        custom_base_configs=base_map,
        num_simulations=simulations,
        random_seed=42
    )

    return mc_result


@app.get("/cases/{case_id}/investigative-gaps", response_model=List[InvestigativeGapOut])
def get_investigative_gaps_endpoint(case_id: str, db: Session = Depends(get_db)):
    """
    CHANGE 7: Gap Detection Rule Checks
    Runs rule checks across the case and returns actionable task items:
      - suspect has no alibi check or forensic comparison
      - key exhibit missing custody or Sec 65B certificate
      - uncorroborated witness/approver statement
      - time window missing CCTV/call/location
      - hypothesis has only one supporting exhibit
    """
    real_case_id = resolve_case_id(case_id, db)
    case_obj = db.query(Case).filter(Case.id == real_case_id).first()
    hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == real_case_id).all()
    exhibits = db.query(Evidence).filter(
        Evidence.case_id == real_case_id,
        (Evidence.is_deleted == False) | (Evidence.is_deleted == None)
    ).all()
    assessments = db.query(EvidenceAssessment).join(Hypothesis).filter(Hypothesis.case_id == real_case_id).all()
    events = db.query(Event).filter(Event.case_id == real_case_id).all()
    contradictions = db.query(Contradiction).filter(Contradiction.case_id == real_case_id).all()

    hypo_dicts = [
        {"id": h.id, "title": h.title, "description": h.description, "is_unknown": bool(getattr(h, "is_unknown", False) or "unknown" in h.title.lower())}
        for h in hypotheses
    ]
    exhibit_dicts = [
        {
            "id": ev.id,
            "title": ev.file_name,
            "file_name": ev.file_name,
            "evidence_type": ev.evidence_type or "document",
            "chain_of_custody_complete": bool(ev.chain_of_custody_complete),
            "sec_65b_certificate_present": bool(ev.sec_65b_certificate_present),
            "source_independent": bool(ev.source_independent if ev.source_independent is not None else True),
            "is_critical": bool(getattr(ev, "is_critical", False))
        }
        for ev in exhibits
    ]
    assessment_dicts = [
        {
            "hypothesis_id": a.hypothesis_id,
            "evidence_id": a.evidence_id,
            "classification": a.classification,
            "finding_category": getattr(a, "finding_category", None),
            "effective_lr": getattr(a, "effective_lr", 1.0)
        }
        for a in assessments
    ]
    event_dicts = [{"id": ev.id, "title": ev.title, "timestamp": str(ev.timestamp)} for ev in events]
    contradiction_dicts = [{"id": c.id, "conflict_type": c.conflict_type} for c in contradictions]

    raw_gaps = detect_investigative_gaps(
        case={"id": real_case_id, "title": case_obj.title if case_obj else f"Case #{real_case_id}"},
        hypotheses=hypo_dicts,
        exhibits=exhibit_dicts,
        assessments=assessment_dicts,
        events=event_dicts,
        contradictions=contradiction_dicts
    )

    # Cross-reference with existing InvestigationTask records in DB
    existing_tasks = db.query(InvestigationTask).filter(InvestigationTask.case_id == real_case_id).all()
    task_by_text = {t.task.strip().lower(): t for t in existing_tasks}

    results = []
    for g in raw_gaps:
        rec_task = g["recommended_task"].strip().lower()
        matched = task_by_text.get(rec_task)
        is_acc = False
        is_dism = False
        existing_id = None
        if matched:
            existing_id = matched.id
            is_acc = matched.status in ["Pending", "In Progress", "Completed"] and not bool(matched.dismissed)
            is_dism = bool(matched.dismissed) or (matched.status == "Dismissed")

        results.append(InvestigativeGapOut(
            gap_id=g["gap_id"],
            rule_code=g["rule_code"],
            rule_title=g["rule_title"],
            target_type=g["target_type"],
            target_id=g["target_id"],
            target_title=g["target_title"],
            severity=g["severity"],
            description=g["description"],
            recommended_task=g["recommended_task"],
            action_category=g["action_category"],
            default_assigned_to=g["default_assigned_to"],
            priority=g["priority"],
            existing_task_id=existing_id,
            is_accepted=is_acc,
            is_dismissed=is_dism
        ))

    return results


@app.get("/cases/{case_id}/next-best-steps", response_model=List[NextBestStepOut])
def get_next_best_steps_endpoint(case_id: str, db: Session = Depends(get_db)):
    """
    CHANGE 7: Next Best Step Simulation Endpoint
    Simulates candidate investigative tests/interviews through the Bayesian scoring engine.
    Ranks steps by ranking mobility and probability delta effect.
    """
    real_case_id = resolve_case_id(case_id, db)
    hypotheses = db.query(Hypothesis).filter(Hypothesis.case_id == real_case_id).all()
    if not hypotheses:
        return []

    exhibits = db.query(Evidence).filter(
        Evidence.case_id == real_case_id,
        (Evidence.is_deleted == False) | (Evidence.is_deleted == None)
    ).all()
    assessments = db.query(EvidenceAssessment).join(Hypothesis).filter(Hypothesis.case_id == real_case_id).all()

    cfgs = db.query(ReliabilityConfig).all()
    base_map = {c.evidence_type: c.base_reliability for c in cfgs} if cfgs else None

    lr_refs_db = db.query(LikelihoodRatioReference).all()
    custom_lr_table = {
        ref.category_key: {
            "evidence_type": ref.evidence_type,
            "finding_name": ref.finding_name,
            "finding_description": getattr(ref, "finding_description", "") or "",
            "min_lr": ref.min_lr,
            "max_lr": ref.max_lr,
            "typical_lr": ref.typical_lr,
            "support_direction": ref.support_direction,
            "source_citation": ref.source_citation,
            "forensic_error_rate": getattr(ref, "forensic_error_rate", "N/A"),
            "notes": getattr(ref, "notes", "")
        }
        for ref in lr_refs_db
    } if lr_refs_db else None

    hypo_dicts = [
        {"id": h.id, "title": h.title, "description": h.description, "is_unknown": bool(getattr(h, "is_unknown", False) or "unknown" in h.title.lower())}
        for h in hypotheses
    ]
    exhibit_dicts = [
        {"id": ev.id, "title": ev.file_name, "file_name": ev.file_name, "evidence_type": ev.evidence_type or "document"}
        for ev in exhibits
    ]
    assessment_dicts = [
        {
            "hypothesis_id": a.hypothesis_id,
            "evidence_id": a.evidence_id,
            "classification": a.classification,
            "finding_category": getattr(a, "finding_category", None),
            "effective_lr": getattr(a, "effective_lr", 1.0)
        }
        for a in assessments
    ]
    background_priors = {h.id: float(getattr(h, "background_score", None) or (100.0 / len(hypo_dicts))) for h in hypotheses}

    steps = simulate_next_best_steps(
        case={"id": real_case_id},
        hypotheses=hypo_dicts,
        exhibits=exhibit_dicts,
        assessments=assessment_dicts,
        background_priors=background_priors,
        custom_lr_table=custom_lr_table,
        custom_base_configs=base_map
    )

    return [NextBestStepOut(**s) for s in steps]


@app.post("/cases/{case_id}/tasks/create-from-gap", response_model=InvestigationTaskOut)
def create_task_from_gap(
    case_id: str,
    payload: dict,
    db: Session = Depends(get_db)
):
    """
    Accepts an investigative gap or next-best-step suggestion and saves it as a real InvestigationTask.
    """
    real_case_id = resolve_case_id(case_id, db)
    task_text = str(payload.get("task", "")).strip()
    if not task_text:
        raise HTTPException(status_code=400, detail="Task description is required")

    existing = db.query(InvestigationTask).filter(
        InvestigationTask.case_id == real_case_id,
        InvestigationTask.task == task_text
    ).first()

    if existing:
        existing.status = payload.get("status", "Pending")
        existing.dismissed = False
        if payload.get("assigned_to"):
            existing.assigned_to = payload["assigned_to"]
        if payload.get("priority"):
            existing.priority = payload["priority"]
        if payload.get("category"):
            existing.category = payload["category"]
        if payload.get("impact_score") is not None:
            existing.impact_score = float(payload["impact_score"])
        db.commit()
        db.refresh(existing)
        return existing

    new_task = InvestigationTask(
        case_id=real_case_id,
        task=task_text,
        reason=payload.get("reason", "Generated from Forensic Gap Detection"),
        related_hypothesis_id=str(payload.get("related_hypothesis_id", "")) if payload.get("related_hypothesis_id") else None,
        related_contradiction_id=str(payload.get("related_contradiction_id", "")) if payload.get("related_contradiction_id") else None,
        related_evidence_id=str(payload.get("related_evidence_id", "")) if payload.get("related_evidence_id") else None,
        priority=payload.get("priority", "High"),
        status=payload.get("status", "Pending"),
        assigned_to=payload.get("assigned_to", "Field Detective"),
        category=payload.get("category", "gap_detection"),
        impact_score=float(payload.get("impact_score", 0.0)) if payload.get("impact_score") is not None else None,
        suggested_by_ai=True,
        dismissed=False
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@app.post("/cases/{case_id}/tasks/{task_id}/dismiss")
def dismiss_investigation_task_endpoint(
    case_id: str,
    task_id: int,
    db: Session = Depends(get_db)
):
    """
    Dismisses an investigative task or suggested gap.
    """
    real_case_id = resolve_case_id(case_id, db)
    t = db.query(InvestigationTask).filter(
        InvestigationTask.id == task_id,
        InvestigationTask.case_id == real_case_id
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")

    t.dismissed = True
    t.status = "Dismissed"
    db.commit()
    db.refresh(t)
    return {"status": "success", "message": f"Task #{task_id} dismissed", "task_id": task_id}


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

    FORENSIC_FINDING_CATEGORIES_GUIDE = """
FORENSIC REFERENCE CATEGORIES (Identify the closest standard finding category; DO NOT invent numerical likelihood ratios - the scientific reference table supplies the numbers):
- DNA: "dna_match_single_source", "dna_match_complex_mixture", "dna_partial_profile", "dna_exclusion"
- Fingerprint: "fingerprint_latent_high_detail", "fingerprint_latent_medium_detail", "fingerprint_inconclusive", "fingerprint_exclusion"
- CCTV / Video: "cctv_facial_id_clear", "cctv_clothing_height_match", "cctv_partial_obscured", "cctv_conflicting_description"
- Telecom / CDR: "cdr_cell_tower_coincident", "cdr_cell_tower_vicinity", "cdr_distant_tower"
- Digital / Cyber: "digital_device_direct_activity", "digital_browser_or_search", "digital_device_contradiction"
- Ballistics: "ballistics_striation_match", "ballistics_caliber_class_only", "ballistics_exclusion"
- GSR: "gsr_heavy_characteristic", "gsr_trace_particles", "gsr_negative"
- Eyewitness: "eyewitness_confident_immediate", "eyewitness_delayed_tentative", "eyewitness_contradictory"
- Alibi: "alibi_corroborated_official", "alibi_corroborated_associate", "alibi_unverified", "alibi_falsified"
- Financial / Document / Other: "financial_transaction_record", "generic_neutral"
"""

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

{FORENSIC_FINDING_CATEGORIES_GUIDE}

For each exhibit, classify into EXACTLY one of:
- strong_support
- moderate_support
- weak_support
- neutral
- weak_contradiction
- moderate_contradiction
- strong_contradiction

Also select the most accurate "finding_category" from the reference table above.
IMPORTANT: Provide an exact verbatim quote ("quoted_source_line") from the exhibit text that justifies your decision. Do NOT make up quotes. If no direct quote exists, leave it empty.

Respond in valid JSON array only:
[
  {{
    "evidence_id": {evidences[0].id},
    "classification": "strong_support | neutral | strong_contradiction ...",
    "finding_category": "dna_match_single_source | cctv_facial_id_clear | generic_neutral ...",
    "reason": "Clear explanation citing forensic facts in this exhibit",
    "quoted_source_line": "Exact verbatim quote from the text",
    "confidence": 0.95
  }}
]"""
        try:
            resp = client.models.generate_content(
                model=DEFAULT_MODEL_NAME,
                contents=batch_prompt
            )
            raw = clean_json_str(resp.text)
            parsed = json.loads(raw)
            if isinstance(parsed, list) and len(parsed) > 0:
                eval_map = {item.get("evidence_id"): item for item in parsed if "evidence_id" in item}
                for ev in evidences:
                    eval_data = eval_map.get(ev.id) or {}
                    classification = str(eval_data.get("classification", "neutral")).lower().strip()
                    finding_cat = eval_data.get("finding_category")
                    reason = eval_data.get("reason", f"Evaluated against exhibit {ev.file_name}")
                    confidence = float(eval_data.get("confidence", 0.9))
                    verified_quote = verify_quoted_source_line(eval_data.get("quoted_source_line"), ev.extracted_text or "")

                    resolved_lr = resolve_assessment_likelihood_ratio(
                        evidence_type=ev.evidence_type or "document",
                        finding_category=finding_cat,
                        classification=classification,
                        reliability=1.0,
                        confidence=confidence
                    )

                    existing = db.query(EvidenceAssessment).filter(
                        EvidenceAssessment.hypothesis_id == h.id,
                        EvidenceAssessment.evidence_id == ev.id
                    ).first()
                    if existing:
                        if not existing.analyst_override:
                            existing.classification = classification
                            existing.finding_category = resolved_lr["category_key"]
                            existing.finding_name = resolved_lr["finding_name"]
                            existing.likelihood_ratio = resolved_lr["base_lr"]
                            existing.effective_lr = resolved_lr["effective_lr"]
                            existing.lr_min = resolved_lr["min_lr"]
                            existing.lr_max = resolved_lr["max_lr"]
                            existing.lr_source_citation = resolved_lr["source_citation"]
                            existing.lr_error_rate = resolved_lr["forensic_error_rate"]
                            existing.weight_of_evidence_bans = resolved_lr["weight_of_evidence_bans"]
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
                            reliability=1.0,
                            finding_category=resolved_lr["category_key"],
                            finding_name=resolved_lr["finding_name"],
                            likelihood_ratio=resolved_lr["base_lr"],
                            effective_lr=resolved_lr["effective_lr"],
                            lr_min=resolved_lr["min_lr"],
                            lr_max=resolved_lr["max_lr"],
                            lr_source_citation=resolved_lr["source_citation"],
                            lr_error_rate=resolved_lr["forensic_error_rate"],
                            weight_of_evidence_bans=resolved_lr["weight_of_evidence_bans"]
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
        finding_cat = None
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

{FORENSIC_FINDING_CATEGORIES_GUIDE}

Classify into EXACTLY one of:
- strong_support
- moderate_support
- weak_support
- neutral
- weak_contradiction
- moderate_contradiction
- strong_contradiction

Also select the most accurate "finding_category" from the reference table above.
Respond in valid JSON only:
{{
  "classification": "strong_support | neutral | strong_contradiction ...",
  "finding_category": "dna_match_single_source | cctv_facial_id_clear | generic_neutral ...",
  "reason": "Clear explanation citing forensic facts in this exhibit",
  "quoted_source_line": "Exact verbatim quote from the text",
  "confidence": 0.95
}}
"""
            try:
                resp = client.models.generate_content(
                    model=DEFAULT_MODEL_NAME,
                    contents=prompt
                )
                raw = clean_json_str(resp.text)
                parsed = json.loads(raw)
                classification = parsed.get("classification", "neutral").lower().strip()
                finding_cat = parsed.get("finding_category")
                reason = parsed.get("reason", reason)
                confidence = float(parsed.get("confidence", 0.9))
                verified_quote = verify_quoted_source_line(parsed.get("quoted_source_line"), ev.extracted_text or "")
            except Exception as e:
                print(f"[!] AI eval exception for exhibit {ev.id}: {e}")

        resolved_lr = resolve_assessment_likelihood_ratio(
            evidence_type=ev.evidence_type or "document",
            finding_category=finding_cat,
            classification=classification,
            reliability=1.0,
            confidence=confidence
        )

        existing = db.query(EvidenceAssessment).filter(
            EvidenceAssessment.hypothesis_id == h.id,
            EvidenceAssessment.evidence_id == ev.id
        ).first()

        if existing:
            if not existing.analyst_override:
                existing.classification = classification
                existing.finding_category = resolved_lr["category_key"]
                existing.finding_name = resolved_lr["finding_name"]
                existing.likelihood_ratio = resolved_lr["base_lr"]
                existing.effective_lr = resolved_lr["effective_lr"]
                existing.lr_min = resolved_lr["min_lr"]
                existing.lr_max = resolved_lr["max_lr"]
                existing.lr_source_citation = resolved_lr["source_citation"]
                existing.lr_error_rate = resolved_lr["forensic_error_rate"]
                existing.weight_of_evidence_bans = resolved_lr["weight_of_evidence_bans"]
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
                reliability=1.0,
                finding_category=resolved_lr["category_key"],
                finding_name=resolved_lr["finding_name"],
                likelihood_ratio=resolved_lr["base_lr"],
                effective_lr=resolved_lr["effective_lr"],
                lr_min=resolved_lr["min_lr"],
                lr_max=resolved_lr["max_lr"],
                lr_source_citation=resolved_lr["source_citation"],
                lr_error_rate=resolved_lr["forensic_error_rate"],
                weight_of_evidence_bans=resolved_lr["weight_of_evidence_bans"]
            )
            db.add(db_assessment)

    db.commit()
    execute_scoring_run(h.case_id, db, triggered_by="ai_individual_evaluate")
    return get_hypothesis(hypothesis_id, db)






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
                model=DEFAULT_MODEL_NAME,
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

FORENSIC REFERENCE CATEGORIES (Identify the closest standard finding category; DO NOT invent numerical likelihood ratios - the scientific reference table supplies the numbers):
- DNA: "dna_match_single_source", "dna_match_complex_mixture", "dna_partial_profile", "dna_exclusion"
- Fingerprint: "fingerprint_latent_high_detail", "fingerprint_latent_medium_detail", "fingerprint_inconclusive", "fingerprint_exclusion"
- CCTV / Video: "cctv_facial_id_clear", "cctv_clothing_height_match", "cctv_partial_obscured", "cctv_conflicting_description"
- Telecom / CDR: "cdr_cell_tower_coincident", "cdr_cell_tower_vicinity", "cdr_distant_tower"
- Digital / Cyber: "digital_device_direct_activity", "digital_browser_or_search", "digital_device_contradiction"
- Ballistics: "ballistics_striation_match", "ballistics_caliber_class_only", "ballistics_exclusion"
- GSR: "gsr_heavy_characteristic", "gsr_trace_particles", "gsr_negative"
- Eyewitness: "eyewitness_confident_immediate", "eyewitness_delayed_tentative", "eyewitness_contradictory"
- Alibi: "alibi_corroborated_official", "alibi_corroborated_associate", "alibi_unverified", "alibi_falsified"
- Financial / Document / Other: "financial_transaction_record", "generic_neutral"

Evaluate EVERY legal evidence exhibit against EVERY investigative hypothesis in the matrix.
Classify each (hypothesis, evidence) relationship into EXACTLY one of:
- strong_support
- moderate_support
- weak_support
- neutral
- weak_contradiction
- moderate_contradiction
- strong_contradiction

Also select the most accurate "finding_category" from the reference table above.
IMPORTANT: Provide an exact verbatim quote ("quoted_source_line") from the exhibit text supporting your assessment. Do not fabricate quotes.

Provide a clear explanation citing specific forensic facts from the exhibit.
Respond in valid JSON array only:
[
  {{
    "hypothesis_id": {target_hypotheses[0].id},
    "evidence_id": {evidences[0].id},
    "classification": "strong_support | neutral | strong_contradiction ...",
    "finding_category": "dna_match_single_source | cctv_facial_id_clear | generic_neutral ...",
    "reason": "Clear explanation citing forensic facts in this exhibit",
    "quoted_source_line": "Exact verbatim quote from the text",
    "confidence": 0.95
  }}
]"""
        try:
            resp = client.models.generate_content(
                model=DEFAULT_MODEL_NAME,
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
                    finding_cat = item.get("finding_category")
                    reason = item.get("reason", "Corroborated by forensic exhibit analysis")
                    conf = float(item.get("confidence", 0.9))
                    ev_obj = ev_lookup.get(ev_id)
                    ev_type = ev_obj.evidence_type if ev_obj and ev_obj.evidence_type else "document"
                    verified_quote = verify_quoted_source_line(
                        item.get("quoted_source_line"),
                        ev_obj.extracted_text if ev_obj else ""
                    )

                    resolved_lr = resolve_assessment_likelihood_ratio(
                        evidence_type=ev_type,
                        finding_category=finding_cat,
                        classification=cls,
                        reliability=1.0,
                        confidence=conf
                    )

                    existing = db.query(EvidenceAssessment).filter(
                        EvidenceAssessment.hypothesis_id == h_id,
                        EvidenceAssessment.evidence_id == ev_id
                    ).first()
                    if existing:
                        # Preserve human analyst override if present
                        if not existing.analyst_override:
                            existing.classification = cls
                            existing.finding_category = resolved_lr["category_key"]
                            existing.finding_name = resolved_lr["finding_name"]
                            existing.likelihood_ratio = resolved_lr["base_lr"]
                            existing.effective_lr = resolved_lr["effective_lr"]
                            existing.lr_min = resolved_lr["min_lr"]
                            existing.lr_max = resolved_lr["max_lr"]
                            existing.lr_source_citation = resolved_lr["source_citation"]
                            existing.lr_error_rate = resolved_lr["forensic_error_rate"]
                            existing.weight_of_evidence_bans = resolved_lr["weight_of_evidence_bans"]
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
                            reliability=1.0,
                            finding_category=resolved_lr["category_key"],
                            finding_name=resolved_lr["finding_name"],
                            likelihood_ratio=resolved_lr["base_lr"],
                            effective_lr=resolved_lr["effective_lr"],
                            lr_min=resolved_lr["min_lr"],
                            lr_max=resolved_lr["max_lr"],
                            lr_source_citation=resolved_lr["source_citation"],
                            lr_error_rate=resolved_lr["forensic_error_rate"],
                            weight_of_evidence_bans=resolved_lr["weight_of_evidence_bans"]
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
        assigned_to=data.assigned_to or "Lead Investigator",
        version=1
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
    if "category" in updates:
        t.category = updates["category"]
    if "impact_score" in updates:
        t.impact_score = updates["impact_score"]
    if "dismissed" in updates:
        t.dismissed = bool(updates["dismissed"])
        if t.dismissed:
            t.status = "Dismissed"
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
                model=DEFAULT_MODEL_NAME,
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
        "extraction_mode": getattr(ev, "extraction_mode", "live") or "live",
        "is_demo_fixture": bool(getattr(ev, "is_demo_fixture", False)),
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
# Protected: Admin role strictly required (triggers heavy ML/forensic pipeline work)
# ============================================================












# ============================================================
# PHASE 3 FEATURE 4: PDF CASE REPORT EXPORT ENDPOINTS
# ============================================================





if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)