"""
backend/routers/priorities.py
=============================
Router for the "What do I do today?" screen and global statutory deadlines.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Case, User, ReportRequest, PersonRegister, StatementTracker, Evidence
)
from schemas import (
    PrioritiesResponseOut, ReportRequestCreate, ReportRequestOut, ReportRequestUpdate,
    PersonRegisterCreate, PersonRegisterOut, StatementTrackerCreate, StatementTrackerOut, StatementTrackerUpdate
)
from auth import get_current_user, check_case_access
from routers.common import resolve_case_id
from priorities_engine import (
    compute_case_priorities, get_global_cases_by_deadline, invalidate_priorities_cache
)
from collaboration import publish_collaboration_event

router = APIRouter(tags=["Priorities & Operational Readiness"])


@router.get("/cases/{case_id}/priorities", response_model=PrioritiesResponseOut)
def get_case_priorities_endpoint(
    case_id: str,
    skip_cache: bool = Query(False, description="Bypass in-memory cache to force recalculation"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns unified 'What do I do today?' priorities payload:
    - Statutory 60/90 days chargesheet & remand countdowns
    - Pending FSL/CDR/Bank report requests
    - Witnesses not yet examined and statements tracker
    - Needs-your-review items and open alerts
    - 'Since you were away' shift briefing
    """
    real_id = resolve_case_id(case_id, db)
    try:
        data = compute_case_priorities(real_id, current_user, db, skip_cache=skip_cache)
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to gather case priorities: {str(e)}")


@router.get("/priorities", response_model=List[Dict[str, Any]])
def get_global_priorities_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Global priority list across all cases accessible to user for the home dashboard.
    Ranks cases by nearest statutory deadline and critical overdue reports.
    """
    return get_global_cases_by_deadline(current_user, db)


# ==============================================================================
# REPORT REQUESTS CRUD
# ==============================================================================

@router.post("/cases/{case_id}/priorities/report-requests", response_model=ReportRequestOut)
def create_report_request(
    case_id: str,
    payload: ReportRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Records a formal request sent to an external authority (FSL, Telecom, Bank, Medical).
    """
    real_id = resolve_case_id(case_id, db)
    now = datetime.now(timezone.utc)

    req = ReportRequest(
        case_id=real_id,
        report_type=payload.report_type,
        requested_from=payload.requested_from,
        requested_date=payload.requested_date or now,
        expected_date=payload.expected_date,
        urgency=payload.urgency or "high",
        status="requested",
        notes=payload.notes
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    invalidate_priorities_cache(real_id)
    publish_collaboration_event(
        db=db,
        case_id=real_id,
        event_type="report_requested",
        item_type="report_request",
        item_id=str(req.id),
        user_id=current_user.id,
        user_name=current_user.full_name or current_user.email,
        summary=f"Report requested: {req.report_type}",
        payload={
            "report_id": req.id,
            "report_type": req.report_type,
            "requested_from": req.requested_from
        }
    )

    return req


@router.patch("/cases/{case_id}/priorities/report-requests/{request_id}", response_model=ReportRequestOut)
def update_report_request(
    case_id: str,
    request_id: int,
    payload: ReportRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates report request status, marks received, or links an incoming exhibit.
    """
    real_id = resolve_case_id(case_id, db)
    req = db.query(ReportRequest).filter(
        ReportRequest.id == request_id,
        ReportRequest.case_id == real_id
    ).first()

    if not req:
        raise HTTPException(status_code=404, detail="Report request not found")

    if payload.status:
        req.status = payload.status
        if payload.status == "received" and not req.received_date:
            req.received_date = payload.received_date or datetime.now(timezone.utc)
    if payload.linked_evidence_id is not None:
        req.linked_evidence_id = payload.linked_evidence_id
    if payload.notes is not None:
        req.notes = payload.notes

    db.commit()
    db.refresh(req)
    invalidate_priorities_cache(real_id)

    publish_collaboration_event(
        db=db,
        case_id=real_id,
        event_type="report_updated",
        item_type="report_request",
        item_id=str(req.id),
        user_id=current_user.id,
        user_name=current_user.full_name or current_user.email,
        summary=f"Report updated: {req.report_type} -> {req.status}",
        payload={
            "report_id": req.id,
            "status": req.status,
            "linked_evidence_id": req.linked_evidence_id
        }
    )

    return req


# ==============================================================================
# PEOPLE REGISTER & STATEMENTS
# ==============================================================================

@router.post("/cases/{case_id}/priorities/people", response_model=PersonRegisterOut)
def add_person_to_register(
    case_id: str,
    payload: PersonRegisterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Adds a person to the case people register."""
    real_id = resolve_case_id(case_id, db)
    pr = PersonRegister(
        case_id=real_id,
        name=payload.name,
        role=payload.role,
        contact_info=payload.contact_info,
        linked_entity_id=payload.linked_entity_id,
        is_important=payload.is_important or False,
        notes=payload.notes
    )
    db.add(pr)
    db.commit()
    db.refresh(pr)

    # Automatically create initial unexamined statement record
    db.add(StatementTracker(
        case_id=real_id,
        person_id=pr.id,
        statement_type="section_161_police",
        status="not_contacted"
    ))
    db.commit()

    invalidate_priorities_cache(real_id)
    return pr


@router.post("/cases/{case_id}/priorities/statements", response_model=StatementTrackerOut)
def record_or_update_statement(
    case_id: str,
    payload: StatementTrackerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Creates or schedules a statement for a person in the registry."""
    real_id = resolve_case_id(case_id, db)
    existing = db.query(StatementTracker).filter(
        StatementTracker.case_id == real_id,
        StatementTracker.person_id == payload.person_id
    ).first()

    if existing:
        existing.statement_type = payload.statement_type
        existing.status = payload.status
        existing.scheduled_date = payload.scheduled_date
        existing.notes = payload.notes
        db.commit()
        db.refresh(existing)
        invalidate_priorities_cache(real_id)
        return existing

    stmt = StatementTracker(
        case_id=real_id,
        person_id=payload.person_id,
        statement_type=payload.statement_type,
        status=payload.status,
        scheduled_date=payload.scheduled_date,
        notes=payload.notes
    )
    db.add(stmt)
    db.commit()
    db.refresh(stmt)
    invalidate_priorities_cache(real_id)
    return stmt
