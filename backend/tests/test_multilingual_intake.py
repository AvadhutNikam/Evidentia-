# backend/tests/test_multilingual_intake.py
"""
Unit tests for Evidentia-AI Multilingual Indic Processing & Low-Typing Intake Pipeline
Tests:
1. Unicode normalization and Devanagari numeral translation.
2. SoundexIndic cross-script phonetic fingerprinting.
3. Multi-signal anti-false-merge protection on common names.
4. FIR copy parsing and date ambiguity detection.
5. WhatsApp export parsing and Section 63 BSA certificate prompt.
6. Reading card confirmation preventing unconfirmed data leakage.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import (
    User, Case, CasePerson, PersonAlias, IntakeItem,
    IntakeFeedback, InvestigationTask, CustodyLog
)
from indic_engine import (
    normalize_indic_text, soundex_indic, strip_indic_honorifics_and_affixes,
    compute_name_similarity, match_person_multi_signal, transliterate_indic
)
from intake_engine import (
    compute_sha256, extract_fir_fields, extract_handwritten_statement_fields,
    extract_voice_note_fields, parse_whatsapp_chat_export,
    process_intake_submission, confirm_intake_item, get_intake_trust_metrics
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    user = User(
        id=1,
        email="inspector.patil@police.gov.in",
        full_name="Inspector S. Patil",
        role="lead_investigator",
        hashed_password="test_hashed_password"
    )
    session.add(user)

    case = Case(
        id=1,
        title="State of Maharashtra vs. Yogesh Raut & Ors",
        fir_number="FIR-2009-MH-PUN-534",
        crime_number="CR-534/2009",
        status="Active"
    )
    session.add(case)
    session.commit()

    yield session
    session.close()


def test_unicode_normalization_and_numerals():
    """Verifies that NFC form, Nukta variants, and Devanagari numerals normalize correctly."""
    raw = "गुन्हा क्र. १२३/२००९, आरोपीचे नाव: क़दम, रक्कम रु. ५०,०००/-"
    normalized = normalize_indic_text(raw)

    # Numerals must be translated to standard Western digits
    assert "123/2009" in normalized
    assert "50,000" in normalized
    # Nukta char 'क़' normalized to base 'क'
    assert "कदम" in normalized


def test_soundex_indic_phonetic_matching():
    """Verifies SoundexIndic accurately maps Devanagari and Latin name variants to identical keys."""
    # Rahul / राहुल / Rahool
    k_latin = soundex_indic("Rahul")
    k_deva = soundex_indic("राहुल")
    k_variant = soundex_indic("Rahool")
    assert k_latin == k_deva == k_variant

    # Raut / राउत / राऊत
    assert soundex_indic("Raut") == soundex_indic("राउत") == soundex_indic("राऊत")

    # Distinct names must not collide
    assert soundex_indic("Patil") != soundex_indic("Shinde")
    assert soundex_indic("Kadam") != soundex_indic("Thakur")

    # Honorifics stripping
    assert soundex_indic("श्री योगेश अशोक राउत") == soundex_indic("Yogesh Ashok Raut")
    assert soundex_indic("Shri Mahesh Thakur s/o Ram Thakur") == soundex_indic("Mahesh Thakur")


def test_anti_false_merge_safeguards(db_session):
    """
    Verifies that common names without corroborating signals are capped at 65%
    and cannot be falsely auto-merged.
    """
    p1 = CasePerson(
        id=1,
        case_id=1,
        name="Rahul Patil",
        role="witness",
        father_or_spouse_name="Suresh Patil",
        age=32,
        contact_info="+91-98200-11223",
        address="Kothrud, Pune"
    )
    db_session.add(p1)
    db_session.commit()

    # Case A: Same name but NO secondary signals provided -> must be capped at 0.65
    cands_no_signals = match_person_multi_signal(
        candidate_name="राहुल पाटील",
        candidate_signals={},
        db=db_session,
        case_id=1
    )
    assert len(cands_no_signals) > 0
    assert cands_no_signals[0]["similarity_score"] <= 0.65
    assert cands_no_signals[0]["confidence_tier"] == "check"

    # Case B: Name with MATCHING father's name and phone -> confidence boosted to high (>= 0.85)
    cands_corroborated = match_person_multi_signal(
        candidate_name="Rahul Patil",
        candidate_signals={
            "father_name": "Suresh Patil",
            "phone": "9820011223"
        },
        db=db_session,
        case_id=1
    )
    assert len(cands_corroborated) > 0
    assert cands_corroborated[0]["similarity_score"] >= 0.85
    assert cands_corroborated[0]["confidence_tier"] == "high"

    # Case C: Name with CONTRADICTING father's name -> confidence heavily penalized
    cands_contradicted = match_person_multi_signal(
        candidate_name="Rahul Patil",
        candidate_signals={
            "father_name": "Dinkar Patil",
            "age": 65
        },
        db=db_session,
        case_id=1
    )
    assert len(cands_contradicted) > 0
    assert cands_contradicted[0]["similarity_score"] < 0.50


def test_fir_header_extraction_and_proposals():
    """Verifies that FIR parser extracts structured fields and detects date ambiguity."""
    sample_fir = """
    प्रथम खबरी अहवाल (First Information Report)
    पोलीस ठाणे: येरवडा पोलीस स्टेशन, पुणे शहर
    गु. र. क्र.: CR-534/2009
    घटनेचा दिनांक: 07/10/2009 वेळ: 21:30
    तक्रार नोंद दिनांक: 08/10/2009 वेळ: 04:15
    कायदेशीर कलमे: कलम 302, 376(2)(g), 397 IPC
    तक्रारदार: अभिजीत पुजारी (वय 28 वर्षे)
    आरोपींची नावे: योगेश अशोक राउत, महेश ठाकूर, विश्वास कदम
    थोडक्यात हकीकत: फिर्यादी यांची बहीण नयना पुजारी हिला कामावरून घरी परतताना आरोपींनी जबरदस्तीने गाडीत बसवून नेले.
    """
    proposals = extract_fir_fields(sample_fir)
    assert len(proposals) >= 5

    keys = {p["field_key"]: p["value"] for p in proposals}
    assert "CR-534/2009" in keys["crime_number"]
    assert "येरवडा" in keys["police_station"]
    assert "302" in keys["offence_section"]
    assert "अभिजीत पुजारी" in keys["complainant_name"]
    assert "योगेश अशोक राउत" in keys["accused_names"]

    # Test ambiguous date handling
    ambig_fir = "घटनेचा दिनांक: 03/04/2026 वेळ 14:00"
    ambig_proposals = extract_fir_fields(ambig_fir)
    incident_field = next(p for p in ambig_proposals if p["field_key"] == "incident_date")
    assert incident_field["is_ambiguous"] is True
    assert len(incident_field["alternative_readings"]) > 0


def test_whatsapp_chat_parser():
    """Verifies multi-format parsing, sender detection, and Section 63 BSA certificate prompt."""
    chat_sample = """
    07/10/09, 21:15 - Yogesh Raut: Reach Swargate ATM fast
    07/10/09, 21:16 - Mahesh Thakur: I am outside in the Qualis
    07/10/09, 21:42 - Yogesh Raut: Withdrew Rs 61000 from SBI card
    07/10/09, 21:43 - <Media omitted>
    07/10/09, 21:44 - Yogesh Raut: Let's move towards Rajgurunagar
    """
    messages, proposals = parse_whatsapp_chat_export(chat_sample)
    assert len(messages) == 5
    assert messages[0]["sender"] == "Yogesh Raut"
    assert messages[3]["has_media"] is True

    # Proposals must include participants, amounts, and Section 63 BSA certificate reminder
    field_keys = [p["field_key"] for p in proposals]
    assert any("chat_participant" in k for k in field_keys)
    assert "stolen_cash_amount" in field_keys
    assert "sec_63_bsa_certificate_required" in field_keys


def test_intake_confirmation_prevents_unconfirmed_leakage(db_session):
    """
    Verifies that unconfirmed fields do not enter database tables until confirmed by an officer.
    Verifies trust metrics recording.
    """
    fir_text = """
    गु. र. क्र.: CR-999/2026
    पोलीस ठाणे: स्वारगेट पोलीस स्टेशन
    तक्रारदार: सुनील शिंदे
    आरोपी: विशाल पवार
    """
    item = process_intake_submission(
        db=db_session,
        case_id=1,
        channel="fir_copy",
        title="FIR 999 Scanned Copy",
        raw_text=fir_text,
        submitter_name="Inspector S. Patil"
    )
    assert item.status == "ready_for_review"
    assert item.file_hash is not None

    # Before confirmation, person 'विशाल पवार' must NOT exist in CasePerson table
    p_before = db_session.query(CasePerson).filter(CasePerson.name == "विशाल पवार").first()
    assert p_before is None

    # Officer confirms accused and complainant, but rejects police station
    confirmations = [
        {
            "field_key": "complainant_name",
            "field_group": "people",
            "action": "confirm",
            "confirmed_value": "सुनील शिंदे",
            "ai_value": "सुनील शिंदे"
        },
        {
            "field_key": "accused_names",
            "field_group": "people",
            "action": "edit",
            "confirmed_value": "विशाल रमेश पवार",
            "ai_value": "विशाल पवार",
            "correction_notes": "Added middle name"
        },
        {
            "field_key": "police_station",
            "field_group": "places",
            "action": "reject",
            "correction_notes": "Station is out of jurisdiction"
        }
    ]

    updated_item = confirm_intake_item(
        db=db_session,
        intake_id=item.id,
        user_id=1,
        user_name="Inspector S. Patil",
        confirmations=confirmations
    )
    assert updated_item.status == "confirmed"
    assert updated_item.applied_entities_count == 2

    # Now the confirmed person must exist in CasePerson table and PersonAlias table
    accused_person = db_session.query(CasePerson).filter(CasePerson.name == "विशाल रमेश पवार").first()
    assert accused_person is not None
    assert accused_person.role == "accused"

    alias_entry = db_session.query(PersonAlias).filter(PersonAlias.person_id == accused_person.id).first()
    assert alias_entry is not None
    assert alias_entry.phonetic_key == soundex_indic("विशाल रमेश पवार")

    # Metrics check
    metrics = get_intake_trust_metrics(db=db_session, case_id=1)
    assert metrics["total_fields_extracted"] == 3
    assert metrics["total_confirmed_unchanged"] == 1
    assert metrics["total_edited_by_officer"] == 1
    assert metrics["total_rejected_fields"] == 1
    assert metrics["acceptance_rate_pct"] == 33.3  # 1 out of 3 unchanged
