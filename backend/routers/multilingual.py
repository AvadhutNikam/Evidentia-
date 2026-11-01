"""
backend/routers/multilingual.py
===============================
Evidentia AI - Multilingual Evidence, OCR Profiling & Versioned Text API Router.
Handles side-by-side viewer payloads, analyst text corrections, immutable version chains,
reviewer sign-offs, separate translations, dual-citations, and cross-language search.
"""

from datetime import datetime, timezone
import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models import (
    Case, Evidence, ExhibitTextVersion, ExhibitSegment,
    ExhibitTranslation, TranslationSegment, SourceCitation,
    LanguageProfileConfig, User
)
from schemas import (
    MultilingualProfileResponse, ExhibitTextVersionOut, ExhibitSegmentOut,
    ExhibitTextCorrectionRequest, ExhibitTranslationOut, TranslationCreateRequest,
    DualCitationOut, LanguageProfileConfigOut, LanguageProfileConfigUpdate
)
from auth import get_current_user, check_case_access
from routers.common import resolve_case_id
from scoring.evidence_scoring import resolve_exhibit_reliability
from multilingual_engine import (
    detect_language_and_script, normalize_multilingual_text,
    create_initial_segments, seed_initial_exhibit_version,
    apply_analyst_text_correction, revert_exhibit_to_version,
    signoff_version, create_or_update_translation, review_translation,
    format_dual_citation, search_multilingual_corpus
)

router = APIRouter(tags=["Multilingual Evidence & Versioning"])


# ==============================================================================
# 1. EXHIBIT MULTILINGUAL PROFILE & SIDE-BY-SIDE PAYLOAD
# ==============================================================================

@router.get("/cases/{case_id}/evidence/{evidence_id}/multilingual", response_model=MultilingualProfileResponse)
def get_exhibit_multilingual_profile(
    case_id: str,
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns the comprehensive multilingual and versioning profile for an exhibit."""
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "view_evidence"):
        raise HTTPException(status_code=403, detail="Access denied to case exhibits.")

    evidence = db.query(Evidence).filter(
        Evidence.id == evidence_id,
        Evidence.case_id == real_id,
        Evidence.is_deleted == False
    ).first()
    if not evidence:
        raise HTTPException(status_code=404, detail=f"Evidence #{evidence_id} not found.")

    # Ensure Version 1 baseline exists
    curr_v = db.query(ExhibitTextVersion).filter(
        ExhibitTextVersion.evidence_id == evidence.id,
        ExhibitTextVersion.is_current == True
    ).first()
    if not curr_v:
        curr_v = seed_initial_exhibit_version(db, evidence.id, user_name=current_user.full_name)

    # Fetch all versions
    versions = db.query(ExhibitTextVersion).filter(
        ExhibitTextVersion.evidence_id == evidence.id
    ).order_by(ExhibitTextVersion.version_number.desc()).all()

    # Fetch all translations
    translations = db.query(ExhibitTranslation).filter(
        ExhibitTranslation.evidence_id == evidence.id
    ).order_by(ExhibitTranslation.id.desc()).all()

    # Fetch citations with dual quote representation
    citations = db.query(SourceCitation).filter(
        SourceCitation.evidence_id == evidence.id
    ).order_by(SourceCitation.id.asc()).all()

    dual_citations = [
        format_dual_citation(cit, evidence, db)
        for cit in citations
    ]

    # Compute reliability audit
    evidence_dict = {
        "evidence_type": evidence.evidence_type,
        "hash_verified": evidence.hash_verified,
        "chain_of_custody_complete": evidence.chain_of_custody_complete,
        "sec_65b_certificate_present": evidence.sec_65b_certificate_present,
        "source_independent": evidence.source_independent,
        "quality_rating": evidence.quality_rating,
        "content_type": evidence.content_type,
        "text_quality_status": evidence.text_quality_status,
        "ocr_confidence": evidence.ocr_confidence,
        "is_poor_audio": evidence.is_poor_audio
    }
    rel_score, rel_audit = resolve_exhibit_reliability(evidence_dict)

    return MultilingualProfileResponse(
        evidence_id=evidence.id,
        file_name=evidence.file_name,
        file_type=evidence.file_type or "document",
        primary_language=evidence.primary_language,
        is_mixed=evidence.is_mixed,
        script=evidence.script,
        content_type=evidence.content_type,
        language_source=evidence.language_source,
        text_quality_status=evidence.text_quality_status,
        is_poor_audio=evidence.is_poor_audio,
        ocr_reading_method=evidence.ocr_reading_method,
        ocr_confidence=evidence.ocr_confidence or 1.0,
        current_version=curr_v,
        versions_count=len(versions),
        versions=versions,
        translations=translations,
        dual_citations=dual_citations,
        reliability_assessment=rel_audit
    )


@router.post("/cases/{case_id}/evidence/{evidence_id}/language-confirm")
def confirm_exhibit_language_profile(
    case_id: str,
    evidence_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Analyst confirms or overrides the exhibit language profile."""
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "edit_evidence"):
        raise HTTPException(status_code=403, detail="Access denied.")

    evidence = db.query(Evidence).filter(
        Evidence.id == evidence_id,
        Evidence.case_id == real_id,
        Evidence.is_deleted == False
    ).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found.")

    if "primary_language" in payload:
        evidence.primary_language = payload["primary_language"]
    if "is_mixed" in payload:
        evidence.is_mixed = bool(payload["is_mixed"])
    if "script" in payload:
        evidence.script = payload["script"]
    if "content_type" in payload:
        evidence.content_type = payload["content_type"]
    if "is_poor_audio" in payload:
        evidence.is_poor_audio = bool(payload["is_poor_audio"])

    evidence.language_source = "user_confirmed"
    db.commit()

    return {
        "success": True,
        "evidence_id": evidence.id,
        "primary_language": evidence.primary_language,
        "content_type": evidence.content_type,
        "language_source": evidence.language_source,
        "message": "Language profile confirmed by analyst."
    }


# ==============================================================================
# 2. VERSION MANAGEMENT & ANALYST CORRECTIONS
# ==============================================================================

@router.get("/cases/{case_id}/evidence/{evidence_id}/versions", response_model=List[ExhibitTextVersionOut])
def list_exhibit_versions(
    case_id: str,
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns the immutable version chain for an exhibit."""
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "view_evidence"):
        raise HTTPException(status_code=403, detail="Access denied.")

    versions = db.query(ExhibitTextVersion).filter(
        ExhibitTextVersion.evidence_id == evidence_id,
        ExhibitTextVersion.case_id == real_id
    ).order_by(ExhibitTextVersion.version_number.desc()).all()

    return versions


@router.post("/cases/{case_id}/evidence/{evidence_id}/corrections")
def submit_text_correction(
    case_id: str,
    evidence_id: int,
    payload: ExhibitTextCorrectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits an analyst correction to an exhibit transcript/OCR.
    Creates a new version, writes Merkle audit block, marks affected facts stale,
    and recalculates hypothesis ACH scores.
    """
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "edit_evidence"):
        raise HTTPException(status_code=403, detail="Analyst role required to submit text corrections.")

    result = apply_analyst_text_correction(
        db=db,
        evidence_id=evidence_id,
        new_text=payload.new_text,
        edit_reason=payload.edit_reason,
        user_id=current_user.id,
        user_name=current_user.full_name,
        user_role=current_user.role,
        requires_second_signoff=bool(payload.requires_second_signoff)
    )

    return result


@router.post("/cases/{case_id}/evidence/{evidence_id}/versions/{version_id}/revert")
def revert_to_version(
    case_id: str,
    evidence_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reverts active exhibit text back to a prior version (creates an incremented version)."""
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "edit_evidence"):
        raise HTTPException(status_code=403, detail="Access denied.")

    v = db.query(ExhibitTextVersion).filter(
        ExhibitTextVersion.id == version_id,
        ExhibitTextVersion.evidence_id == evidence_id
    ).first()
    if not v:
        raise HTTPException(status_code=404, detail="Version not found.")

    res = revert_exhibit_to_version(
        db=db,
        evidence_id=evidence_id,
        target_version_number=v.version_number,
        user_id=current_user.id,
        user_name=current_user.full_name,
        user_role=current_user.role
    )
    return res


@router.post("/cases/{case_id}/evidence/{evidence_id}/versions/{version_id}/signoff")
def second_reviewer_signoff(
    case_id: str,
    evidence_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Second reviewer signs off on a corrected exhibit version."""
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "review_case"):
        raise HTTPException(status_code=403, detail="Lead investigator or reviewer role required for signoff.")

    res = signoff_version(
        db=db,
        evidence_id=evidence_id,
        version_id=version_id,
        reviewer_name=current_user.full_name
    )
    return res


# ==============================================================================
# 3. TRANSLATIONS & SEGMENT ALIGNMENTS
# ==============================================================================

@router.post("/cases/{case_id}/evidence/{evidence_id}/translations", response_model=ExhibitTranslationOut)
def add_exhibit_translation(
    case_id: str,
    evidence_id: int,
    payload: TranslationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Creates a new human-certified or machine translation linked to current active version."""
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "edit_evidence"):
        raise HTTPException(status_code=403, detail="Access denied.")

    trans = create_or_update_translation(
        db=db,
        evidence_id=evidence_id,
        target_language=payload.target_language or "en",
        author_type=payload.author_type or "certified_human",
        author_name=payload.author_name or current_user.full_name,
        model_used="human_entry",
        custom_text=payload.translated_text
    )
    return trans


@router.post("/cases/{case_id}/evidence/{evidence_id}/translations/{translation_id}/review")
def mark_translation_as_reviewed(
    case_id: str,
    evidence_id: int,
    translation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Marks a machine translation as certified human reviewed."""
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "review_case"):
        raise HTTPException(status_code=403, detail="Access denied.")

    res = review_translation(db, translation_id, current_user.full_name)
    return res


# ==============================================================================
# 4. CROSS-LANGUAGE CORPUS SEARCH
# ==============================================================================

@router.get("/cases/{case_id}/multilingual/search")
def search_multilingual(
    case_id: str,
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Searches exhibits across original script, normalized text, and translations."""
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "view_evidence"):
        raise HTTPException(status_code=403, detail="Access denied.")

    results = search_multilingual_corpus(db=db, case_id=real_id, query=q)
    return {"query": q, "total_matches": len(results), "matches": results}


# ==============================================================================
# 5. LANGUAGE SETTINGS CONFIGURATION
# ==============================================================================

@router.get("/cases/{case_id}/multilingual/settings", response_model=List[LanguageProfileConfigOut])
def get_language_settings(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns the list of OCR/STT language profile configurations."""
    real_id = resolve_case_id(case_id, db)
    configs = db.query(LanguageProfileConfig).all()
    if not configs:
        # Seed default language configs
        defaults = [
            LanguageProfileConfig(
                language="mr", script="devanagari", content_type="printed",
                reading_method="gemini_multimodal", fallback_method="tesseract_deva",
                preprocessing_steps=json.dumps(["deskew", "denoise", "contrast", "crop_borders", "super_res"]),
                confidence_threshold=0.75, translate_by_default=True, default_target_language="en"
            ),
            LanguageProfileConfig(
                language="hi", script="devanagari", content_type="printed",
                reading_method="gemini_multimodal", fallback_method="tesseract_deva",
                preprocessing_steps=json.dumps(["deskew", "denoise", "contrast", "crop_borders", "super_res"]),
                confidence_threshold=0.75, translate_by_default=True, default_target_language="en"
            ),
            LanguageProfileConfig(
                language="mr", script="devanagari", content_type="handwritten",
                reading_method="gemini_multimodal", fallback_method="analyst_mandatory_review",
                preprocessing_steps=json.dumps(["contrast", "denoise", "super_res"]),
                confidence_threshold=0.60, translate_by_default=True, default_target_language="en"
            ),
            LanguageProfileConfig(
                language="en", script="latin", content_type="printed",
                reading_method="pypdf_native", fallback_method="gemini_multimodal",
                preprocessing_steps=json.dumps(["deskew"]),
                confidence_threshold=0.85, translate_by_default=False, default_target_language="en"
            ),
            LanguageProfileConfig(
                language="mixed", script="mixed", content_type="audio",
                reading_method="whisper_stt", fallback_method="gemini_audio",
                stt_model_hint="whisper_large_v3_indic",
                preprocessing_steps=json.dumps([]),
                confidence_threshold=0.70, translate_by_default=True, default_target_language="en"
            )
        ]
        db.add_all(defaults)
        db.commit()
        configs = db.query(LanguageProfileConfig).all()

    return configs
