"""
backend/tests/test_security_upgrades.py
=======================================
Integration tests for Security Upgrades:
1. Private Model & Air-Gap Switch (blocking external AI calls for sensitive cases)
2. Two-Factor Authentication (TOTP + Backup Codes)
3. Shorter Sessions & Active Session List / Revocation
4. Field-Level AES-GCM Encryption & Role-Based Access Restrictions
5. Statutory Retention, Legal Hold Enforcement & Automated Restore Testing
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import pyotp

from app import app
from models import (
    Case, User, CaseMember, PriorRecord, SuspectProfileFactor,
    SystemSecurityConfig, BackupRecord, UserSession, Hypothesis
)
from auth import (
    hash_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
)
from security_encryption import encrypt_field, decrypt_field, CIPHERTEXT_PREFIX
from totp_security import (
    generate_totp_secret, verify_totp_code,
    generate_backup_codes, verify_and_consume_backup_code
)
from ai_dispatch_engine import (
    check_airgap_status, dispatch_ai_completion,
    AirGapSecurityViolationError
)
from backup_engine import (
    create_backup, run_sandbox_restore_test, set_case_legal_hold
)


@pytest.fixture
def test_setup(db: Session):
    """Sets up a test case, admin, and analyst."""
    admin = db.query(User).filter(User.email == "sec_admin@evidentia.test").first()
    if not admin:
        admin = User(
            email="sec_admin@evidentia.test",
            full_name="Captain Admin",
            hashed_password=hash_password("AdminSecurePass123!"),
            role="admin",
            is_active=True,
            session_duration_minutes=15
        )
        db.add(admin)

    analyst = db.query(User).filter(User.email == "sec_analyst@evidentia.test").first()
    if not analyst:
        analyst = User(
            email="sec_analyst@evidentia.test",
            full_name="Junior Analyst",
            hashed_password=hash_password("AnalystPass123!"),
            role="analyst",
            is_active=True,
            session_duration_minutes=15
        )
        db.add(analyst)

    test_case = db.query(Case).filter(Case.title == "Operation Iron Vault").first()
    if not test_case:
        test_case = Case(
            title="Operation Iron Vault",
            description="High-security sensitive financial conspiracy case",
            status="Active",
            created_by="Captain Admin",
            is_sensitive_airgapped=False,
            retention_period_years=25
        )
        db.add(test_case)
        db.flush()

    # Assign analyst to case
    member = db.query(CaseMember).filter(CaseMember.case_id == test_case.id, CaseMember.user_id == analyst.id).first()
    if not member:
        db.add(CaseMember(case_id=test_case.id, user_id=analyst.id, case_role="analyst", added_by="Test Setup"))

    db.commit()
    db.refresh(admin)
    db.refresh(analyst)
    db.refresh(test_case)

    admin_token = create_access_token({"sub": str(admin.id), "email": admin.email, "role": admin.role})
    analyst_token = create_access_token({"sub": str(analyst.id), "email": analyst.email, "role": analyst.role})

    return {
        "admin": admin,
        "analyst": analyst,
        "case": test_case,
        "admin_token": admin_token,
        "analyst_token": analyst_token
    }


def test_private_model_and_airgap_switch(db: Session, client: TestClient, test_setup):
    """
    Validates that:
    1. A sensitive case toggles air-gap mode.
    2. Cloud AI calls are strictly blocked when air-gapped.
    3. Requests route to the local model endpoint instead of cloud.
    """
    c = test_setup["case"]
    admin_tok = test_setup["admin_token"]

    # Initially standard mode
    is_airgapped, reason, _ = check_airgap_status(c.id, db)
    assert not is_airgapped

    # 1. Engage air-gap via API
    res = client.post(
        f"/cases/{c.id}/airgap-toggle",
        headers={"Authorization": f"Bearer {admin_tok}"},
        json={
            "is_sensitive_airgapped": True,
            "ai_provider_override": "local_ollama",
            "local_ai_endpoint": "http://localhost:11434/v1",
            "local_ai_model": "mistral"
        }
    )
    assert res.status_code == 200
    assert res.json()["is_sensitive_airgapped"] is True

    # Check status
    is_airgapped, reason, eff_cfg = check_airgap_status(c.id, db)
    assert is_airgapped is True
    assert "Sensitive / Air-Gapped" in reason
    assert eff_cfg["default_ai_provider"] == "local_ollama"

    # 2. Assert cloud calls are blocked with AirGapSecurityViolationError
    with pytest.raises(AirGapSecurityViolationError):
        dispatch_ai_completion(
            prompt="Summarize evidence",
            case_id=c.id,
            db=db,
            requested_provider="cloud_gemini"
        )

    # 3. Local model dispatch executes safely without external egress
    local_res = dispatch_ai_completion(
        prompt="Analyze local exhibit",
        case_id=c.id,
        db=db
    )
    assert local_res["provider"] == "local_ollama"
    assert local_res["endpoint"].startswith("http://localhost:11434")


def test_two_factor_authentication_and_backup_codes(db: Session, client: TestClient, test_setup):
    """
    Validates:
    1. TOTP secret generation & standard URI generation.
    2. TOTP verification with code.
    3. Hashed single-use backup recovery codes.
    4. 2FA challenge login flow.
    """
    admin = test_setup["admin"]

    # 1. Setup 2FA
    setup_res = client.post(
        "/auth/2fa/setup",
        headers={"Authorization": f"Bearer {test_setup['admin_token']}"}
    )
    assert setup_res.status_code == 200
    data = setup_res.json()
    secret = data["secret"]
    backup_codes = data["backup_codes"]
    assert len(backup_codes) == 8
    assert "otpauth://" in data["otpauth_uri"]

    # 2. Verify and enable with valid code
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()

    enable_res = client.post(
        "/auth/2fa/verify-and-enable",
        headers={"Authorization": f"Bearer {test_setup['admin_token']}"},
        json={"code": valid_code, "secret": secret}
    )
    assert enable_res.status_code == 200
    assert enable_res.json()["status"] == "success"

    # Check DB: is_2fa_enabled True, secret encrypted at rest
    db.refresh(admin)
    assert admin.is_2fa_enabled is True
    assert admin.totp_secret.startswith(CIPHERTEXT_PREFIX)

    # 3. Login attempt requires 2FA intermediate challenge
    login_res = client.post(
        "/auth/login",
        json={"email": admin.email, "password": "AdminSecurePass123!"}
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["requires_2fa"] is True
    temp_token = login_data["temp_token"]
    assert temp_token is not None

    # 4. Challenge with valid TOTP code delivers final access token
    challenge_res = client.post(
        "/auth/2fa/challenge",
        json={"temp_token": temp_token, "code": totp.now()}
    )
    assert challenge_res.status_code == 200
    assert challenge_res.json()["access_token"] != ""
    assert challenge_res.json()["requires_2fa"] is False

    # 5. Backup code consumption: use one backup code to login
    login_res2 = client.post(
        "/auth/login",
        json={"email": admin.email, "password": "AdminSecurePass123!"}
    )
    temp_token2 = login_res2.json()["temp_token"]
    first_backup_code = backup_codes[0]

    backup_challenge_res = client.post(
        "/auth/2fa/challenge",
        json={"temp_token": temp_token2, "code": first_backup_code}
    )
    assert backup_challenge_res.status_code == 200

    # Clean up 2FA for subsequent tests
    admin.is_2fa_enabled = False
    admin.totp_secret = None
    admin.backup_codes = None
    db.commit()


def test_shorter_sessions_and_revocation(db: Session, client: TestClient, test_setup):
    """
    Validates:
    1. Access tokens enforce high-security 15-minute expiration default.
    2. Active sessions are tracked in user_sessions table.
    3. Remote revocation of a session denies further access.
    """
    admin = test_setup["admin"]
    admin.is_2fa_enabled = False
    db.commit()

    # Login to generate an active session
    login_res = client.post(
        "/auth/login",
        json={"email": admin.email, "password": "AdminSecurePass123!"}
    )
    token = login_res.json()["access_token"]
    assert login_res.json()["expires_in_minutes"] == 15

    # List active sessions
    sess_res = client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert sess_res.status_code == 200
    sessions = sess_res.json()
    assert len(sessions) >= 1
    target_session = sessions[0]
    assert target_session["is_current"] is True

    # Revoke session
    revoke_res = client.delete(
        f"/auth/sessions/{target_session['id']}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert revoke_res.status_code == 200

    # Subsequent request using that token must be rejected with 401
    verify_blocked = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert verify_blocked.status_code == 401
    assert "revoked" in verify_blocked.json()["detail"].lower()


def test_field_level_encryption_and_role_restrictions(db: Session, client: TestClient, test_setup):
    """
    Validates:
    1. PriorRecord and SuspectProfileFactor fields are AES-GCM encrypted in the database.
    2. Database raw columns contain ciphertext with 'ENC_v1:' prefix.
    3. Decrypted automatically for Admin and Lead Investigator.
    4. Masked / restricted for Analyst and Reviewer under Section 54 IEA.
    """
    c = test_setup["case"]
    admin_tok = test_setup["admin_token"]
    analyst_tok = test_setup["analyst_token"]

    # 1. Create encrypted PriorRecord
    plain_name = "Vijay Raut"
    plain_mo = "Targeted rear entrance using hydraulic cutters between 02:00 and 03:00"
    plain_doc = "SCRB Dossier #SCRB-MH-2024-889"

    create_res = client.post(
        f"/cases/{c.id}/prior-records",
        headers={"Authorization": f"Bearer {admin_tok}"},
        json={
            "suspect_name": plain_name,
            "offense_type": "commercial_burglary",
            "legal_section": "BNS 305",
            "outcome": "convicted",
            "mo_description": plain_mo,
            "source_agency": "SCRB Maharashtra",
            "source_document": plain_doc
        }
    )
    assert create_res.status_code == 200
    record_id = create_res.json()["id"]

    # 2. Check raw database record at rest: must be ciphertext
    raw_db_rec = db.query(PriorRecord).filter(PriorRecord.id == record_id).first()
    assert raw_db_rec.suspect_name.startswith(CIPHERTEXT_PREFIX)
    assert raw_db_rec.mo_description.startswith(CIPHERTEXT_PREFIX)
    assert raw_db_rec.source_document.startswith(CIPHERTEXT_PREFIX)
    assert plain_name not in raw_db_rec.suspect_name
    assert "hydraulic" not in raw_db_rec.mo_description

    # 3. Query as Admin: fields decrypted transparently
    admin_view = client.get(
        f"/cases/{c.id}/prior-records",
        headers={"Authorization": f"Bearer {admin_tok}"}
    )
    assert admin_view.status_code == 200
    records = admin_view.json()["records"]
    assert any(r["suspect_name"] == plain_name for r in records)
    assert any(plain_mo in r["mo_description"] for r in records)

    # 4. Query as Analyst: Section 54 IEA restriction active (records masked/partitioned)
    analyst_view = client.get(
        f"/cases/{c.id}/prior-records",
        headers={"Authorization": f"Bearer {analyst_tok}"}
    )
    assert analyst_view.status_code == 200
    assert analyst_view.json()["is_role_restricted"] is True
    assert analyst_view.json()["records"] == []
    assert "Section 54" in analyst_view.json()["restricted_message"]


def test_retention_legal_hold_and_restore_testing(db: Session, client: TestClient, test_setup):
    """
    Validates:
    1. Retention settings and Legal Hold placement.
    2. Deletion of case or evidence is strictly locked (HTTP 423) when Legal Hold is active.
    3. Automated database backup executes sandbox restore test (PRAGMA integrity_check).
    """
    c = test_setup["case"]
    admin_tok = test_setup["admin_token"]

    # 1. Place Legal Hold
    hold_res = client.post(
        f"/cases/{c.id}/legal-hold",
        headers={"Authorization": f"Bearer {admin_tok}"},
        json={
            "is_legal_hold": True,
            "reason": "High Court writ petition preservation order #WP-2026-4011"
        }
    )
    assert hold_res.status_code == 200
    assert hold_res.json()["is_legal_hold"] is True

    # 2. Attempt case deletion: MUST be locked with HTTP 423
    del_res = client.delete(
        f"/cases/{c.id}",
        headers={"Authorization": f"Bearer {admin_tok}"}
    )
    assert del_res.status_code == 423
    assert "Legal Hold" in del_res.json()["detail"]

    # 3. Release Legal Hold
    release_res = client.post(
        f"/cases/{c.id}/legal-hold",
        headers={"Authorization": f"Bearer {admin_tok}"},
        json={"is_legal_hold": False}
    )
    assert release_res.status_code == 200
    assert release_res.json()["is_legal_hold"] is False

    # 4. Create Automated Backup with Sandbox Restore Test
    backup_res = client.post(
        "/admin/backups/create",
        headers={"Authorization": f"Bearer {admin_tok}"}
    )
    assert backup_res.status_code == 200
    backup_data = backup_res.json()
    assert backup_data["restore_test_status"] == "passed"
    assert len(backup_data["sha256_hash"]) == 64
    assert "PRAGMA integrity_check OK" in backup_data["restore_test_notes"]

    # 5. Re-verify restore test on demand
    verify_res = client.post(
        f"/admin/backups/{backup_data['id']}/verify-restore",
        headers={"Authorization": f"Bearer {admin_tok}"}
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["restore_status"] == "passed"
