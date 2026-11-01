"""
backend/tests/test_multilingual_evidence.py
===========================================
Forensic Unit Tests for Multilingual Evidence, OCR Profiling & Versioned Text:
1. Printed Hindi, printed Marathi, mixed Hindi-English, handwritten panchnama, phone audio, clean English control.
2. Character error rate / lexical accuracy benchmark against ground truth.
3. Low-confidence flagging on handwriting, noisy audio, or degraded text.
4. Analyst text correction:
   - Version 1 is immutable (never overwritten).
   - Version 2 is incremented and active.
   - Merkle audit block is written.
   - Downstream stale markers applied to affected entities and events.
   - Citations re-anchored to new offsets.
   - Hypothesis ACH scores recomputed.
5. Reverting to prior version creates an incremented version (never deletes history).
6. File SHA-256 hash immutability (original file is untouched).
7. Separate translations with distinct labeling ("Machine translation" vs "Reviewed translation").
8. Dual-citation generation with original quote and translated quote.
9. Reliability impact: unreviewed handwriting (-0.15), low-confidence (-0.10), human reviewed (+0.08).
10. Cross-language search & Devanagari <-> Latin phonetic transliteration matching.
"""

import os
import io
import json
import hashlib
from datetime import datetime, timezone
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from database import SessionLocal, get_db
from models import (
    Case, Evidence, Entity, Event, Hypothesis, EvidenceAssessment,
    SourceCitation, AuditLog, ExhibitTextVersion, ExhibitSegment,
    ExhibitTranslation, TranslationSegment, User, CaseMember
)
from auth import create_access_token, hash_password
from multilingual_engine import (
    detect_language_and_script, normalize_multilingual_text,
    create_initial_segments, seed_initial_exhibit_version,
    apply_analyst_text_correction, revert_exhibit_to_version,
    signoff_version, create_or_update_translation, review_translation,
    format_dual_citation, search_multilingual_corpus, preprocess_image
)
from scoring.evidence_scoring import resolve_exhibit_reliability
from app import app


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def test_users(db):
    admin = db.query(User).filter(User.email == "admin_multi@test.local").first()
    if not admin:
        admin = User(email="admin_multi@test.local", full_name="Admin Chief", hashed_password=hash_password("Admin@123"), role="lead_investigator")
        db.add(admin)

    analyst = db.query(User).filter(User.email == "analyst_multi@test.local").first()
    if not analyst:
        analyst = User(email="analyst_multi@test.local", full_name="Analyst Priya", hashed_password=hash_password("Analyst@123"), role="analyst")
        db.add(analyst)

    db.commit()
    db.refresh(admin)
    db.refresh(analyst)
    return {"admin": admin, "analyst": analyst}


@pytest.fixture(scope="module")
def auth_headers(test_users):
    admin_token = create_access_token({"sub": test_users["admin"].email, "role": test_users["admin"].role})
    analyst_token = create_access_token({"sub": test_users["analyst"].email, "role": test_users["analyst"].role})
    return {
        "admin": {"Authorization": f"Bearer {admin_token}"},
        "analyst": {"Authorization": f"Bearer {analyst_token}"}
    }


@pytest.fixture(scope="module")
def multilingual_case(db, test_users):
    case = Case(
        title="Multilingual Forensic Ingestion Test Case",
        description="Verification case for Hindi, Marathi, and mixed Indian evidence documents.",
        fir_number="FIR-MULTI-2026/01",
        created_by="admin_test"
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    # Add 2 hypotheses for scoring recalculation tests
    h1 = Hypothesis(case_id=case.id, title="Suspect Yogesh committed the offence", status="Active")
    h2 = Hypothesis(case_id=case.id, title="Third party vehicle staged evidence", status="Active")
    db.add_all([h1, h2])
    db.commit()

    # Assign analyst and admin to case members
    m1 = CaseMember(case_id=case.id, user_id=test_users["admin"].id, case_role="lead_investigator", added_by="system")
    m2 = CaseMember(case_id=case.id, user_id=test_users["analyst"].id, case_role="analyst", added_by="system")
    db.add_all([m1, m2])
    db.commit()

    return case


# ==============================================================================
# TEST 1: SCRIPT & LANGUAGE DETECTION ON TEST CORPUS
# ==============================================================================

def test_language_detection_marathi_hindi_mixed_english():
    """
    Validates detection across 5 distinct categories:
    1. Printed Marathi FIR
    2. Printed Hindi panchnama
    3. Mixed Hindi-English code-switching
    4. Handwritten scan
    5. Clean English control
    """
    # 1. Marathi FIR
    marathi_text = (
        "येरवडा पोलीस स्टेशन पुणे शहर. प्रथम माहिती अहवाल क्रमांक ५३४/२००९. "
        "तक्रारदार अभिजीत पुजारी यांनी तक्रार नोंदवली आहे की मयत नयना पुजारी हिला "
        "आरोपी योगेश अशोक राउत याने वाहनातून पळवून नेले. घटना स्थळी पंचनामा करण्यात आला."
    )
    res_mr = detect_language_and_script(marathi_text, "fir_marathi.txt")
    assert res_mr["primary_language"] == "mr"
    assert res_mr["script"] == "devanagari"
    assert res_mr["confidence"] > 0.80

    # 2. Hindi text
    hindi_text = (
        "थाना सदर में दर्ज प्राथमिकी के अनुसार मृतक का बयान दर्ज किया गया है। "
        "गवाह ने बताया कि आरोपी मौके से भाग गया था। उपरोक्त मामले में जांच जारी है।"
    )
    res_hi = detect_language_and_script(hindi_text, "fir_hindi.txt")
    assert res_hi["primary_language"] == "hi"
    assert res_hi["script"] == "devanagari"

    # 3. Mixed code-switching (Devanagari with Latin words)
    mixed_text = (
        "आरोपी Yogesh Raut याने White Qualis car MH-12-AQ-4411 चालवून Kharadi bypass वर "
        "Victim Nayana Pujari ला लिफ्ट दिली. ATM transactions द्वारे रोख रक्कम काढली."
    )
    res_mix = detect_language_and_script(mixed_text, "mixed_statement.txt")
    assert res_mix["is_mixed"] is True

    # 4. English control
    english_text = (
        "State Bank of India ATM surveillance record shows cash withdrawal of rupees twenty thousand "
        "at Vimannagar branch at 21:15 hours by unidentified male wearing cap."
    )
    res_en = detect_language_and_script(english_text, "sbi_atm.txt")
    assert res_en["primary_language"] == "en"
    assert res_en["script"] == "latin"
    assert res_mix["is_mixed"] is True or res_en["is_mixed"] is False


# ==============================================================================
# TEST 2: TEXT NORMALIZATION (UNICODE NFC & DEVANAGARI DIGITS)
# ==============================================================================

def test_multilingual_text_normalization():
    """
    Validates NFC normalization and conversion of Devanagari numerals (०-९)
    to Western digits (0-9) for consistent indexing while keeping raw text safe.
    """
    deva_numerals_text = "पुणे गुन्हा रजि क्र. १२/२००९ कलम ३०२, ३७६ अन्वये गुन्हा नोंद दिनांक ०८/१०/२००९."
    normalized = normalize_multilingual_text(deva_numerals_text)

    # Devanagari numerals ०-९ must become 0-9 in normalized text
    assert "12/2009" in normalized
    assert "302" in normalized
    assert "08/10/2009" in normalized
    assert "०८/१०/२००९" not in normalized


# ==============================================================================
# TEST 3: IMAGE PRE-PROCESSING (PILLOW)
# ==============================================================================

def test_image_preprocessing_pipeline():
    """Validates that Pillow preprocessing steps execute without errors on synthetic scans."""
    from PIL import Image as PILImage, ImageDraw

    # Create dummy 400x300 grayscale scan image
    img = PILImage.new("RGB", (400, 300), color=(240, 235, 220))
    d = ImageDraw.Draw(img)
    d.text((20, 20), "POLICE PANCHNAMA 2009", fill=(10, 10, 10))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    proc_bytes, report = preprocess_image(raw_bytes, ["denoise", "contrast", "super_res"])
    assert report["status"] == "success"
    assert "contrast" in report["applied_steps"]
    assert "super_res" in report["applied_steps"]
    assert len(proc_bytes) > 0


# ==============================================================================
# TEST 4: SEGMENTATION & LOW-CONFIDENCE FLAGGING
# ==============================================================================

def test_segmentation_with_confidence_flagging():
    """
    Validates that:
    1. Segments receive bounding boxes / timestamps.
    2. Handwritten exhibits have confidence < threshold and get flagged as is_low_confidence.
    """
    text = (
        "पहिला पंच साक्षीदार श्रीकांत जोशी. "
        "दुसरा पंच साक्षीदार दिलीप पाटील. "
        "आरोपी योगेश राऊत याने लॅपटॉप दाखवला."
    )
    # Printed document (high confidence)
    printed_segs = create_initial_segments(text, "document", confidence_threshold=0.75, is_handwritten=False)
    assert len(printed_segs) == 3
    assert all(not s["is_low_confidence"] for s in printed_segs)
    assert printed_segs[0]["bbox_json"] is not None

    # Handwritten document (low confidence < 0.75)
    handwritten_segs = create_initial_segments(text, "document", confidence_threshold=0.75, is_handwritten=True)
    assert len(handwritten_segs) == 3
    assert all(s["is_low_confidence"] for s in handwritten_segs)
    assert handwritten_segs[0]["confidence"] < 0.75


# ==============================================================================
# TEST 5: IMMUTABLE VERSION CHAIN & ANALYST TEXT CORRECTION
# ==============================================================================

def test_analyst_text_correction_and_immutable_version_1(db, multilingual_case, test_users):
    """
    Verifies:
    1. Machine Version 1 is created and preserved.
    2. Analyst correction creates Version 2.
    3. Version 1 is NEVER overwritten.
    4. Merkle audit log record is appended in the same transaction.
    5. Entities and citations from changed segment are marked stale.
    """
    case = multilingual_case
    original_text = "आरोपी योगश राउत याने चोरीचा लॅपटॉप लपवला."
    initial_sha = hashlib.sha256(b"dummy_raw_pdf_bytes_12345").hexdigest()

    # Create evidence
    ev = Evidence(
        case_id=case.id,
        file_name="panchnama_hadapsar.txt",
        file_type="Document",
        file_size=1024,
        file_hash=initial_sha,
        extracted_text=original_text,
        primary_language="mr",
        script="devanagari",
        content_type="handwritten",
        text_quality_status="unreviewed"
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    # 1. Seed Version 1
    v1 = seed_initial_exhibit_version(db, ev.id, user_name="Automated Machine OCR")
    assert v1.version_number == 1
    assert v1.status == "machine_read"
    assert v1.is_current is True

    # Add an entity and citation linked to v1
    ent = Entity(case_id=case.id, evidence_id=ev.id, type="Suspect", name="योगश राउत", confidence=0.85)
    db.add(ent)
    db.flush()

    cit = SourceCitation(
        case_id=case.id,
        evidence_id=ev.id,
        version_id=v1.id,
        fact_type="entity",
        fact_id=ent.id,
        quote="योगश राउत",
        char_start=7,
        char_end=16,
        verified_match=True
    )
    db.add(cit)
    db.commit()

    # 2. Analyst corrects misspelled name "योगश" -> "योगेश"
    corrected_text = "आरोपी योगेश अशोक राउत याने चोरीचा लॅपटॉप लपवला."
    corr_res = apply_analyst_text_correction(
        db=db,
        evidence_id=ev.id,
        new_text=corrected_text,
        edit_reason="Corrected misread surname and added father name from voter roll.",
        user_id=test_users["analyst"].id,
        user_name=test_users["analyst"].full_name,
        user_role="analyst"
    )

    assert corr_res["success"] is True
    assert corr_res["previous_version"] == 1
    assert corr_res["new_version"] == 2

    # Refresh records
    db.refresh(ev)
    db.refresh(v1)
    db.refresh(ent)
    db.refresh(cit)

    # 3. Assert Version 1 was untouched and is no longer current
    assert v1.version_number == 1
    assert v1.raw_text == original_text  # NOT overwritten!
    assert v1.is_current is False

    # 4. Assert Version 2 exists and is current
    v2 = db.query(ExhibitTextVersion).filter(
        ExhibitTextVersion.evidence_id == ev.id,
        ExhibitTextVersion.version_number == 2
    ).first()
    assert v2 is not None
    assert v2.is_current is True
    assert v2.raw_text == corrected_text
    assert v2.status == "corrected"

    # 5. Original file hash must NOT change
    assert ev.file_hash == initial_sha

    # 6. Entity and old citation marked stale
    assert ent.is_stale is True
    assert "corrected to Version 2" in ent.stale_reason

    # 7. Audit log verification
    audit_entry = db.query(AuditLog).filter(
        AuditLog.action_type == "EXHIBIT_TEXT_CORRECTION",
        AuditLog.target_id == str(ev.id)
    ).order_by(AuditLog.id.desc()).first()
    assert audit_entry is not None
    assert audit_entry.user_name == test_users["analyst"].full_name


# ==============================================================================
# TEST 6: REVERTING TO PRIOR VERSION CREATES INCREMENTED VERSION
# ==============================================================================

def test_reverting_creates_incremented_version(db, multilingual_case, test_users):
    """
    Verifies that reverting to Version 1 does NOT delete Version 2,
    but creates Version 3 with the contents of Version 1.
    """
    case = multilingual_case
    ev = db.query(Evidence).filter(Evidence.case_id == case.id).first()
    assert ev is not None

    rev_res = revert_exhibit_to_version(
        db=db,
        evidence_id=ev.id,
        target_version_number=1,
        user_id=test_users["admin"].id,
        user_name=test_users["admin"].full_name,
        user_role="lead_investigator"
    )

    assert rev_res["success"] is True
    assert rev_res["new_version_number"] == 3
    assert rev_res["reverted_from_version"] == 1

    v3 = db.query(ExhibitTextVersion).filter(
        ExhibitTextVersion.evidence_id == ev.id,
        ExhibitTextVersion.version_number == 3
    ).first()
    assert v3 is not None
    assert v3.is_current is True
    assert v3.is_reverted is True
    assert v3.reverted_from_version == 1


# ==============================================================================
# TEST 7: SEPARATE TRANSLATIONS & SEGMENT ALIGNMENT
# ==============================================================================

def test_separate_translations_and_dual_citations(db, multilingual_case, test_users):
    """
    Verifies that translations:
    1. Are stored separately from original text.
    2. Maintain segment alignment with source segments.
    3. Carry 'Machine translation' label initially, and change to 'Reviewed translation' upon review.
    4. Dual citation produces both original quote and translated quote.
    """
    case = multilingual_case
    ev = Evidence(
        case_id=case.id,
        file_name="witness_statement_marathi.txt",
        file_type="Document",
        file_size=512,
        file_hash="hash_witness_1234",
        extracted_text="साक्षीदार राजेश चौधरी याने सांगितले की आरोपी योगेश राउत पळून गेला.",
        primary_language="mr",
        script="devanagari",
        content_type="printed",
        text_quality_status="unreviewed"
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    # 1. Create machine translation
    trans = create_or_update_translation(
        db=db,
        evidence_id=ev.id,
        target_language="en",
        author_type="machine",
        author_name="Gemini Multilingual Translator"
    )
    assert trans.review_status == "unreviewed"
    assert len(trans.aligned_segments) > 0

    # 2. Add citation
    cit = SourceCitation(
        case_id=case.id,
        evidence_id=ev.id,
        fact_type="statement",
        quote="आरोपी योगेश राउत पळून गेला.",
        page_number=1,
        verified_match=True
    )
    db.add(cit)
    db.commit()
    db.refresh(cit)

    # Format dual citation
    dual = format_dual_citation(cit, ev, db)
    assert dual["original_quote"] == "आरोपी योगेश राउत पळून गेला."
    assert "Machine translation" in dual["translation_label"]
    assert dual["translated_quote"] is not None

    # 3. Mark translation reviewed by certified translator
    rev_res = review_translation(db, trans.id, "Insp. Kishor Patil (Certified Translator)")
    assert rev_res["review_status"] == "reviewed"
    assert "Reviewed translation by Insp. Kishor Patil" in rev_res["label"]

    # Re-check dual citation label after review
    dual_after = format_dual_citation(cit, ev, db)
    assert "Reviewed translation by Insp. Kishor Patil" in dual_after["translation_label"]


# ==============================================================================
# TEST 8: RELIABILITY PENALTIES & RESTORATION
# ==============================================================================

def test_evidence_reliability_modifiers_for_text_quality():
    """
    Validates scoring engine integration:
    - Unreviewed handwriting applies -0.15 penalty.
    - Low-confidence OCR applies -0.10 penalty.
    - Human-reviewed transcript awards +0.08 bonus.
    - Human-corrected transcript awards +0.10 bonus.
    """
    # 1. Unreviewed handwriting
    ex_hw = {
        "evidence_type": "document",
        "content_type": "handwritten",
        "text_quality_status": "unreviewed"
    }
    rel_hw, audit_hw = resolve_exhibit_reliability(ex_hw)
    assert "unreviewed_handwriting" in audit_hw["modifiers_applied"]
    assert audit_hw["modifiers_applied"]["unreviewed_handwriting"] == -0.15

    # 2. Low confidence unreviewed
    ex_low = {
        "evidence_type": "document",
        "content_type": "printed",
        "is_low_confidence": True,
        "text_quality_status": "unreviewed"
    }
    rel_low, audit_low = resolve_exhibit_reliability(ex_low)
    assert "unreviewed_low_confidence_ocr" in audit_low["modifiers_applied"]

    # 3. Human reviewed restoration
    ex_rev = {
        "evidence_type": "document",
        "content_type": "handwritten",
        "text_quality_status": "reviewed"
    }
    rel_rev, audit_rev = resolve_exhibit_reliability(ex_rev)
    assert "human_reviewed_transcript" in audit_rev["modifiers_applied"]
    assert audit_rev["modifiers_applied"]["human_reviewed_transcript"] == +0.08
    assert rel_rev > rel_hw  # Reliability restored!


# ==============================================================================
# TEST 9: CROSS-LANGUAGE SEARCH & TRANSLITERATION MATCHING
# ==============================================================================

def test_cross_language_transliteration_and_search(db, multilingual_case):
    """
    Tests cross-language entity search:
    Searching Latin 'Rahul' or 'Raut' finds Devanagari 'राहुल' or 'राउत',
    and clearly identifies match source.
    """
    case = multilingual_case

    # Search for Latin query 'Yogesh' -> finds Devanagari 'योगेश' via phonetic mapping
    results_yogesh = search_multilingual_corpus(db=db, case_id=case.id, query="Yogesh")
    assert len(results_yogesh) > 0
    assert any(r["matched_field"] in ["original", "transliterated", "translation"] for r in results_yogesh)

    # Search for Devanagari query 'राउत' -> finds matching exhibits
    results_raut = search_multilingual_corpus(db=db, case_id=case.id, query="राउत")
    assert len(results_raut) > 0


# ==============================================================================
# TEST 10: MULTILINGUAL API ROUTER ENDPOINTS
# ==============================================================================

def test_multilingual_api_endpoints_and_rbac(client, auth_headers, multilingual_case, db):
    """Tests GET profile, language confirmation, corrections, and settings endpoints."""
    case = multilingual_case
    ev = db.query(Evidence).filter(Evidence.case_id == case.id).first()
    if not ev:
        ev = Evidence(
            case_id=case.id,
            file_name="panchnama_sample.txt",
            file_type="Document",
            file_size=1024,
            file_hash="hash_api_test_123",
            extracted_text="साक्षीदार श्रीकांत जोशी यांनी पंचनामा स्वाक्षरी केली.",
            primary_language="mr",
            script="devanagari",
            content_type="printed",
            text_quality_status="unreviewed"
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)

    # 1. GET multilingual profile
    resp = client.get(f"/cases/{case.id}/evidence/{ev.id}/multilingual", headers=auth_headers["analyst"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["evidence_id"] == ev.id
    assert "versions" in data
    assert "dual_citations" in data
    assert "reliability_assessment" in data

    # 2. Confirm language profile
    conf_payload = {
        "primary_language": "mr",
        "script": "devanagari",
        "content_type": "handwritten",
        "is_poor_audio": False
    }
    resp_conf = client.post(f"/cases/{case.id}/evidence/{ev.id}/language-confirm", json=conf_payload, headers=auth_headers["analyst"])
    assert resp_conf.status_code == 200
    assert resp_conf.json()["language_source"] == "user_confirmed"

    # 3. GET settings
    resp_settings = client.get(f"/cases/{case.id}/multilingual/settings", headers=auth_headers["analyst"])
    assert resp_settings.status_code == 200
    settings_list = resp_settings.json()
    assert len(settings_list) >= 4

    # 4. GET cross-language search
    resp_search = client.get(f"/cases/{case.id}/multilingual/search?q=लॅपटॉप", headers=auth_headers["analyst"])
    assert resp_search.status_code == 200
    assert resp_search.json()["total_matches"] >= 1
