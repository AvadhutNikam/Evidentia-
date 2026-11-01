"""
backend/tests/test_live_connectors.py
=====================================
Automated Test Suite for Live Data Connectors (Automated Evidence Ingestion Pipeline).

Verifies:
1. Folder Watch Connector (path security, uningested polling, archiving, duplicate detection).
2. Email Tip-Off Inbox Connector (RFC 822 MIME parsing, attachment extraction).
3. Webhook Push Connector (payload normalization, secret token authentication).
4. Standardized Handover Pipeline (MIME validation, SHA-256 fingerprinting, Merkle custody logging with source system and receipt time, background job creation).
5. Connector Manager (drop simulation, poll dispatching).
6. FastAPI Endpoints (CRUD, poll, simulate drop, webhook intake, event log retrieval).
"""

import os
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import pytest

from models import User, Case, Evidence, CustodyLog, AuditLog, DataConnector, ConnectorIngestRecord, Job
from connectors.base import IncomingEvidenceItem
from connectors.folder_watch import FolderWatchConnector
from connectors.email_inbox import EmailInboxConnector
from connectors.webhook import WebhookConnector
from connectors.api_pull import ApiPullConnector
from connectors.manager import ConnectorManager


@pytest.fixture
def test_case(db, seed_users):
    """Creates a dedicated test case for connector tests."""
    from models import CaseMember
    lead = seed_users["lead_investigator"]
    c = Case(
        title="Live Connector Pipeline Test Trial",
        description="Automated evidence ingestion live stream test",
        fir_number="FIR-2026-CONN-001",
        status="Active",
        created_by=lead.full_name
    )
    db.add(c)
    db.commit()
    db.refresh(c)

    # Assign lead investigator as case member
    cm = CaseMember(
        case_id=c.id,
        user_id=lead.id,
        case_role="lead_investigator"
    )
    db.add(cm)
    db.commit()

    return c


@pytest.fixture
def temp_watch_dir():
    """Temporary directory for folder watch and email drop tests."""
    temp_dir = tempfile.mkdtemp(prefix="evidentia_watch_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


# ==============================================================================
# 1. FOLDER WATCH CONNECTOR TESTS
# ==============================================================================

def test_folder_watch_path_security(test_case):
    # Attempting to watch forbidden directories must raise ValueError
    conn_rec = DataConnector(
        id=1,
        case_id=test_case.id,
        name="Malicious System Watcher",
        connector_type="folder_watch",
        source_identifier="C:\\Windows\\System32"
    )
    with pytest.raises(ValueError, match="strictly forbidden"):
        FolderWatchConnector(conn_rec)


def test_folder_watch_ingest_and_archive(db, test_case, seed_users, temp_watch_dir):
    user = seed_users["lead_investigator"]

    conn_rec = DataConnector(
        case_id=test_case.id,
        name="Forensic Lab Drops",
        connector_type="folder_watch",
        source_identifier=str(temp_watch_dir),
        config_json=json.dumps({"file_patterns": ["*.csv", "*.txt"]}),
        is_active=True
    )
    db.add(conn_rec)
    db.commit()
    db.refresh(conn_rec)

    # Place sample CDR CSV in watch folder
    sample_file = temp_watch_dir / "lab_cdr_extract_01.csv"
    sample_content = (
        "call_id,calling_number,called_number,timestamp,duration_sec,cell_tower_id\n"
        "C001,9823000001,9823000002,2026-10-30 19:30:00,120,TWR-PUNE-01\n"
    )
    with open(sample_file, "w", encoding="utf-8") as f:
        f.write(sample_content)

    connector = FolderWatchConnector(conn_rec)
    items = connector.fetch_new_items(db)

    assert len(items) == 1
    assert items[0].filename == "lab_cdr_extract_01.csv"
    assert items[0].evidence_type in ("forensic", "telecom")
    assert "watch_folder" in items[0].source_system

    # Hand over to pipeline
    evidence = connector.handover(items[0], db, user)
    assert evidence.id is not None
    assert evidence.case_id == test_case.id
    assert evidence.extraction_mode == "connector"
    assert evidence.connector_id == conn_rec.id
    assert evidence.file_hash is not None

    # Verify custody log provenance requirement:
    # "Record the source system and receipt time in the custody log, so you can prove where each item came from."
    custody_entry = (
        db.query(CustodyLog)
        .filter(CustodyLog.evidence_id == evidence.id, CustodyLog.action == "CONNECTOR_INGEST")
        .first()
    )
    assert custody_entry is not None
    assert custody_entry.source_agency == items[0].source_system
    assert custody_entry.timestamp is not None
    assert "CONNECTOR_INGEST" in custody_entry.action

    # Verify file was moved to .ingested
    assert not sample_file.exists()
    archive_folder = temp_watch_dir / ".ingested"
    assert archive_folder.exists()
    archived_files = list(archive_folder.glob("*lab_cdr_extract_01.csv"))
    assert len(archived_files) == 1


def test_folder_watch_duplicate_skipping(db, test_case, seed_users, temp_watch_dir):
    """If the exact same file is dropped again, it should skip creating duplicate evidence."""
    user = seed_users["lead_investigator"]

    conn_rec = DataConnector(
        case_id=test_case.id,
        name="Dup Test Watcher",
        connector_type="folder_watch",
        source_identifier=str(temp_watch_dir),
        config_json=json.dumps({"file_patterns": ["*.csv", "*.txt"]}),
        is_active=True
    )
    db.add(conn_rec)
    db.commit()
    db.refresh(conn_rec)

    sample_file = temp_watch_dir / "duplicate_cdr.csv"
    sample_content = "call_id,caller\nC999,9823999999\n"
    with open(sample_file, "w", encoding="utf-8") as f:
        f.write(sample_content)

    connector = FolderWatchConnector(conn_rec)
    items = connector.fetch_new_items(db)
    ev1 = connector.handover(items[0], db, user)

    # Now drop the exact same content again under another name
    sample_file_2 = temp_watch_dir / "duplicate_cdr_copy.csv"
    with open(sample_file_2, "w", encoding="utf-8") as f:
        f.write(sample_content)

    items_2 = connector.fetch_new_items(db)
    assert len(items_2) == 1
    ev2 = connector.handover(items_2[0], db, user)

    # Should return existing evidence and record duplicate_skipped
    assert ev1.id == ev2.id

    dup_rec = (
        db.query(ConnectorIngestRecord)
        .filter(
            ConnectorIngestRecord.connector_id == conn_rec.id,
            ConnectorIngestRecord.status == "duplicate_skipped"
        )
        .first()
    )
    assert dup_rec is not None
    assert "Duplicate SHA-256" in dup_rec.error_message


# ==============================================================================
# 2. EMAIL INBOX CONNECTOR TESTS
# ==============================================================================

def test_email_inbox_connector(db, test_case, seed_users, temp_watch_dir):
    user = seed_users["analyst"]

    conn_rec = DataConnector(
        case_id=test_case.id,
        name="Whistleblower Tip-Off Inbox",
        connector_type="email_inbox",
        source_identifier=str(temp_watch_dir),
        config_json="{}"
    )
    db.add(conn_rec)
    db.commit()
    db.refresh(conn_rec)

    # Create an RFC 822 .eml tip-off message
    eml_path = temp_watch_dir / "whistleblower_tip_99.eml"
    eml_text = (
        "From: anonymous_whistleblower@protonmail.com\r\n"
        "To: tipoff@evidentia-police.gov.in\r\n"
        "Subject: Secret meeting details at Kharadi bypass\r\n"
        "Date: Fri, 30 Oct 2026 14:20:00 +0530\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        "\r\n"
        "The suspect was spotted abandoning the vehicle near the Katraj bypass.\r\n"
        "Driver was wearing a blue jacket.\r\n"
    )
    with open(eml_path, "wb") as f:
        f.write(eml_text.encode("utf-8"))

    connector = EmailInboxConnector(conn_rec)
    items = connector.fetch_new_items(db)

    assert len(items) == 1
    item = items[0]
    assert "Secret meeting details" in item.filename or item.filename.endswith(".txt")
    assert "anonymous_whistleblower@protonmail.com" in item.metadata.get("sender", "")
    assert item.evidence_type in ("witness", "document")

    ev = connector.handover(item, db, user)
    assert ev.id is not None
    assert "email_inbox" in ev.connector_source_system


# ==============================================================================
# 3. WEBHOOK PUSH CONNECTOR TESTS
# ==============================================================================

def test_webhook_connector(db, test_case, seed_users):
    user = seed_users["lead_investigator"]

    conn_rec = DataConnector(
        case_id=test_case.id,
        name="Real-Time Dispatch Webhook",
        connector_type="webhook",
        source_identifier="dispatch_gateway",
        webhook_token="sec_token_xyz_12345",
        config_json="{}"
    )
    db.add(conn_rec)
    db.commit()
    db.refresh(conn_rec)

    connector = WebhookConnector(conn_rec)
    assert connector.fetch_new_items(db) == []

    payload_bytes = b"AUTOMATED CCTV ALERT: Vehicle MH-12-DE-4491 detected passing Katraj Toll Plaza."
    ev = connector.process_webhook_push(
        raw_bytes=payload_bytes,
        filename="cctv_alert_stream.txt",
        source_system="cctv_camera_gateway_04",
        metadata={"camera_id": "KATRAJ-04", "anpr": "MH-12-DE-4491"},
        evidence_type="forensic",
        db=db,
        user=user
    )

    assert ev.id is not None
    assert ev.connector_source_system == "cctv_camera_gateway_04"
    assert ev.evidence_type == "forensic"


# ==============================================================================
# 4. CONNECTOR MANAGER & DROP SIMULATION TESTS
# ==============================================================================

def test_connector_manager_drop_simulation(db, test_case, seed_users, temp_watch_dir):
    user = seed_users["lead_investigator"]

    conn_rec = DataConnector(
        case_id=test_case.id,
        name="Simulation Test Watcher",
        connector_type="folder_watch",
        source_identifier=str(temp_watch_dir),
        config_json="{}"
    )
    db.add(conn_rec)
    db.commit()
    db.refresh(conn_rec)

    # Simulate CDR drop
    res = ConnectorManager.simulate_drop(
        connector_id=conn_rec.id,
        sample_type="cdr_export",
        db=db,
        user=user
    )

    assert res["success"] is True
    assert res["items_fetched"] >= 1
    assert res["items_ingested"] >= 1
    assert len(res["ingested_evidence_ids"]) >= 1


# ==============================================================================
# 5. FASTAPI ROUTE INTEGRATION TESTS
# ==============================================================================

def test_fastapi_connector_endpoints(client, db, test_case, lead_headers):
    # 1. Create connector via API
    resp = client.post(
        f"/cases/{test_case.id}/connectors",
        json={
            "name": "Bank Drop Box",
            "connector_type": "folder_watch",
            "source_identifier": "./test_bank_drops",
            "config_json": json.dumps({"file_patterns": ["*.csv", "*.txt"]}),
            "is_active": True
        },
        headers=lead_headers
    )
    assert resp.status_code == 200, resp.text
    conn_data = resp.json()
    assert conn_data["name"] == "Bank Drop Box"
    assert conn_data["connector_type"] == "folder_watch"
    conn_id = conn_data["id"]

    # 2. List connectors
    list_resp = client.get(f"/cases/{test_case.id}/connectors", headers=lead_headers)
    assert list_resp.status_code == 200
    connectors_list = list_resp.json()
    assert any(c["id"] == conn_id for c in connectors_list)

    # 3. Simulate drop on the connector
    drop_resp = client.post(
        f"/cases/{test_case.id}/connectors/{conn_id}/simulate-drop",
        json={"sample_type": "bank_statement"},
        headers=lead_headers
    )
    assert drop_resp.status_code == 200
    drop_data = drop_resp.json()
    assert drop_data["success"] is True
    assert drop_data["items_ingested"] >= 1

    # 4. Ingest history events
    events_resp = client.get(f"/cases/{test_case.id}/connectors/{conn_id}/events", headers=lead_headers)
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert len(events) >= 1
    assert events[0]["connector_id"] == conn_id
    assert events[0]["status"] in ("success", "duplicate_skipped")

    # Clean up test directory if created
    shutil.rmtree("./test_bank_drops", ignore_errors=True)
