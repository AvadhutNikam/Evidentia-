"""
Tests for Cryptographic Merkle Audit Chain & Evidence Integrity.
Validates:
1. Merkle chain sequential hashing and cryptographic link validity.
2. Immediate detection of row modification (tampered payload/description/value).
3. Immediate detection of broken chain links (tampered previous_hash).
4. Full API endpoint verification via FastAPI routers.
"""

import pytest
from audit_engine import log_audit_event, verify_audit_chain, GENESIS_HASH
from models import AuditLog, Case


def test_audit_chain_sequential_integrity(db):
    """Verifies that sequentially logged events build a valid, unbroken Merkle chain."""
    # Create a dummy case
    case = Case(title="Audit Test Case", description="Testing audit chain")
    db.add(case)
    db.commit()
    db.refresh(case)

    # Log sequential audit events
    log_audit_event(
        db=db,
        case_id=case.id,
        user_name="Detective John",
        action_type="CREATE_CASE",
        target_type="case",
        target_id=str(case.id),
        description="Created case docket",
        after_value={"title": case.title}
    )

    log_audit_event(
        db=db,
        case_id=case.id,
        user_name="Analyst Alice",
        action_type="UPLOAD_EXHIBIT",
        target_type="evidence",
        target_id="101",
        description="Uploaded forensic DNA report",
        after_value={"filename": "dna_report.pdf"}
    )

    log_audit_event(
        db=db,
        case_id=case.id,
        user_name="Analyst Alice",
        action_type="RUN_SCORING",
        target_type="scoring_run",
        target_id="1",
        description="Executed Bayesian ACH recalculation",
        after_value={"primary_suspect": "Suspect A"}
    )

    res = verify_audit_chain(db, case_id=case.id)
    assert res["chain_intact"] is True
    assert res["status"] == "VALID"
    assert res["total_entries"] >= 3
    assert res["verified_count"] >= 3


def test_tamper_detection_on_row_content_modification(db):
    """Modifying any row data directly in the database immediately triggers TAMPER_DETECTED."""
    case = Case(title="Tamper Test Case", description="Testing tamper detection")
    db.add(case)
    db.commit()

    entry1 = log_audit_event(
        db=db,
        case_id=case.id,
        user_name="Officer One",
        action_type="ADD_HYPOTHESIS",
        target_type="hypothesis",
        target_id="1",
        description="Original authentic entry 1"
    )

    entry2 = log_audit_event(
        db=db,
        case_id=case.id,
        user_name="Officer One",
        action_type="ADD_HYPOTHESIS",
        target_type="hypothesis",
        target_id="2",
        description="Original authentic entry 2"
    )

    # Chain is initially valid
    initial_check = verify_audit_chain(db)
    assert initial_check["chain_intact"] is True

    # Maliciously tamper with entry 2 description without updating hash
    log_to_tamper = db.query(AuditLog).filter(AuditLog.id == entry2.id).first()
    log_to_tamper.description = "MALICIOUSLY ALTERED EVIDENCE RECORD"
    db.commit()

    # Verify audit chain catches the modification
    tamper_check = verify_audit_chain(db)
    assert tamper_check["chain_intact"] is False
    assert tamper_check["status"] == "TAMPER_DETECTED"
    assert tamper_check["tampered_entry_id"] == entry2.id


def test_tamper_detection_on_broken_hash_link(db):
    """Modifying previous_hash breaks the cryptographic link and is flagged."""
    case = Case(title="Link Break Test", description="Testing link tampering")
    db.add(case)
    db.commit()

    entry1 = log_audit_event(
        db=db,
        case_id=case.id,
        user_name="Officer One",
        action_type="NOTE",
        target_type="case",
        target_id=str(case.id),
        description="Block 1"
    )

    entry2 = log_audit_event(
        db=db,
        case_id=case.id,
        user_name="Officer One",
        action_type="NOTE",
        target_type="case",
        target_id=str(case.id),
        description="Block 2"
    )

    # Tamper with previous_hash pointer
    log_to_tamper = db.query(AuditLog).filter(AuditLog.id == entry2.id).first()
    log_to_tamper.previous_hash = "deadbeef" * 8
    db.commit()

    tamper_check = verify_audit_chain(db)
    assert tamper_check["chain_intact"] is False
    assert tamper_check["status"] == "TAMPER_DETECTED"
    assert tamper_check["tampered_entry_id"] == entry2.id


def test_audit_chain_router_endpoints(client, admin_headers, db):
    """Tests the GET /cases/{case_id}/audit-chain and POST /audit/verify-chain router endpoints."""
    # Create a test case
    case = Case(title="API Audit Case", description="Docket for API test")
    db.add(case)
    db.commit()

    log_audit_event(
        db=db,
        case_id=case.id,
        user_name="Admin",
        action_type="SYSTEM_INIT",
        target_type="case",
        target_id=str(case.id),
        description="Initialized system audit"
    )

    # Call verify-chain endpoint
    resp = client.get("/audit/verify-chain", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["chain_intact"] is True
    assert data["status"] == "VALID"

    # Call case-specific audit chain endpoint
    resp_case = client.get(f"/cases/{case.id}/audit-chain", headers=admin_headers)
    assert resp_case.status_code == 200
    case_chain = resp_case.json()
    assert case_chain["chain_intact"] is True


def test_verify_evidence_integrity_file_missing_fails_with_tamper_alert(db):
    """
    Verifies Problem A Fix:
    If the physical evidence file is missing on disk, verify_evidence_integrity must:
    1. NEVER fall back to synthetic or stored hash to pass trivially.
    2. Fail with 'file missing, cannot verify' (success=False, integrity_verified=False).
    3. Update Evidence.hash_verified to False and reduce reliability score.
    4. Write a critical tamper alert to the Alert table.
    5. Log FILE_MISSING_TAMPER in CustodyLog and TAMPER_OR_MISSING in AuditLog.
    """
    from audit_engine import verify_evidence_integrity
    from models import Evidence, Alert, CustodyLog

    case = Case(title="Missing File Test Docket", description="Testing missing file verification failure")
    db.add(case)
    db.commit()
    db.refresh(case)

    # Create evidence pointing to a non-existent file
    ev = Evidence(
        case_id=case.id,
        file_name="missing_ballistics_scan.pdf",
        file_type="application/pdf",
        evidence_type="forensic",
        source="Central Forensic Science Laboratory",
        file_hash="a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
        storage_path="uploads/non_existent_file_99999.pdf",
        quality_rating=4.5,
        hash_verified=True  # Initially marked True to test that failure flips it
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    res = verify_evidence_integrity(
        db=db,
        evidence_id=ev.id,
        user_name="Forensic Inspector Rao",
        user_id=1
    )

    # 1. Assert failure status and exact message
    assert res["success"] is False
    assert res["integrity_verified"] is False
    assert res["is_match"] is False
    assert res["status"] == "FILE_MISSING_TAMPER"
    assert "file missing, cannot verify" in res["message"].lower()

    # 2. Assert evidence row updated in DB
    db.refresh(ev)
    assert ev.hash_verified is False
    assert ev.quality_rating <= 1.0

    # 3. Assert critical tamper alert created in Alert table
    alert = db.query(Alert).filter(
        Alert.case_id == case.id,
        Alert.linked_item_id == str(ev.id),
        Alert.rule_type == "integrity_failure"
    ).first()
    assert alert is not None
    assert alert.severity == "critical"
    assert "file missing, cannot verify" in alert.message.lower()

    # 4. Assert chain of custody log recorded
    custody_entry = db.query(CustodyLog).filter(
        CustodyLog.evidence_id == ev.id,
        CustodyLog.action == "FILE_MISSING_TAMPER"
    ).first()
    assert custody_entry is not None
    assert "file missing, cannot verify" in custody_entry.notes.lower()

    # 5. Assert audit ledger entry recorded
    audit_entry = db.query(AuditLog).filter(
        AuditLog.case_id == case.id,
        AuditLog.target_id == str(ev.id),
        AuditLog.action_type == "TAMPER_OR_MISSING"
    ).first()
    assert audit_entry is not None
    assert "file missing, cannot verify" in audit_entry.description.lower()


def test_verify_evidence_integrity_file_replaced_fails_with_tamper_alert(db, tmp_path):
    """
    Verifies that if a physical file exists on disk but has been replaced with altered content,
    verify_evidence_integrity catches the hash mismatch, fails, and generates a tamper alert.
    """
    from audit_engine import verify_evidence_integrity
    from models import Evidence, Alert, CustodyLog

    case = Case(title="Replaced File Test Docket", description="Testing replaced file verification failure")
    db.add(case)
    db.commit()
    db.refresh(case)

    # Create an actual file on disk with known content
    test_file = tmp_path / "tampered_cctv.mp4"
    test_file.write_bytes(b"ALTERED AND COMPROMISED CCTV FRAME BYTES")

    # Create evidence record expecting a different original hash
    ev = Evidence(
        case_id=case.id,
        file_name="tampered_cctv.mp4",
        file_type="video/mp4",
        evidence_type="cctv",
        source="Traffic Cam #4",
        file_hash="0000000000000000000000000000000000000000000000000000000000000000",
        storage_path=str(test_file),
        quality_rating=4.5,
        hash_verified=True
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    res = verify_evidence_integrity(
        db=db,
        evidence_id=ev.id,
        user_name="Forensic Inspector Rao",
        user_id=1
    )

    # 1. Assert mismatch failure
    assert res["success"] is False
    assert res["integrity_verified"] is False
    assert res["is_match"] is False
    assert res["status"] == "TAMPER_WARNING"
    assert res["recomputed_hash"] is not None
    assert res["recomputed_hash"] != ev.file_hash

    # 2. Assert DB updated
    db.refresh(ev)
    assert ev.hash_verified is False
    assert ev.quality_rating <= 1.0

    # 3. Assert tamper alert generated
    alert = db.query(Alert).filter(
        Alert.case_id == case.id,
        Alert.linked_item_id == str(ev.id),
        Alert.rule_type == "integrity_failure"
    ).first()
    assert alert is not None
    assert alert.severity == "critical"
    assert "differs from original intake fingerprint" in alert.message

