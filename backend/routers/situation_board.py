"""
backend/routers/situation_board.py
==================================
Live Case Wall (Situation Board) API Router.
Provides a consolidated real-time case state payload tailored for team briefing rooms,
command center wall displays, and secondary monitors.

Features:
- Leading hypotheses with Bayesian posterior percentages & confidence ranges
- Newest evidentiary exhibits with hash integrity verification & Sec 65B badges
- Open forensic & custody alerts sorted by severity
- Real-time statutory procedural deadline countdowns (BNSS / CrPC charge sheet timers)
- Active personnel presence ("Who is online")
- High-priority investigative tasks due
- Background worker jobs running / queued
- Briefing Presentation Mode with automatic redaction of restricted character data
  (prior criminal records, suspect profiling factors, sensitive PII)
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case as sa_case

from database import get_db
from models import (
    Case, User, Hypothesis, Evidence, Alert, CaseDeadline,
    InvestigationTask, Job, CasePresence, PriorRecord, SuspectProfileFactor
)
from auth import get_current_user, check_case_access
from routers.common import resolve_case_id
from collaboration import get_active_presence, record_presence_heartbeat
from procedure_engine import recalculate_case_deadlines

router = APIRouter(tags=["Live Case Wall & Situation Board"])
logger = logging.getLogger("evidentia.situation_board")


def _sanitize_for_presentation(text: str) -> str:
    """
    Strips or redacts mentions of prior convictions, previous FIRs, and prejudicial character
    evidence pursuant to Section 54 of the Indian Evidence Act / Section 52 BSA.
    """
    if not text:
        return ""
    redacted = text
    patterns = [
        (r"(?i)\b(convicted|prior convict|habitual offender|history-sheeter|record of arrest|previous conviction|past criminal record)\b", "[CHARACTER EVIDENCE REDACTED - SEC 54]"),
        (r"(?i)\b(FIR\s+No\.?\s*\d+/\d{2,4}\s+at\s+[\w\s]+PS)\b", "[PREVIOUS FIR REDACTED]"),
        (r"(?i)\b(suspect\s+profile|criminal\s+predisposition|motive\s+speculation)\b", "[PROFILE RESTRICTED]"),
    ]
    for pattern, repl in patterns:
        redacted = re.sub(pattern, repl, redacted)
    return redacted


@router.get("/cases/{case_id}/situation-board")
def get_case_situation_board(
    case_id: str,
    presentation_mode: bool = Query(False, description="Redact restricted character records and suspect profiling for briefings"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Retrieves full aggregated situational awareness for the Live Case Wall.
    Designed for zero-click overview on large displays with auto-refreshing SSE integration.
    """
    real_id = resolve_case_id(case_id, db)
    if not check_case_access(real_id, current_user, db, "read"):
        raise HTTPException(status_code=403, detail="Access denied to this case docket.")

    case = db.query(Case).filter(Case.id == real_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case docket not found.")

    now = datetime.now(timezone.utc)

    # 1. Update viewer presence as "Live Case Wall"
    try:
        record_presence_heartbeat(
            db=db,
            case_id=real_id,
            user_id=current_user.id,
            user_name=current_user.full_name or current_user.email,
            user_role=current_user.role or "analyst",
            current_location="Live Case Wall",
            item_id="situation_board"
        )
    except Exception as e:
        logger.warning(f"Could not update wall presence: {e}")

    # 2. Leading Hypotheses with Robust Confidence Ranges
    evidence_count = db.query(Evidence).filter(Evidence.case_id == real_id).count()
    hypotheses_query = (
        db.query(Hypothesis)
        .filter(Hypothesis.case_id == real_id, Hypothesis.status != "Discarded")
        .all()
    )

    leading_hypotheses = []
    for h in hypotheses_query:
        # Determine base score
        if presentation_mode:
            # In presentation mode, use purely evidentiary Bayesian support
            score = float(h.bayesian_evidence_score or h.evidence_score or h.combined_score or 50.0)
            title = _sanitize_for_presentation(h.title)
            h_desc = _sanitize_for_presentation(h.description or "")
        else:
            score = float(h.bayesian_lr_score or h.combined_score or h.support_score or 50.0)
            title = h.title
            h_desc = h.description or ""

        # Normalize score range (0-100%)
        if 0.0 < score <= 1.0:
            score = round(score * 100, 1)
        else:
            score = round(score, 1)

        penalty = float(h.disconfirmation_penalty or 0.0)

        # Derive empirical confidence range [range_min, range_max]
        # Margin narrows as evidence increases, widens with Heuer disconfirmation penalty
        margin = max(3.5, round(12.0 * max(0.2, 1.0 - (min(evidence_count, 12) / 14.0)) + penalty * 1.2, 1))
        range_min = max(0.0, round(score - margin, 1))
        range_max = min(100.0, round(score + margin, 1))

        # Format hypothesis short code (e.g., H1, H2)
        code = f"H{h.id}"
        if ":" in h.title:
            code = h.title.split(":")[0].strip()

        leading_hypotheses.append({
            "id": h.id,
            "code": code,
            "title": title,
            "description": h_desc,
            "score": score,
            "range_min": range_min,
            "range_max": range_max,
            "evidence_score": round(float(h.evidence_score or score), 1),
            "background_score": None if presentation_mode else round(float(h.background_score or 50.0), 1),
            "disconfirmation_penalty": round(penalty, 2),
            "is_unknown": bool(getattr(h, "is_unknown", False)),
            "status": h.status
        })

    # Sort descending by score
    leading_hypotheses.sort(key=lambda x: x["score"], reverse=True)

    # 3. Newest Evidence Exhibits (Last 6)
    recent_evidence = (
        db.query(Evidence)
        .filter(Evidence.case_id == real_id)
        .order_by(Evidence.id.desc())
        .limit(6)
        .all()
    )
    newest_evidence = []
    for ev in recent_evidence:
        upload_time_str = ev.upload_date.isoformat() if ev.upload_date else now.isoformat()
        newest_evidence.append({
            "id": ev.id,
            "file_name": ev.file_name,
            "file_type": ev.file_type or "Document",
            "evidence_type": ev.evidence_type or "document",
            "file_size": ev.file_size or 0,
            "upload_date": upload_time_str,
            "hash_verified": bool(ev.hash_verified),
            "sec_65b_present": bool(ev.sec_65b_certificate_present),
            "processing_status": str(ev.processing_status.value if hasattr(ev.processing_status, "value") else ev.processing_status),
            "extraction_mode": ev.extraction_mode or "live"
        })

    # 4. Open Intelligent Alerts
    alerts_query = (
        db.query(Alert)
        .filter(
            Alert.case_id == real_id,
            Alert.status.in_(["unread", "read", "acknowledged"])
        )
        .order_by(Alert.id.desc())
        .limit(8)
        .all()
    )
    open_alerts = []
    for a in alerts_query:
        # In presentation mode, skip alerts dealing with restricted background or prior convictions
        if presentation_mode and (a.is_restricted or "prior" in a.title.lower() or "character" in a.title.lower()):
            continue

        created_str = a.created_at.isoformat() if a.created_at else now.isoformat()
        open_alerts.append({
            "id": a.id,
            "rule_type": a.rule_type,
            "severity": a.severity,
            "title": _sanitize_for_presentation(a.title) if presentation_mode else a.title,
            "message": _sanitize_for_presentation(a.message) if presentation_mode else a.message,
            "status": a.status,
            "created_at": created_str,
        })

    # 5. Statutory Deadline Countdowns
    deadlines = (
        db.query(CaseDeadline)
        .filter(
            CaseDeadline.case_id == real_id,
            CaseDeadline.status.in_(["pending", "extended", "overdue"])
        )
        .order_by(CaseDeadline.due_date.asc())
        .all()
    )

    # If no deadlines exist yet, synchronize standard statutory procedural deadlines
    if not deadlines:
        try:
            deadlines = recalculate_case_deadlines(real_id, db)
        except Exception as de:
            logger.warning(f"Could not recalculate deadlines: {de}")
            deadlines = []

    deadline_countdowns = []
    for d in deadlines:
        due = d.due_date
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)

        delta = due - now
        total_seconds = int(delta.total_seconds())
        is_overdue = total_seconds < 0

        abs_sec = abs(total_seconds)
        days = abs_sec // 86400
        hours = (abs_sec % 86400) // 3600
        minutes = (abs_sec % 3600) // 60
        seconds = abs_sec % 60

        if is_overdue:
            urgency = "overdue"
        elif days <= 3:
            urgency = "critical"
        elif days <= 14:
            urgency = "urgent"
        else:
            urgency = "normal"

        deadline_countdowns.append({
            "id": d.id,
            "title": d.title,
            "due_date": due.isoformat(),
            "status": "overdue" if is_overdue else d.status,
            "urgency": urgency,
            "is_overdue": is_overdue,
            "total_seconds": total_seconds,
            "days_remaining": days if not is_overdue else -days,
            "hours_remaining": hours,
            "minutes_remaining": minutes,
            "seconds_remaining": seconds,
            "formatted_countdown": f"{'-' if is_overdue else ''}{days}d {hours:02d}h {minutes:02d}m {seconds:02d}s"
        })

    # Sort deadlines by urgency (overdue & critical first)
    urgency_order = {"overdue": 0, "critical": 1, "urgent": 2, "normal": 3}
    deadline_countdowns.sort(key=lambda x: (urgency_order.get(x["urgency"], 4), x["total_seconds"]))

    # 6. Who Is Online (Real-Time Team Presence)
    online_users = get_active_presence(db=db, case_id=real_id, timeout_seconds=120)
    # Ensure current user is listed
    if not any(u["user_id"] == current_user.id for u in online_users):
        online_users.append({
            "user_id": current_user.id,
            "user_name": current_user.full_name or current_user.email,
            "user_role": current_user.role or "lead_investigator",
            "current_location": "Live Case Wall",
            "item_id": "situation_board",
            "last_seen_at": now.isoformat()
        })

    # 7. High-Priority Investigative Tasks Due
    tasks_query = (
        db.query(InvestigationTask)
        .filter(
            InvestigationTask.case_id == real_id,
            InvestigationTask.status.in_(["Pending", "In Progress"])
        )
        .order_by(
            sa_case(
                (InvestigationTask.priority == "Critical", 1),
                (InvestigationTask.priority == "High", 2),
                (InvestigationTask.priority == "Medium", 3),
                else_=4
            ),
            InvestigationTask.id.desc()
        )
        .limit(6)
        .all()
    )

    tasks_due = []
    for t in tasks_query:
        task_title = _sanitize_for_presentation(t.task) if presentation_mode else t.task
        tasks_due.append({
            "id": t.id,
            "task": task_title,
            "priority": t.priority or "High",
            "status": t.status or "Pending",
            "assigned_to": t.assigned_to or "Unassigned",
            "category": t.category or "investigation",
            "created_at": t.created_at.isoformat() if t.created_at else now.isoformat()
        })

    # 8. Background Jobs Running / Queued
    jobs_query = (
        db.query(Job)
        .filter(
            Job.case_id == real_id,
            Job.status.in_(["queued", "running"])
        )
        .order_by(Job.id.desc())
        .all()
    )
    jobs_running = []
    for j in jobs_query:
        jobs_running.append({
            "id": j.id,
            "job_type": j.job_type,
            "current_stage": j.current_stage or "queued",
            "progress_pct": round(float(j.progress_pct or 0.0), 1),
            "status": j.status,
            "created_by": j.created_by or "Investigator"
        })

    return {
        "case_info": {
            "id": case.id,
            "fir_number": case.fir_number or f"FIR-2026-CASE-{case.id:04d}",
            "title": case.title,
            "description": case.description,
            "status": case.status,
            "created_at": case.created_at.isoformat() if case.created_at else now.isoformat(),
        },
        "leading_hypotheses": leading_hypotheses,
        "newest_evidence": newest_evidence,
        "open_alerts": open_alerts,
        "deadline_countdowns": deadline_countdowns,
        "who_is_online": online_users,
        "tasks_due": tasks_due,
        "jobs_running": jobs_running,
        "presentation_mode_active": presentation_mode,
        "redacted_items_count": 0 if not presentation_mode else (
            db.query(PriorRecord).filter(PriorRecord.case_id == real_id).count() +
            db.query(SuspectProfileFactor).filter(SuspectProfileFactor.case_id == real_id).count()
        ),
        "timestamp": now.isoformat(),
    }
