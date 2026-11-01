"""
backend/tests/test_system_health_and_data_quality.py
Unit and integration tests for:
1. Live System Health Diagnostics (Queue length, Job success rate, AI services, Time since backup).
2. Exhibit Data-Quality Scoring Engine (4 Pillars: Text, Hash, Sec 65B Certificate, Language Review).
3. Weakest items first priority ordering and on-demand integrity remediation.
"""

import hashlib
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import app
from models import (
    User, Case, CaseMember, Evidence, Job, BackupRecord,
    CustodyLog, ExhibitTranslation
)
from auth import hash_password, create_access_token
from system_health_engine import get_live_system_health, format_seconds_human
from data_quality_engine import calculate_exhibit_data_quality, get_case_data_quality_report


@pytest.fixture
def health_test_setup(db: Session):
    """Sets up an investigator, a case, and test data."""
    user = db.query(User).filter(User.email == "health_officer@evidentia.test").first()
    if not user:
        user = User(
            email="health_officer@evidentia.test",
            full_name="Captain Rajesh Verma",
            hashed_password=hash_password("Pass123!"),
            role="lead_investigator",
            is_active=True,
            badge_number="SYS-CAP-99"
        )
        db.add(user)
        db.flush()

    test_case = db.query(Case).filter(Case.title == "Telemetry & Quality Evaluation Case").first()
    if not test_case:
        test_case = Case(
            title="Telemetry & Quality Evaluation Case",
            description="Testing system health telemetry and forensic data quality",
            status="Active",
            created_by="Captain Rajesh Verma"
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

    token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )
    headers = {"Authorization": f"Bearer {token}"}

    return {
        "user": user,
        "case": test_case,
        "token": token,
        "headers": headers
    }


def test_format_seconds_human():
    assert format_seconds_human(10) == "10 seconds ago"
    assert format_seconds_human(120) == "2 mins ago"
    assert format_seconds_human(3700) == "1 hour ago"
    assert format_seconds_human(7500) == "2 hours ago"
    assert format_seconds_human(90000) == "1 day ago"


def test_live_system_health_engine_and_endpoint(health_test_setup, client: TestClient, db: Session):
    """Tests queue metrics, job success rate, AI availability, and backup tracking."""
    case = health_test_setup["case"]
    headers = health_test_setup["headers"]

    # 1. Seed some jobs
    j1 = Job(
        case_id=case.id,
        job_type="analysis",
        status="completed",
        progress_pct=100,
        current_stage="complete",
        created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        started_at=datetime.now(timezone.utc) - timedelta(minutes=9),
        finished_at=datetime.now(timezone.utc) - timedelta(minutes=8)
    )
    j2 = Job(
        case_id=case.id,
        job_type="analysis",
        status="pending",
        progress_pct=0,
        current_stage="queued",
        created_at=datetime.now(timezone.utc) - timedelta(minutes=2)
    )
    j3 = Job(
        case_id=case.id,
        job_type="ocr",
        status="running",
        progress_pct=45,
        current_stage="ocr_processing",
        created_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        started_at=datetime.now(timezone.utc) - timedelta(seconds=30)
    )
    db.add_all([j1, j2, j3])

    # 2. Seed a backup record
    b1 = BackupRecord(
        backup_filename="evidentia_backup_20261030.db",
        storage_path="backups/evidentia_backup_20261030.db",
        size_bytes=1048576,
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        backup_type="full",
        created_by="Automated Test",
        created_at=datetime.now(timezone.utc) - timedelta(minutes=25),
        restore_test_status="passed",
        restore_test_notes="Automated sandbox restore test verified PRAGMA integrity_check."
    )
    db.add(b1)
    db.commit()

    # Call endpoint
    resp = client.get("/system/health", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["system_status"] in ["operational", "degraded"]
    assert "timestamp" in data
    assert data["uptime_seconds"] >= 0

    # Queue checks
    queue = data["queue"]
    assert queue["pending_jobs_count"] >= 1
    assert queue["running_jobs_count"] >= 1
    assert queue["total_active_queue"] >= 2
    assert queue["queue_status"] in ["healthy", "busy", "congested", "idle"]

    # Job success checks
    job_success = data["job_success"]
    assert job_success["total_jobs"] >= 3
    assert job_success["completed_jobs"] >= 1
    assert job_success["success_rate_pct"] > 0
    assert len(job_success["recent_jobs"]) > 0

    # AI Service checks
    ai_services = data["ai_services"]
    assert len(ai_services) >= 4
    service_names = [s["service_name"] for s in ai_services]
    assert any("Gemini" in s for s in service_names)
    assert any("Air-Gap LLM" in s for s in service_names)
    assert any("Whisper" in s for s in service_names)
    assert any("Tesseract" in s for s in service_names)

    # Backup checks
    backup = data["backup"]
    assert backup["last_backup_id"] is not None
    assert "ago" in backup["time_since_backup_human"]
    assert backup["restore_test_status"] == "passed"
    assert backup["last_backup_hash"] is not None


def test_trigger_manual_backup_endpoint(health_test_setup, client: TestClient, db: Session):
    """Verifies triggering an on-demand encrypted backup with integrity validation."""
    headers = health_test_setup["headers"]

    resp = client.post("/system/backup/trigger", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["last_backup_id"] is not None
    assert data["backup_status"] in ["up_to_date", "due"]
    assert data["restore_test_status"] == "passed"
    assert "seconds ago" in data["time_since_backup_human"] or "min" in data["time_since_backup_human"]


def test_data_quality_scoring_weakest_first(health_test_setup, client: TestClient, db: Session):
    """
    Tests 4-pillar data quality scoring and verifies that:
    1. Exhibits are strictly sorted WEAKEST FIRST by composite quality score.
    2. Pillars (Text, Hash, Certificate, Language) are computed accurately.
    3. Weakest item with missing certificate, unverified hash, and low OCR appears at index 0.
    """
    case = health_test_setup["case"]
    headers = health_test_setup["headers"]

    # Exhibit 1: Pristine Exhibit (High Text 95%, Verified Hash 100%, Sec 65B Cert 100%, English 100%)
    ev_pristine = Evidence(
        case_id=case.id,
        file_name="Pristine_CCTV_Log.pdf",
        file_type="application/pdf",
        evidence_type="document",
        file_hash="a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90",
        hash_verified=True,
        hash_match_verified=True,
        sec_65b_certificate_present=True,
        primary_language="en",
        extracted_text="Fully verified CCTV entry and exit timestamps outside building lobby from 21:00 to 23:30 hours with certified hash.",
        uploaded_by="Captain Rajesh Verma"
    )

    # Exhibit 2: Medium Quality Exhibit (Moderate OCR 70%, Verified Hash 100%, Missing Cert 0%, English 100%)
    ev_medium = Evidence(
        case_id=case.id,
        file_name="Bank_Statement_Scan.png",
        file_type="image/png",
        evidence_type="document",
        file_hash="b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90a1",
        hash_verified=True,
        hash_match_verified=True,
        sec_65b_certificate_present=False,  # Missing 65B!
        primary_language="en",
        extracted_text="Account statement showing transfer of Rs 50,000 to merchant ID 8891.",
        ocr_confidence=70.0,
        uploaded_by="Sub-Inspector Deshmukh"
    )

    # Exhibit 3: Weak / Critical Quality Exhibit (Low OCR 38%, Unverified Hash, Missing Cert, Untranslated Marathi Dialect)
    ev_weakest = Evidence(
        case_id=case.id,
        file_name="Faded_Handwritten_Note.jpg",
        file_type="image/jpeg",
        evidence_type="document",
        file_hash=None,  # Missing hash!
        hash_verified=False,
        hash_match_verified=False,
        sec_65b_certificate_present=False,  # Missing 65B!
        primary_language="mr",  # Untranslated regional Marathi!
        extracted_text="संशयित इसम रात्री १० वाजता...",
        ocr_confidence=38.0,
        uploaded_by="Constable Patil"
    )

    db.add_all([ev_pristine, ev_medium, ev_weakest])
    db.commit()

    # Query Case Data Quality report
    resp = client.get(f"/cases/{case.id}/evidence/data-quality", headers=headers)
    assert resp.status_code == 200, resp.text
    report = resp.json()

    assert report["case_id"] == case.id
    assert report["total_exhibits"] >= 3
    assert report["weak_exhibits_count"] >= 1
    assert report["missing_certificates_count"] >= 2

    sorted_items = report["sorted_exhibits"]
    assert len(sorted_items) >= 3

    # CRITICAL CHECK: WEAKEST FIRST
    # The first item must have the lowest overall_quality_score
    first_item = sorted_items[0]
    last_item = sorted_items[-1]

    assert first_item["overall_quality_score"] <= last_item["overall_quality_score"]
    assert first_item["evidence_id"] == ev_weakest.id
    assert first_item["quality_tier"] in ["Critical Attention Needed", "Weak Quality"]
    assert first_item["is_weak_item"] is True

    # Check 4 pillars of the weakest item
    p = first_item["pillars"]
    assert p["text_confidence_pct"] == 38.0
    assert p["hash_score"] == 0.0
    assert p["certificate_score"] == 0.0
    assert p["language_status"] == "untranslated"
    assert len(first_item["warning_flags"]) >= 3
    assert "Run OCR" in first_item["recommended_action"] or "hash" in first_item["recommended_action"].lower() or "certificate" in first_item["recommended_action"].lower() or "transcript" in first_item["recommended_action"].lower() or "translation" in first_item["recommended_action"].lower()

    # The last item must be the pristine exhibit
    assert last_item["evidence_id"] == ev_pristine.id
    assert last_item["overall_quality_score"] >= 90.0
    assert last_item["pillars"]["certificate_score"] == 25.0
    assert last_item["pillars"]["hash_score"] == 25.0
    assert last_item["pillars"]["language_status"] == "native_english"


def test_recompute_hash_remediation_endpoint(health_test_setup, client: TestClient, db: Session):
    """Verifies that on-demand hash recomputation elevates an exhibit's quality score."""
    case = health_test_setup["case"]
    headers = health_test_setup["headers"]

    ev = Evidence(
        case_id=case.id,
        file_name="Unverified_Ledger.csv",
        file_type="text/csv",
        evidence_type="financial",
        file_hash=None,
        hash_verified=False,
        hash_match_verified=False,
        sec_65b_certificate_present=True,
        primary_language="en",
        extracted_text="Transaction ID 9012, Amount 14000, Payee XYZ Logistics",
        uploaded_by="Captain Rajesh Verma"
    )
    db.add(ev)
    db.commit()

    # Pre-check score: hash pillar should be 0.0
    initial_score = calculate_exhibit_data_quality(ev, db)
    assert initial_score["pillars"]["hash_score"] == 0.0

    # Call remediation endpoint
    resp = client.post(f"/cases/{case.id}/evidence/{ev.id}/verify-hash", headers=headers)
    assert resp.status_code == 200, resp.text
    updated = resp.json()

    # Post-check: hash pillar is now 25.0, overall score improved
    assert updated["pillars"]["hash_score"] == 25.0
    assert updated["pillars"]["hash_status"] == "verified"
    assert updated["overall_quality_score"] > initial_score["overall_quality_score"]

    # Verify custody log recorded
    log = (
        db.query(CustodyLog)
        .filter(CustodyLog.evidence_id == ev.id, CustodyLog.action == "INTEGRITY_VERIFY")
        .first()
    )
    assert log is not None
