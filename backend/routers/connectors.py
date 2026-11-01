"""
backend/routers/connectors.py
=============================
Live Data Connectors API: Automated Evidence Ingestion Pipeline.

Supports:
- Watch Folder polling (shared forensic lab / drop directory)
- Email Inbox parsing (tip-off & whistleblower submissions)
- Scheduled API Pull (forensic lab & CMS integrations)
- Webhook Push (real-time automated intake)

Every stream automatically undergoes:
- MIME & payload integrity validation
- SHA-256 fingerprinting & secure persistence
- Merkle-chained custody & audit logging with source system and receipt time
- Background job extraction & citation indexing
- Section 65B Electronic Evidence certificate compliance checking
"""

import json
import secrets
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form
from sqlalchemy.orm import Session

from database import get_db
from models import Case, DataConnector, ConnectorIngestRecord, Evidence, User
from schemas import (
    DataConnectorCreate,
    DataConnectorUpdate,
    DataConnectorOut,
    ConnectorIngestRecordOut,
    ConnectorPollResponse,
    ConnectorSimulateDropRequest
)
from auth import get_current_user, check_case_access
from audit_engine import log_audit_event
from routers.common import resolve_case_id
from connectors.manager import ConnectorManager

router = APIRouter(tags=["Live Data Connectors & Ingestion Streams"])


def _serialize_connector(conn: DataConnector, req: Request = None) -> Dict[str, Any]:
    """Helper to convert DataConnector model into DataConnectorOut dict with webhook URL."""
    base_url = str(req.base_url).rstrip("/") if req else ""
    webhook_url = None
    if conn.webhook_token:
        webhook_url = f"{base_url}/connectors/webhook/{conn.webhook_token}"

    return {
        "id": conn.id,
        "case_id": conn.case_id,
        "name": conn.name,
        "connector_type": conn.connector_type,
        "source_identifier": conn.source_identifier,
        "config_json": conn.config_json or "{}",
        "webhook_token": conn.webhook_token,
        "webhook_url": webhook_url,
        "is_active": conn.is_active,
        "status": conn.status,
        "last_polled_at": conn.last_polled_at,
        "last_ingest_at": conn.last_ingest_at,
        "items_ingested_count": conn.items_ingested_count,
        "error_message": conn.error_message,
        "created_by": conn.created_by,
        "created_at": conn.created_at,
        "updated_at": conn.updated_at
    }


# ==============================================================================
# CASE CONNECTOR MANAGEMENT ENDPOINTS
# ==============================================================================

@router.get("/cases/{case_id}/connectors", response_model=List[DataConnectorOut])
def list_connectors_for_case(
    case_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all configured live data connectors for a given case.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to case connectors."
        )

    conns = (
        db.query(DataConnector)
        .filter(DataConnector.case_id == real_case_id)
        .order_by(DataConnector.id.desc())
        .all()
    )

    return [_serialize_connector(c, request) for c in conns]


@router.post("/cases/{case_id}/connectors", response_model=DataConnectorOut)
def create_connector_for_case(
    case_id: str,
    payload: DataConnectorCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Register a new live evidence connector for an active case.
    Supported types: 'folder_watch', 'email_inbox', 'api_pull', 'webhook'.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "add_evidence"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to register evidence connectors."
        )

    valid_types = {"folder_watch", "email_inbox", "api_pull", "webhook"}
    ctype = payload.connector_type.strip().lower()
    if ctype not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid connector_type '{payload.connector_type}'. Must be one of: {sorted(valid_types)}"
        )

    webhook_tok = secrets.token_urlsafe(32) if ctype == "webhook" else None

    # Validate JSON syntax if provided
    cfg = payload.config_json or "{}"
    try:
        json.loads(cfg)
    except Exception as je:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"config_json must be valid JSON: {str(je)}"
        )

    new_conn = DataConnector(
        case_id=real_case_id,
        name=payload.name.strip(),
        connector_type=ctype,
        source_identifier=payload.source_identifier.strip(),
        config_json=cfg,
        webhook_token=webhook_tok,
        is_active=payload.is_active if payload.is_active is not None else True,
        status="idle",
        items_ingested_count=0,
        created_by=current_user.full_name or current_user.username
    )
    db.add(new_conn)
    db.commit()
    db.refresh(new_conn)

    log_audit_event(
        db=db,
        action_type="CONNECTOR_CREATE",
        target_type="connector",
        target_id=str(new_conn.id),
        description=f"User registered live connector '{new_conn.name}' ({new_conn.connector_type}) for Case #{real_case_id}.",
        user_id=current_user.id,
        user_name=current_user.full_name or current_user.username,
        user_role=current_user.role,
        case_id=real_case_id,
        after_value=new_conn.source_identifier
    )

    return _serialize_connector(new_conn, request)


@router.get("/cases/{case_id}/connectors/{connector_id}", response_model=DataConnectorOut)
def get_connector_detail(
    case_id: str,
    connector_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve details and status for a specific data connector.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    conn = db.query(DataConnector).filter(
        DataConnector.id == connector_id,
        DataConnector.case_id == real_case_id
    ).first()

    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")

    return _serialize_connector(conn, request)


@router.patch("/cases/{case_id}/connectors/{connector_id}", response_model=DataConnectorOut)
def update_connector_config(
    case_id: str,
    connector_id: int,
    payload: DataConnectorUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update connector settings, pause/resume polling, or update config parameters.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "add_evidence"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    conn = db.query(DataConnector).filter(
        DataConnector.id == connector_id,
        DataConnector.case_id == real_case_id
    ).first()

    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")

    if payload.name is not None:
        conn.name = payload.name.strip()
    if payload.source_identifier is not None:
        conn.source_identifier = payload.source_identifier.strip()
    if payload.config_json is not None:
        try:
            json.loads(payload.config_json)
            conn.config_json = payload.config_json
        except Exception as je:
            raise HTTPException(status_code=400, detail=f"Invalid config_json: {je}")
    if payload.is_active is not None:
        conn.is_active = payload.is_active
        if not conn.is_active:
            conn.status = "paused"
        else:
            conn.status = "idle"

    conn.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(conn)

    log_audit_event(
        db=db,
        action_type="CONNECTOR_UPDATE",
        target_type="connector",
        target_id=str(conn.id),
        description=f"User updated connector '{conn.name}'. Active: {conn.is_active}.",
        user_id=current_user.id,
        user_name=current_user.full_name or current_user.username,
        user_role=current_user.role,
        case_id=real_case_id
    )

    return _serialize_connector(conn, request)


@router.delete("/cases/{case_id}/connectors/{connector_id}")
def delete_connector(
    case_id: str,
    connector_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove an automated data connector.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "delete_evidence"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    conn = db.query(DataConnector).filter(
        DataConnector.id == connector_id,
        DataConnector.case_id == real_case_id
    ).first()

    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")

    name = conn.name
    db.delete(conn)
    db.commit()

    log_audit_event(
        db=db,
        action_type="CONNECTOR_DELETE",
        target_type="connector",
        target_id=str(connector_id),
        description=f"Deleted live connector '{name}' from Case #{real_case_id}.",
        user_id=current_user.id,
        user_name=current_user.full_name or current_user.username,
        user_role=current_user.role,
        case_id=real_case_id
    )

    return {"status": "success", "message": f"Connector '{name}' deleted successfully."}


@router.post("/cases/{case_id}/connectors/{connector_id}/poll", response_model=ConnectorPollResponse)
def trigger_connector_poll(
    case_id: str,
    connector_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Triggers an immediate poll pass on the connector.
    Fetches pending items, ingests into evidence docket, logs chain of custody.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "add_evidence"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    conn = db.query(DataConnector).filter(
        DataConnector.id == connector_id,
        DataConnector.case_id == real_case_id
    ).first()

    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")

    result = ConnectorManager.poll_connector(conn.id, db, current_user)
    return result


@router.post("/cases/{case_id}/connectors/{connector_id}/simulate-drop", response_model=ConnectorPollResponse)
def simulate_evidence_drop(
    case_id: str,
    connector_id: int,
    payload: ConnectorSimulateDropRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Simulates an incoming evidence drop into the connector's pipeline.
    Supported samples: 'cdr_export', 'lab_toxicology', 'bank_statement', 'cctv_metadata', 'whistleblower_email'.
    Allows instant end-to-end verification without requiring external network dependencies.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "add_evidence"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    conn = db.query(DataConnector).filter(
        DataConnector.id == connector_id,
        DataConnector.case_id == real_case_id
    ).first()

    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found.")

    result = ConnectorManager.simulate_drop(
        connector_id=conn.id,
        sample_type=payload.sample_type or "cdr_export",
        db=db,
        user=current_user,
        custom_filename=payload.custom_filename,
        custom_content=payload.custom_content
    )
    return result


@router.get("/cases/{case_id}/connectors/{connector_id}/events", response_model=List[ConnectorIngestRecordOut])
def get_connector_ingest_history(
    case_id: str,
    connector_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns cryptographic custody history of all files received via this connector.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    records = (
        db.query(ConnectorIngestRecord)
        .filter(
            ConnectorIngestRecord.connector_id == connector_id,
            ConnectorIngestRecord.case_id == real_case_id
        )
        .order_by(ConnectorIngestRecord.id.desc())
        .limit(100)
        .all()
    )

    return records


# ==============================================================================
# REAL-TIME WEBHOOK INTAKE ENDPOINT (EXTERNAL PUSH)
# ==============================================================================

@router.post("/connectors/webhook/{webhook_token}")
async def receive_webhook_push(
    webhook_token: str,
    request: Request,
    file: Optional[UploadFile] = File(None),
    metadata: Optional[str] = Form(None),
    source_system: Optional[str] = Form(None),
    evidence_type: Optional[str] = Form("document"),
    db: Session = Depends(get_db)
):
    """
    Public webhook receiver endpoint for authorized external pushing systems
    (Forensic lab systems, bank statement drops, dispatch gateways).
    Secured via connector-specific secret webhook_token.
    """
    conn = db.query(DataConnector).filter(
        DataConnector.webhook_token == webhook_token,
        DataConnector.is_active == True
    ).first()

    if not conn:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or deactivated webhook token."
        )

    # Determine payload type
    content_type = request.headers.get("content-type", "")
    raw_bytes: bytes = b""
    filename: str = "webhook_payload.bin"
    meta_dict: Dict[str, Any] = {}

    if metadata:
        try:
            meta_dict = json.loads(metadata)
        except Exception:
            meta_dict = {"raw_metadata": metadata}

    if file is not None:
        raw_bytes = await file.read()
        filename = file.filename or f"webhook_upload_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.bin"
    elif "application/json" in content_type:
        body_json = await request.json()
        import base64
        if "payload_base64" in body_json:
            raw_bytes = base64.b64decode(body_json["payload_base64"])
            filename = body_json.get("filename", f"webhook_data_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.bin")
        elif "content" in body_json:
            raw_bytes = str(body_json["content"]).encode("utf-8")
            filename = body_json.get("filename", f"webhook_text_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.txt")
        else:
            raw_bytes = json.dumps(body_json, indent=2).encode("utf-8")
            filename = f"webhook_event_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        meta_dict.update(body_json.get("metadata", {}))
        evidence_type = body_json.get("evidence_type", evidence_type)
        source_system = body_json.get("source_system", source_system)
    else:
        # Raw body stream
        raw_bytes = await request.body()
        filename = f"webhook_stream_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.bin"

    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Empty payload received.")

    from connectors.webhook import WebhookConnector
    wh_conn = WebhookConnector(conn)

    evidence = wh_conn.process_webhook_push(
        raw_bytes=raw_bytes,
        filename=filename,
        source_system=source_system or f"webhook:{conn.name}",
        metadata=meta_dict,
        evidence_type=evidence_type or "document",
        db=db,
        user=None
    )

    return {
        "status": "success",
        "message": f"Webhook payload successfully ingested into Evidence Docket #{evidence.id}.",
        "evidence_id": evidence.id,
        "file_name": evidence.file_name,
        "file_hash": evidence.file_hash,
        "timestamp_utc": evidence.created_at.isoformat() if evidence.created_at else datetime.now(timezone.utc).isoformat()
    }
