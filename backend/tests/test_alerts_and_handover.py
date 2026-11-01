import pytest
import json
from datetime import datetime, timezone, timedelta
from models import (
    Case, CaseMember, Hypothesis, Evidence, AuditLog,
    Alert, AlertRuleConfig, StatutoryDeadlineRule, CaseDeadline,
    UserCaseState, HandoverSummary, ScoringRun
)
from audit_engine import log_audit_event
from alerts_engine import (
    ensure_statutory_rules,
    check_top_hypothesis_rule,
    check_integrity_failure_rule,
    check_missing_certificate_rule,
    check_statutory_deadlines,
    acknowledge_alert,
    snooze_alert,
    resolve_alert_manually,
    get_case_alerts,
    auto_resolve_alert,
)
from handover_engine import (
    generate_handover_report,
    get_since_you_were_away,
    update_user_case_last_seen,
)


@pytest.fixture
def alert_test_case(db, seed_users):
    c = Case(
        title="Alert & Handover Test Case",
        description="Testing automated alerts and shift handover summaries",
        created_by="Lead Investigator",
        status="active",
        fir_number="FIR-2026/884",
        fir_date=datetime.now(timezone.utc) - timedelta(days=20),
        incident_date=datetime.now(timezone.utc) - timedelta(days=25),
        arrest_date=datetime.now(timezone.utc) - timedelta(days=15),
        remand_date=datetime.now(timezone.utc) - timedelta(days=5),
        offence_section="Section 302 IPC / Section 103 BNS",
        statutory_time_limit_days=90,
        version=1,
    )
    db.add(c)
    db.commit()
    db.refresh(c)

    for role_key in ["admin", "lead_investigator", "analyst", "reviewer"]:
        u = seed_users[role_key]
        m = CaseMember(case_id=c.id, user_id=u.id, case_role=u.role, added_by="Setup")
        db.add(m)
    db.commit()
    return c


@pytest.fixture
def hypotheses_pair(db, alert_test_case):
    h1 = Hypothesis(
        case_id=alert_test_case.id,
        title="Suspect A Committed The Crime",
        description="Forensic evidence points to A",
        support_score=60.0,
        combined_score=60.0,
        status="active",
        version=1,
    )
    h2 = Hypothesis(
        case_id=alert_test_case.id,
        title="Suspect B Committed The Crime",
        description="Financial motive points to B",
        support_score=40.0,
        combined_score=40.0,
        status="active",
        version=1,
    )
    db.add_all([h1, h2])
    db.commit()
    db.refresh(h1)
    db.refresh(h2)
    return h1, h2


def test_top_hypothesis_alert_and_rank_gap(db, alert_test_case, hypotheses_pair):
    h1, h2 = hypotheses_pair

    # Run 1: h1 leading (60% vs 40%)
    run1 = ScoringRun(
        case_id=alert_test_case.id,
        run_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        results_snapshot=json.dumps({
            "hypotheses": [
                {"id": h1.id, "title": h1.title, "combined_score": 60.0},
                {"id": h2.id, "title": h2.title, "combined_score": 40.0},
            ]
        })
    )
    db.add(run1)
    db.commit()

    # Run 2: h2 flips to lead (55% vs 45%)
    run2 = ScoringRun(
        case_id=alert_test_case.id,
        run_at=datetime.now(timezone.utc),
        results_snapshot=json.dumps({
            "hypotheses": [
                {"id": h2.id, "title": h2.title, "combined_score": 55.0},
                {"id": h1.id, "title": h1.title, "combined_score": 45.0},
            ]
        })
    )
    db.add(run2)
    db.commit()

    alerts = check_top_hypothesis_rule(
        case_id=alert_test_case.id,
        db=db,
        triggered_by="New ballistic exhibit EX-003 added"
    )

    assert len(alerts) >= 1
    leader_alert = next(a for a in alerts if a.rule_type == "top_hypothesis_changed")
    assert leader_alert.severity == "warning"
    assert "Suspect B" in leader_alert.title
    assert "Suspect B" in leader_alert.message
    assert leader_alert.linked_item_type == "hypothesis"
    assert leader_alert.linked_item_id == str(h2.id)

    # Deduplication test: Running again with same leading pair does not create duplicate
    dup_alerts = check_top_hypothesis_rule(
        case_id=alert_test_case.id,
        db=db,
        triggered_by="Duplicate run"
    )
    assert dup_alerts[0].id == leader_alert.id
    count = db.query(Alert).filter(Alert.case_id == alert_test_case.id, Alert.rule_type == "top_hypothesis_changed").count()
    assert count == 1

    # Run 3: Narrow gap (< 5%)
    run3 = ScoringRun(
        case_id=alert_test_case.id,
        run_at=datetime.now(timezone.utc),
        results_snapshot=json.dumps({
            "hypotheses": [
                {"id": h2.id, "title": h2.title, "combined_score": 51.0},
                {"id": h1.id, "title": h1.title, "combined_score": 49.0},
            ]
        })
    )
    db.add(run3)
    db.commit()
    gap_alerts = check_top_hypothesis_rule(case_id=alert_test_case.id, db=db, triggered_by="Analyst override")
    assert any(a.rule_type == "rank_gap_narrow" for a in gap_alerts)


def test_integrity_failure_alert_and_autoresolve(db, alert_test_case):
    ev = Evidence(
        case_id=alert_test_case.id,
        file_name="store_cctv.mp4",
        file_type="video/mp4",
        evidence_type="cctv",
        source="CCTV DVR",
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        sec_65b_certificate_present=True,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    alert = check_integrity_failure_rule(
        case_id=alert_test_case.id,
        db=db,
        exhibit_id=ev.id,
        error_detail="Calculated SHA-256 did not match recorded custody hash for store_cctv.mp4."
    )
    assert alert is not None
    assert alert.severity == "critical"
    assert alert.rule_type == "integrity_failure"
    assert alert.status == "unread"

    # Check auto-resolve when verification passes
    resolved = auto_resolve_alert(
        db=db,
        case_id=alert_test_case.id,
        dedup_key=alert.dedup_key,
        resolution_reason="Re-verified SHA-256 against primary archive: matches perfectly."
    )
    assert resolved is not None
    assert resolved.status == "resolved"
    assert "Re-verified" in resolved.resolution_reason


def test_missing_sec65b_certificate_alert(db, alert_test_case):
    # Electronic evidence without certificate
    ev = Evidence(
        case_id=alert_test_case.id,
        file_name="telecom_cdr_dump.csv",
        file_type="text/csv",
        evidence_type="cdr",
        source="Telecom Service Provider",
        sec_65b_certificate_present=False,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    alert = check_missing_certificate_rule(case_id=alert_test_case.id, exhibit_id=ev.id, db=db)
    assert alert is not None
    assert alert.rule_type == "missing_certificate"
    assert alert.severity == "warning"
    assert alert.status == "unread"
    assert "Section 65B" in alert.message or "Section 63" in alert.message

    # Auto-resolve when certificate is added
    ev.sec_65b_certificate_present = True
    db.commit()
    resolved = check_missing_certificate_rule(case_id=alert_test_case.id, exhibit_id=ev.id, db=db)
    assert resolved is None

    db.refresh(alert)
    assert alert.status == "resolved"


def test_statutory_deadline_approaching_and_extend(db, alert_test_case, seed_users):
    ensure_statutory_rules(db)

    # Deadline expiring in 3 days
    dl = CaseDeadline(
        case_id=alert_test_case.id,
        title="Statutory Charge Sheet Filing",
        due_date=datetime.now(timezone.utc) + timedelta(days=3, hours=1),
        status="pending",
    )
    db.add(dl)
    db.commit()
    db.refresh(dl)

    created_alerts = check_statutory_deadlines(case_id=alert_test_case.id, db=db)
    assert len(created_alerts) >= 1
    charge_alert = next(a for a in created_alerts if a.linked_item_id == str(dl.id))
    assert charge_alert.severity == "critical"  # <= 3 days is critical
    assert "3 Day" in charge_alert.title or "3 day" in charge_alert.title.lower()

    # Lead extends deadline
    dl.extended_until = dl.due_date + timedelta(days=14)
    dl.status = "extended"
    dl.extension_reason = "Extension granted by Sessions Court Order No. 44."
    db.commit()
    assert dl.status == "extended"


def test_alert_acknowledge_and_snooze(db, alert_test_case, seed_users):
    alert = Alert(
        case_id=alert_test_case.id,
        rule_type="gap_unresolved",
        severity="warning",
        title="Forensic ballistic timeline gap",
        message="Witness statement conflicts with ballistic trajectory window.",
        dedup_key=f"gap_{alert_test_case.id}_1",
        status="unread",
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    analyst = seed_users["analyst"]

    # 1. Acknowledge
    ack_res = acknowledge_alert(alert_id=alert.id, user=analyst, db=db, note="Investigating ballistic timeline now.")
    assert ack_res.status == "acknowledged"
    assert ack_res.acknowledged_by == analyst.full_name
    assert ack_res.acknowledged_at is not None

    # Check audit log written
    audit = db.query(AuditLog).filter(
        AuditLog.case_id == alert_test_case.id,
        AuditLog.action_type == "ALERT_ACKNOWLEDGED"
    ).first()
    assert audit is not None

    # 2. Snooze for 4 hours
    snooze_res = snooze_alert(alert_id=alert.id, hours=4, user=analyst, db=db)
    assert snooze_res.snoozed_until is not None

    # Check snooze filter: in get_case_alerts it should be excluded
    active_alerts = get_case_alerts(case_id=alert_test_case.id, user=analyst, db=db)
    assert not any(a["id"] == alert.id for a in active_alerts)

    # 3. Resolve manually
    res = resolve_alert_manually(alert_id=alert.id, reason="Ballistics reconciled with CCTV timecode.", user=analyst, db=db)
    assert res.status == "resolved"


def test_reviewer_privacy_redaction_for_alerts(db, alert_test_case, seed_users):
    alert = Alert(
        case_id=alert_test_case.id,
        rule_type="prior_record_warning",
        severity="info",
        title="Prior Conviction Match: Suspect Raut has 2 prior narcotics offenses",
        message="State Criminal Database confirms prior convictions under NDPS Act for suspect Raut.",
        linked_item_type="prior_record",
        linked_item_id="12",
        dedup_key=f"prior_{alert_test_case.id}_12",
        status="unread",
        is_restricted=True,
    )
    db.add(alert)
    db.commit()

    analyst = seed_users["analyst"]
    reviewer = seed_users["reviewer"]

    # Analyst sees full text
    analyst_alerts = get_case_alerts(case_id=alert_test_case.id, user=analyst, db=db)
    matched_analyst = next(a for a in analyst_alerts if a["id"] == alert.id)
    assert "Suspect Raut" in matched_analyst["title"]

    # Reviewer sees sanitized/redacted text
    reviewer_alerts = get_case_alerts(case_id=alert_test_case.id, user=reviewer, db=db)
    matched_reviewer = next(a for a in reviewer_alerts if a["id"] == alert.id)
    assert "Restricted Case Finding Alert" in matched_reviewer["title"]
    assert "protected record requires review" in matched_reviewer["message"]


def test_shift_handover_report_generation(db, alert_test_case, seed_users, hypotheses_pair):
    h1, h2 = hypotheses_pair
    analyst = seed_users["analyst"]

    ev = Evidence(
        case_id=alert_test_case.id,
        file_name="fingerprint_lift.png",
        file_type="image/png",
        evidence_type="physical",
        source="Crime Scene Investigation Unit",
        upload_date=datetime.now(timezone.utc),
    )
    db.add(ev)

    al = Alert(
        case_id=alert_test_case.id,
        rule_type="missing_certificate",
        severity="warning",
        title="Missing Section 65B Certificate",
        message="1 exhibit requires certification.",
        dedup_key="demo_cert_dedup",
        status="unread",
        created_at=datetime.now(timezone.utc),
    )
    db.add(al)

    log_audit_event(
        db=db,
        action_type="EXHIBIT_ADDED",
        target_type="evidence",
        target_id="1",
        description="Exhibit fingerprint_lift.png added to evidence locker.",
        case_id=alert_test_case.id,
        user_id=analyst.id,
        user_name=analyst.full_name,
        user_role=analyst.role,
        commit=True,
    )

    summary = generate_handover_report(
        case_id=alert_test_case.id,
        db=db,
        period_hours=24,
        user=analyst,
        generation_type="manual"
    )

    assert summary is not None
    assert summary.headline != ""
    assert "fingerprint" in summary.rendered_text.lower()
    assert summary.generated_by == analyst.full_name

    saved = db.query(HandoverSummary).filter(HandoverSummary.id == summary.id).first()
    assert saved is not None


def test_since_you_were_away_view(db, alert_test_case, seed_users):
    lead = seed_users["lead_investigator"]
    analyst = seed_users["analyst"]

    past_time = datetime.now(timezone.utc) - timedelta(hours=6)
    state = UserCaseState(
        user_id=lead.id,
        case_id=alert_test_case.id,
        last_seen_at=past_time,
    )
    db.add(state)

    log_audit_event(
        db=db,
        action_type="HYPOTHESIS_UPDATED",
        target_type="hypothesis",
        target_id="1",
        description="Updated weight",
        case_id=alert_test_case.id,
        user_id=analyst.id,
        user_name=analyst.full_name,
        user_role=analyst.role,
        commit=True,
    )

    away_summary = get_since_you_were_away(case_id=alert_test_case.id, user=lead, db=db)
    assert away_summary["hours_away"] >= 5.9
    assert away_summary["case_id"] == alert_test_case.id
    assert "headline" in away_summary
    assert len(away_summary["summary_points"]) >= 1

    # Update last seen
    update_user_case_last_seen(case_id=alert_test_case.id, user_id=lead.id, db=db)
    db.refresh(state)
    assert (datetime.now(timezone.utc) - state.last_seen_at.replace(tzinfo=timezone.utc)).total_seconds() < 10


def test_api_alerts_endpoints(client, alert_test_case, analyst_headers):
    # Test GET /cases/{case_id}/alerts
    res = client.get(f"/cases/{alert_test_case.id}/alerts", headers=analyst_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # Test GET /cases/{case_id}/deadlines
    res_dl = client.get(f"/cases/{alert_test_case.id}/deadlines", headers=analyst_headers)
    assert res_dl.status_code == 200
    assert isinstance(res_dl.json(), list)

    # Test GET /cases/{case_id}/handover/since-away
    res_away = client.get(f"/cases/{alert_test_case.id}/handover/since-away", headers=analyst_headers)
    assert res_away.status_code == 200
    away_json = res_away.json()
    assert "headline" in away_json
    assert "summary_points" in away_json
