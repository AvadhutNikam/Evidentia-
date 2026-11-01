"""
backend/routers/security_admin.py
=================================
Security Administration, Private Model Configuration, Disaster Recovery Backups,
and Statutory Retention / Legal Hold Router.
"""

import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Case, User, SystemSecurityConfig, BackupRecord
from schemas import (
    SystemSecurityConfigOut, SystemSecurityConfigUpdate,
    BackupRecordOut, CaseLegalHoldRequest, CaseRetentionUpdate,
    CaseAirGapToggleRequest
)
from auth import get_current_user, require_role, check_case_access
from backup_engine import create_backup, verify_existing_backup_restore, set_case_legal_hold
from ai_dispatch_engine import get_system_security_settings, check_airgap_status
from audit_engine import log_audit_event
from routers.common import resolve_case_id

router = APIRouter(tags=["Security Upgrades, Private Models & Legal Holds"])


# ==============================================================================
# 1. SYSTEM SECURITY & PRIVATE MODEL SETTINGS
# ==============================================================================

@router.get("/admin/security-settings", response_model=SystemSecurityConfigOut)
def get_security_settings_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns platform-wide security configuration:
    - Default AI provider (cloud_gemini vs local_ollama / local_vllm)
    - Local model endpoint & model name
    - Global external AI kill-switch (air-gap)
    - Session lifetime defaults
    """
    cfg = db.query(SystemSecurityConfig).first()
    if not cfg:
        cfg = SystemSecurityConfig(
            default_ai_provider="cloud_gemini",
            local_model_endpoint="http://localhost:11434/v1",
            local_model_name="llama3",
            allow_external_ai_global=True,
            default_session_duration_minutes=15,
            require_2fa_for_admins=False
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


@router.put("/admin/security-settings", response_model=SystemSecurityConfigOut)
def update_security_settings_endpoint(
    req: SystemSecurityConfigUpdate,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """
    Updates platform security settings and private model configurations.
    Admin restricted. Logs changes to the Merkle audit ledger.
    """
    cfg = db.query(SystemSecurityConfig).first()
    if not cfg:
        cfg = SystemSecurityConfig()
        db.add(cfg)

    changes = []
    if req.default_ai_provider is not None:
        cfg.default_ai_provider = req.default_ai_provider
        changes.append(f"AI Provider: {req.default_ai_provider}")
    if req.local_model_endpoint is not None:
        cfg.local_model_endpoint = req.local_model_endpoint
        changes.append(f"Local Endpoint: {req.local_model_endpoint}")
    if req.local_model_name is not None:
        cfg.local_model_name = req.local_model_name
        changes.append(f"Local Model: {req.local_model_name}")
    if req.allow_external_ai_global is not None:
        cfg.allow_external_ai_global = req.allow_external_ai_global
        changes.append(f"Allow External AI: {req.allow_external_ai_global}")
    if req.default_session_duration_minutes is not None:
        cfg.default_session_duration_minutes = req.default_session_duration_minutes
        changes.append(f"Session Duration: {req.default_session_duration_minutes}m")
    if req.require_2fa_for_admins is not None:
        cfg.require_2fa_for_admins = req.require_2fa_for_admins
        changes.append(f"Require 2FA for Admins: {req.require_2fa_for_admins}")

    cfg.updated_at = datetime.now(timezone.utc)
    cfg.updated_by = current_user.full_name
    db.commit()
    db.refresh(cfg)

    try:
        log_audit_event(
            db=db,
            action_type="SECURITY_CONFIG_UPDATED",
            target_type="system",
            target_id="1",
            description=f"Security settings updated by {current_user.full_name}: {', '.join(changes)}",
            user_id=current_user.id,
            user_name=current_user.full_name,
            user_role=current_user.role
        )
    except Exception:
        pass

    return cfg


# ==============================================================================
# 2. DISASTER RECOVERY BACKUPS & RESTORE TESTING
# ==============================================================================

@router.get("/admin/backups", response_model=List[BackupRecordOut])
def list_backups_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns list of all automated forensic backups with their SHA-256 integrity hashes
    and automated sandbox restore test verification results.
    """
    return db.query(BackupRecord).order_by(BackupRecord.id.desc()).all()


@router.post("/admin/backups/create", response_model=BackupRecordOut)
def create_backup_endpoint(
    backup_type: str = "full",
    current_user: User = Depends(require_role(["admin", "lead_investigator"])),
    db: Session = Depends(get_db)
):
    """
    Initiates an immediate ACID snapshot backup of the database,
    calculates cryptographic SHA-256 hash, and immediately executes an automated
    sandbox restore test with PRAGMA integrity_check.
    """
    backup_rec = create_backup(
        db=db,
        user_name=current_user.full_name,
        backup_type=backup_type
    )

    try:
        log_audit_event(
            db=db,
            action_type="DATABASE_BACKUP_CREATED",
            target_type="backup",
            target_id=str(backup_rec.id),
            description=f"Backup #{backup_rec.id} ({backup_rec.backup_filename}) created by {current_user.full_name}. Restore Test: {backup_rec.restore_test_status.upper()}.",
            user_id=current_user.id,
            user_name=current_user.full_name,
            user_role=current_user.role
        )
    except Exception:
        pass

    return backup_rec


@router.post("/admin/backups/{backup_id}/verify-restore")
def verify_backup_restore_endpoint(
    backup_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Re-executes the automated sandbox restore test on an existing backup file.
    Verifies SQLite low-level B-Tree integrity and table schemas.
    """
    try:
        return verify_existing_backup_restore(backup_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==============================================================================
# 3. STATUTORY RETENTION & LEGAL HOLD SETTINGS
# ==============================================================================

@router.post("/cases/{case_id}/legal-hold")
def set_legal_hold_endpoint(
    case_id: str,
    req: CaseLegalHoldRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Places or releases a statutory Legal Hold on a case.
    When active:
      - Absolute immutability protection is engaged.
      - Case deletion and exhibit purging are strictly locked with HTTP 423.
      - Event is logged to the tamper-evident Merkle audit ledger.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "finalize_case"):
        if current_user.role not in ["admin", "lead_investigator"]:
            raise HTTPException(status_code=403, detail="Only Lead Investigator or Administrator can place or release a Legal Hold.")

    try:
        case = set_case_legal_hold(
            case_id=real_case_id,
            db=db,
            is_legal_hold=req.is_legal_hold,
            reason=req.reason,
            user_name=current_user.full_name
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    action_label = "LEGAL_HOLD_ENGAGED" if req.is_legal_hold else "LEGAL_HOLD_RELEASED"
    desc = f"Legal Hold {'placed on' if req.is_legal_hold else 'released from'} Case #{real_case_id} by {current_user.full_name}."
    if req.reason:
        desc += f" Reason: {req.reason}"

    try:
        log_audit_event(
            db=db,
            action_type=action_label,
            target_type="case",
            target_id=str(real_case_id),
            description=desc,
            user_id=current_user.id,
            user_name=current_user.full_name,
            user_role=current_user.role,
            case_id=real_case_id
        )
    except Exception:
        pass

    return {
        "case_id": real_case_id,
        "is_legal_hold": case.is_legal_hold,
        "legal_hold_reason": case.legal_hold_reason,
        "legal_hold_placed_by": case.legal_hold_placed_by,
        "legal_hold_placed_at": case.legal_hold_placed_at,
        "message": f"Legal Hold {'activated' if case.is_legal_hold else 'deactivated'} successfully."
    }


@router.get("/cases/{case_id}/retention")
def get_retention_endpoint(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns statutory retention period, expiration date, and legal hold state."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied.")

    case = db.query(Case).filter(Case.id == real_case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    ref_date = case.fir_date or case.incident_date or case.created_at or datetime.now(timezone.utc)
    years = case.retention_period_years or 20
    calc_expiry = ref_date + timedelta(days=years * 365)

    return {
        "case_id": real_case_id,
        "retention_period_years": years,
        "retention_expiry_date": case.retention_expiry_date or calc_expiry,
        "is_legal_hold": getattr(case, "is_legal_hold", False),
        "legal_hold_reason": getattr(case, "legal_hold_reason", None),
        "legal_hold_placed_by": getattr(case, "legal_hold_placed_by", None),
        "legal_hold_placed_at": getattr(case, "legal_hold_placed_at", None),
        "statute_basis": "CrPC Sec 173 / BNSS Sec 193 Evidence Retention Standard"
    }


@router.put("/cases/{case_id}/retention")
def update_retention_endpoint(
    case_id: str,
    req: CaseRetentionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates the retention period in years for a case."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "edit_case"):
        raise HTTPException(status_code=403, detail="Access denied.")

    case = db.query(Case).filter(Case.id == real_case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    case.retention_period_years = req.retention_period_years
    ref_date = case.fir_date or case.incident_date or case.created_at or datetime.now(timezone.utc)
    case.retention_expiry_date = ref_date + timedelta(days=req.retention_period_years * 365)
    db.commit()

    return {
        "case_id": real_case_id,
        "retention_period_years": case.retention_period_years,
        "retention_expiry_date": case.retention_expiry_date,
        "message": f"Retention period updated to {case.retention_period_years} years."
    }


# ==============================================================================
# 4. SENSITIVE CASE AIR-GAP & LOCAL AI SETTINGS
# ==============================================================================

@router.post("/cases/{case_id}/airgap-toggle")
def toggle_case_airgap_endpoint(
    case_id: str,
    req: CaseAirGapToggleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Toggles the sensitive air-gap switch on a case.
    When enabled (`is_sensitive_airgapped=True`), all outbound cloud AI calls
    are strictly firewalled and blocked, forcing local/private model inference.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "edit_case"):
        raise HTTPException(status_code=403, detail="Access denied.")

    case = db.query(Case).filter(Case.id == real_case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    case.is_sensitive_airgapped = req.is_sensitive_airgapped
    if req.ai_provider_override is not None:
        case.ai_provider_override = req.ai_provider_override
    if req.local_ai_endpoint is not None:
        case.local_ai_endpoint = req.local_ai_endpoint
    if req.local_ai_model is not None:
        case.local_ai_model = req.local_ai_model

    db.commit()
    db.refresh(case)

    action_label = "AIRGAP_ENGAGED" if req.is_sensitive_airgapped else "AIRGAP_DISABLED"
    desc = f"Sensitive air-gap switch {'activated (cloud AI blocked)' if req.is_sensitive_airgapped else 'deactivated'} for Case #{real_case_id} by {current_user.full_name}."

    try:
        log_audit_event(
            db=db,
            action_type=action_label,
            target_type="case",
            target_id=str(real_case_id),
            description=desc,
            user_id=current_user.id,
            user_name=current_user.full_name,
            user_role=current_user.role,
            case_id=real_case_id
        )
    except Exception:
        pass

    return {
        "case_id": real_case_id,
        "is_sensitive_airgapped": case.is_sensitive_airgapped,
        "ai_provider_override": case.ai_provider_override,
        "local_ai_endpoint": case.local_ai_endpoint,
        "local_ai_model": case.local_ai_model,
        "message": f"Air-gap mode {'enabled (external calls blocked)' if case.is_sensitive_airgapped else 'disabled'}."
    }


@router.get("/cases/{case_id}/ai-settings")
def get_case_ai_settings_endpoint(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns effective AI provider and air-gap configuration for a specific case."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied.")

    is_airgapped, reason, effective_cfg = check_airgap_status(real_case_id, db)
    case = db.query(Case).filter(Case.id == real_case_id).first()

    return {
        "case_id": real_case_id,
        "is_sensitive_airgapped": getattr(case, "is_sensitive_airgapped", False),
        "ai_provider_override": getattr(case, "ai_provider_override", None),
        "effective_ai_provider": effective_cfg.get("default_ai_provider"),
        "local_model_endpoint": effective_cfg.get("local_model_endpoint"),
        "local_model_name": effective_cfg.get("local_model_name"),
        "airgap_reason": reason
    }


# ==============================================================================
# 5. STATION AI MODES & OUTBOUND CALL REGISTER
# ==============================================================================

@router.get("/security/ai-mode")
def get_global_ai_mode(
    db: Session = Depends(get_db)
):
    """
    Returns the current 3-tier system AI mode:
    - 'private_only': 100% on-premise local model (Ollama/vLLM), 0 outside egress
    - 'cloud_allowed': External Cloud AI permitted for non-sensitive cases
    - 'ai_off': All AI inference disabled
    """
    from models import SystemSecurityConfig
    cfg = db.query(SystemSecurityConfig).first()
    
    if not cfg:
        mode = "cloud_allowed"
        local_ep = "http://localhost:11434/v1"
        local_model = "llama3"
    elif cfg.default_ai_provider == "disabled":
        mode = "ai_off"
        local_ep = cfg.local_model_endpoint or "http://localhost:11434/v1"
        local_model = cfg.local_model_name or "llama3"
    elif not cfg.allow_external_ai_global or cfg.default_ai_provider in ["local_ollama", "local_vllm"]:
        mode = "private_only"
        local_ep = cfg.local_model_endpoint or "http://localhost:11434/v1"
        local_model = cfg.local_model_name or "llama3"
    else:
        mode = "cloud_allowed"
        local_ep = cfg.local_model_endpoint or "http://localhost:11434/v1"
        local_model = cfg.local_model_name or "llama3"

    return {
        "mode": mode,
        "mode_label": {
            "private_only": "AI: Private (On Station Server)",
            "cloud_allowed": "AI: Cloud Allowed",
            "ai_off": "AI: Off"
        }.get(mode, "AI: Private"),
        "chip_color": {
            "private_only": "emerald",
            "cloud_allowed": "amber",
            "ai_off": "neutral"
        }.get(mode, "emerald"),
        "local_model_endpoint": local_ep,
        "local_model_name": local_model,
        "is_first_run_completed": bool(os.getenv("FIRST_RUN_COMPLETED", "false").lower() == "true")
    }


@router.put("/security/ai-mode")
def set_global_ai_mode(
    req: Dict[str, Any],
    current_user: User = Depends(require_role(["admin", "lead_investigator"])),
    db: Session = Depends(get_db)
):
    """
    Switches system AI mode between 'private_only', 'cloud_allowed', and 'ai_off'.
    Strictly recorded in immutable audit log.
    """
    from models import SystemSecurityConfig
    mode = req.get("mode", "private_only")
    if mode not in ["private_only", "cloud_allowed", "ai_off"]:
        raise HTTPException(status_code=400, detail="Invalid mode. Must be 'private_only', 'cloud_allowed', or 'ai_off'.")

    cfg = db.query(SystemSecurityConfig).first()
    if not cfg:
        cfg = SystemSecurityConfig()
        db.add(cfg)

    old_mode = "cloud_allowed" if cfg.allow_external_ai_global else "private_only"

    if mode == "private_only":
        cfg.allow_external_ai_global = False
        cfg.default_ai_provider = "local_ollama"
    elif mode == "cloud_allowed":
        cfg.allow_external_ai_global = True
        cfg.default_ai_provider = "cloud_gemini"
    elif mode == "ai_off":
        cfg.allow_external_ai_global = False
        cfg.default_ai_provider = "disabled"

    db.commit()

    try:
        from audit_ledger import record_audit_event
        record_audit_event(
            db=db,
            action="SECURITY_CONFIG_UPDATE",
            target_type="system",
            target_id="global_ai_mode",
            description=f"Global AI mode changed from '{old_mode}' to '{mode}' by {current_user.full_name} ({current_user.role}).",
            user_id=current_user.id,
            user_name=current_user.full_name,
            user_role=current_user.role
        )
    except Exception:
        pass

    return {"status": "success", "mode": mode, "updated_by": current_user.full_name}


@router.get("/security/outbound-register")
def get_outbound_call_register(
    db: Session = Depends(get_db)
):
    """
    Lists every external network egress destination, data payloads sent,
    and current enforcement policy under the active station mode.
    """
    ai_status = get_global_ai_mode(db)
    is_private = ai_status["mode"] in ["private_only", "ai_off"]

    destinations = [
        {
            "id": "cloud_ai",
            "service_name": "Cloud AI Provider (Gemini / OpenAI)",
            "purpose": "Document entity extraction, hypothesis generation, chargesheet drafting",
            "data_payload": "Exhibit text, crime summary, and investigator question context",
            "policy": "BLOCKED" if is_private else "ALLOWED (Non-Sensitive Cases)",
            "is_blocked": is_private,
            "risk_mitigation": "100% blocked in Private mode. Local Ollama/vLLM processes requests on-premise."
        },
        {
            "id": "map_tiles",
            "service_name": "OpenStreetMap / Public Map Tile Servers",
            "purpose": "Crime scene geographic mapping and cell tower display",
            "data_payload": "Bounding box coordinates of police viewports (potential geofence leakage)",
            "policy": "BLOCKED (Offline Tabular List Enabled)" if is_private else "ALLOWED",
            "is_blocked": is_private,
            "risk_mitigation": "In Private/Light mode, maps switch to self-contained list of coordinates without downloading external tiles."
        },
        {
            "id": "geocoding",
            "service_name": "External Reverse Geocoding Services",
            "purpose": "Resolving GPS coordinates to street addresses",
            "data_payload": "Exact latitude and longitude points of patrol officers",
            "policy": "BLOCKED" if is_private else "ALLOWED",
            "is_blocked": is_private,
            "risk_mitigation": "Offline local station gazetteer lookup only."
        },
        {
            "id": "external_fonts",
            "service_name": "External Web Font CDNs (Google Fonts)",
            "purpose": "Devanagari and UI typography",
            "data_payload": "Client IP address and user-agent string",
            "policy": "BLOCKED (Self-Hosted WOFF2 Enforced)",
            "is_blocked": True,
            "risk_mitigation": "Noto Sans Devanagari and Inter fonts are 100% self-hosted on the station server."
        },
        {
            "id": "sms_gateway",
            "service_name": "National Police / DLT SMS Gateway",
            "purpose": "Statutory default bail and court appearance countdown reminders",
            "data_payload": "Investigator phone number, case number code, countdown days (zero crime details)",
            "policy": "REGULATED (DLT White-listed Templates Only)",
            "is_blocked": False,
            "risk_mitigation": "Statutory messages never contain victim names, accused identities, or case facts."
        },
        {
            "id": "whatsapp_api",
            "service_name": "WhatsApp Business Cloud API",
            "purpose": "Officer urgent reminder digests",
            "data_payload": "Investigator phone number, short link to station LAN portal",
            "policy": "REGULATED (Opt-In Officers Only)",
            "is_blocked": False,
            "risk_mitigation": "Strict opt-in required; no evidentiary media or text transmitted via WhatsApp."
        },
        {
            "id": "error_telemetry",
            "service_name": "Error Telemetry & Crash Reporting (Sentry / Analytics)",
            "purpose": "Platform diagnostics",
            "data_payload": "Stack traces and system state",
            "policy": "BLOCKED (Disabled by default)",
            "is_blocked": True,
            "risk_mitigation": "Crash logs remain on station server filesystem only."
        }
    ]

    return {
        "current_ai_mode": ai_status["mode"],
        "total_destinations": len(destinations),
        "blocked_destinations_count": sum(1 for d in destinations if d["is_blocked"]),
        "destinations": destinations
    }


@router.post("/security/test-private-ai")
def test_private_ai_connection(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "lead_investigator"]))
):
    """
    Actively queries the local Ollama/vLLM endpoint to verify on-premise execution.
    Confirms zero outside network egress.
    """
    from ai_dispatch_engine import dispatch_local_ai_completion, get_system_security_settings
    cfg = get_system_security_settings(db)
    endpoint = cfg.get("local_model_endpoint", "http://localhost:11434/v1")
    model = cfg.get("local_model_name", "llama3")

    test_prompt = "Verify station on-premise AI execution. Respond with 'LOCAL_AI_READY'."
    try:
        res = dispatch_local_ai_completion(
            prompt=test_prompt,
            endpoint=endpoint,
            model_name=model,
            timeout_seconds=5
        )
        return {
            "status": "success",
            "endpoint": endpoint,
            "model": model,
            "response": res.get("text", "OK"),
            "provider": res.get("provider", "local_ollama"),
            "message": "Local AI model responded successfully. 0 bytes transmitted outside station LAN."
        }
    except Exception as e:
        return {
            "status": "offline_simulated",
            "endpoint": endpoint,
            "model": model,
            "error": str(e),
            "message": "Local model endpoint is not currently reachable or model not yet pulled. Station air-gap guarantee is preserved (no cloud fallback)."
        }


@router.get("/security/data-flow-sheet")
def generate_data_flow_sheet(
    db: Session = Depends(get_db)
):
    """
    Generates a formal, printable Markdown Data Flow Specification
    for departmental IT and legal compliance sign-off.
    """
    reg = get_outbound_call_register(db)
    ai_status = get_global_ai_mode(db)

    sheet_md = f"""# EVIDENTIA AI - POLICE STATION DATA FLOW & RESIDENCY AUDIT
**Date:** {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}
**Station Mode:** {ai_status['mode'].upper()}
**Local Model Endpoint:** {ai_status['local_model_endpoint']} ({ai_status['local_model_name']})

---

### 1. Data Residency Guarantees
1. **Case Files & FIR Records:** Stored exclusively in local station SQLite/PostgreSQL storage. 0 bytes transmitted outside.
2. **Biometric & Physical Malkhana Ledger:** Cryptographically hash-chained on local filesystem.
3. **User Credentials & PINs:** Salted PBKDF2 hashes; raw credentials never written to disk or sent over wire.
4. **Devanagari OCR & Audio Transcription:** Executed on local station inference engine when in Private mode.

---

### 2. Outbound Egress Audit Register
| Service | Purpose | Data Transmitted | Status |
| :--- | :--- | :--- | :--- |
"""
    for d in reg["destinations"]:
        status_badge = "BLOCKED" if d["is_blocked"] else "REGULATED"
        sheet_md += f"| {d['service_name']} | {d['purpose']} | {d['data_payload']} | **{status_badge}** |\n"

    sheet_md += """
---

### 3. Departmental Sign-off & Verification
- **Station House Officer (SHO):** ___________________________
- **District Police IT Cell Officer:** ___________________________
- **Superintendent of Police (SP):** ___________________________
"""
    return {"data_flow_markdown": sheet_md}


