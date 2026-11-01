# backend/routers/intake.py
"""
Evidentia-AI Multi-Channel Intake & Reading Card Router
Endpoints for low-typing ingestion, reading card verification, and Indic disambiguation.
"""

import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from database import get_db
from models import User, Case, IntakeItem, PersonAlias
from schemas import (
    IntakeItemOut, IntakeConfirmationRequest, IntakeRejectRequest,
    IntakeTrustMetricsOut, TransliterateRequest, TransliterateResponse,
    NameDisambiguationResponse, PersonAliasCreate, PersonAliasOut
)
from auth import get_current_user, check_case_access
from routers.common import resolve_case_id
from intake_engine import (
    process_intake_submission, confirm_intake_item, get_intake_trust_metrics
)
from indic_engine import (
    transliterate_indic, soundex_indic, strip_indic_honorifics_and_affixes,
    match_person_multi_signal
)

router = APIRouter(tags=["intake"])


def _format_intake_out(item: IntakeItem) -> IntakeItemOut:
    """Helper to deserialize proposed_fields JSON string into Pydantic schema."""
    props = []
    if item.proposed_fields:
        try:
            props = json.loads(item.proposed_fields)
        except Exception:
            props = []
    
    return IntakeItemOut(
        id=item.id,
        case_id=item.case_id,
        channel=item.channel,
        title=item.title,
        original_file_name=item.original_file_name,
        storage_path=item.storage_path,
        file_hash=item.file_hash,
        file_size_bytes=item.file_size_bytes,
        mime_type=item.mime_type,
        detected_language=item.detected_language,
        detected_script=item.detected_script,
        status=item.status,
        confidence_score=item.confidence_score,
        proposed_fields=props,
        raw_text=item.raw_text,
        submitter_name=item.submitter_name,
        submitter_role=item.submitter_role,
        reviewed_by=item.reviewed_by,
        reviewed_at=item.reviewed_at,
        review_notes=item.review_notes,
        applied_entities_count=item.applied_entities_count,
        created_at=item.created_at
    )


# ==============================================================================
# INTAKE LISTING & DETAILS
# ==============================================================================

@router.get("/cases/{case_id}/intake", response_model=List[IntakeItemOut])
def list_case_intake_items(
    case_id: str,
    channel: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists all intake items for a case, with optional channel and status filters."""
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "view_evidence"):
        raise HTTPException(status_code=403, detail="Access denied")

    q = db.query(IntakeItem).filter(IntakeItem.case_id == real_id)
    if channel:
        q = q.filter(IntakeItem.channel == channel)
    if status:
        q = q.filter(IntakeItem.status == status)

    items = q.order_by(IntakeItem.created_at.desc()).all()
    return [_format_intake_out(it) for it in items]


@router.get("/cases/{case_id}/intake/{intake_id}", response_model=IntakeItemOut)
def get_intake_item_detail(
    case_id: str,
    intake_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves full details and extracted fields for an intake item."""
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "view_evidence"):
        raise HTTPException(status_code=403, detail="Access denied")

    item = db.query(IntakeItem).filter(
        IntakeItem.id == intake_id,
        IntakeItem.case_id == real_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Intake item not found")

    return _format_intake_out(item)


# ==============================================================================
# INTAKE INGESTION (TEXT & FILE UPLOAD)
# ==============================================================================

@router.post("/cases/{case_id}/intake/submit-text", response_model=IntakeItemOut)
def submit_text_intake(
    case_id: str,
    channel: str = Form(...),
    title: str = Form(...),
    text_content: str = Form(...),
    detected_language: str = Form("mr"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submits text content (e.g. pasted WhatsApp log, FIR text, typed statement) to the intake gateway."""
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "edit_evidence"):
        raise HTTPException(status_code=403, detail="Access denied")

    item = process_intake_submission(
        db=db,
        case_id=real_id,
        channel=channel,
        title=title,
        raw_text=text_content,
        submitter_name=current_user.full_name,
        submitter_role=current_user.role or "analyst"
    )
    return _format_intake_out(item)


@router.post("/cases/{case_id}/intake/upload", response_model=IntakeItemOut)
async def upload_intake_file(
    case_id: str,
    channel: str = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads a physical exhibit, handwritten statement scan, voice note audio,
    or WhatsApp export zip/txt. Computes cryptographic hash and extracts draft fields.
    """
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "edit_evidence"):
        raise HTTPException(status_code=403, detail="Access denied")

    file_bytes = await file.read()
    item = process_intake_submission(
        db=db,
        case_id=real_id,
        channel=channel,
        title=title,
        file_bytes=file_bytes,
        original_filename=file.filename,
        mime_type=file.content_type,
        submitter_name=current_user.full_name,
        submitter_role=current_user.role or "analyst"
    )
    return _format_intake_out(item)


# ==============================================================================
# READING CARD CONFIRMATION & REJECTION
# ==============================================================================

@router.post("/cases/{case_id}/intake/{intake_id}/confirm", response_model=IntakeItemOut)
def confirm_intake_fields(
    case_id: str,
    intake_id: int,
    req: IntakeConfirmationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Officer confirmation gate:
    Applies confirmed fields to official records (Case, CasePerson, Diary, Tasks).
    Unconfirmed/rejected fields are logged in feedback and strictly isolated from case strength scoring.
    """
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "edit_evidence"):
        raise HTTPException(status_code=403, detail="Access denied")

    confirmations_dicts = [c.dict() for c in req.confirmations]
    item = confirm_intake_item(
        db=db,
        intake_id=intake_id,
        user_id=current_user.id,
        user_name=current_user.full_name,
        confirmations=confirmations_dicts,
        apply_to_case_file=req.apply_to_case_file,
        apply_to_people_register=req.apply_to_people_register,
        apply_to_case_diary=req.apply_to_case_diary,
        create_exhibit_record=req.create_exhibit_record
    )
    return _format_intake_out(item)


@router.post("/cases/{case_id}/intake/{intake_id}/reject", response_model=IntakeItemOut)
def reject_intake_item(
    case_id: str,
    intake_id: int,
    req: IntakeRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Rejects an intake item with an explanation notes log."""
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "edit_evidence"):
        raise HTTPException(status_code=403, detail="Access denied")

    item = db.query(IntakeItem).filter(
        IntakeItem.id == intake_id,
        IntakeItem.case_id == real_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Intake item not found")

    item.status = "rejected"
    item.reviewed_by = current_user.full_name
    item.review_notes = req.reason
    db.commit()
    db.refresh(item)
    return _format_intake_out(item)


# ==============================================================================
# TRUST METRICS & DISAMBIGUATION
# ==============================================================================

@router.get("/cases/{case_id}/intake-metrics", response_model=IntakeTrustMetricsOut)
def get_intake_metrics(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns empirical field acceptance rates and accuracy metrics."""
    real_id = resolve_case_id(case_id, db)
    metrics = get_intake_trust_metrics(db=db, case_id=real_id)
    return metrics


@router.post("/cases/{case_id}/intake/transliterate", response_model=TransliterateResponse)
@router.post("/intake/transliterate", response_model=TransliterateResponse)
def transliterate_text(
    req: TransliterateRequest
):
    """Provides zero-latency transliteration suggestions for low-typing data entry."""
    sugg = transliterate_indic(
        text=req.text,
        source_script=req.source_script,
        target_script=req.target_script,
        max_suggestions=req.max_suggestions
    )
    snd = soundex_indic(req.text)
    return TransliterateResponse(
        input_text=req.text,
        suggestions=sugg,
        phonetic_key=snd
    )


@router.post("/cases/{case_id}/intake/disambiguate-name", response_model=NameDisambiguationResponse)
def disambiguate_person_name(
    case_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cross-script multi-signal name disambiguation.
    Enforces anti-false-merge safeguards: caps common names without corroboration at 65%.
    """
    real_id = resolve_case_id(case_id, db)
    name = payload.get("name", "")
    signals = payload.get("signals", {})

    candidates = match_person_multi_signal(
        candidate_name=name,
        candidate_signals=signals,
        db=db,
        case_id=real_id
    )
    snd = soundex_indic(name)
    exact_match = any(c["similarity_score"] >= 0.95 for c in candidates)

    return NameDisambiguationResponse(
        queried_name=name,
        phonetic_key=snd,
        candidates=candidates,
        exact_match_found=exact_match
    )


# ==============================================================================
# PERSON ALIASES REGISTRY
# ==============================================================================

@router.get("/cases/{case_id}/aliases", response_model=List[PersonAliasOut])
def list_person_aliases(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists verified multi-script aliases for people associated with this case."""
    real_id = resolve_case_id(case_id, db)
    aliases = db.query(PersonAlias).filter(PersonAlias.case_id == real_id).all()
    return aliases


@router.post("/cases/{case_id}/aliases", response_model=PersonAliasOut)
def create_person_alias(
    case_id: str,
    req: PersonAliasCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registers a new verified cross-script alias for a person."""
    real_id = resolve_case_id(case_id, db)
    snd = soundex_indic(req.canonical_name)
    alias = PersonAlias(
        case_id=real_id,
        person_id=req.person_id,
        canonical_name=req.canonical_name,
        alias_name=req.alias_name,
        script=req.script,
        phonetic_key=snd,
        source_exhibit_id=req.source_exhibit_id,
        confirmed_by=current_user.full_name,
        is_verified=True
    )
    db.add(alias)
    db.commit()
    db.refresh(alias)
    return alias
