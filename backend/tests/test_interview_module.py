"""
backend/tests/test_interview_module.py
Comprehensive test suite for Evidentia AI Interview & Deposition Module:
- Suggesting questions from contradictions, gaps, and unverified alibis.
- Storing answers/statements per interview session.
- Real-time claim comparison against prior statements and exhibits.
- Immediate contradiction flagging with dual linked quotes and audit logging.
- RBAC permissions (Read-only reviewers restricted from creating sessions or recording statements).
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
    Hypothesis, User, AuditLog, Contradiction, InvestigationTask,
    PriorRecord, CaseMember, Interview, InterviewStatement, InterviewContradiction
)
from auth import create_access_token, hash_password
from app import app
from interview_engine import (
    suggest_interview_questions,
    ensure_case_interviews,
    record_and_analyze_statement
)

TEST_DB_URL = "sqlite:///./test_interviews.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()

    # Seed test users
    admin = User(
        email="admin_int@evidentia.test",
        full_name="Admin Director",
        hashed_password=hash_password("AdminPass123!"),
        role="admin",
        badge_number="DIR-001"
    )
    lead = User(
        email="lead_int@evidentia.test",
        full_name="DSP Vikram Joshi",
        hashed_password=hash_password("LeadPass123!"),
        role="lead_investigator",
        badge_number="DSP-108"
    )
    analyst = User(
        email="analyst_int@evidentia.test",
        full_name="Analyst Priya Sharma",
        hashed_password=hash_password("AnalystPass123!"),
        role="analyst",
        badge_number="ANA-505"
    )
    reviewer = User(
        email="reviewer_int@evidentia.test",
        full_name="Judicial Reviewer Gupta",
        hashed_password=hash_password("RevPass123!"),
        role="reviewer",
        badge_number="REV-999"
    )
    db.add_all([admin, lead, analyst, reviewer])
    db.commit()

    # Seed test case
    case = Case(
        title="Yerwada Bank Robbery & Deposition Inquiry",
        description="Armed robbery case testing interview deposition contradictions, gap questions, and alibi checks.",
        status="Active",
        fir_number="FIR/Yerwada/342/2024",
        offence_section="Section 310 BNS / Section 392 IPC"
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    # Assign users to case
    for u in [admin, lead, analyst, reviewer]:
        cm = CaseMember(case_id=case.id, user_id=u.id, case_role=u.role, added_by="Setup")
        db.add(cm)
    db.commit()

    # Seed Evidence
    ev1 = Evidence(
        case_id=case.id,
        file_name="Yerwada_SBI_ATM_CCTV.mp4",
        file_type="video/mp4",
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        extracted_text="Yerwada SBI ATM CCTV Exhibit captures Yogesh Ashok Raut at 21:42:15 withdrawing cash with victim ATM card.",
        sec_65b_certificate_present=True,
        chain_of_custody_complete=True,
        source="Yerwada Police Vault"
    )
    ev2 = Evidence(
        case_id=case.id,
        file_name="FSL_Serology_Report.pdf",
        file_type="application/pdf",
        file_hash="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        extracted_text="FSL Kalina Serology report reveals latent O+ human blood matching victim Nayana Pujari on rear floor mat of Qualis.",
        sec_65b_certificate_present=True,
        chain_of_custody_complete=True,
        source="State FSL Mumbai"
    )
    db.add_all([ev1, ev2])
    db.commit()

    # Seed Contradictions
    c1 = Contradiction(
        case_id=case.id,
        statement_a="Suspect Yogesh Ashok Raut claimed he was at his residence in Khed all night on 07-Oct-2009.",
        source_a_id="Suspect Interrogation Form",
        statement_b="Yerwada SBI ATM CCTV Exhibit captures Yogesh Raut at 21:42:15 IST withdrawing cash with victim ATM card.",
        source_b_id=str(ev1.id),
        conflict_type="Alibi Discrepancy",
        confidence=98.0,
        status="Detected"
    )
    c2 = Contradiction(
        case_id=case.id,
        statement_a="Co-accused Rajesh Chaudhari stated that the cab never stopped at Kharadi Bypass.",
        source_a_id="Section 161 CrPC Statement",
        statement_b="Kharadi Cellular Tower Dump records co-accused IMEI stationary from 20:30 to 22:15 IST.",
        source_b_id="Cellular Tower Log",
        conflict_type="Timeline Conflict",
        confidence=96.0,
        status="Detected"
    )
    db.add_all([c1, c2])
    db.commit()

    # Seed Investigation Tasks (Gaps)
    t1 = InvestigationTask(
        case_id=case.id,
        task="Subpoena CDR cell tower records and schedule formal alibi verification interview for Yogesh Raut",
        priority="High",
        status="Open"
    )
    t2 = InvestigationTask(
        case_id=case.id,
        task="Verify missing timeline interval between 20:00 and 21:30 along Kharadi bypass",
        priority="High",
        status="Open"
    )
    db.add_all([t1, t2])
    db.commit()

    # Seed Prior Record (Unverified Alibi Context)
    pr1 = PriorRecord(
        case_id=case.id,
        suspect_name="Yogesh Raut",
        offense_type="Armed Highway Robbery",
        outcome="convicted",
        source_agency="Pune Rural Police"
    )
    db.add(pr1)
    db.commit()

    # Seed Entities
    ent1 = Entity(case_id=case.id, name="Yogesh Raut", type="suspect", confidence=0.98)
    ent2 = Entity(case_id=case.id, name="Rajesh Chaudhari", type="approver", confidence=0.95)
    db.add_all([ent1, ent2])
    db.commit()

    # Seed Initial Interview Sessions
    ensure_case_interviews(case.id, db)

    db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("./test_interviews.db"):
        try:
            os.remove("./test_interviews.db")
        except Exception:
            pass


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

def test_suggest_interview_questions_from_analysis():
    """
    Verifies that the engine dynamically suggests interrogation questions
    synthesized from contradictions, gaps, and unverified alibis.
    """
    db = TestingSessionLocal()
    case = db.query(Case).first()

    questions = suggest_interview_questions(
        case_id=case.id,
        interviewee_name="Yogesh Raut",
        db=db
    )
    db.close()

    assert len(questions) >= 3

    categories = {q["category"] for q in questions}
    assert "contradiction" in categories
    assert "gap" in categories
    assert "alibi" in categories

    # Verify contradiction question contains both statements
    contra_q = next(q for q in questions if q["category"] == "contradiction")
    assert "Alibi Discrepancy" in contra_q["title"] or "Timeline Conflict" in contra_q["title"]
    assert contra_q["quote_a"] is not None
    assert contra_q["quote_b"] is not None
    assert contra_q["severity"] == "critical"

    # Verify gap question targets open tasks / timeline
    gap_q = next(q for q in questions if q["category"] == "gap")
    assert "gap" in gap_q["category"].lower()
    assert "Investigative Gap" in gap_q["title"] or "Timeline" in gap_q["title"]

    # Verify unverified alibi question targets Yogesh Raut
    alibi_q = next(q for q in questions if q["category"] == "alibi")
    assert "Yogesh Raut" in alibi_q["title"] or "Alibi" in alibi_q["title"]
    assert alibi_q["is_subject_specific"] is True


def test_ensure_case_interviews_and_seed_data():
    """
    Verifies that default interview sessions and statements are initialized properly.
    """
    db = TestingSessionLocal()
    case = db.query(Case).first()

    interviews = ensure_case_interviews(case.id, db)
    assert len(interviews) >= 1
    int_session = interviews[0]
    session_code = int_session.session_code
    interviewee_name = int_session.interviewee_name
    int_id = int_session.id
    assert session_code is not None
    assert interviewee_name is not None

    stmts = db.query(InterviewStatement).filter(InterviewStatement.interview_id == int_id).all()
    assert len(stmts) >= 1
    assert stmts[0].text is not None
    db.close()


def test_record_statement_and_detect_immediate_contradiction():
    """
    Tests recording an answer and immediately detecting a contradiction against
    case evidence (e.g. CCTV exhibit) and prior depositions.
    Verifies that:
    1. Both quotes are linked side-by-side in InterviewContradiction.
    2. is_contradiction_flag is updated to True.
    3. Merkle AuditLog records INTERVIEW_CONTRADICTION_FLAGGED.
    """
    db = TestingSessionLocal()
    case = db.query(Case).first()
    lead = db.query(User).filter(User.role == "lead_investigator").first()
    interview = db.query(Interview).filter(Interview.case_id == case.id).first()
    if not interview:
        interviews = ensure_case_interviews(case.id, db)
        interview = interviews[0]

    # Statement 1: Subject claims alibi of being asleep in Khed (directly conflicts with CCTV at Yerwada)
    res = record_and_analyze_statement(
        interview_id=interview.id,
        payload={
            "speaker": interview.interviewee_name,
            "role": "interviewee",
            "timestamp_marker": "04:15",
            "seconds": 255,
            "question": "Where were you at 21:42 on the night of October 7th?",
            "question_source_type": "contradiction",
            "text": "I was at home in Khed sleeping all night and never went to Yerwada."
        },
        db=db,
        user=lead
    )

    assert res["has_contradiction"] is True
    assert len(res["new_contradictions"]) >= 1

    c = res["new_contradictions"][0]
    assert "home in Khed" in c["quote_new"]
    assert "ATM" in c["quote_prior"] or "Yerwada" in c["quote_prior"] or "CCTV" in c["quote_prior"]
    assert c["conflict_type"] == "Alibi Discrepancy"
    assert c["severity"] == "critical"
    assert c["confidence"] >= 95.0

    # Verify statement in DB has is_contradiction_flag = True
    stmt_id = res["statement"]["id"]
    db_stmt = db.query(InterviewStatement).filter(InterviewStatement.id == stmt_id).first()
    assert db_stmt.is_contradiction_flag is True

    # Verify Merkle audit event was created
    audit = db.query(AuditLog).filter(
        AuditLog.action_type == "INTERVIEW_CONTRADICTION_FLAGGED",
        AuditLog.case_id == case.id
    ).order_by(AuditLog.id.desc()).first()
    assert audit is not None
    assert "Alibi Discrepancy" in audit.description
    assert audit.current_hash is not None

    db.close()


def test_cross_statement_contradiction_between_interviewees():
    """
    Tests detecting a contradiction between two separate statements:
    Statement A states subject was alone; earlier statement by co-accused stated accomplices were present.
    """
    db = TestingSessionLocal()
    case = db.query(Case).first()
    lead = db.query(User).filter(User.role == "lead_investigator").first()
    interview = db.query(Interview).filter(Interview.case_id == case.id).first()
    if not interview:
        interviews = ensure_case_interviews(case.id, db)
        interview = interviews[0]

    # First add a prior statement from Rajesh Chaudhari
    prior_stmt = InterviewStatement(
        interview_id=interview.id,
        case_id=case.id,
        sequence_order=10,
        speaker="Rajesh Chaudhari",
        role="interviewee",
        timestamp_marker="02:00",
        seconds=120,
        question="Who was in the vehicle?",
        text="Vishwas Kadam and Mahesh Thakur were in the vehicle and accompanied us.",
        is_contradiction_flag=False
    )
    db.add(prior_stmt)
    db.commit()

    # Now add new statement where subject claims being completely alone
    res = record_and_analyze_statement(
        interview_id=interview.id,
        payload={
            "speaker": "Yogesh Raut",
            "role": "interviewee",
            "timestamp_marker": "06:10",
            "seconds": 370,
            "question": "Confirm who was in the vehicle with you.",
            "text": "I was completely alone by myself in the vehicle on that evening."
        },
        db=db,
        user=lead
    )

    assert res["has_contradiction"] is True
    found_accomplice_conflict = any(
        c["conflict_type"] == "Accomplice Divergence"
        for c in res["new_contradictions"]
    )
    assert found_accomplice_conflict is True

    db.close()


def test_interview_api_endpoints_and_rbac():
    """
    Tests REST API endpoints for interviews, suggested questions, statement recording,
    and RBAC restrictions (Reviewer cannot record statements or create sessions).
    """
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    db = TestingSessionLocal()
    case = db.query(Case).first()
    case_id = case.id
    interview = db.query(Interview).filter(Interview.case_id == case_id).first()
    interview_id = interview.id
    db.close()

    lead_token = get_token("lead_int@evidentia.test")
    analyst_token = get_token("analyst_int@evidentia.test")
    rev_token = get_token("reviewer_int@evidentia.test")

    # 1. GET /cases/{case_id}/interviews
    resp = client.get(
        f"/cases/{case_id}/interviews",
        headers={"Authorization": f"Bearer {analyst_token}"}
    )
    assert resp.status_code == 200
    interviews = resp.json()
    assert len(interviews) >= 1
    assert "statement_count" in interviews[0]

    # 2. GET /cases/{case_id}/interviews/suggested-questions
    sug_resp = client.get(
        f"/cases/{case_id}/interviews/suggested-questions?interviewee_name=Yogesh+Raut",
        headers={"Authorization": f"Bearer {analyst_token}"}
    )
    assert sug_resp.status_code == 200
    questions = sug_resp.json()
    assert len(questions) >= 2
    assert any(q["category"] == "contradiction" for q in questions)

    # 3. GET /cases/{case_id}/interviews/{interview_id}
    detail_resp = client.get(
        f"/cases/{case_id}/interviews/{interview_id}",
        headers={"Authorization": f"Bearer {lead_token}"}
    )
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert "statements" in detail
    assert "contradictions" in detail

    # 4. POST /cases/{case_id}/interviews/{interview_id}/statements (Lead can record and analyze)
    stmt_payload = {
        "speaker": "Yogesh Raut",
        "role": "interviewee",
        "timestamp_marker": "08:20",
        "seconds": 500,
        "question": "Did you take the vehicle to Hadapsar?",
        "text": "The vehicle never stopped at Kharadi bypass and proceeded elsewhere."
    }
    add_resp = client.post(
        f"/cases/{case_id}/interviews/{interview_id}/statements",
        json=stmt_payload,
        headers={"Authorization": f"Bearer {lead_token}"}
    )
    assert add_resp.status_code == 200
    stmt_data = add_resp.json()
    assert stmt_data["statement"]["speaker"] == "Yogesh Raut"
    assert stmt_data["has_contradiction"] is True
    assert len(stmt_data["new_contradictions"]) >= 1

    # 5. RBAC: Read-only Reviewer CANNOT record statement (403 Forbidden)
    rev_post = client.post(
        f"/cases/{case_id}/interviews/{interview_id}/statements",
        json=stmt_payload,
        headers={"Authorization": f"Bearer {rev_token}"}
    )
    assert rev_post.status_code == 403

    # 6. RBAC: Read-only Reviewer CANNOT create new interview session (403 Forbidden)
    rev_create = client.post(
        f"/cases/{case_id}/interviews",
        json={
            "interviewee_name": "Unauthorized Interview",
            "interviewer_name": "Reviewer"
        },
        headers={"Authorization": f"Bearer {rev_token}"}
    )
    assert rev_create.status_code == 403

    # 7. GET /cases/{case_id}/interviews/{interview_id}/contradictions
    contra_resp = client.get(
        f"/cases/{case_id}/interviews/{interview_id}/contradictions",
        headers={"Authorization": f"Bearer {lead_token}"}
    )
    assert contra_resp.status_code == 200
    contradictions = contra_resp.json()
    assert len(contradictions) >= 1
    assert "quote_new" in contradictions[0]
    assert "quote_prior" in contradictions[0]
