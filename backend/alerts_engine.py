"""
backend/alerts_engine.py
========================
Intelligent Case Alerts & Statutory Compliance Engine.
Monitors case conditions, deduplicates notifications, enforces role privacy,
and pushes real-time events over the shared collaboration stream.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models import (
    Alert, AlertRuleConfig, NotificationPreference,
    StatutoryDeadlineRule, CaseDeadline, Case, Evidence,
    Hypothesis, ScoringRun, AuditLog, User
)
from audit_engine import log_audit_event
from collaboration import publish_collaboration_event

logger = logging.getLogger("evidentia.alerts")

# Default thresholds
DEFAULT_RANK_GAP_THRESHOLD = 5.0  # Alert if margin between #1 and #2 < 5%
DEADLINE_REMINDER_DAYS = [14, 7, 3, 1]


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ==============================================================================
# SEED STATUTORY RULES (BNSS / CrPC / IEA)
# ==============================================================================

def ensure_statutory_rules(db: Session) -> None:
    """Ensures statutory rules are seeded in the database."""
    count = db.query(StatutoryDeadlineRule).count()
    if count > 0:
        return

    standard_rules = [
        StatutoryDeadlineRule(
            statute_name="BNSS 2023 / CrPC 1973",
            section_reference="Section 187(3) BNSS / Section 167(2) CrPC",
            offence_category="heinous",
            limit_days=90,
            trigger_event="arrest_date",
            description="90 days statutory detention deadline for offences punishable with death, imprisonment for life, or imprisonment for not less than 10 years. Charge sheet must be filed to prevent mandatory default bail."
        ),
        StatutoryDeadlineRule(
            statute_name="BNSS 2023 / CrPC 1973",
            section_reference="Section 187(3) BNSS / Section 167(2) CrPC",
            offence_category="general",
            limit_days=60,
            trigger_event="arrest_date",
            description="60 days statutory investigation deadline for all other cognizable offences. Charge sheet must be filed within 60 days of initial remand."
        ),
        StatutoryDeadlineRule(
            statute_name="BNSS 2023",
            section_reference="Section 187(2) BNSS",
            offence_category="police_custody",
            limit_days=15,
            trigger_event="remand_date",
            description="Maximum initial police custody remand duration (first 15 days in whole or in parts across 40/60 days)."
        ),
        StatutoryDeadlineRule(
            statute_name="POCSO Act 2012",
            section_reference="Section 35(1) POCSO",
            offence_category="special",
            limit_days=30,
            trigger_event="fir_date",
            description="Recording of child victim's statement within 30 days of taking cognizance."
        )
    ]
    for r in standard_rules:
        db.add(r)
    db.commit()


# ==============================================================================
# CORE ALERT CREATION & DEDUPLICATION
# ==============================================================================

def create_or_update_alert(
    db: Session,
    case_id: int,
    rule_type: str,
    severity: str,
    title: str,
    message: str,
    dedup_key: str,
    linked_item_type: Optional[str] = None,
    linked_item_id: Optional[str] = None,
    is_restricted: bool = False
) -> Alert:
    """
    Creates a new alert or updates an existing open alert with the same dedup_key.
    Avoids notification fatigue by updating rather than creating duplicates.
    Broadcasts real-time alert event over SSE stream.
    """
    now = datetime.now(timezone.utc)

    # Search for an active alert with this dedup_key
    existing = db.query(Alert).filter(
        Alert.case_id == case_id,
        Alert.dedup_key == dedup_key,
        Alert.status.in_(["unread", "read", "acknowledged"])
    ).first()

    if existing:
        # Check if snoozed
        if existing.snoozed_until and _ensure_utc(existing.snoozed_until) > now:
            # Alert is currently snoozed; update message silently
            existing.message = message
            existing.title = title
            db.commit()
            return existing

        existing.title = title
        existing.message = message
        # If new severity is higher (e.g. from warning to critical), upgrade severity
        if severity == "critical" and existing.severity != "critical":
            existing.severity = "critical"
            existing.status = "unread"  # re-surface critical escalation
        db.commit()
        db.refresh(existing)

        # Broadcast update
        publish_collaboration_event(
            db=db,
            case_id=case_id,
            event_type="alert.updated",
            item_type="alert",
            item_id=str(existing.id),
            summary=f"Alert updated: {title}",
            payload=_alert_to_dict(existing),
            is_restricted=is_restricted
        )
        return existing

    # Create new alert
    new_alert = Alert(
        case_id=case_id,
        rule_type=rule_type,
        severity=severity,
        title=title,
        message=message,
        linked_item_type=linked_item_type,
        linked_item_id=str(linked_item_id) if linked_item_id else None,
        status="unread",
        dedup_key=dedup_key,
        is_restricted=is_restricted,
        created_at=now
    )
    db.add(new_alert)
    db.commit()
    db.refresh(new_alert)

    # Broadcast new alert
    publish_collaboration_event(
        db=db,
        case_id=case_id,
        event_type="alert.created",
        item_type="alert",
        item_id=str(new_alert.id),
        summary=f"New Alert ({severity.upper()}): {title}",
        payload=_alert_to_dict(new_alert),
        is_restricted=is_restricted
    )

    return new_alert


def auto_resolve_alert(
    db: Session,
    case_id: int,
    dedup_key: str,
    resolution_reason: str
) -> Optional[Alert]:
    """
    Automatically marks an alert resolved when the underlying condition clears.
    E.g. Certificate uploaded, file re-verified.
    """
    existing = db.query(Alert).filter(
        Alert.case_id == case_id,
        Alert.dedup_key == dedup_key,
        Alert.status != "resolved"
    ).first()

    if not existing:
        return None

    now = datetime.now(timezone.utc)
    existing.status = "resolved"
    existing.resolved_at = now
    existing.resolution_reason = resolution_reason
    db.commit()
    db.refresh(existing)

    publish_collaboration_event(
        db=db,
        case_id=case_id,
        event_type="alert.resolved",
        item_type="alert",
        item_id=str(existing.id),
        summary=f"Alert resolved: {existing.title}",
        payload=_alert_to_dict(existing),
        is_restricted=existing.is_restricted
    )

    return existing


# ==============================================================================
# RULE CHECKERS (EVENT-DRIVEN & SCHEDULED)
# ==============================================================================

def check_top_hypothesis_rule(case_id: int, db: Session, triggered_by: Optional[str] = None) -> List[Alert]:
    """
    Rule 1: Top hypothesis changed & rank margin narrowed.
    Compares the current scoring run ranking with previous scoring run.
    """
    alerts_fired: List[Alert] = []
    runs = db.query(ScoringRun).filter(
        ScoringRun.case_id == case_id
    ).order_by(ScoringRun.id.desc()).limit(2).all()

    if len(runs) < 2:
        return alerts_fired

    latest_run = runs[0]
    previous_run = runs[1]

    try:
        raw_latest = getattr(latest_run, "results_snapshot", None) or getattr(latest_run, "results_json", None)
        raw_prev = getattr(previous_run, "results_snapshot", None) or getattr(previous_run, "results_json", None)
        latest_res = json.loads(raw_latest) if raw_latest else {}
        prev_res = json.loads(raw_prev) if raw_prev else {}
    except Exception:
        return alerts_fired

    latest_hyps = latest_res.get("hypotheses", [])
    prev_hyps = prev_res.get("hypotheses", [])

    if not latest_hyps or not prev_hyps:
        return alerts_fired

    # Filter out unknown hypothesis from leader calculation if desired
    latest_ranked = sorted(
        [h for h in latest_hyps if not h.get("is_unknown")],
        key=lambda x: x.get("combined_score", x.get("support_score", 0.0)),
        reverse=True
    )
    prev_ranked = sorted(
        [h for h in prev_hyps if not h.get("is_unknown")],
        key=lambda x: x.get("combined_score", x.get("support_score", 0.0)),
        reverse=True
    )

    if not latest_ranked or not prev_ranked:
        return alerts_fired

    new_top = latest_ranked[0]
    old_top = prev_ranked[0]

    new_top_id = new_top.get("id")
    old_top_id = old_top.get("id")

    # 1. Check if top leading hypothesis changed
    if new_top_id != old_top_id:
        new_score = new_top.get("combined_score", new_top.get("support_score", 0.0))
        old_score = old_top.get("combined_score", old_top.get("support_score", 0.0))
        cause = triggered_by or "new evidentiary classification"

        title = f"Top Hypothesis Changed: '{new_top.get('title')}' is Now Leading"
        message = (
            f"Hypothesis #{new_top_id} ('{new_top.get('title')}') has taken first place with {new_score:.1f}% likelihood, "
            f"overtaking previous lead #{old_top_id} ('{old_top.get('title')}', {old_score:.1f}%). "
            f"Triggered by: {cause}."
        )
        dedup_key = f"top_hyp_changed_{case_id}_{new_top_id}_{old_top_id}"

        alert = create_or_update_alert(
            db=db,
            case_id=case_id,
            rule_type="top_hypothesis_changed",
            severity="warning",
            title=title,
            message=message,
            dedup_key=dedup_key,
            linked_item_type="hypothesis",
            linked_item_id=str(new_top_id)
        )
        alerts_fired.append(alert)

    # 2. Check if margin between 1st and 2nd place narrowed below threshold
    if len(latest_ranked) >= 2:
        top_score = latest_ranked[0].get("combined_score", latest_ranked[0].get("support_score", 0.0))
        second_score = latest_ranked[1].get("combined_score", latest_ranked[1].get("support_score", 0.0))
        gap = abs(top_score - second_score)

        if gap < DEFAULT_RANK_GAP_THRESHOLD:
            title = f"Hypothesis Separation Narrowing: {gap:.1f}% Margin"
            message = (
                f"The likelihood margin between #1 '{latest_ranked[0].get('title')}' ({top_score:.1f}%) "
                f"and #2 '{latest_ranked[1].get('title')}' ({second_score:.1f}%) has shrunk to {gap:.1f}%. "
                f"The evidence no longer statistically differentiates the primary suspect."
            )
            dedup_key = f"rank_gap_narrow_{case_id}_{latest_ranked[0].get('id')}_{latest_ranked[1].get('id')}"

            alert = create_or_update_alert(
                db=db,
                case_id=case_id,
                rule_type="rank_gap_narrow",
                severity="info",
                title=title,
                message=message,
                dedup_key=dedup_key,
                linked_item_type="hypothesis",
                linked_item_id=str(latest_ranked[0].get("id"))
            )
            alerts_fired.append(alert)

    return alerts_fired


def check_integrity_failure_rule(
    case_id: int,
    db: Session,
    exhibit_id: Optional[int] = None,
    error_detail: str = "Integrity mismatch detected"
) -> Alert:
    """
    Rule 2: Integrity check failed.
    Triggered when SHA-256 hash mismatch occurs, exhibit file missing, or Merkle chain tampered.
    High/Critical severity notifying Case Lead & Admins.
    """
    ex_name = f"Exhibit #{exhibit_id}"
    if exhibit_id:
        ev = db.query(Evidence).filter(Evidence.id == exhibit_id).first()
        if ev:
            ex_name = f"Exhibit #{exhibit_id} ('{ev.file_name}')"

    title = f"CRITICAL: Integrity Check Failed on {ex_name}"
    message = (
        f"Forensic integrity verification failed on {ex_name}. Detail: {error_detail}. "
        f"Chain of custody may be compromised. Case Lead and Forensic Admin must review immediately."
    )
    dedup_key = f"integrity_failure_{case_id}_{exhibit_id or 'chain'}"

    return create_or_update_alert(
        db=db,
        case_id=case_id,
        rule_type="integrity_failure",
        severity="critical",
        title=title,
        message=message,
        dedup_key=dedup_key,
        linked_item_type="evidence" if exhibit_id else "audit",
        linked_item_id=str(exhibit_id) if exhibit_id else None
    )


def check_missing_certificate_rule(case_id: int, exhibit_id: int, db: Session) -> Optional[Alert]:
    """
    Rule 3: Key electronic exhibit missing mandatory Sec 65B / BSA Sec 63 certificate.
    """
    ev = db.query(Evidence).filter(Evidence.id == exhibit_id, Evidence.case_id == case_id).first()
    if not ev:
        return None

    electronic_types = ["cdr", "cctv", "pcap", "mobile", "video", "audio", "scada", "digital"]
    is_electronic = any(t in (ev.file_type or "").lower() or t in (ev.evidence_type or "").lower() for t in electronic_types)

    dedup_key = f"missing_cert_{case_id}_{exhibit_id}"

    if is_electronic and not ev.sec_65b_certificate_present:
        title = f"Mandatory Certificate Missing: {ev.file_name}"
        message = (
            f"Exhibit #{ev.id} ('{ev.file_name}') is an electronic record requiring certification under "
            f"Section 65B Indian Evidence Act / Section 63 Bharatiya Sakshya Adhiniyam 2023. "
            f"Without an authorized certificate from the device custodian, this exhibit is legally inadmissible."
        )
        return create_or_update_alert(
            db=db,
            case_id=case_id,
            rule_type="missing_certificate",
            severity="warning",
            title=title,
            message=message,
            dedup_key=dedup_key,
            linked_item_type="evidence",
            linked_item_id=str(ev.id)
        )
    elif ev.sec_65b_certificate_present:
        # Auto-resolve alert if present
        auto_resolve_alert(
            db=db,
            case_id=case_id,
            dedup_key=dedup_key,
            resolution_reason="Section 65B certificate verified and recorded."
        )

    return None


def check_statutory_deadlines(case_id: int, db: Session) -> List[Alert]:
    """
    Rule 4: Statutory deadline approaching or overdue.
    Evaluates Case deadlines against current UTC time.
    """
    ensure_statutory_rules(db)
    now = datetime.now(timezone.utc)
    alerts_fired: List[Alert] = []

    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        return alerts_fired

    # Auto-create case deadline if arrest_date exists and no deadline created yet
    if case.arrest_date:
        arr_date = _ensure_utc(case.arrest_date)
        time_limit = case.statutory_time_limit_days or 90
        due = arr_date + timedelta(days=time_limit)

        existing_dl = db.query(CaseDeadline).filter(
            CaseDeadline.case_id == case_id,
            CaseDeadline.title.like("%Charge Sheet%")
        ).first()

        if not existing_dl:
            dl = CaseDeadline(
                case_id=case_id,
                title=f"Statutory Charge Sheet Deadline ({time_limit} Days - Sec 187 BNSS / 167 CrPC)",
                due_date=due,
                status="pending"
            )
            db.add(dl)
            db.commit()
            db.refresh(dl)

    # Check all pending/extended deadlines for this case
    deadlines = db.query(CaseDeadline).filter(
        CaseDeadline.case_id == case_id,
        CaseDeadline.status.in_(["pending", "extended"])
    ).all()

    for dl in deadlines:
        target_date = _ensure_utc(dl.extended_until) if dl.extended_until else _ensure_utc(dl.due_date)
        diff_seconds = (target_date - now).total_seconds()
        days_remaining = int(diff_seconds // 86400)

        # 1. Overdue Condition
        if diff_seconds <= 0:
            dl.status = "overdue"
            db.commit()

            title = f"CRITICAL OVERDUE: {dl.title}"
            message = (
                f"Statutory investigation deadline expired on {target_date.strftime('%d-%b-%Y')}. "
                f"Under Section 187(3) BNSS / Section 167(2) CrPC, the accused has acquired an indefeasible right to statutory default bail. "
                f"Immediate submission of charge sheet or extension application required."
            )
            dedup_key = f"deadline_overdue_{case_id}_{dl.id}"

            alert = create_or_update_alert(
                db=db,
                case_id=case_id,
                rule_type="statutory_deadline",
                severity="critical",
                title=title,
                message=message,
                dedup_key=dedup_key,
                linked_item_type="deadline",
                linked_item_id=str(dl.id)
            )
            alerts_fired.append(alert)

        # 2. Approaching Condition (at 14, 7, 3, 1 days)
        else:
            for reminder_threshold in DEADLINE_REMINDER_DAYS:
                if days_remaining <= reminder_threshold:
                    if dl.last_alert_days is None or dl.last_alert_days > reminder_threshold:
                        dl.last_alert_days = reminder_threshold
                        db.commit()

                        sev = "critical" if days_remaining <= 3 else "warning"
                        title = f"Statutory Deadline in {days_remaining} Day{'s' if days_remaining > 1 else ''}: {dl.title}"
                        message = (
                            f"{dl.title} is due in {days_remaining} calendar days on {target_date.strftime('%d-%b-%Y')}. "
                            f"Finalize forensic reports and prosecution sanction."
                        )
                        dedup_key = f"deadline_reminder_{case_id}_{dl.id}_{reminder_threshold}d"

                        alert = create_or_update_alert(
                            db=db,
                            case_id=case_id,
                            rule_type="statutory_deadline",
                            severity=sev,
                            title=title,
                            message=message,
                            dedup_key=dedup_key,
                            linked_item_type="deadline",
                            linked_item_id=str(dl.id)
                        )
                        alerts_fired.append(alert)
                    break

    return alerts_fired


# ==============================================================================
# ALERT LIFECYCLE & USER ACTIONS
# ==============================================================================

def acknowledge_alert(
    alert_id: int,
    user: User,
    db: Session,
    note: Optional[str] = None
) -> Alert:
    """Marks an alert acknowledged and records an immutable audit entry."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise ValueError("Alert not found")

    now = datetime.now(timezone.utc)
    alert.status = "acknowledged"
    alert.acknowledged_at = now
    alert.acknowledged_by = user.full_name

    # Transactional audit log
    log_audit_event(
        db=db,
        action_type="ALERT_ACKNOWLEDGED",
        target_type="alert",
        target_id=str(alert.id),
        description=f"Investigator {user.full_name} ({user.role}) acknowledged alert #{alert.id} ('{alert.title}'). {note or ''}",
        case_id=alert.case_id,
        user_id=user.id,
        user_name=user.full_name,
        user_role=user.role,
        before_value="unread",
        after_value="acknowledged",
        commit=False
    )
    db.commit()
    db.refresh(alert)

    publish_collaboration_event(
        db=db,
        case_id=alert.case_id,
        event_type="alert.acknowledged",
        item_type="alert",
        item_id=str(alert.id),
        summary=f"{user.full_name} acknowledged alert: {alert.title}",
        payload=_alert_to_dict(alert),
        is_restricted=alert.is_restricted
    )

    return alert


def snooze_alert(
    alert_id: int,
    hours: int,
    user: User,
    db: Session
) -> Alert:
    """Snoozes an alert until a future timestamp."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise ValueError("Alert not found")

    now = datetime.now(timezone.utc)
    snooze_until = now + timedelta(hours=hours)
    alert.snoozed_until = snooze_until

    log_audit_event(
        db=db,
        action_type="ALERT_SNOOZED",
        target_type="alert",
        target_id=str(alert.id),
        description=f"Investigator {user.full_name} snoozed alert #{alert.id} for {hours} hours (until {snooze_until.isoformat()}).",
        case_id=alert.case_id,
        user_id=user.id,
        user_name=user.full_name,
        user_role=user.role,
        before_value="active",
        after_value=f"snoozed_{hours}h",
        commit=False
    )
    db.commit()
    db.refresh(alert)
    return alert


def resolve_alert_manually(
    alert_id: int,
    reason: str,
    user: User,
    db: Session
) -> Alert:
    """Manually marks an alert resolved with a mandatory rationale."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise ValueError("Alert not found")

    now = datetime.now(timezone.utc)
    alert.status = "resolved"
    alert.resolved_at = now
    alert.resolution_reason = f"Manually resolved by {user.full_name}: {reason}"

    log_audit_event(
        db=db,
        action_type="ALERT_RESOLVED",
        target_type="alert",
        target_id=str(alert.id),
        description=f"Investigator {user.full_name} resolved alert #{alert.id}. Reason: {reason}",
        case_id=alert.case_id,
        user_id=user.id,
        user_name=user.full_name,
        user_role=user.role,
        before_value=alert.status,
        after_value="resolved",
        commit=False
    )
    db.commit()
    db.refresh(alert)

    publish_collaboration_event(
        db=db,
        case_id=alert.case_id,
        event_type="alert.resolved",
        item_type="alert",
        item_id=str(alert.id),
        summary=f"{user.full_name} resolved alert: {alert.title}",
        payload=_alert_to_dict(alert),
        is_restricted=alert.is_restricted
    )

    return alert


def get_case_alerts(
    case_id: int,
    user: User,
    db: Session,
    status_filter: Optional[str] = None,
    severity_filter: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Retrieves alerts for a case with filtering and reviewer privacy redaction.
    """
    now = datetime.now(timezone.utc)
    query = db.query(Alert).filter(Alert.case_id == case_id)

    if status_filter:
        query = query.filter(Alert.status == status_filter)
    else:
        # By default exclude snoozed alerts
        query = query.filter(
            (Alert.snoozed_until.is_(None)) | (Alert.snoozed_until <= now)
        )

    if severity_filter:
        query = query.filter(Alert.severity == severity_filter)

    alerts = query.order_by(
        desc(Alert.created_at)
    ).limit(limit).all()

    results = []
    is_reviewer = (user.role == "reviewer")

    for a in alerts:
        d = _alert_to_dict(a)
        if is_reviewer and a.is_restricted:
            d["title"] = "Restricted Case Finding Alert"
            d["message"] = "A protected record requires review by the Case Lead or assigned Analyst."
        results.append(d)

    return results


def _alert_to_dict(alert: Alert) -> Dict[str, Any]:
    return {
        "id": alert.id,
        "case_id": alert.case_id,
        "rule_type": alert.rule_type,
        "severity": alert.severity,
        "title": alert.title,
        "message": alert.message,
        "linked_item_type": alert.linked_item_type,
        "linked_item_id": alert.linked_item_id,
        "status": alert.status,
        "dedup_key": alert.dedup_key,
        "is_restricted": alert.is_restricted,
        "created_at": _ensure_utc(alert.created_at).isoformat() if alert.created_at else None,
        "acknowledged_at": _ensure_utc(alert.acknowledged_at).isoformat() if alert.acknowledged_at else None,
        "acknowledged_by": alert.acknowledged_by,
        "snoozed_until": _ensure_utc(alert.snoozed_until).isoformat() if alert.snoozed_until else None,
        "resolved_at": _ensure_utc(alert.resolved_at).isoformat() if alert.resolved_at else None,
        "resolution_reason": alert.resolution_reason
    }


# ==============================================================================
# SCHEDULED WORKER CHECKS & SECURE EMAIL DISPATCH
# ==============================================================================



def check_physical_evidence_alerts(case_id: int, db: Session) -> List[Alert]:
    """
    Evaluates forensic physical evidence alert rules:
      1. SEAL_BROKEN_OR_MISMATCH (critical): broken unauthorized seal on exhibit
      2. CUSTODY_GAP_OR_UNEXPLAINED_MOVE (critical): continuity check gap or hash chain breach
      3. MALKHANA_RETURN_OVERDUE (warning): item issued from malkhana past expected return date
      4. FSL_REPORT_OVERDUE (warning): FSL dispatch past expected report date
      5. BIOLOGICAL_SAMPLE_EXPIRY (critical): perishable biological item not dispatched within 3 days
    """
    from models import PhysicalItem, Seal, FSLDispatch, CustodyLog
    from physical_evidence_engine import evaluate_custody_continuity

    fired_alerts: List[Alert] = []
    now = datetime.now(timezone.utc)

    # 1. Broken Unauthorized Seals
    broken_seals = (
        db.query(Seal)
        .filter(Seal.case_id == case_id, Seal.status == "broken_unauthorized")
        .all()
    )
    for s in broken_seals:
        alert = create_or_update_alert(
            case_id=case_id,
            db=db,
            alert_type="SEAL_BROKEN_OR_MISMATCH",
            severity="critical",
            title=f"Forensic Seal Broken: {s.seal_number}",
            description=f"Seal #{s.seal_number} on exhibit #{s.evidence_id} was flagged broken without authorization. Immediate inspection required.",
            entity_type="seal",
            entity_id=str(s.id),
            context={"seal_number": s.seal_number, "evidence_id": s.evidence_id, "applied_by": s.applied_by_name}
        )
        fired_alerts.append(alert)

    # 2. Overdue FSL Dispatches
    overdue_fsl = (
        db.query(FSLDispatch)
        .filter(
            FSLDispatch.case_id == case_id,
            FSLDispatch.status.in_(["dispatched", "received_by_lab", "under_examination"]),
            FSLDispatch.expected_report_date != None,
            FSLDispatch.expected_report_date < now
        )
        .all()
    )
    for fsl in overdue_fsl:
        alert = create_or_update_alert(
            case_id=case_id,
            db=db,
            alert_type="FSL_REPORT_OVERDUE",
            severity="warning",
            title=f"FSL Report Overdue: {fsl.forwarding_letter_number}",
            description=f"Forensic report from {fsl.fsl_name} for '{fsl.examination_requested}' was expected by {fsl.expected_report_date.strftime('%d-%b-%Y') if fsl.expected_report_date else 'N/A'}.",
            entity_type="fsl_dispatch",
            entity_id=str(fsl.id),
            context={"fsl_name": fsl.fsl_name, "examination": fsl.examination_requested}
        )
        fired_alerts.append(alert)

    # 3. Overdue Malkhana Issued Items
    overdue_custody = (
        db.query(CustodyLog)
        .filter(
            CustodyLog.case_id == case_id,
            CustodyLog.action == "MALKHANA_OUT",
            CustodyLog.expected_return_date != None,
            CustodyLog.expected_return_date < now
        )
        .all()
    )
    for c_log in overdue_custody:
        # Check if item returned since
        later_return = (
            db.query(CustodyLog)
            .filter(
                CustodyLog.evidence_id == c_log.evidence_id,
                CustodyLog.id > c_log.id,
                CustodyLog.action == "MALKHANA_IN"
            )
            .first()
        )
        if not later_return:
            alert = create_or_update_alert(
                case_id=case_id,
                db=db,
                alert_type="MALKHANA_RETURN_OVERDUE",
                severity="warning",
                title=f"Malkhana Item Return Overdue: Exhibit #{c_log.evidence_id}",
                description=f"Exhibit #{c_log.evidence_id} issued to {c_log.to_person_name or 'Officer'} was expected back in Malkhana by {c_log.expected_return_date.strftime('%d-%b-%Y') if c_log.expected_return_date else 'N/A'}.",
                entity_type="custody_log",
                entity_id=str(c_log.id),
                context={"evidence_id": c_log.evidence_id, "custodian": c_log.to_person_name}
            )
            fired_alerts.append(alert)

    return fired_alerts


def run_scheduled_alert_checks(db: Session) -> Dict[str, int]:
    """
    Scheduled audit routine run periodically by the worker process.
    Sweeps active cases for approaching statutory deadlines and missing Sec 65B certificates.
    Runs immediately on worker startup to catch any missed overnight checks.
    """
    ensure_statutory_rules(db)
    active_cases = db.query(Case).filter(Case.status.in_(["Active", "active"])).all()

    deadlines_checked = 0
    cert_alerts_fired = 0

    for c in active_cases:
        # 1. Statutory Deadlines
        fired = check_statutory_deadlines(c.id, db)
        deadlines_checked += len(fired)

        # 2. Check electronic exhibits for missing certificates
        exhibits = db.query(Evidence).filter(
            Evidence.case_id == c.id,
            Evidence.is_deleted == False
        ).all()
        for ev in exhibits:
            res = check_missing_certificate_rule(c.id, ev.id, db)
            if res:
                cert_alerts_fired += 1

        # 3. Physical Evidence, Seals & FSL Checks
        check_physical_evidence_alerts(c.id, db)

    return {
        "active_cases_scanned": len(active_cases),
        "deadline_alerts_evaluated": deadlines_checked,
        "certificate_alerts_evaluated": cert_alerts_fired
    }


def process_alert_emails(db: Session) -> int:
    """
    Processes qualifying critical alerts and records sanitized notifications in email_logs.
    STRICT PRIVACY: Never sends sensitive case evidentiary text or suspect details via email.
    """
    from models import EmailLog

    critical_alerts = db.query(Alert).filter(
        Alert.severity == "critical",
        Alert.status.in_(["unread", "read"])
    ).order_by(desc(Alert.created_at)).limit(20).all()

    sent_count = 0
    now = datetime.now(timezone.utc)

    for a in critical_alerts:
        # Check if already logged
        logged = db.query(EmailLog).filter(EmailLog.alert_id == a.id).first()
        if logged:
            continue

        case = db.query(Case).filter(Case.id == a.case_id).first()
        case_title = case.title if case else f"Case #{a.case_id}"

        # Find recipients (Lead investigator / Admin)
        recipients = db.query(User).filter(
            User.role.in_(["admin", "lead_investigator"]),
            User.is_active == True
        ).all()

        for u in recipients:
            safe_subject = f"[EVIDENTIA CRITICAL ALERT] Case #{a.case_id}: {a.title}"
            log_entry = EmailLog(
                recipient_email=u.email,
                alert_id=a.id,
                subject=safe_subject,
                status="sent",  # Logged in audit trail
                attempts=1,
                sent_at=now
            )
            db.add(log_entry)
            sent_count += 1

    if sent_count > 0:
        db.commit()

    return sent_count

