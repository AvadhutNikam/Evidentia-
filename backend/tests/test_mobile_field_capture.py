"""
backend/tests/test_mobile_field_capture.py
==========================================
Integration tests for Mobile Evidence Capture:
1. On-device SHA-256 hash calculation & server-side verification.
2. Tamper/corruption detection when client hash mismatches byte stream.
3. Geo-temporal stamping (GPS lat/lon, accuracy, captured timestamp, device info).
4. Automatic First-Class Chain of Custody logging (FIELD_CAPTURE).
5. Mandatory officer confirmation and signed legal integrity declaration.
6. Field exhibit filtering endpoint and UI attributes.
"""

import hashlib
import io
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import app
from models import Case, User, CaseMember, Evidence, CustodyLog, AuditLog
from auth import hash_password, create_access_token
from mobile_capture_engine import calculate_sha256, verify_on_device_hash


@pytest.fixture
def field_test_setup(db: Session):
    """Sets up a test case and a lead investigator with field capture rights."""
    user = db.query(User).filter(User.email == "field_officer@evidentia.test").first()
    if not user:
        user = User(
            email="field_officer@evidentia.test",
            full_name="Inspector Aniket Shinde",
            hashed_password=hash_password("FieldPass123!"),
            role="lead_investigator",
            is_active=True,
            badge_number="SOCO-MUM-409"
        )
        db.add(user)
        db.flush()

    reviewer = db.query(User).filter(User.email == "reviewer_field@evidentia.test").first()
    if not reviewer:
        reviewer = User(
            email="reviewer_field@evidentia.test",
            full_name="Adv. K. Sharma",
            hashed_password=hash_password("ReviewerPass123!"),
            role="reviewer",
            is_active=True,
            badge_number="JUD-REV-088"
        )
        db.add(reviewer)
        db.flush()

    test_case = db.query(Case).filter(Case.title == "Operation Red Sandalwood Scene").first()
    if not test_case:
        test_case = Case(
            title="Operation Red Sandalwood Scene",
            description="Forest crime scene contraband seizure",
            status="Active",
            created_by="Inspector Aniket Shinde"
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

    db.commit()
    db.refresh(user)
    db.refresh(reviewer)
    db.refresh(test_case)

    user_token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    rev_token = create_access_token({"sub": str(reviewer.id), "email": reviewer.email, "role": reviewer.role})

    return {
        "user": user,
        "reviewer": reviewer,
        "case": test_case,
        "token": user_token,
        "rev_token": rev_token
    }


def test_on_device_hash_verification_utility():
    """Validates on-device SHA-256 calculation and matching logic."""
    test_bytes = b"Scene photograph of weapon recovered under wooden floorboards"
    expected_hash = hashlib.sha256(test_bytes).hexdigest().lower()

    calc_hash = calculate_sha256(test_bytes)
    assert calc_hash == expected_hash

    is_match, s_hash, c_hash = verify_on_device_hash(test_bytes, expected_hash)
    assert is_match is True
    assert s_hash == expected_hash

    # Mismatched hash
    is_match, s_hash, c_hash = verify_on_device_hash(test_bytes, "0000000000000000000000000000000000000000000000000000000000000000")
    assert is_match is False


def test_successful_field_evidence_capture(db: Session, client: TestClient, field_test_setup):
    """
    Validates end-to-end mobile field evidence capture:
    1. Uploads file with on-device computed SHA-256 hash.
    2. Attaches GPS coordinates, timestamp, and device metadata.
    3. Requires signed declaration and officer confirmation.
    4. Automatically logs CustodyLog action FIELD_CAPTURE and INTAKE.
    5. Returns exhibit marked as 'is_field_captured=True'.
    """
    c = field_test_setup["case"]
    tok = field_test_setup["token"]

    file_content = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00Simulated Scene Photo JPEG"
    client_hash = hashlib.sha256(file_content).hexdigest()

    declaration = "I hereby certify under Section 63/65B IEA that this photograph was captured directly at the crime scene without alteration."

    payload = {
        "client_computed_hash": client_hash,
        "officer_confirmed": "true",
        "officer_declaration": declaration,
        "evidence_type": "photograph",
        "title": "Recovered Timber Markings",
        "latitude": "19.076090",
        "longitude": "72.877726",
        "accuracy_meters": "4.5",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "device_info": "Pixel 8 Pro (Android 14, Camera v9.2)",
        "location_name": "Godown #4, Sector 7, Nhava Sheva Port Enclave",
        "tamper_seal_number": "SEAL-SOCO-2026-9912",
        "source_agency": "Special Task Force - Forest Crime Wing",
        "custody_notes": "Recovered from locked rear storage room."
    }

    files = {
        "file": ("scene_timber_photo.jpg", io.BytesIO(file_content), "image/jpeg")
    }

    res = client.post(
        f"/cases/{c.id}/evidence/field-capture",
        headers={"Authorization": f"Bearer {tok}"},
        data=payload,
        files=files
    )

    assert res.status_code == 200, f"Error: {res.text}"
    data = res.json()
    assert data["is_field_captured"] is True
    assert data["capture_source"] == "field_mobile"
    assert data["field_latitude"] == pytest.approx(19.076090, abs=1e-5)
    assert data["field_longitude"] == pytest.approx(72.877726, abs=1e-5)
    assert data["field_accuracy_meters"] == pytest.approx(4.5, abs=1e-2)
    assert data["field_officer_confirmed"] is True
    assert data["client_computed_hash"] == client_hash
    assert data["hash_match_verified"] is True
    assert data["field_tamper_seal_number"] == "SEAL-SOCO-2026-9912"
    assert "Nhava Sheva" in data["field_location_name"]

    # Verify Chain of Custody Entries in Database
    evidence_id = data["id"]
    custody_entries = db.query(CustodyLog).filter(CustodyLog.evidence_id == evidence_id).all()
    actions = [ce.action for ce in custody_entries]
    assert "FIELD_CAPTURE" in actions
    assert "INTAKE" in actions

    field_entry = next(ce for ce in custody_entries if ce.action == "FIELD_CAPTURE")
    assert "GPS: (19.076090, 72.877726" in field_entry.location
    assert "SEAL-SOCO-2026-9912" in field_entry.notes
    assert field_entry.file_hash_snapshot == client_hash


def test_field_evidence_tamper_detection_mismatched_hash(db: Session, client: TestClient, field_test_setup):
    """
    Validates that if on-device hash does not match uploaded byte stream,
    the server rejects the capture with HTTP 400 Cryptographic Hash Integrity Failure.
    """
    c = field_test_setup["case"]
    tok = field_test_setup["token"]

    real_bytes = b"Actual file bytes from scene"
    fake_client_hash = "deadbeef12345678deadbeef12345678deadbeef12345678deadbeef12345678"

    payload = {
        "client_computed_hash": fake_client_hash,
        "officer_confirmed": "true",
        "officer_declaration": "I hereby certify under penalty of perjury that this file is unaltered.",
        "latitude": "18.5204",
        "longitude": "73.8567"
    }

    files = {
        "file": ("corrupted_audio.wav", io.BytesIO(real_bytes), "audio/wav")
    }

    res = client.post(
        f"/cases/{c.id}/evidence/field-capture",
        headers={"Authorization": f"Bearer {tok}"},
        data=payload,
        files=files
    )

    assert res.status_code == 400
    assert "Cryptographic Hash Integrity Failure" in res.json()["detail"]


def test_field_evidence_requires_officer_confirmation_and_declaration(db: Session, client: TestClient, field_test_setup):
    """
    Validates that unconfirmed uploads or uploads lacking a legal declaration are rejected.
    """
    c = field_test_setup["case"]
    tok = field_test_setup["token"]

    file_bytes = b"Test photograph bytes"
    real_hash = hashlib.sha256(file_bytes).hexdigest()

    # 1. officer_confirmed is false
    res1 = client.post(
        f"/cases/{c.id}/evidence/field-capture",
        headers={"Authorization": f"Bearer {tok}"},
        data={
            "client_computed_hash": real_hash,
            "officer_confirmed": "false",
            "officer_declaration": "Valid declaration statement over 15 chars long"
        },
        files={"file": ("test.jpg", io.BytesIO(file_bytes), "image/jpeg")}
    )
    assert res1.status_code == 400
    assert "confirmation box" in res1.json()["detail"]

    # 2. officer_declaration is too short / missing
    res2 = client.post(
        f"/cases/{c.id}/evidence/field-capture",
        headers={"Authorization": f"Bearer {tok}"},
        data={
            "client_computed_hash": real_hash,
            "officer_confirmed": "true",
            "officer_declaration": "Too short"
        },
        files={"file": ("test.jpg", io.BytesIO(file_bytes), "image/jpeg")}
    )
    assert res2.status_code == 400
    assert "legal integrity declaration" in res2.json()["detail"]


def test_field_evidence_rbac_and_query_filter(db: Session, client: TestClient, field_test_setup):
    """
    Validates that:
    1. Reviewers cannot upload field evidence (HTTP 403).
    2. GET /cases/{id}/field-evidence returns only exhibits marked is_field_captured.
    """
    c = field_test_setup["case"]
    rev_tok = field_test_setup["rev_token"]
    officer_tok = field_test_setup["token"]

    file_bytes = b"Scene photo review test"
    real_hash = hashlib.sha256(file_bytes).hexdigest()

    # 1. Reviewer attempt blocked
    res_rev = client.post(
        f"/cases/{c.id}/evidence/field-capture",
        headers={"Authorization": f"Bearer {rev_tok}"},
        data={
            "client_computed_hash": real_hash,
            "officer_confirmed": "true",
            "officer_declaration": "Certified under Section 63/65B of Indian Evidence Act."
        },
        files={"file": ("photo.jpg", io.BytesIO(file_bytes), "image/jpeg")}
    )
    assert res_rev.status_code == 403

    # 2. Query field exhibits endpoint
    res_list = client.get(
        f"/cases/{c.id}/field-evidence",
        headers={"Authorization": f"Bearer {officer_tok}"}
    )
    assert res_list.status_code == 200
    items = res_list.json()
    assert isinstance(items, list)
    for it in items:
        assert it["is_field_captured"] is True
        assert it["capture_source"] == "field_mobile"

