"""
backend/handover_engine.py
==========================
Shift Handover & Daily Briefing Dossier Engine.
Factual, reproducible synthesis of case changes derived directly from the
Merkle audit ledger, scoring runs, evidence records, and alert ledgers.
Powers both historical shift handovers and real-time 'Since You Were Away' views.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from models import (
    HandoverSummary, UserCaseState, Case, Evidence, Hypothesis,
    EvidenceAssessment, ScoringRun, AuditLog, InvestigationTask,
    Alert, CaseDeadline, User
)
from audit_engine import log_audit_event

logger = logging.getLogger("evidentia.handover")


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ==============================================================================
# STRUCTURED DATA EXTRACTION FROM AUDIT & SCORING LEDGERS
# ==============================================================================

def extract_case_activity_window(
    case_id: int,
    start_time: datetime,
    end_time: datetime,
    db: Session,
    is_reviewer: bool = False
) -> Dict[str, Any]:
    """
    Extracts deterministic facts and metrics strictly from stored records:
    Audit logs, scoring runs, evidence, tasks, and alerts.
    """
    start_utc = _ensure_utc(start_time)
    end_utc = _ensure_utc(end_time)

    # 1. Audit Logs in period
    audit_entries = db.query(AuditLog).filter(
        AuditLog.case_id == case_id,
        AuditLog.timestamp >= start_utc,
        AuditLog.timestamp <= end_utc
    ).order_by(AuditLog.id.asc()).all()

    # 2. Evidence uploaded in period
    new_evidence = db.query(Evidence).filter(
        Evidence.case_id == case_id,
        Evidence.upload_date >= start_utc,
        Evidence.upload_date <= end_utc,
        Evidence.is_deleted == False
    ).all()

    # 3. Scoring runs in period
    scoring_runs = db.query(ScoringRun).filter(
        ScoringRun.case_id == case_id,
        ScoringRun.run_at >= start_utc,
        ScoringRun.run_at <= end_utc
    ).order_by(ScoringRun.id.asc()).all()

    # 4. Analyst overrides from audit log
    overrides = [
        a for a in audit_entries
        if a.action_type in ["ASSESSMENT_OVERRIDE", "CLASSIFICATION_OVERRIDE", "FACTOR_ENTRY"]
    ]

    # 5. Open tasks
    open_tasks = db.query(InvestigationTask).filter(
        InvestigationTask.case_id == case_id,
        InvestigationTask.status.in_(["pending", "in_progress"])
    ).all()

    # 6. Unresolved Alerts
    active_alerts = db.query(Alert).filter(
        Alert.case_id == case_id,
        Alert.status.in_(["unread", "read", "acknowledged"])
    ).all()

    # 7. Approaching Deadlines
    deadlines = db.query(CaseDeadline).filter(
        CaseDeadline.case_id == case_id,
        CaseDeadline.status.in_(["pending", "extended", "overdue"])
    ).all()

    # Active investigators from audit entries
    active_users = list({a.user_name for a in audit_entries if a.user_name})

    # Evidence details
    evidence_items = []
    missing_cert_count = 0
    for ev in new_evidence:
        electronic_types = ["cdr", "cctv", "pcap", "mobile", "video", "audio"]
        is_elec = any(t in (ev.file_type or "").lower() or t in (ev.evidence_type or "").lower() for t in electronic_types)
        if is_elec and not ev.sec_65b_certificate_present:
            missing_cert_count += 1

        evidence_items.append({
            "id": ev.id,
            "file_name": ev.file_name,
            "evidence_type": ev.evidence_type or ev.file_type,
            "uploaded_by": ev.uploaded_by,
            "hash_verified": bool(ev.hash_verified),
            "sec_65b_certified": bool(ev.sec_65b_certificate_present)
        })

    # Scoring Shifts
    scoring_shift = {
        "runs_count": len(scoring_runs),
        "top_hypothesis_changed": False,
        "old_leader": None,
        "new_leader": None,
        "leader_margin": 0.0,
        "ranking_moves": []
    }

    if len(scoring_runs) >= 1:
        first_run = scoring_runs[0]
        last_run = scoring_runs[-1]
        try:
            raw_first = getattr(first_run, "results_snapshot", None) or getattr(first_run, "results_json", None)
            raw_last = getattr(last_run, "results_snapshot", None) or getattr(last_run, "results_json", None)
            first_data = json.loads(raw_first).get("hypotheses", []) if raw_first else []
            last_data = json.loads(raw_last).get("hypotheses", []) if raw_last else []

            if first_data and last_data:
                first_sorted = sorted([h for h in first_data if not h.get("is_unknown")], key=lambda x: x.get("combined_score", 0.0), reverse=True)
                last_sorted = sorted([h for h in last_data if not h.get("is_unknown")], key=lambda x: x.get("combined_score", 0.0), reverse=True)

                if first_sorted and last_sorted:
                    old_top = first_sorted[0]
                    new_top = last_sorted[0]
                    scoring_shift["old_leader"] = {"id": old_top.get("id"), "title": old_top.get("title"), "score": old_top.get("combined_score", 0.0)}
                    scoring_shift["new_leader"] = {"id": new_top.get("id"), "title": new_top.get("title"), "score": new_top.get("combined_score", 0.0)}
                    scoring_shift["top_hypothesis_changed"] = (old_top.get("id") != new_top.get("id"))

                    if len(last_sorted) >= 2:
                        scoring_shift["leader_margin"] = round(abs(last_sorted[0].get("combined_score", 0.0) - last_sorted[1].get("combined_score", 0.0)), 1)
        except Exception as e:
            logger.warning(f"Could not parse scoring shift JSON: {e}")

    # Overrides details
    override_items = []
    for o in overrides:
        if is_reviewer and "prior_record" in (o.target_type or ""):
            continue
        override_items.append({
            "id": o.id,
            "target_type": o.target_type,
            "target_id": o.target_id,
            "analyst": o.user_name,
            "description": o.description,
            "before": o.before_value,
            "after": o.after_value,
            "time": _ensure_utc(o.timestamp).isoformat() if o.timestamp else None
        })

    # Deadlines details
    deadlines_summary = []
    now = datetime.now(timezone.utc)
    for dl in deadlines:
        target = _ensure_utc(dl.extended_until) if dl.extended_until else _ensure_utc(dl.due_date)
        days_left = int((target - now).total_seconds() // 86400)
        deadlines_summary.append({
            "id": dl.id,
            "title": dl.title,
            "due_date": target.isoformat(),
            "status": dl.status,
            "days_remaining": days_left
        })

    return {
        "period_start": start_utc.isoformat(),
        "period_end": end_utc.isoformat(),
        "total_audit_events": len(audit_entries),
        "new_evidence_count": len(new_evidence),
        "evidence_items": evidence_items,
        "missing_cert_count": missing_cert_count,
        "scoring_shift": scoring_shift,
        "overrides_count": len(override_items),
        "override_items": override_items,
        "open_tasks_count": len(open_tasks),
        "active_alerts_count": len(active_alerts),
        "deadlines_summary": deadlines_summary,
        "active_investigators": active_users
    }


# ==============================================================================
# HEADLINE & MARKDOWN BRIEFING GENERATION
# ==============================================================================

def generate_handover_headline(data: Dict[str, Any]) -> str:
    """Generates an executive plain-language headline summarising the shift."""
    total_events = data.get("total_audit_events", 0)
    ev_count = data.get("new_evidence_count", 0)
    cert_missing = data.get("missing_cert_count", 0)
    scoring = data.get("scoring_shift", {})
    deadlines = data.get("deadlines_summary", [])

    if total_events == 0 and ev_count == 0:
        return "No case activity recorded during this shift window."

    parts = []
    if scoring.get("top_hypothesis_changed"):
        new_lead = scoring.get("new_leader", {})
        parts.append(f"Top hypothesis shifted to '{new_lead.get('title')}'")
    else:
        parts.append("Top hypothesis unchanged")

    if ev_count > 0:
        parts.append(f"{ev_count} exhibit{'s' if ev_count > 1 else ''} added")

    if cert_missing > 0:
        parts.append(f"{cert_missing} Sec 65B certificate{'s' if cert_missing > 1 else ''} missing")

    if deadlines:
        min_days = min([d["days_remaining"] for d in deadlines])
        if min_days < 0:
            parts.append("Statutory deadline OVERDUE")
        elif min_days <= 7:
            parts.append(f"Statutory deadline in {min_days} day{'s' if min_days != 1 else ''}")

    return ". ".join(parts) + "."


def render_handover_markdown(
    case: Case,
    headline: str,
    data: Dict[str, Any],
    generated_by: str
) -> str:
    """Renders a structured, court-standard shift handover markdown document."""
    start_str = data.get("period_start", "")[:16].replace("T", " ")
    end_str = data.get("period_end", "")[:16].replace("T", " ")

    lines = [
        f"# Shift Handover Briefing: Case #{case.id} - {case.title}",
        f"**Docket Number:** {case.fir_number or f'CR-{case.id:04d}'} | **Offence Section:** {case.offence_section or 'Unspecified'} | **Period:** `{start_str}` to `{end_str}` UTC",
        f"**Generated By:** {generated_by} | **Status:** {case.status.upper()}",
        "",
        f"> [!IMPORTANT] Executive Summary",
        f"> **{headline}**",
        "",
        "---",
        "",
        "## 1. Evidentiary Ingestion & Admissibility Status",
    ]

    ev_items = data.get("evidence_items", [])
    if ev_items:
        lines.append(f"During this window, **{len(ev_items)}** new evidence exhibit(s) were submitted to the case locker:")
        lines.append("| Exhibit ID | Description / File | Type | Custodian | Integrity | Section 65B Certificate |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for item in ev_items:
            h_stat = "Verified SHA-256" if item["hash_verified"] else "Pending Verification"
            c_stat = "Present (Admissible)" if item["sec_65b_certified"] else "MISSING (Inadmissible)"
            lines.append(f"| #{item['id']} | `{item['file_name']}` | {item['evidence_type']} | {item['uploaded_by']} | {h_stat} | **{c_stat}** |")
    else:
        lines.append("*No new evidence exhibits uploaded in this window.*")

    lines.append("")
    lines.append("## 2. Hypothesis Ranking & Bayesian Scoring Movements")

    shift = data.get("scoring_shift", {})
    if shift.get("new_leader"):
        lead = shift["new_leader"]
        lines.append(f"- **Current Leading Hypothesis:** #{lead.get('id')} — **{lead.get('title')}** ({lead.get('score', 0):.1f}% combined support)")
        lines.append(f"- **Rank Separation Margin:** {shift.get('leader_margin', 0)}% margin over runner-up.")
        if shift.get("top_hypothesis_changed"):
            old = shift.get("old_leader", {})
            lines.append(f"- ⚠️ **Leadership Flip:** Overtook previous lead #{old.get('id')} ({old.get('title')}, {old.get('score', 0):.1f}%).")
    else:
        lines.append("*No scoring recalculations triggered during this period.*")

    lines.append("")
    lines.append("## 3. Human Analyst Overrides & Scientific Calibration")
    overrides = data.get("override_items", [])
    if overrides:
        lines.append(f"Recorded **{len(overrides)}** forensic analyst override(s) under human-in-the-loop sign-off:")
        for o in overrides:
            lines.append(f"- **{o['analyst']}** modified `{o['target_type']} #{o['target_id']}`: {o['description']}")
    else:
        lines.append("*Zero analyst overrides performed in this period. AI matrix classifications maintained.*")

    lines.append("")
    lines.append("## 4. Statutory Deadlines & Procedural Compliance")
    deadlines = data.get("deadlines_summary", [])
    if deadlines:
        for dl in deadlines:
            status_emoji = "🚨" if dl["days_remaining"] <= 3 else "⏳"
            lines.append(f"- {status_emoji} **{dl['title']}**: Due `{dl['due_date'][:10]}` (**{dl['days_remaining']} calendar days remaining**) — Status: `{dl['status'].upper()}`")
    else:
        lines.append("*No active statutory deadlines flagged for this case docket.*")

    lines.append("")
    lines.append("## 5. Personnel & Case Activity")
    users = data.get("active_investigators", [])
    if users:
        lines.append(f"Active investigators during this shift: {', '.join(users)}")
    else:
        lines.append("*Automated scheduled evaluation; no interactive user sessions.*")

    lines.append("")
    lines.append("---")
    lines.append("*This shift handover was factually generated from the cryptographic Merkle audit ledger.*")

    return "\n".join(lines)


# ==============================================================================
# GENERATE HANDOVER REPORT
# ==============================================================================

def generate_handover_report(
    case_id: int,
    db: Session,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    period_hours: int = 24,
    user: Optional[User] = None,
    generation_type: str = "manual"
) -> HandoverSummary:
    """
    Generates, audits, and persists a formal shift handover briefing document.
    """
    now = datetime.now(timezone.utc)
    if not end_time:
        end_time = now
    if not start_time:
        start_time = end_time - timedelta(hours=period_hours)

    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise ValueError(f"Case #{case_id} not found")

    is_reviewer = (user.role == "reviewer") if user else False
    user_name = user.full_name if user else "Automated System"

    # Extract deterministic data
    data = extract_case_activity_window(
        case_id=case_id,
        start_time=start_time,
        end_time=end_time,
        db=db,
        is_reviewer=is_reviewer
    )

    headline = generate_handover_headline(data)
    rendered_md = render_handover_markdown(case, headline, data, user_name)

    # Persist summary
    summary = HandoverSummary(
        case_id=case_id,
        period_start=start_time,
        period_end=end_time,
        headline=headline,
        structured_content=json.dumps(data),
        rendered_text=rendered_md,
        generated_by=user_name,
        generation_type=generation_type,
        created_at=now
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)

    # Log generation to Merkle audit ledger
    log_audit_event(
        db=db,
        action_type="HANDOVER_GENERATED",
        target_type="handover_summary",
        target_id=str(summary.id),
        description=f"Shift handover dossier #{summary.id} generated by {user_name} ({generation_type}). Headline: {headline}",
        case_id=case_id,
        user_id=user.id if user else None,
        user_name=user_name,
        user_role=user.role if user else "system",
        commit=True
    )

    return summary


# ==============================================================================
# "SINCE YOU WERE AWAY" DELTA SYNTHESIS
# ==============================================================================

def get_since_you_were_away(
    case_id: int,
    user: User,
    db: Session
) -> Dict[str, Any]:
    """
    Synthesizes what changed in the case since the user's last visit.
    Queries the UserCaseState table to get exact last_seen_at timestamp.
    """
    now = datetime.now(timezone.utc)

    # Retrieve or initialize user state
    state = db.query(UserCaseState).filter(
        UserCaseState.case_id == case_id,
        UserCaseState.user_id == user.id
    ).first()

    if not state or not state.last_seen_at:
        # First time opening or state missing: default to past 24 hours
        last_seen = now - timedelta(hours=24)
    else:
        last_seen = _ensure_utc(state.last_seen_at)
        # Avoid zero-duration comparisons if user just refreshed 5 seconds ago
        if (now - last_seen).total_seconds() < 60:
            last_seen = now - timedelta(hours=24)

    hours_away = round((now - last_seen).total_seconds() / 3600, 1)

    # Extract facts strictly in the absence window
    data = extract_case_activity_window(
        case_id=case_id,
        start_time=last_seen,
        end_time=now,
        db=db,
        is_reviewer=(user.role == "reviewer")
    )

    headline = generate_handover_headline(data)

    # Formulate 3-5 concise bullet points
    summary_points = []
    if data["new_evidence_count"] > 0:
        summary_points.append(f"{data['new_evidence_count']} new exhibit(s) uploaded and ingested into evidence locker.")
    if data["scoring_shift"].get("top_hypothesis_changed"):
        summary_points.append(f"Top hypothesis changed to #{data['scoring_shift']['new_leader']['id']} ('{data['scoring_shift']['new_leader']['title']}').")
    if data["overrides_count"] > 0:
        summary_points.append(f"{data['overrides_count']} human analyst override(s) signed off on evidentiary classifications.")
    if data["missing_cert_count"] > 0:
        summary_points.append(f"{data['missing_cert_count']} electronic exhibit(s) flagged for missing Section 65B certificates.")
    if data["active_alerts_count"] > 0:
        summary_points.append(f"{data['active_alerts_count']} actionable alert(s) pending review in case docket.")

    if not summary_points:
        summary_points.append("No material evidentiary or score changes occurred while you were away.")

    return {
        "case_id": case_id,
        "last_seen_at": last_seen.isoformat(),
        "headline": headline,
        "summary_sentence": headline,
        "hours_away": hours_away,
        "new_evidence_count": data["new_evidence_count"],
        "changed_hypotheses_count": 1 if data["scoring_shift"].get("top_hypothesis_changed") else 0,
        "overrides_count": data["overrides_count"],
        "open_tasks_count": data["open_tasks_count"],
        "unresolved_alerts_count": data["active_alerts_count"],
        "recent_active_users": data["active_investigators"],
        "summary_points": summary_points
    }


def update_user_case_last_seen(case_id: int, user_id: int, db: Session) -> None:
    """Updates the user's last_seen_at record upon opening or navigating the case."""
    now = datetime.now(timezone.utc)
    state = db.query(UserCaseState).filter(
        UserCaseState.case_id == case_id,
        UserCaseState.user_id == user_id
    ).first()

    if not state:
        state = UserCaseState(
            case_id=case_id,
            user_id=user_id,
            last_seen_at=now
        )
        db.add(state)
    else:
        state.last_seen_at = now

    db.commit()
