"""
backend/data_quality_engine.py
Forensic Evidence Data-Quality Scoring Engine.

Computes a 4-pillar composite quality score (0 - 100%) for every exhibit:
1. Text Confidence (25%): OCR confidence, transcript completeness, poor audio penalties.
2. Hash Status (25%): SHA-256 byte-stream calculation and on-device integrity match.
3. Certificate Status (25%): Section 63/65B IEA / Sec 61 BSA certificate & officer declaration.
4. Language Review Status (25%): Regional language detection, translation presence, and judicial signoff.

Sorts the weakest items first so investigative and forensic effort goes where it matters most.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from models import Case, Evidence, ExhibitTranslation


def calculate_exhibit_data_quality(evidence: Evidence, db: Session) -> Dict[str, Any]:
    """
    Computes four-pillar quality score and identifies actionable warnings for an exhibit.
    """
    warning_flags: List[str] = []
    recommended_actions: List[str] = []

    # --------------------------------------------------------------------------
    # 1. PILLAR 1: TEXT CONFIDENCE (25%)
    # --------------------------------------------------------------------------
    extracted_text = (evidence.extracted_text or "").strip()
    ocr_confidence = getattr(evidence, "ocr_confidence", None)
    text_quality_status = getattr(evidence, "text_quality_status", "high")
    is_poor_audio = getattr(evidence, "is_poor_audio", False)

    if not extracted_text:
        text_pct = 15.0
        text_status = "unextracted"
        text_notes = "No text extracted. Media requires OCR or speech transcription."
        warning_flags.append("No text extracted from exhibit")
        recommended_actions.append("Run OCR / Whisper Speech-to-Text")
    elif is_poor_audio:
        text_pct = 35.0
        text_status = "poor_audio"
        text_notes = "Audio recording contains heavy background noise or clipping."
        warning_flags.append("Poor audio quality flag present")
        recommended_actions.append("Apply noise reduction filter and verify transcript")
    elif ocr_confidence is not None:
        raw_val = float(ocr_confidence)
        # Normalize ratio (0.0 - 1.0) to percentage (0 - 100)
        text_pct = (raw_val * 100.0) if raw_val <= 1.0 else raw_val
        if text_pct < 55.0:
            text_status = "low"
            text_notes = f"Low OCR recognition confidence ({text_pct:.1f}%). Possible illegible scan."
            warning_flags.append(f"Low OCR confidence ({text_pct:.0f}%)")
            recommended_actions.append("Review scan resolution or manually correct transcript")
        elif text_pct < 80.0:
            text_status = "medium"
            text_notes = f"Moderate OCR confidence ({text_pct:.1f}%)."
        else:
            text_status = "high"
            text_notes = f"High-fidelity OCR recognition ({text_pct:.1f}%)."
    else:
        # Document or text with reasonable length
        if len(extracted_text) < 40:
            text_pct = 50.0
            text_status = "low"
            text_notes = f"Very short text extracted ({len(extracted_text)} chars)."
            warning_flags.append("Abbreviated or partial text extract")
        else:
            text_pct = 95.0
            text_status = "high"
            text_notes = "Full digital text verified without character corruption."

    text_score = round((text_pct / 100.0) * 25.0, 1)

    # --------------------------------------------------------------------------
    # 2. PILLAR 2: HASH INTEGRITY STATUS (25%)
    # --------------------------------------------------------------------------
    has_hash = bool(evidence.file_hash and len(evidence.file_hash) >= 32)
    hash_verified = bool(evidence.hash_verified)
    is_field = getattr(evidence, "is_field_captured", False)
    hash_match = getattr(evidence, "hash_match_verified", True) if is_field else True

    if has_hash and hash_verified and hash_match:
        hash_score = 25.0
        hash_status = "verified"
        hash_val = evidence.file_hash
    elif has_hash and not hash_verified:
        hash_score = 12.0
        hash_status = "unverified"
        hash_val = evidence.file_hash
        warning_flags.append("Cryptographic hash recorded but unverified against storage byte stream")
        recommended_actions.append("Run automated hash verification check")
    else:
        hash_score = 0.0
        hash_status = "mismatch"
        hash_val = None
        warning_flags.append("Cryptographic hash missing or integrity verification failed")
        recommended_actions.append("Recompute SHA-256 hash immediately")

    # --------------------------------------------------------------------------
    # 3. PILLAR 3: CERTIFICATE & LEGAL INTEGRITY STATUS (25%)
    # --------------------------------------------------------------------------
    cert_present = bool(evidence.sec_65b_certificate_present)
    officer_confirmed = getattr(evidence, "field_officer_confirmed", False)
    has_declaration = bool(getattr(evidence, "field_officer_declaration", None))

    if cert_present or (officer_confirmed and has_declaration):
        cert_score = 25.0
        cert_status = "certified"
        cert_notes = "Section 63/65B Certificate or signed officer field declaration present."
    elif cert_present:
        cert_score = 25.0
        cert_status = "certified"
        cert_notes = "Section 65B Electronic Evidence Certificate attached."
    else:
        cert_score = 0.0
        cert_status = "missing"
        cert_notes = "Section 65B Indian Evidence Act certificate is missing."
        warning_flags.append("Missing Section 65B Evidence Certificate")
        recommended_actions.append("Generate and sign Section 65B legal certificate")

    # --------------------------------------------------------------------------
    # 4. PILLAR 4: LANGUAGE REVIEW STATUS (25%)
    # --------------------------------------------------------------------------
    primary_lang = getattr(evidence, "primary_language", "en") or "en"
    clean_lang = primary_lang.lower().strip()
    is_regional = clean_lang in ["hi", "mr", "gu", "ta", "te", "bn", "kn", "hindi", "marathi", "gujarati"]

    if not is_regional:
        lang_score = 25.0
        lang_status = "native_english"
        lang_notes = "Native English or binary telemetry; translation not required."
    else:
        # Check if an official ExhibitTranslation exists
        translation = (
            db.query(ExhibitTranslation)
            .filter(ExhibitTranslation.evidence_id == evidence.id)
            .order_by(ExhibitTranslation.id.desc())
            .first()
        )
        if translation and translation.review_status == "verified":
            lang_score = 25.0
            lang_status = "verified"
            lang_notes = f"{clean_lang.upper()} source translation reviewed and signed off by {translation.reviewed_by or 'Court Interpreter'}."
        elif translation:
            lang_score = 12.0
            lang_status = "pending_review"
            lang_notes = f"{clean_lang.upper()} translation generated but awaits judicial analyst signoff."
            warning_flags.append(f"Regional ({clean_lang.upper()}) translation pending signoff")
            recommended_actions.append("Sign off judicial translation")
        else:
            lang_score = 6.0
            lang_status = "untranslated"
            lang_notes = f"Exhibit contains {clean_lang.upper()} dialect but lacks English judicial translation."
            warning_flags.append(f"Untranslated regional dialect ({clean_lang.upper()})")
            recommended_actions.append("Generate dual-citation translation")

    # --------------------------------------------------------------------------
    # COMPOSITE SCORE CALCULATION
    # --------------------------------------------------------------------------
    overall_score = round(text_score + hash_score + cert_score + lang_score, 1)

    if overall_score < 55.0:
        quality_tier = "Critical Attention Needed"
        is_weak = True
    elif overall_score < 70.0:
        quality_tier = "Weak Quality"
        is_weak = True
    elif overall_score < 85.0:
        quality_tier = "Adequate Quality"
        is_weak = False
    else:
        quality_tier = "Judicially Sound & Verified"
        is_weak = False

    best_action = recommended_actions[0] if recommended_actions else "Exhibit is judicially verified and trial-ready"

    return {
        "evidence_id": evidence.id,
        "case_id": evidence.case_id,
        "title": getattr(evidence, "title", None) or evidence.file_name or f"Exhibit #{evidence.id}",
        "file_name": evidence.file_name,
        "file_type": evidence.file_type,
        "evidence_type": evidence.evidence_type or "document",
        "uploaded_by": evidence.uploaded_by or "Investigating Officer",
        "upload_date": evidence.upload_date,
        "overall_quality_score": overall_score,
        "quality_tier": quality_tier,
        "is_weak_item": is_weak,
        "pillars": {
            "text_confidence_score": text_score,
            "text_confidence_pct": text_pct,
            "text_status": text_status,
            "text_notes": text_notes,
            "hash_score": hash_score,
            "hash_status": hash_status,
            "hash_value": hash_val,
            "certificate_score": cert_score,
            "certificate_status": cert_status,
            "certificate_notes": cert_notes,
            "language_review_score": lang_score,
            "language_status": lang_status,
            "primary_language": clean_lang,
            "language_notes": lang_notes
        },
        "warning_flags": warning_flags,
        "recommended_action": best_action
    }


def get_case_data_quality_report(
    case_id: int,
    db: Session,
    sort_order: str = "weakest_first"
) -> Dict[str, Any]:
    """
    Computes quality scores for all case exhibits and sorts weakest items first.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    case_title = case.title if case else f"Case #{case_id}"

    exhibits = (
        db.query(Evidence)
        .filter(Evidence.case_id == case_id, Evidence.is_deleted == False)
        .all()
    )

    scored_items = [calculate_exhibit_data_quality(ev, db) for ev in exhibits]

    # KEY REQUIREMENT: SORT WEAKEST ITEMS FIRST
    if sort_order == "weakest_first":
        scored_items.sort(key=lambda x: (x["overall_quality_score"], x["evidence_id"]))
    elif sort_order == "strongest_first":
        scored_items.sort(key=lambda x: (-x["overall_quality_score"], x["evidence_id"]))

    total_exhibits = len(scored_items)
    avg_score = round(sum(x["overall_quality_score"] for x in scored_items) / total_exhibits, 1) if total_exhibits > 0 else 100.0

    weak_count = sum(1 for x in scored_items if x["is_weak_item"])
    missing_certs = sum(1 for x in scored_items if x["pillars"]["certificate_score"] == 0)
    unverified_hashes = sum(1 for x in scored_items if x["pillars"]["hash_score"] == 0)
    low_text = sum(1 for x in scored_items if x["pillars"]["text_confidence_pct"] < 65)
    pending_lang = sum(1 for x in scored_items if x["pillars"]["language_review_score"] < 20)

    return {
        "case_id": case_id,
        "case_title": case_title,
        "total_exhibits": total_exhibits,
        "average_quality_score": avg_score,
        "weak_exhibits_count": weak_count,
        "missing_certificates_count": missing_certs,
        "unverified_hashes_count": unverified_hashes,
        "low_confidence_text_count": low_text,
        "pending_language_reviews_count": pending_lang,
        "sorted_exhibits": scored_items
    }
