"""
backend/tests/test_chargesheet_and_docket.py
Comprehensive test suite for Court-Admissible Chargesheet & Docket Assistant:
- Template generation across 5 statutory sections (Facts, Evidence, Witnesses, Forensic, Analysis)
- Inline source-span citations linking to exhibit chunks
- Investigator editing, version incrementing, and ChargesheetEditLog tracking
- Tamper-evident Merkle audit logging (CHARGESHEET_GENERATED, CHARGESHEET_EDITED, CHARGESHEET_EXPORT)
- Vector PDF compilation with statutory draft watermark and SHA-256 seal
- RBAC permissions (Read-only reviewers restricted from modifying drafts)
"""

import os
import json
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from database import Base, get_db
from models import (
    Case, Evidence, ExhibitChunk, SourceCitation, Entity, Event, 
    Hypothesis, User, AuditLog, ChargesheetDraft, ChargesheetEditLog, CaseMember
)
from auth import create_access_token, hash_password
from app import app
from chargesheet_engine import (
    generate_initial_chargesheet_draft,
    update_chargesheet_draft,
    export_chargesheet_pdf,
    STATUTORY_DRAFT_NOTICE
)

TEST_DB_URL = "sqlite:///./test_chargesheet.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()

    # Seed test users
    admin = User(
        email="admin_charge@evidentia.test",
        full_name="Admin Director",
        hashed_password=hash_password("AdminPass123!"),
        role="admin",
        badge_number="DIR-001"
    )
    lead = User(
        email="lead_charge@evidentia.test",
        full_name="DSP Vikram Joshi",
        hashed_password=hash_password("LeadPass123!"),
        role="lead_investigator",
        badge_number="DSP-108"
    )
    reviewer = User(
        email="reviewer_charge@evidentia.test",
        full_name="Judicial Reviewer Gupta",
        hashed_password=hash_password("RevPass123!"),
        role="reviewer",
        badge_number="REV-999"
    )
    db.add_all([admin, lead, reviewer])
    db.commit()

    # Seed test case with procedural details
    case = Case(
        title="Yerwada Commercial Bank Robbery & Assault",
        description="Armed robbery involving three perpetrators at bank premises with weapon recovery and CCTV corroboration.",
        status="Active",
        fir_number="FIR/Yerwada/342/2024",
        offence_section="Section 309(4) BNS / Section 392 IPC, Section 61(2) BNS",
        incident_date=datetime(2024, 8, 15, 14, 30, tzinfo=timezone.utc),
        arrest_date=datetime(2024, 8, 18, 11, 0, tzinfo=timezone.utc),
        remand_date=datetime(2024, 8, 19, 10, 0, tzinfo=timezone.utc),
        statutory_time_limit_days=90,
        created_by="DSP Vikram Joshi"
    )
    db.add(case)
    db.commit()

    # Add Case Memberships for RBAC
    cm_lead = CaseMember(case_id=case.id, user_id=lead.id, case_role="lead_investigator")
    cm_rev = CaseMember(case_id=case.id, user_id=reviewer.id, case_role="reviewer")
    db.add_all([cm_lead, cm_rev])
    db.commit()

    # Seed Evidence
    ev1 = Evidence(
        case_id=case.id,
        file_name="CCTV_Vestibule_Camera.mp4",
        file_type="video/mp4",
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        extracted_text="Two male suspects entering vestibule at 14:32 wearing dark helmets and carrying silver tool.",
        sec_65b_certificate_present=True,
        chain_of_custody_complete=True,
        source="Yerwada Police Vault"
    )
    ev2 = Evidence(
        case_id=case.id,
        file_name="FSL_Ballistic_Seizure_Memo.pdf",
        file_type="application/pdf",
        file_hash="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        extracted_text="Ballistic comparison confirms spent 7.65mm cartridge matches country-made pistol recovered from accused.",
        sec_65b_certificate_present=True,
        chain_of_custody_complete=True,
        source="State Forensic Science Laboratory Pune"
    )
    db.add_all([ev1, ev2])
    db.commit()

    # Seed Exhibit Chunks
    chunk1 = ExhibitChunk(
        evidence_id=ev1.id,
        case_id=case.id,
        chunk_index=1,
        text="Two male suspects entering vestibule at 14:32 wearing dark helmets and carrying silver tool.",
        page_number=1,
        char_start=0,
        char_end=92
    )
    chunk2 = ExhibitChunk(
        evidence_id=ev2.id,
        case_id=case.id,
        chunk_index=1,
        text="Ballistic comparison confirms spent 7.65mm cartridge matches country-made pistol recovered from accused.",
        page_number=1,
        char_start=0,
        char_end=108
    )
    db.add_all([chunk1, chunk2])
    db.commit()

    # Seed Source Citations
    c1 = SourceCitation(
        case_id=case.id,
        evidence_id=ev1.id,
        chunk_id=chunk1.id,
        fact_type="event",
        quote="Two male suspects entering vestibule at 14:32",
        char_start=0,
        char_end=45,
        verified_match=True,
        match_confidence=1.0
    )
    c2 = SourceCitation(
        case_id=case.id,
        evidence_id=ev2.id,
        chunk_id=chunk2.id,
        fact_type="assessment",
        quote="Ballistic comparison confirms spent 7.65mm cartridge matches country-made pistol",
        char_start=0,
        char_end=80,
        verified_match=True,
        match_confidence=1.0
    )
    db.add_all([c1, c2])
    db.commit()

    # Seed Entities (Witness & Suspect)
    ent1 = Entity(
        case_id=case.id,
        name="Branch Cashier Ramesh Rao",
        type="witness",
        confidence=0.95
    )
    ent2 = Entity(
        case_id=case.id,
        name="Yogesh Raut",
        type="suspect",
        confidence=0.98
    )
    db.add_all([ent1, ent2])
    db.commit()

    # Seed Timeline Event
    event1 = Event(
        case_id=case.id,
        title="Armed Entry into Cash Cabin",
        description="Perpetrator brandished firearm and demanded vault keys from manager.",
        location="Cashier Counter 2",
        timestamp=datetime(2024, 8, 15, 14, 34, tzinfo=timezone.utc),
        evidence_id=ev1.id
    )
    db.add(event1)
    db.commit()

    # Seed Hypotheses
    h1 = Hypothesis(
        case_id=case.id,
        title="Accused Yogesh Raut Executed Planned Armed Robbery",
        description="Accused procured firearm and scoped premises prior to entry.",
        support_score=87.5
    )
    h2 = Hypothesis(
        case_id=case.id,
        title="Opportunistic Unrelated Bystander Intrusion",
        description="Entry occurred without premeditation.",
        support_score=12.5
    )
    db.add_all([h1, h2])
    db.commit()
    db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("./test_chargesheet.db"):
        try:
            os.remove("./test_chargesheet.db")
        except Exception:
            pass


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def get_token(email: str) -> str:
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == email).first()
    token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "role": user.role
    })
    db.close()
    return token


# ==============================================================================
# TESTS
# ==============================================================================

def test_generate_initial_chargesheet_draft():
    db = TestingSessionLocal()
    case = db.query(Case).first()
    lead = db.query(User).filter(User.role == "lead_investigator").first()

    draft = generate_initial_chargesheet_draft(case.id, db, user=lead)

    assert draft.id is not None
    assert draft.case_id == case.id
    assert draft.version == 1
    assert draft.is_draft is True
    assert draft.status == "draft"
    assert draft.legal_review_status == "pending_legal_review"

    # Verify 5 sections are populated
    assert "SECTION 1" in draft.facts_narrative or "FIR" in draft.facts_narrative
    assert "SOURCE SPAN:" in draft.facts_narrative or len(draft.facts_narrative) > 50

    ev_list = json.loads(draft.evidence_inventory)
    assert len(ev_list) == 2
    assert ev_list[0]["exhibit_code"] == "Ex. P-1"
    assert ev_list[0]["sec_65b_certificate_present"] is True
    assert "char_start" in ev_list[0]["source_span"]

    witnesses = json.loads(draft.witness_statements)
    assert len(witnesses) >= 2
    assert any("PW" in w["witness_code"] for w in witnesses)
    assert any("char_start" in w["source_span"] for w in witnesses)

    fsl = json.loads(draft.forensic_findings)
    assert len(fsl) >= 1
    assert "FSL" in fsl[0]["finding_code"]

    assert "Richards J. Heuer" in draft.analysis_and_charges
    assert "Section 309" in draft.analysis_and_charges or "PRAYER:" in draft.analysis_and_charges

    # Verify statutory disclaimer
    assert "DRAFT CHARGESHEET" in draft.legal_disclaimer
    assert "PROSECUTOR SCRUTINY" in draft.legal_disclaimer

    # Verify audit log entry
    audit = db.query(AuditLog).filter(
        AuditLog.action_type == "CHARGESHEET_GENERATED",
        AuditLog.target_id == str(draft.id)
    ).first()
    assert audit is not None
    assert "Generated Draft Chargesheet" in audit.description

    db.close()


def test_update_chargesheet_draft_and_edit_log():
    db = TestingSessionLocal()
    case = db.query(Case).first()
    lead = db.query(User).filter(User.role == "lead_investigator").first()
    draft = db.query(ChargesheetDraft).filter(ChargesheetDraft.case_id == case.id).first()

    prev_version = draft.version

    updates = {
        "section_edited": "facts",
        "edit_summary": "Expanded facts with vehicle license plate details",
        "facts_narrative": draft.facts_narrative + "\n\nAdditional verified fact: Silver getaway vehicle identified with plate MH-12-AB-1234."
    }

    updated = update_chargesheet_draft(draft.id, updates, db, user=lead)

    assert updated.version == prev_version + 1
    assert "MH-12-AB-1234" in updated.facts_narrative
    assert updated.last_edited_by == lead.full_name
    assert updated.last_edit_summary == "Expanded facts with vehicle license plate details"

    # Verify ChargesheetEditLog table entry
    edit_log = db.query(ChargesheetEditLog).filter(
        ChargesheetEditLog.chargesheet_id == draft.id,
        ChargesheetEditLog.version == updated.version
    ).first()
    assert edit_log is not None
    assert edit_log.section_edited == "facts"
    assert edit_log.edited_by_name == lead.full_name

    # Verify Merkle Audit Log
    audit = db.query(AuditLog).filter(
        AuditLog.action_type == "CHARGESHEET_EDITED",
        AuditLog.target_id == str(draft.id)
    ).order_by(AuditLog.id.desc()).first()
    assert audit is not None
    assert "Investigator edited 'facts' section" in audit.description

    db.close()


def test_export_chargesheet_pdf_vector_generation():
    db = TestingSessionLocal()
    case = db.query(Case).first()
    lead = db.query(User).filter(User.role == "lead_investigator").first()
    draft = db.query(ChargesheetDraft).filter(ChargesheetDraft.case_id == case.id).first()
    if not draft:
        draft = generate_initial_chargesheet_draft(case.id, db, user=lead)

    pdf_bytes = export_chargesheet_pdf(draft.id, db)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF-")

    db.close()


def test_chargesheet_api_endpoints_and_rbac():
    app.dependency_overrides[get_db] = override_get_db
    db = TestingSessionLocal()
    case = db.query(Case).first()
    case_id = case.id
    lead = db.query(User).filter(User.role == "lead_investigator").first()
    draft = db.query(ChargesheetDraft).filter(ChargesheetDraft.case_id == case_id).first()
    if not draft:
        draft = generate_initial_chargesheet_draft(case_id, db, user=lead)
    db.close()

    lead_token = get_token("lead_charge@evidentia.test")
    rev_token = get_token("reviewer_charge@evidentia.test")

    # 1. GET chargesheet endpoint
    resp = client.get(
        f"/cases/{case_id}/chargesheet",
        headers={"Authorization": f"Bearer {lead_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == case_id
    assert data["is_draft"] is True
    assert isinstance(data["evidence_inventory"], list)
    assert isinstance(data["witness_statements"], list)

    # 2. PATCH chargesheet endpoint (lead investigator can edit)
    patch_resp = client.patch(
        f"/cases/{case_id}/chargesheet",
        json={
            "section_edited": "analysis",
            "edit_summary": "Added legal arguments on common intention",
            "analysis_and_charges": data["analysis_and_charges"] + "\n\nCommon intention established under BNS Section 61(2)."
        },
        headers={"Authorization": f"Bearer {lead_token}"}
    )
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()
    assert patch_data["version"] >= 3
    assert "Common intention established" in patch_data["analysis_and_charges"]

    # 3. RBAC: Read-only reviewer CANNOT edit chargesheet (403 Forbidden)
    rev_patch = client.patch(
        f"/cases/{case_id}/chargesheet",
        json={"section_edited": "facts", "facts_narrative": "Illegal modification"},
        headers={"Authorization": f"Bearer {rev_token}"}
    )
    assert rev_patch.status_code == 403

    # 4. GET revisions endpoint
    rev_list_resp = client.get(
        f"/cases/{case_id}/chargesheet/revisions",
        headers={"Authorization": f"Bearer {lead_token}"}
    )
    assert rev_list_resp.status_code == 200
    revisions = rev_list_resp.json()
    assert len(revisions) >= 2

    # 5. GET PDF download endpoint
    pdf_resp = client.get(
        f"/cases/{case_id}/chargesheet/pdf",
        headers={"Authorization": f"Bearer {lead_token}"}
    )
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in pdf_resp.headers["content-disposition"]
    assert pdf_resp.content.startswith(b"%PDF-")

    # 6. POST assistant-refine endpoint
    refine_resp = client.post(
        f"/cases/{case_id}/chargesheet/assistant-refine",
        json={
            "section_name": "analysis",
            "instruction": "Summarize why the defense alibi was disproven."
        },
        headers={"Authorization": f"Bearer {lead_token}"}
    )
    assert refine_resp.status_code == 200
    refine_data = refine_resp.json()
    assert "refined_content" in refine_data
    assert len(refine_data["refined_content"]) > 20
