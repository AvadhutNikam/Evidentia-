"""
backend/tests/test_omni_search.py
Comprehensive test suite for:
1. Cross-corpus Omni-Search across exhibits, entities, claims, quotes, suspects, tasks, and alerts.
2. Multilingual matching across original text, normalized text, and judicial translations.
3. Source attribution, context snippet extraction, and character offset deep-linking.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import app
from models import (
    User, Case, CaseMember, Evidence, Entity, Hypothesis,
    EvidenceAssessment, SourceCitation, ExhibitChunk,
    SuspectProfileFactor, PriorRecord, InvestigationTask,
    Alert, ExhibitTextVersion, ExhibitTranslation
)
from auth import hash_password, create_access_token
from omni_search_engine import search_case_omni, extract_highlighted_snippet


@pytest.fixture
def omni_search_setup(db: Session):
    """Sets up an investigator, a test case, and rich cross-corpus artifacts."""
    user = db.query(User).filter(User.email == "omni_detective@evidentia.test").first()
    if not user:
        user = User(
            email="omni_detective@evidentia.test",
            full_name="Inspector Vikram Gokhale",
            hashed_password=hash_password("Pass123!"),
            role="lead_investigator",
            is_active=True,
            badge_number="DET-OMNI-77"
        )
        db.add(user)
        db.flush()

    test_case = db.query(Case).filter(Case.title == "Operation Cross-Corpus Forensic Search").first()
    if not test_case:
        test_case = Case(
            title="Operation Cross-Corpus Forensic Search",
            description="Testing unified omni-search across all 7 evidentiary dimensions",
            status="Active",
            created_by="Inspector Vikram Gokhale"
        )
        db.add(test_case)
        db.flush()

    membership = (
        db.query(CaseMember)
        .filter(CaseMember.case_id == test_case.id, CaseMember.user_id == user.id)
        .first()
    )
    if not membership:
        membership = CaseMember(
            case_id=test_case.id,
            user_id=user.id,
            case_role="lead_investigator"
        )
        db.add(membership)
        db.flush()

    # 1. Exhibit 1 (English original)
    ev1 = Evidence(
        case_id=test_case.id,
        file_name="Gate_Camera_Security_Feed.mp4",
        file_type="video/mp4",
        evidence_type="cctv",
        extracted_text="At 21:15:20, a distinct silver-maroon utility cab MH-12-Q-4455 was spotted idling near the eastern perimeter gate.",
        primary_language="en",
        uploaded_by="Inspector Vikram Gokhale"
    )
    db.add(ev1)
    db.flush()

    # Exhibit Chunk & Source Citation for Exhibit 1
    chk1 = ExhibitChunk(
        evidence_id=ev1.id,
        case_id=test_case.id,
        chunk_index=0,
        text="At 21:15:20, a distinct silver-maroon utility cab MH-12-Q-4455 was spotted idling near the eastern perimeter gate.",
        char_start=0,
        char_end=115,
        page_number=1
    )
    db.add(chk1)
    db.flush()

    cit1 = SourceCitation(
        case_id=test_case.id,
        evidence_id=ev1.id,
        chunk_id=chk1.id,
        fact_type="event",
        quote="silver-maroon utility cab MH-12-Q-4455 was spotted idling near the eastern perimeter gate",
        char_start=23,
        char_end=110,
        page_number=1
    )
    db.add(cit1)

    # 2. Exhibit 2 (Regional Marathi dialect with English Translation)
    ev2 = Evidence(
        case_id=test_case.id,
        file_name="Panchnama_Witness_Deposit.pdf",
        file_type="application/pdf",
        evidence_type="witness",
        extracted_text="रात्रीच्या पहारेकऱ्याने संशयित इसमाला पळताना पाहिले.",  # "The night watchman saw suspect running"
        primary_language="mr",
        uploaded_by="Sub-Inspector More"
    )
    db.add(ev2)
    db.flush()

    ev_ver = ExhibitTextVersion(
        evidence_id=ev2.id,
        case_id=test_case.id,
        version_number=1,
        raw_text=ev2.extracted_text,
        normalized_text=ev2.extracted_text,
        reading_method="ocr",
        overall_confidence=0.95,
        created_by="system"
    )
    db.add(ev_ver)
    db.flush()

    trans2 = ExhibitTranslation(
        evidence_id=ev2.id,
        version_id=ev_ver.id,
        source_language="mr",
        target_language="en",
        author_type="certified_human",
        author_name="Court Interpreter Kulkarni",
        review_status="reviewed",
        full_translated_text="The night watchman spotted the masked culprit fleeing toward the railway siding."
    )
    db.add(trans2)

    # 3. Entity
    ent1 = Entity(
        case_id=test_case.id,
        evidence_id=ev1.id,
        name="MH-12-Q-4455",
        type="vehicle",
        confidence=98.5,
        source_quote="silver-maroon utility cab MH-12-Q-4455",
        source_char_start=23,
        source_char_end=62
    )
    db.add(ent1)

    # 4. Hypothesis & Claim Assessment
    hyp1 = Hypothesis(
        case_id=test_case.id,
        title="Premeditated Abduction via Commercial Cab Decoy",
        description="Suspect utilized a stolen commercial utility vehicle to circumvent security checkpoints.",
        status="Active"
    )
    db.add(hyp1)
    db.flush()

    ass1 = EvidenceAssessment(
        hypothesis_id=hyp1.id,
        evidence_id=ev1.id,
        classification="strong_support",
        reason="CCTV telemetry corroborates cab presence precisely at the abduction timestamp.",
        quoted_source_line="silver-maroon utility cab MH-12-Q-4455 was spotted idling",
        llm_confidence=0.91
    )
    db.add(ass1)

    # 5. Suspect Profile Factor & Prior Record
    fac1 = SuspectProfileFactor(
        case_id=test_case.id,
        hypothesis_id=hyp1.id,
        suspect_name="Baban Shinde",
        factor_type="means",
        factor_value="Possession of unregistered master key",
        note="Unregistered master key recovered from suspect's residence during lawful search.",
        source_evidence_id=ev1.id
    )
    pr1 = PriorRecord(
        case_id=test_case.id,
        suspect_name="Baban Shinde",
        offense_type="Armed Robbery and Vehicle Theft",
        legal_section="Section 392/397 IPC",
        location="Pune Rural Highway",
        outcome="convicted",
        source_agency="State Crime Records Bureau"
    )
    db.add_all([fac1, pr1])

    # 6. Investigation Task
    task1 = InvestigationTask(
        case_id=test_case.id,
        task="Subpoena FASTag toll plaza logs for MH-12-Q-4455 on Urse Toll Plaza",
        reason="Confirm vehicle egress trajectory along the expressway.",
        priority="High",
        status="Pending",
        assigned_to="Detective Patil"
    )
    db.add(task1)

    # 7. Alert
    alert1 = Alert(
        case_id=test_case.id,
        rule_type="rank_gap_narrow",
        severity="critical",
        title="FASTag Cross-Reference Alert",
        message="Urgent FASTag checkpoint transit match detected for vehicle MH-12-Q-4455.",
        dedup_key="alert-fastag-test-01"
    )
    db.add(alert1)
    db.commit()

    token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )
    headers = {"Authorization": f"Bearer {token}"}

    return {
        "user": user,
        "case": test_case,
        "token": token,
        "headers": headers,
        "evidence_cctv": ev1,
        "evidence_marathi": ev2
    }


def test_extract_highlighted_snippet():
    text = "The quick brown fox jumps over the lazy dog near the riverbank on a sunny morning."
    snippet, start, end = extract_highlighted_snippet(text, "lazy dog", context_chars=15)
    assert "lazy dog" in snippet
    assert start > 0
    assert end > start


def test_omni_search_original_text(omni_search_setup, client: TestClient, db: Session):
    """Verifies matching verbatim original text inside exhibits with snippet and char offsets."""
    case = omni_search_setup["case"]
    headers = omni_search_setup["headers"]

    resp = client.get(f"/cases/{case.id}/omni-search?q=silver-maroon", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["total_matches"] >= 1
    matches = data["matches"]
    
    # Check that exhibit match is found
    ex_match = next((m for m in matches if m["category"] == "exhibit"), None)
    assert ex_match is not None
    assert ex_match["match_source"] == "Exhibit Original Text"
    assert "silver-maroon" in ex_match["matched_snippet"]
    assert "highlight=silver-maroon" in ex_match["target_url"]


def test_omni_search_translation(omni_search_setup, client: TestClient, db: Session):
    """Verifies cross-language matching inside judicial English translations for regional exhibits."""
    case = omni_search_setup["case"]
    headers = omni_search_setup["headers"]

    # "railway siding" only appears in the Marathi exhibit's English translation!
    resp = client.get(f"/cases/{case.id}/omni-search?q=railway siding", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["total_matches"] >= 1
    trans_match = next((m for m in data["matches"] if "Translation" in m["match_source"]), None)
    assert trans_match is not None
    assert "railway siding" in trans_match["matched_snippet"]
    assert trans_match["category"] == "exhibit"


def test_omni_search_across_all_7_dimensions(omni_search_setup, client: TestClient, db: Session):
    """
    Verifies searching across:
    1. Quotes
    2. Entities
    3. Claims & Hypotheses
    4. Suspects & Criminal Records
    5. Tasks
    6. Alerts
    """
    case = omni_search_setup["case"]
    headers = omni_search_setup["headers"]

    # 1. Search vehicle registration plate -> should find Entity, Exhibit, Task, and Alert!
    resp = client.get(f"/cases/{case.id}/omni-search?q=MH-12-Q-4455", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    categories = {m["category"] for m in data["matches"]}
    assert "entity" in categories
    assert "exhibit" in categories or "quote" in categories
    assert "task" in categories
    assert "alert" in categories

    # 2. Search suspect name -> should find Suspect Factor and Prior Record!
    resp_suspect = client.get(f"/cases/{case.id}/omni-search?q=Baban Shinde", headers=headers)
    assert resp_suspect.status_code == 200, resp_suspect.text
    suspect_data = resp_suspect.json()
    suspect_categories = [m["category"] for m in suspect_data["matches"]]
    assert "suspect" in suspect_categories

    # 3. Search claim / hypothesis
    resp_claim = client.get(f"/cases/{case.id}/omni-search?q=Commercial Cab Decoy", headers=headers)
    assert resp_claim.status_code == 200, resp_claim.text
    claim_data = resp_claim.json()
    assert any(m["category"] == "claim" for m in claim_data["matches"])


def test_global_cross_case_omni_search(omni_search_setup, client: TestClient, db: Session):
    """Verifies global search across all accessible cases."""
    headers = omni_search_setup["headers"]

    resp = client.get("/search/omni?q=master key", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["total_matches"] >= 1
    assert any("master key" in m["matched_snippet"].lower() for m in data["matches"])
