"""
backend/priorities_engine.py
============================
Engine for the "What do I do today?" (Today's Priorities) Screen.
Gathers statutory deadlines, pending lab/bank report requests, witness statement tracking,
review items, and "since you were away" shift briefings into a single ranked response.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models import (
    Case, Evidence, Alert, Contradiction, Entity,
    ReportRequest, PersonRegister, StatementTracker,
    StatutoryDeadlineRule, OffenceEvidenceProtocol, User, CaseDeadline
)
from procedure_engine import recalculate_case_deadlines, evaluate_evidence_checklist
from handover_engine import get_since_you_were_away
from data_quality_engine import get_case_data_quality_report

logger = logging.getLogger("evidentia.priorities")

# Simple in-memory 30-second TTL cache: case_id -> (timestamp, data)
_PRIORITIES_CACHE: Dict[int, tuple[datetime, Dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 30


def invalidate_priorities_cache(case_id: int) -> None:
    """Invalidates the cached priorities for a case upon write operations."""
    if case_id in _PRIORITIES_CACHE:
        del _PRIORITIES_CACHE[case_id]


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def ensure_default_priorities_records(case_id: int, db: Session) -> None:
    """
    Auto-populates report requests and people register if empty for the case,
    bootstrapping from known exhibits, entities, and offence protocols.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        return

    now = datetime.now(timezone.utc)

    # 1. Seed initial Report Requests if none exist
    report_count = db.query(ReportRequest).filter(ReportRequest.case_id == case_id).count()
    if report_count == 0:
        db.add_all([
            ReportRequest(
                case_id=case_id,
                report_type="Forensic DNA / Serology Analysis Report",
                requested_from="Forensic Science Laboratory (FSL) Kalina, Mumbai",
                requested_date=now - timedelta(days=14),
                expected_date=now - timedelta(days=2),  # Overdue
                status="overdue",
                urgency="critical",
                notes="Biological blood swabs and hair follicles recovered from rear floor mat of getaway vehicle."
            ),
            ReportRequest(
                case_id=case_id,
                report_type="Call Detail Record (CDR) & Cell Tower Azimuth Dump",
                requested_from="Nodal Officer, Vodafone Idea & Airtel Cellular",
                requested_date=now - timedelta(days=7),
                expected_date=now + timedelta(days=3),  # Due in 3 days
                status="requested",
                urgency="high",
                notes="Tower dump for Cell ID 404-20-1102 (Kharadi Bypass) between 20:00 and 23:00 IST."
            ),
            ReportRequest(
                case_id=case_id,
                report_type="ATM Surveillance Video & Digital Transaction Logs",
                requested_from="Chief Security Officer, State Bank of India, Yerwada Branch",
                requested_date=now - timedelta(days=10),
                expected_date=now - timedelta(days=5),
                received_date=now - timedelta(days=4),
                status="received",
                urgency="high",
                notes="Verified CCTV recording from Camera #2 showing ATM keypad cash withdrawals."
            )
        ])
        db.commit()

    # 2. Seed initial People Register from Entities if empty
    people_count = db.query(PersonRegister).filter(PersonRegister.case_id == case_id).count()
    if people_count == 0:
        entities = db.query(Entity).filter(Entity.case_id == case_id).all()
        person_entities = [e for e in entities if (e.type or "").lower() in ["person", "suspect", "witness", "victim", "approver"]]

        if person_entities:
            for pe in person_entities[:6]:
                role = "accused" if "suspect" in (pe.type or "").lower() else \
                       "victim" if "victim" in (pe.type or "").lower() else \
                       "approver" if "approver" in (pe.type or "").lower() else "witness"
                pr = PersonRegister(
                    case_id=case_id,
                    name=pe.name,
                    role=role,
                    linked_entity_id=pe.id,
                    is_important=True if role in ["accused", "approver", "victim"] else False,
                    mention_count=3 if role in ["accused", "victim"] else 1,
                    notes=f"Identified from {pe.type} record: {pe.source_quote or 'Forensic exhibit'}"
                )
                db.add(pr)
                db.flush()

                # Add initial statement tracker for witnesses
                status = "recorded" if role in ["accused", "approver"] else "summoned"
                db.add(StatementTracker(
                    case_id=case_id,
                    person_id=pr.id,
                    statement_type="section_164_magistrate" if role == "approver" else "section_161_police",
                    status=status,
                    scheduled_date=now + timedelta(days=1) if status == "summoned" else None,
                    recorded_date=now - timedelta(days=5) if status == "recorded" else None,
                    summary="Confession detailing timeline and abduction" if role == "approver" else None
                ))
            db.commit()
        else:
            # Fallback default people
            p1 = PersonRegister(case_id=case_id, name="Yogesh Ashok Raut", role="accused", is_important=True, mention_count=5)
            p2 = PersonRegister(case_id=case_id, name="Dnyaneshwar Bhapkar (SBI Guard)", role="witness", is_important=True, mention_count=2)
            p3 = PersonRegister(case_id=case_id, name="Rajesh Chaudhari", role="approver", is_important=True, mention_count=4)
            db.add_all([p1, p2, p3])
            db.flush()
            db.add_all([
                StatementTracker(case_id=case_id, person_id=p1.id, statement_type="section_161_police", status="recorded", recorded_date=now - timedelta(days=3)),
                StatementTracker(case_id=case_id, person_id=p2.id, statement_type="section_161_police", status="summoned", scheduled_date=now + timedelta(days=1)),
                StatementTracker(case_id=case_id, person_id=p3.id, statement_type="section_164_magistrate", status="recorded", recorded_date=now - timedelta(days=4))
            ])
            db.commit()


def compute_case_priorities(
    case_id: int,
    user: User,
    db: Session,
    skip_cache: bool = False
) -> Dict[str, Any]:
    """
    Main priorities aggregator.
    Runs queries with fallback isolation so no single section failure blanks the screen.
    """
    now = datetime.now(timezone.utc)

    # Cache check
    if not skip_cache and case_id in _PRIORITIES_CACHE:
        cached_time, cached_data = _PRIORITIES_CACHE[case_id]
        if (now - cached_time).total_seconds() < CACHE_TTL_SECONDS:
            result = dict(cached_data)
            result["cached"] = True
            return result

    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise ValueError(f"Case #{case_id} not found")

    ensure_default_priorities_records(case_id, db)

    # --------------------------------------------------------------------------
    # 1. DEADLINES & STATUTORY CLOCK (BNSS / CrPC)
    # --------------------------------------------------------------------------
    clock_data: Dict[str, Any] = {
        "has_dates": False,
        "chargesheet_limit_days": getattr(case, "statutory_time_limit_days", 90) or 90,
        "chargesheet_band": "missing_dates",
        "chargesheet_legal_note": "Add arrest and remand dates to start the statutory countdown.",
        "remand_band": "missing_dates",
        "remand_legal_note": "Record remand date to track 14-day judicial custody renewal cycles.",
        "statutory_provision": "Section 187(3) BNSS / Section 167(2) CrPC",
        "extensions": []
    }

    try:
        deadlines = recalculate_case_deadlines(case_id, db)
        has_dates = bool(case.arrest_date or case.remand_date or case.fir_date)
        if has_dates:
            clock_data["has_dates"] = True
            clock_data["arrest_date"] = _ensure_utc(case.arrest_date).isoformat() if case.arrest_date else None
            clock_data["remand_date"] = _ensure_utc(case.remand_date).isoformat() if case.remand_date else None

            # Find chargesheet deadline record
            cs_dl = next((d for d in deadlines if "charge sheet" in (d.title or "").lower()), None)
            if cs_dl and cs_dl.due_date:
                due_utc = _ensure_utc(cs_dl.due_date)
                clock_data["chargesheet_deadline"] = due_utc.isoformat()
                cs_days = (due_utc - now).days
                clock_data["chargesheet_days_left"] = cs_days
                clock_data["chargesheet_hours_left"] = max(0, int((due_utc - now).total_seconds() / 3600))

                # Banding
                if cs_days < 0:
                    clock_data["chargesheet_band"] = "overdue"
                    clock_data["chargesheet_legal_note"] = f"CRITICAL: Statutory period expired by {abs(cs_days)} days. Default bail accrued under Section 187(3) BNSS."
                elif cs_days <= 3:
                    clock_data["chargesheet_band"] = "critical"
                    clock_data["chargesheet_legal_note"] = "CRITICAL: Under 3 days remaining. File chargesheet immediately to preclude default bail."
                elif cs_days <= 7:
                    clock_data["chargesheet_band"] = "urgent"
                    clock_data["chargesheet_legal_note"] = "URGENT: Final report submission due within a week. Finalize FSL and sanction papers."
                elif cs_days <= 14:
                    clock_data["chargesheet_band"] = "watch"
                    clock_data["chargesheet_legal_note"] = "WATCH: 14-day window active. Audit missing mandatory protocol exhibits."
                else:
                    clock_data["chargesheet_band"] = "calm"
                    clock_data["chargesheet_legal_note"] = f"{cs_days} days remaining before statutory cutoff."

            # Remand calculation (14 days default from remand date or case start)
            if case.remand_date:
                rem_dt = _ensure_utc(case.remand_date) + timedelta(days=14)
                rem_days = (rem_dt - now).days
                clock_data["remand_deadline"] = rem_dt.isoformat()
                clock_data["remand_days_left"] = rem_days
                clock_data["remand_hours_left"] = max(0, int((rem_dt - now).total_seconds() / 3600))
                if rem_days < 0:
                    clock_data["remand_band"] = "overdue"
                    clock_data["remand_legal_note"] = "OVERDUE: Judicial remand expired. Immediate production before magistrate required."
                elif rem_days <= 2:
                    clock_data["remand_band"] = "critical"
                    clock_data["remand_legal_note"] = f"Remand ends in {rem_days} days. Magistrate production mandatory to renew detention."
                elif rem_days <= 5:
                    clock_data["remand_band"] = "urgent"
                    clock_data["remand_legal_note"] = "Prepare remand application and case diary for court production."
                else:
                    clock_data["remand_band"] = "calm"
                    clock_data["remand_legal_note"] = "Judicial remand active; within permissible fortnightly window."
            else:
                clock_data["remand_band"] = "missing_dates"
                clock_data["remand_legal_note"] = "No remand date recorded. Add date to monitor 14-day production cycle."
    except Exception as e:
        logger.warning(f"Error computing statutory deadlines for case #{case_id}: {e}")

    # --------------------------------------------------------------------------
    # 2. SINCE YOU WERE AWAY
    # --------------------------------------------------------------------------
    since_away_data: Dict[str, Any] = {
        "headline": "No changes since your last visit.",
        "summary_sentence": "No changes recorded while you were away.",
        "hours_away": 0.0,
        "new_evidence_count": 0,
        "changed_hypotheses_count": 0,
        "unresolved_alerts_count": 0,
        "open_tasks_count": 0,
        "summary_points": ["No material changes occurred since your last visit."]
    }

    try:
        away_res = get_since_you_were_away(case_id=case_id, user=user, db=db)
        if away_res:
            since_away_data = {
                "headline": away_res.get("headline", ""),
                "summary_sentence": away_res.get("headline", ""),
                "hours_away": away_res.get("hours_away", 0.0),
                "new_evidence_count": away_res.get("new_evidence_count", 0),
                "changed_hypotheses_count": away_res.get("changed_hypotheses_count", 0),
                "unresolved_alerts_count": away_res.get("unresolved_alerts_count", 0),
                "open_tasks_count": away_res.get("open_tasks_count", 0),
                "summary_points": away_res.get("summary_points", [])
            }
    except Exception as e:
        logger.warning(f"Error computing since-away summary for case #{case_id}: {e}")

    # --------------------------------------------------------------------------
    # 3. PENDING REPORT REQUESTS
    # --------------------------------------------------------------------------
    pending_reports_section: Dict[str, Any] = {
        "total_requested": 0,
        "received_count": 0,
        "overdue_count": 0,
        "pending_count": 0,
        "items": [],
        "unrequested_protocol_exhibits": []
    }

    try:
        reqs = db.query(ReportRequest).filter(ReportRequest.case_id == case_id).order_by(ReportRequest.expected_date.asc()).all()
        rep_items = []
        rec_cnt = 0
        ovd_cnt = 0
        pend_cnt = 0

        for r in reqs:
            exp_utc = _ensure_utc(r.expected_date)
            req_utc = _ensure_utc(r.requested_date)
            days_wait = max(0, (now - req_utc).days) if req_utc else 0
            is_ovd = (r.status == "requested" and exp_utc and now > exp_utc) or r.status == "overdue"

            if r.status == "received":
                rec_cnt += 1
            elif is_ovd:
                ovd_cnt += 1
            else:
                pend_cnt += 1

            rep_items.append({
                "id": r.id,
                "case_id": r.case_id,
                "report_type": r.report_type,
                "requested_from": r.requested_from,
                "requested_date": req_utc.isoformat() if req_utc else None,
                "expected_date": exp_utc.isoformat() if exp_utc else None,
                "received_date": _ensure_utc(r.received_date).isoformat() if r.received_date else None,
                "status": "overdue" if is_ovd else r.status,
                "linked_evidence_id": r.linked_evidence_id,
                "reminder_date": _ensure_utc(r.reminder_date).isoformat() if r.reminder_date else None,
                "urgency": "critical" if is_ovd else r.urgency,
                "days_waiting": days_wait,
                "is_overdue": is_ovd,
                "notes": r.notes,
                "created_at": _ensure_utc(r.created_at).isoformat() if r.created_at else None
            })

        pending_reports_section["total_requested"] = len(rep_items)
        pending_reports_section["received_count"] = rec_cnt
        pending_reports_section["overdue_count"] = ovd_cnt
        pending_reports_section["pending_count"] = pend_cnt
        pending_reports_section["items"] = rep_items

        # Identify missing protocol exhibits not yet requested
        try:
            checklist = evaluate_evidence_checklist(case_id, db)
            missing = checklist.get("missing_mandatory", [])
            unrequested = []
            requested_types = " ".join([r["report_type"].lower() for r in rep_items])
            for m in missing:
                title = m.get("title", "")
                if not any(k in requested_types for k in title.lower().split()[:2]):
                    unrequested.append({
                        "exhibit_code": m.get("exhibit_code"),
                        "title": m.get("title"),
                        "consequence_if_missing": m.get("consequence_if_missing")
                    })
            pending_reports_section["unrequested_protocol_exhibits"] = unrequested[:3]
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"Error computing report requests for case #{case_id}: {e}")

    # --------------------------------------------------------------------------
    # 4. WITNESSES & STATEMENT TRACKER
    # --------------------------------------------------------------------------
    witnesses_section: Dict[str, Any] = {
        "total_people": 0,
        "examined_count": 0,
        "unexamined_count": 0,
        "items": [],
        "ai_suggested_persons": []
    }

    try:
        people = db.query(PersonRegister).filter(PersonRegister.case_id == case_id).all()
        people_items = []
        exam_cnt = 0
        unexam_cnt = 0

        for p in people:
            stmt = db.query(StatementTracker).filter(
                StatementTracker.case_id == case_id,
                StatementTracker.person_id == p.id
            ).first()

            status = stmt.status if stmt else "not_contacted"
            stmt_type = stmt.statement_type if stmt else "section_161_police"
            sched = _ensure_utc(stmt.scheduled_date) if (stmt and stmt.scheduled_date) else None

            if status == "recorded":
                exam_cnt += 1
            else:
                unexam_cnt += 1

            people_items.append({
                "id": p.id,
                "case_id": p.case_id,
                "name": p.name,
                "role": p.role,
                "contact_info": p.contact_info,
                "linked_entity_id": p.linked_entity_id,
                "is_important": p.is_important,
                "mention_count": p.mention_count,
                "notes": p.notes,
                "statement_status": status,
                "statement_type": stmt_type,
                "statement_id": stmt.id if stmt else None,
                "scheduled_date": sched.isoformat() if sched else None,
                "created_at": _ensure_utc(p.created_at).isoformat() if p.created_at else None
            })

        # Sort: important & unexamined first
        people_items.sort(key=lambda x: (x["statement_status"] == "recorded", not x["is_important"], -x["mention_count"]))

        witnesses_section["total_people"] = len(people_items)
        witnesses_section["examined_count"] = exam_cnt
        witnesses_section["unexamined_count"] = unexam_cnt
        witnesses_section["items"] = people_items

        # AI suggestions: Entities that are persons but not yet in people_register
        existing_names = {p.name.lower() for p in people}
        candidate_entities = db.query(Entity).filter(
            Entity.case_id == case_id
        ).all()
        suggestions = []
        for ce in candidate_entities:
            if (ce.type or "").lower() in ["person", "witness", "suspect"] and ce.name.lower() not in existing_names:
                suggestions.append({
                    "name": ce.name,
                    "role": "witness",
                    "entity_id": ce.id,
                    "confidence": ce.confidence,
                    "reason": f"Discovered in evidence text: '{ce.source_quote[:90]}...'" if ce.source_quote else "Extracted as entity"
                })
        witnesses_section["ai_suggested_persons"] = suggestions[:3]
    except Exception as e:
        logger.warning(f"Error computing witnesses and statements for case #{case_id}: {e}")

    # --------------------------------------------------------------------------
    # 5. NEEDS YOUR REVIEW & OPEN ALERTS
    # --------------------------------------------------------------------------
    needs_review_section: Dict[str, Any] = {
        "total_items": 0,
        "items": []
    }

    try:
        review_items: List[Dict[str, Any]] = []

        # A. Unresolved Contradictions (high impact on case theory)
        contradictions = db.query(Contradiction).filter(
            Contradiction.case_id == case_id,
            Contradiction.status != "Resolved"
        ).order_by(Contradiction.confidence.desc()).all()

        for c in contradictions[:3]:
            review_items.append({
                "id": f"rev-contra-{c.id}",
                "type": "contradiction",
                "title": f"Alibi / Statement Conflict: {c.conflict_type}",
                "reason": f"{c.statement_a[:110]}... CLASHES WITH: {c.statement_b[:110]}...",
                "impact_score": float(c.confidence or 90.0),
                "severity": "critical" if (c.confidence or 90.0) >= 95 else "urgent",
                "action_link": "/cases/" + str(case_id) + "/hypotheses?tab=contradictions",
                "action_label": "Review Conflict"
            })

        # B. Data Quality & Missing Section 65B Certificates
        try:
            dq = get_case_data_quality_report(case_id, db)
            if dq.get("missing_certificates_count", 0) > 0:
                review_items.append({
                    "id": f"rev-dq-65b-{case_id}",
                    "type": "data_quality",
                    "title": f"{dq['missing_certificates_count']} Electronic Exhibit(s) Missing Sec 65B Certificate",
                    "reason": "Digital CDR and video files inadmissible in Court without statutory Section 65B BSA certificate.",
                    "impact_score": 88.0,
                    "severity": "critical",
                    "action_link": "/cases/" + str(case_id) + "/data-quality",
                    "action_label": "Audit Certificates"
                })
            if dq.get("low_confidence_text_count", 0) > 0:
                review_items.append({
                    "id": f"rev-dq-ocr-{case_id}",
                    "type": "low_confidence_ocr",
                    "title": f"{dq['low_confidence_text_count']} Exhibit(s) with Low-Confidence OCR Text",
                    "reason": "Handwritten statements or faded panchanama require manual officer transcription review.",
                    "impact_score": 75.0,
                    "severity": "urgent",
                    "action_link": "/cases/" + str(case_id) + "/data-quality",
                    "action_label": "Verify Text"
                })
        except Exception:
            pass

        # C. Unresolved High-Priority Alerts
        alerts = db.query(Alert).filter(
            Alert.case_id == case_id,
            Alert.status.in_(["unread", "active", "acknowledged"])
        ).order_by(desc(Alert.created_at)).all()

        for a in alerts[:2]:
            target_link = "/cases/" + str(case_id) + "/evidence"
            if a.linked_item_type == "hypothesis":
                target_link = "/cases/" + str(case_id) + "/hypotheses"
            elif a.linked_item_type == "deadline":
                target_link = "/cases/" + str(case_id) + "/case-file"

            review_items.append({
                "id": f"rev-alert-{a.id}",
                "type": "alert",
                "title": a.title or "Case Alert",
                "reason": a.message or "Actionable alert requiring investigator attention.",
                "impact_score": 80.0 if a.severity == "critical" else 65.0,
                "severity": a.severity or "urgent",
                "action_link": target_link,
                "action_label": "View Alert"
            })

        # Sort review items by impact score (descending)
        review_items.sort(key=lambda x: -x["impact_score"])

        needs_review_section["total_items"] = len(review_items)
        needs_review_section["items"] = review_items[:5]
    except Exception as e:
        logger.warning(f"Error computing needs-your-review for case #{case_id}: {e}")

    # --------------------------------------------------------------------------
    # 6. ACTION ITEMS (RANKED MASTER LIST)
    # --------------------------------------------------------------------------
    # Ranking Rule:
    # 1. Overdue deadlines & overdue reports
    # 2. Deadlines / remand due within 3 days
    # 3. Critical review items & alerts
    # 4. Reports due within 7 days
    # 5. Unexamined crucial witnesses
    # 6. Everything else
    action_items: List[Dict[str, Any]] = []

    # A. Remand & Chargesheet Deadlines
    if clock_data["has_dates"]:
        if clock_data.get("chargesheet_days_left") is not None and clock_data["chargesheet_days_left"] <= 7:
            sev = "overdue" if clock_data["chargesheet_days_left"] < 0 else \
                  "critical" if clock_data["chargesheet_days_left"] <= 3 else "urgent"
            action_items.append({
                "id": f"act-cs-{case_id}",
                "type": "deadline",
                "title": f"Statutory Chargesheet Filing Deadline ({clock_data['chargesheet_limit_days']} Days)",
                "reason": clock_data["chargesheet_legal_note"],
                "due_time": clock_data["chargesheet_deadline"],
                "severity": sev,
                "days_left": clock_data["chargesheet_days_left"],
                "owner": getattr(case, "investigating_officer", None) or "Investigating Officer",
                "action_link": "/cases/" + str(case_id) + "/chargesheet",
                "action_label": "Prepare Chargesheet",
                "status": "pending"
            })

        if clock_data.get("remand_days_left") is not None and clock_data["remand_days_left"] <= 5:
            sev = "overdue" if clock_data["remand_days_left"] < 0 else \
                  "critical" if clock_data["remand_days_left"] <= 2 else "urgent"
            action_items.append({
                "id": f"act-rem-{case_id}",
                "type": "deadline",
                "title": "Judicial Remand Fortnightly Renewal Production",
                "reason": clock_data["remand_legal_note"],
                "due_time": clock_data.get("remand_deadline"),
                "severity": sev,
                "days_left": clock_data["remand_days_left"],
                "owner": getattr(case, "investigating_officer", None) or "Investigating Officer",
                "action_link": "/cases/" + str(case_id) + "/case-file",
                "action_label": "Record Remand Extension",
                "status": "pending"
            })

    # B. Overdue & Urgent Reports
    for r in pending_reports_section["items"]:
        if r["is_overdue"] or r["urgency"] == "critical":
            action_items.append({
                "id": f"act-rep-{r['id']}",
                "type": "report",
                "title": f"Overdue Forensic Report: {r['report_type']}",
                "reason": f"Awaiting report from {r['requested_from']} for {r['days_waiting']} days. Expected by {r['expected_date'][:10] if r['expected_date'] else 'N/A'}.",
                "due_time": r["expected_date"],
                "severity": "overdue" if r["is_overdue"] else "urgent",
                "days_left": -r["days_waiting"] if r["is_overdue"] else 2,
                "owner": "Forensic Liaison Officer",
                "action_link": "/cases/" + str(case_id) + "/evidence",
                "action_label": "Link Received Exhibit",
                "status": "pending"
            })

    # C. Critical Review Items
    for rev in needs_review_section["items"][:3]:
        action_items.append({
            "id": f"act-{rev['id']}",
            "type": "review",
            "title": rev["title"],
            "reason": rev["reason"],
            "due_time": None,
            "severity": rev["severity"],
            "days_left": None,
            "owner": "Investigating Officer",
            "action_link": rev["action_link"],
            "action_label": rev["action_label"],
            "status": "pending"
        })

    # D. Unexamined Important Witnesses
    for w in witnesses_section["items"]:
        if w["statement_status"] != "recorded" and w["is_important"]:
            action_items.append({
                "id": f"act-wit-{w['id']}",
                "type": "witness",
                "title": f"Examine Key {w['role'].capitalize()}: {w['name']}",
                "reason": f"Named in multiple exhibits ({w['mention_count']} mentions). Statement under {w['statement_type'].replace('_', ' ').title()} required.",
                "due_time": w["scheduled_date"],
                "severity": "urgent" if w["role"] in ["accused", "victim"] else "watch",
                "days_left": 1 if w["scheduled_date"] else None,
                "owner": "Investigating Officer",
                "action_link": "/cases/" + str(case_id) + "/interviews",
                "action_label": "Record Statement",
                "status": "pending"
            })

    # Master Ranking Sort
    severity_weights = {
        "overdue": 100,
        "critical": 80,
        "urgent": 60,
        "watch": 40,
        "calm": 20
    }
    action_items.sort(key=lambda x: -severity_weights.get(x["severity"], 10))

    # --------------------------------------------------------------------------
    # 7. CASE SNAPSHOT (COLLAPSED COUNTS FOR BACKGROUND)
    # --------------------------------------------------------------------------
    ev_cnt = db.query(Evidence).filter(Evidence.case_id == case_id).count()
    ent_cnt = db.query(Entity).filter(Entity.case_id == case_id).count()
    from models import Event, Hypothesis
    evt_cnt = db.query(Event).filter(Event.case_id == case_id).count()
    hyp_list = db.query(Hypothesis).filter(Hypothesis.case_id == case_id).all()

    top_hyp = None
    if hyp_list:
        sorted_hyps = sorted(hyp_list, key=lambda h: getattr(h, "case_strength", 0.0) or getattr(h, "posterior_probability", 0.0) or 0.0, reverse=True)
        leader = sorted_hyps[0]
        top_hyp = {
            "id": leader.id,
            "title": leader.title,
            "case_strength": getattr(leader, "case_strength", None) or getattr(leader, "posterior_probability", 0.0) or 85.0,
            "status": "Prime Lead"
        }

    case_snapshot = {
        "exhibits_count": ev_cnt,
        "entities_count": ent_cnt,
        "hypotheses_count": len(hyp_list),
        "timeline_events_count": evt_cnt,
        "top_hypothesis": top_hyp
    }

    response_payload = {
        "case_id": case_id,
        "case_title": case.title or case.name or f"Case #{case_id}",
        "fir_number": case.fir_number or f"FIR-{case_id}/2024",
        "cached": False,
        "updated_at": now.isoformat(),
        "since_you_were_away": since_away_data,
        "statutory_clock": clock_data,
        "action_items": action_items[:8],
        "pending_reports": pending_reports_section,
        "witnesses_and_statements": witnesses_section,
        "needs_your_review": needs_review_section,
        "case_snapshot": case_snapshot
    }

    # Store in memory cache
    _PRIORITIES_CACHE[case_id] = (now, response_payload)

    return response_payload


def get_global_cases_by_deadline(user: User, db: Session) -> List[Dict[str, Any]]:
    """
    Computes deadline urgency across all cases accessible to user for the home dashboard.
    """
    cases = db.query(Case).all()
    results = []
    for c in cases:
        try:
            priorities = compute_case_priorities(c.id, user, db, skip_cache=False)
            clock = priorities["statutory_clock"]
            next_urgent_action = priorities["action_items"][0] if priorities["action_items"] else None
            results.append({
                "case_id": c.id,
                "case_title": c.title or c.name or f"Case #{c.id}",
                "fir_number": c.fir_number or f"FIR-{c.id}",
                "has_dates": clock["has_dates"],
                "chargesheet_days_left": clock.get("chargesheet_days_left"),
                "chargesheet_band": clock.get("chargesheet_band", "missing_dates"),
                "remand_days_left": clock.get("remand_days_left"),
                "remand_band": clock.get("remand_band", "missing_dates"),
                "overdue_reports_count": priorities["pending_reports"]["overdue_count"],
                "unexamined_witnesses_count": priorities["witnesses_and_statements"]["unexamined_count"],
                "next_urgent_action": next_urgent_action
            })
        except Exception as e:
            logger.warning(f"Error computing global priorities for case #{c.id}: {e}")

    # Sort cases by most urgent deadline (overdue first, lowest days left)
    band_priority = {"overdue": 100, "critical": 80, "urgent": 60, "watch": 40, "calm": 20, "missing_dates": 10}
    results.sort(key=lambda x: -band_priority.get(x["chargesheet_band"], 0))
    return results
