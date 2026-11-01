# backend/routers/sync.py
"""
Evidentia-AI Station Offline Sync Router
Provides idempotent bulk ingestion of offline outbox operations,
delta change feeds, and full case offline bundles.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from database import get_db
from models import (
    User, Case, CasePerson, InvestigationTask, CaseDeadline, 
    Evidence, Alert, SyncIdempotencyRecord, CollaborationEvent
)
from schemas import (
    BulkSyncRequest, BulkSyncResponse, OfflineBundleResponse, OutboxSyncItem
)
from auth import get_current_user, check_case_access
from routers.common import resolve_case_id

router = APIRouter(tags=["Station Offline & Sync"])

# Offline Permissions Matrix
ALLOWED_OFFLINE_ACTIONS = {
    "field_capture",
    "draft_diary",
    "create_note",
    "create_task",
    "statement_draft",
    "malkhana_scan"
}

BLOCKED_OFFLINE_ACTIONS = {
    "delete_case",
    "delete_evidence",
    "chargesheet_signoff",
    "verdict_commit",
    "user_permission_change"
}


@router.post("/cases/{case_id}/sync", response_model=BulkSyncResponse)
def sync_outbox_operations(
    case_id: str,
    req: BulkSyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ingests queued offline operations.
    Guarantees idempotency via unique client keys; prevents duplicate execution.
    Enforces offline permissions policy.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "edit"):
        raise HTTPException(status_code=403, detail="Access denied.")

    server_time = datetime.now(timezone.utc)
    applied_keys = []
    skipped_duplicates = 0
    errors = []

    for item in req.operations:
        # 1. Deduplication check via Idempotency Key
        existing = db.query(SyncIdempotencyRecord).filter(
            SyncIdempotencyRecord.idempotency_key == item.idempotency_key
        ).first()

        if existing:
            skipped_duplicates += 1
            continue

        # 2. Permissions validation
        if item.action in BLOCKED_OFFLINE_ACTIONS:
            errors.append({
                "idempotency_key": item.idempotency_key,
                "error": f"Action '{item.action}' is strictly prohibited offline. Requires live server authorization."
            })
            continue

        if item.action not in ALLOWED_OFFLINE_ACTIONS:
            errors.append({
                "idempotency_key": item.idempotency_key,
                "error": f"Unknown offline action '{item.action}'."
            })
            continue

        # 3. Apply operation
        try:
            summary = ""
            payload = item.payload or {}

            if item.action == "create_task":
                title = payload.get("title", "Offline Task")
                task = InvestigationTask(
                    case_id=real_case_id,
                    title=f"[Offline] {title}",
                    description=payload.get("description", f"Captured on mobile device at {item.device_timestamp}"),
                    status="pending",
                    category=payload.get("category", "Field Inquiry"),
                    created_at=item.device_timestamp
                )
                db.add(task)
                summary = f"Created task '{title}'"

            elif item.action in ["create_note", "draft_diary"]:
                note_text = payload.get("note", payload.get("text", ""))
                event = CollaborationEvent(
                    case_id=real_case_id,
                    item_type="diary_draft",
                    item_id=0,
                    version=1,
                    user_id=current_user.id,
                    user_name=current_user.full_name,
                    summary=f"[Offline Diary Note] Device Time: {item.device_timestamp}",
                    payload=note_text
                )
                db.add(event)
                summary = "Recorded offline diary entry"

            elif item.action == "field_capture":
                title = payload.get("title", "Offline Field Photo")
                ev = Evidence(
                    case_id=real_case_id,
                    title=f"[Field Capture] {title}",
                    description=f"Device GPS: {payload.get('gps', 'Scene')}, Time: {item.device_timestamp}",
                    category="Digital Image",
                    file_name=payload.get("file_name", "offline_capture.jpg"),
                    file_path=payload.get("file_path", "uploads/offline_capture.jpg"),
                    file_hash=payload.get("hash", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
                    is_processed=True,
                    collected_date=item.device_timestamp
                )
                db.add(ev)
                summary = f"Recorded offline evidence exhibit '{title}'"

            # Record Idempotency
            sync_rec = SyncIdempotencyRecord(
                idempotency_key=item.idempotency_key,
                case_id=real_case_id,
                action=item.action,
                endpoint=item.endpoint,
                status="applied",
                device_timestamp=item.device_timestamp,
                server_receipt_timestamp=server_time,
                result_summary=summary
            )
            db.add(sync_rec)
            db.commit()
            applied_keys.append(item.idempotency_key)

        except Exception as e:
            db.rollback()
            errors.append({
                "idempotency_key": item.idempotency_key,
                "error": str(e)
            })

    return BulkSyncResponse(
        applied_count=len(applied_keys),
        skipped_duplicates_count=skipped_duplicates,
        failed_count=len(errors),
        applied_keys=applied_keys,
        errors=errors,
        server_timestamp=server_time
    )


@router.get("/cases/{case_id}/changes")
def get_case_delta_changes(
    case_id: str,
    since: Optional[datetime] = Query(None, description="Fetch changes modified strictly after this UTC timestamp"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns delta change feed for offline sync since given timestamp.
    Minimizes mobile bandwidth usage.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied.")

    task_q = db.query(InvestigationTask).filter(InvestigationTask.case_id == real_case_id)
    deadline_q = db.query(CaseDeadline).filter(CaseDeadline.case_id == real_case_id)
    evidence_q = db.query(Evidence).filter(Evidence.case_id == real_case_id)

    if since:
        task_q = task_q.filter(InvestigationTask.created_at >= since)
        deadline_q = deadline_q.filter(CaseDeadline.created_at >= since)
        evidence_q = evidence_q.filter(Evidence.uploaded_at >= since)

    tasks = task_q.all()
    deadlines = deadline_q.all()
    exhibits = evidence_q.all()

    return {
        "case_id": real_case_id,
        "since": since,
        "server_timestamp": datetime.now(timezone.utc),
        "changes": {
            "tasks_count": len(tasks),
            "tasks": [{"id": t.id, "title": t.title, "status": t.status} for t in tasks],
            "deadlines_count": len(deadlines),
            "deadlines": [{"id": d.id, "due_date": d.due_date, "status": d.status} for d in deadlines],
            "exhibits_count": len(exhibits),
            "exhibits": [{"id": e.id, "title": e.title} for e in exhibits]
        }
    }


@router.get("/cases/{case_id}/offline-bundle", response_model=OfflineBundleResponse)
def get_case_offline_bundle(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Downloads complete structured case bundle for full offline execution on patrol devices.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied.")

    case = db.query(Case).filter(Case.id == real_case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    persons = db.query(CasePerson).filter(CasePerson.case_id == real_case_id).all()
    tasks = db.query(InvestigationTask).filter(InvestigationTask.case_id == real_case_id).all()
    deadlines = db.query(CaseDeadline).filter(CaseDeadline.case_id == real_case_id).all()
    evidence = db.query(Evidence).filter(Evidence.case_id == real_case_id).all()
    alerts = db.query(Alert).filter(Alert.case_id == real_case_id).all()

    return OfflineBundleResponse(
        id=case.id,
        case_number=getattr(case, "crime_number", None) or getattr(case, "fir_number", None) or f"CR-{case.id}/2009",
        title=case.title or "Case Investigation",
        police_station=getattr(case, "police_station", "Yerwada Police Station"),
        investigating_officer=getattr(case, "investigating_officer_name", "Inspector S. Patil"),
        incident_date=str(case.incident_date) if getattr(case, "incident_date", None) else None,
        particulars={
            "fir_number": getattr(case, "fir_number", None),
            "offence_section": getattr(case, "offence_section", None),
            "bail_status": getattr(case, "bail_status", None),
            "stage": getattr(case, "case_stage", "under_investigation")
        },
        people=[{
            "id": p.id,
            "name": p.name,
            "role": p.role,
            "father_name": p.father_or_spouse_name,
            "phone": p.contact_info,
            "address": p.address
        } for p in persons],
        tasks=[{
            "id": t.id,
            "title": t.title,
            "status": t.status,
            "category": getattr(t, "category", "general")
        } for t in tasks],
        deadlines=[{
            "id": d.id,
            "due_date": str(d.due_date),
            "status": d.status
        } for d in deadlines],
        diary_entries=[],
        exhibits=[{
            "id": e.id,
            "title": e.title,
            "category": e.category,
            "file_name": e.file_name,
            "file_hash": e.file_hash
        } for e in evidence],
        hypotheses=[],
        alerts=[{
            "id": a.id,
            "title": a.title,
            "severity": a.severity,
            "status": a.status
        } for a in alerts],
        downloaded_at=datetime.now(timezone.utc),
        is_pinned=True
    )

