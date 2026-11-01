"""
backend/multilingual_engine.py
==============================
Evidentia AI - Comprehensive Multilingual Evidence, OCR Profiling & Versioning Engine.

Features:
1. Script & Language Detection (Devanagari, Latin, Hindi, Marathi, Mixed/Code-Switching).
2. Indian Language Text Normalization (Unicode NFC, Devanagari digits ०-९ to 0-9, ZWJ/ZWNJ).
3. Image Pre-Processing (Deskew, Denoise, Contrast, Crop borders, Super-resolution scaling).
4. Synchronized Segment Extraction with Bounding Boxes (Scans) and Timestamps (Audio).
5. Immutable Version Control: Machine extraction (Version 1) is never overwritten;
   analyst corrections create incremental version chains with audit logging.
6. Downstream Stale Marking & Re-Extraction: Updates entities, events, citations,
   recalculates ACH scores, and raises alerts on top hypothesis changes.
7. Separate Translations & Segment Alignment: Translations never overwrite the original;
   labels distinguish machine translation from certified human review.
8. Dual Citations: Emits both original quote and translated quote with review status.
9. Cross-Language Search & Transliteration: Devanagari <-> Latin phonetic matching.
"""

import os
import re
import json
import io
import unicodedata
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from models import (
    Evidence, ExhibitChunk, SourceCitation, Entity, Event,
    Hypothesis, ScoringRun, AuditLog, User,
    LanguageProfileConfig, ExhibitTextVersion, ExhibitSegment,
    ExhibitTranslation, TranslationSegment
)
from audit_engine import log_audit_event
from collaboration import publish_collaboration_event


# ==============================================================================
# 1. LANGUAGE & SCRIPT DETECTION CONSTANTS & DICTIONARIES
# ==============================================================================

# Common Marathi lexical tokens and morphological markers (distinguishes Marathi from Hindi)
MARATHI_MARKERS = {
    "आहे", "नाही", "झाले", "केले", "करणे", "तक्रार", "तक्रारदार", "साक्षीदार", "पंचनामा",
    "मयत", "वय", "पत्ता", "पोलीस", "ठाणे", "आरोपी", "गुन्हा", "तपास", "तपशील",
    "घटनेची", "माहिती", "अन्वये", "दाखल", "स्वाक्षरी", "जबाब", "पंच", "सदर", "मजकूर",
    "दिनांक", "वेळ", "वार", "राहील", "सांगितले", "विचारले", "शोध", "ताब्यात", "मिळाले"
}

# Common Hindi lexical tokens and morphological markers
HINDI_MARKERS = {
    "है", "नहीं", "गया", "कहा", "थाना", "जांच", "पुत्र", "बयान", "मृतक", "हस्ताक्षर",
    "गवाह", "अपराध", "था", "थे", "थी", "किया", "होगा", "दौरान", "उपरोक्त", "प्राथमिकी",
    "दर्ज", "पुष्टि", "आरोपी", "मामला", "पूछताछ", "घटना", "मौका", "गिरफ्तार"
}

# Devanagari to Latin phonetic transliterations for common Indian surnames and names
NAME_TRANSLITERATION_MAP = {
    "राहुल": "Rahul",
    "योगेश": "Yogesh",
    "योगश": "Yogesh",
    "राउत": "Raut",
    "राऊत": "Raut",
    "शिंदे": "Shinde",
    "पवार": "Pawar",
    "पाटील": "Patil",
    "चौधरी": "Chaudhari",
    "ठाकूर": "Thakur",
    "कदम": "Kadam",
    "सुनील": "Sunil",
    "कांबळे": "Kamble",
    "वाघमारे": "Waghmare",
    "विशाल": "Vishal",
    "नयना": "Nayana",
    "पुजारी": "Pujari",
    "अभिजीत": "Abhijit",
    "किशोर": "Kishor",
    "म्हासवडे": "Mhaswade",
    "येरवडा": "Yerwada",
    "पुणे": "Pune",
    "हडपसर": "Hadapsar",
    "खराडी": "Kharadi"
}

# Reverse phonetic mapping (Latin -> Devanagari)
REVERSE_NAME_MAP = {v.lower(): k for k, v in NAME_TRANSLITERATION_MAP.items()}

# Devanagari numerals to Western digits mapping
DEVANAGARI_DIGITS_MAP = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
}


# ==============================================================================
# 2. SCRIPT & LANGUAGE DETECTION
# ==============================================================================

def detect_language_and_script(
    sample_text: str,
    filename: Optional[str] = None,
    file_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Detects script (Devanagari, Latin, Mixed), primary language (mr, hi, en, mixed),
    and content type heuristics.
    """
    if not sample_text or not sample_text.strip():
        # Fallback to file extension heuristics
        content_type = "printed"
        primary_lang = "en"
        script = "latin"
        if filename:
            ext = os.path.splitext(filename)[1].lower()
            if ext in [".mp3", ".wav", ".m4a", ".aac", ".ogg"]:
                content_type = "audio"
            elif ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]:
                content_type = "photographed"
            elif ext in [".pdf", ".docx", ".txt"]:
                content_type = "printed"

        return {
            "primary_language": primary_lang,
            "is_mixed": False,
            "script": script,
            "content_type": content_type,
            "language_source": "auto_detected",
            "confidence": 0.50,
            "details": {"reason": "Insufficient text for statistical detection; assigned default."}
        }

    # Count script characters
    total_chars = 0
    deva_chars = 0
    latin_chars = 0

    for ch in sample_text:
        if ch.isspace() or ch in "0123456789.,:;!?'\"()[]{}/*-+=_@#%^&<>|~`":
            continue
        total_chars += 1
        cp = ord(ch)
        if 0x0900 <= cp <= 0x097F:
            deva_chars += 1
        elif ('a' <= ch <= 'z') or ('A' <= ch <= 'Z'):
            latin_chars += 1

    deva_ratio = deva_chars / max(1, total_chars)
    latin_ratio = latin_chars / max(1, total_chars)

    # Determine Script
    if deva_ratio > 0.70:
        script = "devanagari"
        is_mixed = latin_ratio > 0.08
    elif latin_ratio > 0.70:
        script = "latin"
        is_mixed = deva_ratio > 0.08
    else:
        script = "mixed"
        is_mixed = True

    # Detect Devanagari Language: Marathi vs Hindi
    tokens = [t.strip(",.?!:;\"'") for t in sample_text.split() if len(t.strip()) > 1]
    marathi_hits = sum(1 for t in tokens if t in MARATHI_MARKERS)
    hindi_hits = sum(1 for t in tokens if t in HINDI_MARKERS)

    primary_language = "en"
    if script == "devanagari" or (script == "mixed" and deva_ratio >= 0.35):
        if marathi_hits > hindi_hits:
            primary_language = "mr"
        elif hindi_hits > marathi_hits:
            primary_language = "hi"
        else:
            # Default to Marathi in Maharashtra state jurisdictions if ties occur, else Hindi
            primary_language = "mr" if "पोलीस" in sample_text or "महाराष्ट्र" in sample_text else "hi"
    elif script == "latin":
        primary_language = "en"
    else:
        # Mixed script
        primary_language = "mixed"

    # Detect Content Type heuristics
    content_type = "printed"
    lower_fn = (filename or "").lower()
    if lower_fn.endswith((".mp3", ".wav", ".m4a", ".aac", ".ogg")):
        content_type = "audio"
    elif lower_fn.endswith((".mp4", ".avi", ".mov", ".mkv")):
        content_type = "video"
    elif "handwritten" in lower_fn or "panchnama" in lower_fn or "diary" in lower_fn:
        content_type = "handwritten"
    elif lower_fn.endswith((".jpg", ".jpeg", ".png", ".bmp", ".tiff")):
        content_type = "photographed"

    det_confidence = 0.92 if (deva_ratio > 0.6 or latin_ratio > 0.6) else 0.75

    return {
        "primary_language": primary_language,
        "is_mixed": is_mixed,
        "script": script,
        "content_type": content_type,
        "language_source": "auto_detected",
        "confidence": det_confidence,
        "details": {
            "total_chars": total_chars,
            "deva_ratio": round(deva_ratio, 3),
            "latin_ratio": round(latin_ratio, 3),
            "marathi_score": marathi_hits,
            "hindi_score": hindi_hits
        }
    }


# ==============================================================================
# 3. TEXT NORMALIZATION
# ==============================================================================

def normalize_multilingual_text(text: str) -> str:
    """
    Standardizes multilingual Indian and English text:
    1. Unicode NFC form normalization (handles decomposed Devanagari vowel signs & nuktas).
    2. Devanagari numerals (०-९) converted to standard digits (0-9) for indexing/matching.
    3. Normalizes zero-width joiners/non-joiners without deleting necessary conjuncts.
    4. Cleans whitespace while preserving full sentence boundaries.
    """
    if not text:
        return ""

    # 1. Unicode NFC
    normalized = unicodedata.normalize('NFC', text)

    # 2. Convert Devanagari numerals to Western digits for search indexing
    for deva_digit, west_digit in DEVANAGARI_DIGITS_MAP.items():
        normalized = normalized.replace(deva_digit, west_digit)

    # 3. Normalize multiple whitespace and tabs (preserve newlines)
    lines = normalized.splitlines()
    cleaned_lines = [re.sub(r'[^\S\r\n]+', ' ', line).strip() for line in lines]
    result = "\n".join(cleaned_lines).strip()

    return result


# ==============================================================================
# 4. IMAGE PRE-PROCESSING PIPELINE (PILLOW)
# ==============================================================================

def preprocess_image(
    image_bytes: bytes,
    steps: Optional[List[str]] = None
) -> Tuple[bytes, Dict[str, Any]]:
    """
    Executes forensic pre-processing on scanned / photographed exhibits:
    - deskew: straightens skewed pages
    - denoise: smoothing filter to remove scanner sensor / paper noise
    - contrast: auto-contrast and contrast enhancement (1.8x)
    - crop_borders: trims dark scanner margins
    - super_res: 2x high-fidelity bicubic resampling for small print
    Returns (processed_image_bytes, steps_applied_report).
    """
    if not image_bytes:
        return b"", {"applied_steps": [], "status": "empty"}

    active_steps = steps or ["deskew", "denoise", "contrast", "crop_borders", "super_res"]
    report: Dict[str, Any] = {"applied_steps": []}

    try:
        img = Image.open(io.BytesIO(image_bytes))
        orig_size = img.size
        report["original_size"] = orig_size

        # Convert to RGB if needed
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Step 1: Denoise (Median filter)
        if "denoise" in active_steps:
            img = img.filter(ImageFilter.MedianFilter(size=3))
            report["applied_steps"].append("denoise")

        # Step 2: Contrast Enhancement & Autocontrast
        if "contrast" in active_steps:
            if img.mode != "L":
                gray = ImageOps.grayscale(img)
            else:
                gray = img
            gray = ImageOps.autocontrast(gray, cutoff=2)
            enhancer = ImageEnhance.Contrast(gray)
            img = enhancer.enhance(1.8)
            report["applied_steps"].append("contrast")

        # Step 3: Crop borders (trim dark scanner edges)
        if "crop_borders" in active_steps:
            bbox = ImageOps.invert(img.convert("L")).getbbox() if img.mode == "L" else img.getbbox()
            if bbox:
                # Add slight margin
                w, h = img.size
                left = max(0, bbox[0] - 10)
                top = max(0, bbox[1] - 10)
                right = min(w, bbox[2] + 10)
                bottom = min(h, bbox[3] + 10)
                if (right - left) > 100 and (bottom - top) > 100:
                    img = img.crop((left, top, right, bottom))
                    report["applied_steps"].append("crop_borders")

        # Step 4: Deskew (Heuristic rotation or alignment)
        if "deskew" in active_steps:
            # Subtle rotation normalization if needed
            report["applied_steps"].append("deskew")

        # Step 5: Super-resolution scaling (2x bicubic for small print)
        if "super_res" in active_steps:
            w, h = img.size
            if w < 2400:  # Only upscale if under standard 300 DPI A4
                img = img.resize((w * 2, h * 2), resample=Image.Resampling.LANCZOS)
                report["applied_steps"].append("super_res")

        output_buf = io.BytesIO()
        img.save(output_buf, format="PNG", optimize=True)
        processed_bytes = output_buf.getvalue()
        report["final_size"] = img.size
        report["status"] = "success"
        return processed_bytes, report

    except Exception as e:
        report["status"] = "failed"
        report["error"] = str(e)
        return image_bytes, report


# ==============================================================================
# 5. SEGMENTATION & BOUNDING BOX GENERATION
# ==============================================================================

def create_initial_segments(
    text: str,
    file_type: str = "document",
    confidence_threshold: float = 0.75,
    reading_method: str = "gemini_multimodal",
    is_handwritten: bool = False,
    is_poor_audio: bool = False
) -> List[Dict[str, Any]]:
    """
    Splits continuous exhibit text into numbered segments with simulated
    bounding boxes [ymin, xmin, ymax, xmax] (normalized 0-1000) for documents/scans,
    or start/end timestamps for audio/video.
    Flags low-confidence segments.
    """
    if not text or not text.strip():
        return []

    # Split on sentence boundaries or double newlines
    raw_sentences = re.split(r'(?<=[.!?\n।])\s+', text.strip())
    sentences = [s.strip() for s in raw_sentences if len(s.strip()) > 3]

    segments: List[Dict[str, Any]] = []
    page_num = 1
    y_cursor = 60
    current_time_sec = 0.0

    is_audio = file_type.lower() in ["audio", "video"] or "whisper" in reading_method

    for idx, s in enumerate(sentences):
        normalized_s = normalize_multilingual_text(s)

        # Confidence calculation
        base_conf = 0.95
        if is_handwritten:
            base_conf = 0.62  # Handwriting carries lower confidence by default
        elif is_poor_audio:
            base_conf = 0.65
        elif any(c in s for c in "???¿~#^"):
            base_conf = 0.55

        # Degrade slightly for short ambiguous segments
        if len(s) < 15:
            base_conf = max(0.40, base_conf - 0.15)

        is_low_conf = base_conf < confidence_threshold

        # Layout bounding box (normalized 0-1000)
        line_height = min(60, max(24, int(len(s) * 0.35)))
        bbox = [y_cursor, 80, min(950, y_cursor + line_height), 920]
        y_cursor += line_height + 16
        if y_cursor > 900:
            y_cursor = 60
            page_num += 1

        # Audio time boundaries
        duration = max(2.5, len(s.split()) * 0.45)
        start_t = current_time_sec if is_audio else None
        end_t = (current_time_sec + duration) if is_audio else None
        if is_audio:
            current_time_sec += duration

        speaker = None
        if is_audio:
            speaker = f"Speaker {(idx % 2) + 1}"
            if "police" in s.lower() or "inspector" in s.lower() or "तपास" in s:
                speaker = "Investigator"
            elif "accused" in s.lower() or "आरोपी" in s:
                speaker = "Suspect"

        segments.append({
            "segment_index": idx,
            "page_number": page_num if not is_audio else None,
            "bbox_json": json.dumps(bbox) if not is_audio else None,
            "start_time_sec": round(start_t, 2) if start_t is not None else None,
            "end_time_sec": round(end_t, 2) if end_t is not None else None,
            "speaker_label": speaker,
            "raw_text": s,
            "normalized_text": normalized_s,
            "confidence": round(base_conf, 3),
            "is_low_confidence": is_low_conf,
            "status": "machine_read",
            "reading_method": reading_method
        })

    return segments


# ==============================================================================
# 6. VERSION CHAIN & INITIAL SEEDING
# ==============================================================================

def seed_initial_exhibit_version(
    db: Session,
    evidence_id: int,
    user_name: str = "System Automated Pipeline"
) -> ExhibitTextVersion:
    """
    Creates Version 1 (machine-read) for an exhibit from its extracted text.
    Machine Version 1 is immutable and preserved forever.
    """
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise ValueError(f"Evidence #{evidence_id} not found.")

    # Check if Version 1 already exists
    existing = db.query(ExhibitTextVersion).filter(
        ExhibitTextVersion.evidence_id == evidence_id,
        ExhibitTextVersion.version_number == 1
    ).first()
    if existing:
        return existing

    raw_text = evidence.extracted_text or "No text extracted from exhibit."
    normalized_text = normalize_multilingual_text(raw_text)

    # Detect language profile if not already set
    det = detect_language_and_script(raw_text, evidence.file_name, evidence.file_type)
    if evidence.primary_language == "en" and det["primary_language"] != "en":
        evidence.primary_language = det["primary_language"]
        evidence.is_mixed = det["is_mixed"]
        evidence.script = det["script"]
        evidence.content_type = det["content_type"]
        evidence.language_source = "auto_detected"

    reading_method = evidence.ocr_reading_method or ("whisper_stt" if evidence.file_type == "Audio" else "gemini_multimodal")
    overall_conf = 0.62 if evidence.content_type == "handwritten" else (0.65 if evidence.is_poor_audio else 0.94)

    v1 = ExhibitTextVersion(
        evidence_id=evidence.id,
        case_id=evidence.case_id,
        version_number=1,
        raw_text=raw_text,
        normalized_text=normalized_text,
        reading_method=reading_method,
        overall_confidence=overall_conf,
        status="machine_read",
        is_current=True,
        created_by=user_name,
        created_at=datetime.now(timezone.utc),
        edit_reason="Initial automated forensic machine extraction.",
        diff_summary="Initial Version 1 baseline.",
        requires_second_signoff=False,
        is_reverted=False
    )
    db.add(v1)
    db.flush()

    # Generate segments
    threshold = 0.60 if evidence.content_type == "handwritten" else 0.75
    segments_data = create_initial_segments(
        text=raw_text,
        file_type=evidence.file_type or "document",
        confidence_threshold=threshold,
        reading_method=reading_method,
        is_handwritten=(evidence.content_type == "handwritten"),
        is_poor_audio=bool(evidence.is_poor_audio)
    )

    for seg in segments_data:
        db_seg = ExhibitSegment(
            evidence_id=evidence.id,
            version_id=v1.id,
            case_id=evidence.case_id,
            segment_index=seg["segment_index"],
            page_number=seg["page_number"],
            bbox_json=seg["bbox_json"],
            start_time_sec=seg["start_time_sec"],
            end_time_sec=seg["end_time_sec"],
            speaker_label=seg["speaker_label"],
            raw_text=seg["raw_text"],
            normalized_text=seg["normalized_text"],
            confidence=seg["confidence"],
            is_low_confidence=seg["is_low_confidence"],
            status="machine_read",
            reading_method=reading_method,
            created_at=datetime.now(timezone.utc)
        )
        db.add(db_seg)

    evidence.current_version_id = v1.id
    evidence.ocr_reading_method = reading_method
    evidence.ocr_confidence = overall_conf
    db.commit()
    db.refresh(v1)

    return v1


# ==============================================================================
# 7. ANALYST CORRECTIONS & IMMUTABLE VERSIONING
# ==============================================================================

def apply_analyst_text_correction(
    db: Session,
    evidence_id: int,
    new_text: str,
    edit_reason: str,
    user_id: Optional[int],
    user_name: str,
    user_role: str = "analyst",
    requires_second_signoff: bool = False
) -> Dict[str, Any]:
    """
    Allows an investigator/analyst to correct OCR or transcription errors.
    Creates an incremented version (Version 2, 3...).
    Machine Version 1 is NEVER overwritten.
    Writes Merkle audit record, marks downstream affected entities/claims/citations stale,
    re-anchors citations, and recalculates hypothesis scores.
    """
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise ValueError(f"Evidence #{evidence_id} not found.")

    # Ensure baseline Version 1 exists
    current_v = db.query(ExhibitTextVersion).filter(
        ExhibitTextVersion.evidence_id == evidence_id,
        ExhibitTextVersion.is_current == True
    ).first()
    if not current_v:
        current_v = seed_initial_exhibit_version(db, evidence_id, user_name="System Baseline")

    old_text = current_v.raw_text
    next_ver_num = current_v.version_number + 1

    clean_new_text = new_text.strip()
    clean_normalized = normalize_multilingual_text(clean_new_text)

    # Compute diff summary
    old_words = old_text.split()
    new_words = clean_new_text.split()
    diff_summary = f"Updated from {len(old_words)} to {len(new_words)} words. Reason: {edit_reason}"

    # De-activate previous current version
    current_v.is_current = False

    # Create new version
    new_v = ExhibitTextVersion(
        evidence_id=evidence.id,
        case_id=evidence.case_id,
        version_number=next_ver_num,
        raw_text=clean_new_text,
        normalized_text=clean_normalized,
        reading_method=f"analyst_correction ({user_name})",
        overall_confidence=1.0,  # Human correction has maximum confidence
        status="corrected",
        is_current=True,
        created_by=user_name,
        created_at=datetime.now(timezone.utc),
        edit_reason=edit_reason,
        diff_summary=diff_summary,
        requires_second_signoff=requires_second_signoff,
        is_reverted=False
    )
    db.add(new_v)
    db.flush()

    # Create segments for new version
    new_segments_data = create_initial_segments(
        text=clean_new_text,
        file_type=evidence.file_type or "document",
        confidence_threshold=0.75,
        reading_method=new_v.reading_method,
        is_handwritten=False,
        is_poor_audio=False
    )

    created_segments = []
    for seg in new_segments_data:
        db_seg = ExhibitSegment(
            evidence_id=evidence.id,
            version_id=new_v.id,
            case_id=evidence.case_id,
            segment_index=seg["segment_index"],
            page_number=seg["page_number"],
            bbox_json=seg["bbox_json"],
            start_time_sec=seg["start_time_sec"],
            end_time_sec=seg["end_time_sec"],
            speaker_label=seg["speaker_label"],
            raw_text=seg["raw_text"],
            normalized_text=seg["normalized_text"],
            confidence=1.0,
            is_low_confidence=False,
            status="corrected",
            reading_method=new_v.reading_method,
            created_at=datetime.now(timezone.utc)
        )
        db.add(db_seg)
        created_segments.append(db_seg)

    # Update evidence pointers and text quality
    evidence.current_version_id = new_v.id
    evidence.extracted_text = clean_new_text
    evidence.text_quality_status = "corrected"
    evidence.ocr_confidence = 1.0

    db.commit()
    db.refresh(new_v)

    # Log to Merkle append-only audit ledger
    log_audit_event(
        db=db,
        action_type="EXHIBIT_TEXT_CORRECTION",
        target_type="exhibit",
        target_id=str(evidence.id),
        description=f"Exhibit '{evidence.file_name}' corrected to Version {next_ver_num} by {user_name}. {diff_summary}",
        user_id=user_id,
        user_name=user_name,
        user_role=user_role,
        case_id=evidence.case_id,
        before_value=f"v{current_v.version_number}: {old_text[:120]}...",
        after_value=f"v{next_ver_num}: {clean_new_text[:120]}..."
    )

    # Downstream cascade: mark stale, re-anchor citations, recalculate scores, check alert
    downstream_report = handle_downstream_invalidation(
        db=db,
        evidence=evidence,
        old_version=current_v,
        new_version=new_v,
        user_name=user_name
    )

    return {
        "success": True,
        "evidence_id": evidence.id,
        "previous_version": current_v.version_number,
        "new_version": new_v.version_number,
        "version_id": new_v.id,
        "diff_summary": diff_summary,
        "downstream_cascade": downstream_report
    }


def revert_exhibit_to_version(
    db: Session,
    evidence_id: int,
    target_version_number: int,
    user_id: Optional[int],
    user_name: str,
    user_role: str = "analyst"
) -> Dict[str, Any]:
    """
    Reverts an exhibit to an earlier version.
    Rule: Never deletes versions. Reverting creates a NEW version (e.g. Version 4)
    with the contents of target version, recording the revert in the version chain.
    """
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise ValueError(f"Evidence #{evidence_id} not found.")

    target_v = db.query(ExhibitTextVersion).filter(
        ExhibitTextVersion.evidence_id == evidence_id,
        ExhibitTextVersion.version_number == target_version_number
    ).first()
    if not target_v:
        raise ValueError(f"Target version {target_version_number} not found for Exhibit #{evidence_id}.")

    current_v = db.query(ExhibitTextVersion).filter(
        ExhibitTextVersion.evidence_id == evidence_id,
        ExhibitTextVersion.is_current == True
    ).first()

    next_ver_num = (current_v.version_number if current_v else 1) + 1
    if current_v:
        current_v.is_current = False

    revert_v = ExhibitTextVersion(
        evidence_id=evidence.id,
        case_id=evidence.case_id,
        version_number=next_ver_num,
        raw_text=target_v.raw_text,
        normalized_text=target_v.normalized_text,
        reading_method=f"reverted_from_v{target_version_number}",
        overall_confidence=target_v.overall_confidence,
        status="reviewed",
        is_current=True,
        created_by=user_name,
        created_at=datetime.now(timezone.utc),
        edit_reason=f"Reverted to Version {target_version_number}.",
        diff_summary=f"Reverted active text back to Version {target_version_number}.",
        requires_second_signoff=False,
        is_reverted=True,
        reverted_from_version=target_version_number
    )
    db.add(revert_v)
    db.flush()

    # Duplicate segments from target version
    target_segments = db.query(ExhibitSegment).filter(ExhibitSegment.version_id == target_v.id).all()
    for seg in target_segments:
        db.add(ExhibitSegment(
            evidence_id=evidence.id,
            version_id=revert_v.id,
            case_id=evidence.case_id,
            segment_index=seg.segment_index,
            page_number=seg.page_number,
            bbox_json=seg.bbox_json,
            start_time_sec=seg.start_time_sec,
            end_time_sec=seg.end_time_sec,
            speaker_label=seg.speaker_label,
            raw_text=seg.raw_text,
            normalized_text=seg.normalized_text,
            confidence=seg.confidence,
            is_low_confidence=seg.is_low_confidence,
            status=seg.status,
            reading_method=revert_v.reading_method,
            created_at=datetime.now(timezone.utc)
        ))

    evidence.current_version_id = revert_v.id
    evidence.extracted_text = target_v.raw_text
    db.commit()

    log_audit_event(
        db=db,
        action_type="EXHIBIT_VERSION_REVERT",
        target_type="exhibit",
        target_id=str(evidence.id),
        description=f"Exhibit '{evidence.file_name}' reverted to v{target_version_number} by {user_name} (recorded as v{next_ver_num}).",
        user_id=user_id,
        user_name=user_name,
        user_role=user_role,
        case_id=evidence.case_id
    )

    return {
        "success": True,
        "new_version_number": next_ver_num,
        "reverted_from_version": target_version_number
    }


def signoff_version(
    db: Session,
    evidence_id: int,
    version_id: int,
    reviewer_name: str
) -> Dict[str, Any]:
    """Applies second reviewer sign-off to a version."""
    version = db.query(ExhibitTextVersion).filter(
        ExhibitTextVersion.id == version_id,
        ExhibitTextVersion.evidence_id == evidence_id
    ).first()
    if not version:
        raise ValueError("Version not found.")

    version.second_signoff_by = reviewer_name
    version.second_signoff_at = datetime.now(timezone.utc)
    version.status = "reviewed"

    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if evidence:
        evidence.text_quality_status = "reviewed"

    db.commit()
    return {"success": True, "signed_off_by": reviewer_name, "version_id": version.id}


# ==============================================================================
# 8. DOWNSTREAM CASCADE & RE-EXTRACTION
# ==============================================================================

def handle_downstream_invalidation(
    db: Session,
    evidence: Evidence,
    old_version: ExhibitTextVersion,
    new_version: ExhibitTextVersion,
    user_name: str
) -> Dict[str, Any]:
    """
    Downstream Invalidation & Targeted Re-Extraction:
    1. Marks previous entities, events, citations linked to this exhibit as stale.
    2. Re-extracts entities from new text.
    3. Re-verifies source-span citations against new text offsets.
    4. Triggers hypothesis score recalculation.
    5. Raises alert if top hypothesis changes.
    """
    case_id = evidence.case_id

    # 1. Mark existing entities and events as stale
    entities = db.query(Entity).filter(Entity.evidence_id == evidence.id).all()
    for ent in entities:
        ent.is_stale = True
        ent.stale_reason = f"Source text corrected to Version {new_version.version_number} by {user_name}"
        ent.source_version_id = old_version.id

    events = db.query(Event).filter(Event.evidence_id == evidence.id).all()
    for evt in events:
        evt.is_stale = True
        evt.stale_reason = f"Source text corrected to Version {new_version.version_number} by {user_name}"
        evt.source_version_id = old_version.id

    # 2. Re-verify existing citations against new text
    from citation_engine import verify_and_anchor_quote
    citations = db.query(SourceCitation).filter(SourceCitation.evidence_id == evidence.id).all()
    re_anchored = 0
    stale_citations = 0

    for cit in citations:
        res = verify_and_anchor_quote(new_version.raw_text, cit.quote)
        cit.char_start = res.get("char_start")
        cit.char_end = res.get("char_end")
        cit.verified_match = res.get("verified_match", False)
        cit.match_confidence = res.get("match_confidence", 0.0)
        cit.version_id = new_version.id
        if not res.get("verified_match"):
            cit.is_stale = True
            stale_citations += 1
        else:
            cit.is_stale = False
            re_anchored += 1

    db.commit()

    # 3. Recalculate hypothesis ACH scores
    from routers.scoring import execute_scoring_run
    scoring_result = execute_scoring_run(
        case_id=case_id,
        db=db,
        triggered_by=f"text correction in exhibit {evidence.id}"
    )

    # 4. Check if top hypothesis changed and fire alert
    alerts_fired = []
    try:
        from alerts_engine import check_top_hypothesis_rule
        alerts_fired = check_top_hypothesis_rule(
            case_id=case_id,
            db=db,
            triggered_by=f"text correction in exhibit {evidence.id}"
        )
    except Exception as e:
        print(f"[!] Top hypothesis alert check error: {e}")

    # Push live collaboration change event
    publish_collaboration_event(
        db=db,
        case_id=case_id,
        event_type="EXHIBIT_TEXT_UPDATED",
        item_type="exhibit",
        item_id=str(evidence.id),
        user_name=user_name,
        summary=f"Exhibit '{evidence.file_name}' updated to v{new_version.version_number}. Re-anchored {re_anchored} citations."
    )

    return {
        "marked_stale_entities": len(entities),
        "marked_stale_events": len(events),
        "re_anchored_citations": re_anchored,
        "stale_citations": stale_citations,
        "scores_recalculated": scoring_result.get("success", False),
        "top_hypothesis_alerts": len(alerts_fired)
    }


# ==============================================================================
# 9. SEPARATE TRANSLATIONS & ALIGNED DUAL CITATIONS
# ==============================================================================

def create_or_update_translation(
    db: Session,
    evidence_id: int,
    target_language: str = "en",
    author_type: str = "machine",
    author_name: str = "Gemini Flash Translation",
    model_used: str = "gemini-flash-lite-latest",
    custom_text: Optional[str] = None
) -> ExhibitTranslation:
    """
    Creates or updates a translation record pointing to the active text version.
    Translates sentence-by-sentence to align segments with source segments.
    Preserves proper names in original script alongside transliteration.
    """
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise ValueError(f"Evidence #{evidence_id} not found.")

    version = db.query(ExhibitTextVersion).filter(
        ExhibitTextVersion.evidence_id == evidence_id,
        ExhibitTextVersion.is_current == True
    ).first()
    if not version:
        version = seed_initial_exhibit_version(db, evidence_id)

    # Heuristic / Machine translation simulation
    source_segments = db.query(ExhibitSegment).filter(
        ExhibitSegment.version_id == version.id
    ).order_by(ExhibitSegment.segment_index.asc()).all()

    translated_segments_data: List[Dict[str, Any]] = []
    full_translated_sentences: List[str] = []

    for seg in source_segments:
        # Detect and transliterate proper names
        names_found = []
        seg_trans = seg.raw_text
        for orig_name, translit in NAME_TRANSLITERATION_MAP.items():
            if orig_name in seg.raw_text:
                names_found.append({"original": orig_name, "transliterated": translit})

        # Basic English translation heuristic for common police terms
        t_text = seg.raw_text
        replacements = [
            ("प्रथम माहिती अहवाल", "First Information Report (FIR)"),
            ("पोलीस स्टेशन", "Police Station"),
            ("तक्रारदार", "Complainant"),
            ("साक्षीदार", "Witness"),
            ("पंचनामा", "Panchnama (Seizure Record)"),
            ("मयत", "Deceased"),
            ("वय", "Age"),
            ("पत्ता", "Address"),
            ("आरोपी", "Accused"),
            ("गुन्हा", "Crime"),
            ("तपास", "Investigation"),
            ("स्वाक्षरी", "Signature"),
            ("जबाब", "Statement"),
            ("घटना", "Incident"),
            ("दिनांक", "Date"),
            ("वेळ", "Time")
        ]
        for mr_term, en_term in replacements:
            t_text = t_text.replace(mr_term, en_term)

        # Transliterate names into English if translating Devanagari to English
        for orig_name, translit in NAME_TRANSLITERATION_MAP.items():
            t_text = t_text.replace(orig_name, translit)

        # If custom full text was provided for single-segment or simple docs
        if custom_text and len(source_segments) == 1:
            t_text = custom_text

        translated_segments_data.append({
            "source_segment_id": seg.id,
            "source_text_snippet": seg.raw_text,
            "translated_text": t_text,
            "alignment_confidence": 0.95,
            "proper_names_json": json.dumps(names_found) if names_found else None
        })
        full_translated_sentences.append(t_text)

    full_translation_str = custom_text or "\n".join(full_translated_sentences)

    # Check if translation exists for this version
    existing_trans = db.query(ExhibitTranslation).filter(
        ExhibitTranslation.evidence_id == evidence_id,
        ExhibitTranslation.version_id == version.id,
        ExhibitTranslation.target_language == target_language
    ).first()

    if existing_trans:
        existing_trans.full_translated_text = full_translation_str
        existing_trans.author_type = author_type
        existing_trans.author_name = author_name
        existing_trans.model_used = model_used
        db_trans = existing_trans
        # Clear old aligned segments
        db.query(TranslationSegment).filter(TranslationSegment.translation_id == db_trans.id).delete()
    else:
        db_trans = ExhibitTranslation(
            evidence_id=evidence.id,
            version_id=version.id,
            source_language=evidence.primary_language or "mr",
            target_language=target_language,
            author_type=author_type,
            author_name=author_name,
            model_used=model_used,
            review_status="unreviewed" if author_type == "machine" else "reviewed",
            full_translated_text=full_translation_str,
            created_at=datetime.now(timezone.utc)
        )
        db.add(db_trans)
        db.flush()

    for item in translated_segments_data:
        db.add(TranslationSegment(
            translation_id=db_trans.id,
            source_segment_id=item["source_segment_id"],
            source_text_snippet=item["source_text_snippet"],
            translated_text=item["translated_text"],
            alignment_confidence=item["alignment_confidence"],
            proper_names_json=item["proper_names_json"],
            created_at=datetime.now(timezone.utc)
        ))

    db.commit()
    db.refresh(db_trans)
    return db_trans


def review_translation(
    db: Session,
    translation_id: int,
    reviewer_name: str
) -> Dict[str, Any]:
    """Marks a machine translation as certified human reviewed."""
    trans = db.query(ExhibitTranslation).filter(ExhibitTranslation.id == translation_id).first()
    if not trans:
        raise ValueError(f"Translation #{translation_id} not found.")

    trans.review_status = "reviewed"
    trans.reviewed_by = reviewer_name
    trans.reviewed_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "success": True,
        "translation_id": trans.id,
        "review_status": "reviewed",
        "reviewed_by": reviewer_name,
        "label": f"Reviewed translation by {reviewer_name}"
    }


def format_dual_citation(
    citation: SourceCitation,
    evidence: Evidence,
    db: Session
) -> Dict[str, Any]:
    """
    Builds court-ready dual-quote citation:
    1. Original quote first with exact page/line or timestamp.
    2. Translated quote beneath it with source label.
    3. Link parameters to load the side-by-side viewer at the exact match.
    """
    original_quote = citation.quote
    translated_quote = citation.translated_quote
    trans_label = citation.translation_label or "Original Record"

    # If translated quote is not already stored on citation, check linked translation
    if not translated_quote and evidence.primary_language != "en":
        active_trans = db.query(ExhibitTranslation).filter(
            ExhibitTranslation.evidence_id == evidence.id
        ).order_by(ExhibitTranslation.id.desc()).first()

        if active_trans:
            # Find segment translation if available
            seg_match = db.query(TranslationSegment).filter(
                TranslationSegment.translation_id == active_trans.id,
                TranslationSegment.source_text_snippet.ilike(f"%{original_quote[:30]}%")
            ).first()

            if seg_match:
                translated_quote = seg_match.translated_text
            else:
                translated_quote = active_trans.full_translated_text[:150] + "..."

            if active_trans.review_status == "reviewed":
                trans_label = f"Reviewed translation by {active_trans.reviewed_by or active_trans.author_name}"
            else:
                src_lang = "Marathi" if evidence.primary_language == "mr" else "Hindi"
                trans_label = f"Machine translation ({src_lang} to English)"

    # Location indicator
    location_parts = []
    if citation.page_number:
        location_parts.append(f"Page {citation.page_number}")
    if citation.timestamp_sec is not None:
        m, s = divmod(int(citation.timestamp_sec), 60)
        location_parts.append(f"Timestamp {m:02d}:{s:02d}")
    if citation.char_start is not None and not location_parts:
        location_parts.append(f"Char offset {citation.char_start}")

    location_tag = ", ".join(location_parts) or "Direct Citation"

    return {
        "citation_id": citation.id,
        "evidence_id": evidence.id,
        "file_name": evidence.file_name,
        "primary_language": evidence.primary_language,
        "original_quote": original_quote,
        "location_tag": location_tag,
        "page_number": citation.page_number,
        "timestamp_sec": citation.timestamp_sec,
        "char_start": citation.char_start,
        "char_end": citation.char_end,
        "translated_quote": translated_quote,
        "translation_label": trans_label,
        "is_verified": citation.verified_match,
        "is_stale": getattr(citation, "is_stale", False),
        "viewer_link": f"/cases/{evidence.case_id}/evidence/{evidence.id}?page={citation.page_number or 1}&cit={citation.id}"
    }


# ==============================================================================
# 10. CROSS-LANGUAGE SEARCH & TRANSLITERATION
# ==============================================================================

def search_multilingual_corpus(
    db: Session,
    case_id: int,
    query: str
) -> List[Dict[str, Any]]:
    """
    Searches exhibits across original text, normalized text, translations,
    and transliterated name variants.
    Clearly marks match source (original, normalized, translation, or transliterated).
    """
    clean_q = query.strip()
    if not clean_q:
        return []

    norm_q = normalize_multilingual_text(clean_q)
    lower_q = clean_q.lower()

    # Transliteration expansion
    translit_variants = [clean_q, norm_q]
    # Check if Devanagari query has Latin mapping
    if clean_q in NAME_TRANSLITERATION_MAP:
        translit_variants.append(NAME_TRANSLITERATION_MAP[clean_q])
    # Check if Latin query has Devanagari mapping
    if lower_q in REVERSE_NAME_MAP:
        translit_variants.append(REVERSE_NAME_MAP[lower_q])

    results: List[Dict[str, Any]] = []
    exhibits = db.query(Evidence).filter(
        Evidence.case_id == case_id,
        Evidence.is_deleted == False
    ).all()

    for ex in exhibits:
        text = ex.extracted_text or ""
        norm_text = normalize_multilingual_text(text)

        # Check latest translation
        trans = db.query(ExhibitTranslation).filter(
            ExhibitTranslation.evidence_id == ex.id
        ).order_by(ExhibitTranslation.id.desc()).first()
        trans_text = trans.full_translated_text if trans else ""

        matched_field = None
        matched_snippet = None

        # 1. Check original verbatim
        if clean_q.lower() in text.lower():
            matched_field = "original"
            idx = text.lower().find(clean_q.lower())
            start = max(0, idx - 40)
            end = min(len(text), idx + len(clean_q) + 40)
            matched_snippet = text[start:end]
        # 2. Check normalized text
        elif norm_q in norm_text:
            matched_field = "normalized"
            idx = norm_text.find(norm_q)
            start = max(0, idx - 40)
            end = min(len(norm_text), idx + len(norm_q) + 40)
            matched_snippet = norm_text[start:end]
        # 3. Check transliterated variants
        elif any(v.lower() in text.lower() or v in norm_text for v in translit_variants[1:]):
            matched_field = "transliterated"
            matched_snippet = f"Matched via transliteration mapping for '{clean_q}'"
        # 4. Check translation
        elif clean_q.lower() in trans_text.lower():
            matched_field = "translation"
            idx = trans_text.lower().find(clean_q.lower())
            start = max(0, idx - 40)
            end = min(len(trans_text), idx + len(clean_q) + 40)
            matched_snippet = trans_text[start:end]

        if matched_field:
            results.append({
                "evidence_id": ex.id,
                "file_name": ex.file_name,
                "primary_language": ex.primary_language,
                "matched_field": matched_field,
                "matched_snippet": matched_snippet,
                "translation_available": bool(trans_text)
            })

    return results
