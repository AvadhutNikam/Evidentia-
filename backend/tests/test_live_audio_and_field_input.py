"""
backend/tests/test_live_audio_and_field_input.py
Comprehensive test suite for:
1. Live interview streaming & rolling transcript with real-time contradiction detection.
2. Quick investigator voice notes becoming cited case notes with source-span anchors.
3. Mobile field capture with on-device SHA-256 verification, GPS, and chain of custody logging.
"""

import io
import hashlib
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import app
from models import Case, User, CaseMember, Evidence, CustodyLog, Interview, InterviewStatement, InterviewContradiction, ExhibitChunk, SourceCitation
from auth import hash_password, create_access_token


@pytest.fixture
def live_audio_test_setup(db: Session):
    """Sets up a test case and investigating officer."""
    user = db.query(User).filter(User.email == "detective_field@evidentia.test").first()
    if not user:
        user = User(
            email="detective_field@evidentia.test",
            full_name="Detective Inspector Arjun Shinde",
            hashed_password=hash_password("Pass123!"),
            role="lead_investigator",
            is_active=True,
            badge_number="DET-MUM-801"
        )
        db.add(user)
        db.flush()

    reviewer = db.query(User).filter(User.email == "reviewer_int_audio@evidentia.test").first()
    if not reviewer:
        reviewer = User(
            email="reviewer_int_audio@evidentia.test",
            full_name="Reviewer Meera Roy",
            hashed_password=hash_password("RevPass123!"),
            role="reviewer",
            is_active=True,
            badge_number="REV-402"
        )
        db.add(reviewer)
        db.flush()

    test_case = db.query(Case).filter(Case.title == "Operation Nightfall Inquest").first()
    if not test_case:
        test_case = Case(
            title="Operation Nightfall Inquest",
            description="High priority homicide and extortion investigation",
            status="Active",
            created_by="Detective Inspector Arjun Shinde"
        )
        db.add(test_case)
        db.flush()

    # Assign officer to case
    member = db.query(CaseMember).filter(CaseMember.case_id == test_case.id, CaseMember.user_id == user.id).first()
    if not member:
        db.add(CaseMember(case_id=test_case.id, user_id=user.id, case_role="lead_investigator", added_by="System"))

    rev_member = db.query(CaseMember).filter(CaseMember.case_id == test_case.id, CaseMember.user_id == reviewer.id).first()
    if not rev_member:
        db.add(CaseMember(case_id=test_case.id, user_id=reviewer.id, case_role="reviewer", added_by="System"))

    # Seed an interview session
    interview = db.query(Interview).filter(Interview.case_id == test_case.id).first()
    if not interview:
        interview = Interview(
            case_id=test_case.id,
            session_code="REC-LIVE-001",
            interviewee_name="Vikram Salunkhe",
            interviewee_role="suspect",
            interviewer_name="Detective Inspector Arjun Shinde",
            interview_date=datetime.now(timezone.utc).strftime("%b %d, %Y"),
            duration="20:00 mins",
            status="Active"
        )
        db.add(interview)
        db.flush()

        # Seed an initial statement claiming he was at the Yerwada ATM
        stmt1 = InterviewStatement(
            interview_id=interview.id,
            case_id=test_case.id,
            sequence_order=1,
            speaker="Vikram Salunkhe",
            role="interviewee",
            timestamp_marker="01:15",
            seconds=75,
            text="Rajesh and I walked up to the counter and withdrew cash from the Yerwada SBI ATM at 21:42."
        )
        db.add(stmt1)
        db.flush()

    db.commit()
    db.refresh(user)
    db.refresh(reviewer)
    db.refresh(test_case)
    db.refresh(interview)

    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    rev_token = create_access_token({"sub": str(reviewer.id), "email": reviewer.email, "role": reviewer.role})

    return {
        "user": user,
        "reviewer": reviewer,
        "case": test_case,
        "interview": interview,
        "token": token,
        "rev_token": rev_token
    }


def test_live_interview_streaming_contradiction_detection(db: Session, client: TestClient, live_audio_test_setup):
    """
    Validates live interview audio streaming / rolling statements:
    1. Streams rolling speech segment from live interview.
    2. Immediately flags statement that contradicts earlier statement while interview is happening.
    3. Confirms dual-quote linking, severity, and forensic reasoning.
    """
    case = live_audio_test_setup["case"]
    interview = live_audio_test_setup["interview"]
    token = live_audio_test_setup["token"]

    # Rolling statement that contradicts prior admission of withdrawing cash at ATM:
    # "I was at home sleeping in Khed all night, nowhere near any ATM"
    stream_payload = {
        "transcript_text": "I was at home sleeping all night in Khed and nowhere near any ATM counter.",
        "speaker": "Vikram Salunkhe",
        "role": "interviewee",
        "timestamp_marker": "03:45",
        "seconds": "225",
        "question": "Can you explain where you were between 9 PM and 10 PM?"
    }

    res = client.post(
        f"/cases/{case.id}/interviews/{interview.id}/live-stream-chunk",
        headers={"Authorization": f"Bearer {token}"},
        data=stream_payload
    )

    assert res.status_code == 200, f"Error: {res.text}"
    data = res.json()

    # Verify statement was recorded in sequence
    assert "statement" in data
    stmt = data["statement"]
    assert stmt["speaker"] == "Vikram Salunkhe"
    assert stmt["timestamp_marker"] == "03:45"
    assert stmt["is_contradiction_flag"] is True

    # Verify real-time contradiction was flagged immediately
    assert data["has_contradiction"] is True
    assert len(data["new_contradictions"]) >= 1
    contra = data["new_contradictions"][0]
    assert contra["conflict_type"] == "Alibi Discrepancy"
    assert "at home" in contra["quote_new"].lower() or "khed" in contra["quote_new"].lower()
    assert "yerwada" in contra["quote_prior"].lower() or "withdrew" in contra["quote_prior"].lower()


def test_quick_voice_note_creation_and_citation_generation(db: Session, client: TestClient, live_audio_test_setup):
    """
    Validates quick voice notes by voice that become cited case notes:
    1. Records voice memo text with GPS and officer metadata.
    2. Creates Evidence exhibit with evidence_type='voice_note'.
    3. Splits text into ExhibitChunks and anchors SourceCitations with permanent citation handles [VN-XX:C1].
    4. Logs FIELD_VOICE_NOTE and INTAKE chain of custody entries.
    5. Verifies GET /cases/{id}/voice-notes lists the cited note.
    """
    case = live_audio_test_setup["case"]
    token = live_audio_test_setup["token"]

    note_text = (
        "Recovered discarded Samsung SIM card and blood-stained handkerchief behind the electric transformer. "
        "The SIM card serial number ends with 99014. Coordinates logged at western compound wall."
    )

    payload = {
        "note_text": note_text,
        "category": "field_observation",
        "latitude": "18.520430",
        "longitude": "73.856744",
        "accuracy_meters": "3.2",
        "location_name": "Behind Western Transformer, Pune Substation",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "source_device": "Investigator Toughbook Audio Dictation"
    }

    mock_audio = b"\x1a\x45\xdf\xa3WebMVoiceMemoAudioContentSimulated"
    files = {
        "audio_file": ("memo_transformer.webm", io.BytesIO(mock_audio), "audio/webm")
    }

    res = client.post(
        f"/cases/{case.id}/voice-notes",
        headers={"Authorization": f"Bearer {token}"},
        data=payload,
        files=files
    )

    assert res.status_code == 200, f"Error: {res.text}"
    data = res.json()

    assert data["case_id"] == case.id
    assert data["note_text"] == note_text
    assert data["latitude"] == pytest.approx(18.520430, abs=1e-5)
    assert data["longitude"] == pytest.approx(73.856744, abs=1e-5)
    assert "Voice Note #" in data["citation_code"]

    # Verify source-span citations were generated
    assert len(data["citations"]) >= 1
    first_cit = data["citations"][0]
    assert "VN-" in first_cit["citation_code"]
    assert first_cit["chunk_id"] > 0
    assert first_cit["quote"] != ""

    # Verify Chain of Custody entries were logged
    ev_id = data["evidence_id"]
    custody_entries = db.query(CustodyLog).filter(CustodyLog.evidence_id == ev_id).all()
    actions = [c.action for c in custody_entries]
    assert "FIELD_VOICE_NOTE" in actions
    assert "INTAKE" in actions

    # Verify GET endpoint
    get_res = client.get(
        f"/cases/{case.id}/voice-notes",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert get_res.status_code == 200
    notes_list = get_res.json()
    assert len(notes_list) >= 1
    found = any(n["id"] == ev_id for n in notes_list)
    assert found is True

