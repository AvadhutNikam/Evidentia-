"""
backend/routers/alerts.py
=========================
Alerts, Statutory Compliance & Shift Handover API Router.
"""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models import (
    Alert, AlertRuleConfig, NotificationPreference,
    StatutoryDeadlineRule, CaseDeadline, HandoverSummary,
    Case, User
)
from schemas import (
    AlertOut, AlertAcknowledgeRequest, AlertSnoozeRequest, AlertResolveRequest,
    NotificationPreferenceOut, NotificationPreferenceUpdate,
    StatutoryDeadlineRuleOut, CaseDeadlineOut, CaseDeadlineUpdateRequest,
    HandoverGenerateRequest, HandoverSummaryOut, SinceYouWereAwayOut
)
from auth import get_current_user, check_case_access, require_role
from routers.common import resolve_case_id
from alerts_engine import (
    get_case_alerts, acknowledge_alert, snooze_alert,
    resolve_alert_manually, check_statutory_deadlines,
    ensure_statutory_rules
)
from handover_engine import (
    generate_handover_report, get_since_you_were_away,
    update_user_case_last_seen
)
from audit_engine import log_audit_event

router = APIRouter(tags=["Alerts & Shift Handover"])


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ==============================================================================
# 1. ALERTS ENDPOINTS
# ==============================================================================

@router.get("/cases/{case_id}/alerts", response_model=List[AlertOut])
def get_alerts_endpoint(
    case_id: str,
    status: Optional[str] = Query(None, description="Filter by unread, acknowledged, resolved"),
    severity: Optional[str] = Query(None, description="Filter by critical, warning, info"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns alerts for a case with status/severity filters and reviewer privacy redaction."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied: You are not assigned to this case.")

    return get_case_alerts(
        case_id=real_case_id,
        user=current_user,
        db=db,
        status_filter=status,
        severity_filter=severity
    )


@router.post("/cases/{case_id}/alerts/{alert_id}/acknowledge", response_model=AlertOut)
def acknowledge_alert_endpoint(
    case_id: str,
    alert_id: int,
    data: Optional[AlertAcknowledgeRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Marks an alert as acknowledged by the current investigator."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied.")

    try:
        return acknowledge_alert(
            alert_id=alert_id,
            user=current_user,
            db=db,
            note=data.note if data else None
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/cases/{case_id}/alerts/{alert_id}/snooze", response_model=AlertOut)
def snooze_alert_endpoint(
    case_id: str,
    alert_id: int,
    data: AlertSnoozeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Snoozes an alert for a specified number of hours (default 24h)."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied.")

    try:
        return snooze_alert(
            alert_id=alert_id,
            hours=data.hours,
            user=current_user,
            db=db
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/cases/{case_id}/alerts/{alert_id}/resolve", response_model=AlertOut)
def resolve_alert_endpoint(
    case_id: str,
    alert_id: int,
    data: AlertResolveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually resolves an alert with a mandatory justification."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "analyze"):
        raise HTTPException(status_code=403, detail="Access denied: Only analysts and leads can resolve alerts.")

    try:
        return resolve_alert_manually(
            alert_id=alert_id,
            reason=data.reason,
            user=current_user,
            db=db
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==============================================================================
# 2. STATUTORY DEADLINES ENDPOINTS
# ==============================================================================

@router.get("/cases/{case_id}/deadlines", response_model=List[CaseDeadlineOut])
def get_case_deadlines_endpoint(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns statutory case deadlines and refreshes approaching reminder alerts."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied.")

    # Refresh deadlines & reminders
    check_statutory_deadlines(real_case_id, db)

    deadlines = db.query(CaseDeadline).filter(
        CaseDeadline.case_id == real_case_id
    ).order_by(CaseDeadline.due_date.asc()).all()

    now = datetime.now(timezone.utc)
    results = []
    for dl in deadlines:
        target = _ensure_utc(dl.extended_until) if dl.extended_until else _ensure_utc(dl.due_date)
        diff_seconds = (target - now).total_seconds()
        days_rem = int(diff_seconds // 86400)
        is_over = (diff_seconds <= 0)

        results.append(CaseDeadlineOut(
            id=dl.id,
            case_id=dl.case_id,
            statute_rule_id=dl.statute_rule_id,
            title=dl.title,
            due_date=target,
            status=dl.status,
            satisfied_at=dl.satisfied_at,
            satisfied_by=dl.satisfied_by,
            extended_until=dl.extended_until,
            extension_reason=dl.extension_reason,
            days_remaining=days_rem,
            is_overdue=is_over,
            created_at=dl.created_at
        ))
    return results


@router.put("/cases/{case_id}/deadlines/{deadline_id}", response_model=CaseDeadlineOut)
def update_case_deadline_endpoint(
    case_id: str,
    deadline_id: int,
    data: CaseDeadlineUpdateRequest,
    current_user: User = Depends(require_role(["admin", "lead_investigator"])),
    db: Session = Depends(get_db)
):
    """Allows Case Lead or Admin to mark a statutory deadline extended or satisfied."""
    real_case_id = resolve_case_id(case_id, db)
    dl = db.query(CaseDeadline).filter(CaseDeadline.id == deadline_id, CaseDeadline.case_id == real_case_id).first()
    if not dl:
        raise HTTPException(status_code=404, detail="Deadline not found")

    before_val = dl.status
    now = datetime.now(timezone.utc)

    if data.satisfied:
        dl.status = "satisfied"
        dl.satisfied_at = now
        dl.satisfied_by = current_user.full_name
    elif data.extended_until:
        dl.status = "extended"
        dl.extended_until = _ensure_utc(data.extended_until)
        dl.extension_reason = data.extension_reason or "Statutory extension granted by Court order"

    if data.status:
        dl.status = data.status

    # Audit the deadline update
    log_audit_event(
        db=db,
        action_type="DEADLINE_UPDATED",
        target_type="case_deadline",
        target_id=str(dl.id),
        description=f"Investigator {current_user.full_name} updated statutory deadline #{dl.id} ('{dl.title}'). Status: {dl.status}. Extension: {dl.extension_reason or 'None'}",
        case_id=real_case_id,
        user_id=current_user.id,
        user_name=current_user.full_name,
        user_role=current_user.role,
        before_value=before_val,
        after_value=dl.status,
        commit=False
    )
    db.commit()
    db.refresh(dl)

    target = _ensure_utc(dl.extended_until) if dl.extended_until else _ensure_utc(dl.due_date)
    diff_seconds = (target - now).total_seconds()

    return CaseDeadlineOut(
        id=dl.id,
        case_id=dl.case_id,
        statute_rule_id=dl.statute_rule_id,
        title=dl.title,
        due_date=target,
        status=dl.status,
        satisfied_at=dl.satisfied_at,
        satisfied_by=dl.satisfied_by,
        extended_until=dl.extended_until,
        extension_reason=dl.extension_reason,
        days_remaining=int(diff_seconds // 86400),
        is_overdue=(diff_seconds <= 0),
        created_at=dl.created_at
    )


@router.get("/statutory-deadline-rules", response_model=List[StatutoryDeadlineRuleOut])
def get_statutory_rules_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns the legal expert reviewed statutory rules catalogue."""
    ensure_statutory_rules(db)
    return db.query(StatutoryDeadlineRule).all()


# ==============================================================================
# 3. SHIFT HANDOVER & "SINCE YOU WERE AWAY" ENDPOINTS
# ==============================================================================

@router.get("/cases/{case_id}/handovers", response_model=List[HandoverSummaryOut])
def list_case_handovers_endpoint(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists historical shift handover briefing records for the case."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied.")

    handovers = db.query(HandoverSummary).filter(
        HandoverSummary.case_id == real_case_id
    ).order_by(desc(HandoverSummary.created_at)).all()

    results = []
    for h in handovers:
        try:
            struct_content = json.loads(h.structured_content) if h.structured_content else {}
        except Exception:
            struct_content = {}
        results.append(HandoverSummaryOut(
            id=h.id,
            case_id=h.case_id,
            period_start=h.period_start,
            period_end=h.period_end,
            headline=h.headline,
            structured_content=struct_content,
            rendered_text=h.rendered_text,
            generated_by=h.generated_by,
            generation_type=h.generation_type,
            created_at=h.created_at
        ))
    return results


@router.post("/cases/{case_id}/handovers/generate", response_model=HandoverSummaryOut)
def generate_handover_endpoint(
    case_id: str,
    data: HandoverGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generates an on-demand shift handover report covering the specified window."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied.")

    summary = generate_handover_report(
        case_id=real_case_id,
        db=db,
        start_time=data.start_time,
        end_time=data.end_time,
        period_hours=data.period_hours or 24,
        user=current_user,
        generation_type=data.generation_type or "manual"
    )

    try:
        struct_content = json.loads(summary.structured_content) if summary.structured_content else {}
    except Exception:
        struct_content = {}

    return HandoverSummaryOut(
        id=summary.id,
        case_id=summary.case_id,
        period_start=summary.period_start,
        period_end=summary.period_end,
        headline=summary.headline,
        structured_content=struct_content,
        rendered_text=summary.rendered_text,
        generated_by=summary.generated_by,
        generation_type=summary.generation_type,
        created_at=summary.created_at
    )


@router.get("/cases/{case_id}/handovers/since-last-visit", response_model=SinceYouWereAwayOut)
@router.get("/cases/{case_id}/handover/since-away", response_model=SinceYouWereAwayOut)
def since_last_visit_endpoint(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns an immediate executive briefing of what changed in the case
    since the user's previous session. Also updates the user's last_seen_at timestamp.
    """
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied.")

    result = get_since_you_were_away(
        case_id=real_case_id,
        user=current_user,
        db=db
    )

    # Update last seen timestamp
    update_user_case_last_seen(real_case_id, current_user.id, db)

    return result


@router.get("/cases/{case_id}/handovers/{handover_id}", response_model=HandoverSummaryOut)
def get_handover_detail_endpoint(
    case_id: str,
    handover_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns full details and rendered markdown for a specific handover record."""
    real_case_id = resolve_case_id(case_id, db)
    if not check_case_access(real_case_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied.")

    h = db.query(HandoverSummary).filter(
        HandoverSummary.id == handover_id,
        HandoverSummary.case_id == real_case_id
    ).first()
    if not h:
        raise HTTPException(status_code=404, detail="Handover summary not found")

    try:
        struct_content = json.loads(h.structured_content) if h.structured_content else {}
    except Exception:
        struct_content = {}

    return HandoverSummaryOut(
        id=h.id,
        case_id=h.case_id,
        period_start=h.period_start,
        period_end=h.period_end,
        headline=h.headline,
        structured_content=struct_content,
        rendered_text=h.rendered_text,
        generated_by=h.generated_by,
        generation_type=h.generation_type,
        created_at=h.created_at
    )


# ==============================================================================
# 4. NOTIFICATION PREFERENCES ENDPOINTS
# ==============================================================================

@router.get("/users/me/notification-preferences", response_model=List[NotificationPreferenceOut])
def get_notification_preferences_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns notification preferences for the logged-in officer."""
    prefs = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id
    ).all()
    if not prefs:
        # Create default preference
        default_pref = NotificationPreference(
            user_id=current_user.id,
            rule_type="all",
            in_app_enabled=True,
            email_enabled=False,
            digest_mode="immediate"
        )
        db.add(default_pref)
        db.commit()
        db.refresh(default_pref)
        return [default_pref]
    return prefs


@router.put("/users/me/notification-preferences", response_model=NotificationPreferenceOut)
def update_notification_preferences_endpoint(
    data: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates notification channels, quiet hours, and digest preferences."""
    pref = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id
    ).first()
    if not pref:
        pref = NotificationPreference(
            user_id=current_user.id,
            rule_type="all",
            in_app_enabled=True,
            email_enabled=False,
            digest_mode="immediate"
        )
        db.add(pref)

    if data.in_app_enabled is not None: pref.in_app_enabled = data.in_app_enabled
    if data.email_enabled is not None: pref.email_enabled = data.email_enabled
    if data.digest_mode is not None: pref.digest_mode = data.digest_mode
    if data.quiet_hours_start is not None: pref.quiet_hours_start = data.quiet_hours_start
    if data.quiet_hours_end is not None: pref.quiet_hours_end = data.quiet_hours_end

    db.commit()
    db.refresh(pref)
    return pref
